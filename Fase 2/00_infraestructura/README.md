# 00_infraestructura

Contiene la configuración de Docker Compose para levantar las instancias de PostgreSQL 17 necesarias para las corridas de la Fase 2.

## Uso

Para levantar una instancia con un nombre de proyecto específico (`fase2_<tipo>`):

```bash
docker compose -p fase2_anio up -d