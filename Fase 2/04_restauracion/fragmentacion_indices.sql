-- ============================================================================
-- fragmentacion_indices.sql
-- Nivel de fragmentación de los índices B-tree del esquema olimpiadas,
-- medido con pgstatindex:
--   tree_level          altura del árbol (0 = solo la raíz)
--   index_size          tamaño total del índice en bytes
--   avg_leaf_density    porcentaje promedio de llenado de las hojas
--   leaf_fragmentation  porcentaje de hojas cuyo orden físico no sigue el
--                       orden lógico
--
-- En un índice vacío avg_leaf_density y leaf_fragmentation salen como NaN
-- (no hay hojas que medir); no es un error.
--
-- Requisitos: CREATE EXTENSION pgstattuple; y ejecutar con un rol
-- superusuario (o miembro de pg_stat_scan_tables).
--
-- Una sola consulta, pensada para exportar a CSV:
--   psql -X -d olimpiadas --csv -f fragmentacion_indices.sql > salida.csv
-- ============================================================================
SELECT t.relname              AS tabla,
       c.relname              AS indice,
       s.tree_level,
       s.index_size,
       s.avg_leaf_density,
       s.leaf_fragmentation
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_am am       ON am.oid = c.relam AND am.amname = 'btree'
JOIN pg_index i     ON i.indexrelid = c.oid
JOIN pg_class t     ON t.oid = i.indrelid
CROSS JOIN LATERAL pgstatindex(c.oid::regclass) s
WHERE n.nspname = 'olimpiadas'
  AND c.relkind = 'i'
ORDER BY t.relname, c.relname;
