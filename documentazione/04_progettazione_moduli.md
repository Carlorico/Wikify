# Progettazione dei moduli

*Risponde alla domanda: come sono stati progettati, uno per uno, i moduli funzionali di
Wikify.*

Wikify è organizzato su una base modulare (Flask + SQLite) che oggi ospita cinque moduli realizzati — Inventario e dashboard, Classificazione base, Catalogo, Validazione AI, Archivio logico — più le funzioni di servizio (utenti e accesso, manutenzione e reset). Questo documento raccoglie la progettazione di ciascun modulo, nell'ordine in cui è stato costruito.

Principio: modularità "povera". Ogni modulo è un blueprint Flask con le proprie tabelle SQLite e le proprie pagine. Il pacchetto `core` (estrazione testo, attraversamento archivio, db) è condiviso fra i moduli e non si duplica.

---

## Modulo 1 — Inventario e Dashboard (Fase 1 dell'assessment)

> **Revisione del 26/07/2026 (sessione 11, impostazione di Carlo)**: l'inventario non è una scansione lanciata a mano di volta in volta, è la **mappa permanente dell'archivio** che l'app mantiene aggiornata. Comportamento: (1) primo inventario completo da zero, salvato; (2) a ogni riapertura dell'app, check automatico che rileva i file nuovi non ancora mappati; (3) i file che non sono mai passati dalla scansione di classificazione (triage) vengono evidenziati come "da classificare". La dashboard diventa la home dell'app e mostra i KPI dell'archivio.

### Scopo
Fotografare l'archivio a livello di filesystem (nessuna lettura dei contenuti, nessuna AI), mantenere la fotografia allineata nel tempo e guidare l'utente verso ciò che resta da classificare.

### Dati in ingresso
- Percorso radice dell'archivio: impostato una volta nelle impostazioni dell'app (non più digitato a ogni scansione) e riusato da inventario e scanner.

