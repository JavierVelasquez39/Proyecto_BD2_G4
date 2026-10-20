# Infraestructura de la Fase 3

## MongoDB

- Imagen `mongo:7`, contenedor `olimpiadas_mongo`, puerto del host **57017**.
- Volumen persistente `olimpiadas_mongo_data`: los datos sobreviven a
  `docker compose down` y a reinicios. Solo se pierden con `docker compose down -v`.
- Base de datos de la Fase 3: `olimpiadas_mongo`.

```
docker compose up -d
mongosh "mongodb://localhost:57017/olimpiadas_mongo"
```

## PostgreSQL (origen de la migracion)

Contenedor `olimpiadas_pg` de la Fase 1, puerto 55433, esquema `olimpiadas`.
No se modifica sin respaldo previo.

## Respaldos

`backups/` contiene los `pg_dump -Fc` tomados antes de cualquier cambio, con fecha y hora
en el nombre. Restauracion: `pg_restore -d <base_de_prueba> <archivo>.dump`.

## Dependencias Python

`pip install -r requirements.txt` (pymongo, psycopg2-binary).
