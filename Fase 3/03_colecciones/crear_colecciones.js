// Fase C2: crea las colecciones de la base olimpiadas_mongo con validadores $jsonSchema.
// Uso: mongosh "mongodb://localhost:57017/olimpiadas_mongo" 03_colecciones/crear_colecciones.js
// Recrea las colecciones (las borra si existen): se ejecuta ANTES de cargar los datos.
// Los indices se crean despues de la carga (05_indices/crear_indices.js).

const ini = new Date();
const num = ["int", "long"];
const numN = ["int", "long", "null"];
const strN = ["string", "null"];
const medallas = {
  bsonType: "object", required: ["oro", "plata", "bronce"],
  properties: { oro: { bsonType: num }, plata: { bsonType: num }, bronce: { bsonType: num } },
};
const medalleroTres = {
  bsonType: "object", required: ["total", "sin_yog", "yog"],
  properties: { total: medallas, sin_yog: medallas, yog: medallas },
};
const resultado = {
  bsonType: "object", required: ["lugar", "empatado", "medalla"],
  properties: { lugar: { bsonType: numN }, empatado: { bsonType: "bool" }, medalla: { enum: ["Oro", "Plata", "Bronce", null] } },
};
const camposParticipacion = {
  anio: { bsonType: num }, tipo: { enum: ["Verano", "Invierno", "Verano-YOG", "Invierno-YOG"] },
  es_yog: { bsonType: "bool" }, edicion_id: { bsonType: num }, sede: { bsonType: strN },
  deporte_id: { bsonType: num }, deporte: { bsonType: "string" }, evento_id: { bsonType: num }, evento: { bsonType: "string" },
  noc: { bsonType: strN }, pais_id: { bsonType: numN }, pais: { bsonType: strN }, equipo: { bsonType: strN },
  edad: { bsonType: numN }, altura_cm: { bsonType: ["double", "int", "long", "null"] }, peso_kg: { bsonType: ["double", "int", "long", "null"] },
  resultados: { bsonType: "array", items: resultado },
  medalla: { enum: ["Oro", "Plata", "Bronce", null] },
  medallas: { bsonType: "array", items: { enum: ["Oro", "Plata", "Bronce"] } },
};
const reqParticipacion = ["anio", "tipo", "es_yog", "edicion_id", "deporte", "evento", "resultados", "medallas"];

const defs = {
  atletas: {
    bsonType: "object",
    required: ["_id", "nombre_usado", "nombre_key", "claves", "tokens", "alias", "deportes", "nocs", "n_participaciones", "resumen_medallas", "participaciones"],
    properties: {
      _id: { bsonType: num }, nombre_usado: { bsonType: "string" }, nombre_completo: { bsonType: strN },
      nombre_key: { bsonType: "string" }, claves: { bsonType: "array", items: { bsonType: "string" } },
      tokens: { bsonType: "array", items: { bsonType: "string" } },
      alias: { bsonType: "array", items: { bsonType: "object", required: ["nombre", "tipo", "id_duplicado"] } },
      sexo: { enum: ["M", "F", null] }, nacionalidad: { bsonType: strN },
      fecha_nacimiento: { bsonType: ["date", "null"] }, fecha_fallecimiento: { bsonType: ["date", "null"] },
      ciudad_nacimiento: { bsonType: strN }, pais_nacimiento: { bsonType: strN },
      deportes: { bsonType: "array", items: { bsonType: "string" } }, nocs: { bsonType: "array", items: { bsonType: "string" } },
      n_participaciones: { bsonType: num }, resumen_medallas: medalleroTres,
      participaciones: {
        bsonType: "array",
        items: { bsonType: "object", required: ["participacion_id", "atleta_id"].concat(reqParticipacion),
                 properties: Object.assign({ participacion_id: { bsonType: num }, atleta_id: { bsonType: num } }, camposParticipacion) },
      },
    },
  },
  participaciones: {
    bsonType: "object",
    required: ["_id", "atleta_id", "atleta_nombre", "atleta_nombre_key"].concat(reqParticipacion),
    properties: Object.assign({ _id: { bsonType: num }, atleta_id: { bsonType: num }, atleta_nombre: { bsonType: "string" }, atleta_nombre_key: { bsonType: "string" } }, camposParticipacion),
  },
  paises: {
    bsonType: "object",
    required: ["_id", "tipo", "nombre", "nombre_key", "tokens", "nocs", "sedes", "medallero", "medallero_por_evento", "por_edicion", "por_deporte"],
    properties: {
      tipo: { enum: ["PAIS", "ENTIDAD"] }, nombre: { bsonType: "string" }, nombre_key: { bsonType: "string" },
      tokens: { bsonType: "array", items: { bsonType: "string" } },
      nocs: { bsonType: "array", items: { bsonType: "object", required: ["codigo", "categoria"],
              properties: { codigo: { bsonType: "string" }, categoria: { enum: ["PAIS_ACTUAL", "ENTIDAD_HISTORICA_NO_ATRIBUIDA", "ENTIDAD_SIN_PAIS"] } } } },
      sedes: { bsonType: "array", items: { bsonType: "object", required: ["anio", "tipo", "es_yog", "ciudad"] } },
      total_participaciones: { bsonType: num }, total_atletas: { bsonType: num },
      medallero: medalleroTres, medallero_por_evento: medalleroTres,
      por_edicion: { bsonType: "array", items: { bsonType: "object", required: ["anio", "tipo", "es_yog", "participaciones", "atletas", "por_atleta", "por_evento"] } },
      por_deporte: { bsonType: "array", items: { bsonType: "object", required: ["deporte", "es_yog", "participaciones", "por_atleta", "por_evento"] } },
    },
  },
  ediciones: {
    bsonType: "object", required: ["_id", "anio", "tipo", "es_yog", "sede"],
    properties: { anio: { bsonType: num }, tipo: { enum: ["Verano", "Invierno", "Verano-YOG", "Invierno-YOG"] }, es_yog: { bsonType: "bool" }, sede: { bsonType: "object" } },
  },
  deportes: {
    bsonType: "object", required: ["_id", "nombre", "nombre_key", "n_eventos"],
    properties: { nombre: { bsonType: "string" }, nombre_key: { bsonType: "string" }, n_eventos: { bsonType: num } },
  },
};

for (const [nombre, esquema] of Object.entries(defs)) {
  if (db.getCollectionNames().includes(nombre)) db[nombre].drop();
  db.createCollection(nombre, { validator: { $jsonSchema: esquema }, validationLevel: "strict", validationAction: "error" });
  print("coleccion creada: " + nombre);
}
print("Fin: " + new Date().toISOString() + " (inicio " + ini.toISOString() + ")");
