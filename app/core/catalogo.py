# -*- coding: utf-8 -*-
"""
Modulo Catalogo, logica di dominio.

2A - Definizione entita': un tipo di entita' (es. "Progetto") nasce da un
criterio di autogenerazione sulle cartelle di primo livello dell'inventario.
La chiave si estrae dal nome cartella in tre modalita': nome intero,
prefisso + formato (riusa il builder guidato del dizionario), pattern regex
avanzato. Le istanze persistono: il riallineamento crea le nuove, marca
"senza riscontro" quelle senza piu' cartella corrispondente, non cancella
mai. Le chiavi duplicate (due cartelle -> stessa chiave) sono un conflitto:
le cartelle coinvolte restano senza entita' finche' l'utente non risolve.

2B - Arricchimento dati: import deterministico da CSV/XLSX. La chiave del
file viene normalizzata (trim, maiuscole, zeri iniziali) per il matching con
le entita'; ogni normalizzazione applicata viene tracciata. Relazione 1:N
nativa; deduplicazione su (entita', attributo, valore); ogni valore viene
salvato con la provenienza (una riga per import: il rollback di un import
rimuove solo le sue righe).
"""

import csv
import datetime
import io
import json
import os
import re

from . import db


def _adesso():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")


# ---------------------------------------------------------------------------
# 2A - Estrazione della chiave dalle cartelle dell'inventario
# ---------------------------------------------------------------------------

MODI = {
    "intero": "Nome intero della cartella",
    "prefisso": "Prefisso + formato (regola guidata)",
    "regex": "Pattern regex (avanzato)",
}


def cartelle_inventario(conn):
    """Cartelle di primo livello dell'inventario (file con stato presente)."""
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT cartella_progetto FROM inventario_file "
        "WHERE stato = 'presente' AND cartella_progetto <> '' "
        "ORDER BY cartella_progetto")]


def criterio_da_parametri(modo, parametri, escluse=None):
    """Costruisce e valida il criterio. Restituisce (criterio, errore)."""
    # Import locale: il builder guidato vive nel modulo dizionario.
    from modules.dizionario import build_pattern

    parametri = dict(parametri or {})
    if modo == "intero":
        parametri = {}
    elif modo == "prefisso":
        pattern, errore = build_pattern("codice", parametri)
        if errore:
            return None, errore
    elif modo == "regex":
        testo = (parametri.get("regex") or "").strip()
        if not testo:
            return None, "Inserire l'espressione regolare per l'estrazione."
        try:
            re.compile(testo, re.IGNORECASE)
        except re.error as e:
            return None, "Espressione non valida: %s" % e
        parametri = {"regex": testo}
    else:
        return None, "Modalità di estrazione non riconosciuta."
    return {"sorgente": "cartelle_inventario", "modo": modo,
            "parametri": parametri, "escluse": sorted(escluse or [])}, None


def estrattore(criterio):
    """Funzione nome_cartella -> chiave estratta (o None). None se il
    criterio non e' compilabile."""
    from modules.dizionario import build_pattern

    modo = criterio.get("modo", "intero")
    if modo == "intero":
        return lambda nome: (nome or "").strip() or None
    if modo == "prefisso":
        pattern, errore = build_pattern("codice", criterio.get("parametri") or {})
        if errore:
            return None
    elif modo == "regex":
        pattern = (criterio.get("parametri") or {}).get("regex") or ""
    else:
        return None
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error:
        return None

    def estrai(nome):
        m = rx.search(nome or "")
        if m is None:
            return None
        chiave = m.group(1) if m.groups() else m.group(0)
        return (chiave or "").strip() or None
    return estrai


