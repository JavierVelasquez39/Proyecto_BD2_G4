# Guion de calificacion

Comandos listos para copiar y salida esperada (resumida), ejecutados el 2026-10-20 01:37:41. Se corren desde la carpeta `Fase 3/` con MongoDB arriba (`docker compose -f 00_infraestructura/docker-compose.yml up -d`). Los tiempos son los de MongoDB (las consultas); el proceso completo de Python tarda cerca de 1 s en arrancar. Antes de empezar conviene correr una vez `python 07_consultas/evidencia_consultas.py` para calentar la cache.

Reglas utiles: el nombre del pais va en ingles (convencion del Banco Mundial, "Russian Federation"); el deporte se escribe completo ("Swimming (Aquatics)"); la busqueda ignora acentos y mayusculas; los YOG solo salen con `--incluir-yog`; las medallas se muestran siempre como **por atleta** (criterio de la Fase 1) y **por evento** (oficial).

## 1. Atleta conocido

Detalle completo de un atleta: datos, medallas por atleta, participaciones y resultados desde un solo documento.

```
python 07_consultas/atleta.py "Michael Phelps"
```

Salida esperada (resumida):

```
MODO: DETALLE | atleta_id 93113
Medallas por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 23 / plata 3 / bronce 2
   desglose: sin YOG oro 23 / plata 3 / bronce 2 | YOG oro 0 / plata 0 / bronce 0
Participaciones: 30
2000  Verano      Sydney         Swimming (Aquatics)    200 metres Butterfly, Men (Olympic)      USA                 5      
2004  Verano      Athina         Swimming (Aquatics)    100 metres Butterfly, Men (Olympic)      USA                 1      Oro
2004  Verano      Athina         Swimming (Aquatics)    200 metres Butterfly, Men (Olympic)      USA                 1      Oro
Tiempo de respuesta: consultas a MongoDB 6.8 ms | total con formato 7.3 ms
```

## 2. Atleta con filtros de deporte y anio

Filtros combinados; se usa el nombre completo del deporte.

```
python 07_consultas/atleta.py "Michael Phelps" --deporte "Swimming (Aquatics)" --anio 2008
```

Salida esperada (resumida):

```
MODO: DETALLE | atleta_id 93113
Medallas (participaciones mostradas) por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 8 / plata 0 / bronce 0
Participaciones: 8
2008  Verano      Beijing        Swimming (Aquatics)    100 metres Butterfly, Men (Olympic)      USA                 1      Oro
2008  Verano      Beijing        Swimming (Aquatics)    200 metres Butterfly, Men (Olympic)      USA                 1      Oro
2008  Verano      Beijing        Swimming (Aquatics)    200 metres Freestyle, Men (Olympic)      USA                 1      Oro
Tiempo de respuesta: consultas a MongoDB 5.0 ms | total con formato 5.3 ms
```

## 3. Atleta con filtro de pais

El filtro de pais usa todos los NOC historicos del pais.

```
python 07_consultas/atleta.py "Katie Ledecky" --pais "United States"
```

Salida esperada (resumida):

```
MODO: DETALLE | atleta_id 124356
Medallas (participaciones mostradas) por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 9 / plata 4 / bronce 1
Participaciones: 15
2012  Verano      London         Swimming (Aquatics)    800 metres Freestyle, Women (Olympic)    USA                 1      Oro
2016  Verano      Rio de Janeiro Swimming (Aquatics)    200 metres Freestyle, Women (Olympic)    USA                 1      Oro
2016  Verano      Rio de Janeiro Swimming (Aquatics)    400 metres Freestyle, Women (Olympic)    USA                 1      Oro
Tiempo de respuesta: consultas a MongoDB 6.5 ms | total con formato 6.8 ms
```

## 4. Atleta con medallas de Paris 2024

Muestra las medallas de Paris que estaban repartidas en dos registros antes de la fusion.

```
python 07_consultas/atleta.py "Summer McIntosh"
```

Salida esperada (resumida):

