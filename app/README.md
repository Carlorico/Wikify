# Wikify, applicazione web locale

Manuale d'uso dell'applicazione. Per il progetto nel suo insieme — contesto,
requisiti, scelte architetturali e percorso di lettura — vedere il
[README del progetto](../README.md) e la cartella `documentazione/`.

Che cosa contiene l'applicazione: dashboard con gli indicatori
dell'archivio, inventario permanente (mappa dei file a livello di
filesystem), dizionario dei pattern con costruzione guidata (senza
espressioni regolari), scansione deterministica, consultazione raggruppata
per file con coda di lavoro, triage per file (registro di segregazione),
catalogo delle entità logiche, validazione delle bozze dell'agente,
archivio logico con export di consegna, anagrafica utenti con accesso
tramite PIN ed export XLSX.

Tutta l'elaborazione avviene in locale: nessun contenuto lascia il computer.

Nota sui nomi: il progetto si chiama Wikify. Alcuni identificatori tecnici
conservano il nome originario del workshop ("Archivio Smart") per non
rompere la compatibilità: il file del database `archivio_smart.db`, la
variabile d'ambiente `ARCHIVIO_SMART_DATA` e i nomi delle tabelle.

## Requisiti

- Python 3.9 o superiore
- Librerie: flask, pyyaml, openpyxl, pypdf (vedere requirements.txt)

## Installazione e avvio su Mac

Aprire il Terminale nella cartella `app` e digitare:

```
python3 -m pip install -r requirements.txt
./avvia.sh
```

## Installazione e avvio su Windows

Aprire il Prompt dei comandi nella cartella `app` e digitare:

```
py -m pip install -r requirements.txt
avvia.bat
```

Lo script di avvio valorizza `ARCHIVIO_SMART_DATA` sulla cartella dati
locale (vedere "Cartella dei dati di lavoro") e poi lancia l'applicazione.
L'avvio diretto con `python3 app.py` resta possibile, ma in quel caso i
dati vengono scritti in `app/data`.

In entrambi i casi il server parte su http://127.0.0.1:5000 e il browser
si apre da solo. Per chiudere l'applicazione: Ctrl+C nella finestra del
terminale (o chiudere la finestra).

## Primo avvio

Al primo avvio il database viene creato in `Wikify_dati/archivio_smart.db`
(vedere "Cartella dei dati di lavoro") e il
dizionario viene popolato con le 13 regole del file
`dizionario_pattern.yaml` dello scanner CLI (se presente nella cartella
`../scanner`, altrimenti dalla copia inclusa `dizionario_seed.yaml`).

Alla prima apertura del browser compare la pagina di benvenuto, che invita
a creare il primo utente (nome e PIN): da quel momento l'accesso avviene
dalla pagina di login. I database creati con le versioni precedenti vengono
aggiornati automaticamente all'avvio, senza perdita dei dati esistenti.

## Dashboard e inventario permanente

