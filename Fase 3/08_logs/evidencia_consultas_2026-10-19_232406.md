# Evidencia de consultas (Fase E1)

Ejecutado el 2026-10-19 23:24:06. Cada consulta se corre una vez para calentar y otra para medir.
Tiempo MongoDB = consultas al servidor; tiempo del proceso incluye el arranque de Python.

## 1. Atleta conocido

`python atleta.py 'Michael Phelps' --explain`  
Estado: **OK**, MongoDB 5.9 ms, total 11.5 ms, proceso completo 965 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 2. Atleta conocido con medallas recientes

`python atleta.py 'Summer McIntosh' --explain`  
Estado: **OK**, MongoDB 4.6 ms, total 9.1 ms, proceso completo 977 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 3. Atleta fusionado (busqueda por alias)

`python atleta.py 'Shiyu Lu' --explain`  
Estado: **OK**, MongoDB 4.1 ms, total 8.7 ms, proceso completo 969 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 4. Homonimos (modo CANDIDATO)

`python atleta.py 'Jack Robinson' --explain`  
Estado: **OK**, MongoDB 2.5 ms, total 4.9 ms, proceso completo 958 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 2, documentos examinados 2, devueltos 2, 0 ms en el servidor
```

## 5. Homonimos (modo CANDIDATO)

`python atleta.py 'Jordan Thompson' --explain`  
Estado: **OK**, MongoDB 2.5 ms, total 5.0 ms, proceso completo 931 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 2, documentos examinados 2, devueltos 2, 0 ms en el servidor
```

## 6. Atleta con filtros combinados

`python atleta.py 'Pawel Fajdek' --deporte Athletics --anio 2024 --explain`  
Estado: **OK**, MongoDB 4.2 ms, total 8.9 ms, proceso completo 962 ms

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 7. Pais grande, resumen

`python pais.py 'United States' --explain`  
Estado: **OK**, MongoDB 2.9 ms, total 5.9 ms, proceso completo 1225 ms

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 8. Pais multi-NOC, resumen

`python pais.py Germany --explain`  
Estado: **OK**, MongoDB 3.4 ms, total 6.5 ms, proceso completo 1002 ms

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
```

## 9. Pais grande, detalle paginado

`python pais.py 'Russian Federation' --detalle --tam 30 --explain`  
Estado: **OK**, MongoDB 12.4 ms, total 17.3 ms, proceso completo 955 ms

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle paginado] plan: LIMIT > FETCH > IXSCAN(pais_id_1_es_yog_1_anio_1_deporte_1) | indices examinados 30, documentos examinados 30, devueltos 30, 0 ms en el servidor
```

## 10. Pais con filtros combinados, detalle

`python pais.py Germany --anio 1972 --deporte Athletics --detalle --explain`  
Estado: **OK**, MongoDB 16.8 ms, total 25.8 ms, proceso completo 957 ms

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain resumen anio+deporte] plan: PROJECTION_DEFAULT > FETCH > IXSCAN(pais_id_1_es_yog_1_anio_1_deporte_1) | indices examinados 188, documentos examinados 188, devueltos 188, 1 ms en el servidor
[explain detalle paginado] plan: LIMIT > FETCH > IXSCAN(pais_id_1_es_yog_1_anio_1_deporte_1) | indices examinados 40, documentos examinados 40, devueltos 40, 0 ms en el servidor
```

## Resumen

| # | Consulta | Comando | Estado | MongoDB (ms) | Total con formato (ms) | Proceso (ms) |
|---|---|---|---|---:|---:|---:|
| 1 | Atleta conocido | `atleta.py Michael Phelps` | OK | 5.9 | 11.5 | 965 |
| 2 | Atleta conocido con medallas recientes | `atleta.py Summer McIntosh` | OK | 4.6 | 9.1 | 977 |
| 3 | Atleta fusionado (busqueda por alias) | `atleta.py Shiyu Lu` | OK | 4.1 | 8.7 | 969 |
| 4 | Homonimos (modo CANDIDATO) | `atleta.py Jack Robinson` | OK | 2.5 | 4.9 | 958 |
| 5 | Homonimos (modo CANDIDATO) | `atleta.py Jordan Thompson` | OK | 2.5 | 5.0 | 931 |
| 6 | Atleta con filtros combinados | `atleta.py Pawel Fajdek --deporte Athletics --anio 2024` | OK | 4.2 | 8.9 | 962 |
| 7 | Pais grande, resumen | `pais.py United States` | OK | 2.9 | 5.9 | 1225 |
| 8 | Pais multi-NOC, resumen | `pais.py Germany` | OK | 3.4 | 6.5 | 1002 |
| 9 | Pais grande, detalle paginado | `pais.py Russian Federation --detalle --tam 30` | OK | 12.4 | 17.3 | 955 |
| 10 | Pais con filtros combinados, detalle | `pais.py Germany --anio 1972 --deporte Athletics --detalle` | OK | 16.8 | 25.8 | 957 |
