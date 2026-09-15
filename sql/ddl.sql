-- ============================================================================
-- Proyecto Olimpiadas - Sistemas de Bases de Datos 2 (USAC)
-- DDL PostgreSQL 16 - diseño independiente a partir del modelo ER acordado.
-- ============================================================================
-- Notas de diseño:
--   * Todas las PK son surrogate (SERIAL/BIGSERIAL) generadas por el ETL/DB;
--     ningún identificador de las fuentes externas (athlete_id, Country Code
--     ISO, etc.) se reutiliza como PK para no acoplar el esquema a una fuente
--     concreta. El ETL mantiene el mapeo fuente->surrogate internamente.
--   * NOC.pais_id es NULLABLE: hay códigos NOC (IOA, ROT/EOR, UNK, EUN, ANZ,
--     SCG, ROC, equipos unificados, etc.) que no corresponden a un país
--     actual reconocible en el catálogo PAIS.
--   * No existe FK directa NOC->ATLETA: el vínculo atleta-comité vive
--     exclusivamente en PARTICIPACION.codigo_noc, porque un mismo atleta
--     puede competir bajo distintos NOC a lo largo de su carrera (ver
--     verificación empírica en el reporte del ETL).
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS olimpiadas;
SET search_path TO olimpiadas;

-- ----------------------------------------------------------------------------
CREATE TABLE pais (
    pais_id     SERIAL PRIMARY KEY,
    nombre      VARCHAR(150) NOT NULL,
    CONSTRAINT uq_pais_nombre UNIQUE (nombre)
);

-- ----------------------------------------------------------------------------
CREATE TABLE poblacion_pais (
    poblacion_id SERIAL PRIMARY KEY,
    pais_id      INTEGER NOT NULL REFERENCES pais(pais_id) ON DELETE CASCADE,
    anio         SMALLINT NOT NULL CHECK (anio BETWEEN 1800 AND 2100),
    cantidad     BIGINT NOT NULL CHECK (cantidad >= 0),
    CONSTRAINT uq_poblacion_pais_anio UNIQUE (pais_id, anio)
);
CREATE INDEX ix_poblacion_pais_pais ON poblacion_pais(pais_id);

-- ----------------------------------------------------------------------------
CREATE TABLE noc (
    codigo_noc    VARCHAR(6) PRIMARY KEY,
    nombre_region VARCHAR(150) NOT NULL,
    notas         VARCHAR(255),
    pais_id       INTEGER REFERENCES pais(pais_id) ON DELETE SET NULL
);
CREATE INDEX ix_noc_pais ON noc(pais_id);

-- ----------------------------------------------------------------------------
CREATE TABLE sede (
    sede_id  SERIAL PRIMARY KEY,
    ciudad   VARCHAR(150) NOT NULL,
    pais_id  INTEGER REFERENCES pais(pais_id) ON DELETE SET NULL,
    CONSTRAINT uq_sede_ciudad_pais UNIQUE (ciudad, pais_id)
);
CREATE INDEX ix_sede_pais ON sede(pais_id);

-- ----------------------------------------------------------------------------
CREATE TABLE atleta (
    atleta_id           SERIAL PRIMARY KEY,
    nombre_completo      VARCHAR(300),
    nombre_usado         VARCHAR(200) NOT NULL,
    sexo                 CHAR(1) CHECK (sexo IN ('M','F')),
    nacionalidad         VARCHAR(150),
    fecha_nacimiento     DATE,
    ciudad_nacimiento    VARCHAR(150),
    pais_nacimiento      VARCHAR(150),
    fecha_fallecimiento  DATE,
    CONSTRAINT ck_atleta_fechas CHECK (
        fecha_fallecimiento IS NULL
        OR fecha_nacimiento IS NULL
        OR fecha_fallecimiento >= fecha_nacimiento
    )
);

-- ----------------------------------------------------------------------------
CREATE TABLE edicion_olimpica (
    edicion_id SERIAL PRIMARY KEY,
    anio       SMALLINT NOT NULL CHECK (anio BETWEEN 1896 AND 2100),
    tipo       VARCHAR(10) NOT NULL CHECK (tipo IN ('Verano','Invierno')),
    sede_id    INTEGER REFERENCES sede(sede_id) ON DELETE SET NULL,
    CONSTRAINT uq_edicion_anio_tipo UNIQUE (anio, tipo)
);
CREATE INDEX ix_edicion_sede ON edicion_olimpica(sede_id);

