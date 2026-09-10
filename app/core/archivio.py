# -*- coding: utf-8 -*-
"""
Modulo Archivio logico, logica di dominio (Modulo 5, chiusura della fase 1).

Consolidamento interamente deterministico (nessuna componente AI) di cio'
che i moduli precedenti hanno gia' prodotto: la mappa dei file (inventario),
la qualifica di riservatezza (triage), le entita' con i loro attributi
(catalogo) e le proposte validate (Validazione AI). Il documento diventa un
oggetto di prima classe (tabella "documenti") con una tipologia e una
riservatezza consolidate secondo tre precedenze esplicite:

    1 (massima)  manuale     - correzione dell'operatore sulla scheda documento
    2            validazione - proposta confermata/corretta in Validazione AI
    3            regola (tipologia) / triage (riservatezza) - derivazione automatica

La ricostruzione (ricostruisci()) e' idempotente e non distruttiva: rieseguirla
non altera mai le assegnazioni di precedenza superiore e produce sempre un
report di cio' che ha cambiato.

Regole di tipologia: classificazione deterministica sul nome del file, sul
percorso e sull'estensione (nessuna lettura del contenuto), con builder
guidato "senza espressioni regolari" analogo a quello del dizionario: campo
osservato + modo di confronto + uno o piu' valori, con normalizzazione di
maiuscole e accenti. Le regole sono ordinate per priorita': vince la prima
che riscontra.
"""

import datetime
import json
import os
import unicodedata

from . import catalogo as cat
from . import db
from . import validazione as val

# ---------------------------------------------------------------------------
# Costanti e tassonomie
# ---------------------------------------------------------------------------

FORMATO_EXPORT = "wikify-archivio/1.1"

# Vocabolario unico della riservatezza nell'export. Il triage scrive
# "Riservato"/"Condivisibile", le proposte dell'agente "riservato",
# "condivisibile", "misto": contratti gia' congelati che non si toccano.
# L'export 1.1 normalizza in un campo dedicato e conserva l'originale.
VOCABOLARIO_RISERVATEZZA = ("condivisibile", "riservato", "misto")

TIPOLOGIA_NON_CLASSIFICATO = "non_classificato"

# Riusa la tassonomia congelata in core/validazione.py: non si ridefinisce.
TASSONOMIA_TIPOLOGIA = list(val.TASSONOMIE["tipologia"])

# Tipologie "attese" ai fini della completezza per entita': l'intera
# tassonomia esclusa "altro", che e' per definizione un contenitore
# residuale e non una categoria che ci si attende di trovare in ogni
# entita'. Scelta di progetto non prescritta dalla specifica (che non
# introduce una configurazione di tipologie attese per tipo di entita'):
# documentata anche nel README del modulo.
TIPOLOGIE_ATTESE = [t for t in TASSONOMIA_TIPOLOGIA if t != "altro"]

CAMPI_OSSERVATI = {
    "nome_file": "Nome file",
    "percorso": "Percorso relativo",
    "cartella_progetto": "Cartella progetto",
    "estensione": "Estensione",
}

MODI = {
    "contiene": "Contiene",
    "inizia_per": "Inizia per",
    "finisce_per": "Finisce per",
    "uguale_a": "Uguale a",
    "estensione_tra": "Estensione tra",
}

# Chiave della tabella impostazioni con cui si ricorda l'ultimo tipo di
# entita' scelto per l'aggancio documento -> entita' del consolidamento.
IMPOSTAZIONE_TIPO_ENTITA = "archivio_tipo_entita_id"


def _adesso():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")


# ---------------------------------------------------------------------------
# Normalizzazione per il confronto (maiuscole e accenti)
# ---------------------------------------------------------------------------

def normalizza_testo(testo):
    """Minuscolo, senza accenti, spazi esterni rimossi: usato per ogni
    confronto delle regole di tipologia."""
    t = "" if testo is None else str(testo)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower().strip()


# ---------------------------------------------------------------------------
# Criterio delle regole di tipologia (builder guidato, senza regex)
# ---------------------------------------------------------------------------

