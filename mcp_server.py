"""
Mizushima MCP: servidor MCP de notas, tareas, skills y consultas a internet.

  TOOLS      → acciones que el cliente/agente ejecuta (14)
               · 3 consumen APIs públicas de internet (sin clave):
                   clima          → Open-Meteo        (open-meteo.com), respaldo wttr.in
                   convertir_moneda → ExchangeRate-API (exchangerate-api.com)
                   buscar_wikipedia → Wikipedia        (wikipedia.org)
  RESOURCES  → datos que se leen por URI: notas, tareas, skills e info del servidor
  PROMPTS    → plantillas reutilizables (3 de ellas usan las APIs de internet)

Para AGREGAR cosas:
  - Tool nueva:   una función con @mcp.tool()
  - Skill nueva:  desde un cliente con la tool crear_skill (el agente: /nueva-skill <nombre>)
                  o creando skills/<nombre>.md  (se publica sola en skills://<nombre>)
  - Prompt nuevo: una función con @mcp.prompt()

Transporte (variable MCP_TRANSPORT):
  stdio (por defecto)  → el cliente lanza este archivo como subproceso (uso local)
  streamable-http      → servidor HTTP en http://HOST:PORT/mcp (ngrok, Render, red local)

No pide autenticación: cualquier cliente MCP puede conectarse a la URL.

Instalación: python -m pip install -r requirements-server.txt
"""
import asyncio, json, os, re, sys, time, datetime, unicodedata
from pathlib import Path
from urllib.parse import quote, unquote
from zoneinfo import ZoneInfo

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

try:  # carga variables desde .env si existe (opcional)
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:
    pass

BASE = Path(__file__).parent
NOTAS, TAREAS, SKILLS = BASE / "notas.json", BASE / "tareas.json", BASE / "skills"
VERSION = "2.0.0"

# Skills que vienen con el proyecto: se pueden leer pero no borrar desde un cliente
SKILLS_BASE = {"redaccion", "organizacion_de_tareas", "investigacion_web", "consultas_externas"}

# ── Red ──
HOST, PORT = os.getenv("HOST", "127.0.0.1"), int(os.getenv("PORT", "8000"))
EXTRA_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]

# Protección DNS rebinding: en 127.0.0.1 solo acepta Host locales o los de ALLOWED_HOSTS.
# Con ngrok usa --host-header=rewrite. En Render/Docker (HOST=0.0.0.0) se desactiva.
seguridad = TransportSecuritySettings(
    enable_dns_rebinding_protection=HOST in ("127.0.0.1", "localhost", "::1"),
    allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"] + EXTRA_HOSTS,
    allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
                    + [f"https://{h}" for h in EXTRA_HOSTS],
)

mcp = FastMCP(
    "mizushima",
    instructions=(
        "Servidor MCP de Mizushima. Tiene notas, tareas, skills (guías de buenas prácticas en "
        "skills://<nombre>) y tres tools que consultan internet: clima (Open-Meteo), "
        "convertir_moneda (ExchangeRate-API) y buscar_wikipedia (Wikipedia). "
        "Antes de redactar, planear o consultar internet, lee la skill correspondiente."
    ),
    log_level="WARNING", host=HOST, port=PORT, transport_security=seguridad,
    stateless_http=True,   # cada petición es independiente: ideal detrás de Render/ngrok
    json_response=True,    # respuestas JSON simples: compatible con más clientes
)


def _load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def _save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Cliente HTTP para las APIs de internet (las pruebas reemplazan esta función) ──
USER_AGENT = f"MizushimaMCP/{VERSION} (proyecto educativo; https://github.com)"

async def _get_json(url: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": USER_AGENT},
                                 follow_redirects=True) as http:
        r = await http.get(url, params=params)
        r.raise_for_status()
        return r.json()


