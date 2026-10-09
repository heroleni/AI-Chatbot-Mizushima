# Documentación del código

## Arquitectura

```
                     ┌────────────────────────────────────────────────────┐
                     │  mcp_server.py  (FastMCP · Streamable HTTP / stdio) │
                     │                                                    │
  Clientes MCP ─────►│  TOOLS ──┬─ notas / tareas ──► notas.json, tareas.json
  (agente, VS Code,  │          ├─ skills ──────────► skills/*.md          │
   Inspector, curl)  │          └─ APIs ──► Open-Meteo · ExchangeRate-API · Wikipedia
                     │  RESOURCES ─► notas://, tareas://, skills://, info:// │
                     │  PROMPTS ───► plantillas (3 usan las APIs)           │
                     │  RUTAS ─────► /mcp · / · /salud                      │
                     └────────────────────────────────────────────────────┘
                                         ▲
                                         │ langchain-mcp-adapters
                     ┌───────────────────┴────────────────────────────────┐
                     │  agente_mcp.py  (Mizushima por terminal)            │
                     │  └─ agente_langchain.py (modelos, memoria, tools)   │
                     └────────────────────────────────────────────────────┘
```

- **Servidor y agente están separados.** El servidor no usa ningún modelo de IA ni necesita claves. El agente es un cliente más del servidor, igual que VS Code o MCP Inspector.
- **El servidor no guarda sesión** (`stateless_http=True`) y **responde JSON** (`json_response=True`). Cada petición es independiente: funciona detrás de Render o ngrok y con clientes simples como `curl`.
- **Sin autenticación.** Para proteger lo básico, las skills base del proyecto no se pueden borrar ni reemplazar desde un cliente.

## Archivos

| Archivo | Líneas | Qué contiene |
|---|---|---|
| `mcp_server.py` | ~530 | El servidor MCP completo: configuración, tools, recursos, prompts y rutas HTTP |
| `agente_mcp.py` | ~260 | Mizushima: interfaz de terminal, conexión al servidor y comandos `/…` |
| `agente_langchain.py` | ~120 | Base del agente: modelos, memoria corta y larga, tools propias y prompt de sistema |
| `verificar_despliegue.py` | ~90 | Revisa un servidor desplegado contra los criterios de aceptación |
| `tests/test_servidor.py` | ~240 | 16 pruebas automáticas (APIs simuladas y servidor HTTP real) |
| `skills/*.md` | — | Skills del servidor, publicadas como `skills://<nombre>` |
| `agent-skills/mizushima-mcp/SKILL.md` | — | Skill para agentes que usan este servidor |
| `render.yaml` | — | Despliegue en Render (Blueprint) |
| `requirements-server.txt` / `requirements.txt` | — | Dependencias del servidor / de todo el proyecto |

## `mcp_server.py`, sección por sección

### 1. Configuración

| Elemento | Qué hace |
|---|---|
| `HOST`, `PORT`, `ALLOWED_HOSTS` | Se leen de variables de entorno. En Render, `HOST=0.0.0.0` y Render pone el `PORT` |
| `seguridad` (`TransportSecuritySettings`) | Protección contra DNS rebinding. Activa solo en `127.0.0.1`; con ngrok se usa `--host-header=rewrite` |
| `mcp = FastMCP(...)` | Crea el servidor con nombre `mizushima`, instrucciones para los clientes, `stateless_http` y `json_response` |
| `_load` / `_save` | Leen y escriben JSON en UTF-8 |
| `_get_json(url, params)` | Única función que sale a internet (httpx, 15 s de timeout, User-Agent propio). Las pruebas la reemplazan |

### 2. Tools

| Grupo | Funciones | Detalle |
|---|---|---|
| Notas | `guardar_nota`, `buscar_notas`, `listar_notas`, `borrar_nota` | Diccionario `{titulo: texto}` en `notas.json` |
| Tareas | `agregar_tarea`, `listar_tareas`, `completar_tarea` | Lista de `{id, texto, prioridad, hecha}` en `tareas.json`. Valida la prioridad |
| Skills | `listar_skills`, `crear_skill`, `borrar_skill` | `_nombre_skill()` normaliza el nombre (quita tildes, solo `a-z0-9_-`, máximo 50). Límite de 20 000 caracteres. `SKILLS_BASE` protege las skills del proyecto |
| Utilidad | `hora_actual` | Usa `zoneinfo` con zonas IANA |
| APIs | `clima`, `convertir_moneda`, `buscar_wikipedia` | Ver abajo |

**Manejo de las APIs:**

