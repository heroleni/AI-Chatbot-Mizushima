# Documentación de las skills

El proyecto tiene dos tipos de skill:

| Tipo | Dónde está | Quién la usa | Para qué |
|---|---|---|---|
| **Skills del servidor** | `skills/*.md` | Cualquier cliente del servidor MCP, que las lee como recurso `skills://<nombre>` | Guías de buenas prácticas que el modelo lee antes de actuar |
| **Skill para agentes** | `agent-skills/mizushima-mcp/SKILL.md` | Agentes con soporte de skills (Claude Code, etc.) | Le enseña a un agente cuándo y cómo usar este servidor MCP |

---

## 1. Skills del servidor

Son archivos Markdown con pasos numerados. El servidor publica cada archivo como recurso: `skills/redaccion.md` queda disponible en `skills://redaccion`. La lista completa está en `skills://indice` y en la tool `listar_skills`.

### Skills incluidas

| Skill | Recurso | Cuándo se usa | Prompts que la piden |
|---|---|---|---|
| Consultas a internet | `skills://consultas_externas` | Antes de usar `clima`, `convertir_moneda` o `buscar_wikipedia`: unidades, fecha de la tasa, ambigüedades ("pesos" de qué país), citar fuentes y no inventar datos | `reporte_clima`, `presupuesto_viaje` |
| Investigar en la web | `skills://investigacion_web` | Antes de investigar un tema: empezar con Wikipedia, contrastar, citar URLs, separar hechos de opiniones | `investigar_tema` |
| Organizar tareas | `skills://organizacion_de_tareas` | Antes de crear o planear tareas: verbo inicial, máximo 2 horas, prioridades y máximo 3 tareas de prioridad alta al día | `plan_del_dia` |
| Redacción clara | `skills://redaccion` | Antes de escribir o reescribir: conclusión primero, frases cortas, voz activa | `redactar_con_estilo` |

Estas cuatro son **skills base**: ningún cliente las puede borrar ni reemplazar, aunque el servidor no tenga autenticación.

### Cómo las usa el modelo

1. El prompt de sistema del agente y las instrucciones del servidor dicen: *"Antes de redactar, planear o consultar internet, lee la skill correspondiente."*
2. Los prompts del servidor lo piden explícitamente. Por ejemplo, `reporte_clima` empieza con *"Lee skills://consultas_externas"*.
3. El modelo lee la skill con `leer_recurso_mcp` (Mizushima) o con `resources/read` (otros clientes) y sigue sus pasos.

### Crear una skill del servidor

| Forma | Cómo | Dónde queda |
|---|---|---|
| Comando del agente | `/nueva-skill revision_de_codigo` y luego escribir los pasos y `FIN` | En el servidor al que esté conectado el agente (local o Render) |
| Desde un archivo | `/nueva-skill revision_de_codigo mi_skill.md` | Igual |
| Pidiéndoselo al agente | *"crea una skill para revisar código"*. Mizushima la redacta y usa `crear_skill` | Igual |
| Cualquier cliente MCP | Tool `crear_skill(nombre, contenido)` | Igual |
| **Código** | Crear `skills/<nombre>.md` y subirlo a GitHub | Permanente: Render la publica en el siguiente despliegue |

Reglas:
- **Nombre:** se normaliza a minúsculas sin tildes, con `_` o `-`. Por ejemplo, "Revisión de Código" queda como `revision_de_codigo`.
- **Tamaño:** máximo 20 000 caracteres.
- **Encabezado:** si no empieza con `#`, se agrega `# Skill: <nombre>`.
- **Duración en Render:** las skills creadas con la tool viven mientras el servidor no se reinicie, porque el disco de Render es temporal. Para que sea permanente, agrégala al repositorio.

Plantilla:

```markdown
# Skill: <título>

Cuando <situación>:
1. <primer paso concreto>.
2. <segundo paso>.
3. <cómo verificar o qué entregar>.
```

---

## 2. Skill para agentes: `mizushima-mcp`

Está en `agent-skills/mizushima-mcp/SKILL.md` y sigue el formato estándar de *Agent Skills*: una carpeta con un `SKILL.md` que empieza con un encabezado YAML.

```yaml
---
name: mizushima-mcp
description: Usa el servidor Mizushima MCP para consultar clima (Open-Meteo), convertir monedas (ExchangeRate-API), buscar en Wikipedia, y gestionar notas, tareas y skills. Úsala cuando…
---
```

El agente lee la `description` para decidir **cuándo** usar la skill. El cuerpo le dice **cómo** hacerlo.

### Qué contiene

| Sección | Contenido |
|---|---|
| Conexión | Endpoint de Render, transporte, autenticación (ninguna), arranque en frío, configuración JSON y `mcp-remote` para clientes que solo usan stdio |
| Elegir la herramienta | Tabla "el usuario quiere… → usa…" con las 14 tools y sus argumentos |
| Recursos | Qué recursos hay y qué skill del servidor leer antes de cada tipo de tarea |
| Prompts listos | Los 9 prompts y cuáles usan APIs |
| Flujos recomendados | Viaje (moneda + clima), investigación (Wikipedia + nota), crear una skill |
| Reglas | Citar fuentes, no inventar datos, ambigüedades, espacio compartido, borrar solo si lo piden |
| Ejemplos | Pedidos reales y la llamada exacta que corresponde |

### Instalarla en un agente

- **Claude Code:** copia la carpeta a `.claude/skills/mizushima-mcp/` en tu proyecto o a `~/.claude/skills/mizushima-mcp/`.
- **Otros agentes con soporte de skills:** copia la carpeta `mizushima-mcp` a su carpeta de skills.
- **Agentes sin soporte de skills:** pega el contenido de `SKILL.md`, sin el encabezado YAML, en el prompt de sistema.

Además, el agente debe tener configurado el servidor MCP. Ver [CLIENTES.md](CLIENTES.md).