# ════════════════════════ TOOLS ════════════════════════
# ── Notas ──
@mcp.tool()
def guardar_nota(titulo: str, texto: str) -> str:
    """Guarda (o sobrescribe) una nota con un título."""
    data = _load(NOTAS, {})
    data[titulo] = texto
    _save(NOTAS, data)
    return f"Nota '{titulo}' guardada."

@mcp.tool()
def buscar_notas(consulta: str) -> str:
    """Busca notas cuyo título o texto contenga la consulta."""
    q = consulta.lower()
    hits = {t: x for t, x in _load(NOTAS, {}).items() if q in t.lower() or q in x.lower()}
    return json.dumps(hits, ensure_ascii=False) if hits else "Sin resultados."

@mcp.tool()
def listar_notas() -> str:
    """Lista los títulos de todas las notas guardadas."""
    return json.dumps(list(_load(NOTAS, {})), ensure_ascii=False)

@mcp.tool()
def borrar_nota(titulo: str) -> str:
    """Borra una nota por su título exacto."""
    data = _load(NOTAS, {})
    if titulo not in data:
        return f"La nota '{titulo}' no existe."
    del data[titulo]
    _save(NOTAS, data)
    return f"Nota '{titulo}' borrada."

# ── Tareas ──
@mcp.tool()
def agregar_tarea(texto: str, prioridad: str = "media") -> str:
    """Agrega una tarea pendiente. prioridad: alta, media o baja."""
    if prioridad not in ("alta", "media", "baja"):
        return "Prioridad inválida: usa alta, media o baja."
    tareas = _load(TAREAS, [])
    nueva_id = max((t["id"] for t in tareas), default=0) + 1
    tareas.append({"id": nueva_id, "texto": texto, "prioridad": prioridad, "hecha": False})
    _save(TAREAS, tareas)
    return f"Tarea #{nueva_id} agregada ({prioridad})."

@mcp.tool()
def listar_tareas(solo_pendientes: bool = True) -> str:
    """Lista las tareas. Por defecto solo las pendientes."""
    tareas = [t for t in _load(TAREAS, []) if not (solo_pendientes and t["hecha"])]
    return json.dumps(tareas, ensure_ascii=False) if tareas else "No hay tareas."

@mcp.tool()
def completar_tarea(id: int) -> str:
    """Marca una tarea como hecha usando su id."""
    tareas = _load(TAREAS, [])
    for t in tareas:
        if t["id"] == id:
            t["hecha"] = True
            _save(TAREAS, tareas)
            return f"Tarea #{id} completada."
    return f"No existe la tarea #{id}."

# ── Skills: guías en skills/<nombre>.md ──
MAX_SKILL = 20_000  # caracteres

def _nombre_skill(nombre: str) -> str:
    """'Revisión de Código' → 'revision_de_codigo' (solo a-z, 0-9, _ y -)."""
    n = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"[^a-z0-9_-]+", "_", n).strip("_-")[:50]

@mcp.tool()
def listar_skills() -> str:
    """Lista las skills disponibles con su título. Léelas con el resource skills://<nombre>."""
    SKILLS.mkdir(exist_ok=True)
    filas = []
    for p in sorted(SKILLS.glob("*.md")):
        primera = p.read_text(encoding="utf-8").strip().splitlines()[:1]
        filas.append(f"- {p.stem}: {primera[0].lstrip('# ').strip() if primera else ''}")
    return "\n".join(filas) if filas else "No hay skills."

