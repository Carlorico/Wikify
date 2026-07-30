# Il dataset di prova

*Risponde alla domanda: da dove viene l'archivio usato per collaudare Wikify, come è
costituito e con quale esito è stato messo alla prova.*

## La scelta della fonte

Per mettere alla prova Wikify serviva un archivio realistico ma non riservato: una struttura a cartelle progetto, documentazione tecnica eterogenea per formato, una relazione 1:N fra progetto e articoli commerciali, e un certo numero di contenuti simulabili come sensibili.

La fonte individuata è il portale **schede-tecniche.it**, un archivio amatoriale-professionale di documentazione tecnica per apparecchi domestici (caldaie, climatizzatori, scaldabagni e altro), costruito per finalità di certificazione energetica e utile, in questo contesto, come giacimento di documentazione tecnica pubblica organizzata in modo per molti versi analogo al dominio reale.

All'interno del portale è stata selezionata la sezione **caldaie Immergas**, con quattro serie di prodotto (ARES, EOLO, VICTRIX, ZEUS), per una motivazione precisa e verificata sul campo, non solo ipotizzata: è l'unica sezione su cui si è potuto accertare concretamente, tramite ispezione di documenti singoli, che i PDF sono nativi e il testo è pienamente estraibile: requisito imprescindibile, dato che lo scanner di Wikify non dispone di riconoscimento ottico dei caratteri.

La sezione presenta inoltre tre tipologie documentali chiaramente distinguibili (manuale d'uso multi-sezione, scheda tecnica parametrica a tabella, libretto istruzioni per l'installatore o il tecnico) utili a esercitare la classificazione documentale, e una relazione 1:N diretta e verificabile fra famiglia di prodotto e codici commerciali, assimilabile al rapporto progetto↔articolo del dominio reale. Con una differenza da tenere presente: qui la relazione va ricostruita dalla struttura delle pagine del sito, non ereditata da un file gestionale già esistente.

Un'alternativa, la sezione caldaie/bollitori/scaldabagni Baxi-Westen, è stata considerata e scartata in seconda battuta: il volume complessivo è maggiore ma meno controllato, e il naming dei file è meno uniforme, con il rischio di introdurre rumore non rappresentativo nella fase di classificazione automatica.

Sul piano dell'uso della fonte va segnalata un'area di attenzione che resta aperta: il sito dichiara esplicitamente che la documentazione tecnica è di proprietà dei singoli produttori e viene ripubblicata per finalità di consultazione, senza rivendicarne la titolarità né dichiarare una licenza d'uso per la redistribuzione.

Il prelievo di un campione limitato, per uso interno a un corso e non ridistribuito pubblicamente, non risulta vietato dal robots.txt del sito né dalle sue condizioni pubblicate, ma non è nemmeno esplicitamente autorizzato: si tratta di un rischio ragionevolmente contenuto per un prelievo mirato e non aggressivo, a fini didattici. La citazione della fonte nel materiale d'aula resta comunque una decisione da assumere consapevolmente, non un dettaglio da omettere.

## Che cosa contiene l'archivio

L'archivio costituito occupa **389 MB** per **95 file**, organizzati in **31 cartelle progetto** poste al primo livello sotto la radice: coerentemente con il modello dati di Wikify, che riconosce come cartella progetto proprio il primo livello. La composizione per formato è la seguente:

