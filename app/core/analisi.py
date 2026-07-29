# -*- coding: utf-8 -*-
"""
Modulo Connettore MCP e sessioni di analisi (progettazione_moduli.md,
Modulo 4): impostazioni di analisi (cascata di modelli, ambito, prezzi),
apertura e avanzamento delle sessioni, vincolo di perimetro sulla lettura
dei file, consegna delle bozze legate alla sessione e KPI di esito.

Questo modulo e' usato sia dalle viste Flask (pagina "Impostazioni
analisi" e sezione "Sessioni di analisi" della pagina Metriche) sia dal
server MCP (app/mcp_server/server.py), che importa core direttamente e
condivide la stessa base dati.
"""

import datetime
import json
import os
import random

from core import db, estrazione
from core import validazione as val

# ---------------------------------------------------------------------------
# Impostazioni di analisi (tabella impostazioni, chiavi con prefisso analisi_)
# ---------------------------------------------------------------------------

CHIAVI = {
    "modello_primario": "analisi_modello_primario",
    "modello_rinforzo": "analisi_modello_rinforzo",
    "soglia_rinforzo": "analisi_soglia_rinforzo",
    "rinforzo_obbligatorio": "analisi_rinforzo_obbligatorio_riservatezza",
    "ambito": "analisi_ambito",
    "campione_n": "analisi_campione_n",
    "campione_seed": "analisi_campione_seed",
    "prezzi_json": "analisi_prezzi_json",
}

DEFAULT_MODELLO_PRIMARIO = "claude-haiku"
DEFAULT_MODELLO_RINFORZO = "claude-sonnet"
DEFAULT_SOGLIA_RINFORZO = 0.7
DEFAULT_AMBITO = "campione"
DEFAULT_CAMPIONE_N = 15

AMBITI = ("campione", "archivio_intero")

MODELLI_SUGGERITI = ["claude-haiku", "claude-sonnet", "claude-opus",
                     "locale-ollama"]

# Prezzi indicativi di partenza (euro per milione di token), modificabili
# dalla pagina Impostazioni analisi.
PREZZI_DEFAULT = [
    {"modello": "claude-haiku", "prezzo_in": 0.25, "prezzo_out": 1.25},
    {"modello": "claude-sonnet", "prezzo_in": 3.0, "prezzo_out": 15.0},
    {"modello": "claude-opus", "prezzo_in": 15.0, "prezzo_out": 75.0},
    {"modello": "locale-ollama", "prezzo_in": 0.0, "prezzo_out": 0.0},
]


def _genera_seed():
    return random.randint(1, 2_000_000_000)


def leggi_impostazioni(conn):
    """Le impostazioni di analisi correnti, applicando i default se non
    sono ancora mai state salvate. Il seed del campione viene generato e
    persistito al primo utilizzo, cosi' resta stabile nelle chiamate
    successive."""
    soglia_raw = db.get_impostazione(conn, CHIAVI["soglia_rinforzo"], "")
    try:
        soglia = float(soglia_raw)
    except ValueError:
        soglia = DEFAULT_SOGLIA_RINFORZO

    seed_raw = db.get_impostazione(conn, CHIAVI["campione_seed"], "")
    try:
        seed = int(seed_raw)
    except ValueError:
        seed = _genera_seed()
        db.set_impostazione(conn, CHIAVI["campione_seed"], str(seed))

    n_raw = db.get_impostazione(conn, CHIAVI["campione_n"],
                                str(DEFAULT_CAMPIONE_N))
    try:
        n = int(n_raw)
    except ValueError:
        n = DEFAULT_CAMPIONE_N

    prezzi_raw = db.get_impostazione(conn, CHIAVI["prezzi_json"], "")
    prezzi = None
    if prezzi_raw:
        try:
            prezzi = json.loads(prezzi_raw)
        except ValueError:
            prezzi = None
    if not prezzi:
        prezzi = PREZZI_DEFAULT

    ambito = db.get_impostazione(conn, CHIAVI["ambito"], DEFAULT_AMBITO) \
        or DEFAULT_AMBITO
    if ambito not in AMBITI:
        ambito = DEFAULT_AMBITO

    return {
        "modello_primario": db.get_impostazione(
            conn, CHIAVI["modello_primario"], DEFAULT_MODELLO_PRIMARIO)
            or DEFAULT_MODELLO_PRIMARIO,
        "modello_rinforzo": db.get_impostazione(
            conn, CHIAVI["modello_rinforzo"], DEFAULT_MODELLO_RINFORZO)
            or DEFAULT_MODELLO_RINFORZO,
        "soglia_rinforzo": soglia,
        "rinforzo_obbligatorio": db.get_impostazione(
            conn, CHIAVI["rinforzo_obbligatorio"], "1") == "1",
        "ambito": ambito,
        "campione_n": n,
        "campione_seed": seed,
        "prezzi": prezzi,
    }


