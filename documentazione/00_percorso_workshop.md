# Percorso del workshop

*Risponde alla domanda: come si presenta e si prova Wikify in due ore, senza slide,
scorrendo i documenti e l'applicazione.*

L'impostazione è deliberata: non si proietta una presentazione, si apre il progetto. La
cartella e i suoi documenti **sono** il materiale d'aula, perché il modo in cui un progetto
è organizzato è parte di ciò che si vuole insegnare. Un progetto che promette di fare ordine
in un archivio e si presenta disordinato smentisce se stesso.

**Preparazione**: applicazione avviata, archivio di prova già inventariato e con almeno una
scansione completata (richiede circa cinque minuti, non va fatta in diretta). Sullo schermo
condiviso devono essere visibili insieme la finestra del browser e quella del terminale:
parte della dimostrazione consiste nel vedere che l'elaborazione avviene in locale.

---

## Segmento 1: La cartella di progetto (~10')

**Cosa mostrare**: la radice del progetto e il [README](../README.md).

Si parte dall'organizzazione, non dal problema. Aprire la cartella, mostrare che ogni
elemento ha un ruolo dichiarato e che i documenti sono numerati secondo un ordine di
lettura. Far notare dove **non** stanno i dati: la cartella `Wikify_dati` è fuori dal
progetto, e questo consente di consegnare il codice senza trasferire un solo contenuto
dell'archivio analizzato.

> **Domanda all'aula**: aprendo la cartella di un progetto vostro, quanto tempo servirebbe a
> un collega per capire da dove iniziare?

## Segmento 2: Il problema e le domande (~15')

**Cosa mostrare**: documento [01: Contesto e problema](01_contesto_e_problema.md).

Il dominio, il collo di bottiglia fra ufficio tecnico e ufficio commerciale, e la richiesta
arrivata già formulata come soluzione. Il passaggio da valorizzare è la riformulazione:
dalla richiesta di uno strumento alle domande che l'archivio deve reggere, distinte in
esatte, esplorative e di confronto.

> **Micro-decisione**: di fronte a una richiesta già formulata come soluzione, da dove
> conviene partire: dalla tecnologia richiesta o dalle domande a cui si deve rispondere?
> Raccogliere due o tre posizioni prima di proseguire.

Chi sostiene che convenga assecondare la richiesta ha un argomento legittimo, da
valorizzare: la differenza non è fra accogliere e respingere, ma fra **accogliere** ed
**eseguire alla lettera**.

## Segmento 3: I requisiti e l'architettura (~20')

**Cosa mostrare**: documento [02: Requisiti e architettura](02_requisiti_e_architettura.md).

Le tre dimensioni da tenere separate, come il tipo di domanda cambia l'architettura, i
volumi e ciò che implicano. Il punto centrale è il requisito dei permessi **per
informazione e non per documento**: da lì discende che l'unità di gestione non è il file,
che il documento va scomposto e classificato, e che la classificazione non è un costo
accessorio ma il cuore del progetto.

Chiudere con lo schema dei livelli architetturali e con la tesi: incrementale, non
alternativo.

> **Micro-decisione**: sul vostro archivio, quale livello sarebbe già sufficiente a
> risolvere la maggior parte delle richieste che arrivano oggi? Far notare quanto spesso la
> risposta sia il primo livello, e quanto raramente venga proposto.

## Segmento 4: La decisione sulla riservatezza (~15')

**Cosa mostrare**: documento [03: Riservatezza: metodo A e metodo B](03_riservatezza_metodo_A_B.md).

È il segmento che gli allievi con responsabilità organizzative ricordano più a lungo, e
merita respiro anche a costo di comprimere il precedente. La domanda "possiamo esporre
questi documenti a un agente AI?" non era stata posta dal committente; la risposta ha
cambiato l'ordine delle fasi. Il non ancora qualificato si tratta come riservato; il metodo
deterministico bonifica il perimetro, l'agentico opera solo su ciò che è stato qualificato;
ciò che l'agente scopre torna nel dizionario dei pattern.

Il principio da estrarre, valido oltre questo progetto: **i vincoli si impongono, non si
raccomandano**. Nel connettore, il perimetro non è una regola scritta nelle istruzioni
dell'agente: è il server che rifiuta la lettura dei file fuori perimetro.

## Segmento 5: La progettazione e il codice (~15')

**Cosa mostrare**: documento [04: Progettazione dei moduli](04_progettazione_moduli.md) e la
cartella [app/](../app/).

Non si legge il codice: si mostra come è organizzato e perché. Il nucleo condiviso, un
modulo per fase con le proprie tabelle e le proprie pagine, le migrazioni additive che
consentono di far evolvere lo schema senza perdere i dati di chi già usa lo strumento.

