# Sauvegarde et restauration PostgreSQL

```bash
# Sauvegarde (format custom, compressé)
pg_dump -h 127.0.0.1 -U hotel_user -Fc hotel_db > backups/hotel_$(date +%F).dump

# Restauration dans une base vide
createdb -h 127.0.0.1 -U hotel_user hotel_db_restore
pg_restore -h 127.0.0.1 -U hotel_user -d hotel_db_restore --no-owner backups/hotel_2026-10-18.dump
```
Planifiez la sauvegarde chaque nuit (cron / Planificateur de tâches) et **testez la restauration** régulièrement.
Pensez aussi à sauvegarder `backend/media/` (images des chambres).
