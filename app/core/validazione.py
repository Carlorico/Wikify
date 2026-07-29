# -*- coding: utf-8 -*-
"""
Modulo Validazione AI, logica di dominio: export del perimetro
condivisibile, import severo delle bozze dell'agente (contratto
wikify-bozza/1.0), coda di revisione, estratto del documento con evidenza,
metriche di affidabilita' ed export delle correzioni.
"""

import datetime
import json
import os
import statistics

from core import db, estrazione

# ---------------------------------------------------------------------------
# Contratto e tassonomie (v. agente/formato_bozze.md, congelato)
# ---------------------------------------------------------------------------

FORMATO_BOZZA = "wikify-bozza/1.0"
FORMATO_PERIMETRO = "wikify-perimetro/1.0"

CAMPI = ("tipologia", "riservatezza", "versione_ufficiale",
         "forma_caratteristiche")

TASSONOMIE = {
    "tipologia": ["specifica_tecnica", "manuale_installazione",
                  "manuale_manutenzione", "parametri_interconnessione",
                  "dati_sperimentazione", "configurazione", "disegno_schema",
                  "corrispondenza", "altro"],
    "riservatezza": ["condivisibile", "riservato", "misto"],
    "forma_caratteristiche": ["tabellare", "prosa", "mista"],
    # versione_ufficiale: valore libero (nome del file candidato ufficiale)
}

LIMITE_CITAZIONE = 300
SEZIONE_INTERO = "intero documento"

ESITI = ("confermata", "corretta", "caso_nuovo")

MOTIVI_SCARTO_LABEL = {
    "senza_evidenza": "Senza evidenza (posizione o citazione mancante)",
    "campo_non_previsto": "Campo non previsto dal contratto",
    "valore_fuori_tassonomia": "Valore fuori tassonomia",
    "file_mancante": "File di riferimento mancante",
    "confidenza_non_valida": "Confidenza non valida",
    "proposta_non_valida": "Proposta malformata",
}

FASCE_CONFIDENZA = [("0-0.5", 0.0, 0.5), ("0.5-0.7", 0.5, 0.7),
                    ("0.7-0.9", 0.7, 0.9), ("0.9-1", 0.9, 1.0001)]

AVVERTENZA_SCANNER = ("Possibile svista dello scanner: riportare il caso "
                      "nel dizionario dei pattern")


def _adesso():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")


# ---------------------------------------------------------------------------
# Perimetro condivisibile
# ---------------------------------------------------------------------------

def perimetro_scansione(conn, scan):
    """Costruisce il perimetro condivisibile della scansione: i file
    Condivisibili dal triage e, separatamente, gli esclusi con la loro
    qualifica (Riservato, Da valutare, oppure Non analizzato)."""
    sid = scan["id"]
    condivisibili = db.elenco_condivisibili(conn, sid)
    triage = {r["file"]: r["qualifica"] for r in conn.execute(
        "SELECT file, qualifica FROM triage_file WHERE scansione_id = ?",
        (sid,))}
    visti = set(condivisibili)
    esclusi = []
    for r in conn.execute(
            "SELECT file FROM file_analizzati WHERE scansione_id = ? "
            "ORDER BY file", (sid,)):
        f = r["file"]
        if f in visti:
            continue
        visti.add(f)
        esclusi.append({"percorso": f,
                        "qualifica": triage.get(f, "Da valutare")})
    for f in sorted(triage):
        if f not in visti:
            visti.add(f)
            esclusi.append({"percorso": f, "qualifica": triage[f]})
    for r in conn.execute(
            "SELECT file FROM non_analizzati WHERE scansione_id = ? "
            "ORDER BY file", (sid,)):
        if r["file"] not in visti:
            visti.add(r["file"])
            esclusi.append({"percorso": r["file"],
                            "qualifica": "Non analizzato"})
    return {
        "formato": FORMATO_PERIMETRO,
        "scansione_id": sid,
        "radice": scan["radice"],
        "data_export": datetime.datetime.now().isoformat(timespec="seconds"),
        "file_condivisibili": condivisibili,
        "file_esclusi": esclusi,
    }


