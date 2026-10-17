# 08_demo: demostración en vivo de la Fase 2

`demo_calificacion.ps1` muestra el proceso de la carga por deportista (Usain
Bolt, atleta 104492) paso a paso, con pausas, sin tomar capturas. Usa los
mismos scripts compartidos que la corrida oficial (`02_carga`, `03_backup`,
`04_restauracion`) sin modificarlos, en un proyecto de Docker Compose propio:
`fase2_demo`.

## Archivos

| Archivo | Qué es |
|---|---|
| `demo_calificacion.ps1` | Script de la demo, PowerShell 5.1, UTF-8 con BOM. |
| `docker-compose.demo.yml` | Override del compose: monta `08_demo/salida` encima de `/fase2/05_logs`. |
| `.gitignore` | Excluye `salida/`, que solo tiene logs de la demo. |
| `salida/` | Se crea al ejecutar la opción B. Logs y CSV de tiempos de la demo. |

## Cómo se aísla de la corrida oficial

Los scripts compartidos derivan sus rutas del tipo y la persona:
`$FASE2_DIR/05_logs/<tipo>_<persona>/` para los logs y
`$FASE2_DIR/05_logs/tiempos_<tipo>_<persona>.csv` para el CSV. `cargar_ronda.sh`
solo acepta las personas `pa`, `pb` y `pc`, así que no se puede usar una persona
distinta para la demo.

Por eso la demo usa `pc` igual que la corrida oficial, pero el override monta
la carpeta `08_demo/salida` del host en `/fase2/05_logs` dentro del contenedor.
Los scripts escriben donde siempre (`/fase2/05_logs/deportista_pc/...`), y eso
cae en `08_demo/salida/deportista_pc/` y `08_demo/salida/tiempos_deportista_pc.csv`.

Protecciones del script:

- Todos los comandos de Docker Compose pasan por la función `X`, que siempre
  usa `-p fase2_demo` y los dos archivos `-f`, y se niega a seguir si el nombre
  del proyecto no es `fase2_demo`.
- Antes de las opciones B y C, `docker compose config` debe mostrar el montaje
  de `08_demo/salida` en `/fase2/05_logs`. Si no, no se ejecuta nada.
- En el paso 1 de B, el contenedor debe ver el archivo centinela
  `/fase2/05_logs/.salida_demo`, que solo existe en `08_demo/salida`.

Recursos de Docker de la demo: contenedor `fase2_demo-db-1`, volúmenes
`fase2_demo_pgdata` y `fase2_demo_backups`, red `fase2_demo_default`. No
publica puertos.

## Qué NO toca

- El proyecto `fase2_deportista`: ni su contenedor ni sus volúmenes. La opción A
  solo los lista y lee los tamaños de los respaldos montando
  `fase2_deportista_backups` en modo solo lectura (`:ro`) en un contenedor
  temporal con `--rm`.
- `05_logs/deportista_pc/`, `05_logs/tiempos_deportista_pc.csv` y
  `06_evidencias/`: la opción A solo los lee.
- `olimpiadas_pg` ni su volumen.
- Los scripts compartidos (`00_infraestructura`, `02_carga`, `03_backup`,
  `04_restauracion`).

## Cómo ejecutarlo

Desde PowerShell, con Docker Desktop encendido:

```powershell
cd "C:\Users\javie\OneDrive\Desktop\Segundo Semestre 2026\BASES2\Proyecto\Fase 2\08_demo"
powershell -NoProfile -ExecutionPolicy Bypass -File .\demo_calificacion.ps1
```

Ajusta la ruta si el repositorio está en otra carpeta. Conviene pausar OneDrive
durante la demo, igual que en la corrida oficial.

Cada paso imprime `PASO N: ...`, una línea `Qué se comprueba:` para leer en voz
alta y los comandos exactos que va a ejecutar. Con Enter se ejecutan. Al
terminar una opción vuelve al menú; `S` sale.

## Opciones

### A. Evidencia oficial (solo lectura)

- Contenedores y volúmenes de `fase2_deportista`.
- Líneas del CSV oficial (esperado 53: encabezado y 52 filas) y resumen con
  `Import-Csv | Group-Object operacion, etapa`: filas y segundos promedio,
  mínimo y máximo. Conteo de `validacion` y filas con `ALERTA`.
- Archivos en `05_logs/deportista_pc/`, logs rotados y capturas PNG en
  `06_evidencias/deportista_pc/`.
- `du -sb` de `/backups/full` e `incr1` a `incr3` dentro del volumen oficial,
  montado de solo lectura.
- Comparación de los CSV de fragmentación del paso 09 contra los del paso 16.