def estrazioni(conn, criterio):
    """Prova del criterio sui nomi reali delle cartelle dell'inventario.

    Restituisce una lista di dizionari {cartella, chiave, esito} con esito
    in: 'ok', 'nessuna' (nessuna estrazione), 'conflitto' (chiave duplicata),
    'esclusa' (cartella esclusa dall'utente)."""
    estrai = estrattore(criterio)
    escluse = set(criterio.get("escluse") or [])
    righe, conteggio = [], {}
    for cartella in cartelle_inventario(conn):
        if cartella in escluse:
            righe.append({"cartella": cartella, "chiave": None,
                          "esito": "esclusa"})
            continue
        chiave = estrai(cartella) if estrai else None
        righe.append({"cartella": cartella, "chiave": chiave,
                      "esito": "ok" if chiave else "nessuna"})
        if chiave:
            conteggio[chiave] = conteggio.get(chiave, 0) + 1
    for r in righe:
        if r["esito"] == "ok" and conteggio[r["chiave"]] > 1:
            r["esito"] = "conflitto"
    return righe


def riepilogo_estrazioni(righe):
    """Conteggi per la prova live: ok, nessuna estrazione, conflitti, escluse."""
    conteggio = {"ok": 0, "nessuna": 0, "conflitto": 0, "esclusa": 0}
    for r in righe:
        conteggio[r["esito"]] = conteggio.get(r["esito"], 0) + 1
    return conteggio


def riallinea(conn, tipo):
    """Riallineamento delle istanze di un tipo con l'inventario.

    Crea le entita' nuove, riattiva/aggiorna quelle con riscontro, marca
    'senza_riscontro' quelle la cui cartella e' sparita o non matcha piu'.
    Non cancella mai. Le cartelle in conflitto di chiave non generano
    entita'. Restituisce il report del riallineamento."""
    criterio = json.loads(tipo["criterio_json"] or "{}")
    righe = estrazioni(conn, criterio)
    valide = {r["chiave"]: r["cartella"] for r in righe if r["esito"] == "ok"}
    conflitti = {}
    for r in righe:
        if r["esito"] == "conflitto":
            conflitti.setdefault(r["chiave"], []).append(r["cartella"])
    adesso = _adesso()
    esistenti = {e["chiave"]: e for e in conn.execute(
        "SELECT * FROM entita WHERE tipo_id = ?", (tipo["id"],))}
    create, riattivate, orfane = [], [], []
    for chiave, cartella in sorted(valide.items()):
        e = esistenti.get(chiave)
        if e is None:
            conn.execute(
                "INSERT INTO entita (tipo_id, chiave, cartella_origine, stato, "
                "data_creazione, data_riallineamento) "
                "VALUES (?, ?, ?, 'attiva', ?, ?)",
                (tipo["id"], chiave, cartella, adesso, adesso))
            create.append({"chiave": chiave, "cartella": cartella})
        else:
            if e["stato"] != "attiva":
                riattivate.append({"chiave": chiave, "cartella": cartella})
            conn.execute(
                "UPDATE entita SET cartella_origine = ?, stato = 'attiva', "
                "data_riallineamento = ? WHERE id = ?",
                (cartella, adesso, e["id"]))
    for chiave, e in sorted(esistenti.items()):
        if chiave not in valide and e["stato"] == "attiva":
            conn.execute(
                "UPDATE entita SET stato = 'senza_riscontro', "
                "data_riallineamento = ? WHERE id = ?", (adesso, e["id"]))
            orfane.append({"chiave": chiave, "cartella": e["cartella_origine"]})
    conn.commit()
    n_attive = conn.execute(
        "SELECT COUNT(*) FROM entita WHERE tipo_id = ? AND stato = 'attiva'",
        (tipo["id"],)).fetchone()[0]
    return {
        "create": create, "riattivate": riattivate, "orfane": orfane,
        "conflitti": conflitti,
        "senza_estrazione": [r["cartella"] for r in righe
                             if r["esito"] == "nessuna"],
        "escluse": [r["cartella"] for r in righe if r["esito"] == "esclusa"],
        "n_attive": n_attive, "data": adesso,
    }


