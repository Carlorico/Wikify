#!/bin/sh
# Prepara la cartella di progetto da consegnare a terzi (allievi, cliente).
#
# Produce una copia completa e funzionante del progetto, escludendo il
# materiale che non va condiviso. L'esclusione e' dichiarata qui sotto e non
# dipende dalla memoria di chi effettua la consegna.
#
# Uso:
#   strumenti/prepara_condivisione.sh [cartella_di_destinazione]
#
# Senza argomenti la destinazione e' ../Wikify_da_consegnare, cartella
# sorella del progetto. Se esiste, viene chiesto di rimuoverla prima.

set -e

PROGETTO=$(cd "$(dirname "$0")/.." && pwd)
NOME=$(basename "$PROGETTO")
DEST=${1:-"$(dirname "$PROGETTO")/Wikify_da_consegnare"}

# --- Cosa NON viene condiviso, e perche' -----------------------------------
# interno/        materiale di lavoro: registro delle sessioni, assessment
#                 originale. Documenti vivi, che continuiamo ad alimentare,
#                 ma non destinati a terzi.
# .git/           storia del progetto e configurazione del repository.
# __pycache__/    bytecode rigenerabile.
# .DS_Store       scorie del Finder.
# app/data/       eventuale cartella dati residua: i dati di lavoro non si
#                 consegnano mai (risiedono comunque in ../Wikify_dati).
# .venv/          ambiente virtuale locale, va ricreato sulla macchina di
#                 destinazione seguendo la guida di avvio.
ESCLUSI="interno .git __pycache__ .DS_Store data .venv"

echo "Progetto:     $PROGETTO"
echo "Destinazione: $DEST"
echo

if [ -e "$DEST" ]; then
    printf "La destinazione esiste già. Rimuoverla e ricrearla? [s/N] "
    read -r risposta
    case "$risposta" in
        s|S|si|Si|SI) rm -rf "$DEST" ;;
        *) echo "Interrotto: nessuna modifica."; exit 1 ;;
    esac
fi

mkdir -p "$DEST"

if command -v rsync >/dev/null 2>&1; then
    rsync -a \
        --exclude 'interno/' \
        --exclude '.git/' \
        --exclude '__pycache__/' \
        --exclude '.DS_Store' \
        --exclude '*.pyc' \
        --exclude 'app/data/' \
        --exclude '.venv/' \
        "$PROGETTO"/ "$DEST"/
else
    # Ripiego senza rsync: copia integrale e successiva potatura.
    cp -R "$PROGETTO"/ "$DEST"/
    for voce in $ESCLUSI; do
        find "$DEST" -name "$voce" -maxdepth 3 -exec rm -rf {} + 2>/dev/null || true
    done
    find "$DEST" -name '*.pyc' -delete 2>/dev/null || true
fi

# --- Verifica: nulla di escluso deve essere sopravvissuto ------------------
errori=0
if [ -d "$DEST/interno" ]; then
    echo "ERRORE: la cartella interno/ è presente nella copia."
    errori=1
fi
if [ -d "$DEST/app/data" ]; then
    echo "ERRORE: app/data è presente nella copia."
    errori=1
fi
residui=$(find "$DEST" \( -name '__pycache__' -o -name '.DS_Store' -o -name '*.pyc' \) | wc -l | tr -d ' ')
if [ "$residui" != "0" ]; then
    echo "ERRORE: $residui scorie tecniche presenti nella copia."
    errori=1
fi
if [ "$errori" != "0" ]; then
    echo
    echo "La copia NON è pronta per la consegna. Verificare lo script."
    exit 1
fi

# --- Riepilogo -------------------------------------------------------------
n_file=$(find "$DEST" -type f | wc -l | tr -d ' ')
dimensione=$(du -sh "$DEST" | cut -f1)

echo "Copia completata: $n_file file, $dimensione"
echo
echo "Contenuto di primo livello:"
ls -1 "$DEST" | sed 's/^/  /'
echo
echo "Da ricordare nella consegna:"
echo "  - l'archivio di prova NON è incluso: si consegna a parte"
echo "    (i documenti appartengono ai rispettivi produttori)"
echo "  - i dati di lavoro non sono inclusi per costruzione"
echo "  - l'ambiente Python va ricreato seguendo documentazione/07 o 08"
echo
printf "Creare anche un archivio compresso accanto alla cartella? [s/N] "
read -r comprimi
case "$comprimi" in
    s|S|si|Si|SI)
        (cd "$(dirname "$DEST")" && zip -qr "$(basename "$DEST").zip" "$(basename "$DEST")")
        echo "Archivio creato: $DEST.zip"
        ;;
    *) echo "Nessun archivio compresso creato." ;;
esac
