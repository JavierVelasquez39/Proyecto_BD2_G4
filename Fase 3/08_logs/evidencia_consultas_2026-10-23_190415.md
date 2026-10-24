# Evidencia de consultas (Fase E1)

Ejecutado el 2026-10-23 19:04:15. Cada consulta se corre una vez para calentar y otra para medir.
Tiempo MongoDB = consultas al servidor; tiempo del proceso incluye el arranque de Python.

## 1. Atleta conocido

`python atleta.py 'Michael Phelps' --explain`  
Estado: **OK**, MongoDB 5.9 ms, total 13.0 ms, proceso completo 1135 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 2. Atleta conocido con medallas recientes

`python atleta.py 'Summer McIntosh' --explain`  
Estado: **OK**, MongoDB 5.7 ms, total 11.8 ms, proceso completo 1170 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 3. Atleta fusionado (busqueda por alias)

`python atleta.py 'Shiyu Lu' --explain`  
Estado: **OK**, MongoDB 5.2 ms, total 10.1 ms, proceso completo 1033 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 4. Homonimos (modo CANDIDATO)

`python atleta.py 'Jack Robinson' --explain`  
Estado: **OK**, MongoDB 2.3 ms, total 4.5 ms, proceso completo 1025 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 2, documentos examinados 2, devueltos 2, 0 ms en el servidor
```

## 5. Homonimos (modo CANDIDATO)

`python atleta.py 'Jordan Thompson' --explain`  
Estado: **OK**, MongoDB 2.8 ms, total 5.2 ms, proceso completo 1071 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 2, documentos examinados 2, devueltos 2, 0 ms en el servidor
```

## 6. Atleta con filtros combinados

`python atleta.py 'Pawel Fajdek' --deporte Athletics --anio 2024 --explain`  
Estado: **OK**, MongoDB 8.0 ms, total 16.2 ms, proceso completo 1510 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 1 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 7. Pais grande, resumen

`python pais.py 'United States' --explain`  
Estado: **OK**, MongoDB 3.1 ms, total 6.4 ms, proceso completo 1206 ms

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 8. Pais multi-NOC, resumen

`python pais.py Germany --explain`  
Estado: **OK**, MongoDB 6.4 ms, total 13.9 ms, proceso completo 1495 ms

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 9. Pais grande, detalle paginado

`python pais.py 'Russian Federation' --detalle --tam 30 --explain`  
Estado: **OK**, MongoDB 15.2 ms, total 24.7 ms, proceso completo 1106 ms

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle paginado] plan: LIMIT > FETCH > IXSCAN(pais_id_1_es_yog_1_anio_1_deporte_1) | indices examinados 30, documentos examinados 30, devueltos 30, 2 ms en el servidor
```

## 10. Pais con filtros combinados, detalle

`python pais.py Germany --anio 1972 --deporte Athletics --detalle --explain`  
Estado: **OK**, MongoDB 18.1 ms, total 34.4 ms, proceso completo 1462 ms

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain resumen anio+deporte] plan: PROJECTION_DEFAULT > FETCH > IXSCAN(pais_id_1_es_yog_1_anio_1_deporte_1) | indices examinados 188, documentos examinados 188, devueltos 188, 3 ms en el servidor
[explain detalle paginado] plan: LIMIT > FETCH > IXSCAN(pais_id_1_es_yog_1_anio_1_deporte_1) | indices examinados 40, documentos examinados 40, devueltos 40, 0 ms en el servidor
```

## Resumen

| # | Consulta | Comando | Estado | MongoDB (ms) | Total con formato (ms) | Proceso (ms) |
|---|---|---|---|---:|---:|---:|
| 1 | Atleta conocido | `atleta.py Michael Phelps` | OK | 5.9 | 13.0 | 1135 |
| 2 | Atleta conocido con medallas recientes | `atleta.py Summer McIntosh` | OK | 5.7 | 11.8 | 1170 |
| 3 | Atleta fusionado (busqueda por alias) | `atleta.py Shiyu Lu` | OK | 5.2 | 10.1 | 1033 |
| 4 | Homonimos (modo CANDIDATO) | `atleta.py Jack Robinson` | OK | 2.3 | 4.5 | 1025 |
| 5 | Homonimos (modo CANDIDATO) | `atleta.py Jordan Thompson` | OK | 2.8 | 5.2 | 1071 |
| 6 | Atleta con filtros combinados | `atleta.py Pawel Fajdek --deporte Athletics --anio 2024` | OK | 8.0 | 16.2 | 1510 |
| 7 | Pais grande, resumen | `pais.py United States` | OK | 3.1 | 6.4 | 1206 |
| 8 | Pais multi-NOC, resumen | `pais.py Germany` | OK | 6.4 | 13.9 | 1495 |
| 9 | Pais grande, detalle paginado | `pais.py Russian Federation --detalle --tam 30` | OK | 15.2 | 24.7 | 1106 |
| 10 | Pais con filtros combinados, detalle | `pais.py Germany --anio 1972 --deporte Athletics --detalle` | OK | 18.1 | 34.4 | 1462 |
