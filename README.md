# AI-Chatbot-Mizushima

Servidor **MCP** (Model Context Protocol) con tools, recursos, prompts y skills, desplegado en internet **sin autenticación** para que cualquier cliente MCP lo use. Incluye a **Mizushima**, un agente por terminal (OpenAI o Gemini) que se conecta a ese servidor desde cualquier computador.

```
            ┌──────────────────────── Mizushima MCP (mcp_server.py) ────────────────────────┐
            │  14 tools · 6 recursos + 2 plantillas · 9 prompts · skills en skills/*.md      │
            │                                                                               │
            │  clima ──────────────► Open-Meteo         (api.open-meteo.com)                │
            │  convertir_moneda ───► ExchangeRate-API   (open.er-api.com)                   │
            │  buscar_wikipedia ───► Wikipedia REST     (es.wikipedia.org)                  │
            └──────────────▲──────────────────────▲───────────────────────▲─────────────────┘
                           │ Streamable HTTP /mcp │ (sin autenticación)    │
             Render (24/7) │       ngrok (local)  │         stdio (local)  │
                           │                      │                       │
                 agente_mcp.py (Mizushima)   VS Code / Claude / Inspector   curl
```

## Criterios de aceptación

| Criterio | Cómo se cumple |
|---|---|
| Al menos 3 recursos | 6 recursos (`info://servidor`, `notas://lista`, `notas://todas`, `tareas://pendientes`, `tareas://todas`, `skills://indice`) y 2 plantillas (`notas://{titulo}`, `skills://{nombre}`) |
| Al menos 5 herramientas | 14 herramientas |
| 2 consumen APIs de internet de servicios distintos | 3: `clima` (Open-Meteo), `convertir_moneda` (ExchangeRate-API) y `buscar_wikipedia` (Wikipedia) |
| Al menos 2 prompts para las APIs | 3: `reporte_clima`, `presupuesto_viaje` (usa 2 APIs) e `investigar_tema` |
| Desplegado para cualquier cliente | Render (siempre activo) y ngrok (local). Streamable HTTP con respuestas JSON: funciona hasta con `curl` |
| Sin autenticación | El servidor no pide token, clave ni usuario |
| Skill para agentes | [`agent-skills/mizushima-mcp/SKILL.md`](agent-skills/mizushima-mcp/SKILL.md) |
| Documentación y código | Este README, la carpeta [`docs/`](docs/) y las pruebas en [`tests/`](tests/) |

## Inicio rápido

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

| Quiero… | Comando |
|---|---|
| Correr las pruebas | `python -m pytest -v` |
| Usar el agente con el servidor local | `python agente_mcp.py` |
| Usar el agente con el servidor desplegado | `python agente_mcp.py --url https://mizushima-mcp.onrender.com` |
| Levantar el servidor HTTP local | `MCP_TRANSPORT=streamable-http python mcp_server.py` |
| Verificar un despliegue | `python verificar_despliegue.py https://mizushima-mcp.onrender.com` |

Para el agente, copia `.env.example` como `.env` y pon tu `OPENAI_API_KEY` y/o `GOOGLE_API_KEY`. **El servidor no necesita ninguna clave.**

> En Windows 11, si el Control inteligente de aplicaciones bloquea librerías (`DLL load failed… Control de aplicaciones`), usa WSL (Ubuntu). Ver [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md#windows-11-y-el-control-de-aplicaciones).

## Estructura

```
AI-Chatbot-Mizushima/
├── mcp_server.py              Servidor MCP: tools, recursos, prompts, rutas / y /salud
├── skills/                    Skills del servidor (se publican como skills://<nombre>)
├── agente_mcp.py              Mizushima: agente por terminal (cliente MCP)
├── agente_langchain.py        Base del agente: modelos, memoria, tools propias
├── agent-skills/
│   └── mizushima-mcp/SKILL.md Skill para agentes: cómo usar este MCP
├── verificar_despliegue.py    Revisa un despliegue contra los criterios
├── tests/test_servidor.py     Pruebas automáticas (APIs simuladas)
├── render.yaml                Despliegue en Render (Blueprint)
├── requirements-server.txt    Dependencias del servidor (Render)
├── requirements.txt           Todo: servidor + agente + pruebas
├── .env.example               Variables de entorno
├── .vscode/                   Tareas, depuración y mcp.json para VS Code
└── docs/
    ├── DESPLIEGUE.md          Local, ngrok, Render y WSL paso a paso
    ├── CLIENTES.md            Cómo conectarse desde cualquier cliente
    ├── REFERENCIA.md          Detalle de tools, recursos y prompts
    └── ENTREGA.md             Checklist y correo de entrega
```

## Agregar cosas

- **Skill:** desde el agente con `/nueva-skill <nombre>`, desde cualquier cliente con la tool `crear_skill`, o creando `skills/<nombre>.md` en el código. Se publica sola como `skills://<nombre>`.
- **Tool:** una función con `@mcp.tool()` en `mcp_server.py`.
- **Prompt:** una función con `@mcp.prompt()` en `mcp_server.py`.

## Documentación

- [Despliegue: local, ngrok y Render](docs/DESPLIEGUE.md)
- [Conectarse desde cualquier cliente](docs/CLIENTES.md)
- [Referencia de tools, recursos y prompts](docs/REFERENCIA.md)
- [Entrega: checklist y correo](docs/ENTREGA.md)

## APIs externas y atribución

- Clima: [Open-Meteo](https://open-meteo.com), licencia CC BY 4.0.
- Tasas de cambio: [Rates By Exchange Rate API](https://www.exchangerate-api.com).
- Enciclopedia: [Wikipedia](https://www.wikipedia.org), licencia CC BY-SA.

Ninguna requiere clave de API.
