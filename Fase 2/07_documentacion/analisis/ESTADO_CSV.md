# Estado de los CSV de tiempos

Generado por `analizar.py`. Criterios: encabezado de 14 columnas de la sección 4.10, 53 líneas, 14 campos por línea, UTF-8 sin BOM, LF, 0 filas con ALERTA y `paso` de dos dígitos leído como texto.

| Archivo | Estado | Motivo |
|---|---|---|
| `tiempos_anio_pa.csv` | excluido | el encabezado no es el de 14 columnas de la 4.10; tiene 20 líneas y se esperan 53; 4 líneas no tienen 14 campos (líneas 1, 2, 3, 4) |
| `tiempos_deportista_pc.csv` | válido |  |
| `tiempos_deporte_pb.csv` | no existe | [PENDIENTE] |
