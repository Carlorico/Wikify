# Il percorso D.2.1 Data Analytics, in sintesi

Cinque sessioni, un filo unico: dal riconoscere che cosa si ha in mano, al decidere che
cosa costruirci sopra. Questa sintesi serve a riusare i concetti fuori dall'aula.

---

## S1: Mappatura di dominio, dati e obiettivi

**Domanda della sessione**: che cosa abbiamo, chi lo tocca, a che cosa dovrebbe servire.

- **La piramide DIKW**: dato (fatto grezzo, senza contesto), informazione (dato collocato in
  un contesto, risponde a un "cosa"), conoscenza (il pattern che lega più informazioni e
  fonda una decisione), saggezza (l'uso esperto della conoscenza). Serve a collocare le
  richieste: quasi sempre chi chiede "dati" vuole conoscenza.
- **Tipi di dato**: strutturato (schema fisso), semi-strutturato (schema flessibile),
  non strutturato (documenti, testo libero). Determinano gli strumenti ammissibili.
- **Il Catalogo Dati**: per ogni sorgente: nome, proprietario, contenuto, granularità,
  frequenza di aggiornamento, chiavi, qualità percepita, vincoli d'accesso. È il primo
  deliverable e la base di tutto il resto.
- **I ruoli intorno al dato**: chi lo produce, chi lo custodisce, chi lo consuma, chi ne
  risponde. Il collo di bottiglia organizzativo si vede qui, prima che nei sistemi.
- **I livelli decisionali**: operativo, tattico, strategico. La stessa informazione serve a
  tre livelli con granularità e tempestività diverse.
- **Il Catalogo Obiettivi**: dalle domande di business alle informazioni necessarie, e da
  queste alla richiesta dati. È il ponte fra ciò che si vuole sapere e ciò che si possiede.
- **Il data swamp**: che cosa succede quando si accumula senza governare.

## S2: Preparare il dato

**Domanda della sessione**: come si passa dal grezzo all'analizzabile senza perdere fiducia.

- **Dal grezzo all'analizzabile**: normalizzazione, deduplicazione, gestione dei mancanti,
  tipizzazione, unità di misura coerenti.
- **L'architettura a livelli Bronze / Silver / Gold**: dato grezzo conservato com'è, dato
  pulito e conformato, dato pronto per il consumo. Il valore sta nel non sovrascrivere mai
  il livello precedente.
- **Le chiavi che legano le fonti**: chiavi naturali e surrogate, join, cardinalità, il
  problema delle corrispondenze parziali. È qui che la maggior parte dei progetti si
  arena.
- **Le dimensioni della qualità**: accuratezza (i valori sono corretti), completezza (non
  mancano), coerenza (non si contraddicono tra fonti), tempestività (sono aggiornati),
  unicità (non duplicati), validità (rispettano il dominio ammesso).
- **Affidabilità e fiducia**: la qualità non è una proprietà del dato ma del processo che lo
  produce; va misurata e dichiarata, non affermata.

## S3: Analisi descrittiva (e diagnostica)

**Domanda della sessione**: che cosa dicono i numeri, e perché è successo.

- **I quattro livelli dell'analisi**: descrittiva (che cosa è successo), diagnostica
  (perché), predittiva (che cosa succederà), prescrittiva (che cosa conviene fare). Si
  procede in ordine: saltare un livello produce risposte non difendibili.
- **L'espressività di ciò che già si ha**: prima di introdurre nuovi indicatori, spremere
  quelli esistenti. Molte richieste di "nuovi KPI" nascono da indicatori mai letti bene.
- **Leggere i numeri**: distribuzioni prima delle medie, segmentazione prima
  dell'aggregato, attenzione ai confronti non normalizzati.
- **Il drill-down**: dall'aggregato al dettaglio, per capire dove si concentra il fenomeno.
- **I cinque perché e il diagramma causa-effetto**: strumenti per non fermarsi al sintomo.
- **Correlazione e causalità**: una correlazione apparente va smentita esplicitamente,
  altrimenti orienta le decisioni.
- **La checklist di fattibilità**: prima di promettere un'analisi, verificare che i dati
  necessari esistano, siano accessibili e abbiano storicità sufficiente.

## S4: Archivio strutturato e LLMwiki

**Domanda della sessione**: come si organizza la conoscenza documentale e quando conviene
metterci davanti un modello linguistico.

- **Cartelle e naming contro metadati**: la prima organizzazione è immediata e non richiede
  strumenti, ma regge una sola gerarchia; i metadati lasciano il file dov'è e permettono più
  chiavi di lettura. Le due logiche convivono.
- **La tassonomia**: il vocabolario condiviso con cui si descrivono i documenti. Va decisa
  con chi conosce il dominio, non dedotta a posteriori.
- **Lo schema di metadati**: la tassonomia applicata, cioè i campi che ogni documento deve
  avere compilati (tipologia, entità di riferimento, versione, riservatezza).
- **I livelli di riservatezza**: pubblico, interno, riservato, con l'avvertenza che nello
  stesso documento possono convivere livelli diversi.
- **La LLMwiki / RAG spiegata bene**: estrazione del testo, suddivisione in unità
  (chunking), indicizzazione vettoriale (embedding), recupero dei passaggi pertinenti
  (retrieval), generazione della risposta con citazione della fonte. Il punto critico non è
  il modello: è il filtro sui permessi applicato **prima** del recupero.
- **Deterministico contro generativo**: il deterministico è ripetibile, verificabile e
  spiegabile; il generativo è flessibile ma va vincolato e misurato. La scelta dipende da
  quanto costa un errore.
- **La checklist di fattibilità**: quasi tutte le voci riguardano l'organizzazione del
  materiale, non la tecnologia.

## S5: Il caso completo: Wikify

**Domanda della sessione**: come si comporta il metodo su un progetto vero, dall'idea alla
consegna.

Vedi `caso-wikify.md`. In sintesi: un archivio di schede progetto ingovernato, una richiesta
arrivata come soluzione ("serve un motore di ricerca"), un requisito di permessi per
informazione che ha reso la classificazione l'attività centrale, e una riflessione sulla
riservatezza che ha imposto di far precedere uno scanner deterministico a qualunque agente
AI. Esito: un archivio logico consegnabile, e la decisione motivata di **non** costruire
ancora il livello semantico.