def _prezzi_da_form(form):
    """Ricostruisce la tabella dei prezzi dai campi ripetuti del form
    (prezzo_modello_N, prezzo_in_N, prezzo_out_N). Restituisce
    (prezzi, errori)."""
    prezzi = []
    errori = []
    indice = 0
    while ("prezzo_modello_%d" % indice) in form:
        modello = (form.get("prezzo_modello_%d" % indice) or "").strip()
        p_in_raw = (form.get("prezzo_in_%d" % indice) or "").strip()
        p_out_raw = (form.get("prezzo_out_%d" % indice) or "").strip()
        indice += 1
        if not modello:
            continue
        try:
            p_in = float((p_in_raw or "0").replace(",", "."))
            p_out = float((p_out_raw or "0").replace(",", "."))
        except ValueError:
            errori.append("Prezzo non valido per il modello %s." % modello)
            continue
        if p_in < 0 or p_out < 0:
            errori.append(
                "I prezzi per il modello %s devono essere non negativi."
                % modello)
            continue
        prezzi.append({"modello": modello, "prezzo_in": p_in,
                       "prezzo_out": p_out})
    if not prezzi:
        prezzi = list(PREZZI_DEFAULT)
    return prezzi, errori


def valida_e_salva(conn, form):
    """Valida e salva il form delle impostazioni di analisi. Restituisce
    (ok, errori): se ok e' False nulla viene salvato."""
    errori = []

    modello_primario = (form.get("modello_primario") or "").strip() \
        or DEFAULT_MODELLO_PRIMARIO
    modello_rinforzo = (form.get("modello_rinforzo") or "").strip() \
        or DEFAULT_MODELLO_RINFORZO

    soglia_raw = (form.get("soglia_rinforzo") or "").strip()
    soglia = None
    try:
        soglia = float(soglia_raw.replace(",", "."))
    except ValueError:
        pass
    if soglia is None or soglia < 0 or soglia > 1:
        errori.append(
            "La soglia di confidenza per il rinforzo deve essere un "
            "numero tra 0 e 1.")

    rinforzo_obbligatorio = form.get("rinforzo_obbligatorio") == "on"

    ambito = form.get("ambito") or DEFAULT_AMBITO
    if ambito not in AMBITI:
        ambito = DEFAULT_AMBITO

    n_raw = (form.get("campione_n") or "").strip()
    n = None
    try:
        n = int(n_raw)
    except ValueError:
        pass
    if ambito == "campione" and (n is None or n < 1):
        errori.append(
            "Il numero di progetti del campione deve essere almeno 1.")

    seed_raw = (form.get("campione_seed") or "").strip()
    if seed_raw:
        try:
            seed = int(seed_raw)
        except ValueError:
            errori.append("Il seed del campione deve essere un numero "
                          "intero.")
            seed = None
    else:
        seed_attuale = db.get_impostazione(conn, CHIAVI["campione_seed"], "")
        seed = int(seed_attuale) if seed_attuale.isdigit() else _genera_seed()

    prezzi, errori_prezzi = _prezzi_da_form(form)
    errori.extend(errori_prezzi)

    if errori:
        return False, errori

    db.set_impostazione(conn, CHIAVI["modello_primario"], modello_primario)
    db.set_impostazione(conn, CHIAVI["modello_rinforzo"], modello_rinforzo)
    db.set_impostazione(conn, CHIAVI["soglia_rinforzo"], str(soglia))
    db.set_impostazione(conn, CHIAVI["rinforzo_obbligatorio"],
                        "1" if rinforzo_obbligatorio else "0")
    db.set_impostazione(conn, CHIAVI["ambito"], ambito)
    db.set_impostazione(conn, CHIAVI["campione_n"],
                        str(n or DEFAULT_CAMPIONE_N))
    db.set_impostazione(conn, CHIAVI["campione_seed"], str(seed))
    db.set_impostazione(conn, CHIAVI["prezzi_json"], json.dumps(prezzi))
    return True, []