# ---------------------------------------------------------------------------
# 2B - Normalizzazione e lettura dei file tabellari
# ---------------------------------------------------------------------------

def normalizza_chiave(testo):
    """Normalizzazione per il matching: trim, maiuscole, zeri iniziali.

    Restituisce (testo_normalizzato, passi_applicati)."""
    t = "" if testo is None else str(testo)
    passi = []
    s = t.strip()
    if s != t:
        passi.append("spazi iniziali/finali rimossi")
    u = s.upper()
    if u != s:
        passi.append("maiuscole applicate")
    z = u.lstrip("0")
    if z != u:
        if z == "":
            z = "0"
        passi.append("zeri iniziali rimossi")
    return z, passi


def _cella_a_testo(valore):
    """Valore di cella (csv o openpyxl) come testo pulito."""
    if valore is None:
        return ""
    if isinstance(valore, float) and valore.is_integer():
        return str(int(valore))
    return str(valore).strip()


def leggi_tabella(nome_file, contenuto):
    """Legge un file CSV o XLSX in (intestazioni, righe, errore).

    CSV: separatore , o ; con sniffing; codifiche utf-8 (anche con BOM)
    e latin-1. XLSX: primo foglio, soli valori. Solo libreria standard
    piu' openpyxl (gia' in uso nell'app)."""
    estensione = os.path.splitext(nome_file or "")[1].lower()
    if estensione in (".xlsx", ".xlsm"):
        import openpyxl
        try:
            wb = openpyxl.load_workbook(io.BytesIO(contenuto),
                                        read_only=True, data_only=True)
        except Exception as e:
            return None, None, "File XLSX non leggibile: %s" % e
        ws = wb.active
        righe = [[_cella_a_testo(v) for v in riga]
                 for riga in ws.iter_rows(values_only=True)]
        wb.close()
    elif estensione == ".csv":
        testo = None
        for codifica in ("utf-8-sig", "latin-1"):
            try:
                testo = contenuto.decode(codifica)
                break
            except UnicodeDecodeError:
                continue
        if testo is None:
            return None, None, "Codifica del CSV non riconosciuta (attese utf-8 o latin-1)."
        try:
            dialetto = csv.Sniffer().sniff(testo[:2048], delimiters=";,")
            separatore = dialetto.delimiter
        except csv.Error:
            prima = testo.splitlines()[0] if testo.strip() else ""
            separatore = ";" if prima.count(";") >= prima.count(",") else ","
        righe = [[_cella_a_testo(v) for v in riga]
                 for riga in csv.reader(io.StringIO(testo),
                                        delimiter=separatore)]
    else:
        return None, None, "Formato non supportato: caricare un file .csv o .xlsx."

    righe = [r for r in righe if any(c != "" for c in r)]
    if not righe:
        return None, None, "Il file non contiene righe di dati."
    intestazioni = [c.strip() or ("Colonna %d" % (i + 1))
                    for i, c in enumerate(righe[0])]
    dati = []
    for r in righe[1:]:
        riga = list(r[:len(intestazioni)])
        riga += [""] * (len(intestazioni) - len(riga))
        dati.append(riga)
    return intestazioni, dati, None


# ---------------------------------------------------------------------------
# 2B - Analisi di qualita' e salvataggio dell'import
# ---------------------------------------------------------------------------

