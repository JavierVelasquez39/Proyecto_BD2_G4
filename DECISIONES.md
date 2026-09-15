# Decisiones de diseño - Proyecto Olimpiadas (BD2, USAC)

> Registro de decisiones según la política del equipo. Entradas
> retroactivas documentadas el 2026-09-12 sobre trabajo ya realizado en
> `sql/ddl.sql` y `etl/etl.py`; de aquí en adelante toda decisión nueva se
> agrega aquí en el mismo momento en que se toma.

## [2026-09-12] No hay FK directa NOC -> ATLETA

**Contexto:** El modelo ER acordado no incluye una FK de `NOC` hacia
`ATLETA`; el vínculo vive solo en `PARTICIPACION.codigo_noc`. La
justificación original era teórica (un atleta puede competir bajo NOC
distintos a lo largo de su carrera: reunificación alemana, disolución de
la URSS, etc.). Se verificó esto contra los datos reales de fuente 1
(`results.csv`, 299,731 filas cargadas en PARTICIPACION tras la carga
final): agrupando por `atleta_id` y contando `codigo_noc` distintos no
nulos, **1,834 atletas** compitieron bajo más de un NOC en su historial.
Adicionalmente, `bios.csv` (fuente 1, clean-data) trae para esos mismos
atletas un campo `NOC` corrupto que concatena los nombres de región sin
separador (ver entrada aparte más abajo), lo que habría sido un intento
fallido de resolver esta misma ambigüedad en el archivo de origen.

**Decisión:** Mantener el modelo tal como está, sin FK `NOC -> ATLETA`,
confirmando que es la decisión correcta con evidencia empírica, no solo
con el argumento teórico original.

**Alternativas consideradas:** Agregar `NOC` "principal" como FK en
`ATLETA` (rechazada: perdería el historial real de cambio de NOC de 1,834
atletas y sería ambigua/arbitraria para elegir "el" NOC de la persona).

**Estado:** Resuelto.

---

## [2026-09-12] Fuente 4 (DataCamp r-olympics) se descarta de la carga

**Contexto:** El enunciado ya identificaba que la fuente 4 (DataCamp,
datalab "r-olympics") comparte linaje con la fuente 2 (Kaggle heesoo37,
"120 years of Olympic history"), ambas derivadas de sports-reference.com,
pero dejaba pendiente confirmar si son idénticas o si una es subconjunto
de la otra. La plataforma DataCamp devuelve HTTP 403 al intentar acceder
sin sesión autenticada, por lo que **no se pudo verificar el contenido
exacto de la fuente 4 de forma independiente** en este entorno.

**Decisión:** No cargar la fuente 4. Se trata como equivalente a la
fuente 2 y se usa (cuando se disponga de archivos) únicamente para
validación cruzada de la fuente 2, nunca para carga directa adicional;
así se evita duplicar `PARTICIPACION`.

**Alternativas consideradas:** Cargar ambas fuentes 2 y 4 por separado y
deduplicar después contra `results.csv` de fuente 1 (rechazada: trabajo
adicional sin beneficio claro si son la misma base de datos empaquetada
dos veces).

**Estado:** Resuelto en cuanto a estrategia de carga. La afirmación
"fuente 4 es idéntica a fuente 2" en sí **no está verificada de forma
independiente** (no se tuvo acceso a los archivos de ninguna de las dos
plataformas); se documenta como no verificado.

---

## [2026-09-12] Exclusión de 5,842 filas de Youth Olympic Games (YOG)

**Contexto:** `results.csv` (fuente 1) mezcla en las mismas columnas
`year`/`type` resultados de Juegos Olímpicos regulares y de Juegos
Olímpicos de la Juventud (YOG), distinguibles solo por el sufijo
`(YOG)` vs `(Olympic)` en el texto de `event`. El modelo ER acordado
(`EDICION_OLIMPICA.tipo CHECK IN ('Verano','Invierno')`) no contempla una
categoría para JJOO de la Juventud. Se excluyeron 5,842 filas cuyo
`event` contiene `(YOG)`, más 233 filas adicionales cuyo `(anio,tipo)` no
calzó con ninguna edición real del catálogo de sedes (mismo fenómeno,
residual: ediciones YOG que caen en (anio,tipo) sin edición regular
correspondiente, por ejemplo (2010,Verano)=Singapur YOG,
(2012,Invierno)=Innsbruck YOG).

**Decisión (provisional):** Excluir todas las filas YOG de la carga
actual.

**Alternativas consideradas:** (a) Agregar valores nuevos a
`EDICION_OLIMPICA.tipo` (por ejemplo `'Verano-YOG'`, `'Invierno-YOG'`),
lo que cambia el modelo ER acordado y requiere aprobación; (b) agregar
una tabla o columna booleana `es_youth`, mismo problema, cambia el
modelo; (c) cargarlas mezcladas con los Juegos regulares sin distinguir,
rechazada porque contaminaría conteos de medallero y participación de
los Juegos "reales".

**Estado:** Pendiente de confirmar con el profesor. Es una decisión de
alcance que el enunciado no cubre explícitamente. Mientras no haya
respuesta, se mantiene la exclusión total de YOG.

---

## [2026-09-12] Referencia manual de sedes/ediciones (`reference_editions.csv`)

**Contexto:** Ninguna de las 4 fuentes del enunciado trae una tabla de
sede/ciudad anfitriona por edición. `SEDE` y `EDICION_OLIMPICA` no se
pueden poblar desde `results.csv`, `bios.csv`, `noc_regions.csv` ni
`populations.csv`.

**Decisión:** Se creó a mano `etl/reference_editions.csv` (53 filas:
anio, tipo, ciudad, país sede), a partir de conocimiento histórico
público de las sedes olímpicas 1896-2022, para poder poblar `SEDE` y
`EDICION_OLIMPICA`. Esta fuente **no es ninguna de las 4 del enunciado**
y se declara explícitamente aquí y en `etl/REPORTE.md`.

**Alternativas consideradas:** Dejar `SEDE`/`EDICION_OLIMPICA` sin poblar
o con `sede_id` NULL en todas las ediciones (rechazada: rompe una parte
central del modelo, la relación EDICION_OLIMPICA->SEDE, sin necesidad,
cuando el dato es de dominio público y de bajo riesgo de error).

**Estado:** Temporal al momento de escribir esta entrada.

**[2026-09-12, cierre] Reemplazado parcialmente por datos reales, no es
un reemplazo total.** De las 55 ediciones finales, **52 usan `City`
real** (fuente 2 o fuente 3) y **3 siguen usando
`reference_editions.csv`** (2018 Invierno, 2020 Verano, 2022 Invierno).
Ya se dispone de `data_raw/fuente2_kaggle120/athlete_events.csv`
(columna `City`) y de `data_raw/fuente3_kaggle2024/olympics_dataset.csv`
(columna `City`, único que llega a 2024). `reference_editions.csv`
**deja de ser la fuente primaria** de `SEDE`/`EDICION_OLIMPICA`; se
retiene en el repo solo como referencia histórica (ya no la lee el ETL
como fuente principal). Regla aplicada en `build_sede_edicion`
(`etl/etl.py`):

