# Despliegue

El servidor se puede desplegar de tres formas. Ninguna pide autenticación.

| Forma | URL | Disponible | Para qué |
|---|---|---|---|
| **Local (stdio)** | — | Mientras lo uses | Desarrollar y probar en tu PC |
| **Local + ngrok** | `https://xxxx.ngrok-free.app/mcp` | Mientras tu PC y ngrok estén encendidos | Mostrarlo desde tu PC a otros equipos |
| **Remoto en Render** | `https://mizushima-mcp.onrender.com/mcp` | Siempre (se duerme si no se usa) | **La entrega**: cualquiera lo usa cuando quiera |

---

## 1. Local (stdio)

```bash
python -m pip install -r requirements.txt
python agente_mcp.py
```

El agente lanza `mcp_server.py` como subproceso. En VS Code: abre `.vscode/mcp.json` y pulsa **Start** sobre `mizushima-local`.

## 2. Local por HTTP + ngrok

### Servidor HTTP

```bash
MCP_TRANSPORT=streamable-http python mcp_server.py
# Windows PowerShell:
$env:MCP_TRANSPORT="streamable-http"; python mcp_server.py
```

Queda en `http://127.0.0.1:8000/mcp`. Al abrir `http://127.0.0.1:8000` en el navegador ves la información del servidor.

### Instalar ngrok (una sola vez)

En Ubuntu / WSL:

```bash
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com bookworm main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install -y ngrok
ngrok config add-authtoken TU_AUTHTOKEN     # está en dashboard.ngrok.com
```

En Windows: `winget install ngrok.ngrok` y luego el mismo `ngrok config add-authtoken`.

### Exponer el servidor

Con el servidor HTTP corriendo, en otra terminal:

```bash
ngrok http 8000 --host-header=rewrite
```

Copia la URL `https://xxxx.ngrok-free.app` de la línea *Forwarding*. El endpoint es esa URL más `/mcp`. En VS Code, la tarea **Despliegue local: servidor + ngrok** hace los dos pasos.

> **¿Por qué `--host-header=rewrite`?** El SDK de MCP rechaza con `421 Invalid Host header` las peticiones cuyo Host no es local, como protección contra DNS rebinding. Si prefieres no usar esa opción, pon tu dominio de ngrok en `ALLOWED_HOSTS`.

**Limitaciones:** el servidor solo funciona mientras tu PC, el servidor y ngrok estén encendidos. Con el plan gratis, la URL cambia cada vez que reinicias ngrok, a menos que actives el dominio fijo gratis en *Domains* y lo uses con `--url=tu-dominio.ngrok-free.app`.

## 3. Remoto en Render (recomendado para la entrega)

Render ejecuta el servidor en la nube, sin tu PC. El archivo `render.yaml` ya trae toda la configuración.

### Paso 1: subir el código a GitHub

**Opción A, desde el navegador (sin git):**

