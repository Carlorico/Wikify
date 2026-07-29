#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server MCP locale di Wikify (progettazione_moduli.md, Modulo 4).

Collega Claude / Claude Code al ciclo agentico del modulo Validazione AI
senza scambio manuale di file: il perimetro condivisibile passa da regola
scritta a vincolo imposto da questo processo (lo strumento leggi_file
rifiuta ogni percorso non assegnato alla sessione aperta).

Usa direttamente i moduli core dell'app (stessa base dati, stesso rispetto
della variabile d'ambiente ARCHIVIO_SMART_DATA) con connessioni SQLite
brevi, per convivere con l'app Flask eventualmente aperta in parallelo.

Avvio manuale (trasporto stdio):
    python3 mcp_server/server.py

Configurazione per Claude Code e Claude Desktop: vedere README.md in
questa cartella.
"""

import json
import os
import sys
from pathlib import Path

# La cartella app/ (un livello sopra questo file) contiene i moduli core.
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from core import analisi as ana  # noqa: E402
from core import db  # noqa: E402
from core import inventario as inv  # noqa: E402
from core import validazione as val  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("wikify")

DOCS_DIR = APP_DIR / "docs_agente"


def _radice(conn):
    return db.get_impostazione(conn, inv.CHIAVE_RADICE, "")


def _leggi_doc(nome):
    percorso = DOCS_DIR / nome
    if not percorso.is_file():
        return ""
    return percorso.read_text(encoding="utf-8")


@mcp.tool()
def ottieni_istruzioni() -> dict:
    """Istruzioni operative per l'agente di rilevazione, formato delle
    bozze (contratto wikify-bozza/1.0), tassonomie ammesse per campo e
    impostazioni di analisi correnti (modelli in cascata, soglia di
    rinforzo, ambito). Da chiamare come primo passo di ogni sessione."""
    conn = db.get_connection()
    try:
        impostazioni = ana.leggi_impostazioni(conn)
    finally:
        conn.close()
    return {
        "istruzioni_agente": _leggi_doc("istruzioni_agente.md"),
        "formato_bozze": _leggi_doc("formato_bozze.md"),
        "formato_atteso": val.FORMATO_BOZZA,
        "campi": list(val.CAMPI),
        "tassonomie": val.TASSONOMIE,
        "impostazioni_analisi": impostazioni,
    }


@mcp.tool()
def ottieni_incarico() -> dict:
    """Apre la sessione di analisi secondo le impostazioni correnti
    (ambito campione o archivio intero, tra le cartelle progetto con
    almeno un file condivisibile nell'ultima scansione completata) e
    restituisce le cartelle assegnate con i rispettivi file
    condivisibili. Se una sessione e' gia' aperta, restituisce quella con
    l'avanzamento (nessuna sessione nuova viene creata)."""
    conn = db.get_connection()
    try:
        sessione, cartelle, creata = ana.apri_sessione(conn)
        completate, rimanenti = ana.avanzamento(
            conn, sessione["id"], cartelle)
    finally:
        conn.close()
    return {
        "sessione_id": sessione["id"],
        "sessione_creata_ora": creata,
        "ambito": sessione["ambito"],
        "cartelle_assegnate": cartelle,
        "cartelle_completate": completate,
        "cartelle_rimanenti": rimanenti,
    }


@mcp.tool()
def leggi_file(percorso_rel: str) -> dict:
    """Testo estratto (con le posizioni, stessa convenzione dello
    scanner) di un file della sessione di analisi aperta. Vincolo
    centrale: se il percorso non e' tra i file condivisibili assegnati
    alla sessione, la lettura viene rifiutata con un errore esplicito e
    nessun contenuto viene restituito."""
    conn = db.get_connection()
    try:
        radice = _radice(conn)
        risultato, errore = ana.leggi_file(conn, radice, percorso_rel)
    finally:
        conn.close()
    if errore:
        return {"errore": errore}
    return {
        "percorso": risultato["percorso"],
        "unita": [{"posizione": pos, "testo": testo}
                  for pos, testo in risultato["unita"]],
        "n_caratteri": risultato["n_caratteri"],
    }


@mcp.tool()
def consegna_bozza(bozza_json: str) -> dict:
    """Consegna una bozza in formato wikify-bozza/1.0 (stringa JSON).
    Valida e importa con la stessa logica severa dell'import manuale
    (proposte senza evidenza o fuori tassonomia vengono scartate e
    motivate), lega il lotto alla sessione aperta e restituisce il
    riepilogo (proposte accettate/scartate con motivi)."""
    conn = db.get_connection()
    try:
        try:
            dati = (json.loads(bozza_json)
                    if isinstance(bozza_json, str) else bozza_json)
        except ValueError:
            return {"errore": "Il contenuto della bozza non è un JSON "
                              "leggibile."}
        lotto_id, esito = ana.consegna_bozza(conn, dati)
    finally:
        conn.close()
    if lotto_id is None:
        return {"errore": esito}
    return {"lotto_id": lotto_id, "riepilogo": esito}


@mcp.tool()
def ottieni_correzioni() -> dict:
    """Le correzioni pregresse (esiti "corretta" e "caso_nuovo" della
    revisione umana), stesso contenuto dell'export JSON correzioni della
    pagina Metriche: da rileggere come esempi prima del lotto
    successivo."""
    conn = db.get_connection()
    try:
        correzioni = val.correzioni_export(conn)
    finally:
        conn.close()
    return {"formato": "wikify-correzioni/1.0", "correzioni": correzioni}


@mcp.tool()
def stato_sessione(chiudi: bool = False) -> dict:
    """Avanzamento della sessione di analisi aperta (cartelle completate
    e rimanenti). Con chiudi=true la chiude: da chiamare quando l'agente
    ha terminato l'incarico assegnato."""
    conn = db.get_connection()
    try:
        stato = ana.stato_sessione(conn, chiudi=chiudi)
    finally:
        conn.close()
    if stato is None:
        return {"errore": "Nessuna sessione di analisi aperta."}
    sessione = stato["sessione"]
    return {
        "sessione_id": sessione["id"],
        "stato": sessione["stato"],
        "cartelle_assegnate": stato["cartelle_assegnate"],
        "cartelle_completate": stato["cartelle_completate"],
        "cartelle_rimanenti": stato["cartelle_rimanenti"],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
