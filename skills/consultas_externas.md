# Skill: consultas a internet (clima, monedas, Wikipedia)

Cuando uses clima, convertir_moneda o buscar_wikipedia:
1. Pide solo lo necesario: una ciudad concreta, códigos de moneda ISO (USD, COP, EUR) o un tema específico.
2. Si el usuario dice "pesos", "dólares" o "euros", traduce a COP, USD o EUR; si es ambiguo (pesos de qué país), pregunta.
3. Muestra las cifras con sus unidades: °C, %, km/h, y el código de moneda junto al monto.
4. En conversiones, indica siempre la fecha de la tasa: cambia todos los días.
5. Cita la fuente al final: Open-Meteo, ExchangeRate-API o Wikipedia (con el enlace).
6. Si la tool devuelve un error, explícalo en una línea y sugiere cómo corregir la consulta; no inventes datos.
7. Separa los datos de la API de tus recomendaciones u opiniones.