-- ----------------------------------------------------------------------------
CREATE TABLE deporte (
    deporte_id  SERIAL PRIMARY KEY,
    nombre      VARCHAR(150) NOT NULL,
    descripcion TEXT,
    CONSTRAINT uq_deporte_nombre UNIQUE (nombre)
);

-- ----------------------------------------------------------------------------
CREATE TABLE evento (
    evento_id  SERIAL PRIMARY KEY,
    nombre     VARCHAR(255) NOT NULL,
    deporte_id INTEGER NOT NULL REFERENCES deporte(deporte_id) ON DELETE RESTRICT,
    CONSTRAINT uq_evento_nombre_deporte UNIQUE (nombre, deporte_id)
);
CREATE INDEX ix_evento_deporte ON evento(deporte_id);

-- ----------------------------------------------------------------------------
CREATE TABLE participacion (
    participacion_id BIGSERIAL PRIMARY KEY,
    atleta_id   INTEGER NOT NULL REFERENCES atleta(atleta_id) ON DELETE CASCADE,
    edicion_id  INTEGER NOT NULL REFERENCES edicion_olimpica(edicion_id) ON DELETE RESTRICT,
    evento_id   INTEGER NOT NULL REFERENCES evento(evento_id) ON DELETE RESTRICT,
    codigo_noc  VARCHAR(6) REFERENCES noc(codigo_noc) ON DELETE SET NULL,
    equipo      VARCHAR(150),
    edad        SMALLINT CHECK (edad BETWEEN 0 AND 120),
    altura_cm   NUMERIC(5,1) CHECK (altura_cm > 0),
    peso_kg     NUMERIC(5,1) CHECK (peso_kg > 0),
    -- Historial de esta restricción (ver DECISIONES.md):
    --   1) Se probó primero UNIQUE(atleta_id, edicion_id, evento_id,
    --      codigo_noc, equipo) -> UniqueViolation real con Polo 1900 (equipos
    --      compuestos/mixtos de la era pre-moderna, sin columna de ronda en
    --      la fuente para desambiguar).
    --   2) Se retiró la restricción -> señalado en revisión como debilitar
    --      la integridad en vez de arreglar la carga.
    --   3) Se corrigió el ETL para deduplicar por clave natural (una fila de
    --      PARTICIPACION por atleta+edición+evento; cada resultado distinto
    --      pasa a RESULTADO, que ya soporta 1:N) y se repone el UNIQUE aquí,
    --      ahora sin codigo_noc/equipo (attributes de la fila colapsada, no
    --      parte de la identidad de la participación).
    CONSTRAINT uq_participacion UNIQUE (atleta_id, edicion_id, evento_id)
);
CREATE INDEX ix_participacion_atleta  ON participacion(atleta_id);
CREATE INDEX ix_participacion_edicion ON participacion(edicion_id);
CREATE INDEX ix_participacion_evento  ON participacion(evento_id);
CREATE INDEX ix_participacion_noc     ON participacion(codigo_noc);

-- ----------------------------------------------------------------------------
CREATE TABLE resultado (
    resultado_id     SERIAL PRIMARY KEY,
    participacion_id BIGINT NOT NULL REFERENCES participacion(participacion_id) ON DELETE CASCADE,
    lugar            INTEGER CHECK (lugar > 0),
    empatado         BOOLEAN NOT NULL DEFAULT FALSE,
    medalla          VARCHAR(10) CHECK (medalla IN ('Oro','Plata','Bronce'))
    -- Nota: el modelo ER declara PARTICIPACION (1) -> RESULTADO (N), así que
    -- deliberadamente NO se agrega UNIQUE(participacion_id) aquí. En la
    -- fuente 1 cada participación empíricamente produce un único resultado
    -- (grano 1:1 en results.csv); se documenta como punto a discutir en el
    -- reporte del ETL en vez de forzar 1:1 en el esquema.
);
CREATE INDEX ix_resultado_participacion ON resultado(participacion_id);

-- ============================================================================
-- Fin del DDL
-- ============================================================================