def analizza_import(conn, tipo_id, intestazioni, righe, mappatura):
    """Analisi deterministica del file rispetto alle entita' del tipo.

    mappatura = {"chiave_col": int, "attributi": {indice_colonna: nome}}.
    Restituisce il quadro completo per l'anteprima di qualita' e per il
    salvataggio (nessuna scrittura su db)."""
    chiave_col = int(mappatura["chiave_col"])
    attributi = {int(k): v for k, v in (mappatura.get("attributi") or {}).items()}

    entita_rows = conn.execute(
        "SELECT id, chiave FROM entita WHERE tipo_id = ?", (tipo_id,)).fetchall()
    indice = {}
    for e in entita_rows:
        norm, _ = normalizza_chiave(e["chiave"])
        indice[norm] = e
    esistenti = set()
    for r in conn.execute(
            "SELECT a.entita_id, a.nome_attributo, a.valore "
            "FROM attributi_entita a "
            "JOIN importazioni i ON i.id = a.importazione_id "
            "WHERE i.stato = 'confermata' AND i.tipo_entita_id = ?",
            (tipo_id,)):
        esistenti.add((r["entita_id"], r["nome_attributo"],
                       normalizza_chiave(r["valore"])[0]))

    visti = {}          # (entita_id, attributo, valore_norm) -> valore raw
    valori = []
    scartate, normalizzazioni = [], []
    duplicati_esatti, duplicati_norm = [], []
    citate = set()
    for n, riga in enumerate(righe, start=2):   # riga 1 = intestazioni
        raw = riga[chiave_col] if chiave_col < len(riga) else ""
        norm, passi = normalizza_chiave(raw)
        if not norm:
            scartate.append({"riga": n, "chiave": raw,
                             "motivo": "chiave vuota"})
            continue
        ent = indice.get(norm)
        if ent is None:
            scartate.append({"riga": n, "chiave": raw,
                             "motivo": "nessuna entità con questa chiave"})
            continue
        citate.add(ent["id"])
        if raw.strip() != ent["chiave"]:
            normalizzazioni.append({
                "riga": n, "chiave": raw, "entita": ent["chiave"],
                "passi": passi or ["confronto normalizzato"]})
        for col, nome_attr in sorted(attributi.items()):
            valore = riga[col].strip() if col < len(riga) else ""
            if not valore:
                continue
            valore_norm, passi_v = normalizza_chiave(valore)
            k = (ent["id"], nome_attr, valore_norm)
            if k in visti:
                if visti[k] == valore:
                    duplicati_esatti.append({
                        "riga": n, "chiave": ent["chiave"],
                        "attributo": nome_attr, "valore": valore})
                else:
                    duplicati_norm.append({
                        "riga": n, "chiave": ent["chiave"],
                        "attributo": nome_attr, "valore": valore,
                        "conservato": visti[k],
                        "passi": passi_v or ["confronto normalizzato"]})
                continue
            visti[k] = valore
            valori.append({
                "entita_id": ent["id"], "chiave": ent["chiave"],
                "attributo": nome_attr, "valore": valore,
                "nuovo": k not in esistenti})
    non_citate = sorted(e["chiave"] for e in entita_rows
                        if e["id"] not in citate)
    return {
        "n_righe": len(righe),
        "valori": valori,
        "n_valori": len(valori),
        "n_valori_nuovi": sum(1 for v in valori if v["nuovo"]),
        "scartate": scartate,
        "normalizzazioni": normalizzazioni,
        "duplicati_esatti": duplicati_esatti,
        "duplicati_norm": duplicati_norm,
        "entita_non_citate": non_citate,
    }


