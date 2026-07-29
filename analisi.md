# Progetto Wikify (workshop "Archivio Smart") — Registro di analisi

Documento vivo: registra l'interazione, le considerazioni e le decisioni del percorso di analisi per la realizzazione di un archivio smart delle schede progetto.

---

## 1. Contesto e specifiche iniziali (25/07/2026)

### Il dominio
- Archivio storico digitale di **schede progetto** relative a: **sonde, controller, porta sonda**.
- Ogni cartella progetto contiene: dati di sperimentazione, specifiche tecniche, manuali di installazione e manutenzione, parametri di interconnessione, altro.
- Formati eterogenei: Word, Excel, PDF, TXT e altri.
- Un progetto è la base di **uno o più articoli commerciali**; la relazione progetto ↔ articolo è mantenuta su un **file XLS**.

### Il problema organizzativo
- L'archivio è di competenza dell'**ufficio tecnico**; l'**ufficio commerciale** necessita spesso di informazioni sui prodotti ma, non avendo competenza sull'archivio, passa attraverso i referenti tecnici.
- Ne deriva un **collo di bottiglia**: onere ricorrente per l'ufficio tecnico, tempi di attesa per il commerciale.
- Esiste inoltre un tema di **profilazione degli accessi**: documenti generici (manuali) fruibili da tutti; dati di configurazione riservati al personale tecnico e a clienti specifici.

### L'obiettivo
Progetto tutorial per realizzare un **archivio smart** basato su:
1. tecniche moderne di **indicizzazione delle informazioni**;
2. **interfaccia guidata** di consultazione.

Soluzioni candidate da valutare (singole o combinate): database relazionale, database documentale, RAG, LLM-Wiki (metodo Carpiati / Grapify). Obiettivo del percorso: definire i **criteri di scelta** e le possibili combinazioni.

---

## 2. Prime considerazioni (Claude)

### 2.1 Osservazione preliminare sulla natura del problema
Il problema presenta tre dimensioni distinte, che conviene tenere separate in fase di analisi perché ammettono soluzioni tecnologiche diverse:

1. **Dimensione strutturata**: la relazione progetto ↔ articolo commerciale, gli attributi anagrafici (famiglia prodotto, codici, date, stati). Dati tabellari, interrogabili con criteri esatti.
2. **Dimensione documentale**: i contenuti dei file (manuali, specifiche, relazioni di sperimentazione). Informazione non strutturata, interrogabile per ricerca semantica o full-text.
3. **Dimensione di governance**: chi può vedere cosa. Trasversale alle prime due e potenzialmente il vincolo più stringente sulla scelta architetturale.

### 2.2 Ipotesi di lavoro
Le soluzioni candidate non sono alternative pure: rispondono a esigenze diverse.

| Soluzione | A cosa risponde bene | Aree di attenzione |
|---|---|---|
| DB relazionale | Relazioni esatte progetto/articolo, metadati, permessi | Non indicizza contenuti documentali |
| DB documentale | Metadati flessibili, schemi eterogenei | Ricerca semantica assente senza componenti aggiuntive |
| RAG (indicizzazione vettoriale + LLM) | Domande in linguaggio naturale sui contenuti | Governance degli accessi da progettare con cura; rischio di risposte non tracciabili alla fonte se mal configurato |
| LLM-Wiki / Knowledge graph (Grapify e simili) | Navigazione guidata, relazioni tra entità (sonda ↔ controller ↔ articolo) | Onere di costruzione e manutenzione della base di conoscenza |

L'ipotesi che emerge dai primi ragionamenti è che la soluzione finale sia verosimilmente **ibrida**: un livello strutturato (catalogo/metadati/permessi) + un livello di indicizzazione semantica dei documenti + un'interfaccia di consultazione che media i due livelli rispettando i profili di accesso.

