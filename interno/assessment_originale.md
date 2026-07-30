# Assessment dell'archivio esistente: Piano operativo

Obiettivo: fotografare lo stato reale dell'archivio (struttura, qualità, uniformità, criticità) e raccogliere le informazioni chiave necessarie per impostare il modello informativo, la pipeline di ingestione e il perimetro del PoC.

Principio guida: l'assessment combina **rilevazione automatica** (estensiva, su tutto l'archivio) e **rilevazione manuale** (intensiva, su un campione). La prima misura, la seconda interpreta.

---

## Fase 0: Preparazione

| Attività | Dettaglio | Esito da registrare |
|---|---|---|
| 0.1 Accesso all'archivio | Percorso di rete/locale, modalità di accesso in sola lettura | Percorso radice, eventuali vincoli |
| 0.2 Copia di lavoro del file XLS progetti↔articoli | Snapshot datato, non lavorare sull'originale | Nome file, data snapshot |
| 0.3 Strumenti | Script di scansione (Python), foglio di raccolta dati | Conferma disponibilità |

**Regola**: nessuna modifica all'archivio originale durante tutto l'assessment.

---

## Fase 1: Scansione automatica dell'intero archivio

Uno script percorre l'albero delle cartelle e produce un **inventario** (CSV/XLSX). Nessuna lettura dei contenuti in questa fase: solo metadati di filesystem.

### 1.1 Dati da rilevare per ogni file
- percorso completo e profondità nell'albero
- nome cartella progetto di appartenenza (primo livello sotto la radice)
- estensione e formato
- dimensione
- data creazione e ultima modifica

### 1.2 Metriche da calcolare (KPI di struttura)

| KPI | Cosa indica | Perché conta |
|---|---|---|
| N. cartelle progetto totali | Dimensione reale del problema | Dimensionamento pipeline |
| Distribuzione file per formato | % doc/docx, xls/xlsx, pdf, txt, altro | Effort di estrazione testo per formato |
| Distribuzione file per cartella (min/mediana/max) | Uniformità dei progetti | Cartelle anomale da esaminare |
| Profondità e varietà delle sottocartelle | Esiste una struttura ricorrente? | Se sì, la struttura è un metadato gratuito |
| Pattern di nomenclatura file | % file il cui nome segue uno schema riconoscibile | La nomenclatura è la prima fonte di classificazione automatica |
| Distribuzione temporale (anno ultima modifica) | Progetti attivi vs storici | Possibile perimetrazione per fasi |
| File "sospetti" | Copie ("copia di", "v2", "old"), file vuoti, formati esotici | Stima del rumore da bonificare |

### 1.3 Output
`rilevazioni/inventario_archivio.xlsx` con un foglio "dettaglio file" e un foglio "KPI".

---

## Fase 2: Analisi del file XLS progetti ↔ articoli

Il file è l'embrione del futuro catalogo: va misurata la sua affidabilità.

### 2.1 Verifiche
1. **Copertura**: ogni cartella progetto dell'inventario ha almeno una riga nel XLS? E viceversa, ogni progetto citato nel XLS ha una cartella? (incrocio con Fase 1)
2. **Chiavi**: i codici progetto e articolo sono univoci e scritti in modo uniforme? (maiuscole, spazi, zeri iniziali)
3. **Cardinalità**: distribuzione articoli per progetto (1:1, 1:N, casi anomali N:M)
4. **Completezza colonne**: quali attributi esistono già (famiglia, descrizione, stato) e quale % di celle è valorizzata
5. **Storicizzazione**: come vengono gestiti articoli dismessi o progetti superati?

### 2.2 Output
Sezione "qualità XLS" nel foglio KPI: % copertura incrociata, n. anomalie per tipo, elenco casi da chiarire con l'ufficio tecnico.

---

## Fase 3: Esame del campione: strategia a due metodi

### Premessa: il vincolo di riservatezza verso l'AI