# ---------------------------------------------------------------------------
# Perimetro condivisibile per l'apertura della sessione
# ---------------------------------------------------------------------------

def _ultima_scansione_completata(conn):
    return conn.execute(
        "SELECT * FROM scansioni WHERE stato = 'completata' "
        "ORDER BY id DESC LIMIT 1").fetchone()


def cartelle_condivisibili(conn, scan=None):
    """Dizionario {cartella_progetto: [percorso_rel, ...]} con le cartelle
    di primo livello che hanno almeno un file condivisibile secondo il
    triage dell'ultima scansione completata (o quella indicata). I
    percorsi sono relativi alla radice dell'archivio, come restituiti da
    core.db.elenco_condivisibili."""
    if scan is None:
        scan = _ultima_scansione_completata(conn)
    if scan is None:
        return {}
    condivisibili = db.elenco_condivisibili(conn, scan["id"])
    cartelle = {}
    for f in condivisibili:
        parti = f.replace(os.sep, "/").split("/")
        if len(parti) < 2:
            continue  # file direttamente in radice: non appartiene a un progetto
        cartella = parti[0]
        cartelle.setdefault(cartella, []).append(f)
    return cartelle


# ---------------------------------------------------------------------------
# Sessioni di analisi
# ---------------------------------------------------------------------------

def sessione_aperta(conn):
    return conn.execute(
        "SELECT * FROM sessioni_analisi WHERE stato = 'aperta' "
        "ORDER BY id DESC LIMIT 1").fetchone()


def avanzamento(conn, sessione_id, assegnate):
    """Cartelle assegnate (completate/rimanenti): completata quando esiste
    almeno un lotto legato alla sessione per quella cartella."""
    completate = []
    for cartella in assegnate:
        n = conn.execute(
            "SELECT COUNT(*) FROM lotti_validazione "
            "WHERE sessione_id = ? AND cartella_progetto = ?",
            (sessione_id, cartella)).fetchone()[0]
        if n:
            completate.append(cartella)
    rimanenti = [c for c in assegnate if c not in completate]
    return sorted(completate), sorted(rimanenti)


def apri_sessione(conn):
    """Se esiste una sessione aperta la restituisce; altrimenti la crea
    secondo le impostazioni correnti (ambito campione o archivio intero).

    Restituisce (sessione_row, cartelle_assegnate_dict, creata_bool)."""
    esistente = sessione_aperta(conn)
    if esistente is not None:
        try:
            cartelle = json.loads(esistente["cartelle_assegnate_json"]
                                  or "{}")
        except ValueError:
            cartelle = {}
        return esistente, cartelle, False

    impostazioni = leggi_impostazioni(conn)
    scan = _ultima_scansione_completata(conn)
    tutte = cartelle_condivisibili(conn, scan)
    nomi = sorted(tutte.keys())
    seed = impostazioni["campione_seed"]

    if impostazioni["ambito"] == "campione":
        n = min(impostazioni["campione_n"], len(nomi))
        rnd = random.Random(seed)
        scelte = sorted(rnd.sample(nomi, n)) if n else []
    else:
        scelte = nomi

    assegnate = {c: tutte[c] for c in scelte}
    adesso = datetime.datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT INTO sessioni_analisi (data_avvio, stato, ambito, "
        "n_progetti_richiesti, seed, modello_primario, modello_rinforzo, "
        "soglia_rinforzo, scansione_id, cartelle_assegnate_json) "
        "VALUES (?, 'aperta', ?, ?, ?, ?, ?, ?, ?, ?)",
        (adesso, impostazioni["ambito"], impostazioni["campione_n"], seed,
         impostazioni["modello_primario"], impostazioni["modello_rinforzo"],
         impostazioni["soglia_rinforzo"], scan["id"] if scan else None,
         json.dumps(assegnate)))
    conn.commit()
    sid = cur.lastrowid
    riga = conn.execute("SELECT * FROM sessioni_analisi WHERE id = ?",
                        (sid,)).fetchone()
    return riga, assegnate, True


def file_assegnati(cartelle_assegnate):
    """Insieme di tutti i percorsi assegnati alla sessione, indipendente
    dalla cartella progetto di appartenenza."""
    tutti = set()
    for lista in cartelle_assegnate.values():
        tutti.update(lista)
    return tutti


