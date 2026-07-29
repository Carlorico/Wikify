# -*- coding: utf-8 -*-
"""
Gestione del database SQLite: connessione, migrazioni semplici, seed iniziale.

Il database vive in app/data/archivio_smart.db (creato al primo avvio).
Le migrazioni sono una lista di script numerati: per aggiungere una tabella
in futuro basta accodare un nuovo script alla lista MIGRAZIONI.
"""

import datetime
import json
import os
import re
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent   # cartella app/

# La cartella dati e' app/data; la variabile d'ambiente ARCHIVIO_SMART_DATA
# consente di spostarla (es. su un percorso locale se l'app sta su una
# condivisione di rete che non supporta SQLite).
DATA_DIR = Path(os.environ.get("ARCHIVIO_SMART_DATA", str(BASE_DIR / "data")))
DB_PATH = DATA_DIR / "archivio_smart.db"

# Il seed viene cercato prima nello scanner CLI esistente, poi nella copia
# inclusa nell'app (cosi' l'app resta autonoma se spostata su un altro PC).
SEED_CANDIDATI = [
    BASE_DIR.parent / "scanner" / "dizionario_pattern.yaml",
    BASE_DIR / "dizionario_seed.yaml",
]

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS regole (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codice      TEXT NOT NULL UNIQUE,
    categoria   TEXT NOT NULL,
    descrizione TEXT DEFAULT '',
    tipo        TEXT NOT NULL DEFAULT 'regex',
    parametri   TEXT DEFAULT '{}',
    pattern     TEXT NOT NULL,
    severita    TEXT NOT NULL DEFAULT 'media',
    note        TEXT DEFAULT '',
    attiva      INTEGER NOT NULL DEFAULT 1,
    creata      TEXT,
    modificata  TEXT
);

CREATE TABLE IF NOT EXISTS scansioni (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    data      TEXT NOT NULL,
    radice    TEXT NOT NULL,
    etichetta TEXT DEFAULT '',
    n_regole  INTEGER DEFAULT 0,
    contesto  INTEGER DEFAULT 80,
    durata    REAL,
    stato     TEXT NOT NULL DEFAULT 'in corso'
);

