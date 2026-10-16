SELECT now() AS medido_en;
SELECT c.relname AS tabla, s.table_len, s.tuple_count, s.tuple_percent,
       s.dead_tuple_count, s.dead_tuple_percent, s.free_space, s.free_percent
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
CROSS JOIN LATERAL pgstattuple(c.oid::regclass) s
WHERE n.nspname = 'olimpiadas' AND c.relkind = 'r'
ORDER BY 1;