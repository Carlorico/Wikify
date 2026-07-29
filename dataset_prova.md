# Dataset di prova per Wikify — analisi di schede-tecniche.it

## Sintesi della raccomandazione

Si raccomanda di costituire il campione a partire dalla sezione **caldaie Immergas** del sito schede-tecniche.it (pagine "manuali uso caldaie Immergas" e "schede tecniche caldaie Immergas"), selezionando 3-4 serie di prodotto (es. ARES, EOLO, VICTRIX, ZEUS). La sezione presenta PDF nativi con testo estraibile, una struttura ricorrente serie→codice commerciale assimilabile al rapporto progetto↔articolo, e almeno tre tipologie documentali distinte (manuale d'uso, scheda tecnica parametrica, libretto istruzioni installatore/tecnico). Come alternativa, in posizione di secondo piano, si propone la sezione **caldaie/bollitori/scaldabagni Baxi–Westen**, più ampia ma meno verificata nel dettaglio.

## Struttura del sito rilevata

schede-tecniche.it si presenta come un portale amatoriale-professionale curato dall'Ing. Stefano Basso (certificatore energetico CENED, Lombardia), nato per raccogliere documentazione tecnica di caldaie, climatizzatori, scaldabagni e altri apparecchi, utile alla compilazione di Attestati di Prestazione Energetica (APE) e relazioni ex Legge 10, specialmente per apparecchi datati o di aziende non più operative. Il sito dichiara oltre 14.000 documenti complessivi.

L'architettura è organizzata su tre livelli:

1. **Macro-categoria di prodotto** (caldaie, condizionatori/climatizzatori, scaldabagni, stampanti, smartphone, elettrodomestici, TV, fotocamere, monitor PC — oltre 50 categorie in totale).
2. **Pagina per produttore**, con due varianti tipiche per macro-categoria:
   - `manuali-uso-<categoria>-<produttore>.html/.php` — elenco dei manuali d'uso/istruzioni per modello;
   - `schede-tecniche-<categoria>-<produttore>.html/.php` — elenco delle schede tecniche parametriche e/o pagine di famiglia prodotto.
3. **Pagina di famiglia/serie** (es. `caldaie-immergas-ares.html`), che raggruppa le varianti di una stessa serie e collega, per ciascuna, uno o più PDF (manuale, scheda tecnica, libretto istruzioni), oppure link diretto al PDF quando la serie ha un'unica variante.

Esempi verificati:
- **Immergas** — pagina manuali uso: 38 modelli, tutti PDF nativi (naming `Manuale-uso-caldaia-Immergas-<MODELLO>.pdf`); pagina schede tecniche: stima 200-250 elementi, comprensiva di manuali tecnici, schede tecniche vere e proprie e libretti istruzioni, con naming eterogeneo (`IMMERGAS-scheda-tecnica-...`, `IMMERGAS-manuale-tecnico-...`, `IMMERGAS-libretto-istruzioni-...`).
- **Baxi** — pagina manuali uso: 79 modelli, PDF nativi, naming con varianti (`Manuale-uso-caldaia-Baxi-...`, `Libretto-caldaia-Baxi-...`, `Manuale-utente-caldaia-Baxi-...`); esiste anche una pagina schede tecniche Baxi, più le sezioni collegate bollitori Baxi e scaldabagni Baxi (gruppo Baxi include il marchio Westen).
- **Daikin (condizionatori)** — pagina manuali uso: 25 gruppi di modelli, ma **solo manuali d'uso**, nessuna scheda tecnica collegata: minore eterogeneità documentale rispetto a caldaie.

Formato: dai campioni scaricati e ispezionati (un manuale Immergas EOLO Eco di 26 pagine e una scheda tecnica Immergas ARES di 1 pagina) risulta **testo pienamente estraibile** — sono PDF nativi generati da sorgente digitale, non scansioni immagine. Le schede tecniche contengono tabelle di parametri (portate gas, potenze termiche, temperature fumi); i manuali contengono sezioni distinte per "Installatore / Utente / Tecnico" con dimensioni, attacchi idraulici, allacciamento elettrico e gas — un contenuto molto vicino, concettualmente, ai "parametri di interconnessione" del dominio reale.

## Aspetti legali

- **robots.txt** (verificato su `https://schede-tecniche.it/robots.txt`): applica `User-agent: *` con `Disallow` limitato a poche directory tecniche e ad alcune sezioni interne (`/detroitchicago/`, `/porpoiseant/`, `/beardeddragon/`, `/tardisrocinant/`, `/ezoimgfmt/`, `/js/`, `/css/`, `/font-awesome/`, `/no-collapse/`, `/choice/`). **Non è indicata alcuna sitemap.** Le cartelle dei PDF (`manuali-uso-caldaie/`, `schede-tecniche-caldaie/`, ecc.) **non risultano bloccate**: la scansione di quelle pagine è quindi tecnicamente ammessa lato robots.txt.
- **Informativa privacy/cookie**: pagina dedicata ("Informativa estesa cookie"), conforme GDPR ma **non contiene alcuna clausola su copyright, condizioni d'uso dei contenuti scaricabili, redistribuzione o uso didattico/commerciale dei PDF**.
- **Nessuna pagina "Termini e condizioni" o "Note legali" distinta** è stata individuata: il footer riporta solo "Copyright © 2015-2024 | Powered by Stefano Basso".
- **Dichiarazione del gestore** (rilevata tramite le pagine di categoria, es. sezione condizionatori Daikin): il sito afferma esplicitamente che *"tutta la documentazione tecnica è di esclusiva proprietà dei singoli produttori ed è condivisa per consentirne la consultazione quando non più reperibile altrove"*. Questo è il punto legale più rilevante: **il sito stesso non rivendica la titolarità dei documenti**, ma li ripubblica come archivio di consultazione per finalità di certificazione energetica.

**Conclusione legale**: il download di un **campione limitato** (poche decine/centinaia di PDF, non l'intera sezione) a fini didattici, per un esercizio d'aula non pubblicato né ridistribuito a terzi, non risulta esplicitamente vietato — né dal robots.txt, né dalle condizioni pubblicate — ma nemmeno esplicitamente autorizzato: il tema non è chiarito. Si tratta di documentazione di terzi (i produttori) ripubblicata dal sito stesso senza una licenza dichiarata. Si ipotizza che un prelievo contenuto, effettuato con richieste sequenziali non aggressive, per uso interno al corso e non ridistribuito pubblicamente, rientri in una prassi comune e a basso rischio; resta tuttavia un'area che richiede una decisione di Carlo, eventualmente accompagnata da un breve richiamo alla fonte nel materiale d'aula.

## Valutazione delle candidate

| Criterio | Caldaie Immergas | Caldaie/bollitori/scaldabagni Baxi–Westen | Condizionatori Daikin |
|---|---|---|---|
| Somiglianza al dominio (componentistica con schede/manuali/parametri) | Alta — manuali con sezioni installatore/utente/tecnico, schede con parametri tecnici tabellari | Alta — stessa impostazione, estesa a più famiglie di prodotto correlate (caldaie, bollitori, scaldabagni) | Media — solo manuali d'uso, meno orientati al dato tecnico-parametrico |
| Volume (indicativo 50-500 doc.) | Adeguato — 38 manuali uso + un sottoinsieme selezionabile dalle ~200-250 schede tecniche/serie | Elevato — 79 manuali uso più le sezioni collegate; il totale complessivo rischia di eccedere il range gestibile se preso per intero | Adeguato — 25 gruppi modello, ma tipologia documentale povera |
| Eterogeneità formati / PDF nativi vs scansioni | PDF nativi confermati su campione, testo pienamente estraibile | Presumibilmente PDF nativi (stessa piattaforma), non verificato su campione diretto | Presumibilmente PDF nativi, non verificato su campione diretto |
| Struttura ricorrente "cartella progetto" (per serie/famiglia) | Sì — pagine di serie (es. ARES) con più varianti e più documenti per variante | Sì, e più articolata — gruppo Baxi/Westen con più famiglie di prodotto oltre alle caldaie | Debole — raggruppamento più per "gruppo di modelli simili" che per famiglia strutturata |
| Più tipologie documentali distinguibili | Sì — manuale d'uso, scheda tecnica, libretto istruzioni installatore/tecnico | Sì, con naming meno uniforme (manuale-uso, libretto, manuale-utente) | No — solo manuale d'uso |
| Relazione 1:N serie→codice commerciale | Confermata concretamente (es. serie ARES → 18-25, 18-25 CS, 36-43-52-58, 150-350 Tec, ecc.) | Presumibile analoga (serie LUNA, NUVOLA, POWER con più varianti), non ricostruita in dettaglio | Debole — varianti spesso raggruppate in un unico manuale multi-modello |
| Presenza di contenuti "sensibili" plausibili | Assente nei documenti originali (sono manuali pubblici); parametri di configurazione tecnica presenti, simulabili come "sensibili" | Idem | Idem |

## Categoria raccomandata e motivazione estesa

**Raccomandazione: caldaie Immergas**, con selezione di 3-4 serie rappresentative (ad esempio ARES, EOLO, VICTRIX, ZEUS), attingendo sia alla pagina "manuali uso caldaie Immergas" sia alla pagina "schede tecniche caldaie Immergas".

Motivazioni:
- È l'unica candidata su cui si è potuto **verificare concretamente**, tramite ispezione di documenti singoli, che i PDF sono nativi e il testo è pienamente estraibile — requisito imprescindibile per lo scanner Wikify, che non dispone di OCR.
- Mostra **tre tipologie documentali chiaramente distinguibili** (manuale d'uso multi-sezione, scheda tecnica parametrica a tabella, libretto istruzioni tecnico/installatore), utile a esercitare la classificazione documentale.
- La pagina di serie (es. ARES) dimostra in modo diretto e verificato una **relazione 1:N tra famiglia di prodotto e codici commerciali**, assimilabile al rapporto progetto↔articolo del dominio reale — con la differenza che qui la relazione andrebbe ricostruita a partire dalla struttura delle pagine, non da un file XLS esterno (aspetto da simulare, v. piano campione).
- Il volume è governabile: 38 manuali d'uso più un sottoinsieme mirato di schede tecniche consentono di restare comodamente nel range 50-500 documenti senza dover scansionare l'intera sezione Immergas (che nel complesso supererebbe le poche centinaia di unità).

## Alternativa: Baxi–Westen (caldaie, bollitori, scaldabagni)

Seconda scelta per **volume potenzialmente maggiore e catalogo più articolato** (più famiglie di prodotto correlate sotto uno stesso gruppo industriale, con il marchio Westen come sotto-brand — utile a simulare relazioni gruppo→marchio→serie→codice). È stata collocata in seconda posizione perché:
- il volume complessivo della sezione Baxi è più ampio e richiederebbe una selezione più attenta per non eccedere il range di gestibilità in aula;
- la coerenza del naming dei file è meno uniforme (manuale-uso, libretto, manuale-utente usati in modo non sempre coerente per lo stesso tipo di documento), il che potrebbe complicare la fase di classificazione automatica se non filtrata a monte;
- non si è effettuata, per questa candidata, la stessa verifica diretta di estraibilità testuale svolta su Immergas (ragionevole per analogia di piattaforma, ma non confermata su campione).

Resta una alternativa solida se in corso d'opera emergesse la necessità di un campione più ampio o di un secondo caso di studio con struttura di gruppo (holding con più marchi).

## Piano di costituzione del campione

**Perimetro suggerito**: 4 serie Immergas (ARES, EOLO, VICTRIX, ZEUS) × documenti collegati (manuale d'uso + scheda tecnica + eventuale libretto installatore), per un totale stimato di 80-150 documenti — nel range richiesto, con margine di regolazione aggiungendo o togliendo una serie.

**Organizzazione su filesystem** (per assomigliare all'archivio progetti del cliente):

```
archivio_prova/
├── Immergas_ARES/
│   ├── ARES_18-25/
│   │   ├── manuale_uso_ARES_18-25.pdf
│   │   ├── scheda_tecnica_ARES_18-25.pdf
│   ├── ARES_36-43-52-58/
│   │   ├── manuale_uso_ARES_36-43-52-58.pdf
│   │   ├── scheda_tecnica_ARES_36-43-52-58.pdf
│   ├── ARES_150-350_Tec/
│   │   └── ...
├── Immergas_EOLO/
│   ├── EOLO_Eco/
│   ├── EOLO_Star/
│   └── ...
├── Immergas_VICTRIX/
│   └── ...
├── Immergas_ZEUS/
│   └── ...
```

Ogni sotto-cartella di serie (es. `ARES_18-25`) rappresenta la "cartella progetto" del dominio reale; i documenti al suo interno (manuale, scheda tecnica, eventuale libretto) simulano l'eterogeneità documentale di una cartella progetto reale (specifiche, manuale installazione/manutenzione, dati tecnici).

**File tabellare progetto↔articolo**: costruire un CSV/XLS `progetti_articoli.xlsx` con colonne indicative:

| id_progetto (cartella) | serie | codice_commerciale (articolo) | tipo_prodotto | data_documento | note |
|---|---|---|---|---|---|
| Immergas_ARES/ARES_18-25 | ARES | ARES-18 | Caldaia murale | 2001 | — |
| Immergas_ARES/ARES_18-25 | ARES | ARES-25 | Caldaia murale | 2001 | — |
| Immergas_ARES/ARES_18-25-CS | ARES | ARES-18-CS | Caldaia murale | 1999 | — |
| ... | ... | ... | ... | ... | ... |

Questo file va costruito manualmente (o con estrazione assistita dai nomi dei modelli), popolando la relazione 1:N cartella-progetto → più codici commerciali, esattamente come il file XLS esterno del cliente lega progetto e articoli.

**Iniezione di contenuti sensibili simulati**: poiché i documenti originali sono manuali pubblici e non contengono dati riservati, si propone di:
- aggiungere a un sottoinsieme di cartelle un **documento aggiuntivo fittizio** (es. `verbale_collaudo_simulato.docx` o `parametri_configurazione_cliente.xlsx`), con dati di collaudo e riferimenti a "clienti" plausibili ma inventati (nomi di fantasia, non riconducibili a soggetti reali);
- inserire in questi file simulati elementi tipici da far intercettare dallo scanner di riservatezza: nominativi, indirizzi email fittizi, numeri di matricola/collaudo, note interne "riservato" — chiaramente etichettati come dati sintetici a scopo didattico.

## Aree di attenzione

- **Incertezza sul piano legale**: come indicato, l'uso didattico di un campione limitato non risulta vietato, ma nemmeno esplicitamente autorizzato dal sito, che a sua volta ripubblica materiale di proprietà dei produttori senza licenza dichiarata. Si ipotizza un rischio contenuto per un prelievo mirato e non ridistribuito, ma la decisione finale sull'opportunità di procedere, e su come citare la fonte in aula, resta di competenza di Carlo.
- **Assenza nativa di contenuti sensibili**: il dataset reale del cliente include verosimilmente dati di collaudo e riferimenti a clienti; qui questi elementi andranno interamente simulati e potrebbero risultare meno "naturali" nella distribuzione e nel linguaggio rispetto a un caso reale, con il rischio che l'esercizio sullo scanner di riservatezza risulti più artefatto che nel caso d'uso originario.
- **Relazione progetto↔articolo ricostruita, non nativa**: nel dominio reale la relazione è mantenuta in un file XLS del cliente già esistente; qui va costruita ex novo a partire dai nomi dei modelli nelle pagine di serie, con un margine di lavoro manuale non trascurabile e una minore "autenticità" del file tabellare rispetto a un vero export gestionale.
- **Eterogeneità di formato solo parziale**: il campione, per come verificato, è quasi interamente PDF; il dominio reale include anche Word, Excel e TXT. Si suggerisce di integrare artificialmente 2-3 file Excel/Word per cartella (es. una tabella parametri ricopiata a mano, un file di note) per riprodurre la varietà di formato del caso reale, non altrimenti presente nella fonte pubblica.
- **Naming dei file non sempre uniforme** (soprattutto nella sezione Baxi, in misura minore in Immergas): può richiedere una fase di normalizzazione preliminare prima dell'esercizio di scansione, per non introdurre rumore non rappresentativo del caso reale.
- **Verifica solo campionaria**: la valutazione di estraibilità testuale è stata condotta su due soli documenti Immergas (un manuale e una scheda tecnica); non è stato verificato l'intero perimetro proposto (80-150 documenti). Si raccomanda, in fase di costituzione effettiva del campione, un controllo automatico di estraibilità testuale (es. con `pdftotext` o libreria equivalente) su tutti i file scaricati, per scartare eventuali eccezioni (scansioni isolate) prima dell'uso in aula.
