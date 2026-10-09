# Discrepancias entre el modelo ER y el DDL

Comparación entre el diagrama `Fase 2/docs/Modelo_ER_actualizado.xml` (draw.io) y
el DDL `Fase 1/sql/ddl.sql`. El diagrama corregido es
`Modelo_ER_fase2.xml`, en esta misma carpeta; la versión en Mermaid es
`modelo_er.mmd`.

## Criterio

Se tomó el DDL como fuente de verdad y se corrigió el diagrama, no el DDL. El
DDL es el que está implementado, el que se entregó en la Fase 1 y el que se
usa para crear las instancias de la Fase 2; cambiarlo alteraría la base que se
respalda y restaura. El diagrama, en cambio, es documentación y debe describir
lo que existe.

El DDL se comparó además con el catálogo de la base de la Fase 1
(`information_schema` y `pg_catalog`, solo lectura, 8 de octubre de 2026): 11
tablas, 11 llaves foráneas, mismas columnas, tipos, UNIQUE, CHECK y 30 índices
B-tree. No hay diferencias entre el DDL y la base.

## Matriz

| # | Elemento | ER original | DDL | Acción sobre el diagrama | Estado |
|---|---|---|---|---|---|
| 1 | PARTICIPACION a RESULTADO | 1 a 0..1 | 1 a N: no hay `UNIQUE(participacion_id)` en `resultado`. En la base hay participaciones con hasta 12 resultados. | Extremo del lado RESULTADO cambiado a 0..N | Corregido en el diagrama |
| 2 | NOC a ATLETA | Relación dibujada | No existe FK; `atleta` no tiene `codigo_noc` (`ddl.sql:13-16`). El vínculo atleta-comité está en `participacion.codigo_noc`, que ya tiene su propia relación NOC a PARTICIPACION. | Arista eliminada; explicado en la leyenda del diagrama | Corregido en el diagrama |
| 3 | `edicion_olimpica.anio` | Marcado FK | No es FK | Marca FK quitada | Corregido en el diagrama |
| 4 | `sede.pais_id` | Sin marca FK | FK a `pais`, `ON DELETE SET NULL` | Marca FK agregada | Corregido en el diagrama |
| 5 | NOC a PARTICIPACION (`participacion.codigo_noc`) | Lado NOC obligatorio (1) | Admite NULL, `ON DELETE SET NULL` | Extremo del lado NOC cambiado a 0..1 | Corregido en el diagrama |
| 6 | SEDE a EDICION_OLIMPICA (`edicion_olimpica.sede_id`) | Lado SEDE obligatorio (1) | Admite NULL, `ON DELETE SET NULL` | Extremo del lado SEDE cambiado a 0..1 | Corregido en el diagrama |
| 7 | PAIS a NOC (`noc.pais_id`) | Lado PAIS obligatorio (1) | Admite NULL, `ON DELETE SET NULL` (16 NOC sin país en la base) | Extremo del lado PAIS cambiado a 0..1 | Corregido en el diagrama |
| 8 | PAIS a SEDE (`sede.pais_id`) | Lado PAIS obligatorio (1) | Admite NULL, `ON DELETE SET NULL` | Extremo del lado PAIS cambiado a 0..1 | Corregido en el diagrama |
| 9 | PAIS a POBLACION_PAIS | Sin extremo del lado PAIS; 1..N del lado POBLACION_PAIS | `pais_id NOT NULL`; el DDL no obliga a que un país tenga población | Extremos cambiados a 1 (PAIS) y 0..N (POBLACION_PAIS) | Corregido en el diagrama |
| 10 | Aristas PAIS a NOC, PAIS a SEDE y EDICION_OLIMPICA a PARTICIPACION | Ancladas solo por coordenadas, sin origen o destino | | Origen y destino conectados a las tablas, para que no se desprendan al mover el dibujo | Corregido en el diagrama |
| 11 | Filas de anclaje | ATLETA salía de `pais_nacimiento`, EDICION_OLIMPICA llegaba a `evento_id`, EVENTO llegaba a `edad`, NOC salía de `nombre_region` | Las FK son `atleta_id`, `edicion_id`, `evento_id` y `codigo_noc` | Aristas reancladas a la columna FK correspondiente | Corregido en el diagrama |
| 12 | Nombres de tablas y atributos | 11 tablas | 11 tablas con los mismos atributos | Ninguna | Sin diferencia |
| 13 | Tipos, UNIQUE, CHECK y acciones `ON DELETE` | No aparecen | Definidos en el DDL (ver abajo) | No se dibujan; se documentan aquí y en `modelo_er.mmd` (marcas UK) | Se documenta |
| 14 | `noc.codigo_noc` como PK natural | | `VARCHAR(6) PRIMARY KEY`; el comentario de `ddl.sql:6` dice que todas las PK son surrogate | Ninguna | Se documenta como decisión de diseño |
| 15 | `atleta.nacionalidad` y `atleta.pais_nacimiento` | Atributos sin relación | Texto libre, sin FK a `pais` | Ninguna | Se documenta como decisión de diseño |
| 16 | Comentario de `ddl.sql:152-156` | | Desactualizado (ver abajo) | Ninguna | `[PENDIENTE]` aplicar el texto propuesto en `Fase 2/01_ddl/01_esquema.sql` |

