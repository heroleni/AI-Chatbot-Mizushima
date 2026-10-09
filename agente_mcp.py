"""
Mizushima: agente LangChain por terminal que usa un servidor MCP (local o remoto).
Reutiliza tools, memoria y modelos de agente_langchain.py y suma las tools del servidor MCP.

Instalación: python -m pip install -r requirements.txt

Uso:
  python agente_mcp.py                                   → lanza el servidor MCP local él solo (stdio)
  python agente_mcp.py --url http://127.0.0.1:8000/mcp   → servidor HTTP en este mismo PC
  python agente_mcp.py --url https://xxxx.ngrok-free.app        → servidor en otro PC (ngrok)
  python agente_mcp.py --url https://mizushima-mcp.onrender.com  → servidor desplegado en Render
  python agente_mcp.py --provider google                 → arrancar con Gemini

También se puede configurar en .env: MCP_URL, PROVIDER.
Escribe /ayuda dentro del agente para ver los comandos.
"""
import argparse, asyncio, importlib.util, os, shlex, sys
from pathlib import Path

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient

from agente_langchain import MODELS, API_KEYS, PAQUETES, ALIAS, TOOLS, SYSTEM, checkpointer, long_mem, to_text

SYSTEM_MCP = SYSTEM + (
    "\n\nTienes un servidor MCP con notas, tareas y skills. Las skills son guías de buenas prácticas: "
    "lístalas con listar_skills y léelas con leer_recurso_mcp('skills://<nombre>'). Antes de redactar, "
    "planear tareas o investigar, consulta la skill correspondiente y sigue sus pasos. "
    "Si el usuario te pide crear una skill, escríbela como lista de pasos en Markdown y guárdala con crear_skill. "
    "Para clima, monedas o Wikipedia usa las tools clima, convertir_moneda y buscar_wikipedia del servidor."
)

# ── Argumentos: --url / --provider (o lo mismo en .env) ──
_args = argparse.ArgumentParser(description="Mizushima: agente por terminal con servidor MCP")
_args.add_argument("--url", default=os.getenv("MCP_URL"), help="URL del servidor MCP (si no, se lanza local por stdio)")
_args.add_argument("--provider", default=os.getenv("PROVIDER", "openai"), help="openai o google")
ARGS, _ = _args.parse_known_args()

# Conexión al servidor MCP:
#   sin URL → el agente lanza mcp_server.py como subproceso (stdio)
#   con URL → se conecta por HTTP (otra terminal, otro PC, ngrok o Render)
MCP_URL = ARGS.url
if MCP_URL:
    if not MCP_URL.rstrip("/").endswith("/mcp"):
        MCP_URL = MCP_URL.rstrip("/") + "/mcp"  # permite pegar la URL de ngrok tal cual
    # timeout amplio: en Render gratis el servidor "despierta" en ~1 minuto si estaba inactivo
    conexion = {"transport": "streamable_http", "url": MCP_URL, "timeout": 90}
else:
    conexion = {"transport": "stdio", "command": sys.executable,
                "args": [str(Path(__file__).with_name("mcp_server.py"))]}
SERVIDOR = "mizushima"
client = MultiServerMCPClient({SERVIDOR: conexion})


@tool
async def leer_recurso_mcp(uri: str) -> str:
    """Lee un resource del servidor MCP por su URI. Ej: skills://<nombre>, skills://indice, notas://todas, notas://<titulo> (espacios como %20), tareas://pendientes."""
    try:
        async with client.session(SERVIDOR) as s:
            res = await s.read_resource(uri)
        return "".join(getattr(c, "text", "") for c in res.contents)
    except BaseException:  # devolver el error al modelo en vez de romper el agente
        return f"No se pudo leer '{uri}': recurso inexistente o inválido."


# ── Utilidades para hablar con el servidor sin pasar por el modelo ──
async def llamar_tool(nombre: str, args: dict) -> str:
    async with client.session(SERVIDOR) as s:
        r = await s.call_tool(nombre, args)
    return "".join(getattr(c, "text", "") for c in r.content)


async def leer(uri: str) -> str:
    async with client.session(SERVIDOR) as s:
        res = await s.read_resource(uri)
    return "".join(getattr(c, "text", "") for c in res.contents)