def leggi_file(conn, radice, percorso_rel):
    """Testo estratto di un file della sessione aperta, con vincolo di
    perimetro imposto dal server: restituisce (risultato, None) se
    ammesso, (None, messaggio_errore) altrimenti. Registra i caratteri
    letti nella sessione (una sola volta per file, per non falsare la
    stima dei token in caso di riletture)."""
    sessione = sessione_aperta(conn)
    if sessione is None:
        return None, ("Nessuna sessione di analisi aperta: chiamare prima "
                      "lo strumento ottieni_incarico.")
    try:
        assegnate = json.loads(sessione["cartelle_assegnate_json"] or "{}")
    except ValueError:
        assegnate = {}
    percorso_rel = (percorso_rel or "").strip().replace(os.sep, "/")
    if percorso_rel not in file_assegnati(assegnate):
        return None, (
            "Il file '%s' non è tra i file condivisibili assegnati a "
            "questa sessione: lettura rifiutata per vincolo di perimetro."
            % percorso_rel)
    if not radice or not os.path.isdir(radice):
        return None, "Cartella archivio non impostata o non trovata."
    base = os.path.realpath(radice)
    reale = os.path.realpath(os.path.join(radice, percorso_rel))
    if not reale.startswith(base + os.sep) or not os.path.isfile(reale):
        return None, "File non trovato sul filesystem dell'archivio."
    try:
        unita = estrazione.estrai(reale)
    except Exception as exc:
        return None, "Impossibile estrarre il testo dal file (%s)." % exc

    testo = "\n".join(t for _pos, t in unita)
    n_caratteri = len(testo)
    adesso = datetime.datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT OR IGNORE INTO sessioni_analisi_letture "
        "(sessione_id, percorso_rel, caratteri, data) VALUES (?, ?, ?, ?)",
        (sessione["id"], percorso_rel, n_caratteri, adesso))
    if cur.rowcount:
        conn.execute(
            "UPDATE sessioni_analisi SET caratteri_letti = "
            "caratteri_letti + ? WHERE id = ?",
            (n_caratteri, sessione["id"]))
    conn.commit()
    return {"percorso": percorso_rel, "unita": unita,
            "n_caratteri": n_caratteri}, None


def consegna_bozza(conn, dati, nome_file=None):
    """Consegna di una bozza legata alla sessione aperta: stessa
    validazione severa dell'import manuale (core.validazione.importa_bozza),
    con registrazione dei caratteri prodotti. Restituisce (lotto_id,
    riepilogo) oppure (None, messaggio_di_rifiuto)."""
    sessione = sessione_aperta(conn)
    if sessione is None:
        return None, ("Nessuna sessione di analisi aperta: chiamare prima "
                      "lo strumento ottieni_incarico.")
    if not nome_file:
        cartella = dati.get("cartella_progetto") if isinstance(dati, dict) \
            else None
        nome_file = "bozza_mcp_%s.json" % (cartella or "sessione")
    lotto_id, esito = val.importa_bozza(conn, nome_file, dati)
    if lotto_id is None:
        return None, esito
    conn.execute("UPDATE lotti_validazione SET sessione_id = ? WHERE id = ?",
                (sessione["id"], lotto_id))
    n_prodotti = len(json.dumps(dati, ensure_ascii=False)) \
        if isinstance(dati, (dict, list)) else 0
    conn.execute(
        "UPDATE sessioni_analisi SET caratteri_prodotti = "
        "caratteri_prodotti + ? WHERE id = ?", (n_prodotti, sessione["id"]))
    conn.commit()
    return lotto_id, esito


def stato_sessione(conn, chiudi=False):
    """Avanzamento della sessione aperta (cartelle completate/rimanenti);
    se chiudi e' vero e la sessione e' aperta, la chiude. Restituisce
    None se non c'e' alcuna sessione aperta al momento della chiamata."""
    sessione = sessione_aperta(conn)
    if sessione is None:
        return None
    try:
        assegnate = json.loads(sessione["cartelle_assegnate_json"] or "{}")
    except ValueError:
        assegnate = {}
    completate, rimanenti = avanzamento(conn, sessione["id"], assegnate)
    if chiudi:
        conn.execute(
            "UPDATE sessioni_analisi SET stato = 'chiusa', data_chiusura = ? "
            "WHERE id = ?",
            (datetime.datetime.now().isoformat(timespec="seconds"),
             sessione["id"]))
        conn.commit()
        sessione = conn.execute(
            "SELECT * FROM sessioni_analisi WHERE id = ?",
            (sessione["id"],)).fetchone()
    return {"sessione": sessione, "cartelle_assegnate": assegnate,
            "cartelle_completate": completate,
            "cartelle_rimanenti": rimanenti}