```
MODO: DETALLE | atleta_id 138069
Alias (nombres con que aparecia en otra fuente): McINTOSH Summer
Medallas por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 3 / plata 1 / bronce 0
   desglose: sin YOG oro 3 / plata 1 / bronce 0 | YOG oro 0 / plata 0 / bronce 0
Participaciones: 11
2020  Verano      Tokyo          Swimming (Aquatics)    200 metres Freestyle, Women (Olympic)    CAN                 9      
2020  Verano      Tokyo          Swimming (Aquatics)    400 metres Freestyle, Women (Olympic)    CAN                 4      
2020  Verano      Tokyo          Swimming (Aquatics)    4 × 200 metres Freestyle Relay, Women (~ CAN  Canada         4      
Tiempo de respuesta: consultas a MongoDB 6.2 ms | total con formato 6.5 ms
```

## 5. Atleta corregido (medalla que faltaba en la fuente)

El oro de ruta de Paris 2024 fue una correccion (B1).

```
python 07_consultas/atleta.py "Kristen Faulkner"
```

Salida esperada (resumida):

```
MODO: DETALLE | atleta_id 151806
Medallas por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 1 / plata 0 / bronce 0
   desglose: sin YOG oro 1 / plata 0 / bronce 0 | YOG oro 0 / plata 0 / bronce 0
Participaciones: 2
2024  Verano      Paris          Cycling Track (Cyclin~ Team Pursuit, Women (Olympic)            USA  United States  -      
2024  Verano      Paris          Cycling Road (Cycling) Women's Road Race                        USA  United States  1      Oro
Tiempo de respuesta: consultas a MongoDB 4.9 ms | total con formato 5.1 ms
```

## 6. Homonimos: modo CANDIDATO

Dos personas con el mismo nombre: se listan, no se elige una.

```
python 07_consultas/atleta.py "Jack Robinson"
```

Salida esperada (resumida):

```
MODO: CANDIDATO | 2 atletas coinciden (exacta (nombre usado, completo o alias)). Use --id para ver el detalle.
   6939  Jack Robinson                      M    USA              1927-04-26  Basketball (Basketball)        1/0/0
 151209  Jack Robinson                      M    Australia        -           Surfing                        0/1/0
Tiempo de respuesta: consultas a MongoDB 2.9 ms | total con formato 3.2 ms
```

## 7. Homonimos: detalle por id

Se elige uno de los candidatos con --id.

```
python 07_consultas/atleta.py "Jack Robinson" --id 151209
```

Salida esperada (resumida):

```
MODO: DETALLE | atleta_id 151209
Medallas por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 0 / plata 1 / bronce 0
   desglose: sin YOG oro 0 / plata 1 / bronce 0 | YOG oro 0 / plata 0 / bronce 0
Participaciones: 1
2024  Verano      Paris          Surfing                Men                                      AUS  Australia      -      Plata
Tiempo de respuesta: consultas a MongoDB 3.9 ms | total con formato 3.9 ms
```

## 8. Alias de un atleta fusionado

Se busca con el nombre que traia la otra fuente y se encuentra al atleta historico.

```
python 07_consultas/atleta.py "Shiyu Lu"
```

Salida esperada (resumida):

```
MODO: DETALLE | atleta_id 138342
Alias (nombres con que aparecia en otra fuente): Shiyu Lu
Medallas por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 0 / plata 0 / bronce 0
   desglose: sin YOG oro 0 / plata 0 / bronce 0 | YOG oro 0 / plata 0 / bronce 0
Participaciones: 2
2020  Verano      Tokyo          Rowing                 Coxless Fours, Women (Olympic)           CHN  People's Repu~ 5      
2024  Verano      Paris          Rowing                 Double Sculls, Women (Olympic)           CHN  China          -      
Tiempo de respuesta: consultas a MongoDB 7.1 ms | total con formato 7.6 ms
```

## 9. Atleta con historia unificada (caso Fajdek)

Cuatro ediciones, 2012 a 2024, bajo un solo atleta.

```
python 07_consultas/atleta.py "Pawel Fajdek"
```

Salida esperada (resumida):