- **1896-2016 (todas las temporadas):** ciudad = la más frecuente por
  `(Year, Season)` en `athlete_events.csv` (fuente 2). Esto reveló un
  caso real interesante, no un error: **1956 Verano** tiene 4,829 filas
  con ciudad "Melbourne" y 298 con "Stockholm"; los eventos ecuestres de
  esos Juegos se disputaron en Estocolmo por las leyes de cuarentena
  animal australianas de la época (hecho histórico real). La regla
  "ciudad más frecuente" elige Melbourne correctamente, que es la sede
  oficialmente reconocida.
- **2024 Verano (París):** ciudad tomada de `olympics_dataset.csv`
  (fuente 3) filtrado a `Year==2024`; es la única fuente que llega hasta
  ahí.
- **2018 Invierno, 2020 Verano, 2022 Invierno:** ninguna fuente real trae
  `City` para estos 3 (fuente 2 no llega a 2018+; fuente 3 es
  exclusivamente Verano, así que nunca cubre años Invierno). Estos 3
  **siguen tomando ciudad/país de `reference_editions.csv`**; es el
  único residuo que queda del hack manual original, documentado
  explícitamente en el código (`EDICIONES_SIN_CITY_REAL`) y en el reporte
  de cada corrida.
- **País sede:** ninguna de las 3 fuentes trae columna de país anfitrión
  (todas solo traen ciudad). Se mantiene una tabla `HOST_COUNTRY_BY_CITY`
  (mismo conocimiento histórico público que antes poblaba
  `reference_editions.csv` completo, ahora acotado a mapear ciudad a país
  en 42 entradas en vez de ser la fuente primaria de ciudad y edición).
- **Hallazgo colateral:** fuente 2 sí tiene una fila `(1906, Verano)` con
  ciudad real "Athina" (Juegos Intercalados de 1906) que fuente 1 no
  incluye en absoluto en `results.csv` (0 participaciones apuntan a esa
  edición). Se deja como fila de `EDICION_OLIMPICA` huérfana (sin
  `PARTICIPACION` asociada) en vez de excluirla artificialmente; no es
  un error, es un reflejo fiel de que las fuentes discrepan sobre si 1906
  cuenta como "edición olímpica" (no reconocida oficialmente por el COI
  como Juegos numerados).

**Estado:** Resuelto como reemplazo parcial. No queda pendiente ninguna
acción sobre esto (los 3 residuos son un límite real de los datos
disponibles, no un trabajo a medias), pero no debe describirse como
"reemplazo total" en ningún resumen o entrega: 3 de 55 ediciones (5.5%)
siguen sin `City` real.

---

## [2026-09-12] `altura_cm`/`peso_kg` constantes por atleta en `PARTICIPACION`

**Contexto:** El modelo ER pone `altura_cm` y `peso_kg` en
`PARTICIPACION` (no en `ATLETA`), lo que sugiere que podrían variar entre
ediciones para un mismo atleta (biometría al momento de cada
participación). Fuente 1 (`bios.csv`, clean-data) solo trae **un** valor
de `height_cm`/`weight_kg` por atleta, no uno por participación.

**Decisión:** Replicar el mismo valor de altura/peso del atleta en todas
sus filas de `PARTICIPACION`, documentando la limitación en vez de dejar
esos campos en NULL o inventar variación falsa.

**Alternativas consideradas:** Dejar `altura_cm`/`peso_kg` NULL en
`PARTICIPACION` y mover esos campos a `ATLETA` (rechazada por ahora: eso
sí modificaría el modelo ER acordado sin autorización; se prefiere
señalar la limitación de la fuente en vez de cambiar el esquema).

**Estado:** Resuelto como limitación conocida y documentada; no requiere
cambio de modelo salvo que el profesor prefiera mover esos campos a
`ATLETA`.

---

## [2026-09-12] Corrupción de `bios.csv.NOC` para atletas multi-NOC, no usado

**Contexto:** El campo `NOC` de `clean-data/bios.csv` (fuente 1), para
atletas que compitieron bajo más de un NOC a lo largo de su carrera,
concatena los nombres de región **sin separador** (por ejemplo `"Greece
Romania"`, `"Canada Italy"`, `"Russian Federation Turkmenistan"`; se
observaron cientos de combinaciones de este tipo al inspeccionar el
archivo). Es evidencia adicional (no la única) de por qué no puede
existir una FK NOC->ATLETA de valor único.

**Decisión:** No usar `bios.csv.NOC` para ningún campo estructural de
`ATLETA`. `pais_nacimiento` se deriva de `born_country` (código de 3
letras al final del campo `Born` parseado) y `nacionalidad` se deriva del
primer NOC del atleta en `results.csv` ordenado por año (ver
`build_atleta` en `etl/etl.py`), nunca del campo `bios.csv.NOC`.

**Alternativas consideradas:** Intentar parsear el campo concatenado
separándolo por posibles nombres de país conocidos (rechazada: sin
separador confiable, el parseo sería ambiguo y propenso a error para
nombres de país compuestos por varias palabras).

**Estado:** Resuelto. Campo confirmado como no confiable y excluido del
pipeline.

---

## [2026-09-12] Deduplicación de clave natural en PARTICIPACION (caso Polo 1900)

**Contexto:** Al aplicar por primera vez
`UNIQUE(atleta_id, edicion_id, evento_id, codigo_noc, equipo)` en
`PARTICIPACION`, la carga real falló con `UniqueViolation` en el evento
"Polo, Men (Olympic (non-medal))" de 1900: el mismo atleta (por ejemplo
`athlete_id=28`, Guy Lejeune) tiene varias filas en `results.csv` para el
mismo evento/edición/NOC/equipo, con distinto `place`. Son equipos
compuestos/mixtos de la era pre-moderna del olimpismo, sin columna de
ronda/partido en la fuente para desambiguar. La reacción inicial fue
retirar la restricción `UNIQUE` por completo.

**Decisión:** Revertir esa primera reacción: el modelo **ya** contempla
este caso mediante la cardinalidad 1:N `PARTICIPACION -> RESULTADO`. Se
corrigió el ETL (`build_participacion_resultado` en `etl/etl.py`) para:
1. Detectar grupos duplicados de `(atleta_id, edicion_id, evento_id)` en
   staging antes de insertar (428 grupos, 943 filas de origen en la
   corrida final).
2. Insertar **una sola fila** de `PARTICIPACION` por grupo (se toma
   `codigo_noc`/`equipo`/`edad`/`altura_cm`/`peso_kg` de la primera fila
   del grupo en orden de aparición en `results.csv`).
3. Insertar **una fila de `RESULTADO` por cada resultado distinto**
   (lugar/empate/medalla) del grupo: 299,731 filas de `RESULTADO` en
   total, sin pérdida frente a las filas de origen que sobrevivieron los
   filtros previos.
4. Restaurar `UNIQUE(atleta_id, edicion_id, evento_id)` en el DDL, ahora
   sin `codigo_noc`/`equipo`, porque esos pasan a ser atributos de la
   fila colapsada, no parte de la identidad de la participación.
5. Se corrió la carga completa de nuevo contra Postgres 16 real: **0
   violaciones de `UNIQUE`**, `participacion=299,216` filas,
   `resultado=299,731` filas.

En 162 de los 428 grupos, el valor de `equipo` difiere entre las filas de
origen colapsadas (por ejemplo "A" vs "B" vs "C" vs "Blue" en Polo 1900);
se documenta como pérdida de información conocida: solo el valor de la
primera fila queda en `PARTICIPACION.equipo`, aunque cada resultado
distinto sigue existiendo en `RESULTADO`. `codigo_noc` no difirió en
ningún grupo (0 de 428) en esta corrida.