## Notas sobre cardinalidad

**PARTICIPACION a RESULTADO es 1 a 0..N.** Hoy todas las participaciones de
la base tienen al menos un resultado (0 participaciones sin resultado al 8 de
octubre de 2026), pero el DDL no lo obliga: una participación puede existir
sin filas en `resultado`. El diagrama refleja lo que permite el esquema, no el
estado actual de los datos.

Las participaciones con más de un resultado vienen de la fuente 1, sobre todo
de las ediciones antiguas (1900: 123 participaciones con varios resultados;
1904: 74; 1912 y 1924: 43 cada una). Son las filas que el ETL colapsó al
deduplicar `participacion` por atleta, edición y evento (ver el historial de
`uq_participacion` en `ddl.sql:126-138`).

**FK que admiten NULL.** `noc.pais_id`, `sede.pais_id`,
`edicion_olimpica.sede_id` y `participacion.codigo_noc` admiten NULL y usan
`ON DELETE SET NULL`. En el diagrama se marcan con el extremo 0..1 (círculo y
raya) del lado de la tabla padre, y la leyenda lo explica. En los datos
actuales solo `noc.pais_id` tiene nulos (16 filas); las otras tres no, pero el
diagrama sigue al esquema.

## Decisiones de diseño documentadas

**PK natural en NOC.** `noc` usa como llave primaria el código del comité
(`codigo_noc`, por ejemplo `JAM` o `URS`) en lugar de un identificador
generado. El código del COI es corto, único por comité y es el
identificador con el que todas las fuentes se refieren al comité, incluidos
los comités históricos (cuando un comité cambia de código, el código nuevo es
otra fila). Con él, `participacion.codigo_noc` se lee sin join adicional; un
surrogate agregaría una columna y un join sin aportar unicidad. El comentario general de `ddl.sql:6`
("Todas las PK son surrogate") describe el resto de las tablas; `noc` es la
excepción deliberada.

**Nacionalidad y país de nacimiento como texto.** `atleta.nacionalidad` y
`atleta.pais_nacimiento` se guardan como texto de la fuente y no como FK a
`pais`: los valores históricos (estados disueltos, nombres antiguos) no
siempre corresponden a un país del catálogo actual, y la relación
atleta-comité que importa para los resultados está en
`participacion.codigo_noc`.

**Sin FK entre NOC y ATLETA.** Un mismo atleta puede competir bajo distintos
NOC a lo largo de su carrera, así que el comité se guarda por participación
(`ddl.sql:13-16`).

## Restricciones que el diagrama no muestra

UNIQUE:

| Tabla | Restricción | Columnas |
|---|---|---|
| pais | `uq_pais_nombre` | `nombre` |
| poblacion_pais | `uq_poblacion_pais_anio` | `pais_id, anio` |
| sede | `uq_sede_ciudad_pais` | `ciudad, pais_id` |
| edicion_olimpica | `uq_edicion_anio_tipo` | `anio, tipo` |
| deporte | `uq_deporte_nombre` | `nombre` |
| deporte_equivalencia | `uq_deporte_equivalencia` | `nombre_fuente, fuente_origen` |
| evento | `uq_evento_nombre_deporte` | `nombre, deporte_id` |
| participacion | `uq_participacion` | `atleta_id, edicion_id, evento_id` |