La home dell'app è la dashboard. Al primo utilizzo chiede di impostare la
cartella archivio (il percorso radice dell'archivio documentale): si
imposta una volta sola, resta modificabile dalla dashboard e viene
proposta precompilata in ogni nuova scansione (dove si può comunque
cambiare per la singola esecuzione).

L'inventario è la mappa permanente dell'archivio, mantenuta a livello di
filesystem: per ogni file vengono registrati percorso, cartella progetto
(primo livello sotto la radice), estensione, dimensione e data di
modifica. Nessun contenuto viene letto.

- **Inventario iniziale**: con la mappa vuota, la dashboard propone il
  pulsante "Esegui inventario iniziale" (attraversamento dei soli
  metadati, rapido).
- **Check all'apertura**: a ogni accesso alla dashboard l'app confronta
  filesystem e mappa, al massimo una volta ogni 10 minuti; il pulsante
  "Ricontrolla ora" forza il controllo immediato. I file nuovi vengono
  segnalati con un avviso ("N file nuovi non mappati") e il pulsante
  "Integra nella mappa"; i file rimossi vengono marcati "scomparso".
- **File da classificare**: un file dell'inventario necessita di
  scansione se non è mai stato coperto da una scansione di riservatezza
  completata, oppure se è stato modificato dopo l'ultima che lo copre.
  Il conteggio riguarda i soli formati che lo scanner sa analizzare.

KPI mostrati in dashboard: numero di cartelle progetto (primo livello),
file mappati, file da classificare (con collegamento diretto a "Nuova
scansione"), tabella dei file per cartella con ripartizione per tipo
(docx, xlsx, pdf, txt, altro).

## Navigazione (sidebar)

Il menu è una barra laterale verticale a sinistra, collassabile con il
pulsante hamburger (lo stato viene ricordato dal browser). Voci:

1. **Dashboard** (home);
2. **Classificazione base**, sezione espandibile con le sotto-voci
   "Storico" e "Dizionario"; il comando "Nuova scansione" è il pulsante
   in evidenza nella pagina Storico;
3. **Catalogo**, sezione espandibile con le sotto-voci "Definizione
   entità" e "Arricchimento dati";
4. **Archivio logico**, sezione espandibile con le sotto-voci "Regole di
   tipologia", "Consolidamento", "Esplora archivio" e "Completezza per
   entità";
5. **Validazione AI**, sezione espandibile con le sotto-voci "Perimetro
   e bozze", "Coda di revisione", "Metriche" e "Impostazioni analisi";
6. **Utenti** (anagrafica);
7. **Password** (cambio PIN dell'utente connesso: PIN attuale e nuovo
   PIN ripetuto due volte, stesse regole 4-6 cifre);
8. **Logout**.

La voce attiva è evidenziata. A finestra stretta la sidebar si dispone
sopra il contenuto.

## Utenti e accesso

- Ogni operatore ha un profilo in anagrafica (menu "Utenti"): nome e PIN
  numerico da 4 a 6 cifre. Il PIN viene salvato solo come hash con sale
  (PBKDF2), mai in chiaro.
- L'accesso avviene selezionando il proprio nome e digitando il PIN; il
  nome dell'utente connesso compare nella barra in alto, con il link
  "Esci" per chiudere la sessione.
- Tutte le pagine operative richiedono l'accesso: senza sessione attiva
  si viene riportati alla pagina di login.
- Dall'anagrafica si possono creare nuovi utenti e disattivare (o
  riattivare) quelli esistenti; l'utente connesso non può disattivare
  se stesso. Gli utenti disattivati non compaiono più nella pagina di
  accesso ma restano in anagrafica.
- Nel triage il validatore non si digita più a mano: viene registrato
  automaticamente con il nome dell'utente connesso, insieme alla data
  di validazione.
- La chiave di sessione viene generata al primo avvio e salvata in
  `Wikify_dati/secret_key.txt`.

## Consultazione e triage per file

Nel dettaglio di una scansione le segnalazioni sono raggruppate per file:
ogni file è un pannello richiudibile (accordion) con percorso, conteggi per
severità e stato del triage. Aprendo il pannello si esaminano le
segnalazioni del file (regola, categoria, severità, posizione, testo
intercettato e contesto) e, in fondo, si compila la riga di triage: una
qualifica per l'intero file (Riservato, Condivisibile, Da valutare) con
motivazione e vincolo in campi di testo estesi.

La consultazione funziona come coda di lavoro:

- "Da fare" (vista predefinita): i file ancora da qualificare;
- "Verificati": i file già qualificati Riservato o Condivisibile, sempre
  consultabili e modificabili (la modifica aggiorna validatore e data);
- "Tutti": l'insieme completo.

La qualifica "Da valutare" non marca il file come verificato: il file resta
in coda. I filtri per severità, categoria e nome file agiscono sia sui file
mostrati sia sulle segnalazioni interne ai pannelli. Nella pagina Storico
ogni scansione riporta l'avanzamento del triage (es. "12/40 file
verificati").

Il foglio "Registro segregazione" dell'export XLSX riflette il triage per
file, con colonne ampie per motivazione e vincolo. I valori delle celle
vengono sanificati prima della scrittura (caratteri di controllo, testi
oltre il limite di 32767 caratteri, testi che iniziano per "="), così
l'export non fallisce con contenuti particolari estratti dai documenti.

## Modulo Validazione AI

Il modulo (menu "Validazione AI") è l'interfaccia con cui il responsabile
tecnico valida le bozze di classificazione prodotte dall'agente di
rilevazione (Claude / Claude Code), nel rispetto del perimetro di
riservatezza. Il contratto di scambio è il formato `wikify-bozza/1.0`
(vedere `../agente/formato_bozze.md`).

### Perimetro e bozze

- **Perimetro condivisibile**: per la scansione scelta (o l'ultima
  completata) la pagina elenca i file qualificati Condivisibile nel
  triage; il pulsante di download genera `perimetro_condivisibile.json`
  (formato `wikify-perimetro/1.0`) con i condivisibili e, separatamente,
  gli esclusi con la loro qualifica. L'agente consulta esclusivamente i
  file del perimetro.
- **Import bozze**: upload di uno o più file JSON `wikify-bozza/1.0` con
  validazione severa: formato sconosciuto, file rifiutato; proposta senza
  evidenza (posizione o citazione mancante), scartata e conteggiata;
  campo non previsto o valore fuori tassonomia, scartata con motivo;
  citazione oltre 300 caratteri, troncata con nota. Ogni upload crea un
  "lotto" con riepilogo degli scarti per motivo, stato e avanzamento
  della validazione.

### Coda di revisione

Le proposte accettate entrano in coda, raggruppate per cartella progetto
e ordinate per **confidenza crescente** (prima i dubbi). La vista di
revisione è affiancata: a sinistra l'estratto del documento (tramite
`core/estrazione.py`, con la citazione evidenziata e la finestra di
contesto attorno alla posizione dell'evidenza; se la posizione non è
ricostruibile si mostra la sola citazione con l'avviso "posizione non
verificabile"); a destra la proposta (campo, valore, confidenza,
evidenza) con le azioni **Conferma**, **Correggi** (valore dalla
tassonomia del campo, con nota) e **Caso nuovo** (valore libero e nota).
Ogni azione registra esito, valore corretto, nota, validatore (utente
della sessione), data e secondi impiegati (misurati dal caricamento
della pagina al submit). Le proposte validate escono dalla coda (filtro
Da fare / Validate / Tutte). Le proposte di riservatezza "riservato" o
"misto" confermate mostrano l'avvertenza di retroazione: "Possibile
svista dello scanner: riportare il caso nel dizionario dei pattern".
Ogni cartella dispone inoltre delle note libere di conoscenza tacita.

