# -*- coding: utf-8 -*-
"""
Suite di verifica dell'applicazione Archivio Smart.

Esecuzione (la cartella dati viene creata in una posizione temporanea,
il database dell'utente non viene toccato):

    python3 tests/test_suite.py [percorso_archivio_di_prova] [db_vecchio]

- percorso_archivio_di_prova: cartella da scansionare nel test di flusso
  (facoltativa: in mancanza viene generato un archivio sintetico);
- db_vecchio: cartella dati creata con la versione precedente dell'app,
  per il test di migrazione (facoltativa).
"""

import io
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

os.environ.setdefault("ARCHIVIO_SMART_DATA", tempfile.mkdtemp(prefix="asdata_test_"))

from core import analisi as ana  # noqa: E402
from core import db  # noqa: E402
from core import manutenzione as manut  # noqa: E402

ARCHIVIO_PROVA = os.environ.get("WIKIFY_ARCHIVIO_PROVA", "")
if not ARCHIVIO_PROVA and len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
    ARCHIVIO_PROVA = sys.argv[1]
DB_VECCHIO = sys.argv[2] if len(sys.argv) > 2 else ""
sys.argv = sys.argv[:1]  # unittest non deve vedere i nostri argomenti


def usa_dati_temporanei():
    """Sposta la cartella dati su una directory temporanea nuova."""
    cartella = tempfile.mkdtemp(prefix="asdata_test_")
    db.DATA_DIR = db.Path(cartella)
    db.DB_PATH = db.DATA_DIR / "archivio_smart.db"
    return cartella


def crea_archivio_sintetico():
    """Archivio di prova con casi limite (caratteri di controllo, formule...)."""
    radice = tempfile.mkdtemp(prefix="arch_test_")
    with open(os.path.join(radice, "documento.txt"), "w", encoding="utf-8") as f:
        f.write("promemoria \x01\x02 riservato interno \x1f con password: alfa123\n")
        f.write("=SOMMA(A1:A2) riga che sembra formula, password: beta456\n")
        f.write("accenti però è già così \"virgolette\" e l'apostrofo, riservato\n")
        f.write("contesto con controllo\x0bverticale riservato qui\n")
    with open(os.path.join(radice, "pulito.txt"), "w", encoding="utf-8") as f:
        f.write("testo ordinario senza alcun pattern sensibile\n")
    # Sottocartella: i test di inventario e dashboard richiedono almeno
    # una cartella di primo livello (KPI per cartella progetto).
    sotto = os.path.join(radice, "P-001_progetto_sintetico")
    os.makedirs(sotto, exist_ok=True)
    with open(os.path.join(sotto, "specifica.txt"), "w", encoding="utf-8") as f:
        f.write("specifica tecnica sintetica, setpoint 48.5\n")
    return radice


def esegui_scansione_sincrona(radice, etichetta="test"):
    """Avvia una scansione e attende il completamento del thread."""
    from core import scansione as motore
    scan_id = motore.avvia_scansione(radice, etichetta, 80)
    for _ in range(400):
        conn = db.get_connection()
        stato = conn.execute("SELECT stato FROM scansioni WHERE id = ?",
                             (scan_id,)).fetchone()[0]
        conn.close()
        if stato != "in corso":
            return scan_id, stato
        time.sleep(0.1)
    return scan_id, "timeout"


class TestSanificaCella(unittest.TestCase):
    """Intervento 1: sanificazione dei valori di cella per openpyxl."""

    def setUp(self):
        from core.report import sanifica_cella
        self.s = sanifica_cella

    def test_none(self):
        self.assertEqual(self.s(None), "")

    def test_numeri_invariati(self):
        self.assertEqual(self.s(42), 42)
        self.assertEqual(self.s(3.5), 3.5)

    def test_caratteri_controllo_rimossi(self):
        pulito = self.s("a\x00b\x01c\x1fd\x7fe")
        self.assertNotRegex(pulito, r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
        self.assertIn("a", pulito)
        self.assertIn("e", pulito)

    def test_tab_e_accapo_conservati(self):
        self.assertEqual(self.s("a\tb\nc"), "a\tb\nc")

    def test_accenti_apostrofi_virgolette(self):
        testo = "però è già così \"virgolette\" l'apostrofo"
        self.assertEqual(self.s(testo), testo)

    def test_formula_neutralizzata(self):
        self.assertTrue(self.s("=SOMMA(A1:A2)").startswith("'="))

    def test_troncamento_32767(self):
        lungo = "x" * 40000
        esito = self.s(lungo)
        self.assertLessEqual(len(esito), 32767)
        self.assertTrue(esito.endswith("[troncato]"))

    def test_surrogati_rimossi(self):
        esito = self.s("ok" + "\ud800" + "fine")
        self.assertNotIn("\ud800", esito)


class TestExportXLSX(unittest.TestCase):
    """Intervento 1: export XLSX in tutti i casi limite."""

    def setUp(self):
        usa_dati_temporanei()
        db.init_db()

    def _scan_fittizia(self, conn):
        cur = conn.execute(
            "INSERT INTO scansioni (data, radice, etichetta, n_regole, contesto, stato, durata) "
            "VALUES ('01/07/2026 10:00', '/tmp/x', 'prova', 5, 80, 'completata', 1.0)")
        return cur.lastrowid

    def _esporta(self, conn, sid):
        from core import report
        scan = conn.execute("SELECT * FROM scansioni WHERE id = ?", (sid,)).fetchone()
        wb = report.genera_report(conn, scan)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        import openpyxl
        return openpyxl.load_workbook(buf)

    def test_export_zero_segnalazioni(self):
        conn = db.get_connection()
        sid = self._scan_fittizia(conn)
        wb = self._esporta(conn, sid)
        conn.close()
        self.assertIn("Registro segregazione", wb.sheetnames)
        self.assertEqual(wb["Segnalazioni"].max_row, 1)

    def test_export_caratteri_difficili(self):
        conn = db.get_connection()
        sid = self._scan_fittizia(conn)
        casi = [
            ("controllo.txt", "riga 1", "R1", "test", "alta",
             "password: a", "prima \x00\x01\x1f password: a \x7f dopo"),
            ("formula.txt", "riga 2", "R2", "test", "media",
             "=SOMMA(A1)", "=SOMMA(A1) contesto con formula apparente"),
            ("accenti.txt", "riga 3", "R3", "test", "bassa",
             "però", "già così \"virgolette\" e l'apostrofo però"),
            ("lungo.txt", "riga 4", "R4", "test", "alta",
             "chiave", "x" * 40000),
            ("nullo.txt", None, "R5", None, "media", None, None),
        ]
        for file_, pos, reg, cat, sev, match, ctx in casi:
            conn.execute(
                "INSERT INTO segnalazioni (scansione_id, file, posizione, regola_id, "
                "categoria, severita, testo_match, contesto) VALUES (?,?,?,?,?,?,?,?)",
                (sid, file_, pos, reg, cat, sev, match, ctx))
        conn.execute(
            "INSERT INTO file_analizzati (scansione_id, file, formato, unita_testo, "
            "n_alta, n_media, n_bassa, totale) VALUES (?,?,?,?,?,?,?,?)",
            (sid, "controllo.txt", ".txt", 4, 2, 2, 1, 5))
        conn.commit()
        wb = self._esporta(conn, sid)
        ws = wb["Segnalazioni"]
        valori = [[c.value for c in r] for r in ws.iter_rows(min_row=2)]
        conn.close()
        self.assertEqual(len(valori), 5)
        for riga in valori:
            for v in riga:
                if isinstance(v, str):
                    self.assertLessEqual(len(v), 32767)
                    self.assertNotRegex(v, r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
        # La formula apparente non deve essere una formula
        for c in ws["F"]:
            if isinstance(c.value, str) and "SOMMA" in c.value:
                self.assertNotEqual(c.data_type, "f")

    def test_export_triage_parziale(self):
        conn = db.get_connection()
        sid = self._scan_fittizia(conn)
        for nome in ("a.txt", "b.txt"):
            conn.execute(
                "INSERT INTO segnalazioni (scansione_id, file, posizione, regola_id, "
                "categoria, severita, testo_match, contesto) VALUES (?,?,?,?,?,?,?,?)",
                (sid, nome, "riga 1", "R1", "test", "alta", "m", "ctx"))
            conn.execute(
                "INSERT INTO file_analizzati (scansione_id, file, formato, unita_testo, "
                "n_alta, n_media, n_bassa, totale) VALUES (?,?,?,1,1,0,0,1)",
                (sid, nome, ".txt"))
        conn.execute(
            "INSERT INTO triage_file (scansione_id, file, qualifica, motivazione, "
            "vincolo, validatore, data, verificato) VALUES (?,?,?,?,?,?,?,1)",
            (sid, "a.txt", "Riservato", "mot", "NDA", "Tester", "01/07/2026 10:00"))
        conn.commit()
        wb = self._esporta(conn, sid)
        conn.close()
        ws = wb["Registro segregazione"]
        righe = {r[0].value: tuple(c.value for c in r)
                 for r in ws.iter_rows(min_row=2)}
        self.assertIn("a.txt", righe)
        self.assertIn("b.txt", righe)
        self.assertEqual(righe["a.txt"][5], "Riservato")
        self.assertEqual(righe["a.txt"][10], "Verificato")
        self.assertEqual(righe["b.txt"][5], "Da valutare")
        self.assertEqual(righe["b.txt"][10], "Da fare")


class TestMigrazione(unittest.TestCase):
    """Retrocompatibilita': un db della versione precedente migra senza perdite."""

    def _prepara_db_vecchio(self, cartella):
        """Ricrea un database con il solo schema V1 e dati minimi."""
        percorso = os.path.join(cartella, "archivio_smart.db")
        conn = sqlite3.connect(percorso)
        conn.executescript(db.MIGRAZIONI[0])
        conn.execute("PRAGMA user_version = 1")
        # Con almeno una regola presente il seed del dizionario non scatta
        # e il confronto prima/dopo resta significativo.
        conn.execute("INSERT INTO regole (codice, categoria, pattern) "
                     "VALUES ('R1', 'test', 'riservato')")
        conn.execute("INSERT INTO scansioni (data, radice, stato) "
                     "VALUES ('01/06/2026 09:00', '/vecchio', 'completata')")
        conn.execute("INSERT INTO segnalazioni (scansione_id, file, regola_id, severita) "
                     "VALUES (1, 'doc.txt', 'R1', 'alta')")
        conn.execute("INSERT INTO triage (scansione_id, file, regola_id, qualifica, "
                     "validatore) VALUES (1, 'doc.txt', 'R1', 'Riservato', 'Carlo')")
        conn.commit()
        conn.close()

    def _prepara_db_v2(self, cartella):
        """Ricrea un database della versione attuale (schema V2) con dati
        reali: scansione, file analizzati, triage per file e utenti."""
        percorso = os.path.join(cartella, "archivio_smart.db")
        conn = sqlite3.connect(percorso)
        conn.executescript(db.MIGRAZIONI[0])
        conn.executescript(db.MIGRAZIONI[1])
        conn.execute("PRAGMA user_version = 2")
        conn.execute("INSERT INTO regole (codice, categoria, pattern) "
                     "VALUES ('R1', 'test', 'riservato')")
        conn.execute("INSERT INTO scansioni (data, radice, stato) "
                     "VALUES ('01/06/2026 09:00', '/vecchio', 'completata')")
        conn.execute("INSERT INTO segnalazioni (scansione_id, file, regola_id, severita) "
                     "VALUES (1, 'doc.txt', 'R1', 'alta')")
        conn.execute("INSERT INTO file_analizzati (scansione_id, file, formato, totale) "
                     "VALUES (1, 'doc.txt', '.txt', 1)")
        conn.execute("INSERT INTO triage_file (scansione_id, file, qualifica, "
                     "validatore, verificato) VALUES (1, 'doc.txt', 'Riservato', "
                     "'Carlo', 1)")
        conn.execute("INSERT INTO utenti (nome, pin, attivo, data_creazione) "
                     "VALUES ('Carlo', 'aa$bb', 1, '01/06/2026 09:00')")
        conn.commit()
        conn.close()

    def _prepara_db_v3(self, cartella):
        """Ricrea un database della versione attuale (schema V3) con dati
        reali: scansione, triage, utenti, impostazioni e inventario."""
        percorso = os.path.join(cartella, "archivio_smart.db")
        conn = sqlite3.connect(percorso)
        conn.executescript(db.MIGRAZIONI[0])
        conn.executescript(db.MIGRAZIONI[1])
        conn.executescript(db.MIGRAZIONI[2])
        conn.execute("PRAGMA user_version = 3")
        conn.execute("INSERT INTO regole (codice, categoria, pattern) "
                     "VALUES ('R1', 'test', 'riservato')")
        conn.execute("INSERT INTO scansioni (data, radice, stato) "
                     "VALUES ('01/06/2026 09:00', '/vecchio', 'completata')")
        conn.execute("INSERT INTO segnalazioni (scansione_id, file, regola_id, severita) "
                     "VALUES (1, 'doc.txt', 'R1', 'alta')")
        conn.execute("INSERT INTO triage_file (scansione_id, file, qualifica, "
                     "validatore, verificato) VALUES (1, 'doc.txt', 'Riservato', "
                     "'Carlo', 1)")
        conn.execute("INSERT INTO utenti (nome, pin, attivo, data_creazione) "
                     "VALUES ('Carlo', 'aa$bb', 1, '01/06/2026 09:00')")
        conn.execute("INSERT INTO impostazioni (chiave, valore) "
                     "VALUES ('radice_archivio', '/vecchio')")
        conn.execute("INSERT INTO inventario_file (percorso_rel, "
                     "cartella_progetto, estensione, stato) "
                     "VALUES ('P-001/doc.txt', 'P-001', '.txt', 'presente')")
        conn.execute("INSERT INTO inventario_esecuzioni (data, tipo, n_totale) "
                     "VALUES ('01/06/2026 09:00', 'completo', 1)")
        conn.commit()
        conn.close()

    def _prepara_db_v4(self, cartella):
        """Ricrea un database della versione attuale (schema V4) con dati
        reali: scansione, triage, utenti, inventario e catalogo."""
        percorso = os.path.join(cartella, "archivio_smart.db")
        conn = sqlite3.connect(percorso)
        for schema in db.MIGRAZIONI[:4]:
            conn.executescript(schema)
        conn.execute("PRAGMA user_version = 4")
        conn.execute("INSERT INTO regole (codice, categoria, pattern) "
                     "VALUES ('R1', 'test', 'riservato')")
        conn.execute("INSERT INTO scansioni (data, radice, stato) "
                     "VALUES ('01/06/2026 09:00', '/vecchio', 'completata')")
        conn.execute("INSERT INTO segnalazioni (scansione_id, file, regola_id, severita) "
                     "VALUES (1, 'doc.txt', 'R1', 'alta')")
        conn.execute("INSERT INTO triage_file (scansione_id, file, qualifica, "
                     "validatore, verificato) VALUES (1, 'doc.txt', 'Riservato', "
                     "'Carlo', 1)")
        conn.execute("INSERT INTO utenti (nome, pin, attivo, data_creazione) "
                     "VALUES ('Carlo', 'aa$bb', 1, '01/06/2026 09:00')")
        conn.execute("INSERT INTO impostazioni (chiave, valore) "
                     "VALUES ('radice_archivio', '/vecchio')")
        conn.execute("INSERT INTO inventario_file (percorso_rel, "
                     "cartella_progetto, estensione, stato) "
                     "VALUES ('P-001/doc.txt', 'P-001', '.txt', 'presente')")
        conn.execute("INSERT INTO tipi_entita (nome, criterio_json, "
                     "data_creazione, stato) VALUES ('Progetto', '{}', "
                     "'01/06/2026 09:00', 'attivo')")
        conn.execute("INSERT INTO entita (tipo_id, chiave, cartella_origine, "
                     "stato) VALUES (1, 'P-001', 'P-001', 'attiva')")
        conn.execute("INSERT INTO importazioni (data, nome_file, "
                     "tipo_entita_id, utente, stato) VALUES "
                     "('01/06/2026 09:00', 'dati.csv', 1, 'Carlo', 'confermata')")
        conn.execute("INSERT INTO attributi_entita (entita_id, "
                     "nome_attributo, valore, importazione_id) "
                     "VALUES (1, 'articolo', 'ART-1', 1)")
        conn.execute("INSERT INTO anomalie_import (importazione_id, tipo, "
                     "riferimento) VALUES (1, 'chiave_senza_entita', 'P-9')")
        conn.commit()
        conn.close()

    TABELLE_NUOVE_V3 = ("impostazioni", "inventario_file", "inventario_esecuzioni")
    TABELLE_NUOVE_V4 = ("tipi_entita", "entita", "importazioni",
                        "attributi_entita", "anomalie_import")
    TABELLE_NUOVE_V5 = ("lotti_validazione", "proposte", "validazioni",
                        "note_conoscenza_tacita")
    TABELLE_NUOVE_V6 = ("sessioni_analisi", "sessioni_analisi_letture")
    TABELLE_NUOVE_V7 = ("documenti", "regole_tipologia")

    def test_migrazione_da_v1(self):
        cartella = usa_dati_temporanei()
        self._prepara_db_vecchio(cartella)
        conn = db.get_connection()
        prima = {t: conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                 for t in ("regole", "scansioni", "segnalazioni", "triage")}
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
        conn.close()

        db.init_db()  # applica le migrazioni V2, V3, V4, V5, V6 e V7

        conn = db.get_connection()
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 7)
        tabelle = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("utenti", tabelle)
        self.assertIn("triage_file", tabelle)
        self.assertIn("triage", tabelle)  # la tabella storica resta
        for t in (self.TABELLE_NUOVE_V3 + self.TABELLE_NUOVE_V4
                 + self.TABELLE_NUOVE_V5 + self.TABELLE_NUOVE_V6
                 + self.TABELLE_NUOVE_V7):
            self.assertIn(t, tabelle)
        dopo = {t: conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                for t in ("regole", "scansioni", "segnalazioni", "triage")}
        self.assertEqual(prima, dopo)  # nessuna perdita di dati
        conn.close()

    def test_migrazione_da_v2_con_dati_reali(self):
        """Db della versione attuale (utenti, scansione, triage per file):
        la migrazione V3 e' additiva e non tocca nulla."""
        cartella = usa_dati_temporanei()
        if DB_VECCHIO and os.path.isdir(DB_VECCHIO):
            # Copia del database generato con la versione precedente dell'app
            for nome in os.listdir(DB_VECCHIO):
                shutil.copy2(os.path.join(DB_VECCHIO, nome),
                             os.path.join(cartella, nome))
        else:
            self._prepara_db_v2(cartella)
        conn = db.get_connection()
        controllate = ("regole", "scansioni", "segnalazioni", "file_analizzati",
                       "triage_file", "utenti")
        prima = {t: conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                 for t in controllate}
        utenti_prima = [tuple(r) for r in conn.execute(
            "SELECT nome, pin FROM utenti ORDER BY id")]
        triage_prima = [tuple(r) for r in conn.execute(
            "SELECT file, qualifica, verificato FROM triage_file ORDER BY id")]
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)
        conn.close()

        db.init_db()  # applica le migrazioni V3, V4, V5, V6 e V7

        conn = db.get_connection()
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 7)
        tabelle = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for t in (self.TABELLE_NUOVE_V3 + self.TABELLE_NUOVE_V4
                 + self.TABELLE_NUOVE_V5 + self.TABELLE_NUOVE_V6
                 + self.TABELLE_NUOVE_V7):
            self.assertIn(t, tabelle)
        dopo = {t: conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                for t in controllate}
        self.assertEqual(prima, dopo)
        self.assertEqual(
            utenti_prima,
            [tuple(r) for r in conn.execute(
                "SELECT nome, pin FROM utenti ORDER BY id")])
        self.assertEqual(
            triage_prima,
            [tuple(r) for r in conn.execute(
                "SELECT file, qualifica, verificato FROM triage_file ORDER BY id")])
        # Le tabelle nuove partono vuote
        for t in (self.TABELLE_NUOVE_V3 + self.TABELLE_NUOVE_V4
                 + self.TABELLE_NUOVE_V5 + self.TABELLE_NUOVE_V6
                 + self.TABELLE_NUOVE_V7):
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0], 0)
        conn.close()

    def test_migrazione_da_v3_con_dati_reali(self):
        """Db della versione attuale (schema V3, con inventario e
        impostazioni): la migrazione V4 e' additiva e non tocca nulla."""
        cartella = usa_dati_temporanei()
        self._prepara_db_v3(cartella)
        controllate = ("regole", "scansioni", "segnalazioni", "triage_file",
                       "utenti", "impostazioni", "inventario_file",
                       "inventario_esecuzioni")
        conn = db.get_connection()
        prima = {t: conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                 for t in controllate}
        inventario_prima = [tuple(r) for r in conn.execute(
            "SELECT percorso_rel, cartella_progetto, stato "
            "FROM inventario_file ORDER BY id")]
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 3)
        conn.close()

        db.init_db()  # applica le migrazioni V4, V5, V6 e V7

        conn = db.get_connection()
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 7)
        tabelle = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for t in (self.TABELLE_NUOVE_V4 + self.TABELLE_NUOVE_V5
                 + self.TABELLE_NUOVE_V6 + self.TABELLE_NUOVE_V7):
            self.assertIn(t, tabelle)
        dopo = {t: conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                for t in controllate}
        self.assertEqual(prima, dopo)  # nessuna perdita di dati
        self.assertEqual(
            inventario_prima,
            [tuple(r) for r in conn.execute(
                "SELECT percorso_rel, cartella_progetto, stato "
                "FROM inventario_file ORDER BY id")])
        for t in (self.TABELLE_NUOVE_V4 + self.TABELLE_NUOVE_V5
                 + self.TABELLE_NUOVE_V6 + self.TABELLE_NUOVE_V7):
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0], 0)
        conn.close()


    def test_migrazione_da_v4_con_dati_reali(self):
        """Db della versione attuale (schema V4, con catalogo popolato):
        la migrazione V5 e' additiva e non tocca nulla."""
        cartella = usa_dati_temporanei()
        self._prepara_db_v4(cartella)
        controllate = ("regole", "scansioni", "segnalazioni", "triage_file",
                       "utenti", "impostazioni", "inventario_file",
                       "tipi_entita", "entita", "importazioni",
                       "attributi_entita", "anomalie_import")
        conn = db.get_connection()
        prima = {t: conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                 for t in controllate}
        catalogo_prima = [tuple(r) for r in conn.execute(
            "SELECT chiave, cartella_origine, stato FROM entita ORDER BY id")]
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 4)
        conn.close()

        db.init_db()  # applica le migrazioni V5, V6 e V7

        conn = db.get_connection()
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 7)
        tabelle = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for t in self.TABELLE_NUOVE_V5 + self.TABELLE_NUOVE_V6 + self.TABELLE_NUOVE_V7:
            self.assertIn(t, tabelle)
        dopo = {t: conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                for t in controllate}
        self.assertEqual(prima, dopo)  # nessuna perdita di dati
        self.assertEqual(
            catalogo_prima,
            [tuple(r) for r in conn.execute(
                "SELECT chiave, cartella_origine, stato FROM entita "
                "ORDER BY id")])
        for t in self.TABELLE_NUOVE_V5 + self.TABELLE_NUOVE_V6 + self.TABELLE_NUOVE_V7:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0], 0)
        conn.close()


