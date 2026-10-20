# Evidencia de consultas (Fase E1)

Ejecutado el 2026-10-20 01:01:51. Cada consulta se corre una vez para calentar y otra para medir.
Tiempo MongoDB = consultas al servidor; tiempo del proceso incluye el arranque de Python.

## 1. Atleta conocido

`python atleta.py 'Michael Phelps' --explain`  
Estado: **OK**, MongoDB 4.6 ms, total 9.3 ms, proceso completo 1026 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 2. Atleta conocido con medallas recientes

`python atleta.py 'Summer McIntosh' --explain`  
Estado: **OK**, MongoDB 4.4 ms, total 8.7 ms, proceso completo 1025 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 3. Atleta fusionado (busqueda por alias)

`python atleta.py 'Shiyu Lu' --explain`  
Estado: **OK**, MongoDB 4.6 ms, total 8.9 ms, proceso completo 981 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 4. Homonimos (modo CANDIDATO)

`python atleta.py 'Jack Robinson' --explain`  
Estado: **OK**, MongoDB 2.2 ms, total 5.1 ms, proceso completo 1002 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 2, documentos examinados 2, devueltos 2, 0 ms en el servidor
```

## 5. Homonimos (modo CANDIDATO)

`python atleta.py 'Jordan Thompson' --explain`  
Estado: **OK**, MongoDB 3.0 ms, total 6.4 ms, proceso completo 987 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 2, documentos examinados 2, devueltos 2, 0 ms en el servidor
```

## 6. Atleta con filtros combinados

`python atleta.py 'Pawel Fajdek' --deporte Athletics --anio 2024 --explain`  
Estado: **OK**, MongoDB 5.2 ms, total 10.8 ms, proceso completo 1093 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 7. Pais grande, resumen

`python pais.py 'United States' --explain`  
Estado: **OK**, MongoDB 2.8 ms, total 5.3 ms, proceso completo 1036 ms

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 8. Pais multi-NOC, resumen

`python pais.py Germany --explain`  
Estado: **OK**, MongoDB 2.7 ms, total 5.4 ms, proceso completo 999 ms

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 9. Pais grande, detalle paginado

`python pais.py 'Russian Federation' --detalle --tam 30 --explain`  
Estado: **OK**, MongoDB 14.1 ms, total 19.8 ms, proceso completo 1017 ms

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle paginado] plan: LIMIT > FETCH > IXSCAN(pais_id_1_es_yog_1_anio_1_deporte_1) | indices examinados 30, documentos examinados 30, devueltos 30, 0 ms en el servidor
```

## 10. Pais con filtros combinados, detalle

`python pais.py Germany --anio 1972 --deporte Athletics --detalle --explain`  
Estado: **OK**, MongoDB 14.5 ms, total 23.5 ms, proceso completo 993 ms

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain resumen anio+deporte] plan: PROJECTION_DEFAULT > FETCH > IXSCAN(pais_id_1_es_yog_1_anio_1_deporte_1) | indices examinados 188, documentos examinados 188, devueltos 188, 1 ms en el servidor
[explain detalle paginado] plan: LIMIT > FETCH > IXSCAN(pais_id_1_es_yog_1_anio_1_deporte_1) | indices examinados 40, documentos examinados 40, devueltos 40, 0 ms en el servidor
```

## Resumen

| # | Consulta | Comando | Estado | MongoDB (ms) | Total con formato (ms) | Proceso (ms) |
|---|---|---|---|---:|---:|---:|
| 1 | Atleta conocido | `atleta.py Michael Phelps` | OK | 4.6 | 9.3 | 1026 |
| 2 | Atleta conocido con medallas recientes | `atleta.py Summer McIntosh` | OK | 4.4 | 8.7 | 1025 |
| 3 | Atleta fusionado (busqueda por alias) | `atleta.py Shiyu Lu` | OK | 4.6 | 8.9 | 981 |
| 4 | Homonimos (modo CANDIDATO) | `atleta.py Jack Robinson` | OK | 2.2 | 5.1 | 1002 |
| 5 | Homonimos (modo CANDIDATO) | `atleta.py Jordan Thompson` | OK | 3.0 | 6.4 | 987 |
| 6 | Atleta con filtros combinados | `atleta.py Pawel Fajdek --deporte Athletics --anio 2024` | OK | 5.2 | 10.8 | 1093 |
| 7 | Pais grande, resumen | `pais.py United States` | OK | 2.8 | 5.3 | 1036 |
| 8 | Pais multi-NOC, resumen | `pais.py Germany` | OK | 2.7 | 5.4 | 999 |
| 9 | Pais grande, detalle paginado | `pais.py Russian Federation --detalle --tam 30` | OK | 14.1 | 19.8 | 1017 |
| 10 | Pais con filtros combinados, detalle | `pais.py Germany --anio 1972 --deporte Athletics --detalle` | OK | 14.5 | 23.5 | 993 |