def documento_da_percorso(percorso_rel, cartella_progetto=None):
    """Il dizionario dei campi osservabili per un percorso relativo
    all'archivio (usato sia dalla prova live sull'inventario sia dalla
    valutazione delle regole sui documenti gia' censiti)."""
    percorso_rel = percorso_rel or ""
    if cartella_progetto is None:
        parti = percorso_rel.split("/")
        cartella_progetto = parti[0] if len(parti) > 1 else ""
    return {
        "nome_file": os.path.basename(percorso_rel),
        "percorso": percorso_rel,
        "cartella_progetto": cartella_progetto or "",
        "estensione": os.path.splitext(percorso_rel)[1].lower(),
    }


def criterio_da_form(form):
    """Costruisce e valida il criterio dai campi del form. Restituisce
    (criterio, errore)."""
    campo = form.get("campo") or "nome_file"
    modo = form.get("modo") or "contiene"
    if modo not in MODI:
        return None, "Modalità di confronto non riconosciuta."
    if modo == "estensione_tra":
        # L'estensione e' l'unico campo sensato per questo modo: forzato,
        # cosi' l'utente non deve nemmeno sceglierlo.
        campo = "estensione"
    if campo not in CAMPI_OSSERVATI:
        return None, "Campo osservato non riconosciuto."
    grezzo = form.get("valori") or ""
    valori = [v.strip() for v in grezzo.splitlines() if v.strip()]
    if not valori:
        return None, "Indicare almeno un valore da confrontare (uno per riga)."
    if modo == "estensione_tra":
        valori = [(v if v.startswith(".") else "." + v).lower() for v in valori]
    return {"campo": campo, "modo": modo, "valori": valori}, None


def valuta_criterio(criterio, doc):
    """Vero se il documento (dizionario di documento_da_percorso) soddisfa
    il criterio. Confronto sempre senza distinzione di maiuscole e con
    normalizzazione degli accenti."""
    campo = criterio.get("campo")
    modo = criterio.get("modo")
    testo = normalizza_testo(doc.get(campo, ""))
    termini = [normalizza_testo(v) for v in (criterio.get("valori") or [])]
    if modo == "contiene":
        return any(t and t in testo for t in termini)
    if modo == "inizia_per":
        return any(t and testo.startswith(t) for t in termini)
    if modo == "finisce_per":
        return any(t and testo.endswith(t) for t in termini)
    if modo == "uguale_a":
        return any(t and testo == t for t in termini)
    if modo == "estensione_tra":
        return testo in termini
    return False


def prova_criterio(conn, criterio, limite_esempi=25):
    """Prova live del criterio sui nomi reali dei file dell'inventario
    (percorso_rel, cartella_progetto): conteggio dei documenti intercettati
    ed esempi (i primi limite_esempi percorsi)."""
    righe = conn.execute(
        "SELECT percorso_rel, cartella_progetto FROM inventario_file "
        "WHERE stato = 'presente' ORDER BY percorso_rel").fetchall()
    esempi, n_match = [], 0
    for r in righe:
        doc = documento_da_percorso(r["percorso_rel"], r["cartella_progetto"])
        if valuta_criterio(criterio, doc):
            n_match += 1
            if len(esempi) < limite_esempi:
                esempi.append(r["percorso_rel"])
    return {"n_totale": len(righe), "n_match": n_match, "esempi": esempi}


# ---------------------------------------------------------------------------
# CRUD delle regole di tipologia
# ---------------------------------------------------------------------------

def regole_tutte(conn):
    return conn.execute(
        "SELECT * FROM regole_tipologia ORDER BY priorita ASC, id ASC").fetchall()


def regole_attive(conn):
    return conn.execute(
        "SELECT * FROM regole_tipologia WHERE attiva = 1 "
        "ORDER BY priorita ASC, id ASC").fetchall()


def _prossima_priorita(conn):
    r = conn.execute("SELECT MAX(priorita) FROM regole_tipologia").fetchone()[0]
    return (r or 0) + 1


def crea_regola(conn, nome, tipologia, criterio):
    cur = conn.execute(
        "INSERT INTO regole_tipologia (nome, tipologia, criterio_json, "
        "priorita, attiva, data_creazione) VALUES (?, ?, ?, ?, 1, ?)",
        (nome, tipologia, json.dumps(criterio), _prossima_priorita(conn),
         _adesso()))
    conn.commit()
    return cur.lastrowid