```
MODO: DETALLE | atleta_id 120119
Medallas por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 0 / plata 0 / bronce 1
   desglose: sin YOG oro 0 / plata 0 / bronce 1 | YOG oro 0 / plata 0 / bronce 0
Participaciones: 4
2012  Verano      London         Athletics              Hammer Throw, Men (Olympic)              POL                 -      
2016  Verano      Rio de Janeiro Athletics              Hammer Throw, Men (Olympic)              POL                 17     
2020  Verano      Tokyo          Athletics              Hammer Throw, Men (Olympic)              POL                 3      Bronce
Tiempo de respuesta: consultas a MongoDB 5.3 ms | total con formato 5.6 ms
```

## 10. Juegos de la Juventud: excluidos por defecto

Sin --incluir-yog solo salen los Juegos adultos.

```
python 07_consultas/atleta.py "Mariana Avitia"
```

Salida esperada (resumida):

```
MODO: DETALLE | atleta_id 110277
Medallas por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 0 / plata 0 / bronce 1
   desglose: sin YOG oro 0 / plata 0 / bronce 1 | YOG oro 0 / plata 0 / bronce 0
Participaciones: 3 (2 de Juegos de la Juventud ocultas; use --incluir-yog)
2008  Verano      Beijing        Archery                Individual, Women (Olympic)              MEX                 8      
2012  Verano      London         Archery                Individual, Women (Olympic)              MEX                 3      Bronce
2012  Verano      London         Archery                Team, Women (Olympic)                    MEX  Mexico         7      
Tiempo de respuesta: consultas a MongoDB 4.4 ms | total con formato 4.7 ms
```

## 11. Juegos de la Juventud: con --incluir-yog

Con la bandera aparecen las participaciones YOG.

```
python 07_consultas/atleta.py "Mariana Avitia" --incluir-yog
```

Salida esperada (resumida):

```
MODO: DETALLE | atleta_id 110277
Medallas por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 0 / plata 0 / bronce 1
   desglose: sin YOG oro 0 / plata 0 / bronce 1 | YOG oro 0 / plata 0 / bronce 0
Participaciones: 5
2008  Verano      Beijing        Archery                Individual, Women (Olympic)              MEX                 8      
2010  Verano-YOG  Singapore      Archery                Individual, Girls (YOG)                  MEX                 4      
2010  Verano-YOG  Singapore      Archery                Team, Mixed Youth (YOG)                  MEX  Joni Hautamäki 17=    
Tiempo de respuesta: consultas a MongoDB 7.6 ms | total con formato 7.9 ms
```

## 12. Atleta inexistente

Modo SIN_COINCIDENCIAS.

```
python 07_consultas/atleta.py "Nadie Inexistente"
```

Salida esperada (resumida):

```
MODO: SIN_COINCIDENCIAS | ningun atleta coincide con 'Nadie Inexistente'
Tiempo de respuesta: consultas a MongoDB 7.0 ms | total con formato 7.2 ms
```

## 13. Pais multi-NOC y sedes

Alemania agrega GER, FRG, GDR y SAA; lista sus sedes.

```
python 07_consultas/pais.py Germany
```

Salida esperada (resumida):

```
PAIS: Germany (id 71, encontrado por nombre exacto)
NOC asociados: FRG [PAIS_ACTUAL], GDR [PAIS_ACTUAL], GER [PAIS_ACTUAL], SAA [PAIS_ACTUAL]
SEDE: 3 edicion(es): 1936 Invierno (Garmisch-Partenkirchen); 1936 Verano (Berlin); 1972 Verano (Munich)
RESUMEN (sin YOG): 49 ediciones con participacion | 17,773 participaciones totales | 8,156 atletas distintos (total historico)
MEDALLAS por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 1357 / plata 1303 / bronce 1331
MEDALLAS por evento (conteo oficial: una medalla por evento y NOC): oro 615 / plata 622 / bronce 615
1896  Verano          154      19  oro 25 / plata 5 / bronce 2        oro 9 / plata 5 / bronce 2
1900  Verano          122      77  oro 14 / plata 20 / bronce 11      oro 4 / plata 3 / bronce 1
1904  Verano           68      20  oro 5 / plata 4 / bronce 5         oro 5 / plata 4 / bronce 5
Tiempo de respuesta: consultas a MongoDB 3.1 ms | total con formato 3.5 ms
```