È emersa un'area di attenzione preliminare: non essendo ancora nota la natura e la riservatezza delle informazioni contenute nell'archivio, non è possibile assumere che tali contenuti siano condivisibili con un agente AI (in particolare se basato su servizi esterni). Il problema è circolare: per classificare la riservatezza servirebbe leggere i contenuti, ma leggerli con un agente presuppone di averne già valutato la condivisibilità.

La strategia adottata scioglie la circolarità con **due metodi in sequenza**:

- **Metodo A: deterministico**: scansione algoritmica in Python, eseguita interamente in locale, che rileva pattern testuali riconducibili a informazioni riservate e li evidenzia in un report. Nessun contenuto esce dal perimetro aziendale.
- **Metodo B: agentico**: l'esame assistito da agente con validazione umana (descritto da §3.2 in poi), applicato **solo ai materiali che il Metodo A e la validazione del responsabile tecnico hanno qualificato come condivisibili**.

### Nota comparativa

| Criterio | Metodo A (deterministico) | Metodo B (agentico) |
|---|---|---|
| Esposizione dei dati | Nessuna: elaborazione locale | Contenuti trasmessi all'LLM (mitigabile con modelli on-premise) |
| Riproducibilità | Totale: stesso input, stesso output, auditabile | Non deterministica: esiti variabili, richiede tracciamento |
| Capacità di rilevazione | Solo pattern noti a priori (regex, parole chiave, formati codici) | Comprende il contesto: coglie riservatezza implicita e casi non previsti |
| Falsi negativi | Rischio alto sul non previsto: ciò che non è nei pattern non viene visto | Rischio più basso, ma non azzerato e non garantito |
| Falsi positivi | Frequenti (pattern generici), ma economici da scartare in revisione | Più rari, motivati con evidenza citata |
| Costo di avvio | Richiede di costruire il dizionario dei pattern con il responsabile tecnico | Pronto all'uso, ma richiede governance della condivisione |
| Costo di manutenzione | Dizionario da mantenere nel tempo | Prompt e tassonomie da raffinare |
| Valore aggiuntivo | Il dizionario dei pattern resta un asset di sicurezza permanente | Prototipa la futura pipeline di classificazione |

**Considerazione di sintesi**: i due metodi non sono in competizione, presidiano rischi diversi. Il Metodo A è lo strumento adatto quando l'errore da evitare è l'esposizione (meglio un falso positivo che un dato riservato condiviso); il Metodo B è lo strumento adatto quando l'errore da evitare è la classificazione povera (meglio comprendere il contesto che applicare regole cieche). Usarli in sequenza consente di ottenere entrambe le garanzie.

### Sequenza operativa adottata

1. **Costruzione del dizionario dei pattern** con il responsabile tecnico: quali dati sono certamente riservati? Ipotesi di partenza: parametri di configurazione, chiavi/credenziali di interconnessione, riferimenti a clienti specifici, codici commessa cliente, dati di sperimentazione non pubblicati. Per ciascuno: pattern testuali rilevabili (etichette ricorrenti, formati di codice, intestazioni di sezione).
2. **Scansione deterministica (Metodo A)** sul campione: report per file con pattern rilevati, posizione, contesto (riga o cella). Nessun contenuto lascia il perimetro.
3. **Triage del responsabile tecnico** sul report: ogni segnalazione viene marcata **Riservato** o **Condivisibile**; i file senza segnalazioni vengono comunque campionati a controllo per stimare i falsi negativi.
4. **Segregazione progressiva**: man mano che le informazioni vengono qualificate, il **registro di segregazione** (v. sotto) viene aggiornato. Regola prudenziale: ciò che non è ancora stato qualificato è trattato come riservato (default: non condivisibile).
5. **Esame agentico (Metodo B)** sui soli materiali condivisibili: l'agente opera con la garanzia che il perimetro è stato bonificato. Le sezioni riservate risultano escluse o mascherate.
6. **Retroazione**: i casi in cui il Metodo B individua indizi di riservatezza sfuggiti al Metodo A vengono ricondotti al dizionario dei pattern, che si arricchisce.