**Alternativas consideradas:** (a) Eliminar el `UNIQUE` sin más
(descartada: debilita la integridad del esquema en vez de arreglar la
causa raíz); (b) agregar una columna de "ronda"/"partido" inventada para
diferenciar filas (descartada: no hay dato en la fuente que la respalde,
sería fabricar información).

**Estado:** Resuelto.

---

## [2026-09-12] Conteo NOC 235 vs 230: confirmado que fuente 1 y fuente 2 comparten el mismo `noc_regions.csv`

**Contexto:** Con `data_raw/fuente2_kaggle120/noc_regions.csv` ya
disponible, se comparó columna por columna contra
`data_raw/Olympics-Dataset/clean-data/noc_regions.csv` (fuente 1).

**Decisión:** Documentar el resultado definitivo en vez de dejarlo como
"no verificado". **Los dos archivos son idénticos**: mismos 230 códigos
NOC, mismos nombres de `region`, 0 diferencias. El conteo de **236** en
la tabla `NOC` de esta corrida es `230 (idéntico en ambas fuentes) + 6
agregados manualmente en el ETL` (LBN, SGP, ROC, EOR, COR, ya
documentados, más **AIN**, código nuevo de fuente 3 para "Individual
Neutral Athletes", atletas rusos/bielorrusos neutrales en París 2024).
Se verificó además que los códigos "base" LIB/SIN (los que sí traía el
`noc_regions.csv` original) tienen **0 participaciones** (`results.csv`
usa siempre los alias modernos LBN/SGP) y que los 5 códigos agregados
antes de esta corrida sí tienen participaciones reales (362, 389, 1128,
47 y 26 respectivamente). Detalle completo en `etl/REPORTE.md` (sección
"Reconciliación de conteos NOC") y en `FUENTES.md`.

**Alternativas consideradas:** Ninguna. Es una verificación, no una
decisión de diseño.

**Estado:** Resuelto.

---

## [2026-09-12] Regla para cargar fuente 3 sin duplicar fuente 1 (solo París 2024)

**Contexto:** Fuente 3 (`olympics_dataset.csv`, CC BY-NC-SA 4.0) cubre
1896-2024 pero solo Verano, y sí trae todas las participaciones (no solo
medallistas, confirmado inspeccionando el archivo real: 14,892 filas para
2024, con `Medal='No medal'` en 12,611 de ellas). Fuente 1 ya cubre
1896-2022 (Verano+Invierno). Cargar fuente 3 completa duplicaría
`PARTICIPACION` para todo el rango 1896-2020.

**Decisión:** Filtrar fuente 3 a `Year == 2024` exclusivamente, antes de
cualquier otro procesamiento (`olympics_f3[olympics_f3["Year"] == 2024]`
en `main()`). Es la única edición que fuente 1 no cubre.
Adicionalmente, como fuente 3 tiene licencia CC BY-NC-SA (más
restrictiva que la CC0 de fuente 2), se usa **exclusivamente** para esto,
nunca como fuente de validación cruzada general (a diferencia de fuente
2), para minimizar cuánta porción del dataset final queda bajo esa
licencia más restrictiva (ver `FUENTES.md`).

Limitación conocida: fuente 3 no trae `Age`/`Height`/`Weight` ni
`place`/`rank`. Para las 14,892 filas de 2024, `PARTICIPACION.edad`,
`altura_cm`, `peso_kg` y `RESULTADO.lugar` quedan `NULL` (las columnas ya
son nullable en el DDL; la carga no falló por esto, verificado con la
corrida real contra Postgres 16, 0 violaciones).

**Alternativas consideradas:** Cargar también 2020 de fuente 3 para
reconciliar contra fuente 1 (mencionado como opcional en el enunciado
original); descartado en esta corrida para minimizar el uso de una
fuente de licencia más restrictiva cuando fuente 1 ya cubre ese año sin
restricciones (MIT).

**Estado:** Resuelto.

---

## [2026-09-12] Emparejamiento de atletas de fuente 3 (2024) contra ATLETA por nombre

**Contexto:** Fuente 3 no comparte namespace de ID con fuente 1
(`player_id` es una numeración propia del archivo, no el `athlete_id` de
`bios.csv`). Un atleta que ya compitió en 2020 o antes y repite en 2024
debe reusar el mismo `atleta_id`, no duplicarse.

**Decisión original (2026-09-12):** Emparejar por nombre normalizado
exacto (`nombre_usado` o `nombre_completo`, sin distinguir
mayúsculas/espacios) contra el catálogo `ATLETA` ya cargado de fuente 1.
De 11,113 atletas distintos en París 2024: 2,744 calzaban, 8,369 quedaban
como nuevos.

---

**[2026-09-13] Auditoría manual y corrección del criterio, entrada
cerrada.**

**Auditoría realizada:** se tomó una muestra aleatoria de 30 casos del
grupo "calzó" y 30 del grupo "nuevo" (semilla fija, reproducible) y se
revisó cada uno a mano contra `atleta_df` completo:

- **Grupo "calzó" (30 revisados): 2 falsos positivos confirmados**
  (6.7%), homónimos reales de países distintos fusionados bajo el mismo
  `atleta_id`:
  - *"Jack Robinson"* (F3, NOC=AUS, surfista real de 2024) se había
    emparejado con `atleta_id=6939` (F1: "Robert Lloyd Jackson \"Jack\"
    Robinson", nacionalidad USA, **fallecido el 2022-02-08**, no podía
    competir en 2024. Prueba inequívoca de falso positivo).
  - *"Jordan Thompson"* (F3, NOC=USA, voleibolista) se había emparejado
    con `atleta_id=129915` (F1: nacionalidad Australia, nacido 1994, el
    tenista australiano real, persona distinta).
- **Grupo "nuevo" (30 revisados): al menos 4 falsos negativos
  confirmados** (13.3%), el mismo atleta, ya cargado de fuente 1, no
  calzó por variante de tilde/diacrítico:
  - *"Pawel Fajdek"* (F3) vs *"Paweł Fajdek"* (F1): martillista polaco
    multi-olímpico, claramente la misma persona.
  - *"Alberto Gonzalez"* (F3) vs *"Alberto González"* (F1).
  - *"Laura Galvan"* (F3) vs *"Laura Galván"* (F1).
  - *"Kate Foo"* (F3, NOC=MRI) vs *"Kate Foo Kune"* (F1): nombre
    truncado, no es un caso de tilde sino de forma abreviada del nombre;
    se documenta pero no se corrige (ver limitación abajo).

**Decisión (criterio revisado, implementado en `etl/etl.py`):**

1. **Corrección de los falsos positivos:** antes de aceptar un
   candidato por nombre, se descarta cualquiera con `fecha_fallecimiento`
   no nula (no puede competir en 2024). Si queda más de un candidato vivo
   con el mismo nombre, o exactamente uno pero su `nacionalidad` no
   coincide con el país del NOC de fuente 3, se rechaza el
   emparejamiento (se trata como atleta nuevo) en vez de adivinar.
2. **Corrección de los falsos negativos por tilde:** se agregó
   `name_match_key()`, que pliega diacríticos (NFKD + remoción de marcas
   combinantes) además de mayúsculas/espacios, antes de comparar. El
   nombre mostrado en la BD conserva la tilde original; el plegado es
   solo para la clave de emparejamiento.
3. **No se corrigió** el caso de nombre truncado/abreviado ("Kate Foo"
   vs "Kate Foo Kune"): requeriría matching por subcadena o similitud
   aproximada, con mayor riesgo de falsos positivos nuevos (dos personas
   distintas cuyo nombre uno sea subcadena del otro). Se documenta como
   limitación conocida, no resuelta.

**Resultado tras la corrección** (corrida real contra Postgres 16, 0
violaciones): de 11,113 atletas de París 2024, **3,140 calzaron** (+396
respecto al criterio original de nombre exacto sin plegado de tildes, que
ya había bajado a 2,649 tras solo el filtro de vivo/nacionalidad) y
**7,973 son nuevos**. Desglose de rechazos: 30 candidatos descartados por
estar fallecidos, 81 por nacionalidad inconsistente (probable homónimo),
48 por ambigüedad (más de un candidato vivo con ese nombre).

**Riesgo residual, no resuelto:** el emparejamiento sigue basado en
nombre (plegado) más nacionalidad/vivo; no hay forma de descartar con
certeza homónimos del mismo país y de edad plausible, ni de recuperar
nombres truncados/reordenados/con apodos distintos del "Used name" de
fuente 1. Fuente 3 no trae fecha de nacimiento, que sería el
discriminador más fuerte (el criterio "nombre + año de nacimiento"
sugerido originalmente no es implementable con los datos disponibles).

**Alternativas consideradas:** Crear siempre un `atleta_id` nuevo para
cada `player_id` de fuente 3, sin intentar emparejar (rechazada: crearía
duplicados garantizados para miles de atletas que sabemos que ya
existían). Matching fonético o por subcadena para casos como "Kate
Foo"/"Kate Foo Kune" (rechazada por ahora: aumenta el riesgo de falsos
positivos más de lo que reduce falsos negativos, sin una muestra más
grande que lo justifique).