AYUDA = """
  Escribe normal para hablarle a Mizushima. Comandos:

  /recursos                         tools, resources y prompts del servidor MCP
  /skills                           lista las skills
  /skill <nombre>                   muestra una skill
  /nueva-skill <nombre>             crea una skill escribiéndola aquí (termina con una línea FIN)
  /nueva-skill <nombre> <archivo>   crea una skill desde un archivo .md o .txt
  /borrar-skill <nombre>            borra una skill
  /prompt <nombre> [clave=valor]    usa un prompt del servidor. Ej: /prompt explicar_tema tema="MCP"
  /provider [openai|google]         muestra o cambia el modelo (gemini = google)
  /ayuda                            esta ayuda
  /salir                            terminar
"""


async def listar_recursos():
    """Responde '¿qué recursos tiene el servidor?': tools, resources y prompts."""
    async with client.session(SERVIDOR) as s:
        tools = (await s.list_tools()).tools
        resources = (await s.list_resources()).resources
        templates = (await s.list_resource_templates()).resourceTemplates
        prompts = (await s.list_prompts()).prompts
    print("\n🔧 TOOLS:     ", [t.name for t in tools])
    print("📄 RESOURCES: ", [str(r.uri) for r in resources])
    print("📄 TEMPLATES: ", [t.uriTemplate for t in templates])
    print("💬 PROMPTS:")
    for p in prompts:
        args = [a.name + ("*" if a.required else "") for a in (p.arguments or [])]
        print(f"   - {p.name}" + (f"  (args: {', '.join(args)})" if args else ""))
    print("   (* = obligatorio)  Uso: /prompt nombre clave=valor\n")


async def nueva_skill(partes: list[str]):
    """/nueva-skill <nombre> [archivo]: crea la skill en el servidor (local o remoto) con la tool crear_skill."""
    if not partes:
        print("Uso: /nueva-skill <nombre> [archivo.md]\n")
        return
    nombre = partes[0].strip('"\'')
    if len(partes) > 1:
        archivo = Path(partes[1].strip('"\'')).expanduser()
        if not archivo.exists():
            print(f"⚠️ No encuentro el archivo {archivo}\n")
            return
        contenido = archivo.read_text(encoding="utf-8")
    else:
        print("  Escribe la skill (pasos en Markdown). Termina con una línea que diga FIN:")
        lineas = []
        while (linea := await asyncio.to_thread(input, "  │ ")).strip() != "FIN":
            lineas.append(linea)
        contenido = "\n".join(lineas)
    r = await llamar_tool("crear_skill", {"nombre": nombre, "contenido": contenido})
    if r.startswith("Ya existe"):
        si = (await asyncio.to_thread(input, f"  La skill '{nombre}' ya existe. ¿Reemplazarla? (s/n) ")).strip().lower()
        if si != "s":
            print("  No se cambió nada.\n")
            return
        r = await llamar_tool("crear_skill", {"nombre": nombre, "contenido": contenido, "sobrescribir": True})
    print(f"✔ {r}\n" if "skills://" in r else f"⚠️ {r}\n")


def revisar_proveedor(provider: str) -> str | None:
    """Devuelve un mensaje de error si al proveedor le falta la clave o el paquete."""
    if provider not in MODELS:
        return f"Proveedor desconocido '{provider}'. Usa: {', '.join(MODELS)} (o gemini)."
    if importlib.util.find_spec(PAQUETES[provider]) is None:
        paquete = PAQUETES[provider].replace("_", "-")
        return f"Falta instalar el paquete de {provider}: python -m pip install {paquete}"
    if not os.getenv(API_KEYS[provider]):
        return f"Falta {API_KEYS[provider]} en el archivo .env (o en la variable de entorno)."
    return None


def _causa(e: BaseException) -> str:
    """Saca el error real de dentro de los ExceptionGroup que lanza la conexión MCP."""
    while getattr(e, "exceptions", None):
        e = e.exceptions[0]
    respuesta = getattr(e, "response", None)
    codigo = f" (HTTP {respuesta.status_code})" if respuesta is not None else ""
    return f"{type(e).__name__}: {e}{codigo}"


async def ask(agent, text):
    recalled = long_mem.search(text)
    if recalled:
        text += f"\n\n[Recuerdos relevantes: {recalled}]"
    result = await agent.ainvoke({"messages": [{"role": "user", "content": text}]},
                                 config={"configurable": {"thread_id": "default"}})
    msgs = result["messages"]
    last_human = max(i for i, m in enumerate(msgs) if m.type == "human")
    for m in msgs[last_human:]:  # muestra qué decidió hacer el agente
        for call in getattr(m, "tool_calls", []) or []:
            print(f"  🔧 {call['name']}({call['args']})")
    print("\nMizushima:", to_text(msgs[-1].content), "\n")


