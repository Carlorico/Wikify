#!/bin/sh
# Avvio di Wikify con la cartella dati tenuta fuori dalla cartella di progetto.
#
# I dati di lavoro (database SQLite, chiave di sessione, temporanei di import)
# risiedono in "dati/lavoro" dentro la cartella di progetto, esclusa dal
# repository tramite .gitignore: restano locali e non entrano nelle copie
# condivise. Per la base dati della demo: ARCHIVIO_SMART_DATA=../dati/demo
# Per usare un percorso diverso basta valorizzare ARCHIVIO_SMART_DATA prima
# di lanciare questo script.

APP_DIR=$(cd "$(dirname "$0")" && pwd)

if [ -z "$ARCHIVIO_SMART_DATA" ]; then
    ARCHIVIO_SMART_DATA=$(cd "$APP_DIR/.." && pwd)/dati/lavoro
fi
export ARCHIVIO_SMART_DATA

mkdir -p "$ARCHIVIO_SMART_DATA"
echo "Cartella dati: $ARCHIVIO_SMART_DATA"
echo "Indirizzo:     http://127.0.0.1:${WIKIFY_PORT:-5000}"

cd "$APP_DIR" || exit 1
exec python3 app.py
