# 04_restauracion: scripts de validación y fragmentación

Scripts SQL que se ejecutan después de cada carga y de cada restauración para
demostrar que la base quedó completa. Todos leen el esquema `olimpiadas` y no
modifican datos.

Estado: probados en una instancia temporal de PostgreSQL 17.10 (vacía y con una
muestra de datos de la Fase 1). Falta probarlos con el `docker-compose.yml`
común de `00_infraestructura/`.

| Archivo | Qué hace |
|---|---|
| `conteos.sql` | `count(*)` de las 11 tablas en orden fijo, sin fechas. Sirve para comparar con `diff` la foto del respaldo contra la base restaurada. |
| `validar.sql` | Fecha y zona horaria del servidor, conteos (incluye `conteos.sql`), `SELECT *` de las 11 tablas ordenado por PK y consultas de muestra: Usain Bolt (atleta 104492), podio del 100 m femenino (evento 1025) y medallero por NOC. |
| `fragmentacion_tablas.sql` | `pgstattuple` por tabla: tamaño, filas vivas y muertas, espacio libre. Una sola consulta, salida CSV. |
| `fragmentacion_indices.sql` | `pgstatindex` por índice B-tree: altura, tamaño, densidad de hojas y fragmentación de hojas. Una sola consulta, salida CSV. |

Requisitos: la extensión `pgstattuple` creada en la base (`CREATE EXTENSION pgstattuple;`)
y ejecutar como `postgres` (superusuario) para los dos scripts de fragmentación.

## Comandos

Dentro del contenedor la carpeta `Fase 2` del repo está montada en `/fase2`, así
que las rutas son absolutas y funcionan desde cualquier directorio. Los
ejemplos usan la corrida por deportista (`fase2_deportista`, `deportista_pc`);
para las otras corridas se cambia el proyecto y el prefijo.

Se ejecutan desde PowerShell. Cuando la salida va a un archivo, la redirección
se hace dentro del contenedor con `bash -c` porque `>` en PowerShell 5.1 escribe
UTF-16.

**Conteos (captura y comparación):**

```powershell
docker compose -p fase2_deportista exec -u postgres db psql -X -At -d olimpiadas -f /fase2/04_restauracion/conteos.sql
```

**Validación para captura (10 filas por tabla):**

```powershell
docker compose -p fase2_deportista exec -u postgres db psql -X -d olimpiadas -v limite=10 -f /fase2/04_restauracion/validar.sql
```

**Validación completa para el log (todas las filas):**

```powershell
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas -v limite=ALL -f /fase2/04_restauracion/validar.sql > /fase2/05_logs/deportista_pc/deportista_pc_15_validar_completo.log 2>&1"
```

Si no se pasa `-v limite=...`, el script usa 10.

**Fragmentación a CSV (pasos 09 y 16):**

```powershell
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas --csv -f /fase2/04_restauracion/fragmentacion_tablas.sql > /fase2/05_logs/deportista_pc/deportista_pc_09_fragmentacion_tablas.csv"
docker compose -p fase2_deportista exec -u postgres db bash -c "psql -X -d olimpiadas --csv -f /fase2/04_restauracion/fragmentacion_indices.sql > /fase2/05_logs/deportista_pc/deportista_pc_09_fragmentacion_indices.csv"
```

Para la captura se corre el mismo comando sin `--csv` ni redirección.

**Comparar antes y después:**

```bash
diff 05_logs/deportista_pc/deportista_pc_09_fragmentacion_tablas.csv 05_logs/deportista_pc/deportista_pc_16_fragmentacion_tablas.csv
```

## Salida esperada

`conteos.sql` imprime 11 líneas `tabla|filas`. Con la base vacía todas valen 0;
después de la carga base:

```text
pais|204
poblacion_pais|13026
noc|236
sede|0
edicion_olimpica|0
deporte|95
deporte_equivalencia|2
evento|0
atleta|0
participacion|0
resultado|0
```

Los conteos acumulados de cada ronda están en la sección 1.2 de
`Fase 2/docs/GUIA_EQUIPO_FASE2.md`.

`validar.sql` termina con código 0 y la línea `FIN DE LA VALIDACION`. Con
`ON_ERROR_STOP` activado, cualquier error detiene el script con código 3.

`fragmentacion_tablas.sql` en tablas vacías devuelve ceros. En
`fragmentacion_indices.sql`, un índice vacío devuelve `tree_level` 0,
`index_size` 8192 y `NaN` en `avg_leaf_density` y `leaf_fragmentation`, porque
no tiene hojas que medir.

## Datos que no son errores

- En la consulta de Bolt, el relevo 4x100 de 2008 sale sin lugar ni medalla
  (medalla retirada en 2017).
- El podio del 100 m se arma con `medalla` y no con `lugar`. En la fuente 1,
  `lugar` es la posición en la última ronda que corrió cada atleta, por lo que
  varias atletas de una edición pueden tener lugar 3 sin medalla. En 2024 todas
  las filas tienen `lugar` NULL porque la fuente 3 solo trae la medalla.
- En 2008 el podio del 100 m femenino tiene dos platas (empate, `empatado = t`)
  y ningún bronce.
- El medallero cuenta medallas por atleta: un oro de relevo suma una por cada
  integrante.