### Comportamento
1. **Inventario iniziale**: attraversamento completo, salvataggio della mappa file su DB.
2. **Check all'apertura**: confronto rapido filesystem ↔ mappa salvata; i file nuovi vengono segnalati e integrabili nella mappa; i file scomparsi vengono marcati.
3. **Stato di classificazione per file**: un file "necessita scansione" se non è mai stato coperto da una scansione di riservatezza (o se è stato modificato dopo l'ultima); l'app lo evidenzia e invita a lanciare la scansione.

### Dashboard (home dell'app)
KPI richiesti:
- numero cartelle progetto (primo livello sotto la radice);
- numero file per cartella: totali e parziali per tipo/estensione;
- file che necessitano scansione per la classificazione (con accesso diretto al lancio).

### Schema tabelle
```
inventari(id, data, radice, etichetta, n_file, n_cartelle_progetto, durata)
file_inventario(id, inventario_id, percorso_rel, cartella_progetto,
                sottocartella, profondita, nome_file, estensione,
                dimensione_byte, data_creazione, data_modifica,
                flag_sospetto, motivo_sospetto)
```
`cartella_progetto` = primo livello sotto la radice. `flag_sospetto` per: copie ("copia di", "v2", "old", "backup"), file vuoti, estensioni esotiche.

### Regole di derivazione (deterministiche, in `core`)
- Pattern di nomenclatura: estrazione di uno "schema nome" (es. `manuale_<codice>.docx` → `manuale_*`), per misurare la % di file con naming riconoscibile.
- Rilevazione struttura ricorrente: confronto degli alberi di sottocartelle tra cartelle progetto (insieme dei nomi di sottocartella normalizzati).

### Viste UI
1. **Lancio inventario**: form percorso + etichetta (o spunta "inventario" nella pagina di scansione, se passata combinata).
2. **Dashboard KPI**: card e tabelle per i KPI di assessment §1.2: n. cartelle progetto, distribuzione per formato, distribuzione file per cartella (min/mediana/max), profondità, % naming riconoscibile, distribuzione temporale per anno, conteggio sospetti. Ogni KPI cliccabile → drill-down sui file.
3. **Esplora file**: tabella filtrabile (cartella, estensione, anno, flag sospetto).
4. **Export XLSX**: `inventario_archivio.xlsx` con fogli "dettaglio file" e "KPI" (come da assessment).

### Note di progetto
- La dashboard KPI alimenta direttamente le righe S1, S3, S4 della tabella di sintesi.
- La distribuzione temporale serve alla costruzione del campione stratificato della Fase 3.

---

## Modulo 2 — Catalogo: entità logiche e arricchimento dati (Fase 2, evoluta)

> **Revisione del 26/07/2026 (sessione 12, impostazione di Carlo)**: il modulo non è più una verifica una tantum del file XLS, è la **nascita del catalogo**. Due funzioni: un motore di entità (definizione + autogenerazione da criterio) e un arricchimento deterministico da fonti esterne tabellari. Le verifiche V1-V6 diventano il controllo di qualità del flusso di import. Voce di menu: sezione **"Catalogo"** (tra Classificazione base e Utenti) con sotto-voci **"Definizione entità"** e **"Arricchimento dati"**.

### 2A — Definizione entità
L'utente crea un **tipo di entità** assegnando un nome (es. "Progetto") e scegliendo il **criterio di autogenerazione** delle istanze. Criteri MVP:
- sorgente: cartelle di primo livello dell'inventario;
- estrazione della chiave dal nome cartella: nome intero, oppure regola guidata (prefisso+formato o pattern, riusando il builder del dizionario) con **prova live sui nomi reali** delle cartelle prima di confermare.

Regole di comportamento:
- le istanze nascono dal criterio ma **persistono**: se la cartella scompare o il criterio cambia, l'entità con i suoi attributi non si cancella, si marca "senza riscontro"; la rigenerazione è un riallineamento con report (nuove create, orfane marcate), mai ricostruzione da zero;
- **chiavi duplicate** (due cartelle → stessa chiave estratta): conflitto mostrato all'utente, mai risolto in automatico.

### 2B — Arricchimento dati (import CSV/XLS)
Carica un file tabellare e aggancia attributi alle entità in modo deterministico:
1. upload (csv o xlsx) → anteprima prime righe;
2. mappatura: quale colonna è la **chiave entità**, quali colonne sono **attributi** (nome attributo = intestazione colonna, rinominabile);
3. relazione **1:N nativa**: più righe con la stessa chiave = più valori dello stesso attributo (es. un progetto, tre codici articolo su tre righe); i valori identici vengono deduplicati;
4. **anteprima di qualità prima della conferma** (le ex verifiche): righe con chiave senza entità corrispondente, entità mai citate dal file, duplicati esatti e post-normalizzazione (trim, maiuscole, zeri iniziali, tracciate);
5. conferma → ogni valore salvato con **provenienza** (import, file, data, utente);
6. ripetibilità: ogni import è un'unità rimovibile in blocco (rollback per provenienza), niente sovrascritture silenziose.

### Schema tabelle
```
tipi_entita(id, nome, criterio_json, data_creazione, stato)
entita(id, tipo_id, chiave, cartella_origine, stato: attiva/senza_riscontro,
       data_creazione, data_riallineamento)
importazioni(id, data, nome_file, tipo_entita_id, mappatura_json,
             n_righe, n_valori, n_scartate, utente, stato)
attributi_entita(id, entita_id, nome_attributo, valore,
                 importazione_id, data)     -- UNIQUE(entita_id, nome_attributo, valore)
anomalie_import(id, importazione_id, tipo, riferimento, dettaglio,
                stato_chiarimento, nota_chiarimento)
```

### Viste UI
1. **Definizione entità**: elenco tipi, creazione guidata con prova live, riallineamento con report, conflitti di chiave.
2. **Arricchimento dati**: wizard upload → mappatura → anteprima qualità → conferma; elenco importazioni con rimozione in blocco.
3. **Scheda entità**: chiave, cartella collegata, attributi con provenienza, stato; elenco entità filtrabile.
4. **Export XLSX**: catalogo entità+attributi e report anomalie import.

### Note di progetto
- Alimenta la riga S5 della sintesi (qualità del legame progetti↔articoli) attraverso le anomalie di import.
- `entita` + `attributi_entita` sono l'embrione del catalogo strutturato di Wikify: la migrazione futura parte da qui.
- Prospettiva: i tag/attributi potranno guidare i permessi e il retrieval del sistema finale.

---

## Modulo 3 — Interfaccia di validazione (Fase 3B)

### Scopo
Coda di revisione con cui il responsabile tecnico valida le proposte dell'agente di rilevazione (schede in bozza). Prototipo del futuro modulo di validazione della pipeline di classificazione. Requisiti già definiti in assessment.md §3.3; qui la traduzione tecnica.

### Vincolo di perimetro
Il modulo consuma solo materiali qualificati **Condivisibili** nel registro di segregazione (tabella `triage` del modulo Classificazione base). Il punto di aggancio è una funzione in `core/db.py`: `elenco_condivisibili(scansione_id)` che restituisce i file/sezioni ammessi. L'agente (esterno all'app) riceve solo quel perimetro.

