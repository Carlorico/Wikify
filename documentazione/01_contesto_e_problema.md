# Contesto e problema

*Risponde alla domanda: da cosa nasce il progetto Wikify e quale problema organizzativo è
chiamato ad affrontare.*

## Il dominio

Wikify nasce a partire da un archivio storico digitale di schede progetto relative a tre famiglie di prodotto: sonde, controller e porta sonda.

Ogni cartella progetto raccoglie materiale eterogeneo maturato nel tempo:

- dati di sperimentazione;
- specifiche tecniche;
- manuali di installazione e di manutenzione;
- parametri di interconnessione;
- altra documentazione di corredo, non sempre riconducibile a una tipologia fissa.

I formati sono anch'essi eterogenei — Word, Excel, PDF, file di testo e altri ancora — riflesso di anni di prassi diverse e di strumenti diversi, senza un impianto unico di archiviazione imposto fin dall'origine.

Un progetto costituisce la base di uno o più articoli commerciali: la relazione tra progetto e articolo è oggi mantenuta in un file Excel, che rappresenta di fatto l'unico punto strutturato dell'intero archivio.

## Il problema organizzativo

L'archivio è di competenza dell'ufficio tecnico, che lo ha costruito nel tempo e lo conosce dall'interno. L'ufficio commerciale, tuttavia, necessita con frequenza di informazioni sui prodotti — specifiche, compatibilità, parametri — ma non ha competenza diretta sull'archivio: per ogni esigenza deve rivolgersi ai referenti tecnici.

Ne deriva un collo di bottiglia strutturale, con effetti su entrambe le parti coinvolte:

- un onere ricorrente per l'ufficio tecnico, distolto da attività di propria competenza per rispondere a richieste altrui;
- tempi di attesa per il commerciale, che dipende da una disponibilità che non è sua.

A questo si aggiunge un secondo tema, trasversale al primo: non tutte le informazioni dell'archivio hanno lo stesso grado di riservatezza. I documenti generici, come i manuali, sono in linea di principio fruibili da chiunque; i dati di configurazione e i parametri di interconnessione sono invece riservati al personale tecnico e, in alcuni casi, a clienti specifici.

Qualunque soluzione al collo di bottiglia deve convivere con questo requisito di profilazione degli accessi, non aggirarlo: un archivio più facile da consultare ma privo di controllo sugli accessi sposterebbe il problema, non lo risolverebbe. Vale la pena osservarlo fin da questo primo documento perché condizionerà, più avanti, il tipo di architettura sostenibile: non basta indicizzare, occorre anche sapere chi può vedere che cosa.

## La richiesta e la distinzione fra sintomo e causa

La richiesta è arrivata già formulata come soluzione: realizzare un "archivio smart" basato su tecniche moderne di indicizzazione delle informazioni e su un'interfaccia guidata di consultazione, con alcune tecnologie candidate indicate a priori — database relazionale, database documentale, retrieval augmented generation (RAG), un approccio a knowledge graph di tipo LLM-Wiki. È una richiesta legittima e concreta, ma vale la pena tenere distinti due piani: il sintomo che l'ha generata e la causa che lo produce.

Il sintomo è visibile e misurabile: il tempo di attesa del commerciale e l'onere ricorrente del tecnico. La causa, con ogni probabilità, sta un livello più a monte: l'archivio non ha oggi una classificazione esplicita delle informazioni che contiene. Ciò che permette al tecnico di rispondere rapidamente è in buona parte conoscenza tacita — sa dove guardare, sa cosa cercare — non una struttura che chiunque altro potrebbe consultare autonomamente.

Scegliere una tecnologia prima di aver compreso questa causa espone a un rischio preciso: automatizzare il sintomo, ottenendo una ricerca più veloce su un archivio ancora privo di struttura, senza risolvere la causa, cioè l'assenza di una classificazione delle informazioni. Per questo motivo il percorso non parte dalla scelta della tecnologia, ma dalla definizione dei criteri con cui quella scelta andrà fatta, lasciando aperta anche la possibilità di una combinazione fra più approcci.

## L'obiettivo dichiarato

Il progetto è impostato come percorso tutorial in due tempi: prima una fase propriamente progettuale, poi un proof of concept (PoC) costruito sulle scelte maturate in quella fase.

L'obiettivo della fase progettuale non è indicare una tecnologia, ma definire i criteri di scelta e le possibili combinazioni fra gli approcci candidati, in modo che la decisione tecnologica risulti conseguenza dell'analisi e non un punto di partenza assunto per convenzione.

Un obiettivo dichiarato in questi termini comporta una conseguenza pratica per tutto il percorso successivo: prima di progettare qualunque componente occorre raccogliere alcune informazioni di base sull'archivio reale — la tipologia prevalente delle domande a cui deve rispondere, i volumi effettivi, il grado di dettaglio richiesto dai permessi, la qualità e l'uniformità dei dati esistenti. Sono le stesse informazioni raccolte in questo documento e nel successivo, ed è per questo che precedono, e non seguono, la scelta architetturale.

## Le domande che l'archivio deve reggere

Una prima ricognizione presso l'ufficio commerciale indica che le richieste si distribuiscono su tre famiglie, con un peso molto diverso fra loro:

- **domande esatte** — la famiglia prevalente: "specifiche di configurazione dell'articolo X", "manuale di installazione dell'articolo Y", "compatibilità tra l'articolo A e l'articolo B". Sono domande a cui corrisponde un'unica risposta corretta, reperibile se l'archivio è ben organizzato;
- **domande esplorative** — meno frequenti ma da presidiare, del tipo "quale sonda regge una determinata condizione operativa": la risposta non è in un metadato, ma dentro i contenuti dei documenti;
- **domande di confronto e sintesi** — richiedono di mettere a fattor comune informazioni provenienti da più documenti o più progetti, ad esempio per costruire una tabella comparativa fra controller.

Questa distribuzione è il primo criterio con cui va letta ogni scelta architetturale successiva: un'architettura pensata solo per le domande esatte rischia di lasciare scoperte le altre due famiglie. Per questo è stata posta esplicitamente la richiesta di analizzare come l'architettura debba cambiare al variare del tipo di domanda — un'analisi che il documento successivo sviluppa nel dettaglio.

## I volumi in gioco

La scala di riferimento indicata è di qualche migliaio di cartelle progetto. Ipotizzando una media di 10-50 file per cartella, la stima realistica si colloca fra 10.000 e oltre 100.000 documenti complessivi.

Si tratta di un volume medio-grande per un contesto aziendale: sufficiente a escludere in partenza qualunque approccio artigianale basato sull'indicizzazione manuale integrale, e a richiedere fin dall'inizio una pipeline automatizzata di ingestione e classificazione.

A questa scala il costo del progetto non è, in prima battuta, un costo tecnologico: le tecnologie in grado di gestire decine o centinaia di migliaia di documenti sono mature e ampiamente disponibili. Il costo reale sta nella qualità e nell'uniformità dei dati di partenza — quanto l'archivio esistente, con la sua storia di prassi non uniformi, si presta a una classificazione automatica prima ancora che a una ricerca intelligente. È un punto che va verificato sul campo, non assunto per ipotesi, ed è l'oggetto del documento che segue.
