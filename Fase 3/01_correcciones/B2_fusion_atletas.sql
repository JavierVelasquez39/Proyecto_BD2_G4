-- ============================================================================
-- B2: fusion de atletas duplicados (nombre mal parseado en la fuente 3)
--
-- Uso: psql -v ON_ERROR_STOP=1 -v fase=1 -f B2_fusion_atletas.sql   (o ejecutar_correccion.py --var fase=1)
-- Lee datos/pares_aprobados.csv (\copy, ruta relativa) y procesa solo las filas de la fase indicada,
-- todo en UNA transaccion. Cada fase se ejecuta por separado, con su propio respaldo y bitacora.
--
-- Por cada par (id_duplicado -> id_conservado): conserva el atleta_id del registro historico, mueve las
-- participaciones del duplicado al conservado, registra la fusion en atleta_fusion_log (con el nombre
-- original, la fila completa del duplicado en jsonb y los participacion_id movidos, para poder deshacer)
-- y elimina el duplicado. Las colisiones (el conservado ya tiene una participacion en el mismo evento y
-- edicion) se reportan en atleta_fusion_colision y el par se EXCLUYE sin resolverse.
-- Idempotente: un duplicado ya registrado en el log se omite. Participaciones y resultados no cambian
-- de conteo, solo de dueno; si algo no cuadra la transaccion completa se revierte.
-- ============================================================================
SET search_path TO olimpiadas;
BEGIN;

CREATE TABLE IF NOT EXISTS atleta_fusion_log (
    id_duplicado              integer PRIMARY KEY,
    id_conservado             integer NOT NULL,
    tipo                      varchar(20) NOT NULL
        CHECK (tipo IN ('ORDEN_INVERTIDO', 'PARTICULAS', 'SUBCONJUNTO', 'MEDIA_MANUAL')),
    confianza                 varchar(10) NOT NULL,
    evidencia                 text NOT NULL,
    fecha                     timestamptz NOT NULL DEFAULT now(),
    fase                      smallint NOT NULL,
    nombre_original_duplicado varchar(300) NOT NULL,
    datos_duplicado           jsonb NOT NULL,
    participacion_ids         bigint[] NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fusion_log_conservado ON atleta_fusion_log (id_conservado);

CREATE TABLE IF NOT EXISTS atleta_fusion_colision (
    id_duplicado  integer NOT NULL,
    id_conservado integer NOT NULL,
    edicion_id    integer NOT NULL,
    evento_id     integer NOT NULL,
    fase          smallint NOT NULL,
    fecha         timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id_duplicado, edicion_id, evento_id)
);

CREATE TEMP TABLE b2_stage (
    fase int, id_duplicado int, id_conservado int, tipo text, confianza text, evidencia text,
    nombre_duplicado text, nombre_conservado text
) ON COMMIT DROP;

\copy b2_stage FROM 'datos/pares_aprobados.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

SELECT set_config('b2.fase', :'fase', true);

CREATE TEMP TABLE b2_antes ON COMMIT DROP AS
SELECT (SELECT count(*) FROM atleta) AS atletas,
       (SELECT count(*) FROM participacion) AS participaciones,
       (SELECT count(*) FROM resultado) AS resultados;

DO $$
DECLARE
    v_fase int := current_setting('b2.fase')::int;
    v_total int; v_ya int; v_col int; v_ok int; v_mal int;
