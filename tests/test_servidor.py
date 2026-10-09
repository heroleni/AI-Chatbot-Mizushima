"""
Pruebas del servidor MCP (no necesitan internet ni API keys: las APIs se simulan).

Ejecutar:  python -m pip install pytest  &&  python -m pytest -v
"""
import asyncio, json, os, shutil, socket, subprocess, sys, time
from pathlib import Path

import httpx
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import mcp_server as srv  # noqa: E402


def correr(coro):
    return asyncio.run(coro)


def texto(resultado) -> str:
    """call_tool devuelve (contenido, estructurado) o una lista de bloques: extrae el texto."""
    if isinstance(resultado, tuple):
        resultado = resultado[0]
    return "".join(getattr(b, "text", "") for b in resultado)


# ── Datos aislados: cada prueba usa una carpeta temporal ──
@pytest.fixture(autouse=True)
def datos_temporales(tmp_path, monkeypatch):
    shutil.copytree(RAIZ / "skills", tmp_path / "skills")
    monkeypatch.setattr(srv, "NOTAS", tmp_path / "notas.json")
    monkeypatch.setattr(srv, "TAREAS", tmp_path / "tareas.json")
    monkeypatch.setattr(srv, "SKILLS", tmp_path / "skills")
    srv._CACHE_CLIMA.clear()

    async def sin_espera(_):  # los reintentos no esperan en las pruebas
        return None
    monkeypatch.setattr(srv.asyncio, "sleep", sin_espera)


# ── APIs simuladas con respuestas reales de ejemplo ──
RESPUESTAS = {
    "geocoding-api.open-meteo.com": {"results": [{"name": "Medellín", "latitude": 6.245, "longitude": -75.57,
                                                  "country": "Colombia", "admin1": "Antioquia"}]},
    "api.open-meteo.com": {
        "current": {"time": "2026-10-09T08:15", "temperature_2m": 21.3, "relative_humidity_2m": 78,
                    "apparent_temperature": 22.0, "weather_code": 2, "wind_speed_10m": 6.1},
        "daily": {"time": ["2026-10-09", "2026-10-10"], "weather_code": [61, 3],
                  "temperature_2m_max": [26.1, 25.0], "temperature_2m_min": [16.2, 15.8],
                  "precipitation_probability_max": [70, 20]},
    },
    "open.er-api.com/v6/latest/USD": {"result": "success", "base_code": "USD",
                                      "time_last_update_utc": "Thu, 08 Oct 2026 00:02:31 +0000",
                                      "rates": {"USD": 1, "COP": 3236.841046, "EUR": 0.892949}},
    "wikipedia.org/w/rest.php": {"pages": [{"id": 1, "key": "Medellín", "title": "Medellín",
                                            "excerpt": "<span>Medellín</span> es una ciudad"}]},
    "wikipedia.org/api/rest_v1": {"type": "standard", "title": "Medellín", "description": "ciudad de Colombia",
                                  "extract": "Medellín es la capital del departamento de Antioquia.",
                                  "content_urls": {"desktop": {"page": "https://es.wikipedia.org/wiki/Medell%C3%ADn"}}},
}


@pytest.fixture
def apis(monkeypatch):
    llamadas = []

    async def falso(url, params=None):
        llamadas.append(url)
        if "open.er-api.com" in url and not url.endswith("/USD"):
            raise httpx.HTTPStatusError("404", request=httpx.Request("GET", url),
                                        response=httpx.Response(404))
        if params and params.get("name") == "Ciudadinexistente":
            return {"generationtime_ms": 0.1}
        for clave, valor in RESPUESTAS.items():
            if clave in url:
                return valor
        raise AssertionError(f"URL no simulada: {url}")

    monkeypatch.setattr(srv, "_get_json", falso)
    return llamadas


# ════════════════ Criterios de aceptación ════════════════
def test_al_menos_cinco_tools_y_tres_de_internet():
    nombres = {t.name for t in correr(srv.mcp.list_tools())}
    assert len(nombres) >= 5
    assert {"clima", "convertir_moneda", "buscar_wikipedia"} <= nombres


