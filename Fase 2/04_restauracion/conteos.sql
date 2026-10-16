SELECT 'pais', count(*) FROM olimpiadas.pais
UNION ALL SELECT 'poblacion_pais', count(*) FROM olimpiadas.poblacion_pais
UNION ALL SELECT 'noc', count(*) FROM olimpiadas.noc
UNION ALL SELECT 'sede', count(*) FROM olimpiadas.sede
UNION ALL SELECT 'edicion_olimpica', count(*) FROM olimpiadas.edicion_olimpica
UNION ALL SELECT 'deporte', count(*) FROM olimpiadas.deporte
UNION ALL SELECT 'deporte_equivalencia', count(*) FROM olimpiadas.deporte_equivalencia
UNION ALL SELECT 'evento', count(*) FROM olimpiadas.evento
UNION ALL SELECT 'atleta', count(*) FROM olimpiadas.atleta
UNION ALL SELECT 'participacion', count(*) FROM olimpiadas.participacion
UNION ALL SELECT 'resultado', count(*) FROM olimpiadas.resultado;