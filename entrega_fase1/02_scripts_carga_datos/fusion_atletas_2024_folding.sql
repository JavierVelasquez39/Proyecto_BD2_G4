-- ============================================================================
-- Fusión puntual: 30 atletas de la extensión fuente 3/2024 que quedaron
-- cargados como fila NUEVA en ATLETA en vez de fusionarse con su registro ya
-- existente de fuente 1, por un gap del folding de acentos usado en la carga
-- original (unicodedata.normalize("NFKD", ...) no cubre letras Unicode sin
-- descomposición de compatibilidad como la ł polaca, la ı turca o la æ
-- nórdica -- ver INFORME_PROYECTO.md, seccion 5, hallazgo 2026-09-14 y su actualización).
--
-- Los 30 pares de abajo se determinaron re-corriendo el MISMO algoritmo de
-- emparejamiento que ya usa build_atleta_extension_f3() en etl/etl.py (vivo +
-- nacionalidad consistente, sin aflojar esa salvaguarda) pero con el folding
-- corregido (text_unidecode en vez de NFKD), aplicado contra el estado ya
-- cargado de la tabla ATLETA. Los 30 pasaron la salvaguarda de nacionalidad
-- sin excepción (motivo='nacionalidad_consistente' en todos los casos) -- no
-- se forzó ningún caso ambiguo ni de nacionalidad distinta.
--
-- Verificado antes de aplicar (ver bitácora):
--   - 0 conflictos con el UNIQUE(atleta_id, edicion_id, evento_id) de
--     PARTICIPACION (todas las participaciones del lado "fuente 3" son de la
--     edición 2024, que fuente 1 no cubre).
--   - Reduce ATLETA de 153,473 a 153,443 filas (-30); PARTICIPACION no
--     cambia de tamaño (314,108), solo se reasigna atleta_id en 30+ filas.
--
-- Uso: correr completo contra la BD real. Termina en COMMIT solo si las
-- validaciones de conteo dentro de la transacción se cumplen; si algo no
-- cuadra, aborta con ROLLBACK automático (ver bloque DO $$ ... $$ al final).
-- ============================================================================

BEGIN;

SET search_path TO olimpiadas;

CREATE TEMP TABLE _fusion_pares (id_f3 INTEGER, id_f1 INTEGER) ON COMMIT DROP;
INSERT INTO _fusion_pares (id_f3, id_f1) VALUES
    (146622, 142327),
    (146806, 143313),
    (146853, 116464),
    (146857, 143285),
    (146875, 133208),
    (147123, 119112),
    (147124, 142329),
    (147126, 132592),
    (147129, 142359),
    (147130, 120230),
    (147147, 120119),
    (147164, 113799),
    (147165, 142310),
    (147280, 142079),
    (147519, 143297),
    (147543, 130756),
    (147764, 138723),
    (147816, 142370),
    (147818, 128824),
    (148497, 142398),
    (148499, 132652),
    (148500, 132656),
    (150139, 132605),
    (150140, 142373),
    (150146, 132630),
    (150919, 142376),
    (150923, 142323),
    (151666, 142382),
    (151943, 132999),
    (152024, 130099);

-- Reasigna las participaciones del atleta_id "de más" (fuente 3/2024) al
-- atleta_id ya existente de fuente 1.
UPDATE olimpiadas.participacion p
SET atleta_id = fp.id_f1
FROM _fusion_pares fp
WHERE p.atleta_id = fp.id_f3;

-- Elimina la fila duplicada de ATLETA (ya sin participaciones apuntándole).
DELETE FROM olimpiadas.atleta a
USING _fusion_pares fp
WHERE a.atleta_id = fp.id_f3;

-- Validación dentro de la misma transacción: aborta si algo no cuadra.
DO $$
DECLARE
    v_huerfanos INTEGER;
    v_filas_afectadas INTEGER;
BEGIN
    SELECT count(*) INTO v_huerfanos
    FROM olimpiadas.participacion p
    JOIN _fusion_pares fp ON fp.id_f3 = p.atleta_id;
    IF v_huerfanos > 0 THEN
        RAISE EXCEPTION 'Quedaron % participaciones con atleta_id viejo -- abortando', v_huerfanos;
    END IF;

    SELECT count(*) INTO v_filas_afectadas FROM olimpiadas.atleta a
    JOIN _fusion_pares fp ON fp.id_f3 = a.atleta_id;
    IF v_filas_afectadas > 0 THEN
        RAISE EXCEPTION '% filas de atleta_id viejo no se eliminaron -- abortando', v_filas_afectadas;
    END IF;
END $$;

-- Reporte final antes del COMMIT (revisar antes de confirmar si se corre a mano).
SELECT
    (SELECT count(*) FROM olimpiadas.atleta) AS atleta_total_esperado_153443,
    (SELECT count(*) FROM olimpiadas.participacion) AS participacion_total_esperado_314108,
    (SELECT count(*) FROM olimpiadas.resultado) AS resultado_total_esperado_314623;

COMMIT;
-- ============================================================================
-- Fin
-- ============================================================================