**Estado:** Resuelto (criterio corregido y verificado con auditoría
real); el riesgo residual de homónimos del mismo país/nacionalidad
desconocida queda documentado como limitación estructural de fuente 3
(no tiene solución con los datos disponibles), no como pendiente de
trabajo.

---

## [2026-09-12 / 2026-09-13] Desajuste de taxonomía DEPORTE y EVENTO entre fuente 1 y fuente 3

**Contexto:** Al extender `DEPORTE`/`EVENTO` con los datos de París 2024,
3 nombres de "Sport" de fuente 3 no calzaron con ningún `deporte.nombre`
existente: `Breaking`, `Equestrian`, `Trampoline Gymnastics`. Se investigó
cada caso antes de asumir que eran deportes nuevos: `Breaking` **sí es
un debut olímpico real** (2024). `Equestrian` y `Trampoline Gymnastics`
**no son deportes nuevos**; ya existían en fuente 1, pero con una
granularidad de nombres distinta: fuente 1 (estilo olympedia) separa
equitación en 5 disciplinas (`Equestrian Dressage (Equestrian)`,
`Equestrian Driving (Equestrian)`, `Equestrian Eventing (Equestrian)`,
`Equestrian Jumping (Equestrian)`, `Equestrian Vaulting (Equestrian)`) y
llama al trampolín `Trampolining (Gymnastics)`, mientras que fuente 3
(estilo sports-reference) agrupa todo bajo `Equestrian` y usa
`Trampoline Gymnastics`. El emparejamiento por "nombre base sin sufijo
`(GrupoPadre)`" que sí reúne 42 de los 45 deportes de 2024 con su
`deporte_id` de fuente 1 no alcanza a resolver estos 2 casos porque el
desajuste no es solo el sufijo, es el nivel de agregación completo.

**Decisión:** Aceptar la duplicación en estos 2 casos puntuales (quedan
como filas `DEPORTE` nuevas, `Equestrian` y `Trampoline Gymnastics`,
separadas de las 5+1 disciplinas equivalentes de fuente 1) en vez de
construir un mapeo manual de reagrupación taxonómica completo, que
requeriría decidir, por ejemplo, si esas 5 disciplinas ecuestres de
fuente 1 deberían fusionarse en una sola fila `DEPORTE` (cambiaría
`EVENTO`/`PARTICIPACION` de fuente 1 ya cargados); eso sí sería un cambio
de alcance mayor, no una simple adición de 2024.

**Alternativas consideradas:** (a) Construir un diccionario de
sinónimos deporte-a-deporte entre fuente 1 y fuente 3 (rechazada por
ahora: requeriría revisar los 93 nombres de fuente 1 uno por uno para
encontrar todos los casos de agregación distinta, no solo estos 2 ya
detectados); (b) fusionar retroactivamente las 5 disciplinas ecuestres de
fuente 1 en una sola (rechazada: es un cambio de esquema/datos de fuente
1 con consecuencias más amplias, fuera del alcance de "agregar 2024").

**Estado (2026-09-12):** Pendiente de confirmar con el profesor si se
prefiere invertir el esfuerzo en unificar la taxonomía de deportes entre
fuentes, o si esta duplicación puntual (2 de 96 filas de `DEPORTE`) es
aceptable tal cual.

---

**[2026-09-13] Escaneo sistemático de similitud (`rapidfuzz`): el
problema era mucho más grande de lo reportado, no solo 2 casos.**

**Auditoría realizada:** por pedido explícito de auditar si había "más
desajustes silenciosos", se corrió `rapidfuzz.token_sort_ratio` y
`token_set_ratio` sobre **los 96 nombres de `DEPORTE`** y los **2,236
nombres de `EVENTO`** ya cargados (no solo los que entraron con 2024).

- **DEPORTE (96 nombres, ~4,560 pares posibles):** ningún par nuevo por
  encima de 65% de similitud resultó ser un duplicado real no detectado
  antes. Todos los pares de alta similitud son deportes genuinamente
  distintos que ya convivían en fuente 1 (por ejemplo `Cycling Road` vs
  `Cycling Track` vs `Cycling Mountain Bike`, `Baseball` vs `Basketball`,
  `Canoe Slalom` vs `Canoe Sprint` vs `Canoe Marathon`); comparten
  palabras pero son disciplinas distintas. **Hallazgo relevante:** el
  propio par ya conocido `Trampolining (Gymnastics)` / `Trampoline
  Gymnastics` sí aparece con 87% de similitud (detectable por texto),
  pero el par `Equestrian` / `Equestrian Dressage (Equestrian)` (etc.)
  **solo llega a ~47-49% de similitud**; la comparación de texto puro
  no habría encontrado ese caso, solo se detectó antes por revisión
  manual de dominio. Esto confirma que un escaneo de similitud de texto,
  por sí solo, es insuficiente para este tipo de desajuste de
  granularidad (no de redacción).

- **EVENTO (2,236 nombres, comparación dirigida: los 332 nuevos de 2024
  contra los 1,904 de fuente 1, restringida al mismo `deporte_id` y
  excluyendo nombres triviales como "Men"/"Women"/"Team"):** **75 pares
  con similitud igual o mayor a 70% resultaron ser el mismo evento real**
  bajo convención de redacción distinta (fuente 1: `"<descriptor>,
  <Género> (Olympic)"`, por ejemplo `"Javelin Throw, Men (Olympic)"`;
  fuente 3: `"<Género>'s <descriptor>"`, por ejemplo `"Men's Javelin
  Throw"`), lo cual afecta a atletismo, natación, remo, ciclismo,
  gimnasia, esgrima, clavados, y más. **No era un problema de 2 deportes
  puntuales: era sistémico**, y sin este escaneo habría quedado sin
  detectar.