def aggiorna_regola(conn, rid, nome, tipologia, criterio):
    conn.execute(
        "UPDATE regole_tipologia SET nome = ?, tipologia = ?, "
        "criterio_json = ? WHERE id = ?",
        (nome, tipologia, json.dumps(criterio), rid))
    conn.commit()


def elimina_regola(conn, rid):
    conn.execute("DELETE FROM regole_tipologia WHERE id = ?", (rid,))
    conn.commit()


def toggle_regola(conn, rid):
    conn.execute(
        "UPDATE regole_tipologia SET attiva = 1 - attiva WHERE id = ?", (rid,))
    conn.commit()


def sposta_priorita(conn, rid, direzione):
    """Scambia la priorita' della regola con quella adiacente (direzione
    'su' o 'giu'). Restituisce True se lo scambio e' avvenuto."""
    regole = regole_tutte(conn)
    idx = next((i for i, r in enumerate(regole) if r["id"] == rid), None)
    if idx is None:
        return False
    vicino = idx - 1 if direzione == "su" else idx + 1
    if vicino < 0 or vicino >= len(regole):
        return False
    a, b = regole[idx], regole[vicino]
    conn.execute("UPDATE regole_tipologia SET priorita = ? WHERE id = ?",
                 (b["priorita"], a["id"]))
    conn.execute("UPDATE regole_tipologia SET priorita = ? WHERE id = ?",
                 (a["priorita"], b["id"]))
    conn.commit()
    return True


def valuta_documento(regole, doc):
    """Prima regola attiva (in ordine di priorita') che riscontra sul
    documento. Restituisce (tipologia, regola_id); (non_classificato, None)
    se nessuna regola intercetta: esito legittimo e misurato."""
    for r in regole:
        criterio = json.loads(r["criterio_json"] or "{}")
        if valuta_criterio(criterio, doc):
            return r["tipologia"], r["id"]
    return TIPOLOGIA_NON_CLASSIFICATO, None


# ---------------------------------------------------------------------------
# Riservatezza consolidata dal triage piu' recente
# ---------------------------------------------------------------------------

def _parse_data(testo):
    try:
        return datetime.datetime.strptime(testo or "", "%d/%m/%Y %H:%M")
    except ValueError:
        return datetime.datetime.min


def _mappa_riservatezza_da_triage(conn, radice):
    """Per ogni percorso relativo alla radice archivio, la qualifica
    dell'ultimo triage che lo riguarda tra tutte le scansioni (stesso
    incrocio radice-scansione/radice-archivio di core.inventario, qui
    esteso alla qualifica anziche' alla sola data di copertura). La
    qualifica "Da valutare" non e' una qualifica consolidabile: non essendo
    un esito finale del triage, non produce una riservatezza."""
    if not radice:
        return {}
    radice_norm = os.path.normpath(radice)
    mappa = {}
    for scan in conn.execute("SELECT id, radice FROM scansioni"):
        scan_radice = os.path.normpath(scan["radice"] or "")
        try:
            rel = os.path.relpath(scan_radice, radice_norm)
        except ValueError:
            continue
        if rel.startswith(".."):
            continue
        prefisso = "" if rel == "." else rel.replace(os.sep, "/") + "/"
        for t in conn.execute(
                "SELECT file, qualifica, data, id FROM triage_file "
                "WHERE scansione_id = ?", (scan["id"],)):
            if not t["qualifica"] or t["qualifica"] == "Da valutare":
                continue
            percorso = prefisso + (t["file"] or "").replace(os.sep, "/")
            candidato = (_parse_data(t["data"]), t["id"])
            attuale = mappa.get(percorso)
            if attuale is None or candidato > attuale[1]:
                mappa[percorso] = (t["qualifica"], candidato)
    return {p: v[0] for p, v in mappa.items()}


# ---------------------------------------------------------------------------
# Sovrapposizione delle proposte validate (Validazione AI)
# ---------------------------------------------------------------------------

def _percorso_da_proposta(cartella_progetto, file_):
    """Il "file" di una proposta e' relativo alla cartella progetto
    (contratto wikify-bozza/1.0, v. docs_agente/formato_bozze.md): qui si
    ricompone il percorso relativo all'archivio, nella stessa convenzione
    di inventario_file.percorso_rel."""
    cartella = (cartella_progetto or "").strip().rstrip("/")
    file_norm = (file_ or "").replace("\\", "/").strip().lstrip("/")
    return (cartella + "/" + file_norm) if cartella else file_norm