## 14. Pais con entidades historicas (URS y EUN)

Rusia incluye URS y EUN como entidades historicas no atribuidas.

```
python 07_consultas/pais.py "Russian Federation"
```

Salida esperada (resumida):

```
PAIS: Russian Federation (id 152, encontrado por nombre exacto)
NOC asociados: EUN [ENTIDAD_HISTORICA_NO_ATRIBUIDA], RUS [PAIS_ACTUAL], URS [ENTIDAD_HISTORICA_NO_ATRIBUIDA]
SEDE: 2 edicion(es): 1980 Verano (Moskva); 2014 Invierno (Sochi)
RESUMEN (sin YOG): 36 ediciones con participacion | 12,150 participaciones totales | 5,727 atletas distintos (total historico)
MEDALLAS por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 1575 / plata 1135 / bronce 1158
MEDALLAS por evento (conteo oficial: una medalla por evento y NOC): oro 719 / plata 586 / bronce 578
1900  Verano            6       4  oro 0 / plata 0 / bronce 0         oro 0 / plata 0 / bronce 0
1908  Verano            7       6  oro 1 / plata 2 / bronce 0         oro 1 / plata 2 / bronce 0
1912  Verano          303     158  oro 0 / plata 5 / bronce 9         oro 0 / plata 2 / bronce 3
Tiempo de respuesta: consultas a MongoDB 3.0 ms | total con formato 3.4 ms
```

## 15. Pais que nunca fue sede

Resultado explicito NUNCA_SEDE, distinto de pais no encontrado.

```
python 07_consultas/pais.py Guatemala
```

Salida esperada (resumida):

```
PAIS: Guatemala (id 76, encontrado por nombre exacto)
NOC asociados: GUA [PAIS_ACTUAL]
NUNCA_SEDE: el pais nunca ha sido sede de unos Juegos (sin contar Juegos de la Juventud)
RESUMEN (sin YOG): 17 ediciones con participacion | 479 participaciones totales | 264 atletas distintos (total historico)
MEDALLAS por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 1 / plata 1 / bronce 1
MEDALLAS por evento (conteo oficial: una medalla por evento y NOC): oro 1 / plata 1 / bronce 1
1952  Verano           38      21  oro 0 / plata 0 / bronce 0         oro 0 / plata 0 / bronce 0
1968  Verano           68      48  oro 0 / plata 0 / bronce 0         oro 0 / plata 0 / bronce 0
1972  Verano           11       8  oro 0 / plata 0 / bronce 0         oro 0 / plata 0 / bronce 0
Tiempo de respuesta: consultas a MongoDB 2.5 ms | total con formato 2.8 ms
```

## 16. Pais con historial de sedes

Francia: seis ediciones como sede.

```
python 07_consultas/pais.py France
```

Salida esperada (resumida):

```
PAIS: France (id 67, encontrado por nombre exacto)
NOC asociados: FRA [PAIS_ACTUAL]
SEDE: 6 edicion(es): 1900 Verano (Paris); 1924 Invierno (Chamonix); 1924 Verano (Paris); 1968 Invierno (Grenoble); 1992 Invierno (Albertville); 2024 Verano (Paris)
RESUMEN (sin YOG): 53 ediciones con participacion | 14,684 participaciones totales | 6,744 atletas distintos (total historico)
MEDALLAS por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 611 / plata 749 / bronce 726
MEDALLAS por evento (conteo oficial: una medalla por evento y NOC): oro 284 / plata 322 / bronce 357
1896  Verano           48      13  oro 5 / plata 4 / bronce 2         oro 5 / plata 4 / bronce 2
1900  Verano         1171     748  oro 57 / plata 110 / bronce 86     oro 29 / plata 40 / bronce 37
1908  Verano          365     222  oro 12 / plata 5 / bronce 23       oro 5 / plata 5 / bronce 9
Tiempo de respuesta: consultas a MongoDB 3.3 ms | total con formato 3.7 ms
```

## 17. Pais con detalle paginado y filtros

Participaciones y resultados, desde la coleccion participaciones con indice.