### 2.3 Criteri di scelta da approfondire (bozza)
- Tipologia prevalente delle domande dell'ufficio commerciale (esatte vs esplorative).
- Volumi: numero progetti, numero file, dimensioni.
- Requisiti di riservatezza: granularità dei permessi (per documento? per sezione? per cliente?).
- Effort di preparazione dei dati (qualità e uniformità dell'archivio esistente).
- Competenze e infrastruttura disponibili (on-premise vs cloud, budget).
- Tracciabilità delle risposte (citazione della fonte come requisito?).

---

## 3. Registro dell'interazione

### Sessione 17 — 29/07/2026
- **Ripresa del progetto e punto sullo stato dell'arte**: applicazione riavviata e verificata (login, dashboard), suite di verifica rieseguita con esito pieno (110 test). Emerso che la base dati non conserva alcun dato di lavoro — effetto del collaudo del Reset archivio del 26/07 alle 22:06, successivo alla prova del connettore MCP: restano dizionario (14 regole), utente e impostazioni. Ne discende che **il ciclo end-to-end non ha ancora prodotto metriche reali** (accuratezza, correlazione confidenza/esito, token e costi), che erano la condizione posta prima di costruire il motore agente integrato.
- **Separazione dei dati di lavoro dalla cartella di progetto**: creata `Workshop/Wikify_dati` (sorella di `Workshop/Wikify`) con database, chiave di sessione e temporanei di import; introdotti gli script `app/avvia.sh` e `app/avvia.bat` che valorizzano `ARCHIVIO_SMART_DATA` con percorso risolto in modo relativo, così da restare validi su qualsiasi macchina. Rimossa la vecchia `app/data` per non lasciare due basi dati apparentemente valide. Documentazione allineata (README dell'app e del server MCP).
- **Server MCP ri-registrato** con `ARCHIVIO_SMART_DATA` nell'ambiente: senza la variabile avrebbe lavorato su una base dati diversa da quella dell'app, con il perimetro condivisibile non visibile e le bozze consegnate invisibili all'interfaccia.
- **Introdotto il versionamento**: repository git con radice in `Wikify/`, `.gitignore` per dati, scorie Python e di sistema, primo commit a fotografare lo stato (75 file). La perdita delle sessioni di lavoro precedenti, non più recuperabili dalla cronologia locale, ha reso evidente l'assenza di una storia del progetto.
- Restano aperti, nell'ordine emerso: giro completo end-to-end su un archivio campione con dati persistenti (unico modo per ottenere le metriche mancanti), Skill installabile dichiarata in sessione 7, motore agente integrato, conferma della tassonomia delle tipologie documentali.

### Sessione 16 — 26/07/2026
- Verificata la pulizia della cartella Wikify: nessun contenuto obsoleto; solo scorie tecniche rigenerabili (__pycache__, .DS_Store, un temporaneo del wizard), lasciate in attesa di indicazione.
- Aggiunto il **Reset archivio** (subagente Sonnet, 110 test verdi): card "Manutenzione" in dashboard, pagina di conferma con parola RESET + PIN. Svuota tutti i dati derivati dall'archivio (inventario, scansioni, segnalazioni, triage, catalogo, validazione, sessioni analisi, temporanei import) e conserva dizionario dei pattern, utenti e impostazioni (radice archivio e chiavi analisi_*; rimosse solo le chiavi di stato dell'inventario). VACUUM finale.

### Sessione 15 — 26/07/2026
- Implementato il **connettore MCP** e le **impostazioni di analisi** (specifica in `progettazione_moduli.md` Modulo 4; subagente Sonnet, 105 test verdi, verifica indipendente superata):
  1. **Impostazioni analisi** (sotto-voce di Validazione AI): modelli in cascata (primario default Haiku, rinforzo default Sonnet, soglia confidenza 0,7, rinforzo obbligatorio sui riservato/misto), ambito campione (N progetti, selezione casuale con seed riproducibile) o archivio intero, prezzi per modello per la stima costi.
  2. **Server MCP** (`app/mcp_server/`, FastMCP stdio): 6 strumenti (ottieni_istruzioni, ottieni_incarico, leggi_file, consegna_bozza, ottieni_correzioni, stato_sessione). Il perimetro è imposto lato server: leggi_file rifiuta i file non condivisibili. Configurazione documentata per Claude Code e Claude Desktop.
  3. **Sessioni di analisi con KPI di esito** nella pagina Metriche: progetti assegnati/completati, file perimetro/letti, proposte per campo, distribuzione confidenze, scarti, durata, token e costo stimati; metriche di accuratezza filtrabili per sessione.
- L'import manuale dei JSON resta disponibile; i lotti da import manuale non hanno sessione.

### Sessione 14 — 26/07/2026
- Discussa l'integrazione dell'agente nel tool: fattibile col contratto già congelato; stima sviluppo contenuta (un modulo "motore agente" con fornitore configurabile) e costi di esercizio indicativi (API Haiku ~150-400 € sull'archivio intero, Sonnet ~500-1.500 €, Ollama zero token ma hardware 32-64 GB). Impostazione concordata: **cascata Haiku → Sonnet** (il modello grande solo su confidenza bassa e casi riservatezza misto/riservato), da tarare con le metriche del campione prima di costruire.
- Migliorata la pagina "Perimetro e bozze": spiegazione dettagliata del ciclo agentico in 5 passi ("l'agente propone, l'umano dispone") e download diretto di `istruzioni_agente.md` e `formato_bozze.md` (copiati in `app/docs_agente/`), oltre al perimetro. Suite 80 test verde.

### Sessione 13 — 26/07/2026
- **Decisione**: la parte agentica usa **Claude / Claude Code come agente di rilevazione** (opzione a): infrastruttura identica se in futuro si passerà ad API o modello locale Ollama (per cui servirebbe una classe 27-32B, 32-64 GB RAM).
- Creata `agente/` con il contratto congelato: `formato_bozze.md` (JSON wikify-bozza/1.0: proposte con campo, valore da tassonomia chiusa, confidenza, evidenza obbligatoria con citazione max 300 caratteri) e `istruzioni_agente.md` (procedura per l'agente: perimetro condivisibile vincolante, evidenza sempre, confidenza onesta, sola lettura).
- **Nuova direttiva base registrata su richiesta di Carlo** (in CLAUDE.md e in memoria): scegliere autonomamente il modello dei subagenti per il compromesso costo/risultati (Sonnet per implementazioni ben specificate, modello grande per progettazione, Haiku per compiti banali); nei casi dubbi chiedere prima. Nasce dall'osservazione che i primi 4 subagenti giravano tutti col modello grande.
- Implementato il **modulo Validazione AI** (subagente su Sonnet, come da nuova direttiva): sezione in sidebar dopo Catalogo con "Perimetro e bozze" (export perimetro_condivisibile.json dal triage + import bozze con validazione severa e lotti), "Coda di revisione" (ordinata per confidenza crescente, vista affiancata con estratto reale ed evidenza marcata, azioni Conferma/Correggi/Caso nuovo con tempi, note di conoscenza tacita) e "Metriche" (accuratezza per campo, puri/misti, fasce di confidenza, tempi mediani, export XLSX e JSON correzioni).
- Nota di collaudo: la suite (80 test) falliva se lanciata con `unittest discover` per un difetto latente (argv catturava "discover" e ripiegava su un archivio sintetico senza sottocartelle); corretto con variabile d'ambiente WIKIFY_ARCHIVIO_PROVA e archivio sintetico con sottocartella. Ora verde in entrambe le modalità.

### Sessione 12 — 26/07/2026
- Carlo evolve la Fase 2: non verifica una tantum del XLS ma **nascita del catalogo**: (1) motore di entità logiche con creazione guidata (nome + criterio di autogenerazione, es. "Progetto" dalle cartelle di primo livello con estrazione della chiave dal nome) e (2) **arricchimento deterministico** da fonti tabellari esterne (CSV/XLS) con relazione 1:N nativa (più righe stessa chiave = più valori, es. più codici articolo per progetto), per codici articolo oggi e qualsiasi informazione o tag domani.
- Principi concordati: entità persistenti (riallineamento marca "senza riscontro", mai cancella), conflitti di chiave mostrati e mai risolti in automatico, valori con provenienza e import rimovibili in blocco (rollback), verifiche V1-V6 trasformate in anteprima di qualità prima della conferma dell'import.
- Menu: nuova sezione **"Catalogo"** (tra Classificazione base e Utenti) con sotto-voci "Definizione entità" e "Arricchimento dati".
- Implementato dal subagente (57 test verdi, migrazione verificata da tutte le versioni precedenti): prova live del criterio sui nomi reali delle cartelle, wizard di import in 4 passi, scheda entità con attributi e provenienza, export XLSX di catalogo e anomalie. Aggiornato `progettazione_moduli.md` (Modulo 2 riscritto).

### Sessione 11 — 26/07/2026
- Carlo ridefinisce l'impostazione dell'inventario: non più scansione lanciata a mano, ma **mappa permanente dell'archivio**: inventario iniziale da zero salvato, check automatico a ogni apertura che rileva i file nuovi non mappati, evidenza dei file mai passati dalla scansione di classificazione. Aggiornato `progettazione_moduli.md` (Modulo 1) e chiuso il punto aperto "passata combinata".
- Implementazione (subagente, 41 test verdi, migrazione verificata anche su copia del db reale):
  1. **Impostazioni**: cartella archivio impostata una volta e riusata ovunque (precompilata in Nuova scansione).
  2. **Inventario permanente**: mappa file su DB (solo metadati), check all'apertura con throttling 10 minuti, integrazione dei nuovi, marcatura scomparsi, stato "da classificare" per file (mai scansionato o modificato dopo l'ultima scansione che lo copre).
  3. **Dashboard come home**: rimossa la descrizione, KPI: n. cartelle primo livello, tabella file per cartella con ripartizione per tipo (docx/xlsx/pdf/txt/altro), file da classificare con link diretto alla scansione.
  4. **Sidebar verticale sinistra** collassabile: Dashboard, Classificazione base (Storico, Dizionario; "Nuova scansione" come pulsante nello Storico), Utenti, Password (nuova pagina cambio PIN), Logout.
- Limitazioni note: cartelle di primo livello vuote non mappate; PDF senza testo restano "da classificare"; inventario iniziale sincrono.

### Sessione 10 — 26/07/2026
- Cartella del workshop rinominata da `Workshop/Archivio Smart/` a **`Workshop/Wikify/`**, allineata al nome del progetto. Aggiornati i percorsi citati nei documenti e i nomi visibili nell'app (titolo, benvenuto, home, export dizionario). Invariati per compatibilità gli identificatori tecnici: nome database, variabile d'ambiente ARCHIVIO_SMART_DATA, nomi tabelle.

### Sessione 9 — 26/07/2026
- **Il tool ha un nome: Wikify**, claim "Trasforma un archivio in una wiki". Carlo fornisce il logo (immagine generata AI): scontornato (bianco su trasparente, rimossi sfondo a scacchiera e artefatti) e salvato in `brand/wikify_logo_bianco.png` + versione header in `app/static/`.
- Riorganizzati header e footer dell'app: header blu con logo in alto a sinistra e claim sotto, nome utente connesso a destra; sotto, barra menu blu profondo con hamburger apribile/chiudibile (stato ricordato); footer con disclaimer fisso: "Questo prototipo è stato generato e integrato con il supporto di sistemi AI generativi, sotto la supervisione e l'architettura tecnica di Carlo Verdini (IT System Integrator & AI Trainer). ✉️ cverdini@gmail.com".
- Creata `brand/branding.md` con l'identità completa e le note per la futura skill (che dovrà applicare nome, logo, claim e disclaimer al prototipo generato). Chiarito inoltre che l'app è locale: il browser è solo l'interfaccia, nessun dato lascia la macchina; eventuale pacchettizzazione PyInstaller rimandata.
- In sospeso: pulsante "Sfoglia" per la scelta cartella (esplora cartelle interno all'app, proposto e non ancora confermato).

### Sessione 8 — 26/07/2026
- Primo riscontro d'uso di Carlo sull'app, cinque interventi richiesti e realizzati (subagente, 26 test superati, migrazione db automatica al primo avvio):
  1. **Fix export XLSX**: causa individuata nei caratteri di controllo presenti nei testi estratti (IllegalCharacterError di openpyxl); introdotta sanificazione unica delle celle (controlli, None, testi oltre 32767 caratteri, formule apparenti).
  2. **Consultazione raggruppata per file**: accordion per file con badge di severità e stato; dentro le segnalazioni, in pedice la riga di triage.
  3. **Campi motivazione e vincolo estesi** (textarea); triage passato a granularità per file (tabella nuova, la precedente conservata per compatibilità).
  4. **Anagrafica utenti e login nome+PIN** (hash PBKDF2): validatore e data assegnati automaticamente dall'utente connesso.
  5. **Coda di lavoro**: commutatore Da fare/Verificati/Tutti; Riservato e Condivisibile marcano il file come verificato e lo tolgono dalla coda, Da valutare lo mantiene; avanzamento triage visibile nello storico.
- Limitazioni note: i vecchi triage per file+regola non vengono convertiti (file da rivalutare nella nuova UI); nessun blocco per tentativi PIN ripetuti (uso locale).

### Sessione 7 — 26/07/2026
- **Nuovo obiettivo dichiarato da Carlo**: creare una **Skill** installabile su Claude Code o Codex che guidi un utente nell'eseguire l'analisi, lo porti in condizione di scegliere tra gli approcci e lo aiuti a realizzare il tool completo. Il presente workshop diventa quindi anche il materiale sorgente della skill.
- Verificata la completezza della documentazione prima di proseguire: presenti `analisi.md` (registro e decisioni), `assessment.md` (piano operativo), `progettazione_moduli.md` (moduli futuri), `scanner/` (CLI + dizionario + README) e `app/` (Workbench completa). Registro allineato con le sessioni 6 e 7.
- Nota sulla natura del registro: è una **sintesi ragionata** di ogni scambio (contesto, alternative discusse, decisione, motivazione), non una trascrizione parola per parola; le informazioni operative per costruire la skill sono tutte nei cinque artefatti sopra.

### Sessione 6 — 26/07/2026
- Fornite le istruzioni di avvio dell'app sul Mac (Terminale, pip install, `python3 app.py`, browser su 127.0.0.1:5000).
- Chiarimenti funzionali richiesti da Carlo: (1) le 13 regole precaricate sono solo un seme dimostrativo, per cercare informazioni del tutto diverse si creano nuove regole dal builder e si disattivano/eliminano le esistenti, la scansione usa solo le regole attive; (2) formati analizzati: docx, xlsx/xlsm, PDF nativi, txt/csv/md/log/ini/cfg/json/xml; non analizzati ma segnalati con motivo: PDF scansionati (no OCR), legacy doc/xls/ppt, altre estensioni. Se la riga S2 della sintesi rivelasse quote rilevanti di legacy/scansioni, si valuteranno conversione automatica e OCR.

### Sessione 5 — 25/07/2026
- Emersa esigenza di usabilità: astrarre la costruzione dei pattern per chi non conosce le regex. Decisione: **mini applicazione web locale** (Flask + SQLite, Mac e Windows) con builder guidato del dizionario, lancio scanner, storico e consultazione scansioni.
- Discussa l'alternativa tool indipendenti vs base modulare. **Decisione: base modulare unica** ("Archivio Smart Workbench"): core condiviso (estrazione, walk, db) + un modulo per fase; costo aggiuntivo stimato ~15%, ripagato dagli incroci tra fasi e dalla sintesi S1-S10 autocompilabile.
- Un subagente ha costruito la base + modulo Scanner in `app/`: builder pattern in 6 tipi guidati con prova live, scansione con avanzamento, storico, consultazione con triage integrato (registro di segregazione su DB), export XLSX compatibile col report CLI. Suite di 36 verifiche superata.
- In parallelo redatto `progettazione_moduli.md`: progettazione dei moduli Inventario (Fase 1), Verifica XLS (Fase 2) e Interfaccia di validazione (Fase 3B) con schemi tabelle, viste UI, roadmap di integrazione e punti aperti (passata combinata, formato JSON bozze agente, tassonomia tipologie, versioning XLS).

### Sessione 4 — 25/07/2026
- Realizzato lo **scanner del Metodo A** in `scanner/`: script Python (`scan_riservatezza.py`), dizionario YAML di partenza (13 regole in 6 categorie: credenziali, interconnessione, configurazione, cliente, sperimentazione, marcature esplicite) e README.
- Il report XLSX prodotto contiene: segnalazioni con evidenza e posizione puntuale, riepiloghi per file e categoria, file non analizzati (legacy/scansioni), e il **registro di segregazione precompilato** pronto per il triage con menu Riservato/Condivisibile/Da valutare.
- Testato con esito positivo su un archivio simulato: intercettato correttamente il caso "documento misto" (manuale con capitolo di configurazione riservato), la marcatura esplicita su PDF, i formati legacy; i file senza pattern vengono indicati per il campionamento di controllo dei falsi negativi.

### Sessione 3 — 25/07/2026
- Carlo solleva un'area di attenzione preliminare: non c'è ancora consapevolezza della riservatezza dei contenuti, quindi non si può assumere che siano condivisibili con un agente AI. Propone due approcci: **A) deterministico** (scanner Python locale su pattern testuali) e **B) agentico** (quello già previsto).
- Aggiornato `assessment.md`: la Fase 3 diventa una **strategia a due metodi in sequenza** con nota comparativa pro/contro. Il Metodo A bonifica il perimetro in locale, il triage del responsabile tecnico qualifica le segnalazioni, il Metodo B opera solo sul condivisibile. Retroazione: ciò che B scopre arricchisce il dizionario dei pattern di A.
- Introdotto il **registro di segregazione** (riservato/condivisibile/da valutare, con motivazione e vincoli cliente): alimentato progressivamente man mano che le informazioni vengono qualificate, è il primo nucleo della tassonomia di riservatezza e la base del futuro security trimming.
- Regola prudenziale adottata: il non ancora qualificato è trattato come riservato.

### Sessione 2 — 25/07/2026
- Carlo valida il documento di analisi e chiede di passare all'assessment a livello pratico.
- Creato `assessment.md`: piano operativo in 5 fasi (scansione automatica, analisi XLS, campione manuale, discovery uffici, sintesi) con schede di rilevazione e tabella delle informazioni chiave S1-S10 che alimenteranno le scelte progettuali.
- Su proposta di Carlo, la Fase 3 evolve da esame manuale a **esame assistito da agente**: l'agente compila le schede in bozza con evidenze citate, il responsabile tecnico valida tramite un'**interfaccia di validazione** dedicata (coda per confidenza, vista affiancata, azioni rapide, tracciamento correzioni).
- **Decisione**: l'interfaccia di validazione nasce come prototipo nell'assessment ma è progettata per diventare il modulo di validazione umana della futura pipeline di classificazione; le metriche raccolte (accuratezza, correlazione confidenza/errore, tempo per scheda) stimeranno l'affidabilità della pipeline a regime.

### Sessione 1 — 25/07/2026
- Carlo definisce le specifiche del workshop (v. §1).
- Creata la struttura `Workshop/Archivio Smart/` con il presente file.
- Claude propone la scomposizione in tre dimensioni (§2.1) e l'ipotesi di soluzione ibrida (§2.2).
- Domande aperte poste a Carlo (v. §4).

---

## 4. Risposte di Carlo (Sessione 1)

1. **Tipo di domande**: dalla prima discovery emergono prevalentemente **ricerche esatte** ("specifiche di configurazione articolo X", "manuale di installazione articolo Y", "compatibilità tra articolo A e articolo B"). Da tenere comunque in considerazione anche domande esplorative e confronti/sintesi. Richiesta esplicita: analizzare **come cambia l'architettura al variare delle esigenze**.
2. **Volumi**: qualche migliaio di cartelle progetto (chiarita la scala di riferimento in §5.2).
3. **Permessi**: granularità **per informazione, non per documento**. Implicazione dichiarata: la razionalizzazione deve prevedere **scomposizione e classificazione** delle informazioni.
4. **Obiettivo**: prima fase progettuale, poi PoC.

---

## 5. Analisi — come le risposte orientano l'architettura

### 5.1 Come cambia l'architettura in base al tipo di domanda

Le tre famiglie di domande sollecitano componenti architetturali diversi. Conviene ragionare per livelli, dove ogni livello abilita la famiglia successiva.

**a) Ricerche esatte (esigenza prevalente)**
"Specifiche di configurazione dell'articolo X" non è una domanda semantica: è una **navigazione strutturata**. Richiede:
- un **catalogo** (articolo → progetto → documenti classificati per tipologia);
- **metadati affidabili** su ogni documento (tipologia, articolo/progetto di riferimento, livello di riservatezza);
- la "compatibilità tra A e B" richiede in più che le **relazioni tra entità** (sonda ↔ controller ↔ porta sonda ↔ articolo) siano modellate esplicitamente.