def _valori_da_validazione(conn):
    """Valori di tipologia e riservatezza confermati/corretti nella coda di
    Validazione AI, indicizzati per percorso relativo all'archivio.

    Per la tipologia, in caso di piu' proposte validate sullo stesso file
    (raro: proposte di lotti diversi) vince quella con id di validazione
    piu' alto, proxy dell'ordine cronologico di validazione. Per la
    riservatezza si aggregano tutte le sezioni validate del file: se
    concordano si consolida quel valore, se discordano il documento e'
    "misto" (riservatezza mista tra sezioni)."""
    righe = conn.execute(
        "SELECT p.cartella_progetto, p.file, p.campo, p.valore_proposto, "
        "v.esito, v.valore_corretto, v.id AS vid "
        "FROM proposte p JOIN validazioni v ON v.proposta_id = p.id "
        "WHERE p.campo IN ('tipologia', 'riservatezza') "
        "ORDER BY v.id ASC")
    tipologia, riservatezza_grezza = {}, {}
    for r in righe:
        percorso = _percorso_da_proposta(r["cartella_progetto"], r["file"])
        if not percorso:
            continue
        valore = (r["valore_proposto"] if r["esito"] == "confermata"
                  else (r["valore_corretto"] or r["valore_proposto"]))
        if r["campo"] == "tipologia":
            tipologia[percorso] = valore  # l'ultimo (id piu' alto) vince
        else:
            riservatezza_grezza.setdefault(percorso, set()).add(valore)
    riservatezza = {}
    for percorso, valori in riservatezza_grezza.items():
        riservatezza[percorso] = (next(iter(valori)) if len(valori) == 1
                                  else "misto")
    return tipologia, riservatezza


# ---------------------------------------------------------------------------
# Ricostruzione dell'archivio logico (consolidamento)
# ---------------------------------------------------------------------------

def _sincronizza_da_inventario(conn):
    """Allinea la tabella documenti all'inventario: crea le righe mancanti,
    aggiorna cartella_progetto e stato di quelle esistenti, non cancella
    mai. Restituisce il numero di documenti creati in questa esecuzione."""
    adesso = _adesso()
    righe_inv = conn.execute(
        "SELECT percorso_rel, cartella_progetto, stato FROM inventario_file"
    ).fetchall()
    percorsi_inv = {r["percorso_rel"] for r in righe_inv}
    esistenti = {r["percorso_rel"] for r in
                 conn.execute("SELECT percorso_rel FROM documenti")}
    nuovi = 0
    for r in righe_inv:
        stato_doc = "attivo" if r["stato"] == "presente" else "assente"
        if r["percorso_rel"] not in esistenti:
            conn.execute(
                "INSERT INTO documenti (percorso_rel, cartella_progetto, "
                "tipologia, tipologia_origine, riservatezza, "
                "riservatezza_origine, stato, data_aggiornamento) "
                "VALUES (?, ?, ?, 'regola', '', 'triage', ?, ?)",
                (r["percorso_rel"], r["cartella_progetto"],
                 TIPOLOGIA_NON_CLASSIFICATO, stato_doc, adesso))
            nuovi += 1
        else:
            conn.execute(
                "UPDATE documenti SET cartella_progetto = ?, stato = ?, "
                "data_aggiornamento = ? WHERE percorso_rel = ?",
                (r["cartella_progetto"], stato_doc, adesso, r["percorso_rel"]))
    # File usciti del tutto dall'inventario (riga rimossa, non solo
    # "scomparso"): il documento resta ma si marca assente.
    for r in conn.execute(
            "SELECT id, percorso_rel FROM documenti WHERE stato != 'assente'"):
        if r["percorso_rel"] not in percorsi_inv:
            conn.execute(
                "UPDATE documenti SET stato = 'assente', "
                "data_aggiornamento = ? WHERE id = ?", (adesso, r["id"]))
    conn.commit()
    return nuovi


