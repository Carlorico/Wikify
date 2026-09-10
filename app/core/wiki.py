# -*- coding: utf-8 -*-
"""
Consulta: la wiki delle famiglie (livello 0, fase D).

La scheda di famiglia e' un rendering deterministico della base dati: nessuna
generazione libera, nessun servizio esterno. Tutto cio' che qui viene
prodotto discende da una lettura diretta delle tabelle gia' popolate dalla
ricostruzione di livello 0 (core/livello0.py) e dal consolidamento
dell'archivio logico (core/archivio.py).

Due profili di uscita:

  - "interno": tutto visibile; i blocchi non pubblici restano marcati come
    tali (badge di visibilita' sull'attributo, di riservatezza sul
    documento), ma il valore reale compare sempre;
  - "condivisibile": gli attributi con visibilita' diversa da 'pubblica'
    sono sostituiti dal segnaposto [riservato]; i documenti con
    riservatezza normalizzata 'riservato' compaiono solo per titolo, con la
    dicitura "documento riservato, non incluso"; i 'misto' restano inclusi
    ma con un'avvertenza esplicita.

Questo e' il vincolo centrale del modulo: il profilo condivisibile non deve
mai far comparire in chiaro un valore non pubblico, ne' il contenuto di un
documento riservato (che qui non viene comunque mai letto: si maneggiano
solo i metadati gia' consolidati)."""

import datetime
import os

from core import archivio as arc
from core import db
from core import livello0 as l0

PROFILO_INTERNO = "interno"
PROFILO_CONDIVISIBILE = "condivisibile"
PROFILI = (PROFILO_INTERNO, PROFILO_CONDIVISIBILE)

SEGNAPOSTO = "[riservato]"
NOTA_DOCUMENTO_RISERVATO = "documento riservato, non incluso"
AVVISO_RISERVATEZZA_MISTA = ("riservatezza mista: il documento e' incluso, "
                             "ma va verificato prima di condividerlo")

FORMATO_CORPUS = "wikify-corpus/1.0"


def _adesso():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")


def _etichetta_tipologia(tipologia):
    """Un'etichetta leggibile per una tipologia dichiarata (vocabolario
    condiviso con la Validazione AI). Non e' interpretazione: e' solo la
    stessa parola, con gli spazi al posto degli underscore."""
    return (tipologia or "").replace("_", " ").strip().capitalize()


def _nome_gruppo_documento(doc):
    """Il nome del gruppo cui appartiene un documento nella scheda. Per i
    documenti non ancora classificati da una regola di tipologia (il caso
    normale, non un'eccezione, finche' non esistono regole per l'albero)
    il gruppo prende il nome dell'ultima cartella del percorso: e' il solo
    raggruppamento disponibile e resta piu' leggibile della tipologia
    generica."""
    if doc["tipologia"] == arc.TIPOLOGIA_NON_CLASSIFICATO:
        cartelle = doc["percorso_rel"].replace("\\", "/").split("/")[:-1]
        return cartelle[-1] if cartelle else "Senza cartella"
    return _etichetta_tipologia(doc["tipologia"])


def _famiglia(conn, entita_id):
    return conn.execute(
        "SELECT e.* FROM entita e JOIN tipi_entita t ON t.id = e.tipo_id "
        "WHERE t.nome = ? AND e.id = ?", (l0.TIPO_FAMIGLIA, entita_id)
    ).fetchone()


def famiglie_attive(conn):
    """Le famiglie attive con i conteggi per l'indice della wiki: numero di
    articoli raccolti, numero di documenti collegati, numero di documenti
    candidati ad aggiornamento. Ordinate per chiave."""
    tipo = conn.execute("SELECT id FROM tipi_entita WHERE nome = ?",
                        (l0.TIPO_FAMIGLIA,)).fetchone()
    if not tipo:
        return []
    righe = conn.execute(
        "SELECT id, chiave, cartella_origine FROM entita "
        "WHERE tipo_id = ? AND stato = 'attiva' ORDER BY chiave",
        (tipo[0],)).fetchall()
    esito = []
    for r in righe:
        n_articoli = conn.execute(
            "SELECT COUNT(*) FROM relazioni_entita WHERE tipo_relazione = ? "
            "AND entita_da_id = ?", (l0.RELAZIONE, r["id"])).fetchone()[0]
        n_documenti = conn.execute(
            "SELECT COUNT(DISTINCT de.documento_id) FROM documenti_entita de "
            "JOIN documenti d ON d.id = de.documento_id "
            "WHERE de.entita_id = ? AND d.stato = 'attivo'",
            (r["id"],)).fetchone()[0]
        n_candidati = conn.execute(
            "SELECT COUNT(DISTINCT de.documento_id) FROM documenti_entita de "
            "JOIN documenti d ON d.id = de.documento_id "
            "WHERE de.entita_id = ? AND d.stato = 'attivo' "
            "AND d.stato_vigenza = 'da_aggiornare'", (r["id"],)).fetchone()[0]
        esito.append({"id": r["id"], "chiave": r["chiave"],
                      "cartella_origine": r["cartella_origine"],
                      "n_articoli": n_articoli, "n_documenti": n_documenti,
                      "n_candidati": n_candidati})
    return esito


