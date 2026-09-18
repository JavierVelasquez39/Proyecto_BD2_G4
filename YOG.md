# Documentación de Cambios: Soporte para Juegos Olímpicos de la Juventud (YOG)
 
## Contexto de la Pregunta
 
¿También hay que contar o no los Juegos Olímpicos de la Juventud?
 
## 1. ¿Qué se hizo?
 
Para integrar plenamente las ediciones juveniles sin alterar la integridad histórica de los Juegos Olímpicos adultos, se realizaron los siguientes ajustes en el pipeline y la base de datos:
 
- **Estructura de Base de Datos (`sql/ddl.sql`)**:
  - Se modificó la restricción `CHECK` de la columna `tipo` en la tabla `edicion_olimpica` para permitir los valores `'Verano'`, `'Invierno'`, `'Verano-YOG'` e `'Invierno-YOG'`.
- **Catálogo de Referencia (`etl/reference_editions.csv`)**:
  - Se registraron las 6 ediciones históricas de los YOG (Singapur 2010, Innsbruck 2012, Nanjing 2014, Lillehammer 2016, Buenos Aires 2018 y Lausanne 2020) con sus respectivas ciudades y países anfitriones.
- **Pipeline de Carga (`etl/etl.py`)**:
  - Se eliminó el filtro que descartaba las filas que contenían `(YOG)` en el evento.
  - Se ajustó la función `build_participacion_resultado` para clasificar automáticamente las participaciones juveniles bajo `'Verano-YOG'` e `'Invierno-YOG'`, logrando la ingesta e indexación de 5,842 filas de resultados adicionales.
- **Procedimientos Almacenados (`sql/procedures.sql`)**:
  - Se agregó el parámetro opcional `p_incluir_yog BOOLEAN DEFAULT FALSE` a las funciones y procedimientos `fn_pais_info`, `pr_pais_info`, `fn_atleta_info` y `pr_atleta_info`.
## 2. Justificación de las Decisiones de Diseño
 
### A. Soporte Híbrido mediante Parámetro Opcional (`p_incluir_yog`)
 
- **Motivo**: Los comités olímpicos y las métricas oficiales tratan los medalleros adultos y juveniles de forma independiente. Mezclar las medallas de YOG con los JJOO absolutos por defecto distorsionaría los reportes de países y atletas.
- **Solución**: Por defecto (`p_incluir_yog := FALSE`), las consultas devuelven estrictamente las estadísticas absolutas/adultas. Si el usuario o evaluador requiere auditar las competencias juveniles, basta con enviar `p_incluir_yog := TRUE`.
### B. Extensión del Enum/Check en `EDICION_OLIMPICA`
 
- **Motivo**: Crear una tabla separada para ediciones juveniles habría duplicado tablas de la base de datos y complicado las consultas globales.
- **Solución**: Mantener la entidad `edicion_olimpica` como catálogo único de ediciones, diferenciando la naturaleza del evento a través de la columna `tipo` (`Verano-YOG` / `Invierno-YOG`), preservando así la normalización del modelo ER.