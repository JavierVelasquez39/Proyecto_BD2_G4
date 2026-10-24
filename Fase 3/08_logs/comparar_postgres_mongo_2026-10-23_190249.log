# Comparacion cruzada Postgres vs MongoDB

Ejecutada el 2026-10-23 19:02:49 (fin 19:04:15, 85 s). Postgres: `fn_atleta_info` y `fn_pais_info` de la Fase 1 sobre la base corregida; MongoDB: `atleta.py` y `pais.py` ejecutados como procesos.
Se comparan modo, candidatos, participaciones (fila por fila en atletas), medallas por atleta, medallas por evento (calculadas en Postgres como medallas distintas por edicion, evento y NOC a partir de las filas de participacion), NOC y sedes.

**Resultado: 38 iguales, 4 con diferencia esperada por diseno, 0 diferencias no esperadas** de 42 entradas.

| # | Consulta | Postgres | MongoDB | Resultado | MongoDB (ms) |
|---|---|---|---|---|---:|
| 1 | atleta.py `Michael Phelps`  | DETALLE id 93113, 30 part., medallas 23/3/2 | DETALLE id 93113, 30 part., medallas 23/3/2 | IGUAL | 5.3 |
| 2 | atleta.py `Usain Bolt`  | DETALLE id 104492, 10 part., medallas 8/0/0 | DETALLE id 104492, 10 part., medallas 8/0/0 | IGUAL | 6.9 |
| 3 | atleta.py `Simone Biles`  | DETALLE id 129489, 19 part., medallas 7/2/2 | DETALLE id 129489, 19 part., medallas 7/2/2 | IGUAL | 7.4 |
| 4 | atleta.py `Katie Ledecky`  | DETALLE id 124356, 15 part., medallas 9/4/1 | DETALLE id 124356, 15 part., medallas 9/4/1 | IGUAL | 8.0 |
| 5 | atleta.py `Pawel Fajdek`  | DETALLE id 120119, 4 part., medallas 0/0/1 | DETALLE id 120119, 4 part., medallas 0/0/1 | IGUAL | 7.4 |
| 6 | atleta.py `Summer McIntosh`  | DETALLE id 138069, 11 part., medallas 3/1/0 | DETALLE id 138069, 11 part., medallas 3/1/0 | IGUAL | 5.2 |
| 7 | atleta.py `Shun Wang`  | SIN_COINCIDENCIAS | DETALLE id 120437, 7 part., medallas 1/0/2 | DIFERENCIA ESPERADA | 6.2 |
| 8 | atleta.py `Wang Shun`  | DETALLE id 120437, 7 part., medallas 1/0/2 | DETALLE id 120437, 7 part., medallas 1/0/2 | IGUAL | 7.1 |
| 9 | atleta.py `Jack Robinson`  | CANDIDATO 2 atletas | CANDIDATO 2 atletas | IGUAL | 3.1 |
| 10 | atleta.py `Jordan Thompson`  | CANDIDATO 2 atletas | CANDIDATO 2 atletas | IGUAL | 3.9 |
| 11 | atleta.py `Jack Robinson` --id 6939 | DETALLE id 6939, 1 part., medallas 1/0/0 | DETALLE id 6939, 1 part., medallas 1/0/0 | IGUAL | 6.7 |
| 12 | atleta.py `Lotte Kopecky`  | DETALLE id 126762, 9 part., medallas 0/0/1 | DETALLE id 126762, 9 part., medallas 0/0/1 | IGUAL | 8.4 |
| 13 | atleta.py `Kristen Faulkner`  | DETALLE id 151806, 2 part., medallas 1/0/0 | DETALLE id 151806, 2 part., medallas 1/0/0 | IGUAL | 7.9 |
| 14 | atleta.py `Sharon van Rouwendaal`  | DETALLE id 123522, 11 part., medallas 2/1/0 | DETALLE id 123522, 11 part., medallas 2/1/0 | IGUAL | 11.2 |
| 15 | atleta.py `Shiyu Lu`  | SIN_COINCIDENCIAS | DETALLE id 138342, 2 part., medallas 0/0/0 | DIFERENCIA ESPERADA | 5.2 |
| 16 | atleta.py `van Sharon`  | SIN_COINCIDENCIAS | DETALLE id 123522, 11 part., medallas 2/1/0 | DIFERENCIA ESPERADA | 9.0 |
| 17 | atleta.py `Kate Foo`  | DETALLE id 128566, 2 part., medallas 0/0/0 | DETALLE id 128566, 2 part., medallas 0/0/0 | IGUAL | 5.7 |
| 18 | atleta.py `Mariana Avitia`  | DETALLE id 110277, 3 part., medallas 0/0/1 | DETALLE id 110277, 3 part., medallas 0/0/1 | IGUAL | 6.7 |
| 19 | atleta.py `Mariana Avitia` --incluir-yog | DETALLE id 110277, 5 part., medallas 0/0/1 | DETALLE id 110277, 5 part., medallas 0/0/1 | IGUAL | 4.8 |
| 20 | atleta.py `Michael Phelps` --deporte Swimming (Aquatics) --anio 2008 | DETALLE id 93113, 8 part., medallas 8/0/0 | DETALLE id 93113, 8 part., medallas 8/0/0 | IGUAL | 12.0 |
| 21 | atleta.py `Katie Ledecky` --pais United States | DETALLE id 124356, 15 part., medallas 9/4/1 | DETALLE id 124356, 15 part., medallas 9/4/1 | IGUAL | 12.4 |
| 22 | atleta.py `Pawel Fajdek` --deporte Athletics --anio 2024 | DETALLE id 120119, 1 part., medallas 0/0/0 | DETALLE id 120119, 1 part., medallas 0/0/0 | IGUAL | 8.4 |
| 23 | atleta.py `Fajdek`  | DETALLE id 120119, 4 part., medallas 0/0/1 | DETALLE id 120119, 4 part., medallas 0/0/1 | IGUAL | 10.0 |
| 24 | atleta.py `Nadie Inexistente`  | SIN_COINCIDENCIAS | SIN_COINCIDENCIAS | IGUAL | 43.2 |
| 25 | pais.py `Germany`  | 4 NOC, por atleta 1357/1303/1331, por evento 615/622/615, sedes 3, 17531 part. | 4 NOC, por atleta 1357/1303/1331, por evento 615/622/615, sedes 3 | IGUAL | 3.2 |
| 26 | pais.py `Russian Federation`  | 3 NOC, por atleta 1575/1135/1158, por evento 719/586/578, sedes 2, 11844 part. | 3 NOC, por atleta 1575/1135/1158, por evento 719/586/578, sedes 2 | IGUAL | 5.5 |
| 27 | pais.py `United States`  | 1 NOC, por atleta 2826/1873/1544, por evento 1219/1001/880, sedes 8, 21615 part. | 1 NOC, por atleta 2826/1873/1544, por evento 1219/1001/880, sedes 8 | IGUAL | 4.5 |
| 28 | pais.py `France`  | 1 NOC, por atleta 611/749/726, por evento 284/322/357, sedes 6, 14492 part. | 1 NOC, por atleta 611/749/726, por evento 284/322/357, sedes 6 | IGUAL | 4.9 |
| 29 | pais.py `Guatemala` --detalle | 1 NOC, por atleta 1/1/1, por evento 1/1/1, sedes nunca, 470 part. | 1 NOC, por atleta 1/1/1, por evento 1/1/1, sedes nunca, 470 part. | IGUAL | 100.1 |
| 30 | pais.py `China`  | 2 NOC, por atleta 488/475/386, por evento 325/258/226, sedes 2, 7561 part. | 2 NOC, por atleta 488/475/386, por evento 325/258/226, sedes 2 | IGUAL | 4.7 |
| 31 | pais.py `Japan`  | 1 NOC, por atleta 350/395/421, por evento 204/189/219, sedes 4, 10296 part. | 1 NOC, por atleta 350/395/421, por evento 204/189/219, sedes 4 | IGUAL | 2.9 |
| 32 | pais.py `Czechia`  | 3 NOC, por atleta 135/267/272, por evento 83/90/105, sedes nunca, 7275 part. | 3 NOC, por atleta 135/267/272, por evento 83/90/105, sedes nunca | IGUAL | 5.1 |
| 33 | pais.py `Serbia`  | 3 NOC, por atleta 188/223/190, por evento 37/44/44, sedes nunca, 3605 part. | 3 NOC, por atleta 188/223/190, por evento 37/44/44, sedes nunca | IGUAL | 3.1 |
| 34 | pais.py `Mexico`  | 1 NOC, por atleta 30/30/84, por evento 13/27/38, sedes 1, 3326 part. | 1 NOC, por atleta 30/30/84, por evento 13/27/38, sedes 1 | IGUAL | 3.5 |
| 35 | pais.py `Germany` --anio 1972 | 4 NOC, por atleta 83/84/108, por evento 40/38/47, sedes 3, 1253 part. | 4 NOC, por atleta 83/84/108, por evento 40/38/47, sedes 1 | IGUAL | 3.9 |
| 36 | pais.py `Germany` --anio 1972 --detalle | 4 NOC, por atleta 83/84/108, por evento 40/38/47, sedes 3, 1253 part. | 4 NOC, por atleta 83/84/108, por evento 40/38/47, sedes 1, 1253 part. | IGUAL | 94.4 |
| 37 | pais.py `Serbia` --detalle | 3 NOC, por atleta 188/223/190, por evento 37/44/44, sedes nunca, 3605 part. | 3 NOC, por atleta 188/223/190, por evento 37/44/44, sedes nunca, 3605 part. | IGUAL | 168.5 |
| 38 | pais.py `Germany` --incluir-yog | 4 NOC, por atleta 1374/1320/1349, por evento 629/635/630, sedes 3, 17773 part. | 4 NOC, por atleta 1374/1320/1349, por evento 629/635/630, sedes 3 | IGUAL | 3.8 |
| 39 | pais.py `United States` --anio 2024 --deporte Swimming (Aquatics) | 1 NOC, por atleta 27/36/7, por evento 8/13/7, sedes 8, 113 part. | 1 NOC, por atleta 27/36/7, por evento 8/13/7, sedes 0 | IGUAL | 25.2 |
| 40 | pais.py `France` --deporte Fencing | 1 NOC, por atleta 130/105/97, por evento 46/47/38, sedes 6, 1079 part. | 1 NOC, por atleta 130/105/97, por evento 46/47/38, sedes 6 | IGUAL | 3.4 |
| 41 | pais.py `Taiwan`  | PAIS_NO_ENCONTRADO | 1 NOC, por atleta 8/33/25, por evento 6/11/21, sedes 0 | DIFERENCIA ESPERADA | 3.0 |
| 42 | pais.py `Wakanda`  | PAIS_NO_ENCONTRADO | PAIS_NO_ENCONTRADO | IGUAL | 13.4 |

## Detalle de las diferencias

**7. atleta.py `Shun Wang` ** (esperada: alias de un atleta fusionado (fase 3): solo MongoDB lo resuelve)
- modo: Postgres SIN_COINCIDENCIAS / MongoDB DETALLE
**15. atleta.py `Shiyu Lu` ** (esperada: alias de un atleta fusionado: solo MongoDB lo resuelve (la funcion de Postgres busca nombre usado y completo))
- modo: Postgres SIN_COINCIDENCIAS / MongoDB DETALLE
**16. atleta.py `van Sharon` ** (esperada: alias de un atleta fusionado: solo MongoDB lo resuelve)
- modo: Postgres SIN_COINCIDENCIAS / MongoDB DETALLE
**41. pais.py `Taiwan` ** (esperada: entidad sin pais (NOC TPE): MongoDB la ofrece como entidad; la funcion de Postgres responde PAIS_NO_ENCONTRADO)
- modo: Postgres PAIS_NO_ENCONTRADO / MongoDB PAIS