def ricostruisci(conn, tipo_entita_id=None):
    """Ricostruzione idempotente e non distruttiva dell'archivio logico.

    Rispetta le tre precedenze (manuale > validazione > regola/triage): le
    righe con origine 'manuale' non vengono mai toccate dalle fasi
    automatiche. L'aggancio a entita' viene ricalcolato solo se si indica
    un tipo_entita_id: altrimenti il collegamento esistente resta invariato
    (non e' distruttivo eseguire il consolidamento senza aver ancora
    scelto un tipo di entita' per l'aggancio).

    Restituisce il report dell'esecuzione."""
    adesso = _adesso()
    nuovi = _sincronizza_da_inventario(conn)

    # --- Baseline tipologia dalle regole (salta le righe manuali) ---
    regole = regole_attive(conn)
    for doc in conn.execute(
            "SELECT id, percorso_rel, cartella_progetto, tipologia_origine "
            "FROM documenti"):
        if doc["tipologia_origine"] == "manuale":
            continue
        d = documento_da_percorso(doc["percorso_rel"], doc["cartella_progetto"])
        tipologia, regola_id = valuta_documento(regole, d)
        conn.execute(
            "UPDATE documenti SET tipologia = ?, tipologia_origine = 'regola', "
            "tipologia_regola_id = ?, data_aggiornamento = ? "
            "WHERE id = ? AND tipologia_origine != 'manuale'",
            (tipologia, regola_id, adesso, doc["id"]))
    conn.commit()

    # --- Baseline riservatezza dal triage piu' recente ---
    radice = db.get_impostazione(conn, "radice_archivio", "")
    mappa_triage = _mappa_riservatezza_da_triage(conn, radice)
    for percorso, qualifica in mappa_triage.items():
        conn.execute(
            "UPDATE documenti SET riservatezza = ?, riservatezza_origine = "
            "'triage', data_aggiornamento = ? WHERE percorso_rel = ? "
            "AND riservatezza_origine != 'manuale'",
            (qualifica, adesso, percorso))
    conn.commit()

    # --- Sovrapposizione delle proposte validate (precedenza 2) ---
    val_tipologia, val_riservatezza = _valori_da_validazione(conn)
    n_val_senza_documento = 0
    for percorso, valore in val_tipologia.items():
        cur = conn.execute(
            "UPDATE documenti SET tipologia = ?, tipologia_origine = "
            "'validazione', tipologia_regola_id = NULL, "
            "data_aggiornamento = ? WHERE percorso_rel = ? "
            "AND tipologia_origine != 'manuale'",
            (valore, adesso, percorso))
        if cur.rowcount == 0:
            n_val_senza_documento += 1
    for percorso, valore in val_riservatezza.items():
        conn.execute(
            "UPDATE documenti SET riservatezza = ?, riservatezza_origine = "
            "'validazione', data_aggiornamento = ? WHERE percorso_rel = ? "
            "AND riservatezza_origine != 'manuale'",
            (valore, adesso, percorso))
    conn.commit()

    # --- Aggancio a entita' (solo se e' stato scelto un tipo di entita') ---
    agganciati_ora = 0
    orfani = []
    if tipo_entita_id:
        mappa_entita = {r["cartella_origine"]: r["id"] for r in conn.execute(
            "SELECT id, cartella_origine FROM entita "
            "WHERE tipo_id = ? AND stato = 'attiva'", (tipo_entita_id,))}
        for doc in conn.execute(
                "SELECT id, percorso_rel, cartella_progetto FROM documenti"):
            eid = (mappa_entita.get(doc["cartella_progetto"])
                   if doc["cartella_progetto"] else None)
            conn.execute("UPDATE documenti SET entita_id = ? WHERE id = ?",
                         (eid, doc["id"]))
            if eid:
                agganciati_ora += 1
            elif doc["cartella_progetto"]:
                orfani.append(doc["percorso_rel"])
        conn.commit()

    return {
        "data": adesso,
        "tipo_entita_id": tipo_entita_id,
        "nuovi_documenti": nuovi,
        "aggancio_eseguito": bool(tipo_entita_id),
        "agganciati": agganciati_ora,
        "orfani": sorted(orfani)[:200],
        "n_orfani": len(orfani),
        "validazioni_senza_documento": n_val_senza_documento,
        **indicatori_copertura(conn),
    }


# ---------------------------------------------------------------------------
# Indicatori e consultazione
# ---------------------------------------------------------------------------