class TestFlussoCompleto(unittest.TestCase):
    """Interventi 2-5: login, scansione, consultazione raggruppata, triage, coda."""

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.archivio = (ARCHIVIO_PROVA if ARCHIVIO_PROVA and os.path.isdir(ARCHIVIO_PROVA)
                        else crea_archivio_sintetico())

    def test_01_senza_utenti_redirect_benvenuto(self):
        r = self.client.get("/", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/utenti/benvenuto", r.headers["Location"])
        r = self.client.get("/utenti/benvenuto")
        self.assertEqual(r.status_code, 200)
        self.assertIn("primo", r.get_data(as_text=True).lower())

    def test_02_creazione_primo_utente(self):
        r = self.client.post("/utenti/benvenuto/crea",
                             data={"nome": "Carlo Verdini", "pin": "1234"},
                             follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Carlo Verdini", r.get_data(as_text=True))
        # PIN non in chiaro sul database
        conn = db.get_connection()
        riga = conn.execute("SELECT pin FROM utenti").fetchone()
        conn.close()
        self.assertNotIn("1234", riga["pin"].split("$")[0])
        self.assertIn("$", riga["pin"])
        self.client.get("/utenti/uscita")

    def test_03_login_pin_errato_rifiutato(self):
        r = self.client.post("/utenti/accesso",
                             data={"utente": "1", "pin": "9999"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("non corretti", r.get_data(as_text=True))
        # Le pagine operative restano protette
        r = self.client.get("/storico/", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/utenti/accesso", r.headers["Location"])

    def test_04_login_corretto(self):
        r = self.client.post("/utenti/accesso",
                             data={"utente": "1", "pin": "1234"},
                             follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn("Carlo Verdini", testo)
        self.assertIn("Esci", testo)

    def test_05_pagine_operative_200(self):
        for pagina in ("/", "/dizionario/", "/scansione/", "/storico/",
                       "/catalogo/", "/catalogo/entita",
                       "/catalogo/arricchimento", "/catalogo/tipi/nuovo",
                       "/validazione/perimetro", "/validazione/coda",
                       "/validazione/metriche",
                       "/utenti/anagrafica", "/utenti/password"):
            r = self.client.get(pagina)
            self.assertEqual(r.status_code, 200, "pagina %s" % pagina)

    def test_06_scansione_archivio(self):
        scan_id, stato = esegui_scansione_sincrona(self.archivio, "flusso di prova")
        self.assertEqual(stato, "completata")
        type(self).scan_id = scan_id
        conn = db.get_connection()
        n = conn.execute("SELECT COUNT(*) FROM segnalazioni WHERE scansione_id = ?",
                         (scan_id,)).fetchone()[0]
        conn.close()
        self.assertGreater(n, 0, "l'archivio di prova deve produrre segnalazioni")

    def test_07_consultazione_raggruppata_per_file(self):
        r = self.client.get("/storico/%d?stato=tutti" % self.scan_id)
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        # Accordion per file presenti
        self.assertIn('<details class="file-acc"', testo)
        self.assertIn("Da fare (", testo)
        self.assertIn("Verificati (", testo)
        self.assertIn("Tutti (", testo)
        # Un accordion per ciascun file con segnalazioni
        conn = db.get_connection()
        n_file = conn.execute(
            "SELECT COUNT(DISTINCT file) FROM segnalazioni WHERE scansione_id = ?",
            (self.scan_id,)).fetchone()[0]
        conn.close()
        self.assertEqual(testo.count('<details class="file-acc"'), n_file)

    def test_08_triage_con_testi_lunghi_e_particolari(self):
        conn = db.get_connection()
        file_ = conn.execute("SELECT file FROM segnalazioni WHERE scansione_id = ? "
                             "ORDER BY file LIMIT 1", (self.scan_id,)).fetchone()[0]
        conn.close()
        type(self).file_triage = file_
        motivazione = ("Motivazione estesa con accenti però è già così, "
                       "\"virgolette\", l'apostrofo e <tag>. " * 20)
        vincolo = "Vincolo NDA, uso interno; carattere = iniziale escluso. " * 10
        r = self.client.post("/storico/%d/triage" % self.scan_id,
                             data={"file": file_, "qualifica": "Riservato",
                                   "motivazione": motivazione, "vincolo": vincolo,
                                   "filtro_stato": "da_fare"},
                             follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        conn = db.get_connection()
        t = conn.execute("SELECT * FROM triage_file WHERE scansione_id = ? AND file = ?",
                         (self.scan_id, file_)).fetchone()
        conn.close()
        self.assertIsNotNone(t)
        self.assertEqual(t["qualifica"], "Riservato")
        self.assertEqual(t["motivazione"], motivazione.strip())
        self.assertEqual(t["vincolo"], vincolo.strip())
        # Validatore assegnato automaticamente dall'utente connesso, con data
        self.assertEqual(t["validatore"], "Carlo Verdini")
        self.assertTrue(t["data"])
        self.assertEqual(t["verificato"], 1)

    def test_09_coda_da_fare_e_verificati(self):
        conn = db.get_connection()
        n_file = conn.execute(
            "SELECT COUNT(DISTINCT file) FROM segnalazioni WHERE scansione_id = ?",
            (self.scan_id,)).fetchone()[0]
        conn.close()
        # Vista di default (Da fare): il file verificato non compare tra gli accordion
        r = self.client.get("/storico/%d" % self.scan_id)
        testo = r.get_data(as_text=True)
        self.assertNotIn('file-nome rompi">%s</span>' % self.file_triage, testo)
        self.assertIn("Da fare (%d)" % (n_file - 1), testo)
        self.assertIn("Verificati (1)", testo)
        self.assertIn("Tutti (%d)" % n_file, testo)
        self.assertEqual(testo.count('<details class="file-acc"'), n_file - 1)
        # Vista Verificati: compare solo il file qualificato
        r = self.client.get("/storico/%d?stato=verificati" % self.scan_id)
        testo = r.get_data(as_text=True)
        self.assertEqual(testo.count('<details class="file-acc"'), 1)
        self.assertIn(self.file_triage, testo)
        self.assertIn("Verificato: Riservato", testo)

    def test_10_riapertura_e_modifica_verificato(self):
        r = self.client.post("/storico/%d/triage" % self.scan_id,
                             data={"file": self.file_triage,
                                   "qualifica": "Condivisibile",
                                   "motivazione": "Rivalutato dopo confronto",
                                   "vincolo": "",
                                   "filtro_stato": "verificati"},
                             follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        conn = db.get_connection()
        t = conn.execute("SELECT * FROM triage_file WHERE scansione_id = ? AND file = ?",
                         (self.scan_id, self.file_triage)).fetchone()
        conn.close()
        self.assertEqual(t["qualifica"], "Condivisibile")
        self.assertEqual(t["verificato"], 1)
        self.assertEqual(t["validatore"], "Carlo Verdini")
        # "Da valutare" riporta il file in coda
        self.client.post("/storico/%d/triage" % self.scan_id,
                         data={"file": self.file_triage, "qualifica": "Da valutare",
                               "motivazione": "", "vincolo": ""})
        conn = db.get_connection()
        t = conn.execute("SELECT verificato FROM triage_file WHERE scansione_id = ? "
                         "AND file = ?", (self.scan_id, self.file_triage)).fetchone()
        conn.close()
        self.assertEqual(t["verificato"], 0)
        r = self.client.get("/storico/%d" % self.scan_id)
        self.assertIn(self.file_triage, r.get_data(as_text=True))
        # Ripristino a Riservato per i test successivi
        self.client.post("/storico/%d/triage" % self.scan_id,
                         data={"file": self.file_triage, "qualifica": "Riservato",
                               "motivazione": "definitivo", "vincolo": "NDA"})

    def test_11_avanzamento_triage_in_storico(self):
        r = self.client.get("/storico/")
        testo = r.get_data(as_text=True)
        self.assertIn("Avanzamento triage", testo)
        self.assertRegex(testo, r"1/\d+ file verificati")

    def test_12_export_xlsx_da_endpoint(self):
        r = self.client.get("/storico/%d/export.xlsx" % self.scan_id)
        self.assertEqual(r.status_code, 200)
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(r.data))
        self.assertEqual(wb.sheetnames,
                         ["Segnalazioni", "Riepilogo file", "Riepilogo categorie",
                          "Non analizzati", "Registro segregazione",
                          "Parametri scansione"])
        ws = wb["Registro segregazione"]
        colonne = [c.value for c in ws[1]]
        self.assertIn("Motivazione", colonne)
        self.assertIn("Vincolo", colonne)
        self.assertIn("Data validazione", colonne)
        trovato = False
        for riga in ws.iter_rows(min_row=2):
            if riga[0].value == self.file_triage:
                trovato = True
                self.assertEqual(riga[5].value, "Riservato")
                self.assertEqual(riga[8].value, "Carlo Verdini")
        self.assertTrue(trovato)

    def test_13_gestione_anagrafica(self):
        # Creazione di un secondo utente e PIN non valido rifiutato
        r = self.client.post("/utenti/anagrafica",
                             data={"nome": "Maria Rossi", "pin": "12"},
                             follow_redirects=True)
        self.assertIn("PIN deve essere numerico", r.get_data(as_text=True))
        r = self.client.post("/utenti/anagrafica",
                             data={"nome": "Maria Rossi", "pin": "567890"},
                             follow_redirects=True)
        self.assertIn("Utente creato", r.get_data(as_text=True))
        # L'utente connesso non puo' disattivarsi da solo
        r = self.client.post("/utenti/anagrafica/1/stato", follow_redirects=True)
        self.assertIn("Non è possibile disattivare", r.get_data(as_text=True))
        # Disattivazione del secondo utente
        conn = db.get_connection()
        uid = conn.execute("SELECT id FROM utenti WHERE nome = 'Maria Rossi'"
                           ).fetchone()[0]
        conn.close()
        r = self.client.post("/utenti/anagrafica/%d/stato" % uid,
                             follow_redirects=True)
        self.assertIn("disattivato", r.get_data(as_text=True))

    def test_14_uscita_e_protezione(self):
        r = self.client.get("/utenti/uscita", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        for pagina in ("/", "/storico/", "/scansione/", "/dizionario/",
                       "/catalogo/", "/catalogo/arricchimento",
                       "/validazione/perimetro", "/validazione/coda",
                       "/validazione/metriche",
                       "/utenti/anagrafica", "/storico/%d" % self.scan_id):
            r = self.client.get(pagina, follow_redirects=False)
            self.assertEqual(r.status_code, 302, "pagina %s" % pagina)
            self.assertIn("/utenti/accesso", r.headers["Location"])
        # Nuovo accesso per lasciare l'ambiente coerente
        self.client.post("/utenti/accesso", data={"utente": "1", "pin": "1234"})


class TestInventarioDashboard(unittest.TestCase):
    """Modulo Inventario e dashboard: impostazione cartella, inventario
    iniziale, check all'apertura, integrazione, scomparsi, da classificare."""

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})
        # Copia di lavoro dell'archivio di prova (i test aggiungono e
        # rimuovono file, l'originale non va toccato).
        origine = (ARCHIVIO_PROVA if ARCHIVIO_PROVA and os.path.isdir(ARCHIVIO_PROVA)
                   else crea_archivio_sintetico())
        cls.radice = os.path.join(tempfile.mkdtemp(prefix="arch_inv_"), "archivio")
        shutil.copytree(origine, cls.radice)

    @classmethod
    def _attesi_filesystem(cls):
        """Conteggio indipendente dei file attesi (stesse esclusioni)."""
        attesi = []
        for cartella, sub, nomi in os.walk(cls.radice):
            sub[:] = [d for d in sub if not d.startswith(".")]
            for nome in nomi:
                if nome.startswith(("~$", ".")):
                    continue
                rel = os.path.relpath(os.path.join(cartella, nome), cls.radice)
                attesi.append(rel.replace(os.sep, "/"))
        return attesi

    def _forza_prossimo_check(self):
        """Simula la riapertura dell'app: l'ultimo check risulta vecchio."""
        conn = db.get_connection()
        conn.execute("UPDATE impostazioni SET valore = ? "
                     "WHERE chiave = 'inventario_ultimo_check'",
                     (str(time.time() - 3600),))
        conn.commit()
        conn.close()

    def test_01_dashboard_senza_radice(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        # La vecchia scritta descrittiva non deve piu' comparire
        self.assertNotIn("Assessment di riservatezza dell'archivio documentale",
                         testo)
        self.assertIn("Cartella archivio", testo)
        self.assertIn("imposta-radice", testo)

    def test_02_impostazione_radice(self):
        # Percorso inesistente rifiutato
        r = self.client.post("/inventario/imposta-radice",
                             data={"radice": "/percorso/inesistente/xyz"},
                             follow_redirects=True)
        self.assertIn("Cartella non trovata", r.get_data(as_text=True))
        # Percorso valido salvato
        r = self.client.post("/inventario/imposta-radice",
                             data={"radice": self.radice},
                             follow_redirects=True)
        testo = r.get_data(as_text=True)
        self.assertIn("Cartella archivio impostata", testo)
        # Mappa vuota: la dashboard propone l'inventario iniziale
        self.assertIn("Esegui inventario iniziale", testo)
        # La pagina Nuova scansione propone il percorso precompilato
        r = self.client.get("/scansione/")
        self.assertIn('value="%s"' % self.radice, r.get_data(as_text=True))

    def test_03_inventario_iniziale_conteggi(self):
        r = self.client.post("/inventario/iniziale", follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        attesi = self._attesi_filesystem()
        conn = db.get_connection()
        righe = conn.execute(
            "SELECT percorso_rel, cartella_progetto, estensione, dimensione "
            "FROM inventario_file WHERE stato = 'presente'").fetchall()
        esecuzione = conn.execute(
            "SELECT * FROM inventario_esecuzioni ORDER BY id LIMIT 1").fetchone()
        conn.close()
        self.assertEqual(sorted(r["percorso_rel"] for r in righe), sorted(attesi))
        self.assertEqual(esecuzione["tipo"], "completo")
        self.assertEqual(esecuzione["n_totale"], len(attesi))
        # Cartella progetto = primo livello; file in radice senza cartella
        for riga in righe:
            parti = riga["percorso_rel"].split("/")
            attesa = parti[0] if len(parti) > 1 else ""
            self.assertEqual(riga["cartella_progetto"], attesa)
            self.assertEqual(riga["estensione"],
                             os.path.splitext(riga["percorso_rel"])[1].lower())
            self.assertGreaterEqual(riga["dimensione"], 0)

    def test_04_dashboard_kpi(self):
        r = self.client.get("/")
        testo = r.get_data(as_text=True)
        self.assertNotIn("Assessment di riservatezza dell'archivio documentale",
                         testo)
        attesi = self._attesi_filesystem()
        cartelle = sorted({p.split("/")[0] for p in attesi if "/" in p})
        # KPI: cartelle di primo livello, file mappati, da classificare
        self.assertIn("Cartelle nel progetto (primo livello)", testo)
        self.assertIn("File mappati nell", testo)
        self.assertIn("File da classificare", testo)
        self.assertIn('<div class="numero">%d</div>' % len(cartelle), testo)
        self.assertIn('<div class="numero">%d</div>' % len(attesi), testo)
        # Tabella per cartella con ripartizione per tipo
        self.assertIn('id="tabella-cartelle"', testo)
        for intestazione in ("docx", "xlsx", "pdf", "txt", "altro"):
            self.assertIn("<th>%s</th>" % intestazione, testo)
        for cartella in cartelle:
            self.assertIn(cartella, testo)
        # Verifica di una riga: conteggi della prima cartella progetto
        conn = db.get_connection()
        riga_txt = conn.execute(
            "SELECT COUNT(*) FROM inventario_file WHERE stato = 'presente' "
            "AND cartella_progetto = ? AND estensione = '.txt'",
            (cartelle[0],)).fetchone()[0]
        conn.close()
        attesi_txt = sum(1 for p in attesi
                         if p.split("/")[0] == cartelle[0] and "/" in p
                         and p.lower().endswith(".txt"))
        self.assertEqual(riga_txt, attesi_txt)

    def test_05_check_apertura_rileva_nuovi_e_integra(self):
        # Due file nuovi nell'archivio
        with open(os.path.join(self.radice, "nuovo_verbale.txt"), "w",
                  encoding="utf-8") as f:
            f.write("verbale di riunione, testo ordinario\n")
        sotto = os.path.join(self.radice, "cartella_nuova")
        os.makedirs(sotto, exist_ok=True)
        with open(os.path.join(sotto, "nota_tecnica.txt"), "w",
                  encoding="utf-8") as f:
            f.write("nota tecnica di prova\n")
        n_prima = len(self._attesi_filesystem()) - 2
        # Nuovo accesso alla dashboard: il check rileva i 2 nuovi
        self._forza_prossimo_check()
        r = self.client.get("/")
        testo = r.get_data(as_text=True)
        self.assertIn("<strong>2</strong> file nuovi non mappati", testo)
        self.assertIn("Integra nella mappa", testo)
        # I nuovi non sono ancora in mappa
        conn = db.get_connection()
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM inventario_file").fetchone()[0], n_prima)
        conn.close()
        # Integrazione: contatori aggiornati
        r = self.client.post("/inventario/integra", follow_redirects=True)
        testo = r.get_data(as_text=True)
        self.assertIn("2 file integrati", testo)
        self.assertNotIn("file nuovi non mappati", testo)
        self.assertIn('<div class="numero">%d</div>' % (n_prima + 2), testo)
        conn = db.get_connection()
        riga = conn.execute(
            "SELECT * FROM inventario_file WHERE percorso_rel = "
            "'cartella_nuova/nota_tecnica.txt'").fetchone()
        conn.close()
        self.assertIsNotNone(riga)
        self.assertEqual(riga["cartella_progetto"], "cartella_nuova")
        self.assertEqual(riga["stato"], "presente")

    def test_06_file_rimosso_marcato_scomparso(self):
        os.remove(os.path.join(self.radice, "nuovo_verbale.txt"))
        r = self.client.post("/inventario/ricontrolla", follow_redirects=True)
        testo = r.get_data(as_text=True)
        self.assertIn("1 scomparsi", testo)
        conn = db.get_connection()
        stato = conn.execute(
            "SELECT stato FROM inventario_file WHERE percorso_rel = "
            "'nuovo_verbale.txt'").fetchone()[0]
        conn.close()
        self.assertEqual(stato, "scomparso")
        # Il file scomparso non conta piu' nei KPI
        self.assertIn('<div class="numero">%d</div>'
                      % len(self._attesi_filesystem()), testo)

    def test_07_da_classificare_prima_della_scansione(self):
        from core import inventario as inv
        conn = db.get_connection()
        elenco = inv.da_classificare(conn, self.radice)
        conn.close()
        attesi = [p for p in self._attesi_filesystem()
                  if os.path.splitext(p)[1].lower() in inv.ESTENSIONI_ANALIZZABILI]
        self.assertEqual(sorted(elenco), sorted(attesi))
        type(self).n_analizzabili = len(attesi)
        r = self.client.get("/")
        testo = r.get_data(as_text=True)
        self.assertIn("necessita" , testo)  # avviso con link alla scansione
        self.assertIn("Nuova scansione", testo)

    def test_08_dopo_scansione_zero_da_classificare(self):
        scan_id, stato = esegui_scansione_sincrona(self.radice, "copertura")
        self.assertEqual(stato, "completata")
        from core import inventario as inv
        conn = db.get_connection()
        elenco = inv.da_classificare(conn, self.radice)
        conn.close()
        self.assertEqual(elenco, [])
        r = self.client.get("/")
        testo = r.get_data(as_text=True)
        self.assertNotIn("necessitano di scansione", testo)

    def test_09_file_modificato_torna_da_classificare(self):
        percorso = os.path.join(self.radice, "cartella_nuova", "nota_tecnica.txt")
        futuro = time.time() + 120
        os.utime(percorso, (futuro, futuro))
        # Il ricontrollo aggiorna la data di modifica in mappa
        self.client.post("/inventario/ricontrolla", follow_redirects=True)
        from core import inventario as inv
        conn = db.get_connection()
        elenco = inv.da_classificare(conn, self.radice)
        conn.close()
        self.assertEqual(elenco, ["cartella_nuova/nota_tecnica.txt"])
        r = self.client.get("/")
        self.assertIn("necessita", r.get_data(as_text=True))


class TestSidebarPassword(unittest.TestCase):
    """Sidebar di navigazione, cambio PIN e logout."""

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})

    def _sidebar(self, pagina="/"):
        testo = self.client.get(pagina).get_data(as_text=True)
        inizio = testo.find("<aside")
        fine = testo.find("</aside>")
        self.assertGreater(inizio, -1, "sidebar assente in %s" % pagina)
        return testo, testo[inizio:fine]

    def test_01_voci_menu_in_ordine(self):
        testo, sidebar = self._sidebar()
        voci = ["Dashboard", "Classificazione base", "Storico", "Dizionario",
                "Catalogo", "Definizione entità", "Arricchimento dati",
                "Validazione AI", "Perimetro e bozze", "Coda di revisione",
                "Metriche", "Utenti", "Password", "Logout"]
        posizioni = [sidebar.find(v) for v in voci]
        for voce, pos in zip(voci, posizioni):
            self.assertGreater(pos, -1, "voce mancante: %s" % voce)
        self.assertEqual(posizioni, sorted(posizioni),
                         "le voci non sono nell'ordine richiesto")
        # "Nuova scansione" non e' una voce di menu
        self.assertNotIn("Nuova scansione", sidebar)
        # ...ma e' il pulsante in evidenza nella vista Storico
        r = self.client.get("/storico/")
        testo = r.get_data(as_text=True)
        self.assertIn('id="bottone-nuova-scansione"', testo)
        self.assertIn("Nuova scansione", testo)

    def test_02_voce_attiva_evidenziata(self):
        _, sidebar = self._sidebar("/")
        self.assertRegex(sidebar, r'class="voce-menu attiva\s*" href="/"')
        _, sidebar = self._sidebar("/utenti/anagrafica")
        self.assertRegex(sidebar,
                         r'class="voce-menu attiva\s*" href="/utenti/anagrafica"')
        _, sidebar = self._sidebar("/dizionario/")
        self.assertRegex(sidebar,
                         r'class="voce-menu sotto-voce attiva\s*" href="/dizionario/"')
        # La sezione Classificazione base risulta aperta ed evidenziata
        self.assertIn("<details class=\"sezione-menu\" open>", sidebar)
        _, sidebar = self._sidebar("/storico/")
        self.assertRegex(sidebar,
                         r'class="voce-menu sotto-voce attiva\s*" href="/storico/"')
        # Sezione Catalogo: sotto-voce attiva e sezione auto-aperta
        _, sidebar = self._sidebar("/catalogo/")
        self.assertRegex(sidebar,
                         r'class="voce-menu sotto-voce attiva\s*" href="/catalogo/"')
        self.assertIn("<details class=\"sezione-menu\" open>", sidebar)
        _, sidebar = self._sidebar("/catalogo/arricchimento")
        self.assertRegex(
            sidebar,
            r'class="voce-menu sotto-voce attiva\s*" href="/catalogo/arricchimento"')
        # La voce Definizione entità non risulta attiva sull'arricchimento
        self.assertRegex(
            sidebar, r'class="voce-menu sotto-voce \s*" href="/catalogo/"')
        # Sezione Validazione AI: sotto-voce attiva e sezione auto-aperta
        _, sidebar = self._sidebar("/validazione/perimetro")
        self.assertRegex(
            sidebar,
            r'class="voce-menu sotto-voce attiva\s*" href="/validazione/perimetro"')
        self.assertIn("<details class=\"sezione-menu\" open>", sidebar)
        _, sidebar = self._sidebar("/validazione/coda")
        self.assertRegex(
            sidebar,
            r'class="voce-menu sotto-voce attiva\s*" href="/validazione/coda"')
        # Le altre sotto-voci della sezione non risultano attive
        self.assertRegex(
            sidebar,
            r'class="voce-menu sotto-voce \s*" href="/validazione/perimetro"')
        _, sidebar = self._sidebar("/validazione/metriche")
        self.assertRegex(
            sidebar,
            r'class="voce-menu sotto-voce attiva\s*" href="/validazione/metriche"')

    def test_03_cambio_pin(self):
        # PIN attuale errato rifiutato
        r = self.client.post("/utenti/password",
                             data={"pin_attuale": "9999", "pin_nuovo": "5678",
                                   "pin_conferma": "5678"})
        self.assertIn("PIN attuale non è corretto", r.get_data(as_text=True))
        # Nuovo PIN non valido rifiutato
        r = self.client.post("/utenti/password",
                             data={"pin_attuale": "1234", "pin_nuovo": "12",
                                   "pin_conferma": "12"})
        self.assertIn("da 4 a 6 cifre", r.get_data(as_text=True))
        # Conferma diversa rifiutata
        r = self.client.post("/utenti/password",
                             data={"pin_attuale": "1234", "pin_nuovo": "5678",
                                   "pin_conferma": "8765"})
        self.assertIn("non coincidono", r.get_data(as_text=True))
        # Cambio valido
        r = self.client.post("/utenti/password",
                             data={"pin_attuale": "1234", "pin_nuovo": "5678",
                                   "pin_conferma": "5678"},
                             follow_redirects=True)
        self.assertIn("PIN aggiornato", r.get_data(as_text=True))
        # Il PIN non e' salvato in chiaro
        conn = db.get_connection()
        memorizzato = conn.execute("SELECT pin FROM utenti").fetchone()[0]
        conn.close()
        self.assertNotIn("5678", memorizzato)

    def test_04_logout_e_accesso_con_nuovo_pin(self):
        r = self.client.get("/utenti/uscita", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        r = self.client.get("/", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/utenti/accesso", r.headers["Location"])
        # Il vecchio PIN non funziona piu'
        r = self.client.post("/utenti/accesso",
                             data={"utente": "1", "pin": "1234"})
        self.assertIn("non corretti", r.get_data(as_text=True))
        # Il nuovo PIN funziona
        r = self.client.post("/utenti/accesso",
                             data={"utente": "1", "pin": "5678"},
                             follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Carlo Verdini", r.get_data(as_text=True))

    def test_05_tutte_le_pagine_200_e_protette(self):
        pagine = ("/", "/dizionario/", "/scansione/", "/storico/",
                  "/catalogo/", "/catalogo/entita", "/catalogo/arricchimento",
                  "/catalogo/tipi/nuovo",
                  "/validazione/perimetro", "/validazione/coda",
                  "/validazione/metriche",
                  "/utenti/anagrafica", "/utenti/password")
        for pagina in pagine:
            r = self.client.get(pagina)
            self.assertEqual(r.status_code, 200, "pagina %s" % pagina)
        self.client.get("/utenti/uscita")
        for pagina in pagine:
            r = self.client.get(pagina, follow_redirects=False)
            self.assertEqual(r.status_code, 302, "pagina %s" % pagina)
            self.assertIn("/utenti/accesso", r.headers["Location"])
        self.client.post("/utenti/accesso", data={"utente": "1", "pin": "5678"})


def crea_cartella_progetto(radice, nome, file_nome="nota.txt"):
    percorso = os.path.join(radice, nome)
    os.makedirs(percorso, exist_ok=True)
    with open(os.path.join(percorso, file_nome), "w", encoding="utf-8") as f:
        f.write("contenuto di prova\n")


class TestCatalogoDefinizione(unittest.TestCase):
    """Modulo Catalogo 2A: tipi di entita', tre modalita' di estrazione,
    prova live sui nomi reali, conflitti di chiave, riallineamento."""

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})
        # Copia di lavoro dell'archivio di prova con le cartelle progetto e
        # due cartelle che generano un conflitto di chiave (stessa "P-010").
        cls.radice = os.path.join(tempfile.mkdtemp(prefix="arch_cat_"),
                                  "archivio")
        if ARCHIVIO_PROVA and os.path.isdir(ARCHIVIO_PROVA):
            shutil.copytree(ARCHIVIO_PROVA, cls.radice)
        else:
            os.makedirs(cls.radice)
        for nome in ("P-001 Impianto Alfa", "P-002 Impianto Beta",
                     "Documenti generali",
                     "P-010 Vecchia versione", "P-010 Nuova versione"):
            crea_cartella_progetto(cls.radice, nome)
        cls.client.post("/inventario/imposta-radice",
                        data={"radice": cls.radice})
        cls.client.post("/inventario/iniziale")

    @classmethod
    def _cartelle_inventario(cls):
        from core import catalogo as cat
        conn = db.get_connection()
        cartelle = cat.cartelle_inventario(conn)
        conn.close()
        return cartelle

    def _dati_prefisso(self, azione, nome="Progetto"):
        return {"nome": nome, "modo": "prefisso", "prefisso": "P-",
                "blocco1_tipo": "cifre", "blocco1_n": "3",
                "separatore": "", "blocco2_tipo": "cifre", "blocco2_n": "0",
                "escluse_json": "[]", "azione": azione}

    def _tipo_id(self, nome):
        conn = db.get_connection()
        riga = conn.execute("SELECT id FROM tipi_entita WHERE nome = ?",
                            (nome,)).fetchone()
        conn.close()
        self.assertIsNotNone(riga, "tipo di entità %s assente" % nome)
        return riga["id"]

    def _chiavi(self, nome_tipo, stato=None):
        conn = db.get_connection()
        sql = ("SELECT e.chiave FROM entita e JOIN tipi_entita t "
               "ON t.id = e.tipo_id WHERE t.nome = ?")
        valori = [nome_tipo]
        if stato:
            sql += " AND e.stato = ?"
            valori.append(stato)
        chiavi = [r[0] for r in conn.execute(sql, valori)]
        conn.close()
        return sorted(chiavi)

    def test_01_prova_live_prefisso(self):
        r = self.client.get("/catalogo/tipi/nuovo")
        self.assertEqual(r.status_code, 200)
        # Prima della prova il pulsante di salvataggio non compare
        self.assertNotIn('value="salva"', r.get_data(as_text=True))
        r = self.client.post("/catalogo/tipi/nuovo",
                             data=self._dati_prefisso("prova"))
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        # Tabella cartella -> chiave sui nomi reali dell'inventario
        self.assertIn('id="tabella-prova"', testo)
        for cartella in self._cartelle_inventario():
            self.assertIn(cartella, testo)
        self.assertIn("P-001", testo)
        self.assertIn("P-002", testo)
        # Evidenza delle cartelle senza estrazione e delle chiavi duplicate
        self.assertIn("nessuna estrazione", testo)
        self.assertIn("conflitto: chiave duplicata", testo)
        # Solo dopo la prova compare il salvataggio
        self.assertIn('value="salva"', testo)
        # Nulla e' stato ancora salvato
        conn = db.get_connection()
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM tipi_entita").fetchone()[0], 0)
        conn.close()

    def test_02_salvataggio_prefisso_genera_entita(self):
        r = self.client.post("/catalogo/tipi/nuovo",
                             data=self._dati_prefisso("salva"))
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        # Report del riallineamento con conflitti mostrati
        self.assertIn("Riallineamento", testo)
        self.assertIn("Entità create", testo)
        self.assertIn("Conflitti di chiave", testo)
        self.assertIn("P-010", testo)
        self.assertIn("Escludi dalla generazione", testo)
        # Entita' create solo per le cartelle con chiave univoca
        chiavi = self._chiavi("Progetto", "attiva")
        self.assertIn("P-001", chiavi)
        self.assertIn("P-002", chiavi)
        # Le cartelle in conflitto restano senza entita'
        self.assertNotIn("P-010", chiavi)
        # La cartella senza estrazione non genera entita'
        conn = db.get_connection()
        n = conn.execute("SELECT COUNT(*) FROM entita e JOIN tipi_entita t "
                         "ON t.id = e.tipo_id WHERE t.nome = 'Progetto' "
                         "AND e.cartella_origine = 'Documenti generali'"
                         ).fetchone()[0]
        conn.close()
        self.assertEqual(n, 0)

    def test_03_modalita_nome_intero(self):
        r = self.client.post("/catalogo/tipi/nuovo",
                             data={"nome": "Cartella", "modo": "intero",
                                   "escluse_json": "[]", "azione": "salva"})
        self.assertEqual(r.status_code, 200)
        # Una entita' per ogni cartella di primo livello, chiave = nome intero
        self.assertEqual(self._chiavi("Cartella", "attiva"),
                         sorted(self._cartelle_inventario()))

    def test_04_modalita_regex(self):
        r = self.client.post("/catalogo/tipi/nuovo",
                             data={"nome": "ProgettoRegex", "modo": "regex",
                                   "regex": r"^(P-\d{3})",
                                   "escluse_json": "[]", "azione": "salva"})
        self.assertEqual(r.status_code, 200)
        chiavi = self._chiavi("ProgettoRegex", "attiva")
        self.assertIn("P-001", chiavi)
        self.assertIn("P-002", chiavi)
        self.assertNotIn("P-010", chiavi)  # conflitto anche in modalita' regex
        # Regex non valida rifiutata
        r = self.client.post("/catalogo/tipi/nuovo",
                             data={"nome": "Rotta", "modo": "regex",
                                   "regex": "(", "escluse_json": "[]",
                                   "azione": "prova"},
                             follow_redirects=True)
        self.assertIn("Espressione non valida", r.get_data(as_text=True))

    def test_05_riallineamento_nuova_e_orfana(self):
        # Nuova cartella e rimozione di una esistente
        crea_cartella_progetto(self.radice, "P-003 Impianto Gamma")
        shutil.rmtree(os.path.join(self.radice, "P-001 Impianto Alfa"))
        self.client.post("/inventario/integra")
        tid = self._tipo_id("Progetto")
        r = self.client.post("/catalogo/tipi/%d/riallinea" % tid)
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn("P-003", testo)
        self.assertIn("Entità senza riscontro", testo)
        self.assertIn("P-001", testo)
        # Nuova entita' creata, orfana marcata e mai cancellata
        self.assertIn("P-003", self._chiavi("Progetto", "attiva"))
        self.assertEqual(self._chiavi("Progetto", "senza_riscontro"),
                         ["P-001"])
        conn = db.get_connection()
        riga = conn.execute(
            "SELECT e.stato FROM entita e JOIN tipi_entita t "
            "ON t.id = e.tipo_id WHERE t.nome = 'Progetto' "
            "AND e.chiave = 'P-001'").fetchone()
        conn.close()
        self.assertIsNotNone(riga)  # l'entita' esiste ancora
        self.assertEqual(riga["stato"], "senza_riscontro")

    def test_06_conflitto_risolto_con_esclusione(self):
        tid = self._tipo_id("Progetto")
        r = self.client.post("/catalogo/tipi/%d/escludi" % tid,
                             data={"cartella": "P-010 Vecchia versione"})
        self.assertEqual(r.status_code, 200)
        # Il conflitto e' risolto: l'entita' P-010 nasce dalla cartella restante
        chiavi = self._chiavi("Progetto", "attiva")
        self.assertIn("P-010", chiavi)
        conn = db.get_connection()
        riga = conn.execute(
            "SELECT e.cartella_origine FROM entita e JOIN tipi_entita t "
            "ON t.id = e.tipo_id WHERE t.nome = 'Progetto' "
            "AND e.chiave = 'P-010'").fetchone()
        conn.close()
        self.assertEqual(riga["cartella_origine"], "P-010 Nuova versione")
        # La pagina di definizione elenca i tipi con i loro contatori
        r = self.client.get("/catalogo/")
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn("Progetto", testo)
        self.assertIn("Cartella", testo)
        self.assertIn("Entità attive", testo)
        self.assertIn("Cartelle escluse", testo)

    def test_07_normalizzazione_chiave_unitaria(self):
        from core.catalogo import normalizza_chiave
        self.assertEqual(normalizza_chiave("P-001")[0], "P-001")
        norm, passi = normalizza_chiave("  p-001 ")
        self.assertEqual(norm, "P-001")
        self.assertEqual(len(passi), 2)  # trim + maiuscole
        norm, passi = normalizza_chiave("007")
        self.assertEqual(norm, "7")
        self.assertIn("zeri iniziali rimossi", passi)
        self.assertEqual(normalizza_chiave("000")[0], "0")
        self.assertEqual(normalizza_chiave("")[0], "")


class TestCatalogoArricchimento(unittest.TestCase):
    """Modulo Catalogo 2B: wizard di import, anteprima di qualita',
    1:N, dedup, provenienza e rollback, anomalie, export XLSX."""

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})
        cls.radice = os.path.join(tempfile.mkdtemp(prefix="arch_arr_"),
                                  "archivio")
        os.makedirs(cls.radice)
        for nome in ("P-001 Impianto Alfa", "P-002 Impianto Beta",
                     "P-003 Impianto Gamma"):
            crea_cartella_progetto(cls.radice, nome)
        cls.client.post("/inventario/imposta-radice",
                        data={"radice": cls.radice})
        cls.client.post("/inventario/iniziale")
        cls.client.post("/catalogo/tipi/nuovo",
                        data={"nome": "Progetto", "modo": "prefisso",
                              "prefisso": "P-", "blocco1_tipo": "cifre",
                              "blocco1_n": "3", "separatore": "",
                              "blocco2_tipo": "cifre", "blocco2_n": "0",
                              "escluse_json": "[]", "azione": "salva"})
        conn = db.get_connection()
        cls.tipo_id = conn.execute(
            "SELECT id FROM tipi_entita WHERE nome = 'Progetto'"
            ).fetchone()[0]
        conn.close()

    # ------------------------------------------------------------------
    # Supporto
    # ------------------------------------------------------------------

    def _carica(self, nome_file, contenuto):
        """Upload del file: restituisce (token, html_mappatura)."""
        r = self.client.post(
            "/catalogo/arricchimento/carica",
            data={"tipo_entita": str(self.tipo_id),
                  "file_dati": (io.BytesIO(contenuto), nome_file)},
            content_type="multipart/form-data")
        self.assertEqual(r.status_code, 302)
        percorso = r.headers["Location"]
        self.assertIn("/mappatura", percorso)
        token = percorso.rstrip("/").split("/")[-2]
        r = self.client.get(percorso)
        self.assertEqual(r.status_code, 200)
        return token, r.get_data(as_text=True)

    def _anteprima(self, token, mappatura_form):
        r = self.client.post(
            "/catalogo/arricchimento/%s/anteprima" % token,
            data=mappatura_form)
        self.assertEqual(r.status_code, 200)
        return r.get_data(as_text=True)

    def _conferma(self, token, html_anteprima):
        import html as html_mod
        m = re.search(r"name=\"mappatura_json\" value='([^']*)'",
                      html_anteprima)
        self.assertIsNotNone(m, "campo mappatura_json assente nell'anteprima")
        r = self.client.post(
            "/catalogo/arricchimento/%s/conferma" % token,
            data={"mappatura_json": html_mod.unescape(m.group(1))})
        self.assertEqual(r.status_code, 302)
        return int(r.headers["Location"].rstrip("/").split("/")[-1])

    def _importa(self, nome_file, contenuto, mappatura_form):
        token, _ = self._carica(nome_file, contenuto)
        html = self._anteprima(token, mappatura_form)
        return self._conferma(token, html), html

    def _entita_id(self, chiave):
        conn = db.get_connection()
        riga = conn.execute(
            "SELECT id FROM entita WHERE tipo_id = ? AND chiave = ?",
            (self.tipo_id, chiave)).fetchone()
        conn.close()
        self.assertIsNotNone(riga, "entità %s assente" % chiave)
        return riga["id"]

    def _valori(self, chiave, attributo):
        """Valori deduplicati dell'attributo per l'entita' (dalla logica
        di consultazione, con provenienza)."""
        from core import catalogo as cat
        conn = db.get_connection()
        attributi = cat.attributi_di_entita(conn, self._entita_id(chiave))
        conn.close()
        return [a for a in attributi if a["attributo"] == attributo]

    # ------------------------------------------------------------------
    # Test
    # ------------------------------------------------------------------

    def test_01_csv_virgola_flusso_completo(self):
        contenuto = (
            "﻿chiave,articolo,descrizione\n"
            "P-001,ART-001,Pompa centrifuga\n"
            "P-001,ART-002,Valvola a sfera\n"
            "P-002,ART-003,Motore elettrico\n"
            "P-999,ART-404,Riga senza entità\n"
            "P-001,ART-001,Pompa centrifuga\n"
            " p-002 ,ART-005,Scambiatore\n").encode("utf-8")
        token, mappatura_html = self._carica("articoli.csv", contenuto)
        # Anteprima delle prime righe con intestazioni riconosciute (BOM
        # rimosso, separatore virgola)
        self.assertIn("chiave", mappatura_html)
        self.assertIn("articolo", mappatura_html)
        self.assertIn("Pompa centrifuga", mappatura_html)
        html = self._anteprima(token, {
            "chiave_col": "0", "includi_1": "1", "nome_1": "articolo",
            "includi_2": "1", "nome_2": "descrizione"})
        # Anteprima di qualita' prima della conferma
        self.assertIn("Righe con chiave senza entità", html)
        self.assertIn("P-999", html)
        self.assertIn("Entità mai citate dal file", html)
        self.assertIn("P-003", html)          # mai citata
        self.assertIn("duplicato esatto", html)
        self.assertIn("normalizzazione", html)
        # Nessun dato salvato prima della conferma
        conn = db.get_connection()
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM attributi_entita").fetchone()[0], 0)
        conn.close()
        imp_id = self._conferma(token, html)
        type(self).imp1_id = imp_id
        # 1:N nativo: due articoli per P-001 (il duplicato e' stato scartato)
        valori = self._valori("P-001", "articolo")
        self.assertEqual([v["valore"] for v in valori],
                         ["ART-001", "ART-002"])
        # Chiave normalizzata " p-002 " agganciata a P-002
        valori = self._valori("P-002", "articolo")
        self.assertEqual([v["valore"] for v in valori],
                         ["ART-003", "ART-005"])
        # Provenienza: importazione, file, data, utente della sessione
        conn = db.get_connection()
        imp = conn.execute("SELECT * FROM importazioni WHERE id = ?",
                           (imp_id,)).fetchone()
        anomalie = [r["tipo"] for r in conn.execute(
            "SELECT tipo FROM anomalie_import WHERE importazione_id = ?",
            (imp_id,))]
        conn.close()
        self.assertEqual(imp["nome_file"], "articoli.csv")
        self.assertEqual(imp["utente"], "Carlo Verdini")
        self.assertEqual(imp["stato"], "confermata")
        self.assertEqual(imp["n_righe"], 6)
        self.assertEqual(imp["n_scartate"], 1)
        self.assertIn("chiave_senza_entita", anomalie)
        self.assertIn("chiave_normalizzata", anomalie)
        self.assertIn("duplicato_esatto", anomalie)
        self.assertIn("entita_non_citate", anomalie)

    def test_02_csv_puntoevirgola_latin1(self):
        contenuto = ("chiave;responsabile\n"
                     "P-002;Società Però S.r.l.\n").encode("latin-1")
        imp_id, _ = self._importa("responsabili.csv", contenuto, {
            "chiave_col": "0", "includi_1": "1", "nome_1": "responsabile"})
        valori = self._valori("P-002", "responsabile")
        self.assertEqual([v["valore"] for v in valori],
                         ["Società Però S.r.l."])

    def test_03_xlsx(self):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["chiave", "fornitore"])
        ws.append(["P-003", "Rossi SpA"])
        ws.append(["P-003", "Bianchi Srl"])
        buf = io.BytesIO()
        wb.save(buf)
        imp_id, html = self._importa("fornitori.xlsx", buf.getvalue(), {
            "chiave_col": "0", "includi_1": "1", "nome_1": "fornitore"})
        valori = self._valori("P-003", "fornitore")
        self.assertEqual([v["valore"] for v in valori],
                         ["Bianchi Srl", "Rossi SpA"])

    def test_04_rinomina_attributo(self):
        contenuto = "chiave,cod_art\nP-001,XY-77\n".encode("utf-8")
        imp_id, _ = self._importa("codici.csv", contenuto, {
            "chiave_col": "0", "includi_1": "1",
            "nome_1": "Codice articolo interno"})
        valori = self._valori("P-001", "Codice articolo interno")
        self.assertEqual([v["valore"] for v in valori], ["XY-77"])
        conn = db.get_connection()
        n = conn.execute("SELECT COUNT(*) FROM attributi_entita "
                         "WHERE nome_attributo = 'cod_art'").fetchone()[0]
        conn.close()
        self.assertEqual(n, 0)

    def test_05_secondo_import_e_rollback_corretto(self):
        contenuto_a = "chiave,collaudo\nP-001,COL-9\n".encode("utf-8")
        contenuto_b = "chiave,collaudo\nP-001,COL-9\n".encode("utf-8")
        imp_a, _ = self._importa("collaudi_a.csv", contenuto_a, {
            "chiave_col": "0", "includi_1": "1", "nome_1": "collaudo"})
        imp_b, html_b = self._importa("collaudi_b.csv", contenuto_b, {
            "chiave_col": "0", "includi_1": "1", "nome_1": "collaudo"})
        # Nessun duplicato in consultazione, ma doppia provenienza
        valori = self._valori("P-001", "collaudo")
        self.assertEqual(len(valori), 1)
        self.assertEqual(valori[0]["valore"], "COL-9")
        self.assertEqual(len(valori[0]["provenienze"]), 2)
        # L'anteprima del secondo import segnala che il valore non e' nuovo
        self.assertIn("Valori nuovi", html_b)
        # Rimozione del primo import: il valore resta per il secondo
        r = self.client.post(
            "/catalogo/arricchimento/importazioni/%d/rimuovi" % imp_a,
            follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        valori = self._valori("P-001", "collaudo")
        self.assertEqual(len(valori), 1)
        self.assertEqual(len(valori[0]["provenienze"]), 1)
        self.assertEqual(valori[0]["provenienze"][0]["file"],
                         "collaudi_b.csv")
        # Rimozione anche del secondo: il valore sparisce
        self.client.post(
            "/catalogo/arricchimento/importazioni/%d/rimuovi" % imp_b)
        self.assertEqual(self._valori("P-001", "collaudo"), [])
        # Gli altri import non sono stati toccati dal rollback
        self.assertEqual(
            [v["valore"] for v in self._valori("P-001", "articolo")],
            ["ART-001", "ART-002"])
        conn = db.get_connection()
        stato = conn.execute("SELECT stato FROM importazioni WHERE id = ?",
                             (imp_a,)).fetchone()[0]
        conn.close()
        self.assertEqual(stato, "rimossa")
        # L'elenco importazioni mostra lo storico, comprese le rimosse
        r = self.client.get("/catalogo/arricchimento")
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn("articoli.csv", testo)
        self.assertIn("collaudi_a.csv", testo)
        self.assertIn("rimossa", testo)

    def test_06_stato_chiarimento_anomalie(self):
        conn = db.get_connection()
        anomalia = conn.execute(
            "SELECT id FROM anomalie_import WHERE importazione_id = ? "
            "AND tipo = 'chiave_senza_entita'", (self.imp1_id,)).fetchone()
        conn.close()
        self.assertIsNotNone(anomalia)
        # La pagina di dettaglio elenca l'anomalia gestibile
        r = self.client.get(
            "/catalogo/arricchimento/importazioni/%d" % self.imp1_id)
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn("Chiave senza entità", testo)
        self.assertIn("P-999", testo)
        # Aggiornamento dello stato con nota
        r = self.client.post(
            "/catalogo/arricchimento/anomalie/%d/stato" % anomalia["id"],
            data={"stato_chiarimento": "chiarita",
                  "nota_chiarimento": "Progetto non ancora a catalogo."},
            follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        conn = db.get_connection()
        riga = conn.execute("SELECT * FROM anomalie_import WHERE id = ?",
                            (anomalia["id"],)).fetchone()
        conn.close()
        self.assertEqual(riga["stato_chiarimento"], "chiarita")
        self.assertEqual(riga["nota_chiarimento"],
                         "Progetto non ancora a catalogo.")
        # Stato non previsto rifiutato
        self.client.post(
            "/catalogo/arricchimento/anomalie/%d/stato" % anomalia["id"],
            data={"stato_chiarimento": "inventato"})
        conn = db.get_connection()
        stato = conn.execute(
            "SELECT stato_chiarimento FROM anomalie_import WHERE id = ?",
            (anomalia["id"],)).fetchone()[0]
        conn.close()
        self.assertEqual(stato, "chiarita")

    def test_07_scheda_entita_ed_elenco_filtrabile(self):
        eid = self._entita_id("P-001")
        r = self.client.get("/catalogo/entita/%d" % eid)
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        # Chiave, cartella, stato e attributi con provenienza
        self.assertIn("P-001", testo)
        self.assertIn("P-001 Impianto Alfa", testo)
        self.assertIn("attiva", testo)
        self.assertIn("ART-001", testo)
        self.assertIn("ART-002", testo)
        self.assertIn("importazione da", testo)
        self.assertIn("articoli.csv", testo)
        self.assertIn("Carlo Verdini", testo)
        # Elenco filtrabile per chiave
        r = self.client.get("/catalogo/entita?q=P-001")
        testo = r.get_data(as_text=True)
        self.assertIn("P-001", testo)
        self.assertNotIn("P-002 Impianto Beta", testo)
        # ... e per stato (tutte attive: nessuna senza riscontro)
        r = self.client.get("/catalogo/entita?stato=senza_riscontro")
        self.assertIn("Nessuna entità corrispondente",
                      r.get_data(as_text=True))

    def test_08_export_xlsx(self):
        import openpyxl
        # Export del catalogo: entita' e attributi con provenienza
        r = self.client.get("/catalogo/export/catalogo.xlsx")
        self.assertEqual(r.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(r.data))
        self.assertEqual(wb.sheetnames, ["Entità", "Attributi"])
        ws = wb["Entità"]
        chiavi = [riga[1].value for riga in ws.iter_rows(min_row=2)]
        self.assertIn("P-001", chiavi)
        self.assertIn("P-002", chiavi)
        self.assertIn("P-003", chiavi)
        ws = wb["Attributi"]
        righe = [(r_[1].value, r_[2].value, r_[3].value, r_[4].value)
                 for r_ in ws.iter_rows(min_row=2)]
        attesa = [r_ for r_ in righe
                  if r_[0] == "P-001" and r_[1] == "articolo"
                  and r_[2] == "ART-001"]
        self.assertEqual(len(attesa), 1)
        self.assertIn("articoli.csv", attesa[0][3])
        # I valori degli import rimossi non compaiono
        self.assertEqual([r_ for r_ in righe if r_[2] == "COL-9"], [])
        # Export delle anomalie
        r = self.client.get("/catalogo/arricchimento/export/anomalie.xlsx")
        self.assertEqual(r.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(r.data))
        self.assertEqual(wb.sheetnames, ["Anomalie import"])
        ws = wb["Anomalie import"]
        righe = [[c.value for c in riga] for riga in ws.iter_rows(min_row=2)]
        self.assertTrue(any(r_[5] == "P-999" for r_ in righe))
        self.assertTrue(any(r_[7] == "Chiarita" for r_ in righe))


def crea_docx_minimo(percorso, paragrafi):
    """Crea un .docx minimo (solo word/document.xml) leggibile
    dall'estrattore dell'app: un paragrafo per elemento della lista."""
    from xml.sax.saxutils import escape
    corpo = "".join("<w:p><w:r><w:t>%s</w:t></w:r></w:p>" % escape(p)
                    for p in paragrafi)
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body>%s</w:body></w:document>'
           % corpo)
    with zipfile.ZipFile(percorso, "w") as z:
        z.writestr("word/document.xml", xml)


def bozza_valida(cartella="P-100 Sonda TX", proposte=None, **extra):
    """Struttura di un file bozza conforme al contratto wikify-bozza/1.0."""
    dati = {"formato": "wikify-bozza/1.0",
            "cartella_progetto": cartella,
            "chiave_entita": "P-100",
            "generato_da": "test",
            "data_generazione": "2026-07-26T10:00:00",
            "perimetro": {"file_esaminati": [],
                          "file_esclusi_da_perimetro": []},
            "proposte": proposte if proposte is not None else [],
            "note_agente": []}
    dati.update(extra)
    return dati


def proposta_valida(file="doc.docx", campo="tipologia",
                    valore="manuale_installazione", confidenza=0.9,
                    posizione="corpo, par. 1",
                    citazione="testo letterale di evidenza",
                    sezione="intero documento"):
    return {"file": file, "sezione": sezione, "campo": campo,
            "valore_proposto": valore, "confidenza": confidenza,
            "evidenza": {"posizione": posizione, "citazione": citazione}}


def importa_bozze(client, *coppie, follow=True):
    """Upload di uno o piu' file bozza: coppie (nome_file, dati_o_bytes)."""
    files = []
    for nome, dati in coppie:
        corpo = dati if isinstance(dati, bytes) else \
            json.dumps(dati, ensure_ascii=False).encode("utf-8")
        files.append((io.BytesIO(corpo), nome))
    return client.post("/validazione/perimetro/importa",
                       data={"bozze": files},
                       content_type="multipart/form-data",
                       follow_redirects=follow)


class TestValidazionePerimetro(unittest.TestCase):
    """Modulo Validazione AI, punto 1: export del perimetro condivisibile
    da un triage misto (condivisibili, riservati, da valutare)."""

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})
        conn = db.get_connection()
        cur = conn.execute(
            "INSERT INTO scansioni (data, radice, etichetta, stato) "
            "VALUES ('01/07/2026 10:00', '/archivio', 'perimetro', "
            "'completata')")
        cls.sid = cur.lastrowid
        for nome in ("a.txt", "b.txt", "c.txt", "d.txt"):
            conn.execute(
                "INSERT INTO file_analizzati (scansione_id, file, formato, "
                "totale) VALUES (?, ?, '.txt', 1)", (cls.sid, nome))
        conn.execute("INSERT INTO non_analizzati (scansione_id, file, motivo) "
                     "VALUES (?, 'legacy.doc', 'formato legacy')", (cls.sid,))
        for nome, qualifica in (("a.txt", "Condivisibile"),
                                ("b.txt", "Riservato"),
                                ("c.txt", "Da valutare")):
            conn.execute(
                "INSERT INTO triage_file (scansione_id, file, qualifica, "
                "validatore, verificato) VALUES (?, ?, ?, 'Carlo', 1)",
                (cls.sid, nome, qualifica))
        conn.commit()
        conn.close()

    def test_01_elenco_condivisibili_da_core(self):
        conn = db.get_connection()
        elenco = db.elenco_condivisibili(conn, self.sid)
        conn.close()
        self.assertEqual(elenco, ["a.txt"])

    def test_02_pagina_perimetro(self):
        r = self.client.get("/validazione/perimetro")
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn("a.txt", testo)
        self.assertIn("b.txt", testo)
        self.assertIn("perimetro_condivisibile.json", testo)

    def test_03_export_json_solo_condivisibili(self):
        r = self.client.get("/validazione/perimetro/export.json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("perimetro_condivisibile.json",
                      r.headers.get("Content-Disposition", ""))
        dati = json.loads(r.get_data(as_text=True))
        self.assertEqual(dati["formato"], "wikify-perimetro/1.0")
        self.assertEqual(dati["scansione_id"], self.sid)
        self.assertEqual(dati["radice"], "/archivio")
        self.assertTrue(dati["data_export"])
        # Solo i condivisibili nell'elenco consultabile
        self.assertEqual(dati["file_condivisibili"], ["a.txt"])
        # Gli esclusi riportano la qualifica; chi non ha triage e' Da valutare
        esclusi = {e["percorso"]: e["qualifica"]
                   for e in dati["file_esclusi"]}
        self.assertEqual(esclusi, {"b.txt": "Riservato",
                                   "c.txt": "Da valutare",
                                   "d.txt": "Da valutare",
                                   "legacy.doc": "Non analizzato"})

    def test_04_scelta_scansione(self):
        conn = db.get_connection()
        cur = conn.execute(
            "INSERT INTO scansioni (data, radice, etichetta, stato) VALUES "
            "('02/07/2026 10:00', '/archivio2', 'seconda', 'completata')")
        sid2 = cur.lastrowid
        conn.execute(
            "INSERT INTO triage_file (scansione_id, file, qualifica, "
            "validatore, verificato) VALUES (?, 'e.txt', 'Condivisibile', "
            "'Carlo', 1)", (sid2,))
        conn.commit()
        conn.close()
        # Senza parametro: l'ultima completata
        r = self.client.get("/validazione/perimetro/export.json")
        dati = json.loads(r.get_data(as_text=True))
        self.assertEqual(dati["scansione_id"], sid2)
        self.assertEqual(dati["file_condivisibili"], ["e.txt"])
        # Con il parametro: la scansione scelta
        r = self.client.get("/validazione/perimetro/export.json?scansione=%d"
                            % self.sid)
        dati = json.loads(r.get_data(as_text=True))
        self.assertEqual(dati["scansione_id"], self.sid)
        self.assertEqual(dati["file_condivisibili"], ["a.txt"])


class TestValidazioneImportBozze(unittest.TestCase):
    """Modulo Validazione AI, punto 1: import severo delle bozze con
    rifiuti, scarti motivati, troncamenti e riepilogo del lotto."""

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})

    def _n_lotti(self):
        conn = db.get_connection()
        n = conn.execute("SELECT COUNT(*) FROM lotti_validazione"
                         ).fetchone()[0]
        conn.close()
        return n

    def _ultimo_lotto(self):
        conn = db.get_connection()
        lotto = conn.execute("SELECT * FROM lotti_validazione "
                             "ORDER BY id DESC LIMIT 1").fetchone()
        proposte = []
        if lotto is not None:
            proposte = conn.execute(
                "SELECT * FROM proposte WHERE lotto_id = ? ORDER BY id",
                (lotto["id"],)).fetchall()
        conn.close()
        return lotto, proposte

    def test_01_file_valido_accettato(self):
        dati = bozza_valida(proposte=[
            proposta_valida(campo="tipologia",
                            valore="manuale_installazione",
                            confidenza=0.92),
            proposta_valida(campo="riservatezza", valore="condivisibile",
                            confidenza=0.7,
                            citazione="testo pubblico ordinario"),
        ])
        r = importa_bozze(self.client, ("bozza_p100.json", dati))
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn("2 proposte accettate", testo)
        lotto, proposte = self._ultimo_lotto()
        self.assertEqual(lotto["formato"], "wikify-bozza/1.0")
        self.assertEqual(lotto["nome_file_origine"], "bozza_p100.json")
        self.assertEqual(lotto["cartella_progetto"], "P-100 Sonda TX")
        self.assertEqual(lotto["chiave_entita"], "P-100")
        self.assertEqual(lotto["n_accettate"], 2)
        self.assertEqual(lotto["n_scartate"], 0)
        self.assertEqual(lotto["stato"], "importato")
        self.assertEqual(len(proposte), 2)
        p = proposte[0]
        self.assertEqual(p["file"], "doc.docx")
        self.assertEqual(p["sezione"], "intero documento")
        self.assertEqual(p["campo"], "tipologia")
        self.assertEqual(p["valore_proposto"], "manuale_installazione")
        self.assertAlmostEqual(p["confidenza"], 0.92)
        self.assertEqual(p["evidenza_posizione"], "corpo, par. 1")
        self.assertEqual(p["citazione_troncata"], 0)
        # Il dettaglio del lotto e' consultabile
        r = self.client.get("/validazione/perimetro/lotti/%d" % lotto["id"])
        self.assertEqual(r.status_code, 200)
        self.assertIn("manuale_installazione", r.get_data(as_text=True))

    def test_02_formato_sconosciuto_rifiutato(self):
        n_prima = self._n_lotti()
        dati = bozza_valida(proposte=[proposta_valida()])
        dati["formato"] = "wikify-bozza/9.9"
        r = importa_bozze(self.client, ("bozza_futura.json", dati))
        testo = r.get_data(as_text=True)
        self.assertIn("File rifiutato", testo)
        self.assertIn("formato sconosciuto", testo)
        self.assertEqual(self._n_lotti(), n_prima)
        # Anche un file che non e' JSON viene rifiutato
        r = importa_bozze(self.client, ("rotto.json", b"non sono json"))
        self.assertIn("non è un JSON leggibile", r.get_data(as_text=True))
        self.assertEqual(self._n_lotti(), n_prima)

    def test_03_proposta_senza_evidenza_scartata_e_contata(self):
        senza_citazione = proposta_valida(citazione="")
        senza_posizione = proposta_valida(posizione="   ")
        senza_evidenza = proposta_valida()
        del senza_evidenza["evidenza"]
        dati = bozza_valida(proposte=[
            proposta_valida(), senza_citazione, senza_posizione,
            senza_evidenza])
        r = importa_bozze(self.client, ("bozza_evidenze.json", dati))
        self.assertIn("3 scartate", r.get_data(as_text=True))
        lotto, proposte = self._ultimo_lotto()
        self.assertEqual(lotto["n_accettate"], 1)
        self.assertEqual(lotto["n_scartate"], 3)
        dettaglio = json.loads(lotto["dettaglio_scarti_json"])
        self.assertEqual(dettaglio["conteggi"]["senza_evidenza"], 3)
        self.assertEqual(len(proposte), 1)

    def test_04_campo_o_valore_fuori_tassonomia_scartati(self):
        dati = bozza_valida(proposte=[
            proposta_valida(campo="colore", valore="rosso"),
            proposta_valida(campo="tipologia", valore="poesia"),
            proposta_valida(campo="riservatezza", valore="segretissimo"),
            proposta_valida(campo="forma_caratteristiche", valore="prosa"),
        ])
        r = importa_bozze(self.client, ("bozza_tassonomie.json", dati))
        self.assertEqual(r.status_code, 200)
        lotto, proposte = self._ultimo_lotto()
        self.assertEqual(lotto["n_accettate"], 1)
        self.assertEqual(lotto["n_scartate"], 3)
        dettaglio = json.loads(lotto["dettaglio_scarti_json"])
        self.assertEqual(dettaglio["conteggi"]["campo_non_previsto"], 1)
        self.assertEqual(dettaglio["conteggi"]["valore_fuori_tassonomia"], 2)
        self.assertEqual(proposte[0]["campo"], "forma_caratteristiche")
        # Il dettaglio del lotto espone i motivi in italiano
        r = self.client.get("/validazione/perimetro/lotti/%d" % lotto["id"])
        testo = r.get_data(as_text=True)
        self.assertIn("Campo non previsto", testo)
        self.assertIn("Valore fuori tassonomia", testo)

    def test_05_citazione_lunga_troncata_con_nota(self):
        lunga = "x" * 450
        dati = bozza_valida(proposte=[
            proposta_valida(citazione=lunga, confidenza=0.5)])
        r = importa_bozze(self.client, ("bozza_lunga.json", dati))
        self.assertIn("troncate", r.get_data(as_text=True))
        lotto, proposte = self._ultimo_lotto()
        self.assertEqual(lotto["n_accettate"], 1)
        self.assertEqual(lotto["n_troncate"], 1)
        self.assertEqual(len(proposte[0]["evidenza_citazione"]), 300)
        self.assertEqual(proposte[0]["citazione_troncata"], 1)

    def test_06_riepilogo_lotto_misto(self):
        dati = bozza_valida(proposte=[
            proposta_valida(confidenza=0.8),
            proposta_valida(citazione=""),
            proposta_valida(campo="tipologia", valore="romanzo"),
            proposta_valida(citazione="y" * 350, confidenza=0.6),
        ])
        r = importa_bozze(self.client, ("bozza_mista.json", dati))
        testo = r.get_data(as_text=True)
        self.assertIn("2 proposte accettate", testo)
        self.assertIn("2 scartate", testo)
        lotto, _proposte = self._ultimo_lotto()
        self.assertEqual(lotto["n_accettate"], 2)
        self.assertEqual(lotto["n_scartate"], 2)
        self.assertEqual(lotto["n_troncate"], 1)
        dettaglio = json.loads(lotto["dettaglio_scarti_json"])
        self.assertEqual(dettaglio["conteggi"],
                         {"senza_evidenza": 1, "valore_fuori_tassonomia": 1})
        self.assertEqual(dettaglio["n_troncate"], 1)

    def test_07_upload_multiplo(self):
        n_prima = self._n_lotti()
        valido = bozza_valida(proposte=[proposta_valida()])
        rifiutato = bozza_valida(proposte=[proposta_valida()])
        rifiutato["formato"] = "sconosciuto/1.0"
        r = importa_bozze(self.client, ("multi_ok.json", valido),
                          ("multi_no.json", rifiutato))
        testo = r.get_data(as_text=True)
        self.assertIn("multi_ok.json", testo)
        self.assertIn("File rifiutato (multi_no.json)", testo)
        self.assertEqual(self._n_lotti(), n_prima + 1)


class TestValidazioneCoda(unittest.TestCase):
    """Modulo Validazione AI, punto 2: coda per cartella ordinata per
    confidenza crescente, vista affiancata con estratto reale e fallback,
    azioni Conferma / Correggi / Caso nuovo, avvertenza scanner e note."""

    CARTELLA = "P-100 Sonda TX"

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})
        # Archivio con un docx reale nella cartella progetto
        cls.radice = os.path.join(tempfile.mkdtemp(prefix="arch_val_"),
                                  "archivio")
        os.makedirs(os.path.join(cls.radice, cls.CARTELLA))
        cls.par1 = "Manuale di installazione Sonda TX100"
        cls.par2 = "La pressione massima di esercizio è pari a 16 bar."
        cls.par3 = "Parametri interni riservati del banco di taratura."
        crea_docx_minimo(
            os.path.join(cls.radice, cls.CARTELLA, "manuale.docx"),
            [cls.par1, cls.par2, cls.par3])
        cls.client.post("/inventario/imposta-radice",
                        data={"radice": cls.radice})
        # Bozza: confidenze volutamente fuori ordine
        dati = bozza_valida(cartella=cls.CARTELLA, proposte=[
            proposta_valida(file="manuale.docx", campo="tipologia",
                            valore="manuale_installazione", confidenza=0.9,
                            posizione="corpo, par. 1", citazione=cls.par1),
            proposta_valida(file="manuale.docx", campo="riservatezza",
                            valore="riservato", confidenza=0.4,
                            posizione="corpo, par. 3",
                            citazione="Parametri interni riservati",
                            sezione="corpo, par. 3"),
            proposta_valida(file="manuale.docx",
                            campo="forma_caratteristiche", valore="prosa",
                            confidenza=0.7, posizione="corpo, par. 99",
                            citazione="pressione massima di esercizio"),
        ])
        importa_bozze(cls.client, ("bozza_p100.json", dati))
        conn = db.get_connection()
        cls.lotto_id = conn.execute(
            "SELECT MAX(id) FROM lotti_validazione").fetchone()[0]
        cls.pid = {r["campo"]: r["id"] for r in conn.execute(
            "SELECT id, campo FROM proposte WHERE lotto_id = ?",
            (cls.lotto_id,))}
        conn.close()

    def _valida(self, pid, dati_form, follow=True):
        return self.client.post("/validazione/coda/proposte/%d/valida" % pid,
                                data=dati_form, follow_redirects=follow)

    def _riga_validazione(self, pid):
        conn = db.get_connection()
        riga = conn.execute("SELECT * FROM validazioni WHERE proposta_id = ?",
                            (pid,)).fetchone()
        conn.close()
        return riga

    def test_01_coda_raggruppata_per_cartella(self):
        r = self.client.get("/validazione/coda")
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn(self.CARTELLA, testo)
        self.assertIn("0.40", testo)  # confidenza minima in coda

    def test_02_revisione_ordinata_e_vista_affiancata(self):
        r = self.client.get("/validazione/coda/revisione?cartella=%s"
                            % self.CARTELLA.replace(" ", "%20"))
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        # Ordinamento per confidenza crescente: prima i dubbi
        posizioni = [testo.find("confidenza 0.40"),
                     testo.find("confidenza 0.70"),
                     testo.find("confidenza 0.90")]
        for pos in posizioni:
            self.assertGreater(pos, -1)
        self.assertEqual(posizioni, sorted(posizioni))
        # Estratto reale dal docx con citazione evidenziata
        self.assertIn("corpo, par. 1", testo)
        self.assertIn("<mark>%s</mark>" % self.par1, testo)
        # Il contesto attorno alla posizione e' visibile
        self.assertIn("pressione massima di esercizio", testo)
        # Fallback sulla posizione inventata (corpo, par. 99)
        self.assertIn("osizione non verificabile", testo)
        self.assertIn("corpo, par. 99", testo)
        # Azioni disponibili
        for azione in ("Conferma", "Correggi", "Caso nuovo"):
            self.assertIn(azione, testo)

    def test_03_conferma_riservato_con_avvertenza(self):
        r = self._valida(self.pid["riservatezza"],
                         {"esito": "confermata", "nota": "confine confermato",
                          "secondi": "7", "filtro_stato": "da_fare"})
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        # Avvertenza di retroazione verso il dizionario dello scanner
        self.assertIn("Possibile svista dello scanner", testo)
        self.assertIn("dizionario dei pattern", testo)
        riga = self._riga_validazione(self.pid["riservatezza"])
        self.assertEqual(riga["esito"], "confermata")
        self.assertEqual(riga["validatore"], "Carlo Verdini")
        self.assertEqual(riga["secondi_impiegati"], 7)
        self.assertEqual(riga["nota"], "confine confermato")
        self.assertTrue(riga["data"])
        # La proposta validata esce dalla coda Da fare
        r = self.client.get("/validazione/coda/revisione?cartella=%s"
                            % self.CARTELLA.replace(" ", "%20"))
        testo = r.get_data(as_text=True)
        self.assertIn("Da fare (2)", testo)
        self.assertIn("Validate (1)", testo)
        self.assertNotIn("confidenza 0.40", testo)
        # ...e compare nella vista Validate, con l'avvertenza persistente
        r = self.client.get(
            "/validazione/coda/revisione?cartella=%s&stato=validate"
            % self.CARTELLA.replace(" ", "%20"))
        testo = r.get_data(as_text=True)
        self.assertIn("confidenza 0.40", testo)
        self.assertIn("Possibile svista dello scanner", testo)

    def test_04_correggi_con_tassonomia(self):
        pid = self.pid["tipologia"]
        # Valore fuori tassonomia rifiutato
        r = self._valida(pid, {"esito": "corretta",
                               "valore_corretto": "valore_inventato",
                               "secondi": "5"})
        self.assertIn("tassonomia", r.get_data(as_text=True))
        self.assertIsNone(self._riga_validazione(pid))
        # Valore uguale al proposto rifiutato (si usa Conferma)
        r = self._valida(pid, {"esito": "corretta",
                               "valore_corretto": "manuale_installazione",
                               "secondi": "5"})
        self.assertIn("usare Conferma", r.get_data(as_text=True))
        self.assertIsNone(self._riga_validazione(pid))
        # Correzione valida
        r = self._valida(pid, {"esito": "corretta",
                               "valore_corretto": "manuale_manutenzione",
                               "nota": "titolo fuorviante",
                               "secondi": "12"})
        self.assertEqual(r.status_code, 200)
        riga = self._riga_validazione(pid)
        self.assertEqual(riga["esito"], "corretta")
        self.assertEqual(riga["valore_corretto"], "manuale_manutenzione")
        self.assertEqual(riga["validatore"], "Carlo Verdini")
        self.assertEqual(riga["secondi_impiegati"], 12)

    def test_05_caso_nuovo(self):
        pid = self.pid["forma_caratteristiche"]
        # Senza valore libero viene rifiutato
        r = self._valida(pid, {"esito": "caso_nuovo", "secondi": "3"})
        self.assertIn("caso nuovo", r.get_data(as_text=True).lower())
        self.assertIsNone(self._riga_validazione(pid))
        r = self._valida(pid, {"esito": "caso_nuovo",
                               "valore_nuovo": "prosa con tabelle allegate",
                               "nota": "serve una categoria dedicata",
                               "secondi": "21"})
        self.assertEqual(r.status_code, 200)
        riga = self._riga_validazione(pid)
        self.assertEqual(riga["esito"], "caso_nuovo")
        self.assertEqual(riga["valore_corretto"], "prosa con tabelle allegate")
        self.assertEqual(riga["secondi_impiegati"], 21)

    def test_06_coda_esaurita_e_lotto_completato(self):
        r = self.client.get("/validazione/coda/revisione?cartella=%s"
                            % self.CARTELLA.replace(" ", "%20"))
        testo = r.get_data(as_text=True)
        self.assertIn("Da fare (0)", testo)
        self.assertIn("Validate (3)", testo)
        self.assertIn("Tutte (3)", testo)
        self.assertIn("Nessuna proposta in questa vista", testo)
        r = self.client.get("/validazione/coda")
        self.assertIn("completata", r.get_data(as_text=True))
        conn = db.get_connection()
        stato = conn.execute(
            "SELECT stato FROM lotti_validazione WHERE id = ?",
            (self.lotto_id,)).fetchone()[0]
        conn.close()
        self.assertEqual(stato, "completato")

    def test_07_note_conoscenza_tacita(self):
        nota = ("Il responsabile ricorda a voce che le tarature del banco "
                "vengono sempre riviste prima della consegna.")
        r = self.client.post("/validazione/coda/note",
                             data={"cartella": self.CARTELLA, "testo": nota,
                                   "lotto_id": str(self.lotto_id),
                                   "filtro_stato": "tutte"},
                             follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("tarature del banco", r.get_data(as_text=True))
        conn = db.get_connection()
        riga = conn.execute(
            "SELECT * FROM note_conoscenza_tacita WHERE cartella_progetto = ?",
            (self.CARTELLA,)).fetchone()
        conn.close()
        self.assertIsNotNone(riga)
        self.assertEqual(riga["testo"], nota)
        self.assertEqual(riga["autore"], "Carlo Verdini")
        self.assertEqual(riga["lotto_id"], self.lotto_id)
        self.assertTrue(riga["data"])


class TestValidazioneMetriche(unittest.TestCase):
    """Modulo Validazione AI, punto 3: metriche su un lotto costruito ad
    hoc (mix di conferme e correzioni con confidenze diverse), export XLSX
    ed export JSON delle correzioni."""

    CARTELLA = "P-200 Metriche"

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})
        dati = bozza_valida(cartella=cls.CARTELLA, chiave_entita="P-200",
                            proposte=[
            proposta_valida(file="spec.docx", campo="tipologia",
                            valore="specifica_tecnica", confidenza=0.95,
                            citazione="Specifica tecnica del sistema"),
            proposta_valida(file="nota.docx", campo="tipologia",
                            valore="corrispondenza", confidenza=0.45,
                            citazione="Spett.le fornitore"),
            proposta_valida(file="spec.docx", campo="riservatezza",
                            valore="condivisibile", confidenza=0.8,
                            citazione="documento a diffusione libera"),
            proposta_valida(file="nota.docx", campo="riservatezza",
                            valore="misto", confidenza=0.6,
                            sezione="corpo, par. 4-6",
                            citazione="allegato con listino interno"),
            proposta_valida(file="spec.docx",
                            campo="forma_caratteristiche", valore="prosa",
                            confidenza=0.9,
                            citazione="le caratteristiche sono descritte"),
        ])
        importa_bozze(cls.client, ("bozza_metriche.json", dati))
        conn = db.get_connection()
        cls.lotto_id = conn.execute(
            "SELECT MAX(id) FROM lotti_validazione").fetchone()[0]
        righe = conn.execute(
            "SELECT id, campo, confidenza FROM proposte WHERE lotto_id = ?",
            (cls.lotto_id,)).fetchall()
        conn.close()
        cls.pid = {(r["campo"], round(r["confidenza"], 2)): r["id"]
                   for r in righe}
        # Esiti: conferme e correzioni con tempi noti
        cls.client.post("/validazione/coda/proposte/%d/valida"
                        % cls.pid[("tipologia", 0.95)],
                        data={"esito": "confermata", "secondi": "10"})
        cls.client.post("/validazione/coda/proposte/%d/valida"
                        % cls.pid[("tipologia", 0.45)],
                        data={"esito": "corretta",
                              "valore_corretto": "configurazione",
                              "nota": "in realtà è una configurazione",
                              "secondi": "30"})
        cls.client.post("/validazione/coda/proposte/%d/valida"
                        % cls.pid[("riservatezza", 0.8)],
                        data={"esito": "confermata", "secondi": "20"})
        cls.client.post("/validazione/coda/proposte/%d/valida"
                        % cls.pid[("riservatezza", 0.6)],
                        data={"esito": "corretta",
                              "valore_corretto": "condivisibile",
                              "nota": "listino già pubblico",
                              "secondi": "40"})
        cls.client.post("/validazione/coda/proposte/%d/valida"
                        % cls.pid[("forma_caratteristiche", 0.9)],
                        data={"esito": "caso_nuovo",
                              "valore_nuovo": "prosa con schemi",
                              "nota": "categoria da valutare",
                              "secondi": "50"})

    def test_01_metriche_calcolate(self):
        from core import validazione as val
        conn = db.get_connection()
        m = val.metriche(conn, self.lotto_id)
        conn.close()
        self.assertEqual(m["n_validate"], 5)
        # Accuratezza per campo: % confermate senza correzione
        self.assertEqual(m["per_campo"]["tipologia"],
                         {"n": 2, "confermate": 1, "accuratezza": 50.0})
        self.assertEqual(m["per_campo"]["riservatezza"],
                         {"n": 2, "confermate": 1, "accuratezza": 50.0})
        self.assertEqual(m["per_campo"]["forma_caratteristiche"],
                         {"n": 1, "confermate": 0, "accuratezza": 0.0})
        self.assertEqual(m["per_campo"]["versione_ufficiale"],
                         {"n": 0, "confermate": 0, "accuratezza": None})
        # Riservatezza separata: documento intero contro sezioni
        self.assertEqual(m["riservatezza"]["puri"],
                         {"n": 1, "confermate": 1, "accuratezza": 100.0})
        self.assertEqual(m["riservatezza"]["misti"],
                         {"n": 1, "confermate": 0, "accuratezza": 0.0})
        # Correlazione confidenza/esito per fasce
        fasce = {f["fascia"]: f for f in m["fasce"]}
        self.assertEqual(fasce["0-0.5"],
                         {"fascia": "0-0.5", "n": 1, "confermate": 0,
                          "accuratezza": 0.0})
        self.assertEqual(fasce["0.5-0.7"],
                         {"fascia": "0.5-0.7", "n": 1, "confermate": 0,
                          "accuratezza": 0.0})
        self.assertEqual(fasce["0.7-0.9"],
                         {"fascia": "0.7-0.9", "n": 1, "confermate": 1,
                          "accuratezza": 100.0})
        self.assertEqual(fasce["0.9-1"],
                         {"fascia": "0.9-1", "n": 2, "confermate": 1,
                          "accuratezza": 50.0})
        # Tempi mediani: per proposta e per cartella
        self.assertEqual(m["tempo_mediano_proposta"], 30)
        self.assertEqual(m["tempo_mediano_cartella"], 150)
        # Casi nuovi
        self.assertEqual(len(m["casi_nuovi"]), 1)
        self.assertEqual(m["casi_nuovi"][0]["valore_corretto"],
                         "prosa con schemi")

    def test_02_pagina_metriche(self):
        r = self.client.get("/validazione/metriche")
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn("Metriche complessive", testo)
        self.assertIn("50.0%", testo)
        self.assertIn("100.0%", testo)
        self.assertIn("Casi nuovi (1)", testo)
        r = self.client.get("/validazione/metriche?lotto=%d" % self.lotto_id)
        self.assertIn("Metriche del lotto %d" % self.lotto_id,
                      r.get_data(as_text=True))

    def test_03_export_xlsx(self):
        import openpyxl
        r = self.client.get("/validazione/metriche/export.xlsx?lotto=%d"
                            % self.lotto_id)
        self.assertEqual(r.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(r.data))
        self.assertEqual(wb.sheetnames,
                         ["Metriche", "Per lotto", "Casi nuovi"])
        righe = [[c.value for c in riga] for riga in wb["Metriche"].iter_rows()]
        self.assertIn(["tipologia", 2, 1, 50.0], righe)
        self.assertIn(["Documento intero (puri)", 1, 1, 100.0],
                      [r_[:4] for r_ in righe])
        self.assertIn(["0.9-1", 2, 1, 50.0], righe)
        self.assertIn(["Tempo mediano per proposta (s)", 30],
                      [r_[:2] for r_ in righe])
        self.assertIn(["Tempo mediano per cartella (s)", 150],
                      [r_[:2] for r_ in righe])
        # Foglio per lotto
        righe = [[c.value for c in riga]
                 for riga in wb["Per lotto"].iter_rows(min_row=2)]
        self.assertIn([self.lotto_id, "bozza_metriche.json", "tipologia",
                       2, 1, 50.0], righe)
        # Casi nuovi
        righe = [[c.value for c in riga]
                 for riga in wb["Casi nuovi"].iter_rows(min_row=2)]
        self.assertEqual(len(righe), 1)
        self.assertEqual(righe[0][2], "forma_caratteristiche")
        self.assertEqual(righe[0][4], "prosa con schemi")
        self.assertEqual(righe[0][6], "Carlo Verdini")

    def test_04_export_json_correzioni(self):
        r = self.client.get("/validazione/metriche/correzioni.json?lotto=%d"
                            % self.lotto_id)
        self.assertEqual(r.status_code, 200)
        self.assertIn("correzioni_validazione.json",
                      r.headers.get("Content-Disposition", ""))
        dati = json.loads(r.get_data(as_text=True))
        self.assertEqual(dati["formato"], "wikify-correzioni/1.0")
        correzioni = dati["correzioni"]
        # Due corrette e un caso nuovo
        self.assertEqual(len(correzioni), 3)
        per_campo = {c["campo"]: c for c in correzioni
                     if c["campo"] != "forma_caratteristiche"}
        c = per_campo["tipologia"]
        self.assertEqual(c["file"], "nota.docx")
        self.assertEqual(c["valore_proposto"], "corrispondenza")
        self.assertEqual(c["valore_corretto"], "configurazione")
        self.assertEqual(c["nota"], "in realtà è una configurazione")
        self.assertEqual(c["evidenza"]["citazione"], "Spett.le fornitore")
        self.assertTrue(c["evidenza"]["posizione"])
        c = per_campo["riservatezza"]
        self.assertEqual(c["valore_proposto"], "misto")
        self.assertEqual(c["valore_corretto"], "condivisibile")
        caso = [c_ for c_ in correzioni
                if c_["campo"] == "forma_caratteristiche"][0]
        self.assertEqual(caso["esito"], "caso_nuovo")
        self.assertEqual(caso["valore_corretto"], "prosa con schemi")