def _attributi_entita(conn, entita_id):
    """Gli attributi di un'entita' con la loro visibilita', deduplicati per
    nome e valore. Non si riusa core.catalogo.attributi_di_entita perche'
    quella funzione non porta la visibilita', che qui e' il dato che serve
    al mascheramento. A parita' di nome e valore, in caso di righe con
    visibilita' diverse (piu' import), vince la piu' recente."""
    righe = conn.execute(
        "SELECT nome_attributo, valore, visibilita FROM attributi_entita "
        "WHERE entita_id = ? ORDER BY id", (entita_id,)).fetchall()
    per_chiave = {}
    for r in righe:
        per_chiave[(r["nome_attributo"], r["valore"])] = r["visibilita"]
    return [{"nome": nome, "valore": valore, "visibilita": vis}
            for (nome, valore), vis in sorted(per_chiave.items())]


def _filtra_attributi(attributi, profilo):
    """Gli attributi come vanno mostrati nel profilo richiesto: il valore
    reale in ogni caso, tranne nel profilo condivisibile quando la
    visibilita' non e' 'pubblica', dove diventa il segnaposto."""
    esito = []
    for a in attributi:
        mascherato = (profilo == PROFILO_CONDIVISIBILE
                     and a["visibilita"] != "pubblica")
        esito.append({"nome": a["nome"],
                      "valore": SEGNAPOSTO if mascherato else a["valore"],
                      "visibilita": a["visibilita"],
                      "mascherato": mascherato})
    return esito


def _articoli_famiglia(conn, entita_id, profilo):
    """Gli articoli raccolti dalla famiglia (relazione 'raccoglie'), ciascuno
    con gli attributi filtrati per profilo."""
    righe = conn.execute(
        "SELECT e.id, e.chiave FROM relazioni_entita r "
        "JOIN entita e ON e.id = r.entita_a_id "
        "WHERE r.tipo_relazione = ? AND r.entita_da_id = ? "
        "ORDER BY e.chiave", (l0.RELAZIONE, entita_id)).fetchall()
    return [{"id": r["id"], "chiave": r["chiave"],
            "attributi": _filtra_attributi(_attributi_entita(conn, r["id"]),
                                           profilo)}
           for r in righe]


def _doc_wiki(doc, profilo):
    """Un documento nella forma della scheda: metadati soli, mai il
    contenuto. Nel profilo condivisibile un documento riservato compare solo
    per titolo; uno misto resta incluso con un'avvertenza."""
    normalizzata = arc.normalizza_riservatezza(doc["riservatezza"])
    nome = os.path.basename(doc["percorso_rel"])
    if profilo == PROFILO_CONDIVISIBILE and normalizzata == "riservato":
        return {"percorso": doc["percorso_rel"], "nome": nome,
                "riservatezza": normalizzata, "escluso": True,
                "nota": NOTA_DOCUMENTO_RISERVATO}
    esito = {"percorso": doc["percorso_rel"], "nome": nome,
            "lingua": doc["lingua"] or "", "revisione": doc["revisione"] or "",
            "data_documento": doc["data_documento"] or "",
            "stato_vigenza": doc["stato_vigenza"],
            "riservatezza": normalizzata, "escluso": False, "avviso": ""}
    if profilo == PROFILO_CONDIVISIBILE and normalizzata == "misto":
        esito["avviso"] = AVVISO_RISERVATEZZA_MISTA
    return esito


def _documenti_famiglia(conn, entita_id, profilo):
    """I documenti collegati alla famiglia (documenti_entita, non solo per
    percorso di cartella: comprende anche le note trasversali collegate da
    contenuto), raggruppati per tipologia. Restituisce una lista ordinata di
    {gruppo, documenti}, cosi' la stessa struttura serve sia all'HTML sia al
    markdown."""
    righe = conn.execute(
        "SELECT DISTINCT d.* FROM documenti d "
        "JOIN documenti_entita de ON de.documento_id = d.id "
        "WHERE de.entita_id = ? AND d.stato = 'attivo' "
        "ORDER BY d.percorso_rel", (entita_id,)).fetchall()
    gruppi = {}
    for doc in righe:
        gruppo = _nome_gruppo_documento(doc)
        gruppi.setdefault(gruppo, []).append(_doc_wiki(doc, profilo))
    return [{"gruppo": nome, "documenti": docs}
           for nome, docs in sorted(gruppi.items())]


