# -*- coding: utf-8 -*-
"""
Motore di scansione: attraversamento delle cartelle, applicazione delle
regole attive del dizionario, salvataggio degli esiti sul database.

La scansione gira in un thread separato; lo stato di avanzamento e'
esposto nel dizionario PROGRESS (letto dall'endpoint JSON di polling).
"""

import datetime
import os
import re
import threading
import time

from . import db
from .estrazione import estrai

# scan_id -> {stato, totali, processati, corrente, errore}
PROGRESS = {}
_LOCK = threading.Lock()


def _aggiorna(scan_id, **kw):
    with _LOCK:
        PROGRESS.setdefault(scan_id, {}).update(kw)


def stato_progress(scan_id):
    with _LOCK:
        info = PROGRESS.get(scan_id)
        return dict(info) if info else None


def cammina(radice):
    """Elenca i file da analizzare, saltando temporanei (~$) e cartelle nascoste."""
    trovati = []
    for cartella, sottocartelle, nomi in os.walk(radice):
        sottocartelle[:] = [d for d in sottocartelle if not d.startswith(".")]
        for nome in sorted(nomi):
            if nome.startswith(("~$", ".")):
                continue
            trovati.append(os.path.join(cartella, nome))
    return trovati


def carica_regole_attive(conn):
    """Carica dal DB le sole regole attive, con la regex gia' compilata."""
    regole = []
    for r in conn.execute("SELECT * FROM regole WHERE attiva = 1 ORDER BY codice"):
        try:
            rx = re.compile(r["pattern"], re.IGNORECASE)
        except re.error:
            continue
        regole.append({"codice": r["codice"], "categoria": r["categoria"],
                       "severita": r["severita"], "rx": rx})
    return regole


def scansiona_file(percorso, regole, ctx):
    """Applica tutte le regole al testo estratto. Restituisce (esiti, n_unita)."""
    unita = estrai(percorso)
    esiti = []
    for pos, testo in unita:
        for r in regole:
            for m in r["rx"].finditer(testo):
                a, b = m.start(), m.end()
                contesto = testo[max(0, a - ctx): b + ctx].strip()
                esiti.append((pos, r, m.group(0), contesto))
    return esiti, len(unita)


def avvia_scansione(radice, etichetta, contesto):
    """Registra la scansione sul DB e lancia il thread di lavoro. Restituisce l'id."""
    conn = db.get_connection()
    regole = carica_regole_attive(conn)
    adesso = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    cur = conn.execute(
        "INSERT INTO scansioni (data, radice, etichetta, n_regole, contesto, stato) "
        "VALUES (?, ?, ?, ?, ?, 'in corso')",
        (adesso, radice, etichetta, len(regole), contesto))
    scan_id = cur.lastrowid
    conn.commit()
    conn.close()
    _aggiorna(scan_id, stato="in corso", totali=0, processati=0, corrente="", errore="")
    t = threading.Thread(target=_esegui, args=(scan_id, radice, contesto, regole),
                         daemon=True)
    t.start()
    return scan_id


def _esegui(scan_id, radice, contesto, regole):
    inizio = time.time()
    conn = db.get_connection()
    try:
        files = cammina(radice)
        _aggiorna(scan_id, totali=len(files))
        for i, percorso in enumerate(files, start=1):
            rel = os.path.relpath(percorso, radice)
            _aggiorna(scan_id, processati=i - 1, corrente=rel)
            try:
                esiti, unita = scansiona_file(percorso, regole, contesto)
            except ValueError as e:
                conn.execute(
                    "INSERT INTO non_analizzati (scansione_id, file, motivo) VALUES (?, ?, ?)",
                    (scan_id, rel, str(e)))
                conn.commit()
                continue
            except Exception as e:
                conn.execute(
                    "INSERT INTO non_analizzati (scansione_id, file, motivo) VALUES (?, ?, ?)",
                    (scan_id, rel, "errore di lettura: %s" % e))
                conn.commit()
                continue
            sev = {"alta": 0, "media": 0, "bassa": 0}
            for pos, r, testo_match, ctx in esiti:
                conn.execute(
                    "INSERT INTO segnalazioni "
                    "(scansione_id, file, posizione, regola_id, categoria, severita, "
                    " testo_match, contesto) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (scan_id, rel, pos, r["codice"], r["categoria"], r["severita"],
                     testo_match, ctx))
                sev[r["severita"]] = sev.get(r["severita"], 0) + 1
            conn.execute(
                "INSERT INTO file_analizzati "
                "(scansione_id, file, formato, unita_testo, n_alta, n_media, n_bassa, totale) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (scan_id, rel, os.path.splitext(percorso)[1].lower(), unita,
                 sev.get("alta", 0), sev.get("media", 0), sev.get("bassa", 0), len(esiti)))
            conn.commit()
        durata = round(time.time() - inizio, 1)
        conn.execute("UPDATE scansioni SET stato = 'completata', durata = ? WHERE id = ?",
                     (durata, scan_id))
        conn.commit()
        _aggiorna(scan_id, stato="completata", processati=len(files), corrente="")
    except Exception as e:
        conn.execute("UPDATE scansioni SET stato = 'errore' WHERE id = ?", (scan_id,))
        conn.commit()
        _aggiorna(scan_id, stato="errore", errore=str(e))
    finally:
        conn.close()