1. Entra a [github.com/new](https://github.com/new), ponle de nombre `AI-Chatbot-Mizushima`, márcalo **Public** y crea el repositorio.
2. Haz clic en **uploading an existing file**.
3. Arrastra **todo el contenido** de la carpeta del proyecto, incluidas `skills/`, `agent-skills/`, `docs/`, `tests/` y `.vscode/`. **No subas `.env`**: tiene tus claves.
4. Haz clic en **Commit changes**.

**Opción B, con git** (desde Ubuntu / WSL):

```bash
cd ~/mizushima
git init && git add . && git commit -m "Mizushima MCP"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/AI-Chatbot-Mizushima.git
git push -u origin main
```

El archivo `.gitignore` ya evita subir `.env`, `.venv` y los datos locales. Para el `push`, GitHub pide un token personal como contraseña. También puedes usar `gh auth login`.

### Paso 2: crear el servicio en Render

1. Entra a [dashboard.render.com](https://dashboard.render.com) e inicia sesión **con tu cuenta de GitHub**.
2. Haz clic en **New → Blueprint**.
3. Conecta tu repositorio `AI-Chatbot-Mizushima`. Render detecta `render.yaml` y muestra el servicio `mizushima-mcp` (plan *Free*).
4. Haz clic en **Deploy Blueprint**. La primera vez tarda unos 2 o 3 minutos.
5. Abre el servicio y copia su URL, algo como `https://mizushima-mcp.onrender.com`. Si el nombre ya estaba ocupado, Render le agrega un sufijo.

Si no te aparece *Blueprint*, usa **New → Web Service** con estos valores:

| Campo | Valor |
|---|---|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements-server.txt` |
| Start Command | `python mcp_server.py` |
| Instance Type | Free |
| Environment Variables | `MCP_TRANSPORT=streamable-http`, `HOST=0.0.0.0`, `PYTHON_VERSION=3.12.7` |
| Health Check Path | `/salud` |

### Paso 3: verificar

1. Abre la URL en el navegador. Debe mostrar un JSON con `"autenticacion": "ninguna"` y la lista de tools.
2. Ejecuta el verificador:
   ```bash
   python verificar_despliegue.py https://mizushima-mcp.onrender.com
   ```
   Todos los puntos deben salir con ✔. El verificador llama de verdad a las 3 APIs de internet.

### Cosas que debes saber de Render gratis

- **Se duerme:** tras 15 minutos sin uso, el servidor se apaga. La siguiente petición lo despierta en unos 50 segundos. El agente espera hasta 90 segundos. Antes de una demo, abre la URL en el navegador para despertarlo.
- **Disco temporal:** las notas, tareas y skills creadas mientras corre se borran cuando Render reinicia o vuelve a desplegar. Las skills que están en `skills/` del repositorio se mantienen. Para que una skill sea permanente, agrégala al repositorio: con `autoDeploy`, Render la publica sola.
- **Actualizar:** cada cambio que subas a GitHub se despliega automáticamente.

## 4. Red local (sin ngrok)

```bash
MCP_TRANSPORT=streamable-http HOST=0.0.0.0 python mcp_server.py
```

Los otros equipos de la misma red usan `http://IP-DE-TU-PC:8000/mcp`. Si el servidor corre dentro de WSL, los otros equipos no lo ven directamente, porque WSL tiene su propia red. En ese caso usa ngrok.

## Windows 11 y el Control de aplicaciones

Windows 11 puede bloquear piezas compiladas de algunas librerías con el error `DLL load failed … Una directiva de Control de aplicaciones bloqueó este archivo`. Las opciones son:

1. **Usar WSL (recomendado):**
   ```bash
   sudo apt update && sudo apt install -y python3-venv python3-pip
   cp -r "/mnt/d/ruta/al/proyecto" ~/mizushima && cd ~/mizushima
   rm -rf .venv && python3 -m venv .venv && source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```
2. Usar siempre `python -m pip` en vez de `pip`. Así se evita el bloqueo de `pip.exe`.
3. Desactivar el *Control inteligente de aplicaciones* en Seguridad de Windows. En muchas versiones, una vez apagado no se puede volver a encender sin reinstalar Windows.

## Variables de entorno

| Variable | Dónde | Valor por defecto | Uso |
|---|---|---|---|
| `MCP_TRANSPORT` | servidor | `stdio` | `streamable-http` para servir por HTTP |
| `HOST` | servidor | `127.0.0.1` | `0.0.0.0` en Render o en red local |
| `PORT` | servidor | `8000` | Render lo asigna solo |
| `ALLOWED_HOSTS` | servidor | — | Dominios extra permitidos (ngrok sin `--host-header=rewrite`) |
| `MCP_URL` | agente | — | Servidor remoto (igual que `--url`) |
| `OPENAI_API_KEY` / `GOOGLE_API_KEY` | agente | — | Claves de los modelos |
| `PROVIDER` | agente | `openai` | `openai` o `google` |
| `OPENAI_MODEL` / `GOOGLE_MODEL` | agente | ver `.env.example` | Nombre del modelo |