# ---------------------------------------------------------------------------
# Import severo delle bozze
# ---------------------------------------------------------------------------

def _valida_proposta(p):
    """Controlli severi su una proposta. Restituisce (proposta_pulita,
    motivo_scarto): se il motivo non e' None la proposta viene scartata."""
    if not isinstance(p, dict):
        return None, "proposta_non_valida"
    file_ = str(p.get("file") or "").strip()
    if not file_:
        return None, "file_mancante"
    campo = p.get("campo")
    if campo not in CAMPI:
        return None, "campo_non_previsto"
    valore = str(p.get("valore_proposto") or "").strip()
    if campo in TASSONOMIE:
        if valore not in TASSONOMIE[campo]:
            return None, "valore_fuori_tassonomia"
    elif not valore:
        # versione_ufficiale: valore libero ma obbligatorio
        return None, "valore_fuori_tassonomia"
    evidenza = p.get("evidenza")
    if not isinstance(evidenza, dict):
        return None, "senza_evidenza"
    posizione = str(evidenza.get("posizione") or "").strip()
    citazione = str(evidenza.get("citazione") or "").strip()
    if not posizione or not citazione:
        return None, "senza_evidenza"
    try:
        confidenza = float(p.get("confidenza"))
    except (TypeError, ValueError):
        return None, "confidenza_non_valida"
    if confidenza < 0 or confidenza > 1:
        return None, "confidenza_non_valida"
    troncata = 0
    if len(citazione) > LIMITE_CITAZIONE:
        citazione = citazione[:LIMITE_CITAZIONE]
        troncata = 1
    sezione = str(p.get("sezione") or "").strip() or SEZIONE_INTERO
    return {"file": file_, "sezione": sezione, "campo": campo,
            "valore_proposto": valore, "confidenza": confidenza,
            "posizione": posizione, "citazione": citazione,
            "troncata": troncata}, None


def importa_bozza(conn, nome_file, dati):
    """Importa un file bozza wikify-bozza/1.0 creando un lotto.

    Restituisce (lotto_id, riepilogo) se il file viene accettato,
    (None, messaggio_di_rifiuto) se il file va rifiutato per intero
    (formato sconosciuto o struttura non valida)."""
    if not isinstance(dati, dict):
        return None, "contenuto non valido: atteso un oggetto JSON"
    formato = dati.get("formato")
    if formato != FORMATO_BOZZA:
        return None, ("formato sconosciuto (%r): questa versione dell'app "
                      "importa solo %s" % (formato, FORMATO_BOZZA))
    proposte = dati.get("proposte")
    if not isinstance(proposte, list):
        return None, "elenco proposte assente o non valido"
    cartella = str(dati.get("cartella_progetto") or "").strip()
    chiave = dati.get("chiave_entita")
    chiave = str(chiave).strip() if chiave else None
    note_agente = dati.get("note_agente")
    if not isinstance(note_agente, list):
        note_agente = []

    accettate, scarti, n_troncate = [], [], 0
    for indice, p in enumerate(proposte, start=1):
        pulita, motivo = _valida_proposta(p)
        if motivo is not None:
            riferimento = ""
            if isinstance(p, dict):
                riferimento = "%s / %s" % (p.get("file") or "?",
                                           p.get("campo") or "?")
            scarti.append({"indice": indice, "riferimento": riferimento,
                           "motivo": motivo})
            continue
        n_troncate += pulita["troncata"]
        accettate.append(pulita)

    conteggi = {}
    for s in scarti:
        conteggi[s["motivo"]] = conteggi.get(s["motivo"], 0) + 1
    dettaglio = {"conteggi": conteggi, "dettagli": scarti,
                 "n_troncate": n_troncate}
    cur = conn.execute(
        "INSERT INTO lotti_validazione (data_import, nome_file_origine, "
        "formato, cartella_progetto, chiave_entita, n_accettate, n_scartate, "
        "n_troncate, dettaglio_scarti_json, note_agente_json, stato) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'importato')",
        (_adesso(), nome_file, formato, cartella, chiave, len(accettate),
         len(scarti), n_troncate, json.dumps(dettaglio),
         json.dumps(note_agente)))
    lotto_id = cur.lastrowid
    for a in accettate:
        conn.execute(
            "INSERT INTO proposte (lotto_id, cartella_progetto, "
            "chiave_entita, file, sezione, campo, valore_proposto, "
            "confidenza, evidenza_posizione, evidenza_citazione, "
            "citazione_troncata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (lotto_id, cartella, chiave, a["file"], a["sezione"], a["campo"],
             a["valore_proposto"], a["confidenza"], a["posizione"],
             a["citazione"], a["troncata"]))
    conn.commit()
    riepilogo = {"lotto_id": lotto_id, "n_accettate": len(accettate),
                 "n_scartate": len(scarti), "n_troncate": n_troncate,
                 "conteggi": conteggi}
    return lotto_id, riepilogo