def esegui_import(conn, tipo_id, nome_file, mappatura, analisi, utente):
    """Salva l'import: riga di provenienza, valori (una riga per import,
    rollback corretto) e anomalie. Restituisce l'id dell'importazione."""
    adesso = _adesso()
    cur = conn.execute(
        "INSERT INTO importazioni (data, nome_file, tipo_entita_id, "
        "mappatura_json, n_righe, n_valori, n_scartate, utente, stato) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'confermata')",
        (adesso, nome_file, tipo_id, json.dumps(mappatura),
         analisi["n_righe"], analisi["n_valori"], len(analisi["scartate"]),
         utente))
    imp_id = cur.lastrowid
    for v in analisi["valori"]:
        conn.execute(
            "INSERT OR IGNORE INTO attributi_entita "
            "(entita_id, nome_attributo, valore, importazione_id, data) "
            "VALUES (?, ?, ?, ?, ?)",
            (v["entita_id"], v["attributo"], v["valore"], imp_id, adesso))

    def anomalia(tipo, riferimento, dettaglio):
        conn.execute(
            "INSERT INTO anomalie_import (importazione_id, tipo, riferimento, "
            "dettaglio, stato_chiarimento) VALUES (?, ?, ?, ?, 'aperta')",
            (imp_id, tipo, riferimento, dettaglio))

    for s in analisi["scartate"]:
        anomalia("chiave_senza_entita", s["chiave"],
                 "Riga %d scartata: %s." % (s["riga"], s["motivo"]))
    for m in analisi["normalizzazioni"]:
        anomalia("chiave_normalizzata", m["chiave"],
                 "Riga %d: chiave \"%s\" agganciata all'entità \"%s\" dopo "
                 "normalizzazione (%s)."
                 % (m["riga"], m["chiave"], m["entita"], ", ".join(m["passi"])))
    for d in analisi["duplicati_esatti"]:
        anomalia("duplicato_esatto", d["chiave"],
                 "Riga %d: valore \"%s\" dell'attributo \"%s\" già presente "
                 "nel file (deduplicato)."
                 % (d["riga"], d["valore"], d["attributo"]))
    for d in analisi["duplicati_norm"]:
        anomalia("duplicato_normalizzazione", d["chiave"],
                 "Riga %d: valore \"%s\" dell'attributo \"%s\" coincide con "
                 "\"%s\" dopo normalizzazione (%s); conservato il primo."
                 % (d["riga"], d["valore"], d["attributo"], d["conservato"],
                    ", ".join(d["passi"])))
    if analisi["entita_non_citate"]:
        elenco = analisi["entita_non_citate"]
        testo = ", ".join(elenco[:50])
        if len(elenco) > 50:
            testo += " (e altre %d)" % (len(elenco) - 50)
        anomalia("entita_non_citate", str(len(elenco)),
                 "Entità mai citate dal file: %s." % testo)
    conn.commit()
    return imp_id


def rimuovi_import(conn, imp_id):
    """Rimozione in blocco: spariscono solo i valori dell'import indicato.
    I valori identici portati da altri import restano (una riga per import).
    L'importazione resta in elenco con stato 'rimossa', con le sue anomalie,
    per tracciabilita'. Restituisce il numero di valori rimossi."""
    n = conn.execute(
        "SELECT COUNT(*) FROM attributi_entita WHERE importazione_id = ?",
        (imp_id,)).fetchone()[0]
    conn.execute("DELETE FROM attributi_entita WHERE importazione_id = ?",
                 (imp_id,))
    conn.execute("UPDATE importazioni SET stato = 'rimossa' WHERE id = ?",
                 (imp_id,))
    conn.commit()
    return n


# ---------------------------------------------------------------------------
# Consultazione
# ---------------------------------------------------------------------------

def attributi_di_entita(conn, entita_id):
    """Attributi deduplicati dell'entita' con provenienza per ogni valore:
    lista di {attributo, valore, provenienze: [{file, data, utente}]}."""
    gruppi = {}
    for r in conn.execute(
            "SELECT a.nome_attributo, a.valore, i.nome_file, i.data, i.utente "
            "FROM attributi_entita a "
            "JOIN importazioni i ON i.id = a.importazione_id "
            "WHERE a.entita_id = ? AND i.stato = 'confermata' "
            "ORDER BY a.nome_attributo, a.valore, i.id", (entita_id,)):
        k = (r["nome_attributo"], r["valore"])
        gruppi.setdefault(k, []).append(
            {"file": r["nome_file"], "data": r["data"], "utente": r["utente"]})
    return [{"attributo": a, "valore": v, "provenienze": p}
            for (a, v), p in sorted(gruppi.items())]


def cartella_temporanea():
    """Cartella dei file di lavoro del wizard di arricchimento."""
    percorso = db.DATA_DIR / "import_temp"
    percorso.mkdir(parents=True, exist_ok=True)
    return percorso