**Decisión (implementada en `etl/etl.py`, función
`extend_deporte_evento_f3` con los helpers `_canon_f1_event` y
`_canon_f3_event`):** en vez de hardcodear cada par encontrado a mano
(72+ pares, propenso a error de transcripción e incompleto), se
construyó una **normalización general y determinística** de ambas
convenciones a una forma canónica `(deporte_id, género,
descriptor_normalizado)`:
- fuente 1: se quita el sufijo `"(...)"`, el último segmento separado
  por coma se interpreta como género si es uno de
  Men/Women/Mixed/Boys/Girls/Open, el resto se une sin comas.
- fuente 3: se separa `"<Género>'s "` (o `"Mixed "`) al inicio.
- ambas formas se normalizan a minúsculas, `metres` pasa a `m`,
  `kilometres` pasa a `km`, y las unidades pegadas al número se separan
  (`"100 m"` se lee igual que `"100m"`).
- solo se reusa el `evento_id` de fuente 1 cuando la clave canónica
  **calza exacto** (nunca por similitud aproximada), lo que evita el
  riesgo de fusionar dos eventos realmente distintos.
- se encontraron **5 claves canónicas de fuente 1 con más de un
  evento_id** (por ejemplo el mismo evento en "(Olympic)" y
  "(Intercalated)" de 1906): se prefiere explícitamente la variante
  "(Olympic)" como destino del reuso, para no vincular por error una
  participación de 2024 con un evento de los Juegos Intercalados de
  1906.

**Resultado verificado** (corrida real contra Postgres 16, 0
violaciones; se revisaron a mano 20 pares reusados al azar, los 20
correctos): de los 332 eventos "nuevos" de 2024 originalmente
reportados, **133 se reconocieron como el mismo evento ya existente**
(`EVENTO` bajó de 2,236 a **2,103** filas) y **199 quedaron como
genuinamente nuevos**: una mezcla de eventos realmente nuevos en 2024
(por ejemplo categorías de peso específicas, formatos nuevos) y
variantes de redacción que esta normalización todavía no resuelve (ver
limitación abajo).

**Limitación conocida, no resuelta:** la normalización cubre el patrón
sistemático dominante, pero no todos los casos. Por ejemplo, no colapsa
diferencias de unidad no métrica (`"74 kg"` vs `"74kg"`, sin espacio) ni
reordenamientos más complejos (`"Foil, Individual, Men"` vs `"Men's Foil
Individual"` sí se resuelve, pero categorías de peso con formato libre
como `"Men's Greco-Roman 97kg"` no tienen contraparte exacta garantizada
en fuente 1 y pueden estar entre los 199 "nuevos" sin serlo realmente).
No se investigó cada uno de los 199 individualmente por quedar fuera de
alcance de esta etapa del trabajo.

**Alternativas consideradas:** (a) Hardcodear cada par uno por uno como
se hizo para las 89 filas de `Sport` corrupto (rechazada para este caso:
75+ pares es demasiado para mantener a mano y seguiría incompleto); (b)
fusionar retroactivamente las 5 disciplinas ecuestres de fuente 1 en una
sola fila `DEPORTE`/consolidar sus `EVENTO` (rechazada, mismo motivo que
el 2026-09-12: cambiaría datos ya cargados de fuente 1, alcance mayor).

**Estado:** Resuelto para el patrón sistemático (133 eventos más los 2
deportes ya conocidos). El caso `Equestrian`/`Trampoline Gymnastics` a
nivel `DEPORTE` sigue pendiente de confirmar con el profesor (sin
cambios respecto al 2026-09-12). Los 199 eventos "nuevos" restantes
quedan como limitación conocida, no como pendiente de acción bloqueante.

## [2026-09-14] Function vs. Procedure para incisos d) y e) (`sql/procedures.sql`)

**Contexto:** El enunciado del proyecto pide "stored procedure" para los
incisos d) (información de atleta) y e) (información de país). En
PostgreSQL, `CREATE PROCEDURE` (invocado con `CALL`) no puede devolver un
result set tabular directamente, solo modifica datos o expone parámetros
`OUT`/`INOUT`. Para que se puedan hacer consultas `SELECT * FROM
...(...)` ad hoc el día de la calificación (filtrando, ordenando,
exportando), la lógica real conviene que viva en una `FUNCTION ...
RETURNS TABLE(...)`.

**Decisión:** se implementaron dos `FUNCTION` (`fn_atleta_info`,
`fn_pais_info`) que hacen todo el trabajo, y dos `PROCEDURE` delgados
(`pr_atleta_info`, `pr_pais_info`) que las envuelven con un parámetro
`INOUT refcursor` y las invocan con `CALL`, para cumplir la letra del
enunciado sin duplicar lógica. Uso de la procedure:
```sql
BEGIN;
CALL olimpiadas.pr_atleta_info('Jack Robinson');
FETCH ALL FROM cur_atleta_info;
COMMIT;
```
Verificado que ambas formas (`SELECT * FROM fn_...` y
`CALL pr_...; FETCH ALL FROM ...`) devuelven exactamente los mismos
datos.

**Alternativas consideradas:** (a) Solo `FUNCTION`, ignorando la letra
del enunciado (rechazada: el enunciado pide explícitamente "stored
procedure"); (b) Solo `PROCEDURE` con parámetros `OUT` escalares
agregados (por ejemplo total de medallas) en vez de un cursor con el
detalle completo (rechazada: pierde la lista de
participaciones/resultados que el enunciado pide mostrar, e impide
filtrar/ordenar ad hoc sobre ella).

**Estado:** Resuelto.

## [2026-09-14] Homónimos en búsqueda de atleta por nombre (inciso d)

**Contexto:** La auditoría del 2026-09-13 ya había confirmado 2 casos
reales de homónimos bajo el mismo nombre que son personas distintas:
"Jack Robinson" (`atleta_id=6939`, USA, fallecido 2022-02-08, baloncesto
1952 vs. `atleta_id=151236`, Australia, surfista París 2024) y "Jordan
Thompson" (`atleta_id=129915`, Australia, tenista, vs.
`atleta_id=143643`, USA, voleibolista). Si `fn_atleta_info` hubiera
elegido uno de los dos arbitrariamente (por ejemplo el primero por
`atleta_id`), el resultado sería silenciosamente incorrecto para quien
busque al otro.

**Decisión:** `fn_atleta_info(nombre, atleta_id DEFAULT NULL, deporte,
pais, anio)` busca por nombre normalizado (acentos/mayúsculas plegados
con `f_normalizar`, mismo criterio que `name_match_key()` en
`etl/etl.py`). Si hay más de un `atleta_id` distinto y no se pasó
`atleta_id` explícito, devuelve `modo='CANDIDATO'`: una fila por persona
con nacionalidad, fecha de nacimiento y deportes practicados (agregados),
sin traer participaciones/resultados, para que quien consulta elija.
Pasando el `atleta_id` exacto (obtenido de esa lista) se va directo a
`modo='DETALLE'` con participaciones, resultados y medallas, aplicando
los filtros opcionales de deporte/país/año.