### Registro di segregazione

Artefatto centrale della fase, alimentato progressivamente: `rilevazioni/registro_segregazione.xlsx`

| Campo | Descrizione |
|---|---|
| File / sezione | Riferimento puntuale (file, foglio, capitolo, intervallo righe) |
| Pattern rilevato | Quale regola l'ha individuato (o "triage manuale") |
| Qualifica | Riservato / Condivisibile / Da valutare |
| Motivazione | Criterio applicato dal responsabile tecnico |
| Vincolo | Eventuale restrizione specifica (es. visibile solo a cliente X) |
| Data e validatore | Tracciamento della decisione |

Questo registro non è un sottoprodotto dell'assessment: è il **primo nucleo della tassonomia di riservatezza** del progetto e la base dati con cui verrà configurato il security trimming del sistema finale.

**Nota di prospettiva sul Metodo A**: come l'interfaccia di validazione, anche lo scanner deterministico non è un usa-e-getta. A regime diventerà il **presidio di sicurezza della pipeline di ingestione**: ogni nuovo documento passa prima dallo scanner, e solo ciò che risulta condivisibile prosegue verso l'indicizzazione accessibile all'AI.

---

## Fase 3B: Esame del campione assistito da agente (Metodo B)

Impostazione: un **agente di rilevazione** compila le schede in bozza; il **responsabile tecnico valida tramite un'interfaccia dedicata**. Le correzioni del validatore misurano il tasso di errore dell'agente. Questa fase è, di fatto, il **prototipo della futura pipeline di classificazione**: se l'approccio regge sul campione, l'architettura "classificazione assistita da LLM con revisione umana" risulta validata su dati reali.

Perimetro: opera esclusivamente sui materiali qualificati come **condivisibili** nel registro di segregazione.

### 3.1 Costruzione del campione
Campionamento **stratificato**, non casuale puro: 15-20 cartelle progetto così composte:
- copertura delle tre famiglie (sonde, controller, porta sonda)
- mix di progetti recenti e storici (dalla distribuzione temporale di Fase 1)
- 2-3 cartelle "anomale" segnalate dai KPI (troppi file, pochissimi file, naming irregolare)
- 1-2 progetti indicati dall'ufficio tecnico come "ben tenuti" (rappresentano lo standard ideale)

### 3.2 Agente di rilevazione

**Input**: cartelle del campione + inventario di Fase 1 + estratto XLS progetti↔articoli (per il contesto: famiglia, articoli collegati).

**Elaborazione, per ogni cartella**:
1. estrazione testo da ogni file (Word, Excel, PDF nativo; i PDF scansionati vengono marcati "non estraibile → OCR" senza bloccare il flusso);
2. classificazione di ogni documento per **tipologia** (specifica tecnica, manuale installazione, manuale manutenzione, parametri interconnessione, dati sperimentazione, configurazione, disegno, corrispondenza, altro), con **grado di confidenza** dichiarato;
3. rilevazione di struttura, versioni multiple (proposta del candidato "ufficiale"), forma delle caratteristiche tecniche (tabellare/prosa);
4. **proposta di classificazione di riservatezza** per documento e, dove il documento appare misto, segnalazione delle sezioni a visibilità presumibilmente diversa, con motivazione;
5. compilazione della **scheda in bozza** (sezioni A, B, C, D proposte; sezione E lasciata al rilevatore umano).

**Output**: schede precompilate in formato strutturato (JSON + resa leggibile) in `rilevazioni/schede_campione/bozze/`.

**Regola di trasparenza**: ogni valutazione dell'agente deve citare l'evidenza (nome file, sezione, frase) che l'ha generata. Nessuna classificazione senza fonte.