class TestMigrazioneV6(unittest.TestCase):
    """Modulo 4: retrocompatibilita' della migrazione V6 (sessioni di
    analisi). Un db V5 con lotti_validazione esistenti migra senza
    perdite; i lotti pregressi restano con sessione_id NULL."""

    def _prepara_db_v5(self, cartella):
        percorso = os.path.join(cartella, "archivio_smart.db")
        conn = sqlite3.connect(percorso)
        for schema in db.MIGRAZIONI[:5]:
            conn.executescript(schema)
        conn.execute("PRAGMA user_version = 5")
        conn.execute("INSERT INTO utenti (nome, pin, attivo, data_creazione) "
                     "VALUES ('Carlo', 'aa$bb', 1, '01/06/2026 09:00')")
        conn.execute(
            "INSERT INTO lotti_validazione (data_import, nome_file_origine, "
            "formato, cartella_progetto, n_accettate, n_scartate, stato) "
            "VALUES ('01/06/2026 09:00', 'bozza.json', 'wikify-bozza/1.0', "
            "'P-001', 1, 0, 'importato')")
        conn.execute(
            "INSERT INTO proposte (lotto_id, cartella_progetto, file, "
            "sezione, campo, valore_proposto, confidenza, "
            "evidenza_posizione, evidenza_citazione) VALUES (1, 'P-001', "
            "'doc.docx', 'intero documento', 'tipologia', "
            "'manuale_installazione', 0.9, 'corpo, par. 1', 'testo')")
        conn.commit()
        conn.close()

    def test_01_migrazione_da_v5_con_lotti_esistenti(self):
        cartella = usa_dati_temporanei()
        self._prepara_db_v5(cartella)
        conn = db.get_connection()
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 5)
        prima = conn.execute(
            "SELECT COUNT(*) FROM lotti_validazione").fetchone()[0]
        conn.close()

        db.init_db()  # applica le migrazioni V6 e V7

        conn = db.get_connection()
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 7)
        tabelle = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("sessioni_analisi", tabelle)
        self.assertIn("sessioni_analisi_letture", tabelle)
        self.assertIn("documenti", tabelle)
        self.assertIn("regole_tipologia", tabelle)
        dopo = conn.execute(
            "SELECT COUNT(*) FROM lotti_validazione").fetchone()[0]
        self.assertEqual(prima, dopo)  # nessuna perdita di dati
        riga = conn.execute(
            "SELECT sessione_id FROM lotti_validazione WHERE id = 1"
        ).fetchone()
        self.assertIsNone(riga["sessione_id"])
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM sessioni_analisi"
                        ).fetchone()[0], 0)
        conn.close()


