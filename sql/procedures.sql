-- ============================================================================
-- Proyecto Olimpiadas - Sistemas de Bases de Datos 2 (USAC)
-- Incisos d) y e): "stored procedures" del enunciado.
-- ============================================================================
-- Decisión de diseño (function vs. procedure) -- ver DECISIONES.md:
--   El enunciado pide "stored procedure", pero en PostgreSQL un
--   CREATE PROCEDURE (invocado con CALL) no puede devolver un result set
--   tabular por sí mismo -- solo modifica datos o usa parámetros INOUT/
--   refcursor. Para que el profesor pueda hacer `SELECT * FROM ...(...)`
--   el día de la calificación, la lógica real vive en dos FUNCTIONS
--   (fn_atleta_info, fn_pais_info) que devuelven RETURNS TABLE. Se agregan
--   además dos PROCEDURES delgados (pr_atleta_info, pr_pais_info) que
--   envuelven esas funciones con un parámetro INOUT refcursor, para cumplir
--   la letra del enunciado ("stored procedure", invocable con CALL) sin
--   duplicar lógica.
--
-- Ambos incisos comparten dos piezas de infraestructura:
--   - f_normalizar(text): plegado de acentos/mayúsculas (mismo criterio que
--     name_match_key() en etl/etl.py, reimplementado en SQL con unaccent).
--   - fn_noc_por_pais(pais): resuelve un nombre de país a TODOS los códigos
--     NOC históricamente asociados (ver inciso e) más abajo para el detalle
--     de por qué esto no es un simple filtro por pais_id).
-- ============================================================================

SET search_path TO olimpiadas;

-- ----------------------------------------------------------------------------
-- Infraestructura: normalización de texto (acentos/mayúsculas)
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE OR REPLACE FUNCTION olimpiadas.f_normalizar(p_texto TEXT)
RETURNS TEXT
LANGUAGE sql
STABLE
AS $$
    -- unaccent() se qualifica con el schema porque CREATE EXTENSION la instaló
    -- en olimpiadas (primer schema del search_path al momento de crearla, ver
    -- SET search_path arriba); qualificarla evita depender del search_path del
    -- caller, igual que el resto de este archivo (ver DECISIONES.md).
    SELECT lower(olimpiadas.unaccent(trim(regexp_replace(coalesce(p_texto, ''), '\s+', ' ', 'g'))));
$$;

COMMENT ON FUNCTION olimpiadas.f_normalizar(TEXT) IS
    'Pliega espacios/mayúsculas/tildes para matching insensible a acentos. '
    'Mismo criterio que name_match_key() en etl/etl.py (documentado en '
    'DECISIONES.md, auditoría 2026-09-13: Paweł/Pawel, González/Gonzalez, '
    'Galván/Galvan). Solo para EMPAREJAR -- nunca se usa para mostrar datos.';