### Dati in ingresso
- Bozze di scheda prodotte dall'agente in formato JSON (una per cartella progetto del campione), importate via upload o cartella osservata. Formato concordato:
```json
{
  "cartella_progetto": "P-0045",
  "proposte": [{
      "file": "...", "sezione": "...",
      "campo": "tipologia | riservatezza | versione_ufficiale | forma_caratteristiche",
      "valore_proposto": "...", "confidenza": 0.0,
      "evidenza": {"posizione": "...", "citazione": "..."}
  }]
}
```
La regola di trasparenza è imposta dallo schema: una proposta senza `evidenza` viene rifiutata all'import.

### Schema tabelle
```
lotti_validazione(id, data_import, origine, n_schede, stato)
proposte(id, lotto_id, cartella_progetto, file, sezione, campo,
         valore_proposto, confidenza, evidenza_posizione, evidenza_citazione)
validazioni(id, proposta_id, esito,            -- confermata / corretta / caso_nuovo
            valore_corretto, nota, validatore, data,
            secondi_impiegati)
note_conoscenza_tacita(id, lotto_id, cartella_progetto, testo, autore, data)
```

### Viste UI
1. **Coda di revisione**: schede ordinate per confidenza crescente (prima i dubbi), avanzamento del lotto.
2. **Vista affiancata**: a sinistra l'estratto del documento (via `core/estrazione.py`, con la sezione evidenziata), a destra le proposte con evidenza citata; azioni rapide per proposta: Conferma / Correggi (select da tassonomia) / Caso nuovo.
3. **Riservatezza mista**: per le proposte di campo "riservatezza", possibilità di ridisegnare il confine (selezione delle sezioni interessate).
4. **Metriche** (assessment §3.4, calcolate dalle `validazioni`): accuratezza per campo, accuratezza riservatezza separata puri/misti, correlazione confidenza/errore (per fasce di confidenza), tempo mediano per scheda, elenco casi nuovi.
5. **Note libere** per la conoscenza tacita (alimenta la sezione E delle schede).

### Note di progetto
- Le `validazioni` sono il dataset che stima l'affidabilità della pipeline a regime (righe S6 e input al dimensionamento della revisione umana futura).
- Le correzioni esportabili in JSON diventano esempi per il raffinamento dei prompt dell'agente.

---

## Modulo 4 — Connettore MCP e sessioni di analisi (26/07/2026)

### Scopo
Collegare Claude/Claude Code a Wikify senza scambio manuale di file: un server MCP locale espone le funzioni del ciclo agentico come strumenti. Il perimetro condivisibile passa da regola scritta a **vincolo imposto dal server**: l'agente non può fisicamente leggere file fuori perimetro.

### Impostazioni analisi (nuova sotto-voce di Validazione AI)
Salvate nella tabella `impostazioni` esistente:
- **Modelli (cascata)**: modello primario (default Haiku), modello di rinforzo (default Sonnet), soglia di confidenza sotto cui rianalizzare col rinforzo (default 0,7), rinforzo obbligatorio per proposte riservatezza riservato/misto (default sì);
- **Ambito**: campione (con numero progetti, selezione casuale riproducibile con seed tra le cartelle con file condivisibili) oppure archivio intero;
- **Prezzi indicativi per modello** (€/milione token in e out, modificabili) per la stima dei costi nei KPI.
Le impostazioni guidano l'agente via MCP oggi e il futuro motore integrato domani.

