-- ============================================================================
-- B1: medallas faltantes de Paris 2024 (aprobado el 2026-10-19)
--
-- Causa: en la fuente 3 (olympics_dataset.csv) los 32 atletas que compitieron
-- en dos deportes en 2024 (89 filas con Sport compuesto, p. ej. "Cycling Road,
-- Cycling Track") traen Medal = 'No medal' en todas sus filas, aunque ganaron
-- medalla; ademas el relevo mixto de triatlon solo trae 2 filas (SUI).
-- Fuente manual declarada (no es una de las 4 del enunciado): resultados
-- oficiales de Paris 2024 segun Wikipedia, URL y fecha por fila en
-- datos/correcciones_paris2024.csv.
--
-- Uso (psql, ejecutar desde la carpeta que contiene este script):
--   psql -v ON_ERROR_STOP=1 -f B1_medallas_paris2024.sql
-- (o python ejecutar_correccion.py, que ademas hace el pg_dump previo y la bitacora)
-- El CSV se lee con \copy (lado cliente, ruta relativa); los datos NO estan incrustados aqui.
--
-- Idempotente: ACTUALIZAR solo toca filas con medalla distinta; INSERTAR usa
-- ON CONFLICT / NOT EXISTS. Una segunda ejecucion no cambia nada.
-- ============================================================================
SET search_path TO olimpiadas;
BEGIN;

CREATE TEMP TABLE b1_stage (
    atleta_id int, atleta text, evento_id int, evento text, medalla text,
    lugar int, noc text, accion text, url_verificacion text,
    fecha_consulta date, nota text
) ON COMMIT DROP;

\copy b1_stage FROM 'datos/correcciones_paris2024.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

-- Validaciones: cualquier fallo aborta toda la transaccion.
DO $$
DECLARE v_ed int; v_mal int;
BEGIN
    SELECT edicion_id INTO v_ed FROM edicion_olimpica WHERE anio = 2024 AND tipo = 'Verano';
    IF v_ed IS NULL THEN RAISE EXCEPTION 'No existe la edicion 2024 Verano'; END IF;

    SELECT count(*) INTO v_mal FROM b1_stage s
    WHERE NOT EXISTS (SELECT 1 FROM atleta a WHERE a.atleta_id = s.atleta_id)
       OR NOT EXISTS (SELECT 1 FROM evento e WHERE e.evento_id = s.evento_id AND e.nombre = s.evento)
       OR s.medalla NOT IN ('Oro','Plata','Bronce')
       OR s.accion NOT IN ('ACTUALIZAR','INSERTAR')
       OR NOT EXISTS (SELECT 1 FROM noc n WHERE n.codigo_noc = s.noc);
    IF v_mal > 0 THEN RAISE EXCEPTION 'B1: % filas del CSV no validan (atleta, evento, medalla, accion o NOC)', v_mal; END IF;

    -- Las filas ACTUALIZAR deben apuntar a una participacion existente en 2024.
    SELECT count(*) INTO v_mal FROM b1_stage s
    WHERE s.accion = 'ACTUALIZAR' AND NOT EXISTS (
        SELECT 1 FROM participacion p JOIN resultado r USING (participacion_id)
        WHERE p.atleta_id = s.atleta_id AND p.evento_id = s.evento_id AND p.edicion_id = v_ed);
    IF v_mal > 0 THEN RAISE EXCEPTION 'B1: % filas ACTUALIZAR sin participacion/resultado en 2024', v_mal; END IF;
END $$;

-- Parte 1: asignar medalla a filas ya cargadas (medalla NULL en la fuente 3)
UPDATE resultado r
SET medalla = s.medalla,
    lugar   = COALESCE(r.lugar, s.lugar)
FROM b1_stage s
JOIN participacion p ON p.atleta_id = s.atleta_id AND p.evento_id = s.evento_id
JOIN edicion_olimpica o ON o.edicion_id = p.edicion_id AND o.anio = 2024 AND o.tipo = 'Verano'
WHERE s.accion = 'ACTUALIZAR'
  AND r.participacion_id = p.participacion_id
  AND r.medalla IS DISTINCT FROM s.medalla;

-- Parte 2: participaciones y resultados que la fuente 3 no trae (relevo mixto)
INSERT INTO participacion (atleta_id, edicion_id, evento_id, codigo_noc, equipo)
SELECT s.atleta_id, o.edicion_id, s.evento_id, s.noc, s.noc
FROM b1_stage s
JOIN edicion_olimpica o ON o.anio = 2024 AND o.tipo = 'Verano'
WHERE s.accion = 'INSERTAR'
ON CONFLICT (atleta_id, edicion_id, evento_id) DO NOTHING;

INSERT INTO resultado (participacion_id, lugar, empatado, medalla)
SELECT p.participacion_id, s.lugar, FALSE, s.medalla
FROM b1_stage s
JOIN participacion p ON p.atleta_id = s.atleta_id AND p.evento_id = s.evento_id
JOIN edicion_olimpica o ON o.edicion_id = p.edicion_id AND o.anio = 2024 AND o.tipo = 'Verano'
WHERE s.accion = 'INSERTAR'
  AND NOT EXISTS (SELECT 1 FROM resultado r WHERE r.participacion_id = p.participacion_id);

-- Verificacion final dentro de la transaccion: todas las filas del CSV deben
-- quedar reflejadas en la base.
DO $$
DECLARE v_falta int;
BEGIN
    SELECT count(*) INTO v_falta FROM b1_stage s
    WHERE NOT EXISTS (
        SELECT 1 FROM participacion p JOIN resultado r USING (participacion_id)
        JOIN edicion_olimpica o ON o.edicion_id = p.edicion_id AND o.anio = 2024 AND o.tipo = 'Verano'
        WHERE p.atleta_id = s.atleta_id AND p.evento_id = s.evento_id AND r.medalla = s.medalla);
    IF v_falta > 0 THEN RAISE EXCEPTION 'B1: % correcciones no quedaron aplicadas', v_falta; END IF;
END $$;

COMMIT;