def test_al_menos_tres_recursos():
    recursos = correr(srv.mcp.list_resources())
    plantillas = correr(srv.mcp.list_resource_templates())
    assert len(recursos) >= 3
    assert {"notas://{titulo}", "skills://{nombre}"} <= {t.uriTemplate for t in plantillas}


def test_al_menos_dos_prompts_de_apis():
    prompts = correr(srv.mcp.list_prompts())
    de_api = [p.name for p in prompts if (p.description or "").startswith("[API")]
    assert len(de_api) >= 2, de_api


def test_apis_de_servicios_distintos(apis):
    correr(srv.mcp.call_tool("clima", {"ciudad": "Medellín"}))
    correr(srv.mcp.call_tool("convertir_moneda", {"monto": 1, "de": "USD", "a": "COP"}))
    correr(srv.mcp.call_tool("buscar_wikipedia", {"tema": "Medellín"}))
    dominios = {httpx.URL(u).host.split(".", 1)[-1] if "wikipedia" in u else httpx.URL(u).host for u in apis}
    servicios = {("open-meteo" if "open-meteo" in d else "er-api" if "er-api" in d else "wikipedia") for d in dominios}
    assert servicios == {"open-meteo", "er-api", "wikipedia"}


# ════════════════ Tools de internet ════════════════
def test_clima(apis):
    r = texto(correr(srv.mcp.call_tool("clima", {"ciudad": "Medellín", "dias": 2})))
    assert "Medellín, Antioquia, Colombia" in r
    assert "21.3 °C" in r and "Parcialmente nublado" in r
    assert "prob. de lluvia 70 %" in r and "Open-Meteo" in r


def test_clima_ciudad_inexistente(apis):
    r = texto(correr(srv.mcp.call_tool("clima", {"ciudad": "Ciudadinexistente"})))
    assert "No encontré" in r


def test_convertir_moneda(apis):
    r = texto(correr(srv.mcp.call_tool("convertir_moneda", {"monto": 100, "de": "usd", "a": "cop"})))
    assert "100.00 USD = 323,684.10 COP" in r
    assert "Exchange Rate API" in r and "2026" in r


def test_convertir_moneda_invalida(apis):
    assert "destino no válida" in texto(correr(srv.mcp.call_tool("convertir_moneda", {"monto": 1, "de": "USD", "a": "XXX"})))
    assert "origen no válida" in texto(correr(srv.mcp.call_tool("convertir_moneda", {"monto": 1, "de": "ZZZ", "a": "COP"})))


def test_buscar_wikipedia(apis):
    r = texto(correr(srv.mcp.call_tool("buscar_wikipedia", {"tema": "Medellín"})))
    assert "capital del departamento de Antioquia" in r
    assert "https://es.wikipedia.org/wiki/" in r


def test_clima_usa_respaldo_si_open_meteo_falla(monkeypatch):
    llamadas = []

    async def falso(url, params=None):
        llamadas.append(url)
        if "open-meteo" in url:
            raise httpx.HTTPStatusError("429", request=httpx.Request("GET", url), response=httpx.Response(429))
        return {
            "current_condition": [{"temp_C": "20", "FeelsLikeC": "21", "humidity": "80", "windspeedKmph": "7",
                                   "weatherDesc": [{"value": "Partly cloudy"}], "lang_es": [{"value": "Parcialmente nublado"}]}],
            "nearest_area": [{"areaName": [{"value": "Medellin"}], "region": [{"value": "Antioquia"}],
                              "country": [{"value": "Colombia"}]}],
            "weather": [{"date": "2026-10-09", "maxtempC": "26", "mintempC": "16",
                         "hourly": [{"chanceofrain": "10"}, {"chanceofrain": "65"}]}],
        }
    monkeypatch.setattr(srv, "_get_json", falso)
    r = texto(correr(srv.mcp.call_tool("clima", {"ciudad": "Medellín", "dias": 1})))
    assert "Fuente: wttr.in" in r and "HTTP 429" in r
    assert "20 °C" in r and "Parcialmente nublado" in r and "prob. de lluvia 65 %" in r
    assert sum("open-meteo" in u for u in llamadas) == 2  # reintentó una vez antes del respaldo