@mcp.tool()
def crear_skill(nombre: str, contenido: str, sobrescribir: bool = False) -> str:
    """Crea una skill nueva: una guía en Markdown con pasos para hacer bien una tarea.
    Queda guardada en el servidor y disponible en skills://<nombre>.
    Usa sobrescribir=True solo si el usuario pidió reemplazar una skill existente."""
    n = _nombre_skill(nombre)
    if len(n) < 2:
        return "Nombre inválido: usa letras y números, ej. revision_de_codigo."
    if not contenido.strip():
        return "La skill está vacía."
    if len(contenido) > MAX_SKILL:
        return f"La skill es muy larga (máximo {MAX_SKILL} caracteres)."
    if n in SKILLS_BASE:
        return f"'{n}' es una skill base del proyecto y no se puede reemplazar. Usa otro nombre."
    SKILLS.mkdir(exist_ok=True)
    path = SKILLS / f"{n}.md"
    if path.exists() and not sobrescribir:
        return f"Ya existe la skill '{n}'. Para reemplazarla usa sobrescribir=True."
    texto = contenido.strip()
    if not texto.startswith("#"):
        texto = f"# Skill: {nombre.strip()}\n\n{texto}"
    path.write_text(texto + "\n", encoding="utf-8")
    return f"Skill '{n}' {'actualizada' if sobrescribir else 'creada'}. Disponible en skills://{n}"

@mcp.tool()
def borrar_skill(nombre: str) -> str:
    """Borra una skill creada por un usuario (las skills base del proyecto no se pueden borrar)."""
    n = _nombre_skill(nombre)
    if n in SKILLS_BASE:
        return f"'{n}' es una skill base del proyecto y no se puede borrar."
    path = SKILLS / f"{n}.md"
    if not path.exists():
        return f"La skill '{nombre}' no existe."
    path.unlink()
    return f"Skill '{n}' borrada."

# ── Utilidades ──
@mcp.tool()
def hora_actual(zona: str = "America/Bogota") -> str:
    """Fecha y hora actual en una zona horaria IANA (ej: America/Bogota, Europe/Madrid, UTC)."""
    try:
        return datetime.datetime.now(ZoneInfo(zona)).strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return f"Zona horaria inválida: {zona}"


# ── APIs de internet (3 servicios distintos, ninguno pide clave) ──
CLIMA_WMO = {
    0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
    45: "Niebla", 48: "Niebla con escarcha", 51: "Llovizna ligera", 53: "Llovizna moderada",
    55: "Llovizna intensa", 56: "Llovizna helada ligera", 57: "Llovizna helada intensa",
    61: "Lluvia ligera", 63: "Lluvia moderada", 65: "Lluvia fuerte", 66: "Lluvia helada ligera",
    67: "Lluvia helada fuerte", 71: "Nevada ligera", 73: "Nevada moderada", 75: "Nevada fuerte",
    77: "Granos de nieve", 80: "Chubascos ligeros", 81: "Chubascos moderados",
    82: "Chubascos violentos", 85: "Chubascos de nieve ligeros", 86: "Chubascos de nieve fuertes",
    95: "Tormenta eléctrica", 96: "Tormenta con granizo ligero", 99: "Tormenta con granizo fuerte",
}

def _codigo_http(e: Exception) -> str:
    """'HTTP 429' si el error trae respuesta, o el nombre del error (ej. ConnectTimeout)."""
    r = getattr(e, "response", None)
    return f"HTTP {r.status_code}" if r is not None else type(e).__name__


async def _get_json_reintento(url: str, params: dict | None = None) -> dict:
    """Como _get_json, pero reintenta una vez si el servicio está saturado (429, 5xx) o tarda."""
    try:
        return await _get_json(url, params)
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 429 and e.response.status_code < 500:
            raise
    except (httpx.TimeoutException, httpx.TransportError):
        pass
    await asyncio.sleep(1.5)
    return await _get_json(url, params)


_CACHE_CLIMA: dict = {}   # (ciudad, dias) → (momento, texto): evita repetir consultas por 10 min
CACHE_SEGUNDOS = 600