```
python 07_consultas/pais.py "United States" --anio 2024 --deporte "Swimming (Aquatics)" --detalle --tam 8
```

Salida esperada (resumida):

```
PAIS: United States (id 194, encontrado por nombre exacto)
NOC asociados: USA [PAIS_ACTUAL]
SEDE: sin sede en 2024 (si fue sede en otros anios: 1904, 1932, 1932, 1960, 1980, 1984, 1996, 2002)
FILTRO anio=2024, deporte='Swimming (Aquatics)': 113 participaciones, 46 atletas
DETALLE: 113 participaciones | pagina 1 de 15 (8 por pagina; --pagina N para avanzar)
2024  Verano      Swimming (Aquatics)    400 metres Freestyle, Women (Olympi~ USA  Katie Ledecky              -      Bronce
2024  Verano      Swimming (Aquatics)    800 metres Freestyle, Women (Olympi~ USA  Katie Ledecky              -      Oro
2024  Verano      Swimming (Aquatics)    Women's 1500m Freestyle              USA  Katie Ledecky              -      Oro
Tiempo de respuesta: consultas a MongoDB 13.6 ms | total con formato 14.6 ms
```

## 18. Pais con Juegos de la Juventud incluidos

Medallero total, con YOG.

```
python 07_consultas/pais.py Germany --incluir-yog
```

Salida esperada (resumida):

```
PAIS: Germany (id 71, encontrado por nombre exacto)
NOC asociados: FRG [PAIS_ACTUAL], GDR [PAIS_ACTUAL], GER [PAIS_ACTUAL], SAA [PAIS_ACTUAL]
SEDE: 3 edicion(es): 1936 Invierno (Garmisch-Partenkirchen); 1936 Verano (Berlin); 1972 Verano (Munich)
RESUMEN: 55 ediciones con participacion | 17,773 participaciones totales | 8,156 atletas distintos (total historico)
MEDALLAS por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 1374 / plata 1320 / bronce 1349
MEDALLAS por evento (conteo oficial: una medalla por evento y NOC): oro 629 / plata 635 / bronce 630
1896  Verano          154      19  oro 25 / plata 5 / bronce 2        oro 9 / plata 5 / bronce 2
1900  Verano          122      77  oro 14 / plata 20 / bronce 11      oro 4 / plata 3 / bronce 1
1904  Verano           68      20  oro 5 / plata 4 / bronce 5         oro 5 / plata 4 / bronce 5
Tiempo de respuesta: consultas a MongoDB 3.5 ms | total con formato 4.0 ms
```

## 19. Entidad sin pais

Taiwan (NOC TPE) existe como entidad aparte.

```
python 07_consultas/pais.py Taiwan
```

Salida esperada (resumida):

```
ENTIDAD (NOC sin pais): Taiwan (id NOC:TPE, encontrado por nombre exacto)
NOC asociados: TPE [ENTIDAD_SIN_PAIS]
RESUMEN (sin YOG): 30 ediciones con participacion | 1,353 participaciones totales | 644 atletas distintos (total historico)
MEDALLAS por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 8 / plata 33 / bronce 25
MEDALLAS por evento (conteo oficial: una medalla por evento y NOC): oro 6 / plata 11 / bronce 21
1956  Verano           24      20  oro 0 / plata 0 / bronce 0         oro 0 / plata 0 / bronce 0
1960  Verano           32      27  oro 0 / plata 1 / bronce 0         oro 0 / plata 1 / bronce 0
1964  Verano           99      40  oro 0 / plata 0 / bronce 0         oro 0 / plata 0 / bronce 0
Tiempo de respuesta: consultas a MongoDB 3.2 ms | total con formato 3.7 ms
```

## 20. Plan de ejecucion de un atleta

IXSCAN en la busqueda y IDHACK en el detalle; nunca COLLSCAN.

```
python 07_consultas/atleta.py "Usain Bolt" --explain
```

Salida esperada (resumida):

