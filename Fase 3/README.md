# Fase 3: migracion de la base de las Olimpiadas a MongoDB

Sistemas de Bases de Datos 2, Universidad de San Carlos de Guatemala. Grupo 4.

La base relacional de la Fase 1 (PostgreSQL) se corrigio y se migro a MongoDB. Las consultas por atleta y por
pais responden en milisegundos porque cada una es una lectura indexada de un documento (o de un rango indexado
paginado), sin `$lookup` ni agregaciones en tiempo real.

## Contenido

| Carpeta | Contenido |
|---|---|
| `00_infraestructura/` | `docker-compose.yml` (MongoDB 7, puerto 57017, volumen persistente), README, respaldos de Postgres con fecha y hora |
| `01_correcciones/` | Scripts SQL idempotentes de las correcciones en Postgres (B1 medallas de Paris 2024, B2 fusion de atletas duplicados), sus CSV de datos, `CAMBIOS_VS_FASE1.md` y `LIMITACIONES_CONOCIDAS.md` |
| `02_exportar/` | `exportar_postgres.py`: genera `data/*.jsonl` desde Postgres en streaming |
| `03_colecciones/` | `crear_colecciones.js`: colecciones con validadores `$jsonSchema` |
| `04_carga/` | `cargar.py`: carga por lotes de 5,000 (`insert_many`, `ordered=False`) |
| `05_indices/` | `crear_indices.js`: indices, creados despues de la carga |
| `06_validacion/` | `validar.py`, `comparar_postgres_mongo.py` y su reporte, linea base (`linea_base_fase1.json`, `linea_base_fase3.json`), auditoria de duplicados |
| `07_consultas/` | `atleta.py`, `pais.py`, `evidencia_consultas.py` y `GUION_CALIFICACION.md` |
| `levantar_todo.py` | Arranque completo en un comando (ver "Arranque rapido") |
| `08_logs/` | Bitacora de cada ejecucion con fecha y hora de inicio y fin, conteos y duracion; evidencia de `--explain` |

## Arranque rapido

```
python levantar_todo.py             # levanta Docker/MongoDB; carga si la base esta vacia, si no solo valida
python levantar_todo.py --recargar  # rehace exportacion, colecciones, carga e indices aunque ya haya datos
```

`levantar_todo.py` verifica que Docker corra, ejecuta `docker compose up -d`, espera el ping de MongoDB y, segun el estado de
la base, corre los pasos 3 a 7 de abajo o solo `validar.py` y los conteos. Es idempotente (se puede repetir sin efectos
colaterales), termina con codigo 1 y un mensaje claro si falta algo (Docker apagado, librerias, PostgreSQL sin `.jsonl`) e
imprime al final comandos de ejemplo. Bitacora con fecha y hora en `08_logs/levantar_todo_*.log`. Si PostgreSQL no responde pero
los `.jsonl` ya existen, los reutiliza; el paso 0 (PostgreSQL) sigue siendo manual.

## Orden de ejecucion

Requisitos: Docker, Python 3.11 y `mongosh`. Todos los comandos se ejecutan desde la carpeta `Fase 3/` (la raiz de este README).

```
0. Preparacion (una sola vez)
     pip install -r requirements.txt
     # PostgreSQL con la base ya corregida (archivo fuente fuente/olimpiadas_fase3_postgres.dump).
     # Si ya existe el contenedor olimpiadas_pg con la base de la Fase 3, se omite. En Git Bash de Windows el prefijo
     # MSYS_NO_PATHCONV=1 evita que se reescriban las rutas del contenedor.
     docker run -d --name olimpiadas_pg -e POSTGRES_PASSWORD=olimpiadas -e POSTGRES_DB=olimpiadas -p 55433:5432 postgres:16
     docker cp fuente/olimpiadas_fase3_postgres.dump olimpiadas_pg:/tmp/olimpiadas_fase3_postgres.dump
     docker exec olimpiadas_pg pg_restore -U postgres -d olimpiadas --no-owner /tmp/olimpiadas_fase3_postgres.dump
     # (esperar unos segundos a que Postgres acepte conexiones antes de restaurar)
     # Nota: la contrasena "olimpiadas" es una credencial de desarrollo local, no reutilizar.
1. docker compose -f 00_infraestructura/docker-compose.yml up -d
2. Correcciones en Postgres (solo si se parte de la base de la Fase 1 sin corregir; el respaldo del paso 0 ya las incluye):
     python 01_correcciones/ejecutar_correccion.py 01_correcciones/B1_medallas_paris2024.sql 01_correcciones/datos/correcciones_paris2024.csv
     python 01_correcciones/ejecutar_correccion.py 01_correcciones/B2_fusion_atletas.sql 01_correcciones/datos/pares_aprobados.csv --var fase=1
     python 01_correcciones/ejecutar_correccion.py 01_correcciones/B2_fusion_atletas.sql 01_correcciones/datos/pares_aprobados.csv --var fase=2
3. python 02_exportar/exportar_postgres.py           (usa postgresql://postgres:olimpiadas@localhost:55433/olimpiadas; otro destino con --dsn)
4. mongosh "mongodb://localhost:57017/olimpiadas_mongo" --file 03_colecciones/crear_colecciones.js
5. python 04_carga/cargar.py
6. mongosh "mongodb://localhost:57017/olimpiadas_mongo" --file 05_indices/crear_indices.js
7. python 06_validacion/validar.py
8. python 07_consultas/evidencia_consultas.py        (calentamiento y evidencia de --explain)
9. python 06_validacion/comparar_postgres_mongo.py   (opcional: compara las funciones de Postgres con atleta.py y pais.py; genera un reporte con fecha y hora)
```