@mcp.tool()
async def clima(ciudad: str, dias: int = 3) -> str:
    """Clima actual y pronóstico (1 a 7 días) de una ciudad. API: Open-Meteo (open-meteo.com),
    con wttr.in como respaldo si Open-Meteo no responde.
    Ej: ciudad='Medellín'. Devuelve temperatura, sensación, humedad, viento y probabilidad de lluvia."""
    dias = max(1, min(int(dias), 7))
    clave = (ciudad.strip().lower(), dias)
    if clave in _CACHE_CLIMA and time.time() - _CACHE_CLIMA[clave][0] < CACHE_SEGUNDOS:
        return _CACHE_CLIMA[clave][1]
    try:
        geo = await _get_json_reintento("https://geocoding-api.open-meteo.com/v1/search",
                                        {"name": ciudad, "count": 1, "language": "es", "format": "json"})
        if not geo.get("results"):
            return f"No encontré la ciudad '{ciudad}'. Prueba con otro nombre (ej: 'Bogotá' o 'Madrid')."
        lugar = geo["results"][0]
        datos = await _get_json_reintento("https://api.open-meteo.com/v1/forecast", {
            "latitude": lugar["latitude"], "longitude": lugar["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto", "forecast_days": dias,
        })
    except httpx.HTTPError as e:
        texto = await _clima_respaldo(ciudad, dias, motivo=_codigo_http(e))
    else:
        texto = _formato_open_meteo(lugar, datos)
    if not texto.startswith("No pude"):
        _CACHE_CLIMA[clave] = (time.time(), texto)
    return texto


def _formato_open_meteo(lugar: dict, datos: dict) -> str:
    nombre = ", ".join(x for x in (lugar.get("name"), lugar.get("admin1"), lugar.get("country")) if x)
    a = datos.get("current", {})
    lineas = [
        f"Clima en {nombre} (hora local {a.get('time', '?').replace('T', ' ')})",
        f"Ahora: {a.get('temperature_2m')} °C (sensación {a.get('apparent_temperature')} °C), "
        f"{CLIMA_WMO.get(a.get('weather_code'), 'condición desconocida')}, "
        f"humedad {a.get('relative_humidity_2m')} %, viento {a.get('wind_speed_10m')} km/h",
        "Pronóstico:",
    ]
    d = datos.get("daily", {})
    for i, fecha in enumerate(d.get("time", [])):
        prob = (d.get("precipitation_probability_max") or [None] * (i + 1))[i]
        lineas.append(
            f"- {fecha}: máx {d['temperature_2m_max'][i]} °C / mín {d['temperature_2m_min'][i]} °C, "
            f"{CLIMA_WMO.get(d['weather_code'][i], '?')}"
            + (f", prob. de lluvia {prob} %" if prob is not None else ""))
    lineas.append("Fuente: Open-Meteo (https://open-meteo.com)")
    return "\n".join(lineas)


async def _clima_respaldo(ciudad: str, dias: int, motivo: str) -> str:
    """Respaldo con wttr.in (sin clave, máximo 3 días) cuando Open-Meteo falla."""
    def valor(lista, campo="value"):
        return (lista or [{}])[0].get(campo, "") if isinstance(lista, list) else ""
    try:
        d = await _get_json_reintento(f"https://wttr.in/{quote(ciudad)}", {"format": "j1", "lang": "es"})
    except httpx.HTTPError as e:
        return (f"No pude consultar el clima: Open-Meteo ({motivo}) y wttr.in ({_codigo_http(e)}) "
                "no respondieron. Intenta de nuevo en un momento.")
    actual = (d.get("current_condition") or [{}])[0]
    area = (d.get("nearest_area") or [{}])[0]
    nombre = ", ".join(x for x in (valor(area.get("areaName")), valor(area.get("region")),
                                   valor(area.get("country"))) if x) or ciudad
    descripcion = valor(actual.get("lang_es")) or valor(actual.get("weatherDesc")) or "condición desconocida"
    lineas = [
        f"Clima en {nombre}",
        f"Ahora: {actual.get('temp_C', '?')} °C (sensación {actual.get('FeelsLikeC', '?')} °C), "
        f"{descripcion}, humedad {actual.get('humidity', '?')} %, viento {actual.get('windspeedKmph', '?')} km/h",
        "Pronóstico:",
    ]
    for dia in (d.get("weather") or [])[:dias]:
        lluvias = [int(h.get("chanceofrain", 0) or 0) for h in dia.get("hourly", [])]
        lineas.append(f"- {dia.get('date', '?')}: máx {dia.get('maxtempC', '?')} °C / mín {dia.get('mintempC', '?')} °C"
                      + (f", prob. de lluvia {max(lluvias)} %" if lluvias else ""))
    if dias > 3:
        lineas.append("(El servicio de respaldo solo da 3 días de pronóstico.)")
    lineas.append(f"Fuente: wttr.in (https://wttr.in), respaldo porque Open-Meteo no respondió ({motivo})")
    return "\n".join(lineas)


@mcp.tool()
async def convertir_moneda(monto: float, de: str = "USD", a: str = "COP") -> str:
    """Convierte dinero entre monedas con la tasa del día. API: ExchangeRate-API (exchangerate-api.com).
    Usa códigos ISO 4217: USD, COP, EUR, MXN, ARS, BRL, GBP, JPY... Ej: monto=100, de='USD', a='COP'."""
    de, a = de.strip().upper(), a.strip().upper()
    try:
        datos = await _get_json_reintento(f"https://open.er-api.com/v6/latest/{quote(de)}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Moneda de origen no válida: '{de}'. Usa un código ISO como USD, COP o EUR."
        return f"No pude consultar ExchangeRate-API ({_codigo_http(e)}). Intenta de nuevo en un momento."
    except httpx.HTTPError as e:
        return f"No pude consultar ExchangeRate-API ({_codigo_http(e)}). Intenta de nuevo en un momento."
    if datos.get("result") != "success":
        return f"Moneda de origen no válida: '{de}' ({datos.get('error-type', 'error')}). Usa códigos como USD, COP, EUR."
    tasa = datos.get("rates", {}).get(a)
    if tasa is None:
        return f"Moneda de destino no válida: '{a}'. Usa un código ISO como USD, COP o EUR."
    total = monto * tasa
    return (f"{monto:,.2f} {de} = {total:,.2f} {a}\n"
            f"Tasa: 1 {de} = {tasa:,.4f} {a}\n"
            f"Actualizada: {datos.get('time_last_update_utc', '?')}\n"
            "Fuente: Rates By Exchange Rate API (https://www.exchangerate-api.com)")


@mcp.tool()
async def buscar_wikipedia(tema: str, idioma: str = "es") -> str:
    """Busca un tema en Wikipedia y devuelve su resumen y enlace. API: Wikipedia REST (wikipedia.org).
    idioma: código de Wikipedia (es, en, pt, fr...)."""
    idioma = idioma.strip().lower()
    if not re.fullmatch(r"[a-z]{2,3}", idioma):
        return "Idioma inválido: usa un código como es, en o pt."
    base = f"https://{idioma}.wikipedia.org"
    try:
        busqueda = await _get_json_reintento(f"{base}/w/rest.php/v1/search/page", {"q": tema, "limit": 1})
        paginas = busqueda.get("pages") or []
        if not paginas:
            return f"No encontré '{tema}' en Wikipedia ({idioma})."
        resumen = await _get_json_reintento(f"{base}/api/rest_v1/page/summary/{quote(paginas[0]['key'], safe='')}")
    except httpx.HTTPError as e:
        return f"No pude consultar Wikipedia ({_codigo_http(e)}). Intenta de nuevo en un momento."
    url = resumen.get("content_urls", {}).get("desktop", {}).get("page", f"{base}/wiki/{paginas[0]['key']}")
    partes = [f"{resumen.get('title', paginas[0]['title'])}"]
    if resumen.get("description"):
        partes[0] += f" ({resumen['description']})"
    if resumen.get("type") == "disambiguation":
        partes.append("Es una página de desambiguación: el tema tiene varios significados. Sé más específico.")
    partes.append(resumen.get("extract") or re.sub(r"<[^>]+>", "", paginas[0].get("excerpt", "")))
    partes.append(f"Enlace: {url}")
    partes.append("Fuente: Wikipedia (https://www.wikipedia.org), licencia CC BY-SA")
    return "\n".join(partes)


# ════════════════════════ RESOURCES ════════════════════════
@mcp.resource("info://servidor")
def recurso_info() -> str:
    """Qué es este servidor, qué APIs usa y cómo agregar skills."""
    return json.dumps({
        "nombre": "Mizushima MCP", "version": VERSION,
        "apis_externas": {
            "clima": "Open-Meteo (https://open-meteo.com), respaldo wttr.in (https://wttr.in)",
            "convertir_moneda": "ExchangeRate-API (https://www.exchangerate-api.com)",
            "buscar_wikipedia": "Wikipedia REST (https://www.wikipedia.org)",
        },
        "autenticacion": "ninguna",
        "agregar_skills": "tool crear_skill, o archivo skills/<nombre>.md en el servidor",
    }, ensure_ascii=False, indent=2)

@mcp.resource("notas://lista")
def recurso_lista_notas() -> str:
    """Títulos de todas las notas guardadas."""
    return json.dumps(list(_load(NOTAS, {})), ensure_ascii=False)

@mcp.resource("notas://todas")
def recurso_todas_notas() -> str:
    """Todas las notas con su contenido ({titulo: texto})."""
    return json.dumps(_load(NOTAS, {}), ensure_ascii=False)

@mcp.resource("notas://{titulo}")
def recurso_nota(titulo: str) -> str:
    """Contenido de una nota por su título. Si tiene espacios, codifícalos: notas://Mi%20nota"""
    return _load(NOTAS, {}).get(unquote(titulo), "La nota no existe.")

@mcp.resource("tareas://pendientes")
def recurso_tareas_pendientes() -> str:
    """Tareas aún no completadas."""
    return json.dumps([t for t in _load(TAREAS, []) if not t["hecha"]], ensure_ascii=False)

@mcp.resource("tareas://todas")
def recurso_tareas_todas() -> str:
    """Todas las tareas, hechas y pendientes."""
    return json.dumps(_load(TAREAS, []), ensure_ascii=False)

@mcp.resource("skills://indice")
def recurso_indice_skills() -> str:
    """Lista las skills disponibles (guías de cómo hacer bien ciertas tareas)."""
    return json.dumps(sorted(p.stem for p in SKILLS.glob("*.md")), ensure_ascii=False)

@mcp.resource("skills://{nombre}")
def recurso_skill(nombre: str) -> str:
    """Texto de una skill. Consulta skills://indice para ver cuáles hay."""
    path = SKILLS / f"{Path(nombre).name}.md"  # Path().name evita salirse de la carpeta
    return path.read_text(encoding="utf-8") if path.exists() else "La skill no existe."


# ════════════════════════ PROMPTS ════════════════════════
# ── Prompts que consumen las APIs de internet ──
@mcp.prompt()
def reporte_clima(ciudad: str) -> str:
    """[API Open-Meteo] Reporte del clima de una ciudad con recomendaciones prácticas."""
    return (f"Lee skills://consultas_externas. Usa la tool clima con ciudad='{ciudad}' y dias=3. "
            "Con el resultado escribe un reporte corto: cómo está ahora, cómo vienen los próximos días "
            "y 3 recomendaciones concretas (ropa, paraguas, mejor momento para salir). "
            "Cita la fuente al final.")

@mcp.prompt()
def presupuesto_viaje(destino: str, monto: str, moneda_origen: str = "COP", moneda_destino: str = "USD") -> str:
    """[APIs ExchangeRate-API + Open-Meteo] Convierte un presupuesto de viaje y revisa el clima del destino."""
    return (f"Lee skills://consultas_externas. Voy a viajar a {destino} con un presupuesto de "
            f"{monto} {moneda_origen}. 1) Usa convertir_moneda para pasarlo a {moneda_destino}. "
            f"2) Usa clima con ciudad='{destino}' y dias=5. 3) Dame un resumen con el presupuesto "
            "convertido, qué clima esperar, qué empacar y un presupuesto diario sugerido. "
            "Indica la fecha de la tasa y las fuentes.")

@mcp.prompt()
def investigar_tema(tema: str) -> str:
    """[API Wikipedia] Investiga un tema en Wikipedia y lo guarda como nota."""
    return (f"Lee skills://investigacion_web. Usa buscar_wikipedia con tema='{tema}'. Resume lo más "
            f"importante en 5 puntos con el enlace de la fuente y guárdalo con guardar_nota usando "
            f"el título 'Investigación: {tema}'.")

# ── Prompts de notas y tareas ──
@mcp.prompt()
def resumir_notas() -> str:
    """Resume todas las notas guardadas."""
    return "Lee notas://todas y haz un resumen de 3 líneas."

@mcp.prompt()
def plan_del_dia() -> str:
    """Arma un plan del día con las tareas pendientes."""
    return ("Lee skills://organizacion_de_tareas y tareas://pendientes, y consulta hora_actual. "
            "Arma un plan del día ordenado por prioridad (alta primero), con horarios sugeridos.")

@mcp.prompt()
def revisar_tareas() -> str:
    """Revisa el estado de las tareas y sugiere qué hacer."""
    return ("Lista todas las tareas (hechas y pendientes). Dime cuántas van, cuáles son "
            "urgentes y cuál deberías hacer primero.")

@mcp.prompt()
def notas_a_tareas(titulo: str) -> str:
    """Convierte el contenido de una nota en tareas."""
    return (f"Lee la nota '{titulo}' (notas://{quote(titulo)}), identifica las acciones concretas "
            f"que contiene y créalas como tareas con agregar_tarea, asignando prioridad.")

@mcp.prompt()
def explicar_tema(tema: str, nivel: str = "básico") -> str:
    """Explica un tema con el nivel pedido (básico, intermedio o avanzado)."""
    return f"Explica '{tema}' a nivel {nivel}, con un ejemplo concreto y en máximo 8 líneas."

@mcp.prompt()
def redactar_con_estilo(texto: str) -> str:
    """Reescribe un texto siguiendo la skill de redacción."""
    return f"Lee skills://redaccion y reescribe el siguiente texto aplicando esa guía:\n\n{texto}"


# ════════════════════════ RUTAS HTTP EXTRA ════════════════════════
# Útiles al abrir la URL en el navegador y para el health check de Render.
from starlette.requests import Request
from starlette.responses import JSONResponse

@mcp.custom_route("/", methods=["GET"])
async def inicio(request: Request) -> JSONResponse:
    base = str(request.base_url).rstrip("/")
    return JSONResponse({
        "servidor": "Mizushima MCP", "version": VERSION,
        "endpoint_mcp": f"{base}/mcp", "transporte": "streamable-http", "autenticacion": "ninguna",
        "como_usar": "Conecta cualquier cliente MCP a endpoint_mcp. Ej: npx @modelcontextprotocol/inspector",
        "tools": [t.name for t in await mcp.list_tools()],
        "prompts": [p.name for p in await mcp.list_prompts()],
        "resources": [str(r.uri) for r in await mcp.list_resources()],
    })

@mcp.custom_route("/salud", methods=["GET"])
async def salud(request: Request) -> JSONResponse:
    return JSONResponse({"estado": "ok"})


if __name__ == "__main__":
    # No uses print() en stdio: stdout es el canal del protocolo (los mensajes van a stderr)
    transporte = os.getenv("MCP_TRANSPORT", "stdio")
    if transporte != "stdio":
        print(f"Servidor MCP Mizushima en http://{HOST}:{PORT}/mcp  (sin autenticación)", file=sys.stderr)
    mcp.run(transport=transporte)