```
[explain busqueda por exacta (nombre usado, completo o alias)] plan: LIMIT > PROJECTION_SIMPLE > FETCH > IXSCAN(claves_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
[explain detalle (un solo documento)] plan: IDHACK | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
MODO: DETALLE | atleta_id 104492
Medallas por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 8 / plata 0 / bronce 0
   desglose: sin YOG oro 8 / plata 0 / bronce 0 | YOG oro 0 / plata 0 / bronce 0
Participaciones: 10
2004  Verano      Athina         Athletics              200 metres, Men (Olympic)                JAM                 5      
2008  Verano      Beijing        Athletics              100 metres, Men (Olympic)                JAM                 1      Oro
2008  Verano      Beijing        Athletics              200 metres, Men (Olympic)                JAM                 1      Oro
Tiempo de respuesta: consultas a MongoDB 5.4 ms | total con formato 10.9 ms
```

## 21. Plan de ejecucion de un pais

IXSCAN sobre el indice compuesto de participaciones.

```
python 07_consultas/pais.py Japan --detalle --tam 5 --explain
```

Salida esperada (resumida):

```
[explain busqueda por nombre exacto] plan: LIMIT > FETCH > IXSCAN(nombre_key_1) | indices examinados 1, documentos examinados 1, devueltos 1, 0 ms en el servidor
PAIS: Japan (id 92, encontrado por nombre exacto)
NOC asociados: JPN [PAIS_ACTUAL]
SEDE: 4 edicion(es): 1964 Verano (Tokyo); 1972 Invierno (Sapporo); 1998 Invierno (Nagano); 2020 Verano (Tokyo)
RESUMEN (sin YOG): 46 ediciones con participacion | 10,469 participaciones totales | 4,879 atletas distintos (total historico)
MEDALLAS por atleta (una medalla por atleta y resultado, criterio de la Fase 1): oro 350 / plata 395 / bronce 421
MEDALLAS por evento (conteo oficial: una medalla por evento y NOC): oro 204 / plata 189 / bronce 219
[explain detalle paginado] plan: LIMIT > FETCH > IXSCAN(pais_id_1_es_yog_1_anio_1_deporte_1) | indices examinados 5, documentos examinados 5, devueltos 5, 0 ms en el servidor
DETALLE: 10,296 participaciones | pagina 1 de 2060 (5 por pagina; --pagina N para avanzar)
1912  Verano      Athletics              Marathon, Men (Olympic)              JPN  Shizo Kanakuri             -      
1912  Verano      Athletics              100 metres, Men (Olympic)            JPN  Yahiko Mishima             16     
1912  Verano      Athletics              200 metres, Men (Olympic)            JPN  Yahiko Mishima             13     
Tiempo de respuesta: consultas a MongoDB 13.3 ms | total con formato 20.2 ms
```

## Diferencias por diseno frente a las funciones de Postgres

Las funciones de la Fase 1 (`fn_atleta_info`, `fn_pais_info`) y estos scripts dan los mismos resultados (comparacion cruzada en `06_validacion/`), salvo por cuatro diferencias deliberadas:

- **Alias de atletas fusionados:** MongoDB encuentra a un atleta por el nombre con que aparecia en la otra fuente ("Shiyu Lu" lleva a Lu Shiyu); Postgres no.
- **Taiwan como entidad:** los NOC sin pais (TPE, ROC, EOR y otros) existen en MongoDB como entidades consultables; la funcion de Postgres responde PAIS_NO_ENCONTRADO.
- **`--anio` filtra las sedes:** `pais.py --anio N` muestra solo la sede de ese anio; la funcion de Postgres siempre lista todas.
- **`--deporte` acepta prefijo:** `--deporte Swimming` equivale a `Swimming (Aquatics)`; Postgres exige el nombre completo.

## Si algo falla

- `Connection refused` en MongoDB: levantar Docker Desktop y `docker compose -f 00_infraestructura/docker-compose.yml up -d`.
- Una consulta de pais responde `PAIS_NO_ENCONTRADO`: usar el nombre en ingles o el codigo NOC (`GER`, `USA`).
- Un atleta famoso aparece con la historia incompleta: ver `01_correcciones/LIMITACIONES_CONOCIDAS.md` (hay pares de duplicados probables no fusionados, por ejemplo los de equipos grandes).
- Validar toda la base: `python 06_validacion/validar.py`.
