# Parches históricos

Estos scripts ya están integrados en `db/init/01_schema.sql` — se
conservan aquí solo como referencia histórica y como plantilla de estilo
para futuros parches (ver sección 5 de `CLAUDE.md` en la raíz del
proyecto). Si tu base de datos se creó ANTES de estos fixes, aplícalos en
orden sobre tu base existente; si tu base salió de un
`docker compose up` reciente, no necesitas correrlos — ya están incluidos.