### Metriche

Per lotto e complessive: accuratezza per campo (% confermate senza
correzione), accuratezza della riservatezza separata tra proposte su
documento intero e su sezioni (puri contro misti), correlazione
confidenza/esito per fasce (0-0.5, 0.5-0.7, 0.7-0.9, 0.9-1), tempo
mediano di validazione per proposta e per cartella, elenco dei casi
nuovi. Export XLSX delle metriche ed export JSON delle correzioni
(formato `wikify-correzioni/1.0`) per il raffinamento dei prompt
dell'agente.

### Schema dati (migrazione V5, additiva)

Tabelle nuove: `lotti_validazione`, `proposte`, `validazioni` (una per
proposta, aggiornabile), `note_conoscenza_tacita`. Scostamenti rispetto
allo schema di progettazione, documentati anche in `core/db.py`: su
`lotti_validazione` sono state aggiunte le colonne `cartella_progetto`,
`chiave_entita`, `n_troncate` e `note_agente_json`; su `proposte` la
colonna `citazione_troncata`. I database esistenti vengono aggiornati
all'avvio senza alcuna modifica alle tabelle precedenti.

## Connettore MCP e sessioni di analisi

Il modulo (sotto-voce "Impostazioni analisi" dentro "Validazione AI")
collega Claude / Claude Code al ciclo agentico senza scambio manuale di
file: un server MCP locale (cartella `mcp_server/`, processo separato)
espone gli strumenti del modulo Validazione AI, con il perimetro
condivisibile imposto come vincolo del server (non solo come regola
scritta nelle istruzioni per l'agente).

### Impostazioni analisi

- **Modelli in cascata**: modello primario (default `claude-haiku`),
  modello di rinforzo (default `claude-sonnet`), soglia di confidenza
  sotto cui rianalizzare col rinforzo (default 0,7) e rinforzo
  obbligatorio sulle proposte di riservatezza "riservato"/"misto"
  (default attivo).
- **Ambito dell'analisi**: campione (numero di progetti, selezione
  casuale riproducibile tramite seed tra le cartelle con almeno un file
  condivisibile nell'ultima scansione completata) oppure archivio
  intero.
- **Prezzi indicativi per modello** (euro per milione di token, in
  ingresso e in uscita): tabella modificabile, usata per stimare i costi
  nei KPI delle sessioni. Le impostazioni correnti sono esposte anche
  dallo strumento MCP `ottieni_istruzioni`.

### Server MCP

Cartella `mcp_server/` (dipendenza `mcp`, l'SDK Python ufficiale,
confinata qui e non nell'app Flask): usa direttamente i moduli `core` e
la stessa base dati dell'app (rispetta `ARCHIVIO_SMART_DATA`), con
connessioni SQLite brevi per convivere con l'app aperta in parallelo.
Strumenti esposti: `ottieni_istruzioni`, `ottieni_incarico` (apre o
recupera la sessione secondo le impostazioni), `leggi_file` (rifiuta con
errore esplicito i file fuori dal perimetro assegnato), `consegna_bozza`
(stessa validazione severa dell'import manuale, lotto legato alla
sessione), `ottieni_correzioni`, `stato_sessione` (avanzamento e
chiusura). Configurazione passo passo per Claude Code e Claude Desktop
in `mcp_server/README.md`.

### Sessioni di analisi e KPI di esito

Migrazione additiva V6: tabella `sessioni_analisi` (ambito, seed, modelli
dichiarati, cartelle assegnate, caratteri letti/prodotti) e colonna
`sessione_id` su `lotti_validazione` (nullable: i lotti da import
manuale restano senza sessione). Scostamento documentato: la tabella
aggiuntiva `sessioni_analisi_letture` traccia i file distinti
effettivamente letti in ciascuna sessione, per non contare due volte i
caratteri di un file riletto e per calcolare il KPI "file nel
perimetro/letti".

Nella pagina Metriche, sezione "Sessioni di analisi": per ciascuna
sessione, progetti assegnati/completati, file nel perimetro/letti,
proposte generate per campo, scarti per motivo, durata, token stimati
(caratteri / 4) e costo stimato con i prezzi impostati per il modello
primario; le metriche di accuratezza esistenti restano inoltre
filtrabili per sessione, oltre che per lotto.

## Modulo Archivio logico

Il modulo (menu "Archivio logico", dopo "Catalogo") chiude la prima versione
di Wikify: consegna un archivio logico e organizzato, in cui il documento è
un oggetto di prima classe con una tipologia e una riservatezza consolidate,
anziché una proprietà sparsa tra inventario, triage e validazioni. Nessuna
componente AI: il consolidamento è interamente deterministico e
riproducibile, a partire da ciò che i moduli precedenti hanno già prodotto.

### Principio di consolidamento

Ogni documento riceve tipologia e riservatezza da tre sorgenti, con
precedenza esplicita e tracciata: **manuale** (correzione dell'operatore
sulla scheda documento) prevale sempre su **validazione** (proposta
confermata o corretta in Validazione AI), che prevale su **regola**
(tipologia) / **triage** (riservatezza), la derivazione automatica
ricalcolata a ogni consolidamento. La ricostruzione è idempotente e non
distruttiva: rieseguirla non altera mai le assegnazioni di precedenza
superiore e produce sempre un report di ciò che ha cambiato.

### Regole di tipologia

Costruzione guidata analoga al builder del dizionario, senza espressioni
regolari: si osserva un campo del documento (nome file, percorso, cartella
progetto o estensione), si sceglie il modo di confronto (contiene, inizia
per, finisce per, uguale a, estensione tra) e si indicano uno o più valori,
con confronto sempre senza distinzione di maiuscole e con normalizzazione
degli accenti. Le regole sono ordinate per priorità (riordinabili con i
comandi "Su"/"Giù"), attivabili e disattivabili: vince la prima regola
attiva che riscontra. La pagina "Regole di tipologia" richiede la prova
live sui nomi reali dei file dell'inventario (conteggio degli intercettati
ed esempi) prima del salvataggio. I documenti che nessuna regola intercetta
restano "non_classificato": un esito legittimo e misurato, non un errore.

### Consolidamento

Il pulsante di ricostruzione (pagina "Consolidamento") applica le regole di
tipologia, consolida la riservatezza dal triage più recente, sovrappone le
proposte confermate o corrette in Validazione AI e aggancia i documenti
alle entità del tipo scelto (selezionabile in pagina, ricordato per la
volta successiva). Il report mostra documenti nuovi, classificati per
regola/validazione/manuale, non classificati, agganciati e orfani (cartella
progetto senza entità corrispondente: segnale che il criterio di
autogenerazione dell'entità va rivisto, o che la cartella è estranea al
perimetro), oltre agli indicatori di copertura sempre consultabili in
pagina, anche prima di una nuova esecuzione.

### Esplora archivio e completezza per entità

"Esplora archivio" naviga entità → tipologia → documenti (con il bucket
"senza entità collegata" per gli orfani), con filtri liberi per entità,
tipologia, riservatezza e stato di classificazione utilizzabili anche in
combinazione diretta. La scheda del singolo documento consente la
correzione manuale della tipologia, che diventa la precedenza massima.
"Completezza per entità" mostra, per ciascuna entità, quali tipologie
attese risultano assenti tra i documenti agganciati: la misura di quanto
l'archivio sia pronto per la fase 2 (retrieval semantico, knowledge graph).

### Export

`archivio_logico.json` (formato `wikify-archivio/1.0`: entità con i propri
attributi e i documenti agganciati, tipologia/riservatezza/origine/percorso;
più i documenti senza entità corrispondente) è il contratto di consegna
verso la fase 2, che leggerà questo file e non il filesystem, ereditando il
security trimming già stabilito dal triage. `archivio_logico.xlsx` affianca
i fogli "Documenti", "Regole di tipologia" e "Completezza per entità" per
la consultazione.

### Schema dati (migrazione V7, additiva) e scostamenti dalla specifica

Tabelle nuove: `documenti` (percorso_rel univoco, cartella_progetto,
entita_id, tipologia/tipologia_origine/tipologia_regola_id,
riservatezza/riservatezza_origine, stato, data_aggiornamento) e
`regole_tipologia` (nome, tipologia, criterio_json, priorita, attiva,
data_creazione). I database esistenti vengono aggiornati all'avvio senza
alcuna modifica alle tabelle precedenti. Scostamenti rispetto allo schema
di progettazione, documentati anche in `core/db.py` e `core/archivio.py`:

- `documenti.entita_id` e `documenti.tipologia_regola_id` non dichiarano
  `REFERENCES`: sono collegamenti derivati, ricalcolati a ogni
  consolidamento, non un vincolo di integrità referenziale permanente —
  coerentemente con la natura non distruttiva della ricostruzione,
  un'entità o una regola cancellate non devono impedire la lettura dei
  documenti già scritti;
- l'aggancio documento → entità richiede la scelta esplicita del tipo di
  entità (la specifica non la rende esplicita, essendo possibili più tipi
  di entità nel catalogo): la scelta è ricordata nelle impostazioni e
  rieseguibile senza aggancio (nessun tipo scelto) senza toccare i
  collegamenti già calcolati;
- la riservatezza consolidata conserva il vocabolario della sorgente da
  cui proviene: "Riservato"/"Condivisibile" dal triage per file (registro
  di segregazione del modulo Scanner), "condivisibile"/"riservato"/"misto"
  dalla Validazione AI (tassonomia per sezione, con "misto" quando sezioni
  diverse dello stesso documento sono state validate con esiti diversi). I
  due vocabolari non vengono unificati: unificarli avrebbe richiesto
  ridefinire una delle due tassonomie già congelate altrove nell'app;
  restano distinguibili dalla colonna riservatezza_origine;
- le "tipologie attese" della completezza per entità coincidono con
  l'intera tassonomia di `core/validazione.py`, esclusa "altro" (che è per
  definizione un contenitore residuale): la specifica non introduce una
  configurazione di tipologie attese per tipo di entità, quindi si è
  scelto il riferimento deterministico più semplice e verificabile.

