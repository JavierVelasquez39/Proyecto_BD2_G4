# Síntesis de Fuentes de Datos Olímpicos

> Referencia compacta de las 4 fuentes mencionadas en el enunciado, hecha
> como primer mapeo antes de decidir la estrategia de carga. Para
> licencias, atribución y estado final de carga de cada una, ver
> `FUENTES.md`; para las decisiones de diseño tomadas, ver `DECISIONES.md`.

| # | Fuente | Origen | Cobertura | Contenido | Notas |
|---|---|---|---|---|---|
| 1 | GitHub, KeithGalli/Olympics-Dataset | Scraping de olympedia.org | Verano e invierno, 1896-2022 | Archivos separados: bio de atletas + resultados por evento | Incluye carpeta procesada con lat/long, códigos de región y población histórica por país |
| 2 | Kaggle, 120 years of Olympic history | sports-reference.com | Moderna, 1896-2016 | 1 archivo central, ~271,116 registros, 15 columnas | Detalla físico del atleta (edad, altura, peso) y evento (deporte, ciudad, medalla) |
| 3 | Kaggle, Summer Olympics Medals 1896-2024 | Fusión histórico + resultados de París 2024 | Solo Verano, 1896-2024 | Atleta, delegación, deporte, medallas | Fuente más actualizada, útil para evolución/distribución de medallas |
| 4 | DataCamp, r-olympics | sports-reference.com (misma base que #2) | Moderna hasta Río 2016 | Mismos registros que la fuente 2 | Integrado en plataforma de aprendizaje, pensado para ejercicios de EDA/programación |

## Nota clave para la unificación

Las fuentes **2 y 4 comparten el mismo origen de datos** (sports-reference.com, hasta 2016), no son independientes. En la práctica hay **3 pools de datos distintos**:
- Olympedia (fuente 1): el más completo en variables auxiliares (geo, población).
- sports-reference (fuentes 2 y 4): mismo contenido, dos empaques distintos.
- Fusión histórica más París 2024 (fuente 3): la única que llega hasta 2024.

Al diseñar la carga (ETL), se evita duplicar atletas/resultados al combinar 2 y 4: se usan como una sola fuente con una copia de respaldo, priorizando la fuente 3 para 2024.

## Cómo quedó resuelto finalmente

Esta síntesis fue el primer mapeo, antes de decidir qué hacer con cada fuente. La estrategia final adoptada (documentada con el detalle completo en `DECISIONES.md` y `FUENTES.md`) fue:
- **Fuente 1:** columna vertebral de la carga, 1896-2022 completo.
- **Fuente 2:** no se carga como participaciones; se usa para derivar `SEDE`/`EDICION_OLIMPICA` reales y como cross-check de fuente 1.
- **Fuente 3:** se carga únicamente el subconjunto `Year==2024` (París), la única edición que fuente 1 no cubre, por ser la de licencia más restrictiva (CC BY-NC-SA 4.0).
- **Fuente 4:** descartada de la carga. Al ser redundante de la fuente 2 (mismo origen, sin acceso verificado a su licencia real por bloqueo HTTP 403 de DataCamp sin sesión), no aporta nada que la fuente 2 no cubra ya.
