# Documento de Diseño y Justificación Técnica: Fase 2 - Tabla de Equivalencias de Deportes
 
## 1. Problema a Resolver
 
En el proceso de integración de datasets olímpicos multidominio (Fuente 1: Olympedia / Keith Galli, Fuente 2: Kaggle 120 Years, Fuente 3: París 2024), se identificó que distintas fuentes utilizan diferentes niveles de abstracción o nomenclaturas para nombrar un mismo deporte o disciplina.
 
### Casos de Estudio Identificados
 
**Diferencia de Granularidad (Equitación / Equestrian):**
 
- **Fuente 1 (1896-2022):** Divide la equitación en sub-disciplinas específicas como `Equestrian Dressage`, `Equestrian Jumping` y `Equestrian Eventing`.
- **Fuente 3 (París 2024):** Reporta todas las competencias bajo el nombre general de deporte `Equestrian`.
- **Riesgo de diseño:** Forzar los registros de 2024 a una sub-disciplina arbitraria (ej. asociar un jinete de Salto a Dressage) distorsiona la especialidad del atleta y corrompe los datos históricos.
**Diferencia de Nomenclatura Exacta (Gimnasia en Trampolín):**
 
- **Fuente 1:** Registra la disciplina como `Trampolining (Gymnastics)`.
- **Fuente 3:** Registra la misma disciplina como `Trampoline Gymnastics`.
- **Riesgo de diseño:** Si se inserta como una nueva fila en la tabla `DEPORTE`, se genera un duplicado semántico y la BD trata el trampolín de 2024 como un deporte distinto al de años anteriores.
---
 
## 2. Solución Estructural Implementada
 
Para resolver este desafío de unificación de datos sin destruir el catálogo canónico de la Fuente 1 ni perder trazabilidad, se implementó una **Tabla de Equivalencias de Deportes** (`deporte_equivalencia`) en el modelo relacional.
 
### A. Modificación al Modelo Relacional (DDL)
 
Se añadió la entidad `deporte_equivalencia` para crear un mapa de traducción N:1 de variantes hacia el deporte canónico:
 
```sql
CREATE TABLE olimpiadas.deporte_equivalencia (
    equivalencia_id SERIAL PRIMARY KEY,
    nombre_fuente   VARCHAR(150) NOT NULL,
    deporte_id      INTEGER NOT NULL REFERENCES olimpiadas.deporte(deporte_id) ON DELETE CASCADE,
    fuente_origen   VARCHAR(50),
    CONSTRAINT uq_deporte_equivalencia UNIQUE (nombre_fuente, fuente_origen)
);
 
CREATE INDEX ix_deporte_equivalencia_deporte ON olimpiadas.deporte_equivalencia(deporte_id);
```
 
### B. Lógica de Negocio e Integración en el ETL (`etl.py`)
 
Durante la fase de transformación de la Fuente 3:
 
1. Se asegura la existencia del deporte general `Equestrian` en la tabla `DEPORTE` para la equitación no segmentada de 2024.
2. Se registran las equivalencias explícitas en la estructura de datos:
   - `'Equestrian'` (Fuente 3) → Deporte canónico `'Equestrian'`.
   - `'Trampoline Gymnastics'` (Fuente 3) → Deporte canónico `'Trampolining (Gymnastics)'`.
3. Antes de intentar insertar un deporte nuevo desde una fuente secundaria, el ETL consulta primero si el nombre de la fuente existe en `deporte_equivalencia`. Si existe, reutiliza el `deporte_id` canónico existente para vincular los eventos.
---
 
## 3. Justificación Técnica y de Diseño
 
### ¿Por qué esta solución es técnicamente superior?
 
**Principio de Aislamiento y Trazabilidad**
 
- No se sobreescriben ni se alteran los datos originales provenientes de las fuentes primarias. La tabla de equivalencias actúa como una capa de traducción transparente.
- El campo `fuente_origen` permite auditar de dónde proviene cada variación de nombre.
**Preservación de la Integridad Semántica (evita la corrupción de datos)**
 
- En lugar de tomar la decisión arbitraria de clasificar a los atletas de equitación de París 2024 en una sola rama (como Dressage), la creación del concepto genérico `Equestrian` preserva la veracidad de la competencia sin inventar especialidades que la fuente original no especifica.
**Escalabilidad para Futuras Fuentes**
 
- Si en el futuro se integra una Fuente 4 u otra edición olímpica (ej. Los Ángeles 2028) que use nombres alternativos como `Athletics` en lugar de `Track and Field`, no se requiere modificar el código base ni la estructura de las tablas principales. Basta con insertar una nueva fila en `deporte_equivalencia`.
**Eficiencia en Consultas**
 
- Al resolver los `deporte_id` durante la fase de transformación (ETL), las tablas transaccionales masivas (`EVENTO`, `PARTICIPACION`, `RESULTADO`) quedan referenciadas directamente al `deporte_id` canónico. Esto evita tener que ejecutar JOINs complejos con funciones de manipulación de texto (`LOWER`, `REPLACE`) en tiempo de ejecución de reportes.