## Verifiche automatiche

La suite di test si esegue con:

```
python3 tests/test_suite.py [archivio_di_prova] [cartella_dati_vecchia]
```

I dati di test vengono scritti in cartelle temporanee: il database di
lavoro non viene toccato.

## Struttura delle cartelle

```
app/
  app.py           avvio e registrazione dei moduli (blueprint)
  avvia.sh/.bat    avvio con la cartella dati locale (Mac / Windows)
  core/            database, estrazione testo, motore di scansione, inventario, catalogo, archivio logico, report, analisi
  modules/         moduli funzionali: inventario, dizionario, scansione, storico, catalogo, validazione, archivio
  templates/       pagine HTML (Jinja2)
  static/          stile CSS e script della prova live
  docs_agente/     istruzioni e formato bozze per l'agente di rilevazione
  mcp_server/      server MCP locale (processo separato, dipendenza propria)

../../Wikify_dati/ database SQLite, chiave di sessione, temporanei di import
```

## Cartella dei dati di lavoro

I dati di lavoro (database SQLite con inventario, esiti di scansione,
triage, catalogo e validazioni; chiave di sessione; temporanei di import)
risiedono in `Wikify_dati`, cartella **sorella** di `Wikify`:

```
Workshop/
  Wikify/         codice, documentazione, brand  (versionabile)
  Wikify_dati/    database, chiave di sessione, import_temp  (solo locale)
```