def _note_applicabili(conn, entita_id):
    """I documenti di ruolo 'aggiornamento' collegati alla famiglia, in
    ordine cronologico: sono le note che chi consulta la scheda deve
    considerare, anche quando dichiarate senza data (che restano in coda)."""
    righe = conn.execute(
        "SELECT DISTINCT d.* FROM documenti d "
        "JOIN documenti_entita de ON de.documento_id = d.id "
        "WHERE de.entita_id = ? AND d.stato = 'attivo' "
        "AND d.ruolo_temporale = ? "
        "ORDER BY (d.data_documento = '') ASC, d.data_documento, d.percorso_rel",
        (entita_id, l0.RUOLO_AGGIORNAMENTO)).fetchall()
    return [{"percorso": d["percorso_rel"],
            "nome": os.path.basename(d["percorso_rel"]),
            "data_documento": d["data_documento"] or "",
            "lingua": d["lingua"] or ""} for d in righe]


def _avvisi_vigenza(conn, entita_id):
    """Le segnalazioni di vigenza aperte per questa famiglia."""
    righe = conn.execute(
        "SELECT s.scarto_giorni, s.lingua, d.percorso_rel AS documento, "
        "c.percorso_rel AS causa FROM segnalazioni_vigenza s "
        "JOIN documenti d ON d.id = s.documento_id "
        "JOIN documenti c ON c.id = s.causa_documento_id "
        "WHERE s.entita_id = ? AND s.stato = 'aperta' "
        "ORDER BY s.scarto_giorni DESC", (entita_id,)).fetchall()
    return [{"documento": r["documento"], "causa": r["causa"],
            "lingua": r["lingua"] or "", "scarto_giorni": r["scarto_giorni"]}
           for r in righe]


def _completezza_famiglia(conn, entita_id):
    """Per ciascuna lingua presente nei documenti della famiglia, i gruppi
    di traduzione che su questa famiglia esistono in una sola lingua. Stessa
    regola del controllo globale (core.livello0.gruppi_traduzione_incompleti),
    ma limitata ai documenti di questa famiglia: un gruppo completo altrove
    puo' essere incompleto qui, e viceversa."""
    righe = conn.execute(
        "SELECT DISTINCT d.gruppo_traduzione, d.lingua, d.percorso_rel "
        "FROM documenti d JOIN documenti_entita de ON de.documento_id = d.id "
        "WHERE de.entita_id = ? AND d.stato = 'attivo' "
        "AND d.gruppo_traduzione <> '' "
        "ORDER BY d.gruppo_traduzione, d.percorso_rel", (entita_id,)).fetchall()
    per_gruppo = {}
    for r in righe:
        per_gruppo.setdefault(r["gruppo_traduzione"], []).append(r)
    per_lingua = {}
    for gruppo, righe_gruppo in sorted(per_gruppo.items()):
        if len(righe_gruppo) != 1:
            continue
        r = righe_gruppo[0]
        lingua = r["lingua"] or "n/d"
        per_lingua.setdefault(lingua, []).append(
            {"gruppo_traduzione": gruppo, "esempio": r["percorso_rel"]})
    return per_lingua


def scheda_famiglia(conn, entita_id, profilo=PROFILO_INTERNO):
    """La scheda completa di una famiglia, nel profilo richiesto. Restituisce
    None se l'entita' non esiste o non e' una famiglia: chi chiama decide se
    e' un 404 o un'anomalia da segnalare."""
    if profilo not in PROFILI:
        profilo = PROFILO_INTERNO
    fam = _famiglia(conn, entita_id)
    if not fam:
        return None
    return {
        "id": fam["id"],
        "chiave": fam["chiave"],
        "percorso_origine": fam["cartella_origine"] or "",
        "stato": fam["stato"],
        "profilo": profilo,
        "articoli": _articoli_famiglia(conn, entita_id, profilo),
        "documenti": _documenti_famiglia(conn, entita_id, profilo),
        "note_applicabili": _note_applicabili(conn, entita_id),
        "avvisi_vigenza": _avvisi_vigenza(conn, entita_id),
        "completezza": _completezza_famiglia(conn, entita_id),
    }


