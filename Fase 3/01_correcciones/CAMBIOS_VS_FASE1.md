# Cambios de la Fase 3 respecto a la base de la Fase 1

Este documento lista cada correccion aplicada a PostgreSQL antes de migrar a MongoDB,
con el antes y el despues verificados contra la base real. La linea base de la Fase 1
esta en `06_validacion/linea_base_fase1.json`.

## Correccion B1: medallas faltantes de Paris 2024

Aplicada el 2026-10-19 22:36 (respaldo previo: `00_infraestructura/backups/olimpiadas_pre_B1_medallas_paris2024_2026-10-19_223606.dump`).
Script: `B1_medallas_paris2024.sql`, datos: `datos/correcciones_paris2024.csv` (25 filas, con URL y fecha de verificacion).

**Causa.** La fuente 3 (`olympics_dataset.csv`) registra `Medal = 'No medal'` en las 89 filas de
los 32 atletas que compitieron en dos deportes en 2024 (campo `Sport` compuesto, por ejemplo
"Cycling Road, Cycling Track"), y no trae a los medallistas del relevo mixto de triatlon.
El ETL cargo la fuente fielmente; el defecto esta en la fuente.

**Verificacion externa.** Medallero oficial de Paris 2024 (Wikipedia, "2024 Summer Olympics medal table",
consultado el 2026-10-19): 329 oro, 330 plata, 385 bronce. Fuente manual declarada, no es una de las 4 del enunciado.

| Dato | Antes (Fase 1) | Despues de B1 | Cambio |
|---|---:|---:|---:|
| atleta | 153,443 | 153,443 | 0 |
| participacion | 319,950 | 319,961 | +11 |
| resultado | 320,465 | 320,476 | +11 |
| Medallas Paris 2024, una por atleta (oro / plata / bronce) | 743 / 744 / 794 | 749 / 753 / 804 | +6 / +9 / +10 |
| Medallas Paris 2024, una por evento (oro / plata / bronce) | 325 / 324 / 378 | 329 / 330 / 385 | +4 / +6 / +7 |
| NOC con diferencia contra el medallero oficial | 8 | 0 | -8 |
| Alemania, oro / plata / bronce (historico) | 1,354 / 1,302 / 1,331 | 1,357 / 1,303 / 1,331 | +3 / +1 / 0 |
| Rusia, oro / plata / bronce (historico) | 1,575 / 1,135 / 1,158 | 1,575 / 1,135 / 1,158 | 0 |
| Sedes Estados Unidos / Francia / Guatemala | 8 / 6 / 0 | 8 / 6 / 0 | 0 |

Las diferencias contra la linea base de la Fase 1 en `participacion`, `resultado` y en el medallero
de Alemania son las esperadas y quedan explicadas por esta correccion. El resto de la linea base no cambia.

Limitaciones de B1 (no corregidas):

- Lasse Luhrs (Alemania, relevo mixto de triatlon) no existe en `atleta`; no se creo el registro.
  Por eso el relevo aleman suma 3 atletas con medalla y no 4.
- Los 199 eventos que solo existen en 2024 conservan la nomenclatura de la fuente 3 ("Men -60 kg",
  "Men's 1500m") distinta de la de la fuente 1 ("Half-Lightweight, Men (Olympic)"). No se unificaron:
  exigiria una tabla de equivalencias hecha a mano con riesgo de error. No afecta ningun medallero.
- Tres eventos de la fuente 3 no son pruebas reales y no tienen medallas: gimnasia artistica "Men"
  (96 filas) y "Women" (94 filas), y natacion "Relay Only Athlete" (157 filas).

## Correccion B2: fusion de atletas duplicados por nombre mal parseado

Aplicada en tres transacciones independientes, cada una con su respaldo previo
(`olimpiadas_pre_B2_fusion_atletas_fase1_2026-10-19_231626.dump`, `..._fase2_2026-10-19_231632.dump` y
`..._fase3_2026-10-20_013426.dump`) y su bitacora en `08_logs/`. Script: `B2_fusion_atletas.sql`; pares: `datos/pares_aprobados.csv` (394 filas);
auditoria: `06_validacion/b2_auditoria_alta.csv` (103 filas de verificacion contra Wikipedia, 102 pares distintos: Shun Wang figura dos veces, no verificable y luego correcto).

**Causa.** La fuente 3 escribe algunos nombres en otro orden ("Shiyu Lu" frente a "Lu Shiyu" de la fuente 1),
trunca nombres compuestos ("Kate Foo" frente a "Kate Foo Kune") o pierde el apellido tras una particula
("van Sharon"). El emparejamiento por nombre del ETL no los reconocio y quedaron como atletas distintos, con
la historia dividida (por ejemplo, las medallas de Paris 2024 de Summer McIntosh estaban en otro registro).

**Tecnica.** Se conserva el `atleta_id` del registro historico, se mueven las participaciones, se elimina el
duplicado y se registra la fusion en la tabla `atleta_fusion_log` (id duplicado y conservado, tipo, confianza,
evidencia, fecha, nombre original, fila completa del duplicado y `participacion_id` movidos). Se puede deshacer
una fusion, un tipo completo o todo con `B2_deshacer_fusion.sql` (probado). Las colisiones (mismo evento y
edicion en ambos registros) se reportan en `atleta_fusion_colision` y el par se excluye: hubo 0.

| Fase | Tipo | Fusiones |
|---|---|---:|
| 1 | Orden invertido | 176 |
| 1 | Particulas | 1 |
| 1 | Manual (Sharon van Rouwendaal, 152796 a 123522) | 1 |
| 2 | Subconjunto (nombre truncado) | 215 |
| 3 | Excepcion verificada individualmente (Shun Wang, 151102, a Wang Shun, 120437; 2026-10-20) | 1 |
| | **Total** | **394** |

| Dato | Antes de B2 (despues de B1) | Despues de B2 | Cambio |
|---|---:|---:|---:|
| atleta | 153,443 | **153,049** | -394 |
| participacion | 319,961 | 319,961 | 0 |
| resultado | 320,476 | 320,476 | 0 |
| Alemania, oro / plata / bronce | 1,357 / 1,303 / 1,331 | 1,357 / 1,303 / 1,331 | 0 |
| Rusia, oro / plata / bronce | 1,575 / 1,135 / 1,158 | 1,575 / 1,135 / 1,158 | 0 |
| Sedes Estados Unidos / Francia / Guatemala | 8 / 6 / 0 | 8 / 6 / 0 | 0 |

La linea base de paises (medalleros y sedes) no se movio. Participaciones y resultados solo cambian de dueno.

**Linea base vigente para validar.** `06_validacion/linea_base_fase3.json` (atleta 153,049; participacion 319,961;
resultado 320,476; Alemania 1,357 / 1,303 / 1,331). Se puede reproducir con
`python linea_base.py --referencia fase3`. La linea base original de la Fase 1 sigue en `linea_base_fase1.json`.

**Alias para MongoDB.** `atleta_fusion_log.nombre_original_duplicado` conserva los 394 nombres originales de los
duplicados; el exportador los incluira en `alias[]`, `tokens` y la busqueda.