**Verificado contra datos reales** (ver bitácora para la salida
completa): ambos casos de homónimos conocidos devuelven exactamente 2
candidatos con los datos correctos para distinguirlos; el `atleta_id`
del surfista de 2024 lleva directo al detalle (Surfing, AUS, medalla
Plata, 2024). Además, la prueba con nombre acentuado reveló un caso no
documentado antes: "Pawel Fajdek"/"Paweł Fajdek" (lanzador de martillo
polaco) quedó cargado bajo **dos** `atleta_id` distintos (120119:
2012/2016/2020; 147147: solo 2024), es decir, la corrección de
emparejamiento de fuente 3 documentada el 2026-09-13 no fusionó este caso
real. `fn_atleta_info` lo muestra correctamente como candidatos en vez de
ocultar el problema fusionándolos o eligiendo uno; no se corrigió el ETL
en ese momento por estar fuera de alcance de esta tarea (incisos d/e),
pero quedó señalado para no perderlo (ver actualizaciones más abajo,
donde el caso se termina resolviendo).

**Alternativas consideradas:** (a) Elegir el primer `atleta_id` por
orden/fecha (rechazada: exactamente el error que ya se detectó y corrigió
en el ETL el 2026-09-13, reintroducirlo en la capa de consulta sería
retroceder); (b) fallar/lanzar excepción ante ambigüedad (rechazada:
quien consulta necesita ver quiénes son los candidatos, no solo que hay
ambigüedad).

**Estado:** Resuelto para el propósito de este inciso (`fn_atleta_info`
maneja el caso correctamente, muestre o no el ETL duplicados). El caso
Fajdek en sí, ver dimensionamiento completo y causa raíz abajo, queda
documentado y finalmente resuelto en la actualización de la noche del
2026-09-14.

### Actualización 2026-09-14 (tarde): dimensionamiento del hallazgo Fajdek

**Contexto:** Antes de asumir que Fajdek era un caso aislado, se corrió
un chequeo sobre **toda** la tabla `atleta` (153,473 filas, no solo la
muestra de 30+30 del 2026-09-13), agrupando por `nombre_completo`
plegado (acentos/mayúsculas, misma normalización que `fn_atleta_info`)
y por separado por `nombre_usado` cruzando específicamente registros de
fuente 1 (`nombre_completo` no nulo, garantizado por el `fillna` en
`build_atleta`) contra registros agregados por la extensión de fuente
3/2024 (`nombre_completo` siempre `NULL` por construcción, ver
`build_atleta_extension_f3` en `etl/etl.py`).

**Resultado (evidencia real, no estimación):**
- **727 grupos** de nombre completo idéntico tras plegar en toda la
  tabla (1,038 pares, 1,586 atletas). La revisión de una muestra de 30
  grupos muestra que son, en su enorme mayoría, **homónimos genuinos**
  (personas reales distintas con el mismo nombre): fechas de nacimiento
  muy distintas y/o nacionalidades distintas en casi todos los casos
  (por ejemplo "Abdul Aziz" Pakistán 1935 vs. 1924; "Andrea Thomas"
  Canadá vs. Jamaica). Esto **no es un bug**, es exactamente el
  escenario para el que se diseñó el modo `CANDIDATO` de
  `fn_atleta_info`, y confirma que los homónimos son comunes en un
  dataset de 128 años y 200+ países, no una rareza de 2 casos.
- **170 grupos** cruzan específicamente la frontera fuente 1 y
  extensión fuente 3/2024 (173 filas de la extensión, 245 candidatos de
  fuente 1 involucrados). Este es el subconjunto que importa para la
  pregunta de Fajdek, porque es la misma frontera de carga donde ya se
  sabe que el emparejamiento puede fallar. Desglose completo, sin
  categorías superpuestas (partición exhaustiva de los 170):
  ```
  170 grupos totales
  |-- 46 con >1 candidato en fuente 1 con ese nombre
  |     (ambigüedad, rechazo correcto, comportamiento ya esperado)
  |-- 3  con >1 fila nueva de fuente 3 con ese nombre
  `-- 121 "1 a 1" (un candidato de fuente 1, una fila nueva de fuente 3)
        |-- 30 misma nacionalidad, candidato de fuente 1 vivo
        |     (patrón tipo Fajdek, candidato a fusión real)
        |--  2 misma nacionalidad, candidato de fuente 1 ya fallecido
        |     (correctamente excluido por el criterio "vivo")
        |-- 78 nacionalidad distinta, candidato vivo
        |     (homónimos genuinos, correctamente no fusionados)
        `-- 11 nacionalidad distinta, candidato ya fallecido
              (doblemente descartado, no es un bug)
  ```
  De los 30 casos "misma nacionalidad y vivo", la muestra revisada a
  mano confirma un patrón sistemático, no aleatorio: nombres polacos
  (Aleksandra Mirosław/Miroslaw, Anita Włodarczyk/Wlodarczyk, Anna
  Puławska/Pulawska, Bartosz Łosiak/Losiak, Cyprian Mrzygłód/Mrzyglod,
  Grzegorz Łomacz/Lomacz, Hanna Łyczbińska/Lyczbinska), turcos (Beste
  Kaynakçı/Kaynakci, Deniz Çınar/Cinar, Ferhat Arıcan/Arican, Hande
  Baladın/Baladin) y nórdicos (Helene Næss/Naess), todos con la misma
  nacionalidad a ambos lados, casi con certeza la misma persona real.

**Causa raíz confirmada (no solo sospechada):** `name_match_key()` en
`etl/etl.py` pliega acentos con `unicodedata.normalize("NFKD", ...)` y
remoción de marcas combinantes. Esto funciona para letras con
diacrítico compuesto por descomposición (`é` a `e`+´, `á` a `a`+´, `ñ` a
`n`+~), pero no para letras que son un carácter Unicode propio sin
descomposición de compatibilidad a ASCII, como la `ł` polaca (U+0142),
la `ı` turca, o la `æ` nórdica; verificado directamente:
`unicodedata.normalize('NFKD', 'ł')` devuelve `'ł'` sin cambios. Por eso
el caso Fajdek (y los casos análogos) no fue cubierto por la corrección
de acentos del 2026-09-13 pese a que esa auditoría lo citó por nombre
como uno de los 4 falsos negativos "corregidos". La corrección resolvió
el criterio de aceptación (vivo más nacionalidad consistente) pero no
el plegado de caracteres en sí para este subconjunto de alfabetos. Nota:
`fn_normalizar()` en `sql/procedures.sql` (que usa la extensión
`unaccent` de Postgres, con tabla de transliteración más completa que
NFKD) sí pliega correctamente `ł` a `l`, `ı` a `i`, etc., confirmado en
las pruebas de este archivo (la búsqueda SQL "Pawel Fajdek" sí encontró
ambos `atleta_id`). El gap era específico del lado Python del ETL, no
de las funciones SQL de este archivo.

**Confirmación directa sobre Fajdek:** es un caso de la extensión
fuente 3/2024, no un duplicado interno de fuente 1 (`atleta_id=147147`
tiene `nombre_completo IS NULL`, marca exclusiva de
`build_atleta_extension_f3`, y su única participación es 2024; no hay
ningún otro registro de Fajdek en fuente 1 aparte del 120119 ya
existente desde antes de esta corrida).

### Actualización 2026-09-14 (noche): búsqueda de atletas 2024 verificada y fix aplicado