-- ----------------------------------------------------------------------------
-- Infraestructura: NOC(s) asociados a un país (multi-NOC histórico)
-- ----------------------------------------------------------------------------
-- Un país puede corresponder a más de un código NOC a lo largo de la historia
-- (por eso NOC no tiene FK directa a ATLETA -- ver modelo_er_proyecto1.md).
-- Ejemplo real ya cargado: Alemania = GER + FRG + GDR, los 3 con
-- noc.pais_id apuntando al mismo país (nunca se forzó NULL para ellos).
--
-- Caso más sutil, y la razón de que esta función NO sea un simple
-- `WHERE pais_id = ...`: URS (URSS) y EUN (Equipo Unificado 1992) tienen
-- pais_id FORZADO A NULL a propósito (ver NOC_FORCE_NULL_PAIS en etl.py y
-- DECISIONES.md "No hay FK directa NOC → ATLETA" / entidades históricas
-- disueltas) -- la fuente original SÍ trae region='Russia' para ambos, pero
-- el ETL deliberadamente no los atribuye a un país sucesor. Antes de
-- "corregir" eso agregándolos a la fuerza a pais_id de Rusia (lo que
-- contradiría esa decisión ya tomada, ver regla 7 de CLAUDE.md), esta
-- función los recupera de otra forma: comparando nombre_region contra el
-- nombre_region de los NOC que SÍ están atribuidos a ese país (RUS también
-- tiene nombre_region='Russia'). Así se listan como categoría aparte
-- ('ENTIDAD_HISTORICA_NO_ATRIBUIDA') sin tocar la decisión original ni
-- adivinar un mapeo país-por-país a mano.
CREATE OR REPLACE FUNCTION olimpiadas.fn_noc_por_pais(p_pais TEXT)
RETURNS TABLE (
    pais_id       INTEGER,
    pais_nombre   VARCHAR,
    codigo_noc    VARCHAR,
    nombre_region VARCHAR,
    categoria     VARCHAR   -- 'PAIS_ACTUAL' | 'ENTIDAD_HISTORICA_NO_ATRIBUIDA'
                             -- | 'SIN_NOC_ASOCIADO' | 'PAIS_NO_ENCONTRADO'
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_pais_id     INTEGER;
    v_pais_nombre VARCHAR;
BEGIN
    -- 1) match exacto (normalizado) contra pais.nombre
    SELECT p.pais_id, p.nombre INTO v_pais_id, v_pais_nombre
    FROM olimpiadas.pais p
    WHERE olimpiadas.f_normalizar(p.nombre) = olimpiadas.f_normalizar(p_pais)
    LIMIT 1;

    -- 2) fallback: coincidencia parcial (pais.nombre sigue convención Banco
    --    Mundial en inglés, ej. "Russian Federation" -- "Russia" calza aquí)
    IF v_pais_id IS NULL THEN
        SELECT p.pais_id, p.nombre INTO v_pais_id, v_pais_nombre
        FROM olimpiadas.pais p
        WHERE olimpiadas.f_normalizar(p.nombre) LIKE '%' || olimpiadas.f_normalizar(p_pais) || '%'
        ORDER BY length(p.nombre) ASC
        LIMIT 1;
    END IF;

    IF v_pais_id IS NULL THEN
        RETURN QUERY SELECT NULL::INTEGER, NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR,
            'PAIS_NO_ENCONTRADO'::VARCHAR;
        RETURN;
    END IF;

    RETURN QUERY
    SELECT v_pais_id, v_pais_nombre, n.codigo_noc, n.nombre_region,
           (CASE WHEN n.pais_id IS NOT NULL THEN 'PAIS_ACTUAL'
                 ELSE 'ENTIDAD_HISTORICA_NO_ATRIBUIDA' END)::VARCHAR
    FROM olimpiadas.noc n
    WHERE n.pais_id = v_pais_id
       OR n.nombre_region IN (
           SELECT DISTINCT n2.nombre_region FROM olimpiadas.noc n2 WHERE n2.pais_id = v_pais_id
       )
    ORDER BY (n.pais_id IS NULL), n.codigo_noc;

    IF NOT FOUND THEN
        RETURN QUERY SELECT v_pais_id, v_pais_nombre, NULL::VARCHAR, NULL::VARCHAR,
            'SIN_NOC_ASOCIADO'::VARCHAR;
    END IF;
END;
$$;

COMMENT ON FUNCTION olimpiadas.fn_noc_por_pais(TEXT) IS
    'Resuelve un nombre de país a TODOS los codigo_noc históricamente '
    'asociados (ej. Alemania -> GER, FRG, GDR; Rusia -> RUS, URS, EUN). '
    'Ver comentario arriba en el archivo para la lógica de URS/EUN.';

