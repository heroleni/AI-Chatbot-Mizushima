"""
Verifica un servidor Mizushima MCP desplegado (Render, ngrok o local) contra los criterios de aceptación.
No necesita API keys: solo se conecta como cliente MCP y llama las tools.

Uso:
    python verificar_despliegue.py https://mizushima-mcp.onrender.com
    python verificar_despliegue.py https://xxxx.ngrok-free.app
    python verificar_despliegue.py http://127.0.0.1:8000
"""
import asyncio, sys

from mcp import ClientSession

try:  # mcp >= 1.2x
    from mcp.client.streamable_http import streamable_http_client as cliente_http
except ImportError:
    from mcp.client.streamable_http import streamablehttp_client as cliente_http

OK, MAL = "✔", "✘"


def texto(resultado) -> str:
    return "".join(getattr(b, "text", "") for b in resultado.content)


async def verificar(url: str) -> bool:
    if not url.rstrip("/").endswith("/mcp"):
        url = url.rstrip("/") + "/mcp"
    print(f"\nConectando a {url} (sin autenticación)…")
    print("Si es Render gratis y estaba dormido, puede tardar hasta un minuto.\n")
    todo_bien = True

    def check(condicion: bool, mensaje: str):
        nonlocal todo_bien
        todo_bien &= condicion
        print(f"  {OK if condicion else MAL} {mensaje}")

    async with cliente_http(url) as (r, w, _):
        async with ClientSession(r, w) as s:
            info = await s.initialize()
            print(f"  Servidor: {info.serverInfo.name} {info.serverInfo.version or ''}\n")
            tools = (await s.list_tools()).tools
            recursos = (await s.list_resources()).resources
            plantillas = (await s.list_resource_templates()).resourceTemplates
            prompts = (await s.list_prompts()).prompts

            print("Criterios de aceptación")
            check(len(recursos) + len(plantillas) >= 3, f"Recursos: {len(recursos)} fijos + {len(plantillas)} plantillas (mínimo 3)")
            check(len(tools) >= 5, f"Herramientas: {len(tools)} (mínimo 5)")
            de_api = [p.name for p in prompts if (p.description or "").startswith("[API")]
            check(len(de_api) >= 2, f"Prompts que usan APIs: {', '.join(de_api)} (mínimo 2)")
            check(True, "Conexión sin autenticación")

            print("\nAPIs de internet (llamadas reales)")
            pruebas = [
                ("clima", {"ciudad": "Medellín", "dias": 1}, "Open-Meteo"),
                ("convertir_moneda", {"monto": 100, "de": "USD", "a": "COP"}, "Exchange Rate API"),
                ("buscar_wikipedia", {"tema": "Model Context Protocol"}, "Wikipedia"),
            ]
            for nombre, args, fuente in pruebas:
                try:
                    res = texto(await s.call_tool(nombre, args))
                except Exception as e:
                    res = f"error: {e}"
                funciona = fuente in res and "No pude" not in res
                check(funciona, f"{nombre} → {fuente}")
                print("      " + res.splitlines()[0][:100] if res else "")

            res = await s.read_resource("skills://indice")
            print(f"\n  Skills en el servidor: {''.join(getattr(c, 'text', '') for c in res.contents)}")

    print("\n" + (f"{OK} Todo listo para entregar." if todo_bien else f"{MAL} Revisa los puntos marcados."))
    return todo_bien


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    try:
        sys.exit(0 if asyncio.run(verificar(sys.argv[1])) else 1)
    except Exception as e:
        causa = e
        while getattr(causa, "exceptions", None):
            causa = causa.exceptions[0]
        print(f"\n{MAL} No me pude conectar: {type(causa).__name__}: {causa}")
        sys.exit(1)
