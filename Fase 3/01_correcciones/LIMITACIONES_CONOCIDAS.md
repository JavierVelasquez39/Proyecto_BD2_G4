# Limitaciones conocidas de la base corregida (Fase 3)

Todo lo que sigue se decidio no corregir, con su motivo y su conteo. Fecha: 2026-10-19.

## Paris 2024

- **199 eventos que solo existen en 2024.** Conservan la nomenclatura de la fuente 3 ("Men -60 kg", "Men's 1500m",
  "Women's Four") distinta de la de la fuente 1 ("Half-Lightweight, Men (Olympic)"). No se unificaron: exigiria una
  tabla de equivalencias de categorias hecha a mano. No afecta ningun medallero ni consulta por atleta o pais.
  Se nota solo en que el nombre del evento mezcla dos estilos.
- **3 pseudo-eventos de la fuente 3 sin medallas:** gimnasia artistica "Men" (96 filas) y "Women" (94 filas),
  natacion "Relay Only Athlete" (157 filas).
- **Lasse Luhrs** (Alemania, oro en el relevo mixto de triatlon) no existe en `atleta` y no se creo el registro. El
  relevo aleman figura con 3 de sus 4 atletas. Las medallas por evento coinciden con el medallero oficial.

## Atletas duplicados (B2)

Se fusionaron 394 pares (393 en las fases 1 y 2 y, el 2026-10-20, Shun Wang con Wang Shun tras una re-verificacion individual: nacimiento 11-feb-1994, resultados 2012, 2016, 2020 y bronce de Paris 2024 en 200 m estilos). No se fusionaron:

| Motivo | Pares ALTA | Detalle |
|---|---:|---|
| Deportes de equipo grandes (futbol, hockey, baloncesto, voleibol, balonmano, waterpolo, rugby 7) | 48 | Excluidos del bloque por decision; 10 de 10 verificados resultaron correctos. Se retoman solo si sobra tiempo |
| No verificables | 12 | 6 de orden invertido (Wang Zifeng, Siyu, Jianan; Zhang Dong; Liu Hong, Liu Xiaoxin) y 6 de subconjunto |
| Verificados como INCORRECTOS | 4 | Wang Zhen (marchista y saltador distintos), Julio Enciso, "de Maria" / Maria de Souza, "van Gert-jan" / Gert Jan van Woudenberg |
| Revision individual pendiente | 1 | Genevieve Gregson (disciplina de atletismo no coincide) |
| El otro registro es tambien de la fuente 3 | 1 | No hay registro historico que conservar |
| **Total ALTA no fusionados** | **66** | |

- **218 atletas de la fuente 3 con nombre "particula + nombre de pila"** (ejemplo "van Wayde", "de Alejandro"): el
  apellido se perdio en la fuente 3. Se fusionaron 40 (con candidato verificado); **quedan 178**, de los cuales
  140 no tienen ningun candidato en la base. No se puede recuperar el apellido sin otra fuente.
- **Pares de confianza MEDIA (69 sin fusionar) y BAJA (418):** no se fusionaron. Los 251 pares descartados lo fueron
  por sexo distinto, atleta fallecido o coincidencia en el mismo evento de 2024.
- **Verificacion contra Wikipedia por muestreo:** 102 pares auditados de 459 ALTA. Los fusionados sin auditoria
  individual descansan en el criterio (mismo sexo, NOC y deporte en comun, candidato unico, filtros de ultimo anio,
  edad y disciplina) y en las muestras: 49 de 52 correctos en subconjunto (los 3 incorrectos los atrapan los filtros)
  y 35 de 36 en orden invertido (el incorrecto lo atrapa el filtro de disciplina). El riesgo residual de algun
  homonimo del mismo pais y deporte no se puede descartar.
- **Busqueda por el nombre antiguo:** las funciones de la Fase 1 (`fn_atleta_info`) no buscan por el nombre del
  duplicado fusionado ("Shiyu Lu" ya no responde). En MongoDB el nombre original queda como alias.

## Heredado de la Fase 1

- **Grupos de apellidos patronimicos** (danes e islandes, informe de la Fase 1, seccion 8): la Fase 1 reporto 24
  grupos de colision internos a la fuente 1 (nombres que solo coinciden al plegar con `unidecode` y no con NFKD).
  En la Fase 3 se intento reproducir esa cifra con el mismo criterio de plegado sobre los atletas de la fuente 1
  (`atleta_id` hasta 145,500) y solo se reproducen **3 grupos (6 atletas)**, tanto con `nombre_usado` como con
  `nombre_completo` (con este ultimo, 1 grupo de 2 atletas). La lista de los 3 grupos esta en
  `datos/patronimicos_f1_pendientes.csv`. No se determino por que la cifra de la Fase 1 era 24: el informe no
  detalla la consulta exacta que la produjo (posiblemente otra clave de agrupacion o un conteo sobre la tabla con la
  extension de la fuente 3, anterior a las fusiones).
  **Por que no se investigaron:** (1) son colisiones entre atletas de la misma fuente, y el algoritmo de la Fase 1
  nunca fusiona fuente 1 contra fuente 1; (2) distinguir homonimos legitimos de duplicados en apellidos patronimicos
  exige fecha de nacimiento y deporte caso por caso, sin una fuente externa que lo resuelva de forma masiva; (3) por
  decision del equipo, tras cerrar las fusiones de la fuente 3 no se abrieron nuevos frentes de limpieza de datos.
  Se desconoce, por tanto, si son duplicados o homonimos legitimos; el impacto es acotado a como maximo 3 pares.
- Se mantienen las demas limitaciones de la seccion 8 del informe de la Fase 1 (gentilicios en espanol, 3 ediciones sin
  ciudad real, altura y peso constantes por atleta, fuente 4 no verificada).