-- ============================================================================
-- Inciso d) Información de un atleta por nombre
-- ============================================================================
-- Homónimos (ver DECISIONES.md, auditoría 2026-09-13: "Jack Robinson",
-- "Jordan Thompson"): si el nombre da más de un atleta_id, la función NO
-- elige uno arbitrariamente -- devuelve la lista de candidatos (modo
-- 'CANDIDATO') con datos para distinguirlos. Se puede pasar p_atleta_id
-- para ir directo al detalle (modo 'DETALLE').
CREATE OR REPLACE FUNCTION olimpiadas.fn_atleta_info(
    p_nombre    TEXT,
    p_atleta_id INTEGER DEFAULT NULL,
    p_deporte   TEXT    DEFAULT NULL,
    p_pais      TEXT    DEFAULT NULL,
    p_anio      SMALLINT DEFAULT NULL
) RETURNS TABLE (
    modo                VARCHAR,  -- 'CANDIDATO' | 'DETALLE' | 'SIN_COINCIDENCIAS'
    atleta_id           INTEGER,
    nombre_completo      VARCHAR,
    nombre_usado         VARCHAR,
    sexo                 CHAR(1),
    nacionalidad         VARCHAR,
    fecha_nacimiento     DATE,
    pais_nacimiento      VARCHAR,
    deportes_practicados TEXT,     -- solo en modo CANDIDATO, para desambiguar
    edicion_anio         SMALLINT,
    edicion_tipo         VARCHAR,
    deporte_nombre       VARCHAR,
    evento_nombre        VARCHAR,
    codigo_noc           VARCHAR,
    equipo               VARCHAR,
    lugar                INTEGER,
    empatado             BOOLEAN,
    medalla              VARCHAR
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_ids       INTEGER[];
    v_count     INTEGER;
    v_target_id INTEGER;
BEGIN
    IF p_atleta_id IS NOT NULL THEN
        v_ids := ARRAY[p_atleta_id];
    ELSE
        SELECT array_agg(DISTINCT a.atleta_id) INTO v_ids
        FROM olimpiadas.atleta a
        WHERE olimpiadas.f_normalizar(a.nombre_usado) = olimpiadas.f_normalizar(p_nombre)
           OR olimpiadas.f_normalizar(a.nombre_completo) = olimpiadas.f_normalizar(p_nombre);

        IF v_ids IS NULL THEN
            -- fallback: coincidencia parcial si no hubo match exacto
            SELECT array_agg(DISTINCT a.atleta_id) INTO v_ids
            FROM olimpiadas.atleta a
            WHERE olimpiadas.f_normalizar(a.nombre_usado) LIKE '%' || olimpiadas.f_normalizar(p_nombre) || '%'
               OR olimpiadas.f_normalizar(a.nombre_completo) LIKE '%' || olimpiadas.f_normalizar(p_nombre) || '%';
        END IF;
    END IF;

    v_count := COALESCE(array_length(v_ids, 1), 0);

    IF v_count = 0 THEN
        RETURN QUERY SELECT 'SIN_COINCIDENCIAS'::VARCHAR,
            NULL::INTEGER, NULL::VARCHAR, NULL::VARCHAR, NULL::CHAR(1), NULL::VARCHAR,
            NULL::DATE, NULL::VARCHAR, NULL::TEXT, NULL::SMALLINT, NULL::VARCHAR,
            NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, NULL::INTEGER,
            NULL::BOOLEAN, NULL::VARCHAR;
        RETURN;
    END IF;

    IF v_count > 1 AND p_atleta_id IS NULL THEN
        -- Homónimos: se listan candidatos, no se elige ninguno.
        RETURN QUERY
        SELECT 'CANDIDATO'::VARCHAR, a.atleta_id, a.nombre_completo, a.nombre_usado, a.sexo,
               a.nacionalidad, a.fecha_nacimiento, a.pais_nacimiento,
               (SELECT string_agg(DISTINCT d.nombre, ', ' ORDER BY d.nombre)
                FROM olimpiadas.participacion p2
                JOIN olimpiadas.evento ev2 ON ev2.evento_id = p2.evento_id
                JOIN olimpiadas.deporte d ON d.deporte_id = ev2.deporte_id
                WHERE p2.atleta_id = a.atleta_id) AS deportes_practicados,
               NULL::SMALLINT, NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR,
               NULL::VARCHAR, NULL::INTEGER, NULL::BOOLEAN, NULL::VARCHAR
        FROM olimpiadas.atleta a
        WHERE a.atleta_id = ANY(v_ids)
        ORDER BY a.atleta_id;
        RETURN;
    END IF;

    v_target_id := v_ids[1];

    IF NOT EXISTS (SELECT 1 FROM olimpiadas.atleta a WHERE a.atleta_id = v_target_id) THEN
        RETURN QUERY SELECT 'SIN_COINCIDENCIAS'::VARCHAR,
            NULL::INTEGER, NULL::VARCHAR, NULL::VARCHAR, NULL::CHAR(1), NULL::VARCHAR,
            NULL::DATE, NULL::VARCHAR, NULL::TEXT, NULL::SMALLINT, NULL::VARCHAR,
            NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, NULL::INTEGER,
            NULL::BOOLEAN, NULL::VARCHAR;
        RETURN;
    END IF;

    -- Detalle: exactamente un atleta (por atleta_id explícito o único match
    -- por nombre). LEFT JOIN para que el atleta siempre aparezca aunque los
    -- filtros opcionales (deporte/país/año) excluyan todas sus participaciones.
    RETURN QUERY
    SELECT 'DETALLE'::VARCHAR, a.atleta_id, a.nombre_completo, a.nombre_usado, a.sexo,
           a.nacionalidad, a.fecha_nacimiento, a.pais_nacimiento,
           NULL::TEXT,
           e.anio, e.tipo, d.nombre, ev.nombre, part.codigo_noc, part.equipo,
           r.lugar, r.empatado, r.medalla
    FROM olimpiadas.atleta a
    LEFT JOIN olimpiadas.participacion part ON part.atleta_id = a.atleta_id
        AND (p_anio IS NULL OR EXISTS (
            SELECT 1 FROM olimpiadas.edicion_olimpica e3
            WHERE e3.edicion_id = part.edicion_id AND e3.anio = p_anio))
        AND (p_deporte IS NULL OR EXISTS (
            SELECT 1 FROM olimpiadas.evento ev3
            JOIN olimpiadas.deporte d3 ON d3.deporte_id = ev3.deporte_id
            WHERE ev3.evento_id = part.evento_id
              AND olimpiadas.f_normalizar(d3.nombre) = olimpiadas.f_normalizar(p_deporte)))
        AND (p_pais IS NULL OR part.codigo_noc IN (
            SELECT np.codigo_noc FROM olimpiadas.fn_noc_por_pais(p_pais) np WHERE np.codigo_noc IS NOT NULL))
    LEFT JOIN olimpiadas.edicion_olimpica e ON e.edicion_id = part.edicion_id
    LEFT JOIN olimpiadas.evento ev ON ev.evento_id = part.evento_id
    LEFT JOIN olimpiadas.deporte d ON d.deporte_id = ev.deporte_id
    LEFT JOIN olimpiadas.resultado r ON r.participacion_id = part.participacion_id
    WHERE a.atleta_id = v_target_id
    ORDER BY e.anio, ev.nombre;
END;
$$;

COMMENT ON FUNCTION olimpiadas.fn_atleta_info(TEXT, INTEGER, TEXT, TEXT, SMALLINT) IS
    'Inciso d). Uso: SELECT * FROM fn_atleta_info(''Jack Robinson''). Si hay '
    'homónimos devuelve modo=CANDIDATO (sin elegir uno); pasar atleta_id '
    'para ir directo a modo=DETALLE (participaciones+resultados+medallas).';

-- Procedure delgado (letra del enunciado): envuelve fn_atleta_info con un
-- refcursor INOUT, ya que un PROCEDURE de Postgres no puede devolver un
-- result set tabular directamente.
CREATE OR REPLACE PROCEDURE olimpiadas.pr_atleta_info(
    IN p_nombre       TEXT,
    IN p_atleta_id    INTEGER  DEFAULT NULL,
    IN p_deporte      TEXT     DEFAULT NULL,
    IN p_pais         TEXT     DEFAULT NULL,
    IN p_anio         SMALLINT DEFAULT NULL,
    INOUT p_cursor    refcursor DEFAULT 'cur_atleta_info'
)
LANGUAGE plpgsql
AS $$
BEGIN
    OPEN p_cursor FOR
        SELECT * FROM olimpiadas.fn_atleta_info(p_nombre, p_atleta_id, p_deporte, p_pais, p_anio);
END;
$$;

COMMENT ON PROCEDURE olimpiadas.pr_atleta_info(TEXT, INTEGER, TEXT, TEXT, SMALLINT, refcursor) IS
    'Uso: BEGIN; CALL pr_atleta_info(''Jack Robinson''); '
    'FETCH ALL FROM cur_atleta_info; COMMIT;';

-- ============================================================================
-- Inciso e) Información de un país
-- ============================================================================
-- Agrega participaciones/medallas/resultados de TODOS los NOC históricamente
-- asociados al país (ver fn_noc_por_pais arriba), y resuelve sede vía
-- PAIS -> SEDE -> EDICION_OLIMPICA. Distingue explícitamente "nunca fue
-- sede" (país válido, 0 filas de sede) de "país no encontrado".
CREATE OR REPLACE FUNCTION olimpiadas.fn_pais_info(
    p_pais TEXT,
    p_anio SMALLINT DEFAULT NULL,
    p_deporte TEXT DEFAULT NULL
) RETURNS TABLE (
    seccion       VARCHAR,  -- 'PAIS_NO_ENCONTRADO' | 'NOC_ASOCIADO' | 'PARTICIPACION'
                             -- | 'RESUMEN_MEDALLAS' | 'SEDE' | 'NUNCA_SEDE'
    codigo_noc    VARCHAR,
    nombre_region VARCHAR,
    categoria_noc VARCHAR,  -- solo en NOC_ASOCIADO: PAIS_ACTUAL / ENTIDAD_HISTORICA_NO_ATRIBUIDA
    edicion_anio  SMALLINT,
    edicion_tipo  VARCHAR,
    deporte_nombre VARCHAR,
    evento_nombre  VARCHAR,
    atleta_id      INTEGER,
    nombre_atleta  VARCHAR,
    lugar          INTEGER,
    empatado       BOOLEAN,
    medalla        VARCHAR,
    sede_ciudad    VARCHAR,
    cantidad       BIGINT   -- solo en RESUMEN_MEDALLAS
) LANGUAGE plpgsql STABLE AS $$
DECLARE
    v_pais_id INTEGER;