class TestMigrazioneV7(unittest.TestCase):
    """Modulo 5: retrocompatibilita' della migrazione V7 (archivio logico).
    Un db V6 con inventario, catalogo e triage esistenti migra senza
    perdite; le tabelle nuove (documenti, regole_tipologia) nascono vuote."""

    def _prepara_db_v6(self, cartella):
        percorso = os.path.join(cartella, "archivio_smart.db")
        conn = sqlite3.connect(percorso)
        for schema in db.MIGRAZIONI[:6]:
            conn.executescript(schema)
        conn.execute("PRAGMA user_version = 6")
        conn.execute("INSERT INTO utenti (nome, pin, attivo, data_creazione) "
                     "VALUES ('Carlo', 'aa$bb', 1, '01/06/2026 09:00')")
        conn.execute("INSERT INTO impostazioni (chiave, valore) "
                     "VALUES ('radice_archivio', '/vecchio')")
        conn.execute("INSERT INTO inventario_file (percorso_rel, "
                     "cartella_progetto, estensione, stato) "
                     "VALUES ('P-001/doc.txt', 'P-001', '.txt', 'presente')")
        conn.execute("INSERT INTO tipi_entita (nome, criterio_json, "
                     "data_creazione, stato) VALUES ('Progetto', '{}', "
                     "'01/06/2026 09:00', 'attivo')")
        conn.execute("INSERT INTO entita (tipo_id, chiave, cartella_origine, "
                     "stato) VALUES (1, 'P-001', 'P-001', 'attiva')")
        conn.commit()
        conn.close()

    def test_01_migrazione_da_v6_con_dati_reali(self):
        cartella = usa_dati_temporanei()
        self._prepara_db_v6(cartella)
        conn = db.get_connection()
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 6)
        controllate = ("utenti", "impostazioni", "inventario_file",
                       "tipi_entita", "entita")
        prima = {t: conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                 for t in controllate}
        conn.close()

        db.init_db()  # applica la sola migrazione V7

        conn = db.get_connection()
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 7)
        tabelle = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("documenti", tabelle)
        self.assertIn("regole_tipologia", tabelle)
        dopo = {t: conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                for t in controllate}
        self.assertEqual(prima, dopo)  # nessuna perdita di dati
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM documenti").fetchone()[0], 0)
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM regole_tipologia"
                        ).fetchone()[0], 0)
        conn.close()


