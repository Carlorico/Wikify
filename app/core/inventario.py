# -*- coding: utf-8 -*-
"""
Inventario permanente dell'archivio: mappa dei file a livello di
filesystem (percorso, cartella progetto, estensione, dimensione, data di
modifica), senza alcuna lettura dei contenuti.

Funzioni principali:
- elenca_filesystem(radice): fotografia corrente del filesystem;
- inventario_iniziale(radice): primo popolamento della mappa;
- confronta(conn, radice): differenze filesystem / mappa (nuovi, scomparsi);
- esegui_check(conn, radice): check di allineamento (aggiorna metadati e
  stato dei file gia' mappati, conta i nuovi senza integrarli);
- integra_nuovi(conn, radice): integra i file nuovi nella mappa;
- conta_da_classificare(conn, radice): file dell'inventario mai coperti da
  una scansione di riservatezza completata (o modificati dopo l'ultima).

Il check all'apertura della dashboard viene eseguito al massimo una volta
ogni CHECK_INTERVALLO_SECONDI (timestamp in impostazioni), salvo richiesta
esplicita ("Ricontrolla ora").
"""

import datetime
import os
import time

from . import db
from .estrazione import TEXT_EXT

# Estensioni che il motore di scansione sa analizzare: solo per queste ha
# senso lo stato "da classificare".
ESTENSIONI_ANALIZZABILI = set(TEXT_EXT) | {".docx", ".xlsx", ".xlsm", ".pdf"}

# Chiavi della tabella impostazioni usate dal modulo.
CHIAVE_RADICE = "radice_archivio"
CHIAVE_ULTIMO_CHECK = "inventario_ultimo_check"
CHIAVE_ESITO_CHECK = "inventario_nuovi_ultimo_check"

CHECK_INTERVALLO_SECONDI = 600  # 10 minuti


def _adesso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _mtime_iso(percorso):
    try:
        return datetime.datetime.fromtimestamp(
            os.path.getmtime(percorso)).isoformat(timespec="seconds")
    except OSError:
        return ""


def elenca_filesystem(radice):
    """Fotografia del filesystem sotto la radice: lista di dizionari con
    percorso_rel, cartella_progetto (primo livello sotto la radice),
    estensione, dimensione e data_modifica. Nessuna lettura dei contenuti.

    Stesse esclusioni del motore di scansione: cartelle nascoste, file
    nascosti e temporanei di Office (~$)."""
    trovati = []
    for cartella, sottocartelle, nomi in os.walk(radice):
        sottocartelle[:] = [d for d in sottocartelle if not d.startswith(".")]
        for nome in sorted(nomi):
            if nome.startswith(("~$", ".")):
                continue
            percorso = os.path.join(cartella, nome)
            rel = os.path.relpath(percorso, radice)
            rel = rel.replace(os.sep, "/")
            parti = rel.split("/")
            cartella_progetto = parti[0] if len(parti) > 1 else ""
            try:
                dimensione = os.path.getsize(percorso)
            except OSError:
                dimensione = 0
            trovati.append({
                "percorso_rel": rel,
                "cartella_progetto": cartella_progetto,
                "estensione": os.path.splitext(nome)[1].lower(),
                "dimensione": dimensione,
                "data_modifica": _mtime_iso(percorso),
            })
    return trovati


def _inserisci(conn, info):
    conn.execute(
        "INSERT INTO inventario_file (percorso_rel, cartella_progetto, "
        "estensione, dimensione, data_modifica, data_rilevazione, stato) "
        "VALUES (?, ?, ?, ?, ?, ?, 'presente') "
        "ON CONFLICT(percorso_rel) DO UPDATE SET "
        "cartella_progetto = excluded.cartella_progetto, "
        "estensione = excluded.estensione, "
        "dimensione = excluded.dimensione, "
        "data_modifica = excluded.data_modifica, "
        "stato = 'presente'",
        (info["percorso_rel"], info["cartella_progetto"], info["estensione"],
         info["dimensione"], info["data_modifica"], _adesso()))


def _registra_esecuzione(conn, tipo, n_nuovi, n_scomparsi, durata):
    n_totale = conn.execute(
        "SELECT COUNT(*) FROM inventario_file WHERE stato = 'presente'"
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO inventario_esecuzioni (data, tipo, n_nuovi, n_scomparsi, "
        "n_totale, durata) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), tipo,
         n_nuovi, n_scomparsi, n_totale, durata))