CHECK: `poblacion_pais.anio` entre 1800 y 2100 y `cantidad >= 0`;
`atleta.sexo` en (`M`, `F`) y fecha de fallecimiento posterior a la de
nacimiento; `edicion_olimpica.anio` entre 1896 y 2100 y `tipo` en (`Verano`,
`Invierno`, `Verano-YOG`, `Invierno-YOG`); `participacion.edad` entre 0 y 120,
`altura_cm > 0`, `peso_kg > 0`; `resultado.lugar > 0` y `medalla` en (`Oro`,
`Plata`, `Bronce`).

Acciones `ON DELETE`: `CASCADE` en `poblacion_pais.pais_id`,
`deporte_equivalencia.deporte_id`, `participacion.atleta_id` y
`resultado.participacion_id`; `SET NULL` en `noc.pais_id`, `sede.pais_id`,
`edicion_olimpica.sede_id` y `participacion.codigo_noc`; `RESTRICT` en
`evento.deporte_id`, `participacion.edicion_id` y `participacion.evento_id`.

## Cruce FK del DDL contra aristas del diagrama corregido

| FK del DDL | Arista en `Modelo_ER_fase2.xml` | Extremos (padre / hijo) |
|---|---|---|
| `poblacion_pais.pais_id` a `pais` | `TPrEf07M2ZDzK_5tVpDP-238` | 1 / 0..N |
| `noc.pais_id` a `pais` | `TPrEf07M2ZDzK_5tVpDP-239` | 0..1 / 0..N |
| `sede.pais_id` a `pais` | `TPrEf07M2ZDzK_5tVpDP-240` | 0..1 / 0..N |
| `edicion_olimpica.sede_id` a `sede` | `TPrEf07M2ZDzK_5tVpDP-247` | 0..1 / 0..N |
| `deporte_equivalencia.deporte_id` a `deporte` | `deq-edge1` | 1 / 0..N |
| `evento.deporte_id` a `deporte` | `TPrEf07M2ZDzK_5tVpDP-246` | 1 / 0..N |
| `participacion.atleta_id` a `atleta` | `TPrEf07M2ZDzK_5tVpDP-243` | 1 / 0..N |
| `participacion.edicion_id` a `edicion_olimpica` | `TPrEf07M2ZDzK_5tVpDP-244` | 1 / 0..N |
| `participacion.evento_id` a `evento` | `TPrEf07M2ZDzK_5tVpDP-245` | 1 / 0..N |
| `participacion.codigo_noc` a `noc` | `TPrEf07M2ZDzK_5tVpDP-242` | 0..1 / 0..N |
| `resultado.participacion_id` a `participacion` | `TPrEf07M2ZDzK_5tVpDP-248` | 1 / 0..N |

11 FK y 11 aristas; no hay aristas sin FK ni FK sin arista. Las columnas
marcadas FK en el diagrama son exactamente estas 11.

## Comentario de `ddl.sql:152-156`

Texto actual:

```sql
    -- Nota: el modelo ER declara PARTICIPACION (1) -> RESULTADO (N), así que
    -- deliberadamente NO se agrega UNIQUE(participacion_id) aquí. En la
    -- fuente 1 cada participación empíricamente produce un único resultado
    -- (grano 1:1 en results.csv); se documenta como punto a discutir en el
    -- reporte del ETL en vez de forzar 1:1 en el esquema.
```

La primera frase coincide con el diagrama corregido. La segunda ya no es
cierta: después de deduplicar `participacion` por atleta, edición y evento, la
fuente 1 sí produce participaciones con varios resultados.

Texto propuesto:

```sql
    -- Nota: el modelo ER declara PARTICIPACION (1) -> RESULTADO (0..N), así
    -- que deliberadamente NO se agrega UNIQUE(participacion_id) aquí. Al
    -- deduplicar PARTICIPACION por (atleta, edición, evento), las filas
    -- colapsadas de la fuente 1 (sobre todo ediciones de 1900 a 1936) quedan
    -- con varios resultados, hasta 12 por participación.
```

`Fase 1/sql/ddl.sql` no se modifica porque es parte de la entrega de la Fase 1.
`[PENDIENTE]` aplicar el texto propuesto solo en la copia
`Fase 2/01_ddl/01_esquema.sql` (responsable: Persona A). Es un cambio de
comentario y no altera el esquema.

## Pendientes

- `[PENDIENTE: exportar desde draw.io a PNG/PDF]` `Modelo_ER_fase2.xml` para
  el PDF técnico.
- `[PENDIENTE]` revisión visual del diagrama en draw.io (posición de la
  leyenda y trazado de las aristas reancladas).
