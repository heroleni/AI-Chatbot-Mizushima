# Conectarse desde cualquier cliente

El servidor usa el transporte estándar **Streamable HTTP** y no pide autenticación. Cualquier cliente MCP se conecta con la URL del endpoint:

```
https://mizushima-mcp.onrender.com/mcp      (Render: reemplaza por tu URL)
https://xxxx.ngrok-free.app/mcp             (ngrok)
http://127.0.0.1:8000/mcp                   (local)
```

> En Render gratis, la primera petición después de 15 minutos sin uso tarda unos 50 segundos.

## 1. Mizushima (agente por terminal)

```bash
python agente_mcp.py --url https://mizushima-mcp.onrender.com
python agente_mcp.py --url https://mizushima-mcp.onrender.com --provider gemini
```

No hace falta poner `/mcp` al final: el agente lo agrega solo.

| Comando | Qué hace |
|---|---|
| `/recursos` | Lista tools, recursos y prompts |
| `/skills`, `/skill <nombre>` | Lista o muestra skills |
| `/nueva-skill <nombre>` | Crea una skill escribiéndola en la terminal. Termina con `FIN` |
| `/nueva-skill <nombre> <archivo.md>` | Crea una skill desde un archivo |
| `/borrar-skill <nombre>` | Borra una skill creada por usuarios |
| `/prompt <nombre> clave=valor` | Usa un prompt. Ej: `/prompt reporte_clima ciudad=Bogotá` |
| `/provider [openai\|gemini]` | Muestra o cambia el modelo sin perder la conversación |
| `/ayuda`, `/salir` | Ayuda y salir |

También puedes hablarle normal: *"¿cuánto son 100 dólares en pesos colombianos?"*.

## 2. MCP Inspector (navegador, sin instalar nada)

Requiere Node.js:

```bash
npx @modelcontextprotocol/inspector
```

En la página que se abre, elige **Transport Type: Streamable HTTP**, pega la URL con `/mcp` y haz clic en **Connect**. Ahí puedes probar cada tool, recurso y prompt.

## 3. VS Code (Copilot Chat en modo Agent)

El proyecto trae `.vscode/mcp.json` con dos entradas:

- `mizushima-local`: lanza el servidor en tu PC.
- `mizushima-remoto`: pide la URL de Render o ngrok, sin `/mcp`.

Pulsa **Start** sobre la que quieras y abre el chat en modo **Agent**. En otro proyecto puedes agregarlo así:

```json
{ "servers": { "mizushima": { "type": "http", "url": "https://mizushima-mcp.onrender.com/mcp" } } }
```

## 4. Claude Desktop y otros clientes que solo usan stdio

Usa el puente `mcp-remote`, que requiere Node.js. En el archivo de configuración del cliente:

```json
{
  "mcpServers": {
    "mizushima": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mizushima-mcp.onrender.com/mcp"]
    }
  }
}
```

Los clientes que aceptan servidores remotos por URL (conectores personalizados) solo necesitan `https://mizushima-mcp.onrender.com/mcp`.

## 5. curl (JSON-RPC directo)

El servidor responde JSON y no guarda sesión, así que cada petición funciona sola:

```bash
URL=https://mizushima-mcp.onrender.com/mcp

# Listar tools
curl -s $URL -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# Clima de Medellín
curl -s $URL -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"clima","arguments":{"ciudad":"Medellín","dias":2}}}'

# Convertir 100 USD a COP
curl -s $URL -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"convertir_moneda","arguments":{"monto":100,"de":"USD","a":"COP"}}}'

# Leer un recurso
curl -s $URL -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":4,"method":"resources/read","params":{"uri":"skills://consultas_externas"}}'
```

## 6. Desde Python (SDK oficial de MCP)

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client("https://mizushima-mcp.onrender.com/mcp") as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("convertir_moneda", {"monto": 50, "de": "EUR", "a": "COP"})
            print(res.content[0].text)

asyncio.run(main())
```

## 7. Agentes con skills

Copia la carpeta [`agent-skills/mizushima-mcp`](../agent-skills/mizushima-mcp/) a la carpeta de skills de tu agente, por ejemplo `.claude/skills/` en Claude Code. El agente aprende cuándo y cómo usar cada tool, recurso y prompt de este servidor.