async def main():
    print("\n  ━━━ AI-Chatbot-Mizushima ━━━")
    print(f"  Servidor MCP: {MCP_URL or 'local (stdio)'}")
    try:
        mcp_tools = await client.get_tools()
    except BaseException as e:
        detalle = _causa(e)
        if "421" in detalle or "Invalid Host" in detalle:
            print("\n⚠️ El servidor rechazó el dominio (421). Inicia ngrok con --host-header=rewrite.")
        else:
            print(f"\n⚠️ No me pude conectar al servidor MCP en {MCP_URL or 'local'}. "
                  f"¿Está encendido y la URL es correcta?\n   {detalle[:300]}")
            if MCP_URL and "onrender.com" in MCP_URL:
                print("   En Render gratis el servidor se duerme tras 15 min sin uso: espera un minuto y reintenta.")
        return
    all_tools = TOOLS + mcp_tools + [leer_recurso_mcp]
    print(f"  Tools: {len(all_tools)}  ({len(mcp_tools)} del servidor MCP)")

    def build(provider):
        return create_agent(model=init_chat_model(MODELS[provider]), tools=all_tools,
                            system_prompt=SYSTEM_MCP, checkpointer=checkpointer)

    provider = ALIAS.get(ARGS.provider.lower(), ARGS.provider.lower())
    agent = None
    if error := revisar_proveedor(provider):
        print(f"  ⚠️ {error}\n  Puedes cambiar con /provider")
    else:
        agent = build(provider)
    print(f"  Modelo: {provider} ({MODELS.get(provider, '?').split(':', 1)[-1]})")
    print("  Escribe /ayuda para ver los comandos.\n")

    while True:
        try:
            text = (await asyncio.to_thread(input, "Tú: ")).strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text in ("/salir", "/exit"):
            break
        try:
            if not text:
                continue
            elif text == "/ayuda":
                print(AYUDA)
            elif text == "/recursos":
                await listar_recursos()
            elif text == "/skills":
                print("\n" + await llamar_tool("listar_skills", {}) + "\n")
            elif text.startswith("/skill "):
                print("\n" + await leer(f"skills://{text.split(maxsplit=1)[1].strip()}") + "\n")
            elif text.startswith("/nueva-skill"):
                await nueva_skill(shlex.split(text, posix=False)[1:])
            elif text.startswith("/borrar-skill "):
                nombre = text.split(maxsplit=1)[1].strip()
                if (await asyncio.to_thread(input, f"  ¿Borrar la skill '{nombre}'? (s/n) ")).strip().lower() == "s":
                    print(await llamar_tool("borrar_skill", {"nombre": nombre}) + "\n")
            elif text.split()[0] == "/provider":
                partes = text.split()
                if len(partes) == 1:
                    print(f"Usando {provider} ({MODELS[provider]}). Disponibles: {', '.join(MODELS)}\n")
                    continue
                nuevo = ALIAS.get(partes[1].lower(), partes[1].lower())
                if error := revisar_proveedor(nuevo):
                    print(f"⚠️ {error}\n")
                    continue
                agent, provider = build(nuevo), nuevo
                print(f"✔ Ahora usando {provider} ({MODELS[provider]}). La conversación continúa.\n")
            elif text.startswith("/prompt "):  # PROMPT del servidor MCP, con argumentos opcionales
                partes = shlex.split(text)[1:]  # /prompt explicar_tema tema="MCP" nivel=básico
                args = dict(p.split("=", 1) for p in partes[1:] if "=" in p)
                msgs = await client.get_prompt(SERVIDOR, partes[0], arguments=args or None)
                if agent is None:
                    print("⚠️ Primero configura un modelo con /provider\n")
                    continue
                await ask(agent, "\n".join(to_text(m.content) for m in msgs))
            elif text.startswith("/"):
                print("Comando desconocido. Escribe /ayuda\n")
            elif agent is None:
                print("⚠️ No hay un modelo listo. Revisa la clave en .env o cambia con /provider\n")
            else:
                await ask(agent, text)
        except Exception as e:
            print(f"⚠️ {type(e).__name__}: {str(e)[:400]}\n")
    print("¡Hasta luego!")


if __name__ == "__main__":
    asyncio.run(main())
