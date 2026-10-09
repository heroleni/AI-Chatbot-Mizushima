# Entrega

## Checklist antes de enviar

- [ ] El código está en GitHub, sin el archivo `.env` (ver [DESPLIEGUE.md](DESPLIEGUE.md#paso-1-subir-el-código-a-github))
- [ ] El servicio de Render está desplegado y en estado *Live*
- [ ] Al abrir la URL de Render en el navegador aparece el JSON con `"autenticacion": "ninguna"`
- [ ] `python verificar_despliegue.py <URL de Render>` muestra todo con ✔, incluidas las 3 APIs
- [ ] Cambiaste `https://mizushima-mcp.onrender.com` por tu URL real en `agent-skills/mizushima-mcp/SKILL.md` y en el correo
- [ ] Están listos los adjuntos: la carpeta `agent-skills/mizushima-mcp/` (la skill) y el `.zip` del proyecto, o el enlace a GitHub

## Correo

**Para:** angelo.gaviria@riwi.io
**Asunto:** Entrega MCP desplegado: Mizushima MCP (tools, recursos, prompts y skill)

> Hola, Angelo:
>
> Envío la entrega del servidor MCP **Mizushima**.
>
> **Link del MCP (sin autenticación):** https://mizushima-mcp.onrender.com/mcp
> Al abrir https://mizushima-mcp.onrender.com en el navegador se ve la información del servidor. Está en el plan gratis de Render: si lleva un rato sin uso, la primera petición tarda unos 50 segundos.
>
> **Repositorio (código y documentación):** https://github.com/heroleni/AI-Chatbot-Mizushima
>
> **Qué incluye:**
> - 14 herramientas. Tres consumen APIs de servicios en la nube distintos: `clima` (Open-Meteo), `convertir_moneda` (ExchangeRate-API) y `buscar_wikipedia` (Wikipedia).
> - 6 recursos y 2 plantillas de recursos (notas, tareas, skills e información del servidor).
> - 9 prompts. Tres usan las APIs: `reporte_clima`, `presupuesto_viaje` e `investigar_tema`.
> - Skill para agentes: `agent-skills/mizushima-mcp/SKILL.md` (adjunta).
> - Agente por terminal (LangChain, OpenAI o Gemini) que se conecta al MCP desde cualquier computador.
>
> **Cómo probarlo:**
> - MCP Inspector: `npx @modelcontextprotocol/inspector`, transporte *Streamable HTTP* y la URL de arriba.
> - VS Code: `{"servers": {"mizushima": {"type": "http", "url": "https://mizushima-mcp.onrender.com/mcp"}}}`
>
> Adjunto la skill y el proyecto comprimido.
>
> Saludos,
> TU NOMBRE

## Qué adjuntar

1. `mizushima-mcp-skill.zip`: la carpeta `agent-skills/mizushima-mcp/`.
2. `AI-Chatbot-Mizushima.zip`: el proyecto completo, sin `.env` ni `.venv`.

Para crearlos desde Ubuntu o WSL:

```bash
cd ~/mizushima
zip -r mizushima-mcp-skill.zip agent-skills/mizushima-mcp
cd .. && zip -r AI-Chatbot-Mizushima.zip mizushima -x "*/.venv/*" "*/.env" "*/__pycache__/*" "*/notas.json" "*/tareas.json" "*/memoria_larga.json"
```