def elenco_sessioni(conn):
    return conn.execute(
        "SELECT * FROM sessioni_analisi ORDER BY id DESC").fetchall()


# ---------------------------------------------------------------------------
# KPI di esito (sezione "Sessioni di analisi" della pagina Metriche)
# ---------------------------------------------------------------------------

def kpi_sessione(conn, sessione):
    """KPI di esito di una sessione: progetti assegnati/completati, file
    nel perimetro/letti/esclusi, proposte per campo e per fascia di
    confidenza, scarti per motivo, durata, token e costo stimati."""
    sid = sessione["id"]
    try:
        assegnate = json.loads(sessione["cartelle_assegnate_json"] or "{}")
    except ValueError:
        assegnate = {}
    n_progetti_assegnati = len(assegnate)
    lotti = conn.execute(
        "SELECT * FROM lotti_validazione WHERE sessione_id = ?",
        (sid,)).fetchall()
    cartelle_con_lotto = {l["cartella_progetto"] for l in lotti}
    n_progetti_completati = len(cartelle_con_lotto & set(assegnate.keys()))

    n_file_perimetro = sum(len(v) for v in assegnate.values())
    n_file_letti = conn.execute(
        "SELECT COUNT(*) FROM sessioni_analisi_letture WHERE sessione_id = ?",
        (sid,)).fetchone()[0]
    n_file_esclusi = max(0, n_file_perimetro - n_file_letti)

    proposte_per_campo = {c: 0 for c in val.CAMPI}
    fasce_confidenza = {etichetta: 0 for etichetta, _min, _max
                        in val.FASCE_CONFIDENZA}
    for lotto in lotti:
        for riga in conn.execute(
                "SELECT campo, confidenza FROM proposte WHERE lotto_id = ?",
                (lotto["id"],)):
            proposte_per_campo[riga["campo"]] = \
                proposte_per_campo.get(riga["campo"], 0) + 1
            for etichetta, minimo, massimo in val.FASCE_CONFIDENZA:
                if minimo <= (riga["confidenza"] or 0) < massimo:
                    fasce_confidenza[etichetta] += 1
                    break

    scarti_per_motivo = {}
    for lotto in lotti:
        try:
            dettaglio = json.loads(lotto["dettaglio_scarti_json"] or "{}")
        except ValueError:
            dettaglio = {}
        for motivo, n in (dettaglio.get("conteggi") or {}).items():
            scarti_per_motivo[motivo] = scarti_per_motivo.get(motivo, 0) + n

    durata_secondi = None
    if sessione["data_chiusura"]:
        try:
            inizio = datetime.datetime.fromisoformat(sessione["data_avvio"])
            fine = datetime.datetime.fromisoformat(sessione["data_chiusura"])
            durata_secondi = (fine - inizio).total_seconds()
        except (ValueError, TypeError):
            durata_secondi = None

    caratteri_letti = sessione["caratteri_letti"] or 0
    caratteri_prodotti = sessione["caratteri_prodotti"] or 0
    token_in = caratteri_letti / 4.0
    token_out = caratteri_prodotti / 4.0
    token_stimati = round(token_in + token_out)

    prezzi = {p["modello"]: p for p in leggi_impostazioni(conn)["prezzi"]}
    prezzo = prezzi.get(sessione["modello_primario"])
    costo_stimato = None
    if prezzo:
        costo_stimato = round(
            token_in / 1_000_000.0 * prezzo["prezzo_in"]
            + token_out / 1_000_000.0 * prezzo["prezzo_out"], 4)

    return {
        "sessione": sessione,
        "n_progetti_assegnati": n_progetti_assegnati,
        "n_progetti_completati": n_progetti_completati,
        "n_file_perimetro": n_file_perimetro,
        "n_file_letti": n_file_letti,
        "n_file_esclusi": n_file_esclusi,
        "proposte_per_campo": proposte_per_campo,
        "fasce_confidenza": fasce_confidenza,
        "scarti_per_motivo": scarti_per_motivo,
        "durata_secondi": durata_secondi,
        "token_stimati": token_stimati,
        "costo_stimato": costo_stimato,
    }