def aggiorna_stato_lotto(conn, lotto_id):
    """Allinea lo stato del lotto all'avanzamento della validazione."""
    riga = conn.execute(
        "SELECT COUNT(*) AS tot, "
        "SUM(CASE WHEN v.id IS NOT NULL THEN 1 ELSE 0 END) AS fatte "
        "FROM proposte p LEFT JOIN validazioni v ON v.proposta_id = p.id "
        "WHERE p.lotto_id = ?", (lotto_id,)).fetchone()
    tot, fatte = riga["tot"], riga["fatte"] or 0
    if tot and fatte >= tot:
        stato = "completato"
    elif fatte > 0:
        stato = "in validazione"
    else:
        stato = "importato"
    conn.execute("UPDATE lotti_validazione SET stato = ? WHERE id = ?",
                 (stato, lotto_id))
    conn.commit()
    return stato


# ---------------------------------------------------------------------------
# Coda di revisione
# ---------------------------------------------------------------------------

def cartelle_in_coda(conn):
    """Riepilogo per cartella progetto: totali, da fare e confidenza minima
    delle proposte ancora da validare (i dubbi in cima)."""
    return conn.execute(
        "SELECT p.cartella_progetto, COUNT(*) AS n_totali, "
        "SUM(CASE WHEN v.id IS NULL THEN 1 ELSE 0 END) AS n_da_fare, "
        "MIN(CASE WHEN v.id IS NULL THEN p.confidenza END) AS conf_minima "
        "FROM proposte p LEFT JOIN validazioni v ON v.proposta_id = p.id "
        "GROUP BY p.cartella_progetto "
        "ORDER BY conf_minima IS NULL, conf_minima, p.cartella_progetto"
    ).fetchall()


def proposte_cartella(conn, cartella):
    """Le proposte della cartella con l'eventuale esito, ordinate per
    confidenza crescente (prima i dubbi)."""
    return conn.execute(
        "SELECT p.*, v.esito, v.valore_corretto, v.nota AS nota_validazione, "
        "v.validatore, v.data AS data_validazione, v.secondi_impiegati "
        "FROM proposte p LEFT JOIN validazioni v ON v.proposta_id = p.id "
        "WHERE p.cartella_progetto = ? "
        "ORDER BY p.confidenza ASC, p.id ASC", (cartella,)).fetchall()