### 3.3 Interfaccia di validazione (prototipo funzionale)

Interfaccia web leggera che agevola il controllo del responsabile tecnico. Requisiti del prototipo:

| Requisito | Descrizione |
|---|---|
| Coda di revisione | Elenco schede in bozza, ordinabile per confidenza crescente (prima i casi dubbi) |
| Vista affiancata | A sinistra il documento (o l'estratto rilevante), a destra la proposta dell'agente con l'evidenza citata |
| Azioni rapide | Conferma / Correggi (con selezione da tassonomia) / Segnala caso nuovo, per singola classificazione |
| Riservatezza mista | Possibilità di confermare o ridisegnare il confine tra sezioni pubbliche e riservate indicato dall'agente |
| Note libere | Campo per la conoscenza tacita emersa durante la revisione (alimenta la sezione E) |
| Tracciamento | Ogni conferma/correzione registrata con autore e data: è il dataset di misura dell'affidabilità |

**Nota di prospettiva**: questa interfaccia non è un usa-e-getta dell'assessment. Il prototipo, verificato sul campione, diventerà il **modulo di validazione umana della pipeline di classificazione** dell'archivio completo. Le tassonomie confermate e le correzioni raccolte costituiranno inoltre i primi esempi per il raffinamento dei prompt di classificazione.

### 3.4 Metriche della fase

| Metrica | Cosa misura |
|---|---|
| Accuratezza classificazione tipologia | % proposte agente confermate senza correzione |
| Accuratezza riservatezza | % proposte confermate; da leggere separatamente per documenti "puri" e "misti" |
| Correlazione confidenza/errore | La confidenza dichiarata dall'agente è predittiva? (serve a calibrare le soglie di revisione futura) |
| Tempo di validazione per scheda | Stima dell'effort umano nella pipeline a regime |
| Casi non previsti dalla tassonomia | Tipologie o livelli di riservatezza emersi non contemplati |

### 3.5 Scheda di rilevazione per cartella progetto
Il template resta il riferimento del contenuto informativo, compilato in bozza dall'agente e finalizzato in validazione:

```
CODICE PROGETTO:            FAMIGLIA: sonda / controller / porta sonda
ARTICOLI COLLEGATI (da XLS):
DATA ESAME:                 ESAMINATORE:

A. STRUTTURA
- La cartella segue una struttura riconoscibile? (sì/parziale/no)
- Sottocartelle presenti e loro funzione:

B. TIPOLOGIE DOCUMENTALI PRESENTI (spuntare + n. file)
[ ] Specifiche tecniche          [ ] Dati di sperimentazione
[ ] Manuale installazione        [ ] Manuale manutenzione
[ ] Parametri interconnessione   [ ] Configurazioni
[ ] Disegni/schemi               [ ] Corrispondenza
[ ] Altro (specificare):

C. QUALITÀ DEI CONTENUTI (per le tipologie chiave)
- Il documento è identificabile dal nome file? (sì/no)
- Testo estraibile? (nativo / PDF scansionato / immagini / tabelle complesse)
- Versioni multiple dello stesso documento? Quale è l'ufficiale?
- Le caratteristiche tecniche chiave sono in forma tabellare o in prosa?

D. RISERVATEZZA (prova pratica della granularità "per informazione")
- Documenti interamente pubblici:
- Documenti interamente riservati:
- Documenti MISTI (sezioni pubbliche + sezioni riservate) → elencare e
  descrivere dove sta il confine (es. "manuale X: cap. 1-4 generici,
  cap. 5 parametri riservati"):

E. NOTE E SEGNALI
- Informazioni che esistono solo nella testa dei referenti (emerse a voce):
- Difficoltà incontrate nel reperire un'informazione tipo:
```

Il punto **D è il più importante**: verifica sul campo quanto è frequente il caso "documento misto", che è ciò che giustifica (o ridimensiona) il requisito dei permessi per unità informativa.

### 3.6 Output
`rilevazioni/schede_campione/` schede validate + tabella riepilogativa + report metriche di affidabilità dell'agente (§3.4).

---

## Fase 4: Discovery con gli uffici

### 4.1 Ufficio commerciale (i richiedenti)
Raccogliere le **ultime 20-30 richieste reali** fatte all'ufficio tecnico (da email, a memoria, da ticket se esistono). Per ognuna registrare:

| Campo | Esempio |
|---|---|
| Richiesta testuale | "Mi serve il range di temperatura della sonda dell'articolo AB-102" |
| Tipo | esatta / esplorativa / confronto-sintesi |
| Informazione risolutiva | valore in una tabella della specifica tecnica |
| Documento sorgente | specifica tecnica progetto P-0045 |
| Tempo medio di evasione oggi | 2 giorni |
| Riservatezza dell'informazione | pubblica |

Questa tabella diventerà il **set di domande di collaudo del PoC**: se il futuro sistema risponde bene a queste 20-30 richieste reali, il progetto funziona.

### 4.2 Ufficio tecnico (i custodi)
Domande guida:
1. Esiste una procedura scritta di archiviazione? Viene seguita?
2. Chi decide cosa è riservato oggi? Con quale criterio?
3. Quali richieste del commerciale sono più onerose da evadere e perché?
4. Ci sono informazioni chiave non presenti nei documenti (conoscenza tacita)?
5. L'archivio è alimentato ancora oggi con nuove cartelle? Con che frequenza?

L'ultima domanda è strutturale: distingue un progetto di **migrazione una tantum** da un sistema che richiede una **pipeline di ingestione continua**.

### 4.3 Output
`rilevazioni/richieste_commerciale.xlsx` + note discovery tecnico in questo file (§ Registro rilevazioni).

---

## Fase 5: Sintesi e informazioni chiave per il progetto

Al termine, compilare la tabella di sintesi: ogni riga è un'informazione chiave che condiziona una scelta progettuale.

| # | Informazione chiave | Valore rilevato | Impatto progettuale |
|---|---|---|---|
| S1 | N. progetti / n. file / GB totali | | dimensionamento |
| S2 | % file con testo estraibile nativamente | | effort pipeline estrazione (OCR sì/no) |
| S3 | % cartelle con struttura riconoscibile | | classificazione da struttura vs da contenuto |
| S4 | % file con nomenclatura affidabile | | classificazione automatica da naming |
| S5 | Qualità XLS (copertura, univocità chiavi) | | il XLS è migrabile o va ricostruito |
| S6 | Frequenza documenti "misti" (riservatezza) | | conferma/ridimensiona permessi per unità informativa |
| S7 | Distribuzione tipi di richiesta commerciale | | priorità: catalogo vs retrieval semantico |
| S8 | Caratteristiche tecniche: tabellari o in prosa | | fattibilità estrazione strutturata / graph |
| S9 | Archivio ancora alimentato? | | migrazione una tantum vs pipeline continua |
| S10 | Conoscenza tacita rilevante | | serve un'attività di formalizzazione dedicata |

Questa tabella è il **ponte tra assessment e progetto**: verrà riportata in `analisi.md` e ogni valore alimenterà la matrice dei criteri di scelta tecnologica.

---

## Organizzazione dei materiali

```
Workshop/Wikify/
├── analisi.md                  ← registro del percorso e decisioni
├── assessment.md               ← questo piano
└── rilevazioni/
    ├── inventario_archivio.xlsx    (Fase 1 + 2)
    ├── schede_campione/            (Fase 3)
    └── richieste_commerciale.xlsx  (Fase 4)
```

---

## Registro rilevazioni

_(da compilare durante l'esecuzione delle fasi)_

| Data | Fase | Attività svolta | Esito / rimando |
|---|---|---|---|
| | | | |