**0) ¿Los ~7,973 atletas exclusivos de 2024 son buscables por nombre?**
Verificado que sí, ya lo eran antes de cualquier cambio: el `WHERE
f_normalizar(nombre_usado) = ... OR f_normalizar(nombre_completo) =
...` en `fn_atleta_info` usa `OR`, y `nombre_usado` está garantizado
poblado para toda fila de `atleta` (tanto fuente 1 como la extensión
fuente 3, ver `build_atleta_extension_f3`: `nuevos["nombre_usado"] =
nuevos["Name"].apply(normalize_ws)`, nunca `NULL`). Prueba directa: 3
atletas al azar con `nombre_completo IS NULL` (Vicki Elmes, Thomas
Heilman, Daniel Coyle), buscados por su `nombre_usado` tal cual está en
la tabla, dieron como resultado los 3 encontrados correctamente en modo
`DETALLE`. No era un bug, no se tocó código por este punto.

**2) Fix del plegado de acentos aplicado (no solo documentado).** Se
reemplazó `unicodedata.normalize("NFKD", ...)` por
`text_unidecode.unidecode()` en `name_match_key()` (`etl/etl.py`),
agregado `text-unidecode` a `etl/requirements.txt` (ya estaba instalado
como dependencia transitiva de `kaggle` a través de `python-slugify`,
ahora es dependencia directa declarada). Verificado:
`unidecode('Paweł Fajdek')` da `'Pawel Fajdek'`, `unidecode('Anita
Włodarczyk')` da `'Anita Wlodarczyk'`, `unidecode('Deniz Çınar')` da
`'Deniz Cinar'`, `unidecode('Helene Næss')` da `'Helene Naess'`.

**Re-verificación de falsos positivos (pedido explícito):** se
recorrió la comparación de colisiones sobre toda la tabla
`nombre_usado` con la clave vieja vs. la clave nueva. Aparecen 54
grupos de colisión que no existían con NFKD. Clasificados los 54 sin
excepción:
- **30** son exactamente los pares fuente 1 y fuente 3 confirmados por
  el algoritmo (mismo criterio "vivo más nacionalidad consistente" que
  ya usaba `build_atleta_extension_f3`, sin aflojarlo, ver detalle
  abajo).
- **24** son colisiones puramente internas a fuente 1 (ambos lados con
  `nombre_completo` no nulo; por ejemplo varios "Sørensen"/"Jørgensen"
  daneses, "Sigurðsson"/"Guðmundsson" islandeses, que por convención de
  nombres patronímicos son extremadamente comunes en esos países).
  Fuera de alcance de este fix (el algoritmo de
  `build_atleta_extension_f3` nunca intenta fusionar fuente 1 contra
  fuente 1, solo fuente 3 contra fuente 1) y no se tocaron. Quedan
  señaladas aquí como posible pregunta a futuro (¿son duplicados reales
  o son homónimos legítimos de un país con apellidos patronímicos
  repetidos? no se investigó, no bloquea nada).
- **0** son falsos positivos del propio criterio de aceptación: el
  chequeo de nacionalidad consistente siguió rechazando correctamente
  los casos de nacionalidad distinta (por ejemplo "Lars Jorgensen" USA
  vs. "Lars Jørgensen" Dinamarca resultó ser un grupo puramente interno
  de fuente 1, ni siquiera pasó por la salvaguarda).

**Los 30 pares confirmados** (re-ejecutando el algoritmo exacto de
`build_atleta_extension_f3` contra el estado ya cargado de `atleta`, con
el nuevo plegado): todos con motivo `nacionalidad_consistente` (ninguno
forzado por "candidato único sin nacionalidad conocida"). Verificado 0
conflictos con `UNIQUE(atleta_id, edicion_id, evento_id)` de
`PARTICIPACION` antes de tocar nada (todas las participaciones del lado
fuente 3 son de la edición 2024, que fuente 1 no cubre). Lista completa
de los 30 pares en `sql/fusion_atletas_2024_folding.sql`.

**Aplicación a la base de datos: ejecutada y verificada.** Se aplicó
manualmente contra la base real, tras revisión y con autorización
explícita, el script `sql/fusion_atletas_2024_folding.sql`. El script
terminó en `COMMIT` sin errores (ninguna validación interna abortó), y
se confirmaron los conteos exactos esperados:

| Tabla | Antes | Después | Esperado |
|---|---:|---:|---:|
| `atleta` | 153,473 | **153,443** | -30 exacto |
| `participacion` | 314,108 | **314,108** | sin cambio |
| `resultado` | 314,623 | **314,623** | sin cambio |

Verificación adicional post-fusión: los 30 `atleta_id` viejos ya no
existen en `atleta`; 0 filas de `participacion` quedaron apuntando a un
`atleta_id` inexistente; `fn_atleta_info('Pawel Fajdek', 120119)` ahora
muestra las 4 ediciones (2012, 2016, 2020, 2024) unificadas bajo un
solo `atleta_id`, donde antes 2024 aparecía como una persona aparte.

**Alternativas consideradas:** (a) Re-correr el ETL completo desde los
CSV crudos con el `name_match_key` corregido (rechazada para esta
corrección puntual: requiere credenciales de Kaggle no disponibles en
este entorno y volvería a ejecutar las ~14,892 filas de fuente 3 desde
cero con mayor riesgo, cuando el problema real son solo 30 filas ya
identificadas con precisión); (b) dejarlo como duplicado y resolverlo
solo en la capa de consulta (rechazada: el enunciado pidió
explícitamente arreglar el dato, no solo el síntoma, y el criterio del
equipo prioriza corregir la carga sobre parchear en la capa de arriba).

**Estado:** Resuelto por completo. `name_match_key()` ya usa `unidecode`
(no vuelve a introducir este gap en corridas futuras del ETL) y los 30
casos reales ya identificados se fusionaron en la base de datos real,
con los conteos exactos esperados confirmados. El caso de los 24 grupos
internos a fuente 1 (patronímicos nórdicos/islandeses, ver arriba) queda
fuera de alcance, no investigado; es una pregunta distinta
(deduplicación dentro de fuente 1 misma) que no fue parte de lo pedido.

## [2026-09-14] Multi-NOC histórico por país (inciso e)