def salva_validazione(conn, proposta, esito, valore_corretto, nota,
                      validatore, secondi):
    """Registra (o aggiorna) l'esito di una proposta. Restituisce True se
    la proposta confermata merita l'avvertenza di retroazione scanner."""
    conn.execute(
        "INSERT INTO validazioni (proposta_id, esito, valore_corretto, nota, "
        "validatore, data, secondi_impiegati) VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(proposta_id) DO UPDATE SET esito = excluded.esito, "
        "valore_corretto = excluded.valore_corretto, nota = excluded.nota, "
        "validatore = excluded.validatore, data = excluded.data, "
        "secondi_impiegati = excluded.secondi_impiegati",
        (proposta["id"], esito, valore_corretto, nota, validatore,
         _adesso(), secondi))
    conn.commit()
    aggiorna_stato_lotto(conn, proposta["lotto_id"])
    return avvertenza_scanner(proposta["campo"], proposta["valore_proposto"],
                              esito)


def avvertenza_scanner(campo, valore_proposto, esito):
    """Vera se la conferma segnala una possibile svista del Metodo A:
    proposta riservato o misto su materiale gia' qualificato condivisibile."""
    return (campo == "riservatezza" and esito == "confermata"
            and valore_proposto in ("riservato", "misto"))


# ---------------------------------------------------------------------------
# Estratto del documento con evidenza
# ---------------------------------------------------------------------------

def percorso_documento(radice, cartella, file_rel):
    """Percorso assoluto del documento citato dalla bozza. Il file e'
    relativo alla cartella progetto (contratto) ma si tollera anche il
    percorso relativo alla radice. Nessuna uscita dalla radice."""
    if not radice or not os.path.isdir(radice):
        return None
    candidati = []
    if cartella:
        candidati.append(os.path.join(radice, cartella, file_rel))
    candidati.append(os.path.join(radice, file_rel))
    base = os.path.realpath(radice)
    for c in candidati:
        reale = os.path.realpath(c)
        if reale.startswith(base + os.sep) and os.path.isfile(reale):
            return reale
    return None


def _normalizza_posizione(testo):
    return " ".join((testo or "").lower().split())


def estratto_documento(radice, cartella, file_rel, posizione, contesto=3):
    """Estrae dal documento la finestra di unita' attorno alla posizione
    indicata dall'evidenza (via core/estrazione.py).

    Restituisce un dizionario {"unita": [(pos, testo, e_match), ...]}
    oppure None se la posizione non e' ricostruibile (file assente, formato
    non estraibile o posizione non trovata): in tal caso la vista mostra la
    sola citazione con l'avviso "posizione non verificabile"."""
    percorso = percorso_documento(radice, cartella, file_rel)
    if percorso is None:
        return None
    try:
        unita = estrazione.estrai(percorso)
    except Exception:
        # File non estraibile (formato legacy, archivio danneggiato...):
        # la vista ricade sulla citazione con avviso.
        return None
    if not unita:
        return None
    voluta = _normalizza_posizione(posizione)
    indice = None
    for i, (pos, _testo) in enumerate(unita):
        if _normalizza_posizione(pos) == voluta:
            indice = i
            break
    if indice is None:
        return None
    inizio = max(0, indice - contesto)
    fine = min(len(unita), indice + contesto + 1)
    finestra = [(pos, testo, i == indice)
                for i, (pos, testo) in enumerate(unita)][inizio:fine]
    return {"unita": finestra, "n_totali": len(unita)}


# ---------------------------------------------------------------------------
# Metriche
# ---------------------------------------------------------------------------

def _percentuale(parte, totale):
    return round(100.0 * parte / totale, 1) if totale else None