BEGIN
    SELECT pais_id INTO v_pais_id FROM olimpiadas.fn_noc_por_pais(p_pais) LIMIT 1;

    IF v_pais_id IS NULL THEN
        RETURN QUERY SELECT 'PAIS_NO_ENCONTRADO'::VARCHAR,
            NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, NULL::SMALLINT, NULL::VARCHAR,
            NULL::VARCHAR, NULL::VARCHAR, NULL::INTEGER, NULL::VARCHAR, NULL::INTEGER,
            NULL::BOOLEAN, NULL::VARCHAR, NULL::VARCHAR, NULL::BIGINT;
        RETURN;
    END IF;

    -- Sección 1: qué NOC se agregaron y por qué (transparencia del multi-NOC)
    RETURN QUERY
    SELECT 'NOC_ASOCIADO'::VARCHAR, np.codigo_noc, np.nombre_region, np.categoria,
        NULL::SMALLINT, NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, NULL::INTEGER,
        NULL::VARCHAR, NULL::INTEGER, NULL::BOOLEAN, NULL::VARCHAR, NULL::VARCHAR, NULL::BIGINT
    FROM olimpiadas.fn_noc_por_pais(p_pais) np
    WHERE np.codigo_noc IS NOT NULL;

    -- Sección 2: participaciones + resultados/medallas, filtros opcionales
    RETURN QUERY
    SELECT 'PARTICIPACION'::VARCHAR, part.codigo_noc, n.nombre_region, NULL::VARCHAR,
        e.anio, e.tipo, d.nombre, ev.nombre, a.atleta_id, a.nombre_usado,
        r.lugar, r.empatado, r.medalla, NULL::VARCHAR, NULL::BIGINT
    FROM olimpiadas.participacion part
    JOIN olimpiadas.noc n ON n.codigo_noc = part.codigo_noc
    JOIN olimpiadas.edicion_olimpica e ON e.edicion_id = part.edicion_id
    JOIN olimpiadas.evento ev ON ev.evento_id = part.evento_id
    JOIN olimpiadas.deporte d ON d.deporte_id = ev.deporte_id
    JOIN olimpiadas.atleta a ON a.atleta_id = part.atleta_id
    LEFT JOIN olimpiadas.resultado r ON r.participacion_id = part.participacion_id
    WHERE part.codigo_noc IN (
            SELECT np.codigo_noc FROM olimpiadas.fn_noc_por_pais(p_pais) np WHERE np.codigo_noc IS NOT NULL)
      AND (p_anio IS NULL OR e.anio = p_anio)
      AND (p_deporte IS NULL OR olimpiadas.f_normalizar(d.nombre) = olimpiadas.f_normalizar(p_deporte))
    ORDER BY e.anio, ev.nombre;

    -- Sección 3: resumen de medallero agregado (todos los NOC del país juntos)
    RETURN QUERY
    SELECT 'RESUMEN_MEDALLAS'::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR,
        NULL::SMALLINT, NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, NULL::INTEGER,
        NULL::VARCHAR, NULL::INTEGER, NULL::BOOLEAN, r.medalla, NULL::VARCHAR, COUNT(*)::BIGINT
    FROM olimpiadas.participacion part
    JOIN olimpiadas.resultado r ON r.participacion_id = part.participacion_id
    JOIN olimpiadas.edicion_olimpica e ON e.edicion_id = part.edicion_id
    JOIN olimpiadas.evento ev ON ev.evento_id = part.evento_id
    JOIN olimpiadas.deporte d ON d.deporte_id = ev.deporte_id
    WHERE part.codigo_noc IN (
            SELECT np.codigo_noc FROM olimpiadas.fn_noc_por_pais(p_pais) np WHERE np.codigo_noc IS NOT NULL)
      AND r.medalla IS NOT NULL
      AND (p_anio IS NULL OR e.anio = p_anio)
      AND (p_deporte IS NULL OR olimpiadas.f_normalizar(d.nombre) = olimpiadas.f_normalizar(p_deporte))
    GROUP BY r.medalla;

    -- Sección 4: sede -- PAIS -> SEDE -> EDICION_OLIMPICA
    RETURN QUERY
    SELECT 'SEDE'::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR,
        e.anio, e.tipo, NULL::VARCHAR, NULL::VARCHAR, NULL::INTEGER, NULL::VARCHAR,
        NULL::INTEGER, NULL::BOOLEAN, NULL::VARCHAR, s.ciudad, NULL::BIGINT
    FROM olimpiadas.sede s
    JOIN olimpiadas.edicion_olimpica e ON e.sede_id = s.sede_id
    WHERE s.pais_id = v_pais_id
    ORDER BY e.anio;

    IF NOT FOUND THEN
        -- País válido pero nunca fue sede: se marca explícitamente, no se
        -- deja como lista vacía sin explicación.
        RETURN QUERY SELECT 'NUNCA_SEDE'::VARCHAR,
            NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR, NULL::SMALLINT, NULL::VARCHAR,
            NULL::VARCHAR, NULL::VARCHAR, NULL::INTEGER, NULL::VARCHAR, NULL::INTEGER,
            NULL::BOOLEAN, NULL::VARCHAR, NULL::VARCHAR, NULL::BIGINT;
    END IF;