Vale la pena raccontare l'errore iniziale: il primo scanner funzionava, ma richiedeva di
scrivere espressioni regolari. Chi conosce il dominio non conosce le espressioni regolari:
lo strumento era inutilizzabile proprio da chi avrebbe dovuto usarlo. Da qui la costruzione
guidata con prova live.

## Segmento 6: La dimostrazione (~30')

**Cosa mostrare**: l'applicazione in esecuzione sull'archivio di prova.

Percorso consigliato:

1. **Dashboard e inventario**: gli indicatori dell'archivio, i file da classificare.
2. **Una scansione già completata**: le segnalazioni raggruppate per file, con evidenza,
   posizione e contesto.
3. **Il triage**: qualificare due file, uno riservato e uno condivisibile, e mostrare come
   la coda si svuota.
4. **Il catalogo**: le entità generate dalle cartelle, l'arricchimento dal file tabellare,
   un progetto con più codici commerciali.
5. **Le regole di tipologia**: crearne una con la prova live sui nomi reali dei file.
6. **Il consolidamento**: eseguirlo e leggere il report, soffermandosi sulla copertura.
7. **L'export**: aprire il file JSON a schermo.

Se il tempo stringe, sacrificare la creazione delle regole e mostrarne di già pronte. I due
passaggi irrinunciabili sono il **consolidamento con il suo report** e l'**apertura
dell'export**: è lì che si vede la differenza fra una cartella di file e un archivio logico.

## Segmento 7: Dove siamo e cosa manca (~10')

**Cosa mostrare**: documento [05: Stato dell'arte](05_stato_dell_arte.md).

Che cosa esiste in numeri, e soprattutto le tre assenze deliberate: niente ricerca
semantica, niente knowledge graph, niente motore agentico integrato. Dichiarare le
motivazioni e le misure che decideranno il seguito.

> **Micro-decisione**: quando un archivio si può dire pronto per la ricerca semantica? Quale
> indicatore usereste, senza affidarvi a un'impressione? Guidare verso la copertura di
> classificazione e la completezza per entità.

## Segmento 8: Consegna e chiusura (~5')

**Cosa mostrare**: documenti [06](06_dataset_di_prova.md), [07](07_avvio_mac.md) e
[08](08_avvio_windows.md).

L'archivio di prova, la guida di avvio per il proprio sistema operativo e l'esercizio.

I tre passaggi da lasciare in aula:

1. il sintomo dichiarato dal committente non è il requisito: lo sono le domande;
2. prima di esporre un archivio a un'intelligenza artificiale bisogna sapere che cosa
   contiene;
3. un archivio non diventa consultabile perché ci si mette un modello davanti, ma perché
   prima lo si rende un archivio logico.

---

## Esercizio assegnato

**Principale.** Su Wikify installato sul proprio computer e sull'archivio di prova:
percorrere l'intera catena fino all'export. Consegna: il file JSON prodotto e due righe sul
dato che ha sorpreso di più fra gli indicatori di copertura. Il criterio di riuscita è
dichiarato in anticipo: non il numero di file trattati, ma la **percentuale di documenti
classificati e agganciati a un'entità**. È una misura, non un'impressione.

**Alternative**, per chi ha esigenze diverse:

- *Su un archivio proprio*: ripetere l'esercizio su una cartella reale del proprio ufficio,
  purché non riservata, e confrontare la copertura ottenuta con quella dell'archivio di
  prova. La differenza racconta la qualità dell'organizzazione esistente.
- *Orientata alla riservatezza*: costruire tre regole nel dizionario dei pattern per
  intercettare un tipo di informazione sensibile del proprio contesto, verificarle con la
  prova live e misurare quanti file vengono intercettati.
- *Senza installare nulla.* A partire dall'export fornito, redigere la scheda di due entità:
quali tipologie sono presenti, quali mancano, quali documenti risultano riservati e perché
  questo condiziona la fase successiva.
- *Di taglio progettuale*: redigere in una pagina la proposta di fase 2 per il proprio
  contesto: quale livello architetturale aggiungere per primo, con quale criterio di
  verifica e quale rischio principale.

## Da raccogliere durante la sessione

Quali domande arrivano più spesso agli uffici che custodiscono documentazione tecnica; se
esistono già convenzioni di nome o tassonomie informali su cui una classificazione
automatica potrebbe innestarsi; quali vincoli l'organizzazione pone all'uso di modelli
linguistici su documenti interni e chi ha titolo per deciderlo; con quale frequenza i
documenti cambiano, dato che incide sul costo di mantenimento più di qualunque scelta
tecnica.
