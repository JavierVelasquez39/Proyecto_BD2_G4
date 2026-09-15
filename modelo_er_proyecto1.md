# Modelo ER: Proyecto Olimpiadas (Sistemas BD2)

> Referencia compacta del diagrama ER (drawio) para usar en el resto de tareas del proyecto.

## Entidades (formato: `tabla(atributo PK, atributo, atributo FK→tabla_referenciada)`)

```
PAIS(pais_id PK, nombre)

POBLACION_PAIS(poblacion_id PK, pais_id FK→PAIS, anio, cantidad)

NOC(codigo_noc PK, nombre_region, notas, pais_id FK→PAIS NULLABLE)

SEDE(sede_id PK, ciudad, pais_id FK→PAIS)

ATLETA(atleta_id PK, nombre_completo, nombre_usado, sexo, nacionalidad,
       fecha_nacimiento, ciudad_nacimiento, pais_nacimiento, fecha_fallecimiento)

EDICION_OLIMPICA(edicion_id PK, anio, tipo, sede_id FK→SEDE)

DEPORTE(deporte_id PK, nombre, descripcion)

EVENTO(evento_id PK, nombre, deporte_id FK→DEPORTE)

PARTICIPACION(participacion_id PK, atleta_id FK→ATLETA, edicion_id FK→EDICION_OLIMPICA,
              evento_id FK→EVENTO, codigo_noc FK→NOC, equipo, edad, altura_cm, peso_kg)

RESULTADO(resultado_id PK, participacion_id FK→PARTICIPACION, lugar, empatado, medalla)
```

## Relaciones (cardinalidad 1:N salvo que se indique otra cosa)

| Padre (1) | Hijo (N) | FK en hijo | Nota |
|---|---|---|---|
| PAIS | POBLACION_PAIS | pais_id | población histórica por año |
| PAIS | NOC | pais_id | un país puede tener uno o más comités olímpicos |
| PAIS | SEDE | pais_id | ciudades sede pertenecen a un país |
| NOC | ATLETA | *(no existe, a propósito)* | **Resuelto** (ver `DECISIONES.md`): no hay FK NOC→ATLETA porque un atleta puede competir bajo varios NOC a lo largo de su carrera. Confirmado empíricamente contra `results.csv` (fuente 1): 1,834 atletas cargados compitieron bajo más de un `codigo_noc` distinto. El vínculo vive solo en `PARTICIPACION.codigo_noc`. |
| NOC | PARTICIPACION | codigo_noc | comité con el que compitió el atleta en esa participación |
| SEDE | EDICION_OLIMPICA | sede_id | ciudad/sede de una edición de juegos. **Poblada con `City` real de fuente 2 (1896–2016) y fuente 3 (2024) para 52 de las 55 ediciones (95%)**; las 3 restantes (2018 Invierno, 2020 Verano, 2022 Invierno) siguen tomando ciudad/país de `reference_editions.csv` (armado a mano) porque ninguna fuente real trae `City` para esos años. Es **reemplazo parcial, no total**. Ver `DECISIONES.md`. |
| ATLETA | PARTICIPACION | atleta_id | historial de participaciones de un atleta |
| EDICION_OLIMPICA | PARTICIPACION | edicion_id | participaciones dentro de una edición |
| DEPORTE | EVENTO | deporte_id | un deporte agrupa varios eventos |
| EVENTO | PARTICIPACION | evento_id | evento específico en el que compitió el atleta |
| PARTICIPACION | RESULTADO | participacion_id | resultado(s)/medalla obtenida en esa participación. **Cardinalidad 1:N confirmada con datos reales**, no solo teórica: en la carga de fuente 1 hay 428 participaciones (ej. Polo 1900, equipos compuestos/mixtos sin columna de ronda en la fuente) con más de un resultado, hasta 12 resultados para una misma participación. Ver `DECISIONES.md`. |

## Notas de diseño a tener presentes

- **PARTICIPACION** es la entidad "puente" central: conecta ATLETA, EDICION_OLIMPICA, EVENTO y NOC. Ahí se guardan atributos que varían por participación (equipo, edad, altura, peso).
- **RESULTADO** separa el resultado/medalla de la participación (permite múltiples resultados o desempates, campo `empatado`). Esto no es solo una posibilidad teórica del modelo: la carga real de fuente 1 la ejercita (428 participaciones con múltiples resultados, caso Polo 1900 como ejemplo documentado en `DECISIONES.md`).
- **EDICION_OLIMPICA** distingue `tipo` (Verano/Invierno). El modelo actual no distingue Juegos Olímpicos de la Juventud (YOG); fuente 1 sí los incluye mezclados con los Juegos regulares, y se excluyen de la carga hasta nueva decisión. **Pendiente de confirmar con el profesor** (ver `DECISIONES.md`).
- **NOC↔ATLETA:** resuelto, ver tabla de relaciones arriba y `DECISIONES.md`.
- **DEPORTE/EVENTO:** fuente 1 y fuente 3 nombran los mismos deportes/eventos con convenciones de texto distintas (ej. "Javelin Throw, Men (Olympic)" vs "Men's Javelin Throw"). Una auditoría sistemática (2026-09-13) encontró ~133 eventos y 2 deportes (Equestrian, Trampoline Gymnastics) que habrían quedado duplicados de no normalizarse; se implementó una canonicalización que reutiliza el `evento_id`/`deporte_id` existente cuando la forma normalizada calza exacto. Aun así, 199 eventos de 2024 quedan como filas nuevas (mezcla de eventos genuinamente nuevos y variantes de redacción no resueltas). Ver `DECISIONES.md`.