def indicatori_copertura(conn):
    """Indicatori di copertura e origine, calcolabili in ogni momento (non
    solo subito dopo una ricostruzione): quanti documenti sono stati
    classificati per regola/validazione/manuale, quanti restano non
    classificati, quanti agganciati, come si consolida la riservatezza."""
    tot = conn.execute("SELECT COUNT(*) FROM documenti").fetchone()[0]
    n_non_class = conn.execute(
        "SELECT COUNT(*) FROM documenti WHERE tipologia = ?",
        (TIPOLOGIA_NON_CLASSIFICATO,)).fetchone()[0]
    n_regola = conn.execute(
        "SELECT COUNT(*) FROM documenti WHERE tipologia_origine = 'regola' "
        "AND tipologia != ?", (TIPOLOGIA_NON_CLASSIFICATO,)).fetchone()[0]
    n_manuale = conn.execute(
        "SELECT COUNT(*) FROM documenti WHERE tipologia_origine = 'manuale'"
    ).fetchone()[0]
    n_validazione = conn.execute(
        "SELECT COUNT(*) FROM documenti WHERE tipologia_origine = 'validazione'"
    ).fetchone()[0]
    n_ris_triage = conn.execute(
        "SELECT COUNT(*) FROM documenti WHERE riservatezza_origine = "
        "'triage' AND riservatezza != ''").fetchone()[0]
    n_ris_validazione = conn.execute(
        "SELECT COUNT(*) FROM documenti WHERE riservatezza_origine = "
        "'validazione'").fetchone()[0]
    n_ris_manuale = conn.execute(
        "SELECT COUNT(*) FROM documenti WHERE riservatezza_origine = "
        "'manuale'").fetchone()[0]
    n_agganciati = conn.execute(
        "SELECT COUNT(*) FROM documenti WHERE entita_id IS NOT NULL"
    ).fetchone()[0]
    pct = round(100.0 * (tot - n_non_class) / tot, 1) if tot else 0.0
    return {
        "totale_documenti": tot,
        "classificati_per_regola": n_regola,
        "classificati_per_validazione": n_validazione,
        "classificati_manuale": n_manuale,
        "non_classificati": n_non_class,
        "percentuale_copertura": pct,
        "riservatezza_da_triage": n_ris_triage,
        "riservatezza_da_validazione": n_ris_validazione,
        "riservatezza_manuale": n_ris_manuale,
        "agganciati_totale": n_agganciati,
    }


def documenti_filtrati(conn, entita_id=None, tipologia=None,
                       riservatezza=None, stato_classificazione=None,
                       senza_entita=False):
    """Elenco documenti secondo i filtri della pagina Esplora archivio."""
    sql = ("SELECT d.*, e.chiave AS entita_chiave, t.nome AS entita_tipo_nome "
           "FROM documenti d LEFT JOIN entita e ON e.id = d.entita_id "
           "LEFT JOIN tipi_entita t ON t.id = e.tipo_id")
    clausole, valori = [], []
    if senza_entita:
        clausole.append("d.entita_id IS NULL")
    elif entita_id:
        clausole.append("d.entita_id = ?")
        valori.append(entita_id)
    if tipologia:
        clausole.append("d.tipologia = ?")
        valori.append(tipologia)
    if riservatezza:
        clausole.append("d.riservatezza = ?")
        valori.append(riservatezza)
    if stato_classificazione == "classificato":
        clausole.append("d.tipologia != ?")
        valori.append(TIPOLOGIA_NON_CLASSIFICATO)
    elif stato_classificazione == "non_classificato":
        clausole.append("d.tipologia = ?")
        valori.append(TIPOLOGIA_NON_CLASSIFICATO)
    if clausole:
        sql += " WHERE " + " AND ".join(clausole)
    sql += " ORDER BY d.cartella_progetto, d.percorso_rel"
    return conn.execute(sql, valori).fetchall()