def inventario_iniziale(conn, radice):
    """Primo popolamento della mappa (o ripopolamento se vuota).
    Restituisce il numero di file rilevati."""
    inizio = time.time()
    files = elenca_filesystem(radice)
    for info in files:
        _inserisci(conn, info)
    _registra_esecuzione(conn, "completo", len(files), 0,
                         round(time.time() - inizio, 1))
    conn.commit()
    db.set_impostazione(conn, CHIAVE_ULTIMO_CHECK, str(time.time()))
    db.set_impostazione(conn, CHIAVE_ESITO_CHECK, "0")
    return len(files)


def confronta(conn, radice):
    """Confronto filesystem / mappa. Restituisce (fs, nuovi, scomparsi):
    - fs: fotografia corrente del filesystem (lista di dizionari);
    - nuovi: elementi di fs non presenti nella mappa;
    - scomparsi: percorsi in mappa con stato 'presente' non piu' sul disco."""
    fs = elenca_filesystem(radice)
    percorsi_fs = {f["percorso_rel"] for f in fs}
    mappa = {r["percorso_rel"]: r["stato"] for r in conn.execute(
        "SELECT percorso_rel, stato FROM inventario_file")}
    nuovi = [f for f in fs if f["percorso_rel"] not in mappa]
    scomparsi = [p for p, stato in mappa.items()
                 if stato == "presente" and p not in percorsi_fs]
    return fs, nuovi, scomparsi


def _allinea_esistenti(conn, fs):
    """Aggiorna metadati e stato dei file gia' mappati (anche quelli
    ricomparsi dopo essere stati marcati scomparsi)."""
    for info in fs:
        conn.execute(
            "UPDATE inventario_file SET dimensione = ?, data_modifica = ?, "
            "cartella_progetto = ?, estensione = ?, stato = 'presente' "
            "WHERE percorso_rel = ?",
            (info["dimensione"], info["data_modifica"],
             info["cartella_progetto"], info["estensione"],
             info["percorso_rel"]))


def _marca_scomparsi(conn, scomparsi):
    for p in scomparsi:
        conn.execute("UPDATE inventario_file SET stato = 'scomparso' "
                     "WHERE percorso_rel = ?", (p,))


def esegui_check(conn, radice):
    """Check di allineamento: aggiorna i metadati dei file mappati, marca
    gli scomparsi e conta i nuovi (senza integrarli: l'integrazione e'
    un'azione esplicita dell'utente). Restituisce (n_nuovi, n_scomparsi)."""
    inizio = time.time()
    fs, nuovi, scomparsi = confronta(conn, radice)
    _allinea_esistenti(conn, fs)
    _marca_scomparsi(conn, scomparsi)
    _registra_esecuzione(conn, "check", len(nuovi), len(scomparsi),
                         round(time.time() - inizio, 1))
    conn.commit()
    db.set_impostazione(conn, CHIAVE_ULTIMO_CHECK, str(time.time()))
    db.set_impostazione(conn, CHIAVE_ESITO_CHECK, str(len(nuovi)))
    return len(nuovi), len(scomparsi)


def check_se_necessario(conn, radice):
    """Esegue il check solo se l'ultimo risale a piu' di
    CHECK_INTERVALLO_SECONDI fa. Restituisce il numero di file nuovi non
    mappati secondo l'ultimo check disponibile."""
    ultimo = db.get_impostazione(conn, CHIAVE_ULTIMO_CHECK, "")
    try:
        trascorso = time.time() - float(ultimo)
    except ValueError:
        trascorso = None
    if trascorso is None or trascorso >= CHECK_INTERVALLO_SECONDI:
        n_nuovi, _ = esegui_check(conn, radice)
        return n_nuovi
    try:
        return int(db.get_impostazione(conn, CHIAVE_ESITO_CHECK, "0"))
    except ValueError:
        return 0


def integra_nuovi(conn, radice):
    """Integra nella mappa i file nuovi rilevati dal check e allinea il
    resto (metadati, scomparsi). Restituisce (n_integrati, n_scomparsi)."""
    inizio = time.time()
    fs, nuovi, scomparsi = confronta(conn, radice)
    for info in nuovi:
        _inserisci(conn, info)
    _allinea_esistenti(conn, fs)
    _marca_scomparsi(conn, scomparsi)
    _registra_esecuzione(conn, "check", len(nuovi), len(scomparsi),
                         round(time.time() - inizio, 1))
    conn.commit()
    db.set_impostazione(conn, CHIAVE_ULTIMO_CHECK, str(time.time()))
    db.set_impostazione(conn, CHIAVE_ESITO_CHECK, "0")
    return len(nuovi), len(scomparsi)


# ----------------------------------------------------------------------
# Stato di classificazione (incrocio con le scansioni di riservatezza)
# ----------------------------------------------------------------------