CREATE TABLE IF NOT EXISTS segnalazioni (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    scansione_id INTEGER NOT NULL REFERENCES scansioni(id) ON DELETE CASCADE,
    file         TEXT NOT NULL,
    posizione    TEXT DEFAULT '',
    regola_id    TEXT NOT NULL,
    categoria    TEXT DEFAULT '',
    severita     TEXT DEFAULT 'media',
    testo_match  TEXT DEFAULT '',
    contesto     TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_segnalazioni_scan ON segnalazioni(scansione_id);

CREATE TABLE IF NOT EXISTS file_analizzati (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    scansione_id INTEGER NOT NULL REFERENCES scansioni(id) ON DELETE CASCADE,
    file         TEXT NOT NULL,
    formato      TEXT DEFAULT '',
    unita_testo  INTEGER DEFAULT 0,
    n_alta       INTEGER DEFAULT 0,
    n_media      INTEGER DEFAULT 0,
    n_bassa      INTEGER DEFAULT 0,
    totale       INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_file_scan ON file_analizzati(scansione_id);

CREATE TABLE IF NOT EXISTS non_analizzati (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    scansione_id INTEGER NOT NULL REFERENCES scansioni(id) ON DELETE CASCADE,
    file         TEXT NOT NULL,
    motivo       TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS triage (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    scansione_id INTEGER NOT NULL REFERENCES scansioni(id) ON DELETE CASCADE,
    file         TEXT NOT NULL,
    regola_id    TEXT NOT NULL,
    qualifica    TEXT NOT NULL DEFAULT 'Da valutare',
    motivazione  TEXT DEFAULT '',
    vincolo      TEXT DEFAULT '',
    validatore   TEXT DEFAULT '',
    data         TEXT,
    UNIQUE (scansione_id, file, regola_id)
);
"""

# V2: anagrafica utenti (login con PIN) e triage a granularita' di file.
# La tabella storica "triage" (per file + regola) resta invariata per
# compatibilita' con i database esistenti, ma la UI usa "triage_file".
SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS utenti (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nome           TEXT NOT NULL UNIQUE,
    pin            TEXT NOT NULL,
    attivo         INTEGER NOT NULL DEFAULT 1,
    data_creazione TEXT
);

CREATE TABLE IF NOT EXISTS triage_file (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    scansione_id INTEGER NOT NULL REFERENCES scansioni(id) ON DELETE CASCADE,
    file         TEXT NOT NULL,
    qualifica    TEXT NOT NULL DEFAULT 'Da valutare',
    motivazione  TEXT DEFAULT '',
    vincolo      TEXT DEFAULT '',
    validatore   TEXT DEFAULT '',
    data         TEXT,
    verificato   INTEGER NOT NULL DEFAULT 0,
    UNIQUE (scansione_id, file)
);
CREATE INDEX IF NOT EXISTS idx_triage_file_scan ON triage_file(scansione_id);
"""

# V3: impostazioni dell'applicazione (chiave/valore) e inventario permanente
# dell'archivio (mappa dei file a livello di filesystem, senza lettura dei
# contenuti). Migrazione puramente additiva: nessuna tabella esistente
# viene modificata.
SCHEMA_V3 = """
CREATE TABLE IF NOT EXISTS impostazioni (
    chiave TEXT PRIMARY KEY,
    valore TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS inventario_file (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    percorso_rel      TEXT NOT NULL UNIQUE,
    cartella_progetto TEXT DEFAULT '',
    estensione        TEXT DEFAULT '',
    dimensione        INTEGER DEFAULT 0,
    data_modifica     TEXT DEFAULT '',
    data_rilevazione  TEXT DEFAULT '',
    stato             TEXT NOT NULL DEFAULT 'presente'
);
CREATE INDEX IF NOT EXISTS idx_inventario_cartella
    ON inventario_file(cartella_progetto);
CREATE INDEX IF NOT EXISTS idx_inventario_stato
    ON inventario_file(stato);

CREATE TABLE IF NOT EXISTS inventario_esecuzioni (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    data        TEXT NOT NULL,
    tipo        TEXT NOT NULL DEFAULT 'completo',
    n_nuovi     INTEGER DEFAULT 0,
    n_scomparsi INTEGER DEFAULT 0,
    n_totale    INTEGER DEFAULT 0,
    durata      REAL
);
"""

# V4: modulo Catalogo, entita' logiche e arricchimento dati.
# Migrazione puramente additiva: nessuna tabella esistente viene toccata.
# Nota di schema rispetto alla progettazione: il vincolo di unicita' su
# attributi_entita include importazione_id (una riga per import, non per
# valore). In questo modo la rimozione in blocco di un import elimina solo
# le sue righe: se un valore identico e' portato anche da un altro import,
# la riga dell'altro import resta e il valore sopravvive. La deduplicazione
# per la consultazione avviene in lettura (GROUP BY entita', attributo,
# valore).
SCHEMA_V4 = """
CREATE TABLE IF NOT EXISTS tipi_entita (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nome           TEXT NOT NULL UNIQUE,
    criterio_json  TEXT NOT NULL DEFAULT '{}',
    data_creazione TEXT,
    stato          TEXT NOT NULL DEFAULT 'attivo'
);

CREATE TABLE IF NOT EXISTS entita (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_id             INTEGER NOT NULL REFERENCES tipi_entita(id) ON DELETE CASCADE,
    chiave              TEXT NOT NULL,
    cartella_origine    TEXT DEFAULT '',
    stato               TEXT NOT NULL DEFAULT 'attiva',
    data_creazione      TEXT,
    data_riallineamento TEXT,
    UNIQUE (tipo_id, chiave)
);
CREATE INDEX IF NOT EXISTS idx_entita_tipo ON entita(tipo_id);

CREATE TABLE IF NOT EXISTS importazioni (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    data           TEXT,
    nome_file      TEXT DEFAULT '',
    tipo_entita_id INTEGER NOT NULL REFERENCES tipi_entita(id),
    mappatura_json TEXT DEFAULT '{}',
    n_righe        INTEGER DEFAULT 0,
    n_valori       INTEGER DEFAULT 0,
    n_scartate     INTEGER DEFAULT 0,
    utente         TEXT DEFAULT '',
    stato          TEXT NOT NULL DEFAULT 'confermata'
);

CREATE TABLE IF NOT EXISTS attributi_entita (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entita_id       INTEGER NOT NULL REFERENCES entita(id) ON DELETE CASCADE,
    nome_attributo  TEXT NOT NULL,
    valore          TEXT NOT NULL,
    importazione_id INTEGER NOT NULL REFERENCES importazioni(id),
    data            TEXT,
    UNIQUE (entita_id, nome_attributo, valore, importazione_id)
);
CREATE INDEX IF NOT EXISTS idx_attributi_entita ON attributi_entita(entita_id);
CREATE INDEX IF NOT EXISTS idx_attributi_import ON attributi_entita(importazione_id);

CREATE TABLE IF NOT EXISTS anomalie_import (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    importazione_id   INTEGER NOT NULL REFERENCES importazioni(id) ON DELETE CASCADE,
    tipo              TEXT NOT NULL,
    riferimento       TEXT DEFAULT '',
    dettaglio         TEXT DEFAULT '',
    stato_chiarimento TEXT NOT NULL DEFAULT 'aperta',
    nota_chiarimento  TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_anomalie_import ON anomalie_import(importazione_id);
"""

# V5: modulo Validazione AI (lotti di bozze dell'agente, proposte, esiti
# di validazione e note di conoscenza tacita). Migrazione puramente
# additiva: nessuna tabella esistente viene toccata.
# Scostamenti documentati rispetto alla progettazione:
# - lotti_validazione: aggiunte le colonne cartella_progetto e chiave_entita
#   (una bozza copre una cartella progetto), n_troncate (citazioni oltre il
#   limite, troncate con nota) e note_agente_json (le note libere del file
#   bozza vivono a livello di lotto, come nel contratto wikify-bozza/1.0);
# - proposte: aggiunta la colonna citazione_troncata (nota di troncamento
#   per le citazioni oltre i 300 caratteri); note_agente_json non e' per
#   proposta perche' il contratto la prevede per file, quindi sta sul lotto;
# - validazioni: proposta_id UNIQUE consente la rivalidazione (upsert).
SCHEMA_V5 = """
CREATE TABLE IF NOT EXISTS lotti_validazione (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    data_import           TEXT,
    nome_file_origine     TEXT DEFAULT '',
    formato               TEXT DEFAULT '',
    cartella_progetto     TEXT DEFAULT '',
    chiave_entita         TEXT,
    n_accettate           INTEGER NOT NULL DEFAULT 0,
    n_scartate            INTEGER NOT NULL DEFAULT 0,
    n_troncate            INTEGER NOT NULL DEFAULT 0,
    dettaglio_scarti_json TEXT DEFAULT '{}',
    note_agente_json      TEXT DEFAULT '[]',
    stato                 TEXT NOT NULL DEFAULT 'importato'
);

CREATE TABLE IF NOT EXISTS proposte (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    lotto_id           INTEGER NOT NULL REFERENCES lotti_validazione(id)
                       ON DELETE CASCADE,
    cartella_progetto  TEXT DEFAULT '',
    chiave_entita      TEXT,
    file               TEXT NOT NULL,
    sezione            TEXT DEFAULT 'intero documento',
    campo              TEXT NOT NULL,
    valore_proposto    TEXT NOT NULL,
    confidenza         REAL NOT NULL DEFAULT 0,
    evidenza_posizione TEXT NOT NULL,
    evidenza_citazione TEXT NOT NULL,
    citazione_troncata INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_proposte_lotto ON proposte(lotto_id);
CREATE INDEX IF NOT EXISTS idx_proposte_cartella ON proposte(cartella_progetto);

CREATE TABLE IF NOT EXISTS validazioni (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    proposta_id       INTEGER NOT NULL UNIQUE REFERENCES proposte(id)
                      ON DELETE CASCADE,
    esito             TEXT NOT NULL,
    valore_corretto   TEXT DEFAULT '',
    nota              TEXT DEFAULT '',
    validatore        TEXT DEFAULT '',
    data              TEXT,
    secondi_impiegati INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS note_conoscenza_tacita (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    lotto_id          INTEGER REFERENCES lotti_validazione(id),
    cartella_progetto TEXT NOT NULL,
    testo             TEXT NOT NULL,
    autore            TEXT DEFAULT '',
    data              TEXT
);
CREATE INDEX IF NOT EXISTS idx_note_tacite_cartella
    ON note_conoscenza_tacita(cartella_progetto);
"""

# V6: connettore MCP e sessioni di analisi (progettazione_moduli.md,
# Modulo 4). Migrazione puramente additiva: nessuna tabella esistente
# viene modificata, salvo l'aggiunta della colonna "sessione_id" su
# lotti_validazione (ADD COLUMN, nullable: i lotti da import manuale
# restano senza sessione).
# Scostamento documentato rispetto alla progettazione: e' stata aggiunta
# la tabella sessioni_analisi_letture (sessione_id, percorso_rel,
# caratteri, data), non prevista nello schema di progettazione. Serve a
# contare i file distinti effettivamente letti dall'agente (KPI "file nel
# perimetro / letti") e a non contare due volte i caratteri se lo stesso
# file viene riletto nella stessa sessione (vincolo UNIQUE su sessione e
# percorso).
SCHEMA_V6 = """
CREATE TABLE IF NOT EXISTS sessioni_analisi (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    data_avvio              TEXT,
    data_chiusura           TEXT,
    stato                   TEXT NOT NULL DEFAULT 'aperta',
    ambito                  TEXT NOT NULL DEFAULT 'campione',
    n_progetti_richiesti    INTEGER DEFAULT 0,
    seed                    INTEGER,
    modello_primario        TEXT DEFAULT '',
    modello_rinforzo        TEXT DEFAULT '',
    soglia_rinforzo         REAL DEFAULT 0.7,
    scansione_id            INTEGER,
    cartelle_assegnate_json TEXT DEFAULT '{}',
    caratteri_letti         INTEGER NOT NULL DEFAULT 0,
    caratteri_prodotti      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessioni_analisi_letture (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sessione_id  INTEGER NOT NULL REFERENCES sessioni_analisi(id) ON DELETE CASCADE,
    percorso_rel TEXT NOT NULL,
    caratteri    INTEGER DEFAULT 0,
    data         TEXT,
    UNIQUE (sessione_id, percorso_rel)
);
CREATE INDEX IF NOT EXISTS idx_letture_sessione
    ON sessioni_analisi_letture(sessione_id);

ALTER TABLE lotti_validazione ADD COLUMN sessione_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_lotti_sessione
    ON lotti_validazione(sessione_id);
"""

# Per una futura migrazione: accodare qui un nuovo script SQL.
MIGRAZIONI = [SCHEMA_V1, SCHEMA_V2, SCHEMA_V3, SCHEMA_V4, SCHEMA_V5, SCHEMA_V6]


def get_secret_key():
    """Chiave segreta di sessione Flask: generata al primo avvio e salvata
    in data/secret_key.txt, cosi' le sessioni sopravvivono ai riavvii."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    percorso = DATA_DIR / "secret_key.txt"
    if percorso.is_file():
        chiave = percorso.read_text(encoding="utf-8").strip()
        if chiave:
            return chiave
    chiave = os.urandom(32).hex()
    percorso.write_text(chiave, encoding="utf-8")
    return chiave


def get_connection():
    """Apre una connessione SQLite (una per richiesta o per thread)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        # WAL migliora la concorrenza tra scansione e consultazione, ma non e'
        # supportato da tutti i filesystem (es. cartelle di rete): in tal caso
        # si resta sul journal predefinito.
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError:
        pass
    return conn


def init_db():
    """Applica le migrazioni mancanti e, se il dizionario e' vuoto, importa il seed."""
    conn = get_connection()
    versione = conn.execute("PRAGMA user_version").fetchone()[0]
    for i in range(versione, len(MIGRAZIONI)):
        conn.executescript(MIGRAZIONI[i])
        conn.execute("PRAGMA user_version = %d" % (i + 1))
    conn.commit()
    n = seed_dizionario(conn)
    conn.close()
    return n


def get_impostazione(conn, chiave, default=""):
    """Legge un valore dalla tabella impostazioni (chiave/valore)."""
    riga = conn.execute("SELECT valore FROM impostazioni WHERE chiave = ?",
                        (chiave,)).fetchone()
    return riga["valore"] if riga is not None else default


def set_impostazione(conn, chiave, valore):
    """Scrive (o aggiorna) un valore nella tabella impostazioni."""
    conn.execute(
        "INSERT INTO impostazioni (chiave, valore) VALUES (?, ?) "
        "ON CONFLICT(chiave) DO UPDATE SET valore = excluded.valore",
        (chiave, str(valore)))
    conn.commit()


def elenco_condivisibili(conn, scansione_id):
    """Perimetro condivisibile di una scansione: i file qualificati
    Condivisibile nel registro di segregazione (triage per file).
    Punto di aggancio del modulo Validazione AI: l'agente di rilevazione
    riceve esclusivamente questo perimetro."""
    return [r["file"] for r in conn.execute(
        "SELECT file FROM triage_file WHERE scansione_id = ? "
        "AND qualifica = 'Condivisibile' ORDER BY file", (scansione_id,))]


def seed_dizionario(conn):
    """Se la tabella regole e' vuota, importa il dizionario YAML dello scanner CLI.

    Le regole importate conservano id (codice), categoria, severita' e note;
    il tipo viene marcato come 'regex' (espressione regolare avanzata).
    Restituisce il numero di regole importate.
    """
    if conn.execute("SELECT COUNT(*) FROM regole").fetchone()[0]:
        return 0
    try:
        import yaml
    except ImportError:
        return 0
    for percorso in SEED_CANDIDATI:
        if not percorso.is_file():
            continue
        with open(percorso, "r", encoding="utf-8") as f:
            dati = yaml.safe_load(f) or {}
        adesso = datetime.datetime.now().isoformat(timespec="seconds")
        importate = 0
        for r in dati.get("regole", []):
            pattern = r.get("pattern", "")
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO regole "
                "(codice, categoria, descrizione, tipo, parametri, pattern, "
                " severita, note, attiva, creata, modificata) "
                "VALUES (?, ?, ?, 'regex', ?, ?, ?, ?, 1, ?, ?)",
                (r.get("id", ""), r.get("categoria", "generale"),
                 r.get("descrizione", "") or "",
                 json.dumps({"regex": pattern}), pattern,
                 r.get("severita", "media"), r.get("note", "") or "",
                 adesso, adesso))
            importate += 1
        conn.commit()
        return importate
    return 0