### B. Ciclo completo en `fase2_demo`

Si ya existe el proyecto `fase2_demo`, avisa y vuelve al menú (hay que usar
antes la opción D). Al empezar vacía `08_demo/salida`.

| Paso | Qué hace | Comprobación automática |
|---|---|---|
| 1 | `up -d --wait`, `chown` de `/backups`, centinela | código de salida 0 |
| 2 | `01_esquema.sql`, `02_extensiones.sql`, `\dt`, `\dx` | código de salida 0 |
| 3 | Carga base | conteos iguales a lo esperado |
| 4 | FULL | CSV con 2 líneas |
| 5 a 10 | r1, INCR 1, r2, INCR 2, r3, INCR 3 | conteos de cada ronda; CSV con 3, 4 y 5 líneas |
| 11 | Fragmentación previa (pantalla y CSV) | código de salida 0 |
| 12 | `DROP DATABASE olimpiadas` | código de salida 0 |
| 13 | `stop db` | código de salida 0 |
| 14 | Restauración n=0, 1, 2, 3, una repetición cada una, sin pausas entre ellas | CSV con 9, 13, 17 y 21 líneas; `VALIDACION OK` y diff de conteos vacío en cada log |
| 15 | `up -d --wait`, conteos contra `conteos_incr3.txt`, fragmentación posterior y `diff` con la previa | `CONTEOS_IGUALES_AL_INCR3` y `FRAGMENTACION_IDENTICA` |

Conteos esperados (iguales a los del runbook): base con pais 204,
poblacion_pais 13026, noc 236, deporte 95, deporte_equivalencia 2 y el resto en
0; después de r1 sede 1, edicion 1, evento 1, atleta 1, participacion 1,
resultado 1; después de r2 2, 2, 3, 1, 4, 4; después de r3 3, 3, 3, 1, 7, 7.

Al final imprime el tiempo total y el tiempo sin contar las pausas.

### C. Restaurar una cadena concreta

Necesita que la opción B se haya ejecutado (volúmenes de `fase2_demo` y CSV de la
demo). Pregunta `n` (0 a 3) y la repetición (1 a 3), muestra los comandos y,
con Enter, ejecuta `stop db`, `restaurar.sh deportista pc <n> <rep> demo` y
muestra `/backups/conteos_full.txt` o `conteos_incr<n>.txt`. Comprueba que el
CSV de la demo ganó 4 filas y que el log tiene `VALIDACION OK` y el diff de
conteos vacío. El servicio `db` queda detenido con la cadena elegida en PGDATA.
Si se repite la misma `n` y repetición, `restaurar.sh` renombra el log
anterior con la hora (solo dentro de `08_demo/salida`).

### D. Limpiar la demo

Muestra los volúmenes de `fase2_demo` y el comando
`docker compose -p fase2_demo ... down -v`. Solo lo ejecuta si se escribe `SI`
en mayúsculas; cualquier otra respuesta cancela. Borra el contenedor, la red y
los dos volúmenes de `fase2_demo`, y luego lista los volúmenes de
`fase2_deportista` para mostrar que siguen ahí. La carpeta `08_demo/salida` se
conserva; la opción B la vacía al empezar.

## Cuánto tarda

Medido en la laptop de la Persona C el 16-oct-2026, sin contar las pausas:

| Opción | Tiempo |
|---|---|
| A | 1.9 s |
| B | 55 s |
| C | [PENDIENTE] medir con reloj; la restauración n=2 en sí tardó 2.5 s (`Total` del log) |
| D | [PENDIENTE] medir con reloj; en la prueba terminó en pocos segundos |

En vivo hay que sumar el tiempo de explicar cada paso.

## Si algo falla

- Ante cualquier código de salida distinto de 0, el script imprime el comando
  que falló y `FALLO. No repitas nada.`, y se detiene. No se repite el paso a
  mano: se revisa el log del paso en `08_demo/salida/deportista_pc/`.
- Si falla el conteo de líneas del CSV o el de las tablas, también se detiene.
  El CSV de la demo está en `08_demo/salida/tiempos_deportista_pc.csv`.
- Para volver a empezar: opción D (con `SI`) y luego opción B. Nada de esto
  toca la corrida oficial.
- Si B avisa que `fase2_demo` ya existe, es de una demo anterior: opción D.
- Si el script dice que el override no monta `08_demo/salida`, no se ejecutó
  nada; revisa que `docker-compose.demo.yml` esté junto al script.
- La evidencia oficial no depende de la demo: si la demo falla en vivo, la
  opción A sigue mostrando la corrida oficial.