La separazione tiene i dati fuori dalla cartella di progetto: nessun
contenuto dell'archivio analizzato finisce in un repository o in una copia
condivisa. Il percorso è determinato dalla variabile d'ambiente
`ARCHIVIO_SMART_DATA`, valorizzata dagli script `avvia.sh` / `avvia.bat`;
in assenza della variabile l'applicazione ripiega su `app/data`.

Lo stesso vale per il server MCP, che deve ricevere la medesima variabile
per lavorare sulla stessa base dati dell'app (vedere `mcp_server/README.md`).

Se l'app risiede su una condivisione di rete che non supporta SQLite, è
sufficiente valorizzare `ARCHIVIO_SMART_DATA` su un percorso locale prima
dell'avvio.

## Aggiungere un nuovo modulo in futuro

La struttura è pensata per crescere (inventario, verifica XLS, validazione):
il procedimento passo passo è descritto nel commento dentro `app.py`
(creare il blueprint in `modules/`, registrarlo, accodare le eventuali
tabelle alla lista MIGRAZIONI di `core/db.py`, aggiungere la voce di menu).

## Compatibilità con lo scanner CLI

Dalla pagina Dizionario il pulsante "Esporta YAML" genera un file con la
stessa struttura `regole:` letta da `scan_riservatezza.py` (opzione
`--dizionario`), così i due strumenti restano allineati.
