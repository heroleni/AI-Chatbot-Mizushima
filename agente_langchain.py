"""
Base del agente LangChain: modelos, tools, prompt, memoria corta y memoria larga.
agente_mcp.py importa de aquí: MODELS, TOOLS, SYSTEM, checkpointer, long_mem, to_text

Instalación:
    python -m pip install -r requirements.txt
    python -m pip install langchain-google-genai   # solo si usas Gemini

Variables de entorno (.env): OPENAI_API_KEY y/o GOOGLE_API_KEY, OPENAI_MODEL, GOOGLE_MODEL
Uso directo (sin MCP): PROVIDER=openai python agente_langchain.py
"""
import json, os
from datetime import datetime
from pathlib import Path

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

try:  # carga variables desde .env si existe (pip install python-dotenv)
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:
    pass

# ── Modelos por proveedor (se pueden cambiar en .env con OPENAI_MODEL / GOOGLE_MODEL) ──
MODELS = {
    "openai": "openai:" + os.getenv("OPENAI_MODEL", "gpt-6-luna"),
    "google": "google_genai:" + os.getenv("GOOGLE_MODEL", "gemini-3.8-flash"),
}
# Variable de entorno con la clave de cada proveedor y paquete que necesita
API_KEYS = {"openai": "OPENAI_API_KEY", "google": "GOOGLE_API_KEY"}
PAQUETES = {"openai": "langchain_openai", "google": "langchain_google_genai"}
ALIAS = {"gemini": "google", "gpt": "openai", "chatgpt": "openai"}

# ── Memoria corta: historial por thread_id (vive mientras corra el programa) ──
checkpointer = InMemorySaver()


# ── Memoria larga: recuerdos guardados en un JSON, con búsqueda por palabras ──
class LongMemory:
    def __init__(self, path):
        self.path = Path(path)
        self.items = json.loads(self.path.read_text("utf-8")) if self.path.exists() else []

    def add(self, texto: str):
        self.items.append({"texto": texto, "fecha": datetime.now().isoformat(timespec="seconds")})
        self.path.write_text(json.dumps(self.items, ensure_ascii=False, indent=2), "utf-8")

    def search(self, consulta: str, k: int = 3) -> str:
        """Devuelve los k recuerdos con más palabras en común con la consulta ('' si no hay)."""
        palabras = {w for w in consulta.lower().split() if len(w) > 3}
        puntuados = []
        for it in self.items:
            score = len(palabras & set(it["texto"].lower().split()))
            if score:
                puntuados.append((score, it["texto"]))
        puntuados.sort(reverse=True)
        return " | ".join(t for _, t in puntuados[:k])


long_mem = LongMemory(Path(__file__).with_name("memoria_larga.json"))


# ── Tools ─────────────────────────────────────────────────────────────
@tool
def buscar_web(consulta: str) -> str:
    """Busca información actual en la web (DuckDuckGo). Devuelve título, URL y resumen."""
    from ddgs import DDGS
    try:
        resultados = DDGS().text(consulta, max_results=5)
    except Exception as e:
        return f"Error en la búsqueda: {e}"
    if not resultados:
        return "Sin resultados."
    return "\n\n".join(f"{r['title']}\n{r['href']}\n{r['body']}" for r in resultados)


@tool
def recordar(dato: str) -> str:
    """Guarda en la memoria de largo plazo un dato importante del usuario (gustos, nombre, preferencias)."""
    long_mem.add(dato)
    return "Guardado en memoria."


TOOLS = [buscar_web, recordar]

SYSTEM = (
    "Eres Mizushima, un asistente útil y conciso. Si te preguntan quién eres, di que te llamas Mizushima. "
    "Responde en el idioma del usuario. "
    "Usa buscar_web cuando necesites información actual y cita las URLs. "
    "Usa recordar cuando el usuario te cuente algo importante sobre sí mismo."
)


# ── Utilidad: el contenido de un mensaje puede ser str o lista de bloques ──
def to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b if isinstance(b, str) else b.get("text", "") for b in content
        )
    return str(content)


# ── Modo directo (opcional): probar este agente solo, sin MCP ──────────
if __name__ == "__main__":
    provider = os.getenv("PROVIDER", "openai").lower()
    agent = create_agent(model=init_chat_model(MODELS[provider]), tools=TOOLS,
                         system_prompt=SYSTEM, checkpointer=checkpointer)
    print(f"Proveedor: {provider}  (escribe /salir para terminar)\n")
    while (text := input("Tú: ").strip()) != "/salir":
        if not text:
            continue
        recalled = long_mem.search(text)
        if recalled:
            text += f"\n\n[Recuerdos relevantes: {recalled}]"
        r = agent.invoke({"messages": [{"role": "user", "content": text}]},
                         config={"configurable": {"thread_id": "default"}})
        print("\nAgente:", to_text(r["messages"][-1].content), "\n")