| Formato | File | Contenuto |
|---|---|---|
| PDF | 76 | documentazione tecnica Immergas (manuali d'uso, schede tecniche, libretti installatore), tutti con testo nativamente estraibile |
| XLSX | 7 | 1 file di relazione progetto↔articolo (`progetti_articoli.xlsx`) + 6 file simulati di parametri di configurazione |
| DOCX | 6 | 6 verbali di collaudo simulati |
| TXT | 6 | 6 note tecniche brevi, per varietà di formato |

Ogni cartella progetto contiene da 1 a 4 documenti (manuale d'uso, scheda tecnica, eventuale libretto installatore), riproducendo l'eterogeneità documentale attesa in una cartella progetto reale.

Le quattro serie di prodotto restano ricavabili dal prefisso del nome cartella e, in modo esplicito, dalla colonna `serie` del file tabellare: non sono più un livello di cartella a sé stante, per non generare quattro entità al posto di trentuno. La struttura, in sintesi, è la seguente:

```
archivio_prova/
├── progetti_articoli.xlsx
├── ARES_18-25/
├── ARES_18-25_CS/            (verbale di collaudo + parametri simulati)
├── ARES_PRO/                 (verbale di collaudo simulato)
├── EOLO_ECO/                 (verbale di collaudo + parametri simulati)
├── VICTRIX_OMNIA/             (verbale di collaudo + parametri simulati)
├── ZEUS_SUPERIOR/             (verbale di collaudo + parametri simulati)
└── ... fino a 31 cartelle progetto, una per variante di serie
```

## Il file tabellare e la relazione 1:N

`progetti_articoli.xlsx` lega ogni cartella progetto ai propri codici commerciali con colonne `id_progetto`, `serie`, `codice_commerciale`, `tipo_prodotto`, `anno_documento`, `note`. Conta 55 righe per 31 progetti distinti, con 54 codici commerciali tutti diversi fra loro.

In 19 progetti su 31 (61%) sono presenti più codici commerciali per lo stesso progetto: è la relazione 1:N che il file deve dimostrare, con esempi come `ARES_18-25`, a cui corrispondono i codici ARES-18 e ARES-25, o `VICTRIX_MAIOR`, a cui ne corrispondono due varianti.

La colonna `anno_documento` è stata lasciata sistematicamente vuota, perché nessuno dei documenti riportava un anno affidabile in etichetta o nel nome file: si è preferito lasciare il vuoto piuttosto che stimarlo. Il file, va ricordato, non discende da un export gestionale ma da una lettura diretta delle pagine del sito di origine: resta quindi un margine di soggettività nella scelta di quali varianti considerare codici commerciali distinti rispetto a semplici rinominazioni dello stesso prodotto.

## I documenti sensibili simulati

Poiché i documenti originali sono manuali pubblici privi di contenuti riservati, in 8 delle 31 cartelle progetto sono stati inseriti file aggiuntivi fittizi: un verbale di collaudo (`verbale_collaudo_simulato.docx`) e un file di parametri di configurazione cliente (`parametri_configurazione_cliente.xlsx`), distribuiti sulle quattro serie con una combinazione bilanciata fra cartelle con entrambi i file e cartelle con un solo file.

Ogni documento riporta in apertura una dicitura che ne dichiara la natura sintetica e la non veridicità dei dati, e non contiene nominativi o ragioni sociali realmente esistenti: i verbali includono matricole fittizie e un cliente di fantasia, i file di parametri includono indirizzi IP di esempio, credenziali fittizie e un indirizzo email su dominio convenzionale (`example.com`). In totale sono 12 i documenti pensati per essere intercettati dallo scanner di riservatezza.

## L'esito del collaudo

L'archivio è stato percorso per intero da Wikify, con esito di **20 verifiche superate su 22**: le due non superate, come si chiarisce più sotto, non sono difetti ma soglie di controllo volutamente rigide.

| Fase | Esito |
|---|---|
| Inventario | 95 file mappati, 31 cartelle progetto riconosciute, esecuzione istantanea |
| Scansione | 95 file analizzati, nessun file non analizzabile, circa 5 minuti |
| Segnalazioni di riservatezza | 1.339 su 67 file, ripartite fra configurazione, cliente, credenziali, interconnessione, marcature esplicite e sperimentazione |
| Documenti simulati | tutti e 12 intercettati dallo scanner |
| Entità di catalogo | 31, generate dalle cartelle progetto |
| Arricchimento dati | 117 valori agganciati; 19 progetti con più codici commerciali, relazione 1:N confermata |
| Consolidamento archivio logico | 95 documenti, 89 classificati (94%), 94 agganciati a un'entità, 12 riservati |
| Export | JSON con 31 entità e 94 documenti (45 KB); XLSX di consultazione (11 KB) |

## I due indicatori non pieni, e perché sono utili in aula

**Copertura di classificazione al 94%.** Sei documenti su 95 non vengono intercettati dalle regole di dimostrazione: cinque sono PDF con una variante di nomenclatura non prevista dal seme di regole (ad esempio `manuale_tecnico_*` o un catalogo tecnico di gamma), il sesto è lo stesso `progetti_articoli.xlsx`, che risiede alla radice dell'archivio e non appartiene a nessuna cartella progetto.

È esattamente la funzione per cui l'indicatore esiste: rendere visibile una lacuna reale e invitare ad aggiungere una regola, non nasconderla dietro una copertura apparentemente perfetta. In aula è materiale prezioso proprio così com'è, e conviene mostrarlo prima di correggerlo, cioè prima di affinare il dizionario delle regole con gli studenti.

**Aggancio alle entità: 94 su 95.** L'unico documento non agganciato è di nuovo `progetti_articoli.xlsx`: un comportamento corretto, non un difetto, perché nel dominio reale il file di relazione progetto↔articolo vive anch'esso fuori dalle cartelle progetto, non al loro interno.

Va segnalata anche un'osservazione collaterale sull'import del file tabellare, utile a scopo didattico: l'import registra 47 anomalie, tutte di tipo duplicato esatto, corrispondenti ai valori di `serie` e `tipo_prodotto` che si ripetono sulle righe di uno stesso progetto mentre solo il codice commerciale varia. Non è un difetto del file, è la deduplicazione che distingue correttamente l'attributo realmente 1:N da quelli costanti: una segnalazione che a prima vista può allarmare e che invece va letta come segno di corretto funzionamento.

## Tempi da prevedere in aula

La scansione dei 95 file per 389 MB ha richiesto circa cinque minuti su un portatile recente: un tempo da mettere in conto nella pianificazione dell'esercitazione, o da ridurre facendo eseguire agli studenti la scansione su un sottoinsieme delle cartelle anziché sull'archivio intero.

## Aree di attenzione residue

Alcuni aspetti del dataset restano da tenere presenti nella conduzione del corso.

Il naming dei file non è sempre univoco fra le due pagine di origine del sito: per alcune cartelle il libretto istruzioni o la scheda tecnica reperibile in una pagina usa una dicitura leggermente diversa da quella usata nell'altra, pur riferendosi alla stessa linea commerciale; l'abbinamento in questi casi è stato fatto per prossimità di modello, non per identità letterale di codice.

I contenuti sensibili, essendo interamente simulati, presentano un linguaggio e una distribuzione più regolari di quanto ci si aspetterebbe in un caso reale: un margine di artificiosità di cui tenere conto nel presentare l'esercizio sullo scanner di riservatezza come dimostrativo, e non come prova esaustiva della sua efficacia su un caso reale.

Resta infine aperta, come già anticipato, la questione della citazione della fonte nel materiale d'aula, dato che il sito ripubblica documentazione di proprietà dei produttori senza una licenza dichiarata: una decisione da assumere in modo esplicito prima della diffusione del materiale, non da rimandare implicitamente.