class TestImpostazioniAnalisi(unittest.TestCase):
    """Modulo 4: pagina Impostazioni analisi, salvataggio e rilettura,
    validazioni e sidebar aggiornata."""

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})

    def test_01_pagina_default_200(self):
        r = self.client.get("/validazione/impostazioni")
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn("claude-haiku", testo)
        self.assertIn("claude-sonnet", testo)
        self.assertIn("Impostazioni analisi", testo)

    def test_02_sidebar_aggiornata(self):
        testo = self.client.get("/validazione/impostazioni").get_data(
            as_text=True)
        inizio = testo.find("<aside")
        fine = testo.find("</aside>")
        sidebar = testo[inizio:fine]
        self.assertIn("Impostazioni analisi", sidebar)
        self.assertRegex(
            sidebar,
            r'class="voce-menu sotto-voce attiva\s*" '
            r'href="/validazione/impostazioni"')

    def test_03_salvataggio_e_rilettura(self):
        r = self.client.post("/validazione/impostazioni", data={
            "modello_primario": "claude-opus",
            "modello_rinforzo": "claude-sonnet",
            "soglia_rinforzo": "0.6", "rinforzo_obbligatorio": "on",
            "ambito": "campione", "campione_n": "3", "campione_seed": "42",
            "prezzo_modello_0": "claude-haiku", "prezzo_in_0": "1",
            "prezzo_out_0": "2",
        }, follow_redirects=True)
        self.assertIn("salvate", r.get_data(as_text=True).lower())
        conn = db.get_connection()
        imp = ana.leggi_impostazioni(conn)
        conn.close()
        self.assertEqual(imp["modello_primario"], "claude-opus")
        self.assertEqual(imp["modello_rinforzo"], "claude-sonnet")
        self.assertEqual(imp["soglia_rinforzo"], 0.6)
        self.assertTrue(imp["rinforzo_obbligatorio"])
        self.assertEqual(imp["ambito"], "campione")
        self.assertEqual(imp["campione_n"], 3)
        self.assertEqual(imp["campione_seed"], 42)
        self.assertEqual(imp["prezzi"], [
            {"modello": "claude-haiku", "prezzo_in": 1.0, "prezzo_out": 2.0}])
        # I valori compaiono precompilati alla rilettura della pagina
        r = self.client.get("/validazione/impostazioni")
        testo = r.get_data(as_text=True)
        self.assertIn('value="claude-opus"', testo)
        self.assertIn('value="42"', testo)

    def test_04_soglia_fuori_range_rifiutata(self):
        r = self.client.post("/validazione/impostazioni", data={
            "modello_primario": "claude-haiku",
            "modello_rinforzo": "claude-sonnet",
            "soglia_rinforzo": "1.5", "ambito": "campione",
            "campione_n": "3",
        }, follow_redirects=True)
        self.assertIn("tra 0 e 1", r.get_data(as_text=True))
        conn = db.get_connection()
        imp = ana.leggi_impostazioni(conn)
        conn.close()
        self.assertEqual(imp["soglia_rinforzo"], 0.6)  # invariata

    def test_05_numero_progetti_campione_minimo_1(self):
        r = self.client.post("/validazione/impostazioni", data={
            "modello_primario": "claude-haiku",
            "modello_rinforzo": "claude-sonnet",
            "soglia_rinforzo": "0.7", "ambito": "campione",
            "campione_n": "0",
        }, follow_redirects=True)
        self.assertIn("almeno 1", r.get_data(as_text=True))
        conn = db.get_connection()
        imp = ana.leggi_impostazioni(conn)
        conn.close()
        self.assertEqual(imp["campione_n"], 3)  # invariato

    def test_06_ambito_archivio_intero_non_richiede_campione(self):
        r = self.client.post("/validazione/impostazioni", data={
            "modello_primario": "claude-haiku",
            "modello_rinforzo": "claude-sonnet",
            "soglia_rinforzo": "0.7", "ambito": "archivio_intero",
            "campione_n": "0",
        }, follow_redirects=True)
        self.assertIn("salvate", r.get_data(as_text=True).lower())
        conn = db.get_connection()
        imp = ana.leggi_impostazioni(conn)
        conn.close()
        self.assertEqual(imp["ambito"], "archivio_intero")