Notas: `ejecutar_correccion.py` (paso 2) usa el contenedor `olimpiadas_pg` y hace un `pg_dump` previo en `00_infraestructura/backups/`.
`06_validacion/linea_base.py --referencia fase3` reproduce la linea base de Postgres. Este README se ensayo desde cero (carpeta nueva con el zip,
entorno virtual limpio, `docker compose down -v`, Postgres restaurado del archivo fuente): los conteos y `validar.py` dieron igual.
Para una demostracion, ver `07_consultas/GUION_CALIFICACION.md`.

Cada paso deja su bitacora en `08_logs/`. El paso 3 genera unos 380 MB de `.jsonl` (no se versionan en git; van en el paquete de entrega).

## Consultas

```
python 07_consultas/atleta.py "Summer McIntosh" [--deporte X] [--pais X] [--anio N] [--incluir-yog] [--id N] [--explain]
python 07_consultas/pais.py "Germany" [--anio N] [--deporte X] [--incluir-yog] [--detalle] [--pagina N] [--tam N] [--explain]
```

- `atleta.py`: modos `CANDIDATO` (varios homonimos, elegir con `--id`), `DETALLE` y `SIN_COINCIDENCIAS`. Busca sin acentos ni
  mayusculas por nombre, nombre completo o alias (nombre con que aparecia un atleta fusionado), luego por palabras en cualquier
  orden y luego por prefijo. El detalle sale de un solo documento.
- `pais.py`: acepta el nombre en ingles (convencion del Banco Mundial, "Russian Federation"), el codigo NOC ("GER") o un
  prefijo. Muestra NOC asociados, sedes (o `NUNCA_SEDE`), medallas, participacion por edicion y por deporte. Con `--detalle`
  pagina las participaciones y resultados.
- Ambos imprimen fecha y hora de ejecucion y el tiempo de respuesta en ms; con `--explain` muestran el plan (`IXSCAN` o `IDHACK`, nunca `COLLSCAN`).
- Los Juegos Olimpicos de la Juventud (YOG) se excluyen salvo que se pase `--incluir-yog`.
- Las medallas van siempre con dos cifras etiquetadas: **por atleta** (una por atleta y resultado, criterio de la Fase 1) y
  **por evento** (conteo oficial: una medalla por evento y NOC). Para Paris 2024 la cifra por evento es 329 / 330 / 385, igual al medallero oficial.

## Modelo en MongoDB

- `atletas` (153,049): un documento por atleta con sus participaciones y resultados embebidos, alias, `claves`, `tokens` y `resumen_medallas`.
- `participaciones` (319,961): coleccion plana con el atleta desnormalizado, `es_yog` y `pais_id` resuelto con la regla multi-NOC.
- `paises` (213): 204 paises y 9 entidades sin pais (por ejemplo `TPE` / Taiwan, `ROC`, `EOR`) con NOC, sedes, medalleros
  (total, sin YOG, YOG; por atleta y por evento), participacion por edicion y por deporte precalculados.
- `ediciones` (61) y `deportes` (95): catalogos.

Indices: `atletas` `{nombre_key}`, `{tokens}`, `{participaciones.anio, participaciones.deporte}` y `{claves}`; `participaciones`
`{atleta_id, anio}`, `{pais_id, es_yog, anio, deporte}`, `{pais_id, medalla}`, `{noc, anio}`; `paises` `{nombre_key}` unico,
`{nocs.codigo}` y `{tokens}`. No se usa indice de texto: las busquedas por prefijo son regex anclado sin la opcion `i` sobre
`nombre_key`, ya plegado (sin acentos, en minusculas).

Decisiones documentadas: un pais agrega todos sus NOC historicos (`URS` y `EUN` se atribuyen a Rusia por nombre de region, igual
que en la Fase 1); `medalla` en `participaciones` es la mejor medalla de la participacion y `medallas` trae todas (42 participaciones
tienen mas de un resultado con medalla); hay 886 atletas sin participaciones (heredados de la Fase 1).

## Correcciones respecto a la Fase 1

Ver `01_correcciones/CAMBIOS_VS_FASE1.md` (antes y despues de cada correccion) y `01_correcciones/LIMITACIONES_CONOCIDAS.md`.

| Dato | Fase 1 | Fase 3 |
|---|---:|---:|
| atletas | 153,443 | 153,049 (394 duplicados fusionados) |
| participaciones | 319,950 | 319,961 (relevo mixto de triatlon de Paris 2024) |
| resultados | 320,465 | 320,476 |
| Alemania, oro / plata / bronce | 1,354 / 1,302 / 1,331 | 1,357 / 1,303 / 1,331 |

## Limitaciones conocidas (resumen)

199 eventos de 2024 con nomenclatura distinta de la Fase 1; 3 pseudo-eventos de la fuente 3; Lasse Luhrs sin registro;
66 pares de duplicados probables sin fusionar (48 de equipos grandes, 12 no verificables, 4 incorrectos, 2 otros);
178 atletas con nombre "particula + nombre de pila" sin apellido; pares de confianza media y baja sin fusionar; los
3 grupos de apellidos patronimicos heredados de la Fase 1. Detalle y conteos en `LIMITACIONES_CONOCIDAS.md`.

## Fuentes de datos y licencias

Heredadas de la Fase 1 (ver su informe): Olympedia via KeithGalli/Olympics-Dataset (MIT), Kaggle "120 years of Olympic history"
(CC0) y Kaggle "Summer Olympics medals 1896-2024" (CC BY-NC-SA 4.0; el entregable hereda esa licencia y no es de uso comercial).
Fuente manual declarada en esta fase: resultados oficiales de Paris 2024 segun Wikipedia, consultados el 2026-10-19, usados en
`datos/correcciones_paris2024.csv`, `datos/pares_aprobados.csv` y `06_validacion/b2_auditoria_alta.csv` (URL por fila).