BEGIN
    CREATE TEMP TABLE b2_trabajo ON COMMIT DROP AS
    SELECT s.* FROM b2_stage s WHERE s.fase = v_fase;
    SELECT count(*) INTO v_total FROM b2_trabajo;
    IF v_total = 0 THEN RAISE EXCEPTION 'B2: la fase % no tiene pares en el CSV', v_fase; END IF;

    -- Ya aplicados (idempotencia)
    DELETE FROM b2_trabajo t USING atleta_fusion_log l WHERE l.id_duplicado = t.id_duplicado;
    SELECT v_total - count(*) INTO v_ya FROM b2_trabajo;

    -- Validaciones: el duplicado existe con ese nombre, el conservado existe, el sexo no se contradice
    SELECT count(*) INTO v_mal FROM b2_trabajo t
    WHERE NOT EXISTS (SELECT 1 FROM atleta a WHERE a.atleta_id = t.id_duplicado AND a.nombre_usado = t.nombre_duplicado)
       OR NOT EXISTS (SELECT 1 FROM atleta a WHERE a.atleta_id = t.id_conservado);
    IF v_mal > 0 THEN RAISE EXCEPTION 'B2: % pares con duplicado inexistente, nombre distinto o conservado inexistente', v_mal; END IF;
    SELECT count(*) INTO v_mal FROM b2_trabajo t
    JOIN atleta d ON d.atleta_id = t.id_duplicado JOIN atleta c ON c.atleta_id = t.id_conservado
    WHERE d.sexo IS NOT NULL AND c.sexo IS NOT NULL AND d.sexo <> c.sexo;
    IF v_mal > 0 THEN RAISE EXCEPTION 'B2: % pares con sexo contradictorio', v_mal; END IF;

    -- Colisiones: mismo evento y edicion en ambos registros. Se reportan y el par se excluye.
    INSERT INTO atleta_fusion_colision (id_duplicado, id_conservado, edicion_id, evento_id, fase)
    SELECT t.id_duplicado, t.id_conservado, p1.edicion_id, p1.evento_id, v_fase
    FROM b2_trabajo t
    JOIN participacion p1 ON p1.atleta_id = t.id_duplicado
    JOIN participacion p2 ON p2.atleta_id = t.id_conservado AND p2.edicion_id = p1.edicion_id AND p2.evento_id = p1.evento_id
    ON CONFLICT DO NOTHING;
    DELETE FROM b2_trabajo t WHERE EXISTS (SELECT 1 FROM atleta_fusion_colision c WHERE c.id_duplicado = t.id_duplicado);
    SELECT count(DISTINCT id_duplicado) INTO v_col FROM atleta_fusion_colision WHERE fase = v_fase;

    -- Registro en el log (antes de mover nada)
    INSERT INTO atleta_fusion_log (id_duplicado, id_conservado, tipo, confianza, evidencia, fase,
                                   nombre_original_duplicado, datos_duplicado, participacion_ids)
    SELECT t.id_duplicado, t.id_conservado, t.tipo, t.confianza, t.evidencia, v_fase,
           a.nombre_usado, to_jsonb(a),
           COALESCE((SELECT array_agg(p.participacion_id ORDER BY p.participacion_id)
                     FROM participacion p WHERE p.atleta_id = t.id_duplicado), '{}')
    FROM b2_trabajo t JOIN atleta a ON a.atleta_id = t.id_duplicado;

    UPDATE participacion p SET atleta_id = t.id_conservado
    FROM b2_trabajo t WHERE p.atleta_id = t.id_duplicado;

    DELETE FROM atleta a USING b2_trabajo t WHERE a.atleta_id = t.id_duplicado;
    SELECT count(*) INTO v_ok FROM b2_trabajo;
    RAISE NOTICE 'B2 fase %: pares en CSV %, ya aplicados %, excluidos por colision %, fusionados %', v_fase, v_total, v_ya, v_col, v_ok;
END $$;

-- Verificacion final: conteos y huerfanos
DO $$
DECLARE a record;
BEGIN
    SELECT * INTO a FROM b2_antes;
    IF (SELECT count(*) FROM participacion) <> a.participaciones THEN RAISE EXCEPTION 'B2: cambio el conteo de participacion'; END IF;
    IF (SELECT count(*) FROM resultado) <> a.resultados THEN RAISE EXCEPTION 'B2: cambio el conteo de resultado'; END IF;
    IF EXISTS (SELECT 1 FROM participacion p WHERE NOT EXISTS (SELECT 1 FROM atleta x WHERE x.atleta_id = p.atleta_id)) THEN
        RAISE EXCEPTION 'B2: participaciones huerfanas'; END IF;
    IF a.atletas - (SELECT count(*) FROM atleta) <> (SELECT count(*) FROM b2_trabajo) THEN
        RAISE EXCEPTION 'B2: la baja de atletas no coincide con las fusiones'; END IF;
    RAISE NOTICE 'B2 verificacion OK: atletas % -> %, participaciones %, resultados %',
        a.atletas, (SELECT count(*) FROM atleta), a.participaciones, a.resultados;
END $$;

COMMIT;
