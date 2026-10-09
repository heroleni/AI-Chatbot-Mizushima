# Documentación del agente (Mizushima)

Mizushima es un agente por terminal hecho con **LangChain** y **LangGraph**. Usa **OpenAI** o **Gemini** como modelo y se conecta al servidor MCP como cliente, ya sea en local, por ngrok o en Render. Así usa sus tools, recursos, prompts y skills.

## Cómo funciona

```
 Tú (terminal) ──► agente_mcp.py ──► create_agent(modelo, tools, prompt, memoria)
                       │                     │
                       │ comandos /…         ├─ tools propias: buscar_web, recordar
                       │ (sin modelo)        ├─ tools del servidor MCP (14)
                       ▼                     └─ leer_recurso_mcp (lee skills://, notas://…)
              servidor MCP (stdio o HTTP) ◄──────────┘
```

1. Al arrancar, se conecta al servidor (`client.get_tools()`) y carga sus 14 tools como tools de LangChain.
2. Arma el agente con `create_agent(...)`: el modelo elegido, las tools (las suyas, las del servidor y `leer_recurso_mcp`), el prompt `SYSTEM_MCP` y la memoria corta (`InMemorySaver`).
3. Cada mensaje tuyo pasa por la memoria larga (`long_mem.search`). Si encuentra recuerdos relacionados, los agrega al mensaje.
4. El modelo decide qué tools usar. La terminal muestra cada una con 🔧 y luego la respuesta.
5. Los comandos que empiezan con `/` no pasan por el modelo: hablan directamente con el servidor.

## Archivos

### `agente_langchain.py`: la base

| Elemento | Qué es |
|---|---|
| `MODELS` | Modelo de cada proveedor: `openai:<OPENAI_MODEL>` y `google_genai:<GOOGLE_MODEL>`, configurables en `.env` |
| `API_KEYS`, `PAQUETES`, `ALIAS` | Variable de clave y paquete de cada proveedor. `gemini` equivale a `google` |
| `checkpointer` | Memoria corta: el historial de la conversación mientras el programa corre |
| `LongMemory` / `long_mem` | Memoria larga en `memoria_larga.json`, con búsqueda por palabras en común |
| `buscar_web` | Tool propia: búsqueda en DuckDuckGo (`ddgs`) |
| `recordar` | Tool propia: guarda un dato del usuario en la memoria larga |
| `SYSTEM` | Prompt de sistema: se llama Mizushima, es conciso y responde en el idioma del usuario |
| `to_text` | Convierte el contenido de un mensaje (texto o bloques) en texto |

También funciona solo, sin MCP: `python agente_langchain.py`.

### `agente_mcp.py`: Mizushima con el servidor MCP

| Elemento | Qué es |
|---|---|
| `SYSTEM_MCP` | `SYSTEM` más instrucciones para usar skills, `crear_skill` y las tools de APIs |
| Argumentos | `--url` (servidor remoto) y `--provider` (`openai` o `gemini`). También se leen de `MCP_URL` y `PROVIDER` |
| `conexion` | Sin `--url`, lanza `mcp_server.py` por **stdio**. Con `--url`, usa **Streamable HTTP**, con 90 s de espera para Render y `/mcp` agregado si falta |
| `leer_recurso_mcp` | Tool para que el modelo lea recursos (`skills://…`, `notas://…`) |
| `llamar_tool`, `leer` | Llaman al servidor directamente, sin modelo. Las usan los comandos `/` |
| `nueva_skill` | `/nueva-skill`: lee la skill de la terminal (hasta `FIN`) o de un archivo y la crea con `crear_skill`. Pregunta antes de reemplazar |
| `revisar_proveedor` | Antes de cambiar de modelo, revisa que el paquete esté instalado y que exista la clave |
| `_causa` | Saca el error real de los `ExceptionGroup` para mostrar mensajes claros (421, sin conexión…) |
| `ask` | Envía el mensaje al agente y muestra las tools usadas y la respuesta |
| `main` | Conecta, arma el agente y atiende los comandos |

## Instalación y uso

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
cp .env.example .env                                  # pon OPENAI_API_KEY y/o GOOGLE_API_KEY
```

```bash
python agente_mcp.py                                              # servidor local (stdio)
python agente_mcp.py --url https://mizushima-mcp.onrender.com     # servidor en Render
python agente_mcp.py --url https://xxxx.ngrok-free.app            # servidor por ngrok
python agente_mcp.py --url https://mizushima-mcp.onrender.com --provider gemini
```

## Comandos

| Comando | Qué hace |
|---|---|
| *(texto normal)* | Habla con Mizushima |
| `/recursos` | Lista las tools, recursos, plantillas y prompts del servidor |
| `/skills` | Lista las skills del servidor |
| `/skill <nombre>` | Muestra una skill |
| `/nueva-skill <nombre>` | Crea una skill escribiéndola en la terminal. Termina con una línea `FIN` |
| `/nueva-skill <nombre> <archivo.md>` | Crea una skill desde un archivo |
| `/borrar-skill <nombre>` | Borra una skill creada por usuarios (pide confirmación) |
| `/prompt <nombre> clave=valor …` | Usa un prompt del servidor. Ej: `/prompt presupuesto_viaje destino=Madrid monto=3000000 moneda_destino=EUR` |
| `/provider` | Muestra el modelo actual |
| `/provider openai` · `/provider gemini` | Cambia de modelo **sin perder la conversación** |
| `/ayuda`, `/salir` | Ayuda y salir |

## Ejemplo de sesión

```
  ━━━ AI-Chatbot-Mizushima ━━━
  Servidor MCP: https://mizushima-mcp.onrender.com/mcp
  Tools: 17  (14 del servidor MCP)
  Modelo: openai (…)

Tú: ¿cuánto son 100 dólares en pesos colombianos?
  🔧 leer_recurso_mcp({'uri': 'skills://consultas_externas'})
  🔧 convertir_moneda({'monto': 100, 'de': 'USD', 'a': 'COP'})

Mizushima: 100 USD son 323.641,77 COP (tasa del 9 de octubre de 2026). Fuente: ExchangeRate-API.

Tú: /provider gemini
✔ Ahora usando google (…). La conversación continúa.
```

## Configuración (`.env`)

| Variable | Uso |
|---|---|
| `OPENAI_API_KEY` / `GOOGLE_API_KEY` | Claves de los modelos |
| `PROVIDER` | Con cuál arranca: `openai` o `google` |
| `OPENAI_MODEL` / `GOOGLE_MODEL` | Nombre del modelo. Cámbialo si el agente dice que el modelo no existe |
| `MCP_URL` | Servidor por defecto, igual que `--url` |

## Errores comunes

| Mensaje | Solución |
|---|---|
| *Falta OPENAI_API_KEY / GOOGLE_API_KEY* | Pon la clave en `.env` y reinicia el agente |
| *Falta instalar el paquete de google* | `python -m pip install langchain-google-genai` |
| *No me pude conectar al servidor MCP* | Revisa la URL. En Render gratis, espera un minuto y reintenta |
| *El servidor rechazó el dominio (421)* | Inicia ngrok con `--host-header=rewrite` |
| *El modelo no existe* | Cambia `OPENAI_MODEL` o `GOOGLE_MODEL` en `.env` |
| `DLL load failed … Control de aplicaciones` (Windows) | Usa WSL (ver [DESPLIEGUE.md](DESPLIEGUE.md#windows-11-y-el-control-de-aplicaciones)) |
