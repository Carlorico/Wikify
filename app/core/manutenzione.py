# -*- coding: utf-8 -*-
"""
Modulo Manutenzione: reset dell'archivio.

Il reset elimina i dati derivati dall'analisi dell'archivio (inventario,
scansioni, triage, catalogo, validazione, sessioni di analisi, archivio
logico) e i file temporanei del wizard di arricchimento. Restano invariati il dizionario
dei pattern (tabella regole), l'anagrafica utenti e le impostazioni,
salvo le chiavi che descrivono lo stato dell'inventario: si tratta di un
timestamp e di un esito legati a una mappa che, dopo il reset, non esiste
più, quindi non avrebbe senso conservarli. La cartella archivio impostata
(radice_archivio) e le chiavi di impostazione dell'analisi (prefisso
analisi_) restano.

Nessuna migrazione: il reset è una cancellazione di righe (DELETE), non
tocca lo schema del database.
"""

import shutil

from core import db
from core.inventario import CHIAVE_ESITO_CHECK, CHIAVE_ULTIMO_CHECK

# Tabelle svuotate dal reset, elencate nell'ordine che rispetta i vincoli
# di integrità referenziale (le tabelle figlie prima delle rispettive
# tabelle padre): il reset funziona così sia con PRAGMA foreign_keys
# attivo sia con i vincoli disattivi, senza dover contare sull'ON DELETE
# CASCADE dichiarato solo su una parte delle relazioni.
TABELLE_RESET = (
    # Archivio logico (Modulo 5): "documenti" si collega a entita' e a
    # regole_tipologia (collegamento derivato, non un vincolo REFERENCES:
    # v. core/db.py), va comunque svuotata per prima delle due.
    "documenti",
    "regole_tipologia",
    # Sessioni di analisi (Modulo 4 / connettore MCP)
    "sessioni_analisi_letture",
    # Validazione AI
    "validazioni",
    "proposte",
    "note_conoscenza_tacita",
    "lotti_validazione",
    # Catalogo
    "anomalie_import",
    "attributi_entita",
    "importazioni",
    "entita",
    "tipi_entita",
    # Classificazione (scansioni, segnalazioni, triage)
    "triage_file",
    "triage",
    "non_analizzati",
    "file_analizzati",
    "segnalazioni",
    "scansioni",
    # Inventario permanente
    "inventario_esecuzioni",
    "inventario_file",
    # Sessioni di analisi (tabella padre, dopo le letture)
    "sessioni_analisi",
)

# Chiavi della tabella impostazioni rimosse dal reset: descrivono lo stato
# dell'inventario (data dell'ultimo check ed esito). La cartella archivio
# (radice_archivio) e le chiavi di impostazione dell'analisi (prefisso
# analisi_) non sono comprese e restano.
CHIAVI_IMPOSTAZIONI_RESET = (CHIAVE_ULTIMO_CHECK, CHIAVE_ESITO_CHECK)


def _svuota_import_temp():
    """Rimuove i file temporanei del wizard di arricchimento del catalogo,
    ricreando la cartella vuota."""
    cartella = db.DATA_DIR / "import_temp"
    if cartella.is_dir():
        shutil.rmtree(cartella)
    cartella.mkdir(parents=True, exist_ok=True)


def reset_archivio(conn):
    """Esegue il reset dell'archivio in un'unica transazione: svuota le
    tabelle derivate dall'analisi (vedi TABELLE_RESET), rimuove dalle
    impostazioni le chiavi di stato dell'inventario e svuota la cartella
    import_temp.

    Il dizionario dei pattern (regole), l'anagrafica utenti e le
    impostazioni restanti (cartella archivio, chiavi di analisi) non
    vengono toccati.

    Restituisce un dizionario {tabella: numero di righe eliminate}. Il
    VACUUM successivo va eseguito fuori transazione (vedi vacuum_db)."""
    conteggi = {}
    try:
        for tabella in TABELLE_RESET:
            n = conn.execute(
                "SELECT COUNT(*) FROM %s" % tabella).fetchone()[0]
            conn.execute("DELETE FROM %s" % tabella)
            conteggi[tabella] = n
        for chiave in CHIAVI_IMPOSTAZIONI_RESET:
            conn.execute("DELETE FROM impostazioni WHERE chiave = ?", (chiave,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    _svuota_import_temp()
    return conteggi


def vacuum_db():
    """VACUUM del database: va eseguito fuori transazione, su una
    connessione dedicata (SQLite non ammette VACUUM all'interno di una
    transazione ne' su una connessione con modifiche pendenti)."""
    conn = db.get_connection()
    conn.execute("VACUUM")
    conn.close()