class TestMCPConnettore(unittest.TestCase):
    """Modulo 4: connettore MCP, sessioni di analisi e KPI di esito. Le
    funzioni core sono chiamate direttamente (stessa logica dietro gli
    strumenti MCP), senza passare dal trasporto stdio."""

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})
        cls.radice = os.path.join(tempfile.mkdtemp(prefix="arch_mcp_"),
                                  "archivio")
        os.makedirs(cls.radice)
        cls.cartelle = ["P-001 Impianto Alfa", "P-002 Impianto Beta",
                        "P-003 Impianto Gamma"]
        cls.testi = {}
        for nome in cls.cartelle:
            sotto = os.path.join(cls.radice, nome)
            os.makedirs(sotto, exist_ok=True)
            testo = ("Manuale di installazione %s. Contenuto tecnico "
                     "di prova per il connettore MCP." % nome)
            crea_docx_minimo(os.path.join(sotto, "manuale.docx"), [testo])
            cls.testi[nome] = testo
        cls.client.post("/inventario/imposta-radice",
                        data={"radice": cls.radice})

        conn = db.get_connection()
        cur = conn.execute(
            "INSERT INTO scansioni (data, radice, etichetta, stato) "
            "VALUES ('01/07/2026 10:00', ?, 'mcp', 'completata')",
            (cls.radice,))
        cls.sid = cur.lastrowid
        for nome in cls.cartelle:
            f = "%s/manuale.docx" % nome
            conn.execute(
                "INSERT INTO file_analizzati (scansione_id, file, formato, "
                "totale) VALUES (?, ?, '.docx', 1)", (cls.sid, f))
            conn.execute(
                "INSERT INTO triage_file (scansione_id, file, qualifica, "
                "validatore, verificato) VALUES (?, ?, 'Condivisibile', "
                "'Carlo', 1)", (cls.sid, f))
        # Un file riservato, fuori dal perimetro condivisibile
        conn.execute(
            "INSERT INTO file_analizzati (scansione_id, file, formato, "
            "totale) VALUES (?, 'P-001 Impianto Alfa/segreto.docx', "
            "'.docx', 1)", (cls.sid,))
        conn.execute(
            "INSERT INTO triage_file (scansione_id, file, qualifica, "
            "validatore, verificato) VALUES (?, "
            "'P-001 Impianto Alfa/segreto.docx', 'Riservato', 'Carlo', 1)",
            (cls.sid,))
        conn.commit()
        conn.close()

    def _reimposta_impostazioni(self, **kwargs):
        conn = db.get_connection()
        for chiave, valore in kwargs.items():
            db.set_impostazione(conn, ana.CHIAVI[chiave], str(valore))
        conn.close()

    def test_01_cartelle_condivisibili(self):
        conn = db.get_connection()
        cartelle = ana.cartelle_condivisibili(conn)
        conn.close()
        self.assertEqual(sorted(cartelle.keys()), sorted(self.cartelle))
        self.assertEqual(cartelle["P-001 Impianto Alfa"],
                         ["P-001 Impianto Alfa/manuale.docx"])

    def test_02_ottieni_incarico_campione_n1_ripetibile(self):
        self._reimposta_impostazioni(ambito="campione", campione_n="1",
                                     campione_seed="777")
        conn = db.get_connection()
        sessione, cartelle, creata = ana.apri_sessione(conn)
        conn.close()
        self.assertTrue(creata)
        self.assertEqual(len(cartelle), 1)
        prima_scelta = list(cartelle.keys())[0]

        # Chiude e riapre con lo stesso seed: stessa cartella selezionata
        conn = db.get_connection()
        ana.stato_sessione(conn, chiudi=True)
        conn.close()
        conn = db.get_connection()
        sessione2, cartelle2, creata2 = ana.apri_sessione(conn)
        conn.close()
        self.assertTrue(creata2)
        self.assertEqual(list(cartelle2.keys()), [prima_scelta])
        # richiude per non interferire con i test successivi
        conn = db.get_connection()
        ana.stato_sessione(conn, chiudi=True)
        conn.close()

    def test_03_ottieni_incarico_archivio_intero(self):
        self._reimposta_impostazioni(ambito="archivio_intero")
        conn = db.get_connection()
        sessione, cartelle, creata = ana.apri_sessione(conn)
        conn.close()
        self.assertTrue(creata)
        self.assertEqual(sorted(cartelle.keys()), sorted(self.cartelle))
        type(self).sessione_id = sessione["id"]

    def test_04_sessione_riaperta_se_gia_esistente(self):
        conn = db.get_connection()
        sessione, _cartelle, creata = ana.apri_sessione(conn)
        conn.close()
        self.assertFalse(creata)
        self.assertEqual(sessione["id"], self.sessione_id)

    def test_05_leggi_file_condivisibile(self):
        conn = db.get_connection()
        risultato, errore = ana.leggi_file(
            conn, self.radice, "P-001 Impianto Alfa/manuale.docx")
        conn.close()
        self.assertIsNone(errore)
        self.assertIn(self.testi["P-001 Impianto Alfa"],
                     "\n".join(t for _p, t in risultato["unita"]))
        self.assertGreater(risultato["n_caratteri"], 0)
        type(self).caratteri_letti_attesi = risultato["n_caratteri"]

    def test_06_leggi_file_fuori_perimetro_rifiutato(self):
        conn = db.get_connection()
        risultato, errore = ana.leggi_file(
            conn, self.radice, "P-001 Impianto Alfa/segreto.docx")
        conn.close()
        self.assertIsNone(risultato)
        self.assertIn("perimetro", errore.lower())

    def test_07_caratteri_registrati_una_volta_sola(self):
        conn = db.get_connection()
        sessione = ana.sessione_aperta(conn)
        prima = sessione["caratteri_letti"]
        # Rilettura dello stesso file: non deve raddoppiare i caratteri
        ana.leggi_file(conn, self.radice,
                       "P-001 Impianto Alfa/manuale.docx")
        sessione2 = ana.sessione_aperta(conn)
        conn.close()
        self.assertEqual(sessione2["caratteri_letti"], prima)
        self.assertEqual(prima, self.caratteri_letti_attesi)

    def test_08_consegna_bozza_valida(self):
        conn = db.get_connection()
        dati = bozza_valida(cartella="P-001 Impianto Alfa", proposte=[
            proposta_valida(
                file="manuale.docx", campo="tipologia",
                valore="manuale_installazione", confidenza=0.9,
                citazione=self.testi["P-001 Impianto Alfa"][:50]),
        ])
        lotto_id, esito = ana.consegna_bozza(conn, dati)
        conn.close()
        self.assertIsNotNone(lotto_id)
        self.assertEqual(esito["n_accettate"], 1)
        conn = db.get_connection()
        riga = conn.execute(
            "SELECT sessione_id FROM lotti_validazione WHERE id = ?",
            (lotto_id,)).fetchone()
        sessione = ana.sessione_aperta(conn)
        conn.close()
        self.assertEqual(riga["sessione_id"], self.sessione_id)
        self.assertGreater(sessione["caratteri_prodotti"], 0)
        type(self).lotto_valido_id = lotto_id

    def test_09_consegna_bozza_con_scarti_come_import_manuale(self):
        conn = db.get_connection()
        dati = bozza_valida(cartella="P-002 Impianto Beta", proposte=[
            proposta_valida(file="manuale.docx", campo="tipologia",
                            valore="manuale_installazione", confidenza=0.8,
                            citazione="testo valido di evidenza"),
            proposta_valida(file="manuale.docx", campo="colore",
                            valore="rosso"),
            proposta_valida(file="manuale.docx", citazione=""),
        ])
        lotto_id, esito = ana.consegna_bozza(conn, dati)
        conn.close()
        self.assertIsNotNone(lotto_id)
        self.assertEqual(esito["n_accettate"], 1)
        self.assertEqual(esito["n_scartate"], 2)
        self.assertEqual(esito["conteggi"]["campo_non_previsto"], 1)
        self.assertEqual(esito["conteggi"]["senza_evidenza"], 1)

    def test_10_consegna_bozza_senza_sessione_aperta_rifiutata(self):
        conn = db.get_connection()
        ana.stato_sessione(conn, chiudi=True)
        dati = bozza_valida(cartella="P-003 Impianto Gamma",
                            proposte=[proposta_valida()])
        lotto_id, errore = ana.consegna_bozza(conn, dati)
        conn.close()
        self.assertIsNone(lotto_id)
        self.assertIn("sessione", errore.lower())
        # Riapre la sessione (stesso ambito/impostazioni) per i test successivi
        conn = db.get_connection()
        sessione, _cartelle, creata = ana.apri_sessione(conn)
        conn.close()
        self.assertTrue(creata)
        type(self).sessione_id = sessione["id"]
        # Ricostituisce lettura e lotto sulla nuova sessione per il resto
        # della suite (la sessione precedente, con la sua lettura
        # registrata, e' stata chiusa e non e' piu' quella corrente).
        conn = db.get_connection()
        ana.leggi_file(conn, self.radice,
                       "P-001 Impianto Alfa/manuale.docx")
        conn.close()
        conn = db.get_connection()
        _lid1, _e1 = ana.consegna_bozza(conn, bozza_valida(
            cartella="P-001 Impianto Alfa", proposte=[proposta_valida(
                file="manuale.docx", campo="tipologia",
                valore="manuale_installazione", confidenza=0.9,
                citazione=self.testi["P-001 Impianto Alfa"][:50])]))
        conn.close()
        type(self).lotto_valido_id = _lid1

    def test_11_stato_sessione_e_chiusura(self):
        conn = db.get_connection()
        stato = ana.stato_sessione(conn)
        conn.close()
        self.assertIn("P-001 Impianto Alfa", stato["cartelle_completate"])
        self.assertIn("P-003 Impianto Gamma", stato["cartelle_rimanenti"])
        conn = db.get_connection()
        stato_chiuso = ana.stato_sessione(conn, chiudi=True)
        conn.close()
        self.assertEqual(stato_chiuso["sessione"]["stato"], "chiusa")
        self.assertTrue(stato_chiuso["sessione"]["data_chiusura"])
        conn = db.get_connection()
        self.assertIsNone(ana.sessione_aperta(conn))
        conn.close()

    def test_12_kpi_sessione(self):
        conn = db.get_connection()
        sessione = conn.execute(
            "SELECT * FROM sessioni_analisi WHERE id = ?",
            (self.sessione_id,)).fetchone()
        # Prezzi noti per il calcolo atteso del costo
        db.set_impostazione(conn, ana.CHIAVI["prezzi_json"], json.dumps([
            {"modello": sessione["modello_primario"], "prezzo_in": 10.0,
             "prezzo_out": 20.0}]))
        kpi = ana.kpi_sessione(conn, sessione)
        conn.close()
        self.assertEqual(kpi["n_progetti_assegnati"], 3)
        self.assertGreaterEqual(kpi["n_progetti_completati"], 1)
        self.assertEqual(kpi["n_file_perimetro"], 3)
        self.assertEqual(kpi["n_file_letti"], 1)
        self.assertGreaterEqual(kpi["proposte_per_campo"]["tipologia"], 1)
        token_in = (sessione["caratteri_letti"] or 0) / 4.0
        token_out = (sessione["caratteri_prodotti"] or 0) / 4.0
        atteso = round(token_in / 1_000_000.0 * 10.0
                       + token_out / 1_000_000.0 * 20.0, 4)
        self.assertEqual(kpi["costo_stimato"], atteso)
        self.assertEqual(kpi["token_stimati"], round(token_in + token_out))
        self.assertIsNotNone(kpi["durata_secondi"])

    def test_13_pagina_metriche_mostra_sessione(self):
        r = self.client.get("/validazione/metriche")
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn("Sessioni di analisi", testo)
        self.assertIn(str(self.sessione_id), testo)

    def test_14_filtro_accuratezza_per_sessione(self):
        conn = db.get_connection()
        proposta = conn.execute(
            "SELECT id FROM proposte WHERE lotto_id = ?",
            (self.lotto_valido_id,)).fetchone()
        conn.close()
        self.client.post(
            "/validazione/coda/proposte/%d/valida" % proposta["id"],
            data={"esito": "confermata", "secondi": "5"})
        r = self.client.get(
            "/validazione/metriche?sessione=%d" % self.sessione_id)
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn("Metriche della sessione %d" % self.sessione_id, testo)


