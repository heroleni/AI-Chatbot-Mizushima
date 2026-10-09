# Referencia del servidor MCP

## Tools (14)

### Consumen APIs de internet

| Tool | Argumentos | Servicio | Devuelve |
|---|---|---|---|
| `clima` | `ciudad: str`, `dias: int = 3` (1–7) | **Open-Meteo**: geocodificación y pronóstico | Clima actual (temperatura, sensación, humedad, viento) y pronóstico diario con probabilidad de lluvia |
| `convertir_moneda` | `monto: float`, `de: str = "USD"`, `a: str = "COP"` | **ExchangeRate-API** (`open.er-api.com`) | Monto convertido, tasa y fecha de actualización |
| `buscar_wikipedia` | `tema: str`, `idioma: str = "es"` | **Wikipedia REST**: búsqueda y resumen | Título, descripción, resumen y enlace |

Las tres son servicios distintos, gratuitos y sin clave. Si un servicio está saturado (HTTP 429 o 5xx), la tool reintenta una vez. Si aun así no responde, devuelve un mensaje claro con el código del error ("No pude consultar… (HTTP 429)") y el servidor sigue funcionando.

`clima` tiene además un **respaldo**: si Open-Meteo falla (pasa a veces en Render, porque muchos servicios comparten sus IP y Open-Meteo las limita), consulta **wttr.in**, que tampoco pide clave. Los resultados del clima se guardan 10 minutos para no repetir consultas.

### Notas

| Tool | Argumentos | Qué hace |
|---|---|---|
| `guardar_nota` | `titulo`, `texto` | Guarda o sobrescribe una nota |
| `buscar_notas` | `consulta` | Busca en títulos y textos |
| `listar_notas` | — | Títulos de todas las notas |
| `borrar_nota` | `titulo` | Borra una nota |

### Tareas

| Tool | Argumentos | Qué hace |
|---|---|---|
| `agregar_tarea` | `texto`, `prioridad = "media"` (alta, media o baja) | Crea una tarea |
| `listar_tareas` | `solo_pendientes = True` | Lista tareas |
| `completar_tarea` | `id` | Marca una tarea como hecha |

### Skills

| Tool | Argumentos | Qué hace |
|---|---|---|
| `listar_skills` | — | Nombre y título de cada skill |
| `crear_skill` | `nombre`, `contenido`, `sobrescribir = False` | Crea `skills/<nombre>.md`. El nombre se normaliza: "Revisión de Código" → `revision_de_codigo`. Máximo 20 000 caracteres |
| `borrar_skill` | `nombre` | Borra una skill creada por usuarios |

Las skills base (`redaccion`, `organizacion_de_tareas`, `investigacion_web`, `consultas_externas`) no se pueden borrar ni reemplazar desde un cliente. Así se protegen, aunque el servidor no tenga autenticación.

### Utilidades

| Tool | Argumentos | Qué hace |
|---|---|---|
| `hora_actual` | `zona = "America/Bogota"` | Fecha y hora en una zona IANA |

## Recursos (6 fijos y 2 plantillas)

| URI | Contenido |
|---|---|
| `info://servidor` | Versión, APIs externas que usa y cómo agregar skills |
| `notas://lista` | Títulos de las notas |
| `notas://todas` | Todas las notas con su texto |
| `notas://{titulo}` | Una nota. Los espacios van como `%20` |
| `tareas://pendientes` | Tareas sin completar |
| `tareas://todas` | Todas las tareas |
| `skills://indice` | Nombres de las skills |
| `skills://{nombre}` | Texto de una skill |

## Prompts (9)

| Prompt | Argumentos | APIs | Qué pide al modelo |
|---|---|---|---|
| `reporte_clima` | `ciudad` | Open-Meteo | Reporte del clima con 3 recomendaciones |
| `presupuesto_viaje` | `destino`, `monto`, `moneda_origen = "COP"`, `moneda_destino = "USD"` | ExchangeRate-API + Open-Meteo | Presupuesto convertido, clima de 5 días, qué empacar y gasto diario sugerido |
| `investigar_tema` | `tema` | Wikipedia | Resumen en 5 puntos guardado como nota |
| `resumir_notas` | — | — | Resumen de las notas en 3 líneas |
| `plan_del_dia` | — | — | Plan por prioridades con horarios |
| `revisar_tareas` | — | — | Estado de las tareas y qué hacer primero |
| `notas_a_tareas` | `titulo` | — | Convierte una nota en tareas |
| `explicar_tema` | `tema`, `nivel = "básico"` | — | Explicación con ejemplo |
| `redactar_con_estilo` | `texto` | — | Reescribe con la skill de redacción |

Los prompts que usan APIs empiezan su descripción con `[API …]`.

## Skills del servidor

| Skill | Para qué |
|---|---|
| `consultas_externas` | Cómo usar clima, monedas y Wikipedia: unidades, fechas, fuentes y errores |
| `investigacion_web` | Cómo investigar y citar fuentes |
| `organizacion_de_tareas` | Cómo escribir y priorizar tareas |
| `redaccion` | Cómo redactar textos claros |

## Rutas HTTP

| Ruta | Método | Uso |
|---|---|---|
| `/mcp` | POST | Endpoint MCP (Streamable HTTP, respuestas JSON, sin sesión) |
| `/` | GET | Información del servidor en JSON: tools, prompts, recursos y endpoint |
| `/salud` | GET | `{"estado": "ok"}`, para el health check de Render |
