// Fase C4: crea los indices DESPUES de cargar los datos (la carga es mas rapida sin indices).
// Uso: mongosh "mongodb://localhost:57017/olimpiadas_mongo" 05_indices/crear_indices.js
// No hay indices de texto ($text). Las busquedas por prefijo usan regex anclado (^prefijo) sin la opcion i,
// sobre campos ya plegados (nombre_key, atleta_nombre_key).

const ini = new Date();
const idx = (col, spec, opts) => { const n = db[col].createIndex(spec, opts || {}); print(col + ": " + n); };

// atletas
idx("atletas", { nombre_key: 1 });
idx("atletas", { tokens: 1 });                                         // multikey: coincidencia parcial por palabras
idx("atletas", { "participaciones.anio": 1, "participaciones.deporte": 1 });
idx("atletas", { claves: 1 });                                         // multikey: nombre usado, completo y alias (busqueda exacta)
// participaciones
idx("participaciones", { atleta_id: 1, anio: 1 });
idx("participaciones", { pais_id: 1, es_yog: 1, anio: 1, deporte: 1 });
idx("participaciones", { pais_id: 1, medalla: 1 });
idx("participaciones", { noc: 1, anio: 1 });
// paises
idx("paises", { nombre_key: 1 }, { unique: true });
idx("paises", { "nocs.codigo": 1 });
idx("paises", { tokens: 1 });
// catalogos
idx("deportes", { nombre_key: 1 }, { unique: true });
idx("ediciones", { anio: 1, tipo: 1 }, { unique: true });
print("Fin: " + new Date().toISOString() + " (inicio " + ini.toISOString() + ")");
