-- ============================================================================
-- fragmentacion_tablas.sql
-- Nivel de fragmentación de las tablas del esquema olimpiadas, medido con
-- pgstattuple (lectura completa de cada tabla, nivel de tupla):
--   tuple_percent       porcentaje del archivo ocupado por filas vivas
--   dead_tuple_percent  porcentaje ocupado por filas muertas (UPDATE/DELETE
--                       sin VACUUM)
--   free_percent        porcentaje de espacio libre dentro de las páginas
--
-- Requisitos: CREATE EXTENSION pgstattuple; y ejecutar con un rol
-- superusuario (o miembro de pg_stat_scan_tables).
--
-- Una sola consulta, pensada para exportar a CSV:
--   psql -X -d olimpiadas --csv -f fragmentacion_tablas.sql > salida.csv
-- No incluye la hora de medición para que la salida del paso 09 (antes de
-- eliminar la base) y la del paso 16 (después de restaurar) se puedan
-- comparar con diff; se espera que sean idénticas porque la copia física
-- conserva las páginas tal como estaban.
-- ============================================================================
SELECT c.relname              AS tabla,
       s.table_len,
       s.tuple_count,
       s.tuple_percent,
       s.dead_tuple_count,
       s.dead_tuple_percent,
       s.free_space,
       s.free_percent
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
CROSS JOIN LATERAL pgstattuple(c.oid::regclass) s
WHERE n.nspname = 'olimpiadas'
  AND c.relkind = 'r'
ORDER BY c.relname;