def riepilogo_entita(conn):
    """Per la navigazione entita' -> tipologia -> documenti: elenco
    entita' con il conteggio dei documenti agganciati, piu' il conteggio
    dei documenti senza entita' (il segnale di quanti restano da
    ricondurre, o davvero estranei al perimetro)."""
    righe = conn.execute(
        "SELECT e.id, e.chiave, e.cartella_origine, e.stato, "
        "t.nome AS tipo_nome, "
        "(SELECT COUNT(*) FROM documenti d WHERE d.entita_id = e.id) "
        "AS n_documenti "
        "FROM entita e JOIN tipi_entita t ON t.id = e.tipo_id "
        "ORDER BY t.nome, e.chiave").fetchall()
    n_senza = conn.execute(
        "SELECT COUNT(*) FROM documenti WHERE entita_id IS NULL").fetchone()[0]
    return righe, n_senza


def riepilogo_tipologie(conn, entita_id=None, senza_entita=False):
    """Conteggio documenti per tipologia, nello scope scelto (un'entita' o
    il bucket "senza entita'")."""
    sql = "SELECT tipologia, COUNT(*) AS n FROM documenti"
    clausole, valori = [], []
    if senza_entita:
        clausole.append("entita_id IS NULL")
    elif entita_id:
        clausole.append("entita_id = ?")
        valori.append(entita_id)
    if clausole:
        sql += " WHERE " + " AND ".join(clausole)
    sql += " GROUP BY tipologia ORDER BY tipologia"
    return conn.execute(sql, valori).fetchall()


def correggi_tipologia_manuale(conn, doc_id, tipologia):
    """Correzione manuale della tipologia sulla scheda documento: diventa
    la precedenza massima e non viene piu' toccata dai consolidamenti
    successivi, finche' non la si corregge di nuovo a mano."""
    conn.execute(
        "UPDATE documenti SET tipologia = ?, tipologia_origine = 'manuale', "
        "tipologia_regola_id = NULL, data_aggiornamento = ? WHERE id = ?",
        (tipologia, _adesso(), doc_id))
    conn.commit()


# ---------------------------------------------------------------------------
# Completezza per entita'
# ---------------------------------------------------------------------------

def completezza_entita(conn, tipo_id=None):
    """Per ciascuna entita', quali tipologie attese (TIPOLOGIE_ATTESE)
    risultano presenti tra i documenti agganciati e quali assenti: la
    misura di quanto l'archivio sia pronto per la fase 2."""
    sql = ("SELECT e.id, e.chiave, e.cartella_origine, e.stato, "
           "t.nome AS tipo_nome FROM entita e "
           "JOIN tipi_entita t ON t.id = e.tipo_id")
    valori = []
    if tipo_id:
        sql += " WHERE e.tipo_id = ?"
        valori.append(tipo_id)
    sql += " ORDER BY t.nome, e.chiave"
    esito = []
    for e in conn.execute(sql, valori):
        presenti_db = {r["tipologia"] for r in conn.execute(
            "SELECT DISTINCT tipologia FROM documenti WHERE entita_id = ? "
            "AND tipologia != ?", (e["id"], TIPOLOGIA_NON_CLASSIFICATO))}
        presenti = [t for t in TIPOLOGIE_ATTESE if t in presenti_db]
        assenti = [t for t in TIPOLOGIE_ATTESE if t not in presenti_db]
        pct = (round(100.0 * len(presenti) / len(TIPOLOGIE_ATTESE), 1)
               if TIPOLOGIE_ATTESE else 0.0)
        esito.append({"entita": e, "presenti": presenti, "assenti": assenti,
                      "percentuale": pct})
    return esito


# ---------------------------------------------------------------------------
# Export (contratto verso la fase 2)
# ---------------------------------------------------------------------------

def normalizza_riservatezza(valore):
    """Il valore di riservatezza nel vocabolario unico dell'export 1.1.
    Cio' che non vi corrisponde diventa stringa vuota: mai indovinare."""
    v = (valore or "").strip().lower()
    return v if v in VOCABOLARIO_RISERVATEZZA else ""


def _doc_export(d, collegate=None):
    """Un documento nel contratto 1.1. I campi della 1.0 restano identici;
    i nuovi si aggiungono in coda. `collegate` e' la mappa documento_id ->
    chiavi delle entita' collegate (prevalente per prima)."""
    return {"percorso": d["percorso_rel"], "tipologia": d["tipologia"],
            "tipologia_origine": d["tipologia_origine"],
            "riservatezza": d["riservatezza"] or "",
            "riservatezza_origine": d["riservatezza_origine"] or "",
            "stato": d["stato"],
            "riservatezza_normalizzata": normalizza_riservatezza(d["riservatezza"]),
            "lingua": d["lingua"] or "",
            "gruppo_traduzione": d["gruppo_traduzione"] or "",
            "data_documento": d["data_documento"] or "",
            "data_origine": d["data_origine"] or "",
            "revisione": d["revisione"] or "",
            "ruolo_temporale": d["ruolo_temporale"],
            "stato_vigenza": d["stato_vigenza"],
            "entita_collegate": (collegate or {}).get(d["id"], [])}


