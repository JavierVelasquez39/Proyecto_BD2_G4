-- ============================================================================
-- conteos.sql
-- Cantidad de filas de las 11 tablas del esquema olimpiadas, en orden fijo
-- (el mismo orden de inserción por llaves foráneas).
--
-- La salida no incluye fechas ni tiempos, para poder comparar con diff la
-- foto tomada al momento del respaldo contra la de la base restaurada.
-- El orden se fija con la columna "orden" y ORDER BY, no se deja al plan.
--
-- Uso:
--   psql -X -At -d olimpiadas -f conteos.sql
-- Salida (una línea por tabla; "|" es el separador por defecto de psql -A):
--   pais|204
--   poblacion_pais|13026
--   ...
-- ============================================================================
SELECT tabla, filas
FROM (
              SELECT  1 AS orden, 'pais' AS tabla, count(*) AS filas FROM olimpiadas.pais
    UNION ALL SELECT  2, 'poblacion_pais',       count(*) FROM olimpiadas.poblacion_pais
    UNION ALL SELECT  3, 'noc',                  count(*) FROM olimpiadas.noc
    UNION ALL SELECT  4, 'sede',                 count(*) FROM olimpiadas.sede
    UNION ALL SELECT  5, 'edicion_olimpica',     count(*) FROM olimpiadas.edicion_olimpica
    UNION ALL SELECT  6, 'deporte',              count(*) FROM olimpiadas.deporte
    UNION ALL SELECT  7, 'deporte_equivalencia', count(*) FROM olimpiadas.deporte_equivalencia
    UNION ALL SELECT  8, 'evento',               count(*) FROM olimpiadas.evento
    UNION ALL SELECT  9, 'atleta',               count(*) FROM olimpiadas.atleta
    UNION ALL SELECT 10, 'participacion',        count(*) FROM olimpiadas.participacion
    UNION ALL SELECT 11, 'resultado',            count(*) FROM olimpiadas.resultado
) c
ORDER BY orden;
