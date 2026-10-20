-- ============================================================================
-- B2: deshace fusiones registradas en atleta_fusion_log (todas, un tipo, o un id)
-- Uso: psql -v ON_ERROR_STOP=1 -v tipo=SUBCONJUNTO -f B2_deshacer_fusion.sql
--      (tipo = ORDEN_INVERTIDO | PARTICULAS | SUBCONJUNTO | MEDIA_MANUAL | TODOS)
-- Restaura la fila del duplicado desde datos_duplicado, devuelve sus participaciones
-- (participacion_ids) y borra el registro del log. Una transaccion; idempotente
-- (lo ya deshecho ya no esta en el log).
-- ============================================================================
SET search_path TO olimpiadas;
BEGIN;
SELECT set_config('b2.tipo', :'tipo', true);
CREATE TEMP TABLE b2_deshacer ON COMMIT DROP AS
SELECT * FROM atleta_fusion_log
WHERE current_setting('b2.tipo') = 'TODOS' OR tipo = current_setting('b2.tipo');

INSERT INTO atleta
SELECT (jsonb_populate_record(NULL::atleta, d.datos_duplicado)).* FROM b2_deshacer d;

UPDATE participacion p SET atleta_id = d.id_duplicado
FROM b2_deshacer d WHERE p.participacion_id = ANY (d.participacion_ids);

DELETE FROM atleta_fusion_log l USING b2_deshacer d WHERE l.id_duplicado = d.id_duplicado;
DO $$ BEGIN RAISE NOTICE 'B2 deshacer: % fusiones revertidas', (SELECT count(*) FROM b2_deshacer); END $$;
COMMIT;
