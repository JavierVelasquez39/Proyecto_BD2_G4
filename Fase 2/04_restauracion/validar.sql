-- ============================================================================
-- validar.sql
-- Validación de la base olimpiadas después de cada carga y de cada
-- restauración: fecha del servidor, conteos de las 11 tablas, SELECT * de
-- cada tabla y consultas de muestra con datos conocidos.
--
-- Uso:
--   psql -X -d olimpiadas -f validar.sql                  (limite 10, captura)
--   psql -X -d olimpiadas -v limite=ALL -f validar.sql    (todas las filas, log)
--
-- La variable "limite" se usa en LIMIT :limite, así que acepta un número o
-- la palabra ALL. Si no se define, vale 10.
-- ============================================================================
\set ON_ERROR_STOP on

\if :{?limite}
\else
  \set limite 10
\endif

\echo '=================================================================='
\echo ' VALIDACION DE LA BASE olimpiadas'
\echo '=================================================================='
SELECT now()                         AS fecha_hora_servidor,
       current_setting('TimeZone')   AS zona_horaria,
       current_database()            AS base,
       current_setting('server_version') AS version;

\echo ''
\echo '--- 1. Conteo de filas por tabla -----------------------------------'
-- \ir resuelve la ruta relativa al directorio de este archivo, no al
-- directorio desde el que se ejecuta psql.
\ir conteos.sql

\echo ''
\echo '--- 2. SELECT * de cada tabla, LIMIT' :limite
\echo '>>> pais'
SELECT * FROM olimpiadas.pais                 ORDER BY pais_id          LIMIT :limite;
\echo '>>> poblacion_pais'
SELECT * FROM olimpiadas.poblacion_pais       ORDER BY poblacion_id     LIMIT :limite;
\echo '>>> noc'
SELECT * FROM olimpiadas.noc                  ORDER BY codigo_noc       LIMIT :limite;
\echo '>>> sede'
SELECT * FROM olimpiadas.sede                 ORDER BY sede_id          LIMIT :limite;
\echo '>>> edicion_olimpica'
SELECT * FROM olimpiadas.edicion_olimpica     ORDER BY edicion_id       LIMIT :limite;
\echo '>>> deporte'
SELECT * FROM olimpiadas.deporte              ORDER BY deporte_id       LIMIT :limite;
\echo '>>> deporte_equivalencia'
SELECT * FROM olimpiadas.deporte_equivalencia ORDER BY equivalencia_id  LIMIT :limite;
\echo '>>> evento'
SELECT * FROM olimpiadas.evento               ORDER BY evento_id        LIMIT :limite;
\echo '>>> atleta'
SELECT * FROM olimpiadas.atleta               ORDER BY atleta_id        LIMIT :limite;
\echo '>>> participacion'
SELECT * FROM olimpiadas.participacion        ORDER BY participacion_id LIMIT :limite;
\echo '>>> resultado'
SELECT * FROM olimpiadas.resultado            ORDER BY resultado_id     LIMIT :limite;

\echo ''
\echo '--- 3. Consultas de muestra ---------------------------------------'

\echo '>>> 3.1 Usain Bolt (atleta_id 104492): participaciones cargadas'
-- Carga por deportista: se esperan 1, 4 y 7 filas después de cada ronda.
-- El relevo 4x100 de 2008 aparece sin lugar ni medalla (medalla retirada
-- en 2017); no es un error de carga.
SELECT e.anio,
       ev.nombre   AS evento,
       p.codigo_noc,
       r.lugar,
       r.medalla
FROM olimpiadas.participacion p
JOIN olimpiadas.edicion_olimpica e USING (edicion_id)
JOIN olimpiadas.evento ev          USING (evento_id)
LEFT JOIN olimpiadas.resultado r   USING (participacion_id)
WHERE p.atleta_id = 104492
ORDER BY e.anio, ev.nombre;

\echo '>>> 3.2 100 m femenino (evento_id 1025): podio por edicion'
-- El podio se arma con la columna medalla y no con lugar, por dos razones:
--  * En la fuente 1, "lugar" es la posición en la última ronda que corrió
--    cada atleta (eliminatoria, semifinal o final), así que varias atletas
--    de una misma edición pueden tener lugar 1, 2 o 3 sin haber ganado
--    medalla.
--  * En 2024 (fuente 3) "lugar" es NULL en todas las filas porque esa fuente
--    solo trae la medalla. Se muestra la columna igual para dejarlo visible.
-- Las medallas reasignadas conservan la medalla final, aunque el lugar no
-- coincida (por ejemplo lugar 1 con medalla Plata).
SELECT e.anio,
       r.medalla,
       a.nombre_usado AS atleta,
       p.codigo_noc,
       r.lugar,
       r.empatado
FROM olimpiadas.participacion p
JOIN olimpiadas.edicion_olimpica e USING (edicion_id)
JOIN olimpiadas.atleta a           USING (atleta_id)
JOIN olimpiadas.resultado r        USING (participacion_id)
WHERE p.evento_id = 1025
  AND r.medalla IS NOT NULL
ORDER BY e.anio,
         CASE r.medalla WHEN 'Oro' THEN 1 WHEN 'Plata' THEN 2 WHEN 'Bronce' THEN 3 END,
         a.nombre_usado;

\echo '>>> 3.3 Medallero por NOC (top 10 de lo cargado)'
-- Cuenta filas de resultado con medalla, es decir, medallas por atleta: un
-- oro en un relevo de 4 atletas suma 4. Sirve como muestra de integridad de
-- los joins, no como medallero oficial.
SELECT coalesce(p.codigo_noc, '(sin NOC)')             AS codigo_noc,
       count(*) FILTER (WHERE r.medalla = 'Oro')       AS oro,
       count(*) FILTER (WHERE r.medalla = 'Plata')     AS plata,
       count(*) FILTER (WHERE r.medalla = 'Bronce')    AS bronce,
       count(*)                                        AS total
FROM olimpiadas.resultado r
JOIN olimpiadas.participacion p USING (participacion_id)
WHERE r.medalla IS NOT NULL
GROUP BY 1
ORDER BY oro DESC, plata DESC, bronce DESC, codigo_noc
LIMIT 10;

\echo ''
\echo '=================================================================='
\echo ' FIN DE LA VALIDACION'
\echo '=================================================================='
SELECT now() AS fin;