def metriche(conn, lotto_id=None, sessione_id=None):
    """Metriche calcolate dalle validazioni (assessment paragrafo 3.4):
    accuratezza per campo, riservatezza puri contro misti, correlazione
    confidenza/esito per fasce, tempi mediani, casi nuovi.

    Filtrabili per lotto (lotto_id) o per sessione di analisi
    (sessione_id, tramite il collegamento lotti_validazione.sessione_id):
    i due filtri sono alternativi."""
    sql = ("SELECT p.*, v.esito, v.valore_corretto, v.nota AS nota_val, "
           "v.validatore, v.data AS data_val, v.secondi_impiegati "
           "FROM proposte p JOIN validazioni v ON v.proposta_id = p.id")
    condizioni = []
    valori = []
    if sessione_id is not None:
        sql += (" JOIN lotti_validazione l ON l.id = p.lotto_id")
        condizioni.append("l.sessione_id = ?")
        valori.append(sessione_id)
    if lotto_id is not None:
        condizioni.append("p.lotto_id = ?")
        valori.append(lotto_id)
    if condizioni:
        sql += " WHERE " + " AND ".join(condizioni)
    righe = conn.execute(sql, valori).fetchall()

    per_campo = {}
    for c in CAMPI:
        gruppo = [r for r in righe if r["campo"] == c]
        conf = sum(1 for r in gruppo if r["esito"] == "confermata")
        per_campo[c] = {"n": len(gruppo), "confermate": conf,
                        "accuratezza": _percentuale(conf, len(gruppo))}

    riservatezza = {}
    for nome, filtro in (
            ("puri", lambda r: r["sezione"] == SEZIONE_INTERO),
            ("misti", lambda r: r["sezione"] != SEZIONE_INTERO)):
        gruppo = [r for r in righe if r["campo"] == "riservatezza"
                  and filtro(r)]
        conf = sum(1 for r in gruppo if r["esito"] == "confermata")
        riservatezza[nome] = {"n": len(gruppo), "confermate": conf,
                              "accuratezza": _percentuale(conf, len(gruppo))}

    fasce = []
    for etichetta, minimo, massimo in FASCE_CONFIDENZA:
        gruppo = [r for r in righe
                  if minimo <= (r["confidenza"] or 0) < massimo]
        conf = sum(1 for r in gruppo if r["esito"] == "confermata")
        fasce.append({"fascia": etichetta, "n": len(gruppo),
                      "confermate": conf,
                      "accuratezza": _percentuale(conf, len(gruppo))})

    secondi = [r["secondi_impiegati"] or 0 for r in righe]
    tempo_proposta = round(statistics.median(secondi), 1) if secondi else None
    per_cartella = {}
    for r in righe:
        per_cartella.setdefault(r["cartella_progetto"], 0)
        per_cartella[r["cartella_progetto"]] += r["secondi_impiegati"] or 0
    tempo_cartella = (round(statistics.median(per_cartella.values()), 1)
                      if per_cartella else None)

    casi_nuovi = [r for r in righe if r["esito"] == "caso_nuovo"]
    return {"n_validate": len(righe), "per_campo": per_campo,
            "riservatezza": riservatezza, "fasce": fasce,
            "tempo_mediano_proposta": tempo_proposta,
            "tempo_mediano_cartella": tempo_cartella,
            "casi_nuovi": casi_nuovi}


def correzioni_export(conn, lotto_id=None):
    """Elenco delle correzioni (esiti corretta e caso_nuovo) nel formato
    concordato per il raffinamento dei prompt dell'agente."""
    sql = ("SELECT p.*, v.esito, v.valore_corretto, v.nota AS nota_val "
           "FROM proposte p JOIN validazioni v ON v.proposta_id = p.id "
           "WHERE v.esito IN ('corretta', 'caso_nuovo')")
    valori = []
    if lotto_id is not None:
        sql += " AND p.lotto_id = ?"
        valori.append(lotto_id)
    sql += " ORDER BY p.cartella_progetto, p.file, p.id"
    out = []
    for r in conn.execute(sql, valori):
        out.append({
            "cartella_progetto": r["cartella_progetto"],
            "file": r["file"],
            "campo": r["campo"],
            "valore_proposto": r["valore_proposto"],
            "valore_corretto": r["valore_corretto"],
            "evidenza": {"posizione": r["evidenza_posizione"],
                         "citazione": r["evidenza_citazione"]},
            "nota": r["nota_val"] or "",
            "esito": r["esito"],
        })
    return out