# ---------------------------------------------------------------------------
# Rendering markdown: la forma pensata per un modello, non per uno schermo.
# ---------------------------------------------------------------------------

def _riga_documento_markdown(doc):
    if doc.get("escluso"):
        return "- %s (%s)" % (doc["nome"], doc["nota"])
    pezzi = ["lingua %s" % (doc["lingua"] or "n/d"),
            "revisione %s" % (doc["revisione"] or "n/d"),
            "data %s" % (doc["data_documento"] or "n/d"),
            "stato %s" % doc["stato_vigenza"]]
    riga = "- %s (%s)" % (doc["nome"], ", ".join(pezzi))
    if doc.get("avviso"):
        riga += "; avvertenza: %s" % doc["avviso"]
    return riga


def _sezione_markdown(scheda):
    righe = ["## Famiglia %s" % scheda["chiave"], ""]
    if scheda["percorso_origine"]:
        righe.append("Percorso di origine: %s" % scheda["percorso_origine"])
        righe.append("")

    if scheda["articoli"]:
        righe.append("### Articoli")
        for art in scheda["articoli"]:
            if art["attributi"]:
                dettaglio = "; ".join("%s: %s" % (a["nome"], a["valore"])
                                      for a in art["attributi"])
            else:
                dettaglio = "nessun attributo registrato"
            righe.append("- %s: %s" % (art["chiave"], dettaglio))
        righe.append("")

    if scheda["documenti"]:
        righe.append("### Documenti")
        for gruppo in scheda["documenti"]:
            righe.append("#### %s" % gruppo["gruppo"])
            for doc in gruppo["documenti"]:
                righe.append(_riga_documento_markdown(doc))
            righe.append("")

    if scheda["note_applicabili"]:
        righe.append("### Note applicabili")
        for nota in scheda["note_applicabili"]:
            righe.append("- %s (data %s, lingua %s)" % (
                nota["nome"], nota["data_documento"] or "n/d",
                nota["lingua"] or "n/d"))
        righe.append("")

    if scheda["avvisi_vigenza"]:
        righe.append("### Avvisi di vigenza")
        for avviso in scheda["avvisi_vigenza"]:
            righe.append("- %s risulta superato da %s (scarto %d giorni)" % (
                avviso["documento"], avviso["causa"], avviso["scarto_giorni"]))
        righe.append("")

    if scheda["completezza"]:
        righe.append("### Completezza per lingua")
        for lingua, gruppi in sorted(scheda["completezza"].items()):
            for g in gruppi:
                righe.append(
                    "- lingua %s: il gruppo di traduzione «%s» risulta "
                    "presente in questa sola lingua (esempio: %s)" % (
                        lingua, g["gruppo_traduzione"], g["esempio"]))
        righe.append("")

    return "\n".join(righe).rstrip() + "\n"


def scheda_markdown(conn, entita_id, profilo=PROFILO_CONDIVISIBILE):
    """La singola scheda di famiglia, in forma markdown. Restituisce None se
    l'entita' non e' una famiglia esistente."""
    scheda = scheda_famiglia(conn, entita_id, profilo)
    if scheda is None:
        return None
    intestazione = ("# Famiglia %s\n\nFormato: %s\nGenerato il: %s\n"
                    "Profilo: %s\n\n---\n\n" % (
                        scheda["chiave"], FORMATO_CORPUS, _adesso(), profilo))
    corpo = _sezione_markdown(scheda).split("\n", 2)
    # la sezione riparte da "## Famiglia ..."; per la scheda singola basta il
    # corpo senza ripetere il titolo di livello 2, gia' presente come H1.
    corpo_senza_titolo = "\n".join(corpo[2:]) if len(corpo) > 2 else ""
    return intestazione + corpo_senza_titolo


def corpus_markdown(conn, profilo=PROFILO_CONDIVISIBILE):
    """Il corpus intero, una sezione per famiglia attiva. E' il testo
    pensato per essere dato in pasto a un modello: il profilo di default e'
    condivisibile, cosi' chi lo invoca senza specificare nulla non rischia di
    portare fuori un valore riservato per distrazione."""
    if profilo not in PROFILI:
        profilo = PROFILO_CONDIVISIBILE
    famiglie = famiglie_attive(conn)
    righe = ["# Wikify, corpus delle famiglie", "",
            "Formato: %s" % FORMATO_CORPUS,
            "Generato il: %s" % _adesso(),
            "Profilo: %s" % profilo, "", "---", ""]
    for f in famiglie:
        scheda = scheda_famiglia(conn, f["id"], profilo)
        righe.append(_sezione_markdown(scheda))
    return "\n".join(righe).rstrip() + "\n"