END;
$$;

COMMENT ON FUNCTION olimpiadas.fn_pais_info(TEXT, SMALLINT, TEXT) IS
    'Inciso e). Uso: SELECT * FROM fn_pais_info(''Germany''). pais.nombre '
    'sigue convención Banco Mundial en inglés (ej. "Russian Federation", '
    'no "Rusia"); la búsqueda es insensible a acentos/mayúsculas y admite '
    'coincidencia parcial, pero no traduce gentilicios en español.';

-- Procedure delgado (letra del enunciado): mismo patrón de refcursor.
CREATE OR REPLACE PROCEDURE olimpiadas.pr_pais_info(
    IN p_pais      TEXT,
    IN p_anio      SMALLINT DEFAULT NULL,
    IN p_deporte   TEXT     DEFAULT NULL,
    INOUT p_cursor refcursor DEFAULT 'cur_pais_info'
)
LANGUAGE plpgsql
AS $$
BEGIN
    OPEN p_cursor FOR
        SELECT * FROM olimpiadas.fn_pais_info(p_pais, p_anio, p_deporte);
END;
$$;

COMMENT ON PROCEDURE olimpiadas.pr_pais_info(TEXT, SMALLINT, TEXT, refcursor) IS
    'Uso: BEGIN; CALL pr_pais_info(''Germany''); '
    'FETCH ALL FROM cur_pais_info; COMMIT;';

-- ============================================================================
-- Fin de procedures.sql
-- ============================================================================
