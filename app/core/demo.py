# -*- coding: utf-8 -*-
"""
Modulo Demo: composizione dell'Archivio Demo all'ingresso e al reset.

La modalita' demo non e' una base dati precotta da copiare (conterrebbe
percorsi assoluti fragili, legati alla macchina su cui e' stata generata):
e' una composizione eseguita al momento sull'Archivio Demo incluso nel
progetto, con la stessa catena disponibile per un archivio reale
(core.livello0.ricostruisci) piu' una scansione dei contenuti. Sull'Archivio
Demo l'intera composizione dura meno di un secondo.
"""

import glob
import time

from core import db, livello0
from core.inventario import CHIAVE_RADICE
from core.scansione import avvia_scansione

# Cartella dell'Archivio Demo, alla radice del progetto (genitore di app/).
# Variabile di modulo, non una costante importata per valore: i test la
# sostituiscono con un percorso inesistente per simulare la demo assente.
RADICE_DEMO = db.Path(__file__).resolve().parent.parent.parent / "Archivio Demo"

CHIAVE_DEMO_ATTIVA = "demo_attiva"

ETICHETTA_SCANSIONE = "Composizione demo"
CONTESTO_SCANSIONE = 80
TETTO_ATTESA_SECONDI = 30


def _cartella_documentale():
    return RADICE_DEMO / "Archivio documentale" / "IDROMETRICA PRODUCTS"


def _file_listino():
    """Il file XLSX della cartella Listino, oppure None se non c'e'."""
    trovati = sorted(glob.glob(str(RADICE_DEMO / "Listino" / "*.xlsx")))
    return trovati[0] if trovati else None


def disponibile():
    """Vero se l'Archivio Demo e' presente con la struttura attesa."""
    return _cartella_documentale().is_dir() and _file_listino() is not None


def componi(conn):
    """Compone la demo: inventario, famiglie, listino, documenti, vigenza
    (core.livello0.ricostruisci) sulla cartella documentale dell'Archivio
    Demo, poi una scansione dei contenuti attesa fino al completamento
    (tetto 30 secondi). Marca infine la modalita' demo come attiva.

    Restituisce il riepilogo, gli stessi numeri della modale."""
    radice = str(_cartella_documentale())
    listino = _file_listino()

    livello0.ricostruisci(conn, radice, listino)

    scan_id = avvia_scansione(radice, ETICHETTA_SCANSIONE, CONTESTO_SCANSIONE)
    inizio = time.time()
    while time.time() - inizio < TETTO_ATTESA_SECONDI:
        attesa = db.get_connection()
        stato = attesa.execute(
            "SELECT stato FROM scansioni WHERE id = ?", (scan_id,)).fetchone()[0]
        attesa.close()
        if stato != "in corso":
            break
        time.sleep(0.05)

    db.set_impostazione(conn, CHIAVE_DEMO_ATTIVA, "1")
    return riepilogo(conn)


def riepilogo(conn):
    """I numeri per la modale, letti dal database: file inventariati,
    famiglie attive, articoli, copertura famiglie, candidati ad
    aggiornamento, segnalazioni di scansione, radice impostata."""
    n_file = conn.execute(
        "SELECT COUNT(*) FROM inventario_file WHERE stato = 'presente'"
        ).fetchone()[0]
    copertura = livello0.misura_copertura(conn)
    vigenza = livello0.misura_vigenza(conn)
    n_segnalazioni_scansione = conn.execute(
        "SELECT COUNT(*) FROM segnalazioni").fetchone()[0]
    return {
        "n_file": n_file,
        "n_famiglie": copertura["famiglie"],
        "n_articoli": copertura["articoli"],
        "copertura_famiglie": copertura["copertura_famiglie"],
        "n_candidati": vigenza["segnalazioni_aperte"],
        "n_segnalazioni_scansione": n_segnalazioni_scansione,
        "radice": db.get_impostazione(conn, CHIAVE_RADICE, ""),
    }