class TestServerMCP(unittest.TestCase):
    """Modulo 4, punto 7: il server MCP si avvia (import senza errori),
    espone gli strumenti attesi (verificati via API FastMCP, senza
    trasporto stdio) e le sue funzioni richiamano correttamente core."""

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        cartella_server = os.path.join(BASE, "mcp_server")
        if cartella_server not in sys.path:
            sys.path.insert(0, cartella_server)
        import server as server_mod
        cls.server = server_mod
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})

    def test_01_import_e_registrazione_strumenti(self):
        import asyncio
        tools = asyncio.run(self.server.mcp.list_tools())
        nomi = {t.name for t in tools}
        self.assertEqual(nomi, {"ottieni_istruzioni", "ottieni_incarico",
                                "leggi_file", "consegna_bozza",
                                "ottieni_correzioni", "stato_sessione"})

    def test_02_ottieni_istruzioni_diretto(self):
        esito = self.server.ottieni_istruzioni()
        self.assertIn("istruzioni_agente", esito)
        self.assertIn("formato_bozze", esito)
        self.assertEqual(esito["formato_atteso"], "wikify-bozza/1.0")
        self.assertIn("impostazioni_analisi", esito)
        self.assertIn("modello_primario", esito["impostazioni_analisi"])

    def test_03_stato_sessione_senza_sessione_aperta(self):
        esito = self.server.stato_sessione()
        self.assertIn("errore", esito)

    def test_04_flusso_completo_diretto(self):
        radice = os.path.join(tempfile.mkdtemp(prefix="arch_srv_"),
                              "archivio")
        os.makedirs(os.path.join(radice, "P-900 Prova"))
        testo_atteso = "Contenuto di prova per il server MCP diretto."
        crea_docx_minimo(
            os.path.join(radice, "P-900 Prova", "manuale.docx"),
            [testo_atteso])
        conn = db.get_connection()
        cur = conn.execute(
            "INSERT INTO scansioni (data, radice, etichetta, stato) "
            "VALUES ('01/07/2026 10:00', ?, 'srv', 'completata')", (radice,))
        sid = cur.lastrowid
        conn.execute(
            "INSERT INTO file_analizzati (scansione_id, file, formato, "
            "totale) VALUES (?, 'P-900 Prova/manuale.docx', '.docx', 1)",
            (sid,))
        conn.execute(
            "INSERT INTO triage_file (scansione_id, file, qualifica, "
            "validatore, verificato) VALUES (?, "
            "'P-900 Prova/manuale.docx', 'Condivisibile', 'Carlo', 1)",
            (sid,))
        conn.commit()
        conn.close()
        self.client.post("/inventario/imposta-radice",
                         data={"radice": radice})

        esito = self.server.ottieni_incarico()
        self.assertIn("P-900 Prova", esito["cartelle_assegnate"])

        letto = self.server.leggi_file("P-900 Prova/manuale.docx")
        self.assertNotIn("errore", letto)
        self.assertIn(testo_atteso,
                     "\n".join(u["testo"] for u in letto["unita"]))

        rifiutato = self.server.leggi_file("P-900 Prova/inesistente.docx")
        self.assertIn("errore", rifiutato)

        bozza = bozza_valida(cartella="P-900 Prova", proposte=[
            proposta_valida(file="manuale.docx", campo="tipologia",
                            valore="manuale_installazione", confidenza=0.85,
                            citazione=testo_atteso)])
        esito_bozza = self.server.consegna_bozza(json.dumps(bozza))
        self.assertIn("lotto_id", esito_bozza)
        self.assertEqual(esito_bozza["riepilogo"]["n_accettate"], 1)

        correzioni = self.server.ottieni_correzioni()
        self.assertEqual(correzioni["formato"], "wikify-correzioni/1.0")

        stato = self.server.stato_sessione(chiudi=True)
        self.assertEqual(stato["stato"], "chiusa")


class TestManutenzioneReset(unittest.TestCase):
    """Reset dell'archivio: cancellazione dei dati derivati dall'analisi
    dietro doppia conferma (parola RESET e PIN), con dizionario, utenti e
    impostazioni conservati (a parte le chiavi di stato dell'inventario)."""

    PIN_CARLO = "1234"

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": cls.PIN_CARLO})

    def _popola_tutte_le_aree(self):
        """Popola una riga in ciascuna delle tabelle da svuotare, piu'
        dizionario (regola personalizzata), un secondo utente e
        impostazioni (radice e chiave di analisi)."""
        conn = db.get_connection()
        adesso = "01/07/2026 10:00"

        conn.execute(
            "INSERT INTO regole (codice, categoria, pattern, creata, "
            "modificata) VALUES ('CUSTOM1', 'personalizzata', "
            "'riservato personale', ?, ?)", (adesso, adesso))

        from modules.utenti import hash_pin
        conn.execute(
            "INSERT INTO utenti (nome, pin, attivo, data_creazione) "
            "VALUES ('Maria Rossi', ?, 1, ?)", (hash_pin("5678"), adesso))

        db.set_impostazione(conn, "radice_archivio", "/tmp/archivio_prova_reset")
        db.set_impostazione(conn, "analisi_modello_primario", "claude-haiku")
        db.set_impostazione(conn, "inventario_ultimo_check", str(time.time()))
        db.set_impostazione(conn, "inventario_nuovi_ultimo_check", "0")

        conn.execute(
            "INSERT INTO inventario_file (percorso_rel, cartella_progetto, "
            "estensione, dimensione, data_modifica, data_rilevazione, "
            "stato) VALUES ('P-001/doc.txt', 'P-001', '.txt', 10, ?, ?, "
            "'presente')", (adesso, adesso))
        conn.execute(
            "INSERT INTO inventario_esecuzioni (data, tipo, n_nuovi, "
            "n_scomparsi, n_totale, durata) VALUES (?, 'completo', 1, 0, "
            "1, 0.5)", (adesso,))

        cur = conn.execute(
            "INSERT INTO scansioni (data, radice, etichetta, n_regole, "
            "contesto, durata, stato) VALUES (?, "
            "'/tmp/archivio_prova_reset', 'prova reset', 1, 80, 1.0, "
            "'completata')", (adesso,))
        sid = cur.lastrowid
        conn.execute(
            "INSERT INTO segnalazioni (scansione_id, file, posizione, "
            "regola_id, categoria, severita, testo_match, contesto) "
            "VALUES (?, 'P-001/doc.txt', 'riga 1', 'CUSTOM1', "
            "'personalizzata', 'alta', 'riservato', 'contesto')", (sid,))
        conn.execute(
            "INSERT INTO file_analizzati (scansione_id, file, formato, "
            "unita_testo, n_alta, n_media, n_bassa, totale) VALUES "
            "(?, 'P-001/doc.txt', '.txt', 1, 1, 0, 0, 1)", (sid,))
        conn.execute(
            "INSERT INTO non_analizzati (scansione_id, file, motivo) "
            "VALUES (?, 'P-001/binario.bin', 'formato non supportato')",
            (sid,))
        conn.execute(
            "INSERT INTO triage (scansione_id, file, regola_id, "
            "qualifica, validatore, data) VALUES (?, 'P-001/doc.txt', "
            "'CUSTOM1', 'Riservato', 'Carlo Verdini', ?)", (sid, adesso))
        conn.execute(
            "INSERT INTO triage_file (scansione_id, file, qualifica, "
            "validatore, data, verificato) VALUES (?, 'P-001/doc.txt', "
            "'Riservato', 'Carlo Verdini', ?, 1)", (sid, adesso))

        cur = conn.execute(
            "INSERT INTO tipi_entita (nome, criterio_json, "
            "data_creazione, stato) VALUES ('Progetto', '{}', ?, "
            "'attivo')", (adesso,))
        tid = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO entita (tipo_id, chiave, cartella_origine, "
            "stato, data_creazione) VALUES (?, 'P-001', 'P-001', "
            "'attiva', ?)", (tid, adesso))
        eid = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO importazioni (data, nome_file, tipo_entita_id, "
            "mappatura_json, n_righe, n_valori, n_scartate, utente, "
            "stato) VALUES (?, 'dati.csv', ?, '{}', 1, 1, 0, "
            "'Carlo Verdini', 'confermata')", (adesso, tid))
        iid = cur.lastrowid
        conn.execute(
            "INSERT INTO attributi_entita (entita_id, nome_attributo, "
            "valore, importazione_id, data) VALUES (?, 'articolo', "
            "'ART-1', ?, ?)", (eid, iid, adesso))
        conn.execute(
            "INSERT INTO anomalie_import (importazione_id, tipo, "
            "riferimento, dettaglio) VALUES (?, 'chiave_senza_entita', "
            "'P-9', 'dettaglio')", (iid,))

        cur = conn.execute(
            "INSERT INTO lotti_validazione (data_import, "
            "nome_file_origine, formato, cartella_progetto, "
            "chiave_entita, n_accettate, n_scartate, n_troncate, stato) "
            "VALUES (?, 'bozza.json', 'json', 'P-001', 'P-001', 1, 0, 0, "
            "'importato')", (adesso,))
        lid = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO proposte (lotto_id, cartella_progetto, "
            "chiave_entita, file, sezione, campo, valore_proposto, "
            "confidenza, evidenza_posizione, evidenza_citazione) VALUES "
            "(?, 'P-001', 'P-001', 'doc.txt', 'intero documento', "
            "'tipologia', 'manuale', 0.9, 'par. 1', 'citazione di prova')",
            (lid,))
        pid = cur.lastrowid
        conn.execute(
            "INSERT INTO validazioni (proposta_id, esito, "
            "valore_corretto, nota, validatore, data, secondi_impiegati) "
            "VALUES (?, 'confermata', '', '', 'Carlo Verdini', ?, 5)",
            (pid, adesso))
        conn.execute(
            "INSERT INTO note_conoscenza_tacita (lotto_id, "
            "cartella_progetto, testo, autore, data) VALUES (?, "
            "'P-001', 'nota di prova', 'Carlo Verdini', ?)", (lid, adesso))

        cur = conn.execute(
            "INSERT INTO sessioni_analisi (data_avvio, stato, ambito, "
            "n_progetti_richiesti, seed, modello_primario, "
            "modello_rinforzo, soglia_rinforzo, scansione_id, "
            "cartelle_assegnate_json, caratteri_letti, "
            "caratteri_prodotti) VALUES (?, 'aperta', 'campione', 1, 42, "
            "'claude-haiku', 'claude-sonnet', 0.7, ?, '{}', 100, 50)",
            (adesso, sid))
        sess_id = cur.lastrowid
        conn.execute(
            "INSERT INTO sessioni_analisi_letture (sessione_id, "
            "percorso_rel, caratteri, data) VALUES (?, 'P-001/doc.txt', "
            "100, ?)", (sess_id, adesso))
        conn.commit()
        conn.close()

        # Cartella import_temp con un file temporaneo del wizard
        from core.catalogo import cartella_temporanea
        cartella = cartella_temporanea()
        with open(os.path.join(str(cartella), "wizard_temp.csv"), "w",
                  encoding="utf-8") as f:
            f.write("a,b\n1,2\n")

    def test_01_pagina_richiede_login(self):
        self.client.get("/utenti/uscita")
        r = self.client.get("/manutenzione/reset", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/utenti/accesso", r.headers["Location"])
        # Nuovo accesso per il resto della suite
        r = self.client.post("/utenti/accesso",
                             data={"utente": "1", "pin": self.PIN_CARLO},
                             follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        r = self.client.get("/manutenzione/reset")
        self.assertEqual(r.status_code, 200)

    def test_02_card_presente_in_dashboard(self):
        r = self.client.get("/")
        testo = r.get_data(as_text=True)
        self.assertIn("Manutenzione", testo)
        self.assertIn("Reset archivio", testo)
        self.assertIn("/manutenzione/reset", testo)

    def test_03_parola_sbagliata_rifiutata(self):
        self._popola_tutte_le_aree()
        conn = db.get_connection()
        prima = conn.execute("SELECT COUNT(*) FROM scansioni").fetchone()[0]
        conn.close()
        r = self.client.post("/manutenzione/reset",
                             data={"conferma": "resettare", "pin": self.PIN_CARLO})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Parola di conferma non corretta",
                     r.get_data(as_text=True))
        conn = db.get_connection()
        dopo = conn.execute("SELECT COUNT(*) FROM scansioni").fetchone()[0]
        conn.close()
        self.assertEqual(prima, dopo, "nessuna cancellazione deve avvenire")

    def test_04_pin_sbagliato_rifiutato(self):
        conn = db.get_connection()
        prima = conn.execute("SELECT COUNT(*) FROM scansioni").fetchone()[0]
        conn.close()
        r = self.client.post("/manutenzione/reset",
                             data={"conferma": "RESET", "pin": "0000"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("PIN non corretto", r.get_data(as_text=True))
        conn = db.get_connection()
        dopo = conn.execute("SELECT COUNT(*) FROM scansioni").fetchone()[0]
        conn.close()
        self.assertEqual(prima, dopo, "nessuna cancellazione deve avvenire")

    def test_05_reset_esegue_e_svuota(self):
        r = self.client.post("/manutenzione/reset",
                             data={"conferma": "RESET", "pin": self.PIN_CARLO},
                             follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        # Jinja esegue l'escape dell'apostrofo (&#39;) nel messaggio flash
        self.assertIn("archivio completato", testo)
        self.assertIn("19 righe eliminate", testo)

        conn = db.get_connection()
        for tabella in manut.TABELLE_RESET:
            n = conn.execute("SELECT COUNT(*) FROM %s" % tabella).fetchone()[0]
            self.assertEqual(n, 0, "tabella %s non svuotata" % tabella)

        # Dizionario, utenti e impostazioni conservati
        self.assertGreater(
            conn.execute("SELECT COUNT(*) FROM regole WHERE codice = "
                        "'CUSTOM1'").fetchone()[0], 0)
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM utenti").fetchone()[0], 2)
        self.assertEqual(
            db.get_impostazione(conn, "radice_archivio", ""),
            "/tmp/archivio_prova_reset")
        self.assertEqual(
            db.get_impostazione(conn, "analisi_modello_primario", ""),
            "claude-haiku")
        # Le chiavi di stato dell'inventario sono rimosse
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM impostazioni WHERE chiave "
                        "= 'inventario_ultimo_check'").fetchone()[0], 0)
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM impostazioni WHERE chiave "
                        "= 'inventario_nuovi_ultimo_check'").fetchone()[0], 0)
        conn.close()

        # import_temp svuotata (ma esistente)
        cartella = db.DATA_DIR / "import_temp"
        self.assertTrue(cartella.is_dir())
        self.assertEqual(list(cartella.iterdir()), [])