**Contexto:** El modelo ya documenta (ver "No hay FK directa NOC ->
ATLETA" arriba) que un país puede corresponder a más de un `codigo_noc`
a lo largo de la historia. Ejemplo ya cargado: Alemania = `GER`+`FRG`+
`GDR` (los 3 con `noc.pais_id` apuntando al mismo país, nunca forzado a
NULL). Caso más delicado: `URS` (URSS) y `EUN` (Equipo Unificado 1992)
tienen `noc.pais_id` forzado a NULL a propósito en el ETL
(`NOC_FORCE_NULL_PAIS`, ver entrada del 2026-09-12 arriba); la fuente
original trae `region='Russia'` para ambos, pero se decidió no
atribuirlos a un país sucesor. Antes de "corregir" esto agregándolos a
la fuerza al `pais_id` de Rusia en la nueva función, lo que
contradiría esa decisión ya tomada, se buscó una forma de recuperarlos
sin tocar esa decisión ni hardcodear un mapeo país por país.

**Decisión:** `fn_noc_por_pais(pais)` agrega dos conjuntos: (1) todo
`codigo_noc` con `pais_id` igual al país buscado
(`categoria='PAIS_ACTUAL'`), y (2) todo `codigo_noc` cuyo `nombre_region`
coincide textualmente con el `nombre_region` de algún NOC ya incluido en
(1), aunque su `pais_id` sea NULL
(`categoria='ENTIDAD_HISTORICA_NO_ATRIBUIDA'`). Esto funciona sin
hardcodear países porque `RUS` y `URS`/`EUN` comparten literalmente
`nombre_region='Russia'` en la tabla ya cargada (y `GER`/`FRG`/`GDR`
comparten `nombre_region='Germany'`); se aprovecha un dato que ya está
en la base de datos en vez de adivinar equivalencias. `fn_pais_info`
usa esta función para agregar participaciones y medallas de todos los
NOC de ambas categorías, mostrando además una sección `NOC_ASOCIADO`
que lista explícitamente cuáles se agregaron y por qué categoría, para
que quede auditable.

**Verificado contra datos reales** (la bitácora tiene la salida
completa):
- `Germany` da 4 NOC, no 3 como se esperaba: `GER`, `FRG`, `GDR` más
  `SAA` (Saar/Saarland, equipo propio 1952-1956 antes de reintegrarse a
  Alemania), capturado automáticamente por compartir
  `nombre_region='Germany'`, sin haber sido anticipado en el enunciado.
- `Russian Federation` (y también la forma parcial `Russia`) da 3 NOC:
  `RUS` (`PAIS_ACTUAL`) más `EUN` y `URS`
  (`ENTIDAD_HISTORICA_NO_ATRIBUIDA`). Medallero agregado: Oro 1,575 /
  Plata 1,135 / Bronce 1,158 (suma de los 3 códigos).
- `Germany` medallero agregado (GER+FRG+GDR+SAA): Oro 1,354 / Plata
  1,302 / Bronce 1,331.
- Sede: `United States` tiene 8 ediciones (1904, 1932 dos veces, 1960,
  1980, 1984, 1996, 2002); `France` tiene 6 ediciones (incluye París
  1900, 1924 y 2024). `Guatemala` da sección `NUNCA_SEDE` explícita (no
  lista vacía sin explicación). País inexistente (`Wakanda`) da sección
  `PAIS_NO_ENCONTRADO` explícita, distinta de `NUNCA_SEDE`.

**Limitación documentada, no oculta:** `pais.nombre` sigue la
convención del Banco Mundial en inglés (por ejemplo `"Russian
Federation"`, no `"Rusia"`; `"Germany"`, no `"Alemania"`). La búsqueda
en `fn_noc_por_pais` es insensible a acentos/mayúsculas y admite
coincidencia parcial (por eso `"Russia"` sin más calza con `"Russian
Federation"`), pero no traduce gentilicios en español. No se implementó
una tabla de alias español-inglés por estar fuera del alcance pedido
(normalizar el nombre del país en acentos/mayúsculas, no traducción).

**Alternativas consideradas:** (a) Filtrar solo por `noc.pais_id =
pais_id` (rechazada: es exactamente el problema que el enunciado pidió
prevenir, habría devuelto un único NOC para Alemania/Rusia); (b)
mantener una tabla hardcodeada de qué NOC históricos corresponden a qué
país (rechazada: mismo motivo que se rechazó hardcodear equivalencias de
`EVENTO` el 2026-09-13, no escala, propensa a quedar incompleta, y
contradice la decisión ya tomada de no atribuir estas entidades a un
sucesor si no es necesario); (c) traducir gentilicios español-inglés
para `p_pais` (rechazada por alcance: el enunciado solo pidió
acentos/mayúsculas, se documenta como limitación conocida en vez de
adivinar una tabla de equivalencias incompleta).

**Estado:** Resuelto.

## [2026-09-14] `unaccent` quedó instalada en el schema `olimpiadas`, no `public`

**Contexto:** `CREATE EXTENSION IF NOT EXISTS unaccent;` se ejecutó
justo después de `SET search_path TO olimpiadas;` al inicio de
`sql/procedures.sql`, así que Postgres instaló sus objetos en el primer
schema del `search_path` vigente en ese momento: `olimpiadas`, no
`public` (donde suele vivir por convención). `f_normalizar()` llamaba a
`unaccent(...)` sin calificar el schema, apoyándose implícitamente en
que el `search_path` de quien la invoque incluya `olimpiadas`, lo cual
no es cierto por defecto (`search_path` por defecto de una sesión
nueva: `"$user", public`). Se detectó al probar `fn_atleta_info` desde
una conexión nueva sin `SET search_path` previo:
`ERROR: function unaccent(text) does not exist`.

**Decisión:** se calificó la llamada como `olimpiadas.unaccent(...)`
dentro de `f_normalizar`, igual que el resto de las funciones de este
archivo (todas usan `olimpiadas.` explícito en cada referencia a tabla u
otra función, precisamente para no depender del `search_path` de quien
llama). Verificado que `fn_atleta_info`, `fn_pais_info` y ambas `CALL
pr_..._info` funcionan correctamente desde una conexión nueva con
`search_path` por defecto (`"$user", public`), sin ningún `SET
search_path` previo.

**Alternativas consideradas:** instalar la extensión explícitamente con
`CREATE EXTENSION unaccent SCHEMA public;` (rechazada: cambiaría un
comportamiento ya aplicado a la BD real sin necesidad; calificar la
única llamada que la usa es un cambio más chico y suficiente).

**Estado:** Resuelto.

## [2026-09-14] Verificación de `poblacion_pais`: no estaba omitida, faltaba en los resúmenes de conteo

**Contexto:** A lo largo de esta serie de tareas (incisos d/e, fusión de
atletas de 2024, limpieza de estilo) los resúmenes de conteo citados
solo mencionaban `atleta`, `participacion` y `resultado`. Esto generó la
duda de si `poblacion_pais` (población histórica por país y año, ver
`modelo_er_proyecto1.md`) se había cargado alguna vez.

**Verificación (no se asumió, se consultó la base real):** `SELECT
count(*) FROM olimpiadas.poblacion_pais` devuelve **13,026 filas**,
exactamente el número que ya figura en `etl/REPORTE.md` (sección de
conteos y en las tres corridas registradas en el historial) desde la
carga inicial del 2026-09-12. La tabla sí se cargó desde
`populations.csv` (fuente 1) en la primera corrida del ETL y no volvió
a cambiar en ninguna corrida posterior, porque ninguna extensión de
fuente 2 o fuente 3 aporta datos de población.

**Conclusión:** no hubo ningún descuido del ETL ni una decisión sin
documentar. La tabla estaba correctamente cargada y documentada en
`etl/REPORTE.md` desde el principio; lo que faltaba era incluirla en
los resúmenes rápidos de esta serie de tareas, que por costumbre solo
citaban las tres tablas más grandes. Conteo completo de las 10 tablas
del modelo, verificado en esta misma revisión:

| Tabla | Filas |
|---|---:|
| pais | 204 |
| poblacion_pais | 13,026 |
| noc | 236 |
| sede | 43 |
| atleta | 153,443 |
| edicion_olimpica | 55 |
| deporte | 96 |
| evento | 2,103 |
| participacion | 314,108 |
| resultado | 314,623 |

Todos los valores coinciden con el último estado conocido tras la
fusión de los 30 atletas duplicados (`atleta` bajó de 153,473 a
153,443 exactamente por esa fusión; el resto no cambió). No se aplicó
ningún cambio a `poblacion_pais` ni a ninguna otra tabla en esta
revisión.

**Estado:** Resuelto. `poblacion_pais` está correctamente cargada; de
ahora en adelante los resúmenes de conteo de este proyecto incluyen las
10 tablas completas, no solo un subconjunto.