### Server MCP (processo separato, stessa base dati e stesso core)
Strumenti esposti:
| Strumento | Funzione | Vincolo |
|---|---|---|
| `ottieni_istruzioni` | Istruzioni, formato bozze, tassonomie, impostazioni cascata correnti | |
| `ottieni_incarico` | Apre una sessione di analisi secondo le impostazioni (ambito/campione) e restituisce cartelle e file assegnati | Solo file condivisibili |
| `leggi_file` | Testo estratto di un file | Rifiuto se fuori perimetro condivisibile |
| `consegna_bozza` | Consegna una bozza wikify-bozza/1.0 | Stessa validazione severa dell'import manuale, lotto legato alla sessione |
| `ottieni_correzioni` | Correzioni pregresse come esempi | |
| `stato_sessione` | Avanzamento della sessione corrente | |

### Sessioni di analisi e KPI di esito
Tabella `sessioni_analisi` (ambito, n. progetti, modelli dichiarati, date, stato) + collegamento dei lotti alla sessione. KPI in una sezione dedicata della pagina Metriche:
- progetti assegnati / completati; file nel perimetro / esaminati / esclusi;
- proposte generate per campo e distribuzione delle confidenze;
- scarti all'import per motivo; durata della sessione;
- stima token e costo (dai caratteri letti/prodotti e dai prezzi impostati);
- e, dopo la validazione umana, le metriche di accuratezza già esistenti filtrabili per sessione.

### Note
- L'import manuale dei JSON resta invariato (chi non usa Claude non perde nulla).
- Dipendenza `mcp` (SDK Python) confinata al server, non all'app Flask.
- Configurazione lato Claude Code documentata nel README (`claude mcp add`).

---

## Modulo 5 — Archivio logico (chiusura della fase 1, 29/07/2026)

### Scopo
Chiudere la prima versione di Wikify consegnando ciò che la fase 2 (retrieval semantico, knowledge graph, LLM-Wiki) presuppone e che oggi manca: **un archivio logico e organizzato**. I moduli esistenti hanno prodotto i materiali grezzi — la mappa dei file, la qualifica di riservatezza, le entità con i loro attributi, le proposte validate — ma il **documento non è ancora un oggetto di prima classe del catalogo**: non ha una tipologia stabile, non è legato esplicitamente all'entità, e la sua riservatezza vive dentro la singola scansione anziché come proprietà consolidata.

Il modulo colma questo scarto senza introdurre alcuna componente AI: è consolidamento deterministico di informazioni già presenti, più una vista di navigazione e un export. La fase 2, quando arriverà, partirà da qui e non dal filesystem.

### Principio di consolidamento
Ogni documento riceve una tipologia e un livello di riservatezza da tre sorgenti, con precedenza esplicita e tracciata:

| Precedenza | Origine | Motivazione |
|---|---|---|
| 1 (massima) | `manuale` — correzione dell'operatore nella scheda documento | La decisione umana diretta non viene mai sovrascritta da una rielaborazione |
| 2 | `validazione` — proposta dell'agente confermata o corretta in Validazione AI | È stata comunque vagliata da un umano |
| 3 | `regola` (tipologia) / `triage` (riservatezza) | Derivazione automatica, sostituibile a ogni ricostruzione |

La ricostruzione è **idempotente e non distruttiva**: rieseguirla non altera le assegnazioni di precedenza superiore e produce sempre un report di ciò che ha cambiato.

### Regole di tipologia
Classificazione deterministica sul **nome del file, sul percorso e sull'estensione** — nessuna lettura del contenuto, nessun costo di elaborazione. Costruzione guidata analoga al builder del dizionario dei pattern, senza espressioni regolari:

- campo osservato: `nome_file`, `percorso`, `cartella_progetto`, `estensione`;
- modo: `contiene`, `inizia_per`, `finisce_per`, `uguale_a`, `estensione_tra`;
- valori: uno o più termini, confronto senza distinzione di maiuscole e con normalizzazione degli accenti;
- tipologia assegnata: valore della tassonomia `tipologia` già congelata in `core/validazione.py` (`specifica_tecnica`, `manuale_installazione`, `manuale_manutenzione`, `parametri_interconnessione`, `dati_sperimentazione`, `configurazione`, `disegno_schema`, `corrispondenza`, `altro`);
- **priorità**: le regole sono ordinate; vince la prima che riscontra. Regole riordinabili e disattivabili;
- **prova live** sui nomi reali dei file dell'inventario prima di confermare la regola, con conteggio dei documenti intercettati ed esempi.

I documenti che nessuna regola intercetta restano `non_classificato`: è un esito legittimo e misurato, non un errore da nascondere.