class TestArchivioRegoleTipologia(unittest.TestCase):
    """Modulo 5: regole di tipologia, builder guidato senza espressioni
    regolari, prova live sui nomi reali, priorità, attiva/disattiva,
    eliminazione, normalizzazione di maiuscole e accenti."""

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})
        cls.radice = os.path.join(tempfile.mkdtemp(prefix="arch_reg_"),
                                  "archivio")
        os.makedirs(cls.radice)
        crea_cartella_progetto(cls.radice, "P-001 Impianto Alfa",
                               "manuale_installazione_TX100.docx")
        crea_cartella_progetto(cls.radice, "P-001 Impianto Alfa",
                               "specifica_tecnica.pdf")
        cls.client.post("/inventario/imposta-radice", data={"radice": cls.radice})
        cls.client.post("/inventario/iniziale")

    def _dati_regola(self, azione, nome="Manuali di installazione",
                     tipologia="manuale_installazione", campo="nome_file",
                     modo="contiene", valori="manuale_installazione"):
        return {"nome": nome, "tipologia": tipologia, "campo": campo,
                "modo": modo, "valori": valori, "azione": azione}

    def test_01_normalizzazione_maiuscole_e_accenti(self):
        from core import archivio as arc
        self.assertEqual(arc.normalizza_testo("Perché"), "perche")
        self.assertEqual(arc.normalizza_testo("MANUALE"), "manuale")
        criterio = {"campo": "nome_file", "modo": "contiene",
                   "valori": ["perché"]}
        doc = {"nome_file": "PERCHE_relazione.docx", "percorso": "",
              "cartella_progetto": "", "estensione": ".docx"}
        self.assertTrue(arc.valuta_criterio(criterio, doc))

    def test_02_prova_live_prima_del_salvataggio(self):
        r = self.client.get("/archivio/regole/nuova")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('value="salva"', r.get_data(as_text=True))
        r = self.client.post("/archivio/regole/nuova",
                             data=self._dati_regola("prova"))
        self.assertEqual(r.status_code, 200)
        testo = r.get_data(as_text=True)
        self.assertIn("1 documenti intercettati", testo)
        self.assertIn("manuale_installazione_TX100.docx", testo)
        self.assertIn('value="salva"', testo)
        conn = db.get_connection()
        self.assertEqual(conn.execute(
            "SELECT COUNT(*) FROM regole_tipologia").fetchone()[0], 0)
        conn.close()

    def test_03_salvataggio_e_priorita_di_creazione(self):
        r = self.client.post("/archivio/regole/nuova",
                             data=self._dati_regola("salva"),
                             follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Regola di tipologia salvata", r.get_data(as_text=True))
        r = self.client.post("/archivio/regole/nuova", data=self._dati_regola(
            "salva", nome="Specifiche tecniche", tipologia="specifica_tecnica",
            campo="estensione", modo="estensione_tra", valori="pdf"),
            follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        conn = db.get_connection()
        regole = conn.execute(
            "SELECT nome, priorita FROM regole_tipologia ORDER BY priorita"
        ).fetchall()
        conn.close()
        self.assertEqual([r["nome"] for r in regole],
                         ["Manuali di installazione", "Specifiche tecniche"])
        self.assertLess(regole[0]["priorita"], regole[1]["priorita"])

    def test_04_riordino_priorita(self):
        conn = db.get_connection()
        prima = conn.execute(
            "SELECT id, nome FROM regole_tipologia ORDER BY priorita"
        ).fetchall()
        conn.close()
        prima_id = prima[0]["id"]
        r = self.client.post("/archivio/regole/%d/sposta" % prima_id,
                             data={"direzione": "giu"}, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        conn = db.get_connection()
        dopo = conn.execute(
            "SELECT id, nome FROM regole_tipologia ORDER BY priorita"
        ).fetchall()
        conn.close()
        self.assertEqual(dopo[0]["id"], prima[1]["id"])
        self.assertEqual(dopo[1]["id"], prima[0]["id"])
        # Spostare oltre il limite non genera errori ne' cambia l'ordine
        r = self.client.post("/archivio/regole/%d/sposta" % dopo[1]["id"],
                             data={"direzione": "giu"}, follow_redirects=True)
        self.assertEqual(r.status_code, 200)

    def test_05_attiva_disattiva_ed_elimina(self):
        conn = db.get_connection()
        riga = conn.execute(
            "SELECT id, attiva FROM regole_tipologia ORDER BY id LIMIT 1"
        ).fetchone()
        conn.close()
        rid, stato_iniziale = riga["id"], riga["attiva"]
        self.client.post("/archivio/regole/%d/toggle" % rid)
        conn = db.get_connection()
        stato_dopo = conn.execute(
            "SELECT attiva FROM regole_tipologia WHERE id = ?",
            (rid,)).fetchone()["attiva"]
        conn.close()
        self.assertNotEqual(stato_iniziale, stato_dopo)
        r = self.client.post("/archivio/regole/%d/elimina" % rid,
                             follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        conn = db.get_connection()
        self.assertIsNone(conn.execute(
            "SELECT id FROM regole_tipologia WHERE id = ?", (rid,)).fetchone())
        conn.close()

    def test_06_criterio_senza_valori_rifiutato(self):
        r = self.client.post("/archivio/regole/nuova", data=self._dati_regola(
            "prova", valori="   \n  "), follow_redirects=True)
        self.assertIn("Indicare almeno un valore", r.get_data(as_text=True))

    def test_07_estensione_tra_forza_il_campo_estensione(self):
        from core import archivio as arc
        criterio, errore = arc.criterio_da_form(
            {"campo": "nome_file", "modo": "estensione_tra", "valori": "pdf\ndocx"})
        self.assertIsNone(errore)
        self.assertEqual(criterio["campo"], "estensione")
        self.assertEqual(criterio["valori"], [".pdf", ".docx"])


class TestArchivioConsolidamento(unittest.TestCase):
    """Modulo 5: ricostruzione idempotente, le tre precedenze (manuale >
    validazione > regola/triage), aggancio a entità e orfani, riservatezza
    dal triage più recente, copertura, completezza per entità, export."""

    CARTELLA_ALFA = "P-001 Impianto Alfa"
    CARTELLA_BETA = "P-002 Impianto Beta"
    CARTELLA_ESTRANEA = "Documenti generali"

    @classmethod
    def setUpClass(cls):
        usa_dati_temporanei()
        from app import create_app
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.client.post("/utenti/benvenuto/crea",
                        data={"nome": "Carlo Verdini", "pin": "1234"})
        cls.radice = os.path.join(tempfile.mkdtemp(prefix="arch_cons_"),
                                  "archivio")
        os.makedirs(cls.radice)
        crea_cartella_progetto(cls.radice, cls.CARTELLA_ALFA,
                               "manuale_installazione_TX100.docx")
        crea_cartella_progetto(cls.radice, cls.CARTELLA_ALFA,
                               "specifica_tecnica.pdf")
        crea_cartella_progetto(cls.radice, cls.CARTELLA_ALFA, "foto.jpg")
        crea_cartella_progetto(cls.radice, cls.CARTELLA_BETA, "config.txt")
        crea_cartella_progetto(cls.radice, cls.CARTELLA_ESTRANEA, "varie.txt")
        cls.client.post("/inventario/imposta-radice", data={"radice": cls.radice})
        cls.client.post("/inventario/iniziale")

        # Tipo di entità "Progetto" (prefisso P- 3 cifre): aggancia le due
        # cartelle P-001/P-002, "Documenti generali" resta senza entità.
        cls.client.post("/catalogo/tipi/nuovo", data={
            "nome": "Progetto", "modo": "prefisso", "prefisso": "P-",
            "blocco1_tipo": "cifre", "blocco1_n": "3", "separatore": "",
            "blocco2_tipo": "cifre", "blocco2_n": "0",
            "escluse_json": "[]", "azione": "salva"})
        conn = db.get_connection()
        cls.tipo_id = conn.execute(
            "SELECT id FROM tipi_entita WHERE nome = 'Progetto'").fetchone()["id"]
        conn.close()

        # Regole di tipologia: manuali di installazione, poi PDF come
        # specifica tecnica. "foto.jpg" e "config.txt" restano senza
        # riscontro (non_classificato), esito legittimo e misurato.
        from core import archivio as arc
        conn = db.get_connection()
        arc.crea_regola(conn, "Manuali di installazione",
                        "manuale_installazione",
                        {"campo": "nome_file", "modo": "contiene",
                         "valori": ["manuale_installazione"]})
        arc.crea_regola(conn, "Specifiche tecniche", "specifica_tecnica",
                        {"campo": "estensione", "modo": "estensione_tra",
                         "valori": [".pdf"]})
        conn.close()

    def _percorso(self, cartella, file_):
        return "%s/%s" % (cartella, file_)

    def _doc(self, conn, percorso):
        return conn.execute(
            "SELECT * FROM documenti WHERE percorso_rel = ?",
            (percorso,)).fetchone()

    def test_01_prima_ricostruzione_classifica_per_regola(self):
        from core import archivio as arc
        conn = db.get_connection()
        report = arc.ricostruisci(conn, self.tipo_id)
        self.assertGreaterEqual(report["nuovi_documenti"], 5)
        self.assertTrue(report["aggancio_eseguito"])

        manuale = self._doc(conn, self._percorso(
            self.CARTELLA_ALFA, "manuale_installazione_TX100.docx"))
        self.assertEqual(manuale["tipologia"], "manuale_installazione")
        self.assertEqual(manuale["tipologia_origine"], "regola")

        pdf = self._doc(conn, self._percorso(
            self.CARTELLA_ALFA, "specifica_tecnica.pdf"))
        self.assertEqual(pdf["tipologia"], "specifica_tecnica")

        foto = self._doc(conn, self._percorso(self.CARTELLA_ALFA, "foto.jpg"))
        self.assertEqual(foto["tipologia"], arc.TIPOLOGIA_NON_CLASSIFICATO)
        conn.close()

    def test_02_aggancio_a_entita_e_orfani(self):
        conn = db.get_connection()
        manuale = self._doc(conn, self._percorso(
            self.CARTELLA_ALFA, "manuale_installazione_TX100.docx"))
        self.assertIsNotNone(manuale["entita_id"])
        entita_alfa = conn.execute(
            "SELECT chiave FROM entita WHERE id = ?",
            (manuale["entita_id"],)).fetchone()
        self.assertEqual(entita_alfa["chiave"], "P-001")

        estranea = self._doc(conn, self._percorso(
            self.CARTELLA_ESTRANEA, "varie.txt"))
        self.assertIsNone(estranea["entita_id"])
        conn.close()

        from core import archivio as arc
        conn = db.get_connection()
        report = arc.ricostruisci(conn, self.tipo_id)
        conn.close()
        self.assertIn(self._percorso(self.CARTELLA_ESTRANEA, "varie.txt"),
                     report["orfani"])
        self.assertGreaterEqual(report["n_orfani"], 1)

    def test_03_ricostruzione_idempotente(self):
        from core import archivio as arc
        conn = db.get_connection()
        arc.ricostruisci(conn, self.tipo_id)
        prima = {r["percorso_rel"]: (r["tipologia"], r["tipologia_origine"],
                                     r["entita_id"], r["riservatezza"])
                 for r in conn.execute("SELECT * FROM documenti")}
        n_prima = conn.execute("SELECT COUNT(*) FROM documenti").fetchone()[0]
        report = arc.ricostruisci(conn, self.tipo_id)
        dopo = {r["percorso_rel"]: (r["tipologia"], r["tipologia_origine"],
                                    r["entita_id"], r["riservatezza"])
                for r in conn.execute("SELECT * FROM documenti")}
        n_dopo = conn.execute("SELECT COUNT(*) FROM documenti").fetchone()[0]
        conn.close()
        self.assertEqual(report["nuovi_documenti"], 0)
        self.assertEqual(n_prima, n_dopo)
        self.assertEqual(prima, dopo)

    def test_04_precedenza_manuale_non_sovrascritta(self):
        from core import archivio as arc
        conn = db.get_connection()
        doc = self._doc(conn, self._percorso(self.CARTELLA_ALFA, "foto.jpg"))
        arc.correggi_tipologia_manuale(conn, doc["id"], "corrispondenza")
        conn.close()

        conn = db.get_connection()
        arc.ricostruisci(conn, self.tipo_id)
        doc = self._doc(conn, self._percorso(self.CARTELLA_ALFA, "foto.jpg"))
        conn.close()
        self.assertEqual(doc["tipologia"], "corrispondenza")
        self.assertEqual(doc["tipologia_origine"], "manuale")

        # ...anche passando dalla vista, con lo stesso esito
        r = self.client.get("/archivio/documenti/%d" % doc["id"])
        self.assertEqual(r.status_code, 200)
        self.assertIn("corrispondenza", r.get_data(as_text=True))

    def test_05_precedenza_validazione_non_sovrascritta_da_regola(self):
        """Una proposta di tipologia confermata in Validazione AI prevale
        sulla regola, anche se la regola classificherebbe diversamente, e
        resta stabile alle ricostruzioni successive."""
        from core import archivio as arc
        conn = db.get_connection()
        cur = conn.execute(
            "INSERT INTO lotti_validazione (data_import, nome_file_origine, "
            "formato, cartella_progetto, n_accettate, n_scartate, stato) "
            "VALUES ('01/06/2026 09:00', 'bozza.json', 'wikify-bozza/1.0', "
            "?, 1, 0, 'importato')", (self.CARTELLA_ALFA,))
        lotto_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO proposte (lotto_id, cartella_progetto, file, "
            "sezione, campo, valore_proposto, confidenza, "
            "evidenza_posizione, evidenza_citazione) VALUES (?, ?, "
            "'specifica_tecnica.pdf', 'intero documento', 'tipologia', "
            "'corrispondenza', 0.9, 'corpo, par. 1', 'testo di prova')",
            (lotto_id, self.CARTELLA_ALFA))
        proposta_id = cur.lastrowid
        conn.execute(
            "INSERT INTO validazioni (proposta_id, esito, valore_corretto, "
            "validatore, data) VALUES (?, 'confermata', '', "
            "'Carlo Verdini', '02/06/2026 10:00')", (proposta_id,))
        conn.commit()

        report = arc.ricostruisci(conn, self.tipo_id)
        pdf = self._doc(conn, self._percorso(
            self.CARTELLA_ALFA, "specifica_tecnica.pdf"))
        self.assertEqual(pdf["tipologia"], "corrispondenza")
        self.assertEqual(pdf["tipologia_origine"], "validazione")

        # Rieseguendo il consolidamento la regola (che classificherebbe
        # "specifica_tecnica") non prevale mai sulla validazione.
        arc.ricostruisci(conn, self.tipo_id)
        pdf = self._doc(conn, self._percorso(
            self.CARTELLA_ALFA, "specifica_tecnica.pdf"))
        conn.close()
        self.assertEqual(pdf["tipologia"], "corrispondenza")
        self.assertEqual(pdf["tipologia_origine"], "validazione")
        self.assertEqual(report["classificati_per_validazione"], 1)

    def test_06_riservatezza_dal_triage_piu_recente(self):
        from core import archivio as arc
        conn = db.get_connection()
        cur = conn.execute(
            "INSERT INTO scansioni (data, radice, stato) VALUES "
            "('01/06/2026 09:00', ?, 'completata')", (self.radice,))
        sid1 = cur.lastrowid
        conn.execute(
            "INSERT INTO triage_file (scansione_id, file, qualifica, "
            "validatore, data) VALUES (?, ?, 'Riservato', 'Carlo Verdini', "
            "'01/06/2026 09:30')",
            (sid1, self._percorso(self.CARTELLA_BETA, "config.txt")))
        cur = conn.execute(
            "INSERT INTO scansioni (data, radice, stato) VALUES "
            "('05/06/2026 09:00', ?, 'completata')", (self.radice,))
        sid2 = cur.lastrowid
        conn.execute(
            "INSERT INTO triage_file (scansione_id, file, qualifica, "
            "validatore, data) VALUES (?, ?, 'Condivisibile', "
            "'Carlo Verdini', '05/06/2026 09:30')",
            (sid2, self._percorso(self.CARTELLA_BETA, "config.txt")))
        conn.commit()
        db.set_impostazione(conn, "radice_archivio", self.radice)

        arc.ricostruisci(conn, self.tipo_id)
        config = self._doc(conn, self._percorso(self.CARTELLA_BETA, "config.txt"))
        conn.close()
        self.assertEqual(config["riservatezza"], "Condivisibile")
        self.assertEqual(config["riservatezza_origine"], "triage")

    def test_07_copertura_e_completezza(self):
        from core import archivio as arc
        conn = db.get_connection()
        indicatori = arc.indicatori_copertura(conn)
        self.assertEqual(
            indicatori["totale_documenti"],
            conn.execute("SELECT COUNT(*) FROM documenti").fetchone()[0])
        self.assertGreater(indicatori["classificati_per_regola"]
                           + indicatori["classificati_per_validazione"], 0)
        # config.txt non e' intercettato da alcuna regola: resta non
        # classificato (esito legittimo e misurato, non un errore).
        self.assertGreaterEqual(indicatori["non_classificati"], 1)

        completezza = arc.completezza_entita(conn, self.tipo_id)
        conn.close()
        chiavi = {r["entita"]["chiave"]: r for r in completezza}
        self.assertIn("P-001", chiavi)
        self.assertIn("manuale_installazione", chiavi["P-001"]["presenti"])
        self.assertNotIn("manuale_installazione", chiavi["P-001"]["assenti"])
        self.assertIn("parametri_interconnessione", chiavi["P-001"]["assenti"])
        self.assertEqual(set(chiavi["P-001"]["presenti"])
                         | set(chiavi["P-001"]["assenti"]),
                         set(arc.TIPOLOGIE_ATTESE))

    def test_08_export_json(self):
        r = self.client.get("/archivio/export/archivio_logico.json")
        self.assertEqual(r.status_code, 200)
        dati = json.loads(r.get_data(as_text=True))
        self.assertEqual(dati["formato"], "wikify-archivio/1.0")
        entita = {e["chiave"]: e for e in dati["entita"]}
        self.assertIn("P-001", entita)
        percorsi = {d["percorso"] for d in entita["P-001"]["documenti"]}
        self.assertIn(self._percorso(
            self.CARTELLA_ALFA, "manuale_installazione_TX100.docx"), percorsi)
        percorsi_orfani = {d["percorso"]
                          for d in dati["documenti_senza_entita"]}
        self.assertIn(self._percorso(self.CARTELLA_ESTRANEA, "varie.txt"),
                     percorsi_orfani)

    def test_09_export_xlsx(self):
        r = self.client.get("/archivio/export/archivio_logico.xlsx")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_data()[:2] == b"PK")
        self.assertIn("archivio_logico.xlsx",
                     r.headers["Content-Disposition"])

    def test_10_pagine_raggiungibili_e_protette(self):
        conn = db.get_connection()
        did = conn.execute("SELECT id FROM documenti LIMIT 1").fetchone()["id"]
        conn.close()
        pagine = ("/archivio/", "/archivio/regole/nuova",
                  "/archivio/consolidamento", "/archivio/esplora",
                  "/archivio/completezza", "/archivio/documenti/%d" % did)
        for pagina in pagine:
            r = self.client.get(pagina)
            self.assertEqual(r.status_code, 200, "pagina %s" % pagina)
        self.client.get("/utenti/uscita")
        for pagina in pagine:
            r = self.client.get(pagina, follow_redirects=False)
            self.assertEqual(r.status_code, 302, "pagina %s" % pagina)
            self.assertIn("/utenti/accesso", r.headers["Location"])
        self.client.post("/utenti/accesso", data={"utente": "1", "pin": "1234"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