- `_get_json_reintento()` reintenta **una vez**, tras 1,5 s, si el servicio responde 429 o 5xx o no contesta a tiempo.
- `_codigo_http(e)` convierte el error en texto legible (`HTTP 429`, `ConnectTimeout`) para el mensaje al usuario.
- Ninguna tool lanza excepciones al cliente. Ante un error devuelve un texto claro y el servidor sigue funcionando.

**`clima`:**

1. Revisa el caché (`_CACHE_CLIMA`, 10 minutos por ciudad y número de días).
2. Geocodifica la ciudad con Open-Meteo Geocoding.
3. Pide el pronóstico con Open-Meteo Forecast. `_formato_open_meteo()` arma el texto y traduce los códigos WMO al español con `CLIMA_WMO`.
4. Si Open-Meteo falla, `_clima_respaldo()` consulta **wttr.in** (formato `j1`, máximo 3 días).

**`convertir_moneda`:** consulta `open.er-api.com/v6/latest/{de}`. Una respuesta 404 significa que la moneda de origen no es válida. Revisa la de destino en `rates`. Muestra el monto, la tasa y la fecha de actualización, con la atribución que exige el servicio.

**`buscar_wikipedia`:** busca con `/w/rest.php/v1/search/page` y luego pide el resumen con `/api/rest_v1/page/summary/{key}`. Avisa si el resultado es una página de desambiguación. El idioma se valida con la expresión regular `[a-z]{2,3}`.

### 3. Recursos

Se definen con `@mcp.resource("esquema://ruta")`. Los que tienen `{variable}` son plantillas. `recurso_nota` decodifica `%20` con `unquote`. `recurso_skill` usa `Path(nombre).name` para que no se pueda salir de la carpeta `skills/`.

### 4. Prompts

Se definen con `@mcp.prompt()`. Cada uno devuelve el texto que el cliente le envía al modelo. Los que usan APIs empiezan su descripción con `[API …]`, y así los detectan las pruebas y el verificador. Cada prompt le indica al modelo qué skill leer antes de actuar.

### 5. Rutas HTTP y arranque

- `@mcp.custom_route("/")` devuelve un JSON con las tools, prompts y recursos disponibles.
- `/salud` es el health check de Render.
- `mcp.run(transport=MCP_TRANSPORT)` arranca el servidor en `stdio` (por defecto) o en `streamable-http`. En stdio no se usa `print()`, porque la salida estándar es el canal del protocolo.

## Pruebas

```bash
python -m pip install -r requirements.txt
python -m pytest -v
```

| Prueba | Qué verifica |
|---|---|
| `test_al_menos_cinco_tools_y_tres_de_internet` | Criterio: 5 o más tools, incluidas las 3 de APIs |
| `test_al_menos_tres_recursos` | Criterio: 3 o más recursos y las plantillas |
| `test_al_menos_dos_prompts_de_apis` | Criterio: 2 o más prompts de APIs |
| `test_apis_de_servicios_distintos` | Las 3 APIs son de servicios distintos |
| `test_clima`, `test_convertir_moneda`, `test_buscar_wikipedia` | Formato de cada respuesta |
| `test_clima_ciudad_inexistente`, `test_convertir_moneda_invalida` | Errores de entrada |
| `test_clima_usa_respaldo_si_open_meteo_falla` | Reintento y respaldo wttr.in ante un 429 |
| `test_clima_usa_cache` | No repite la consulta en 10 minutos |
| `test_api_caida_no_rompe_el_servidor` | Si no hay red, responde un mensaje claro |
| `test_crear_leer_y_borrar_skill`, `test_skills_base_protegidas` | Gestión de skills |
| `test_nota_con_espacios_y_tareas` | Recursos con `%20` y tareas |
| `test_servidor_http_sin_autenticacion` | Levanta el servidor HTTP real y se conecta como cliente, sin token |

Las APIs se simulan reemplazando `_get_json`, así que las pruebas no necesitan internet. La prueba real contra las APIs la hace `verificar_despliegue.py`.

## Extender

| Quiero… | Cómo |
|---|---|
| Una tool nueva | Función con `@mcp.tool()` y su docstring. El docstring es lo que ve el modelo |
| Una tool que llame a una API | Usa `await _get_json_reintento(url, params)` y captura `httpx.HTTPError` |
| Un recurso | `@mcp.resource("esquema://ruta")`, con `{variable}` si es plantilla |
| Un prompt | `@mcp.prompt()`. Si usa una API, empieza la descripción con `[API Nombre]` |
| Una skill | Archivo `skills/<nombre>.md` o la tool `crear_skill` (ver [SKILLS.md](SKILLS.md)) |