def _parse_data_scansione(testo):
    """Le scansioni salvano la data come 'gg/mm/aaaa HH:MM'."""
    try:
        return datetime.datetime.strptime(testo or "", "%d/%m/%Y %H:%M")
    except ValueError:
        return None

def _parse_iso(testo):
    try:
        return datetime.datetime.fromisoformat(testo or "")
    except ValueError:
        return None


def copertura_scansioni(conn, radice):
    """Per ogni percorso relativo alla radice dell'archivio, la data
    dell'ultima scansione completata che lo ha analizzato.

    Le scansioni possono avere una radice uguale all'archivio o una sua
    sottocartella: i percorsi dei file analizzati vengono riportati alla
    radice dell'archivio. Le scansioni fuori dall'archivio si ignorano."""
    radice_norm = os.path.normpath(radice)
    copertura = {}
    for scan in conn.execute(
            "SELECT id, data, radice FROM scansioni WHERE stato = 'completata'"):
        scan_radice = os.path.normpath(scan["radice"] or "")
        try:
            rel = os.path.relpath(scan_radice, radice_norm)
        except ValueError:
            continue  # es. unita' diverse su Windows
        if rel.startswith(".."):
            continue  # scansione fuori dall'archivio
        prefisso = "" if rel == "." else rel.replace(os.sep, "/") + "/"
        data_scan = _parse_data_scansione(scan["data"])
        if data_scan is None:
            continue
        for riga in conn.execute(
                "SELECT file FROM file_analizzati WHERE scansione_id = ?",
                (scan["id"],)):
            percorso = prefisso + (riga["file"] or "").replace(os.sep, "/")
            attuale = copertura.get(percorso)
            if attuale is None or data_scan > attuale:
                copertura[percorso] = data_scan
    return copertura


def da_classificare(conn, radice):
    """Elenco dei percorsi dell'inventario (presenti e analizzabili) che
    necessitano di una scansione di classificazione: mai coperti da una
    scansione completata, oppure modificati dopo l'ultima che li copre."""
    copertura = copertura_scansioni(conn, radice)
    esito = []
    for r in conn.execute(
            "SELECT percorso_rel, estensione, data_modifica FROM inventario_file "
            "WHERE stato = 'presente' ORDER BY percorso_rel"):
        if r["estensione"] not in ESTENSIONI_ANALIZZABILI:
            continue
        data_scan = copertura.get(r["percorso_rel"])
        if data_scan is None:
            esito.append(r["percorso_rel"])
            continue
        mtime = _parse_iso(r["data_modifica"])
        # La data di scansione ha granularita' al minuto: si considera
        # "modificato dopo" solo oltre la fine di quel minuto, per non
        # segnalare file toccati nello stesso minuto della scansione.
        if mtime is not None and mtime > data_scan + datetime.timedelta(seconds=59):
            esito.append(r["percorso_rel"])
    return esito


# ----------------------------------------------------------------------
# KPI per la dashboard
# ----------------------------------------------------------------------

# Colonne di ripartizione per tipo nella tabella per cartella.
ESTENSIONI_PRINCIPALI = [
    ("docx", {".docx"}),
    ("xlsx", {".xlsx", ".xlsm"}),
    ("pdf", {".pdf"}),
    ("txt", {".txt"}),
]


def kpi_dashboard(conn):
    """KPI dall'inventario: numero cartelle progetto e tabella per cartella
    (totale file e ripartizione per estensione principale)."""
    righe = conn.execute(
        "SELECT cartella_progetto, estensione, COUNT(*) AS n "
        "FROM inventario_file WHERE stato = 'presente' "
        "GROUP BY cartella_progetto, estensione").fetchall()
    cartelle = {}
    for r in righe:
        nome = r["cartella_progetto"] or "(radice)"
        c = cartelle.setdefault(
            nome, {"cartella": nome, "totale": 0, "altro": 0,
                   **{etichetta: 0 for etichetta, _ in ESTENSIONI_PRINCIPALI}})
        c["totale"] += r["n"]
        for etichetta, gruppo in ESTENSIONI_PRINCIPALI:
            if r["estensione"] in gruppo:
                c[etichetta] += r["n"]
                break
        else:
            c["altro"] += r["n"]
    tabella = sorted(cartelle.values(), key=lambda c: c["cartella"].lower())
    n_cartelle = sum(1 for c in tabella if c["cartella"] != "(radice)")
    n_file = sum(c["totale"] for c in tabella)
    return {"n_cartelle": n_cartelle, "n_file": n_file, "tabella": tabella}