def test_clima_usa_cache(apis):
    correr(srv.mcp.call_tool("clima", {"ciudad": "Medellín"}))
    antes = len(apis)
    correr(srv.mcp.call_tool("clima", {"ciudad": "medellín"}))
    assert len(apis) == antes


def test_api_caida_no_rompe_el_servidor(monkeypatch):
    async def caida(url, params=None):
        raise httpx.ConnectError("sin red")
    monkeypatch.setattr(srv, "_get_json", caida)
    assert "No pude consultar" in texto(correr(srv.mcp.call_tool("clima", {"ciudad": "Lima"})))
    assert "No pude consultar" in texto(correr(srv.mcp.call_tool("convertir_moneda", {"monto": 1})))


# ════════════════ Skills, notas y tareas ════════════════
def test_crear_leer_y_borrar_skill():
    r = texto(correr(srv.mcp.call_tool("crear_skill", {"nombre": "Revisión de Código", "contenido": "1. Lee todo."})))
    assert "skills://revision_de_codigo" in r
    contenido = list(correr(srv.mcp.read_resource("skills://revision_de_codigo")))[0].content
    assert "Lee todo" in contenido
    assert "borrada" in texto(correr(srv.mcp.call_tool("borrar_skill", {"nombre": "revision_de_codigo"})))


def test_skills_base_protegidas():
    assert "no se puede borrar" in texto(correr(srv.mcp.call_tool("borrar_skill", {"nombre": "redaccion"})))
    assert "no se puede reemplazar" in texto(correr(srv.mcp.call_tool(
        "crear_skill", {"nombre": "redaccion", "contenido": "x", "sobrescribir": True})))


def test_nota_con_espacios_y_tareas():
    correr(srv.mcp.call_tool("guardar_nota", {"titulo": "Ideas despliegue", "texto": "Render"}))
    assert list(correr(srv.mcp.read_resource("notas://Ideas%20despliegue")))[0].content == "Render"
    correr(srv.mcp.call_tool("agregar_tarea", {"texto": "Enviar correo", "prioridad": "alta"}))
    pendientes = json.loads(list(correr(srv.mcp.read_resource("tareas://pendientes")))[0].content)
    assert pendientes[0]["texto"] == "Enviar correo"


# ════════════════ Despliegue HTTP sin autenticación (como en Render) ════════════════
def _puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_servidor_http_sin_autenticacion(tmp_path):
    puerto = _puerto_libre()
    env = {**os.environ, "MCP_TRANSPORT": "streamable-http", "HOST": "0.0.0.0", "PORT": str(puerto)}
    proc = subprocess.Popen([sys.executable, str(RAIZ / "mcp_server.py")], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        url = f"http://127.0.0.1:{puerto}"
        for _ in range(50):
            try:
                if httpx.get(f"{url}/salud").status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.2)
        info = httpx.get(url + "/").json()
        assert info["autenticacion"] == "ninguna" and "clima" in info["tools"]

        from mcp import ClientSession
        try:  # mcp >= 1.2x
            from mcp.client.streamable_http import streamable_http_client as cliente_http
        except ImportError:
            from mcp.client.streamable_http import streamablehttp_client as cliente_http

        async def listar():
            async with cliente_http(f"{url}/mcp") as (r, w, _):
                async with ClientSession(r, w) as s:
                    await s.initialize()
                    tools = (await s.list_tools()).tools
                    hora = await s.call_tool("hora_actual", {"zona": "UTC"})
                    return [t.name for t in tools], hora.content[0].text

        nombres, hora = correr(listar())
        assert "convertir_moneda" in nombres and "UTC" in hora
    finally:
        proc.terminate()
        proc.wait(timeout=10)