Architettura minima sufficiente: **DB relazionale (o documentale) + interfaccia di navigazione guidata**. Non serve alcun componente AI: serve un buon modello dati. Il file XLS progetti↔articoli è l'embrione di questo catalogo.

**b) Domande esplorative ("quale sonda regge 150°C in ambiente umido?")**
Qui la risposta è dentro i contenuti, non nei metadati. Richiede in aggiunta:
- **indicizzazione dei contenuti**: full-text come base, **indice vettoriale (embedding)** per la ricerca semantica;
- una pipeline di **estrazione testo** dai formati eterogenei (Word, Excel, PDF, TXT);
- opzionalmente un **LLM in modalità RAG** per formulare la risposta citando le fonti.

Architettura: livello (a) + **motore di retrieval semantico**. Il catalogo resta indispensabile: il retrieval deve essere **filtrato dai metadati** (per articolo, per tipologia, per permesso) prima della ricerca semantica, altrimenti precisione e governance degradano.

**c) Confronti e sintesi (tabella comparativa tra controller, riepiloghi)**
Richiede aggregazione da più documenti. Due strade complementari:
- **estrazione strutturata a monte**: le caratteristiche chiave (range temperatura, protocolli, tensioni) vengono estratte una volta e salvate come dati tabellari → i confronti diventano query esatte, affidabili e ripetibili;
- **sintesi LLM a valle** su più documenti recuperati → flessibile ma con esito meno controllabile.

