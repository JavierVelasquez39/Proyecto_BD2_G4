# Prueba de los scripts de 04_restauracion en instancia temporal

Fecha: jueves 8 de octubre de 2026, 21:52 a 21:58 (America/Guatemala).
Responsable: Javier (Persona C).

Objetivo: comprobar la sintaxis y la lógica de `conteos.sql`, `validar.sql`,
`fragmentacion_tablas.sql` y `fragmentacion_indices.sql`. No es una corrida
oficial y no usa el `docker-compose.yml` común.

## Entorno

- Contenedor desechable `c1_test`, imagen `postgres:17`, PGDATA en `tmpfs` (sin
  volúmenes), `TZ=America/Guatemala`, `--data-checksums`.
- `SELECT version()`: PostgreSQL 17.10 (Debian 17.10-1.pgdg13+1).
- `SHOW TimeZone` = `America/Guatemala`; `SHOW data_checksums` = `on`.
- Esquema creado con `Fase 1/sql/ddl.sql` sin cambios, más
  `CREATE EXTENSION pgstattuple`. El DDL no necesita `unaccent` (solo lo usan
  los procedimientos de la Fase 1, que no forman parte de esta fase).
- Los scripts se ejecutaron como `postgres` con directorio de trabajo `/`, para
  comprobar que `\ir conteos.sql` resuelve la ruta relativa al script.

## Prueba A: instancia vacía

| Script | Resultado |
|---|---|
| `conteos.sql` (2 veces) | Código 0; 11 líneas, todas en 0; `diff` entre las dos salidas sin diferencias |
| `validar.sql -v limite=10` | Código 0 |
| `validar.sql` sin `limite` | Código 0; usa 10 por defecto (salida igual a la anterior salvo las horas) |
| `fragmentacion_tablas.sql --csv` | Código 0; 11 tablas con todos los valores en 0 |
| `fragmentacion_indices.sql --csv` | Código 0; 30 índices B-tree, `tree_level` 0, `index_size` 8192, `avg_leaf_density` y `leaf_fragmentation` = `NaN` |

Con esto queda verificado el pendiente de la guía sobre `pgstattuple` y
`pgstatindex` con tablas vacías: no fallan.

## Prueba B: muestra de datos

Muestra extraída de `olimpiadas_pg` con `COPY (SELECT ...) TO STDOUT` en
sesiones de solo lectura (`default_transaction_read_only=on`) y cargada con
`COPY ... FROM STDIN` en el orden de las llaves foráneas:

- Catálogos completos: pais, poblacion_pais, noc, deporte, deporte_equivalencia.
- Ediciones 45, 47, 51 (Atenas, Pekín, Londres) y 55, 59, 61 (Río, Tokio, París)
  con sus sedes.
- Las 7 participaciones de Bolt (atleta 104492) en 2004, 2008 y 2012.
- 5 participaciones del evento 1025 por edición (medallistas primero).

Conteos obtenidos (iguales en las dos ejecuciones, `diff` sin diferencias):

```text
pais|204
poblacion_pais|13026
noc|236
sede|6
edicion_olimpica|6
deporte|95
deporte_equivalencia|2
evento|4
atleta|22
participacion|37
resultado|37
```

| Script | Resultado |
|---|---|
| `validar.sql -v limite=10` | Código 0; 10 filas por tabla |
| `validar.sql -v limite=ALL` | Código 0; todas las filas (por ejemplo 13,026 en poblacion_pais) |
| `fragmentacion_tablas.sql --csv` | Código 0; por ejemplo poblacion_pais: 917,504 bytes, 13,026 filas, 68.15 % ocupado, 0 filas muertas |
| `fragmentacion_indices.sql --csv` | Código 0; por ejemplo `uq_poblacion_pais_anio`: nivel 1, densidad 76.38 %, fragmentación 42.86 % |

Consultas de muestra:

- Bolt: 7 filas. 2004 200 m (lugar 5), 2008 100 m y 200 m (oro), 2008 relevo
  sin lugar ni medalla, 2012 100 m, 200 m y relevo (oro).
- 100 m femenino: 18 filas, podio de 2004 a 2024. En 2024 `lugar` sale NULL y
  la consulta no falla. En 2008 hay dos platas empatadas y ningún bronce.
- Medallero: JAM 9 oros, 3 platas, 4 bronces (sobre la muestra cargada).

## Limpieza

`docker rm -f c1_test`. Se compararon `docker ps -a` y `docker volume ls` antes
y después: sin contenedores ni volúmenes nuevos. `olimpiadas_pg` siguió
encendido con su volumen original y sin cambios (319,950 participaciones y
320,465 resultados). Los CSV temporales se borraron.

## Pendiente

- Probar los cuatro scripts con el `docker-compose.yml` común (montaje `/fase2`).
- Confirmar los conteos contra los CSV oficiales de las rondas cuando estén.