def costruisci_export(conn):
    """Struttura del contratto wikify-archivio/1.1: entita' con attributi e
    documenti agganciati, i documenti senza entita', le relazioni fra
    entita', le segnalazioni di vigenza e le statistiche di copertura.
    Evoluzione additiva della 1.0: ogni campo preesistente resta al suo
    posto con lo stesso significato."""
    chiave_di = {r["id"]: r["chiave"] for r in conn.execute(
        "SELECT id, chiave FROM entita")}
    collegate = {}
    for r in conn.execute(
            "SELECT documento_id, entita_id, prevalente FROM documenti_entita "
            "ORDER BY documento_id, prevalente DESC, entita_id"):
        chiave = chiave_di.get(r["entita_id"])
        if chiave:
            collegate.setdefault(r["documento_id"], []).append(chiave)
    entita_out = []
    for e in conn.execute(
            "SELECT e.*, t.nome AS tipo_nome FROM entita e "
            "JOIN tipi_entita t ON t.id = e.tipo_id ORDER BY t.nome, e.chiave"):
        documenti = conn.execute(
            "SELECT * FROM documenti WHERE entita_id = ? "
            "ORDER BY percorso_rel", (e["id"],)).fetchall()
        entita_out.append({
            "tipo": e["tipo_nome"], "chiave": e["chiave"],
            "cartella_origine": e["cartella_origine"], "stato": e["stato"],
            "attributi": [{"attributo": a["attributo"], "valore": a["valore"]}
                         for a in cat.attributi_di_entita(conn, e["id"])],
            "documenti": [_doc_export(d, collegate) for d in documenti],
        })
    orfani = conn.execute(
        "SELECT * FROM documenti WHERE entita_id IS NULL "
        "ORDER BY percorso_rel").fetchall()
    relazioni = [
        {"tipo": r["tipo_relazione"],
         "da": chiave_di.get(r["entita_da_id"], ""),
         "a": chiave_di.get(r["entita_a_id"], "")}
        for r in conn.execute(
            "SELECT tipo_relazione, entita_da_id, entita_a_id "
            "FROM relazioni_entita ORDER BY tipo_relazione, id")
        if chiave_di.get(r["entita_da_id"]) and chiave_di.get(r["entita_a_id"])]

    segnalazioni = [
        {"entita": chiave_di.get(sv["entita_id"], ""),
         "documento": sv["percorso_doc"], "causa": sv["percorso_causa"],
         "lingua": sv["lingua"] or "", "scarto_giorni": sv["scarto_giorni"],
         "stato": sv["stato"], "nota": sv["nota"] or ""}
        for sv in conn.execute(
            "SELECT s.*, d.percorso_rel AS percorso_doc, "
            "c.percorso_rel AS percorso_causa FROM segnalazioni_vigenza s "
            "JOIN documenti d ON d.id = s.documento_id "
            "JOIN documenti c ON c.id = s.causa_documento_id "
            "ORDER BY s.scarto_giorni DESC")]

    # Statistiche senza elenchi: i numeri, non le liste.
    from core import livello0
    copertura = {k: v for k, v in livello0.misura_copertura(conn).items()
                 if isinstance(v, (int, float))}
    vigenza = {k: v for k, v in livello0.misura_vigenza(conn).items()
               if isinstance(v, (int, float))}

    return {
        "formato": FORMATO_EXPORT,
        "data_export": datetime.datetime.now().isoformat(timespec="seconds"),
        "entita": entita_out,
        "documenti_senza_entita": [
            dict(_doc_export(d, collegate),
                 cartella_progetto=d["cartella_progetto"])
            for d in orfani],
        "relazioni": relazioni,
        "segnalazioni_vigenza": segnalazioni,
        "statistiche": {"copertura": copertura, "vigenza": vigenza},
    }