Un **knowledge graph** (l'approccio Grapify/LLM-Wiki) è la formalizzazione della prima strada: entità + attributi + relazioni. Per un dominio a entità ben definite come questo (sonde, controller, porta sonda, articoli) è particolarmente adatto.

**Sintesi**: l'architettura è **incrementale, non alternativa**. Il catalogo strutturato serve comunque; il retrieval semantico si aggiunge per l'esplorativo; l'estrazione strutturata/graph si aggiunge per confronti affidabili. La scelta non è "quale tecnologia" ma "fino a quale livello spingersi e in che ordine".

### 5.2 Volumi — scala di riferimento

Chiarimento richiesto: la scala usata era indicativa. Con **qualche migliaio di cartelle progetto** e, ipotizzando 10-50 file per cartella, si stimano **10.000-100.000+ documenti**. Implicazioni:
- volume medio-grande per un contesto aziendale: **esclude approcci artigianali** (indicizzazione manuale integrale) e richiede una **pipeline automatizzata** di ingestione e classificazione;
- pienamente gestibile da tecnologie standard (PostgreSQL, motori vettoriali come Qdrant/pgvector, Elasticsearch): **nessun vincolo di scala** sulla scelta architetturale;
- il costo rilevante non è tecnologico ma di **qualità dei dati**: quanti documenti hanno nomi/struttura uniformi? Il punto andrà verificato con un assessment su un campione.

### 5.3 Permessi per informazione — l'implicazione più strutturante

La granularità "per informazione, non per documento" è la scelta con l'impatto architetturale maggiore. Comporta che:
- lo stesso documento può contenere informazioni a visibilità diversa (es. un manuale con una sezione di parametri riservati);
- l'unità di gestione non è il file ma l'**unità informativa**: il documento va **scomposto** (chunking consapevole, per sezioni logiche) e ogni unità **classificata** (tipologia + livello di riservatezza + eventuale vincolo cliente);
- il modello di sicurezza deve applicarsi **al livello del retrieval**: l'indice interrogato deve restituire solo unità autorizzate per il profilo richiedente (security trimming), non filtrare a valle;
- questo requisito, di fatto, **impone la razionalizzazione dell'informazione** che era già emersa come esigenza: la classificazione non è un costo accessorio, è il cuore del progetto.

Nota di attenzione: la classificazione di decine di migliaia di unità informative non può essere interamente manuale. Ipotesi da esplorare: classificazione assistita da LLM con validazione umana a campione, partendo da regole deterministiche dove possibile (tipologia documento, posizione nella cartella progetto).

### 5.4 Prima ipotesi architetturale (da validare)

```
[Archivio file esistente]
        │  ingestione + estrazione testo
        ▼
[Pipeline di scomposizione e classificazione]
   (unità informative + metadati + livello riservatezza)
        │
        ├──► [Catalogo strutturato]  ← migrazione XLS progetti/articoli
        │      entità, relazioni, permessi
        │
        ├──► [Indice full-text + vettoriale]
        │      con security trimming sui metadati
        │
        └──► (fase 2) [Knowledge graph caratteristiche tecniche]

[Interfaccia guidata]
   ricerca esatta (catalogo) + ricerca semantica (indice) + profili di accesso
```

---

## 6. Decisioni prese

- (25/07/2026) Percorso: **prima fase progettuale, poi PoC**.
- (25/07/2026) Esigenza primaria: ricerche esatte; esplorative e sintesi da presidiare come evoluzione.
- (25/07/2026) Granularità permessi: **per unità informativa** → la scomposizione/classificazione entra nel perimetro del progetto come attività centrale.
- (25/07/2026) Fase 3 assessment: rilevazione **assistita da agente** con validazione umana tramite interfaccia dedicata; l'interfaccia prototipo sarà riutilizzata come modulo di validazione della pipeline di classificazione.
- (25/07/2026) Riservatezza verso l'AI: **sequenza Metodo A → Metodo B**. Scanner deterministico locale e triage umano prima di qualunque esposizione di contenuti all'agente; registro di segregazione come artefatto centrale; default prudenziale "riservato" per il non qualificato. Lo scanner A diventerà a regime il presidio di sicurezza della pipeline di ingestione.

---

## 7. Prossimi passi proposti

1. **Assessment dell'archivio esistente** su un campione di cartelle progetto: uniformità di struttura, nomenclatura, formati, qualità del file XLS progetti↔articoli.
2. **Modello informativo**: definire entità, relazioni, tipologie di unità informativa e tassonomia dei livelli di riservatezza.
3. **Matrice dei criteri di scelta** tecnologica valorizzata sul caso (da §2.3).
4. Definizione del **perimetro del PoC** (quali domande dimostrare, su quale campione).