### Aggancio documento → entità
Il legame si deriva dalla `cartella_progetto` dell'inventario confrontata con `entita.cartella_origine` del tipo di entità scelto. I documenti la cui cartella non corrisponde ad alcuna entità restano **orfani** e vengono elencati: sono il segnale che il criterio di autogenerazione dell'entità va rivisto, oppure che la cartella è estranea al perimetro.

### Schema tabelle (migrazione V7, additiva)
```
documenti(id, percorso_rel UNIQUE, cartella_progetto, entita_id,
          tipologia, tipologia_origine, tipologia_regola_id,
          riservatezza, riservatezza_origine,
          stato, data_aggiornamento)
regole_tipologia(id, nome, tipologia, criterio_json, priorita,
                 attiva, data_creazione)
```

### Viste UI
Nuova sezione di menu **"Archivio logico"**, dopo Catalogo:
1. **Regole di tipologia**: elenco ordinato per priorità con creazione guidata e prova live, riordino, attivazione/disattivazione.
2. **Consolidamento**: pulsante di ricostruzione con report dettagliato (classificati per regola, da validazione, manuali conservati, non classificati, agganciati, orfani, riservatezza consolidata dal triage) e indicatori di copertura.
3. **Esplora archivio**: navigazione entità → tipologia → documenti, con badge di riservatezza, filtri (entità, tipologia, riservatezza, stato di classificazione) e correzione manuale della tipologia sulla scheda del singolo documento.
4. **Completezza per entità**: quali tipologie attese risultano assenti per ciascuna entità — la misura di quanto l'archivio sia effettivamente pronto per la fase 2.
5. **Export**: `archivio_logico.json` (formato `wikify-archivio/1.0`: entità, attributi, documenti con tipologia, riservatezza, origine e percorso) e `archivio_logico.xlsx` per la consultazione.

### Note di progetto
- L'export JSON è il **contratto di consegna verso la fase 2**: l'indicizzazione semantica e il knowledge graph leggeranno quello, non il filesystem, ereditando così il security trimming già stabilito dal triage.
- La copertura di classificazione e la completezza per entità sono gli indicatori con cui decidere se l'archivio è maturo per la fase 2 o se serve un altro giro di regole.
- Nessuna chiamata a modelli: il modulo è interamente deterministico e riproducibile.

## Roadmap di integrazione

| Ordine | Modulo | Dipende da | Stato | Motivo dell'ordine |
|---|---|---|---|---|
| 1 | Classificazione base | base | Realizzato | Sblocca il triage di riservatezza, prerequisito di tutto |
| 2 | Inventario e dashboard | base, walk condiviso | Realizzato | Serve alla costruzione del campione e alla dashboard |
| 3 | Catalogo | Inventario | Realizzato | Fa nascere le entità logiche e vi aggancia gli attributi importati |
| 4 | Validazione AI | Classificazione base (triage) | Realizzato | Consuma solo il perimetro condivisibile |
| 5 | Archivio logico | Inventario, Catalogo, Validazione AI | Realizzato | Consolida tipologia, aggancio all'entità e riservatezza; produce il contratto di consegna verso la fase 2 |
| 6 | Fase 2 — retrieval semantico e knowledge graph | Archivio logico (export `wikify-archivio/1.0`) | Sviluppo futuro, non ancora avviato | Costruisce indicizzazione semantica e grafo delle caratteristiche tecniche a partire dall'archivio logico, non dal filesystem |

## Punti aperti

1. ~~Passata combinata inventario+scanner~~ **Risolto**: l'inventario è la mappa permanente con check automatico all'apertura; lo scanner resta operazione distinta, collegata dallo stato "da classificare" per file.
2. ~~Formato JSON delle bozze agente~~ **Risolto**: il formato è stato congelato in `agente/formato_bozze.md` (contratto `wikify-bozza/1.0`) ed è quello effettivamente in uso da parte del connettore MCP e dell'import manuale.
3. **Tassonomia delle tipologie documentali**: quella della scheda di rilevazione (assessment §3.5) resta l'elenco di partenza per i select dell'interfaccia di validazione e per le regole di tipologia dell'Archivio logico; va ancora confermata col responsabile tecnico.
4. **Snapshot e versioning del XLS**: se il file aziendale cambia spesso, resta da valutare il confronto tra snapshot successivi (fuori perimetro delle versioni realizzate finora).
