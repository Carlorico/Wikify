#!/bin/sh
# Avvio di Wikify con la cartella dati tenuta fuori dalla cartella di progetto.
#
# I dati di lavoro (database SQLite, chiave di sessione, temporanei di import)
# risiedono in "Wikify_dati", cartella sorella di "Wikify": restano quindi
# locali e non entrano in eventuali repository o copie condivise.
# Per usare un percorso diverso basta valorizzare ARCHIVIO_SMART_DATA prima
# di lanciare questo script.

APP_DIR=$(cd "$(dirname "$0")" && pwd)

if [ -z "$ARCHIVIO_SMART_DATA" ]; then
    ARCHIVIO_SMART_DATA=$(cd "$APP_DIR/../.." && pwd)/Wikify_dati
fi
export ARCHIVIO_SMART_DATA

mkdir -p "$ARCHIVIO_SMART_DATA"
echo "Cartella dati: $ARCHIVIO_SMART_DATA"

cd "$APP_DIR" || exit 1
exec python3 app.py
