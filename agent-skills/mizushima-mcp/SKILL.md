---
name: mizushima-mcp
description: Usa el servidor Mizushima MCP para consultar clima (Open-Meteo), convertir monedas (ExchangeRate-API), buscar en Wikipedia, y gestionar notas, tareas y skills. Úsala cuando el usuario pida el clima de una ciudad, convertir dinero entre monedas, información enciclopédica de un tema, planear su día o guardar notas y tareas en Mizushima.
---

# Mizushima MCP

Servidor MCP público y sin autenticación. Combina tres APIs de internet con un espacio de notas, tareas y guías (skills) compartido entre todos los clientes.

## Conexión

- **Endpoint:** `https://mizushima-mcp.onrender.com/mcp` (reemplázalo por la URL del despliegue que te dieron)
- **Transporte:** Streamable HTTP. Responde JSON y no guarda sesión.
- **Autenticación:** ninguna.
- **Primera llamada lenta:** en el plan gratis de Render el servidor se duerme tras 15 minutos sin uso. Si la primera conexión falla por tiempo, espera unos 50 segundos y reintenta una vez.

Configuración típica de un cliente MCP:

```json
{ "mcpServers": { "mizushima": { "type": "http", "url": "https://mizushima-mcp.onrender.com/mcp" } } }
```

Si el cliente solo soporta stdio: `npx -y mcp-remote https://mizushima-mcp.onrender.com/mcp`.

## Elegir la herramienta

| El usuario quiere… | Usa | Notas |
|---|---|---|
| Clima actual o pronóstico | `clima(ciudad, dias=3)` | `dias` de 1 a 7. Nombre de ciudad simple: "Medellín", "Madrid" |
| Convertir dinero | `convertir_moneda(monto, de, a)` | Códigos ISO 4217: USD, COP, EUR, MXN… Tasa diaria |
| Saber qué es algo | `buscar_wikipedia(tema, idioma="es")` | Devuelve resumen y enlace |
| Hora en una zona | `hora_actual(zona)` | Zona IANA: America/Bogota |
| Guardar o consultar notas | `guardar_nota`, `buscar_notas`, `listar_notas`, `borrar_nota` | |
| Gestionar tareas | `agregar_tarea(texto, prioridad)`, `listar_tareas`, `completar_tarea(id)` | prioridad: alta, media o baja |
| Ver o crear guías | `listar_skills`, `crear_skill(nombre, contenido)`, `borrar_skill` | Las skills base no se pueden borrar ni reemplazar |

## Recursos que puedes leer

- `info://servidor`: qué APIs usa el servidor y cómo agregar skills
- `skills://indice` y `skills://{nombre}`: guías de buenas prácticas. **Léelas antes de actuar:**
  - `consultas_externas` antes de usar clima, monedas o Wikipedia
  - `investigacion_web` antes de investigar un tema
  - `organizacion_de_tareas` antes de crear o planear tareas
  - `redaccion` antes de escribir o reescribir textos
- `notas://todas`, `notas://lista`, `notas://{titulo}` (espacios como `%20`)
- `tareas://pendientes`, `tareas://todas`

## Prompts listos

| Prompt | APIs | Para qué |
|---|---|---|
| `reporte_clima(ciudad)` | Open-Meteo | Reporte del clima con recomendaciones |
| `presupuesto_viaje(destino, monto, moneda_origen, moneda_destino)` | ExchangeRate-API + Open-Meteo | Presupuesto convertido y clima del destino |
| `investigar_tema(tema)` | Wikipedia | Resumen en 5 puntos guardado como nota |
| `plan_del_dia`, `revisar_tareas`, `resumir_notas`, `notas_a_tareas(titulo)` | — | Trabajo con notas y tareas |
| `explicar_tema(tema, nivel)`, `redactar_con_estilo(texto)` | — | Explicar y redactar |

## Flujos recomendados

**Viaje:** `convertir_moneda` del presupuesto, luego `clima` del destino con `dias=5`. Al final resume el monto convertido, la fecha de la tasa, qué empacar y las fuentes.

**Investigación:** lee `skills://investigacion_web`, usa `buscar_wikipedia`, resume con enlace y, si el usuario quiere conservarlo, guárdalo con `guardar_nota` y el título `Investigación: <tema>`.

**Crear una skill:** escríbela como pasos numerados en Markdown, empezando con `# Skill: <título>`. Usa `crear_skill` con un nombre corto en minúsculas, por ejemplo `revision_de_codigo`. Usa `sobrescribir=True` solo si el usuario lo pide.

## Reglas

1. **Cita la fuente** de los datos de internet: Open-Meteo, ExchangeRate-API o Wikipedia, con enlace cuando exista.
2. **No inventes datos.** Si una tool devuelve "No pude consultar…" o "No encontré…", dilo y sugiere cómo corregir la consulta.
3. **Ambigüedades:** si el usuario dice "pesos" sin decir de qué país, pregunta. Si dice "dólares", asume USD y aclara.
4. **Espacio compartido:** las notas, tareas y skills las ven todos los clientes. No guardes datos personales sensibles.
5. **Borrado:** borra notas, tareas o skills solo si el usuario lo pidió explícitamente.

## Ejemplos

- "¿Cómo está el clima en Cartagena esta semana?" → `clima(ciudad="Cartagena", dias=7)`
- "¿Cuánto son 250 dólares en pesos colombianos?" → `convertir_moneda(monto=250, de="USD", a="COP")`
- "¿Qué es el Model Context Protocol?" → `buscar_wikipedia(tema="Model Context Protocol")`. Si no hay resultado en español, reintenta con `idioma="en"`.
- "Prepárame el viaje a Madrid con 3 millones de pesos" → prompt `presupuesto_viaje(destino="Madrid", monto="3000000", moneda_origen="COP", moneda_destino="EUR")`
