# Requisiti e architettura

*Risponde alla domanda: che cosa serve davvero all'archivio e quale architettura ne
consegue.*

## Le tre dimensioni del problema

Il problema, per quanto si presenti come un'unica richiesta, contiene in realtà tre dimensioni distinte, che conviene tenere separate in fase di analisi perché ammettono soluzioni tecnologiche diverse e, soprattutto, tempi di realizzazione diversi:

- **dimensione strutturata**: la relazione fra progetto e articolo commerciale, gli attributi anagrafici come famiglia di prodotto, codici, date, stati. È informazione tabellare, interrogabile con criteri esatti;
- **dimensione documentale**, il contenuto dei file: manuali, specifiche, relazioni di sperimentazione. È informazione non strutturata, interrogabile solo per ricerca testuale o semantica;
- **dimensione di governance**: chi può vedere cosa. È trasversale alle prime due dimensioni e, come si vedrà, è potenzialmente il vincolo più stringente sull'intera scelta architetturale, più della quantità di documenti o della loro varietà di formato.

## Come cambia l'architettura al variare del tipo di domanda

Le tre famiglie di domande individuate (esatte, esplorative, di confronto) non sollecitano la stessa componente architetturale: conviene ragionare per livelli, dove ogni livello abilita la famiglia successiva senza sostituire il precedente.

**Ricerche esatte.** Una domanda come "specifiche di configurazione dell'articolo X" non è, in senso proprio, una domanda semantica: è una navigazione strutturata.

Risponde bene a questa esigenza un catalogo che leghi articolo, progetto e documenti classificati per tipologia, con metadati affidabili su ciascun documento: tipologia, riferimento di progetto o articolo, livello di riservatezza. Una domanda come "compatibilità fra l'articolo A e l'articolo B" richiede in più che le relazioni fra le entità del dominio (sonda, controller, porta sonda, articolo) siano modellate esplicitamente.

L'architettura minima sufficiente per questa famiglia è un database relazionale (o documentale) accoppiato a un'interfaccia di navigazione guidata: non è necessario alcun componente basato su intelligenza artificiale, serve un buon modello dati. Il file Excel progetti↔articoli, per quanto oggi grezzo, è già l'embrione di questo catalogo.

**Domande esplorative.** Una domanda come "quale sonda regge una determinata condizione operativa" ha la risposta dentro i contenuti, non nei metadati.

Richiede in aggiunta un'indicizzazione dei contenuti (testo integrale come base, indice vettoriale per la ricerca semantica) una pipeline di estrazione del testo dai formati eterogenei, e, opzionalmente, un livello di generazione della risposta in linguaggio naturale con citazione delle fonti secondo l'approccio RAG.

Questo livello si somma al precedente, non lo sostituisce: il retrieval semantico va comunque filtrato dai metadati del catalogo (per articolo, per tipologia, per permesso) prima della ricerca nel contenuto, altrimenti la precisione dei risultati e la governance degli accessi degradano insieme.

**Confronti e sintesi.** Costruire una tabella comparativa fra controller richiede aggregare informazioni da più documenti. Due strade sono possibili, e sono complementari più che alternative.

La prima: estrarre a monte, una volta per tutte, le caratteristiche tecniche rilevanti (intervalli di temperatura, protocolli, tensioni) e salvarle come dati tabellari, così che i confronti diventino interrogazioni esatte, affidabili e ripetibili. La seconda: produrre a valle una sintesi generata da un modello linguistico su più documenti recuperati, più flessibile ma con un esito meno controllabile.

Un knowledge graph (entità, attributi, relazioni) è la formalizzazione della prima strada, ed è un approccio particolarmente adatto a un dominio con entità ben definite come questo, dove sonda, controller, porta sonda e articolo sono concetti stabili e ricorrenti.

**La conclusione che ne deriva** è che l'architettura è incrementale, non alternativa. Il catalogo strutturato serve comunque, a prescindere dal livello di ambizione del progetto; il retrieval semantico si aggiunge per l'esplorativo; l'estrazione strutturata e l'eventuale grafo si aggiungono per confronti affidabili. La domanda progettuale corretta non è "quale tecnologia scegliere", ma "fino a quale livello spingersi, e in che ordine costruirlo".

## Volumi e loro implicazione

La scala di riferimento è nell'ordine delle centinaia di cartelle progetto, con 5-10 file per cartella: alcune migliaia di documenti complessivi. È un volume contenuto, che non pone alcun vincolo tecnologico: database relazionali, motori vettoriali e motori di ricerca full-text lo gestiscono senza tensione, e lo stesso vale per soluzioni ordinarie e poco impegnative come un database incorporato.

Questa scala non allarga le opzioni architetturali, le **restringe in senso utile**: rende sconsigliabile qualunque sovradimensionamento. Costruire un'infrastruttura pensata per centinaia di migliaia di documenti, su un archivio che ne conta alcune migliaia, aggiungerebbe complessità di esercizio senza alcun beneficio misurabile, e sposterebbe il costo dove non serve.

Il costo rilevante non è dunque tecnologico, ma di qualità del dato: quanti documenti hanno nomi e struttura uniformi, quanto è affidabile il file Excel esistente, quanto la nomenclatura dei file può essere sfruttata come prima fonte di classificazione automatica. È un punto che va verificato empiricamente su un campione prima di dimensionare qualunque cosa, non assunto per ipotesi: un volume gestibile in astratto può comunque nascondere margini di fragilità nella qualità dei dati che nessuna tecnologia, da sola, può colmare.

## Permessi per informazione: il requisito più strutturante

Fra i requisiti raccolti, la granularità dei permessi, per informazione e non per documento, è quello con l'impatto architetturale maggiore. Comporta alcune conseguenze dirette:

- lo stesso documento può contenere informazioni a visibilità diversa: un manuale può avere un capitolo generico e una sezione di parametri riservati;
- l'unità di gestione dei permessi non può quindi essere il file, ma l'unità informativa: il documento va scomposto in modo consapevole (per sezioni logiche, non meccanicamente) e ogni unità classificata per tipologia, livello di riservatezza ed eventuale vincolo legato a un cliente specifico;
- il modello di sicurezza deve applicarsi al momento del recupero dell'informazione, l'indice interrogato deve restituire solo le unità autorizzate per chi interroga, e non come filtro applicato a valle su risultati già recuperati.

Questo requisito, di fatto, impone la razionalizzazione dell'informazione che era già emersa come esigenza generale: la classificazione non è un costo accessorio del progetto, ne è il cuore.

Va aggiunta un'area di attenzione realistica. Su alcune migliaia di unità informative una classificazione interamente manuale sarebbe, in teoria, affrontabile: l'obiezione non è la quantità, è che una passata manuale non lascia una regola dietro di sé. Non si ripeterebbe sui documenti che entrano domani, non garantirebbe che il criterio applicato resti lo stesso nel tempo e fra operatori diversi, e non produrrebbe alcuna misura della propria affidabilità. L'ipotesi di lavoro resta quindi una classificazione assistita: da regole deterministiche dove possibile, basate sulla tipologia di documento e sulla posizione nella cartella progetto, da un modello linguistico con validazione umana dove le regole non bastano. Il volume contenuto rende però quella validazione umana **sostenibile per intero** e non solo a campione, il che rafforza l'impianto anziché indebolirlo. Ne consegue che la classificazione va trattata come attività effettivamente centrale del progetto, non come passaggio preliminare a margine: è il tema del documento che segue, dedicato alla riservatezza e al metodo con cui è stata affrontata.

## Confronto fra gli approcci candidati

Le soluzioni indicate in fase di richiesta non sono alternative pure fra cui scegliere una sola: rispondono a esigenze diverse, e la tabella seguente ne riassume la relazione con il problema, senza pronunciarsi ancora su quale o quali adottare.

| Approccio | A cosa risponde bene | Aree di attenzione |
|---|---|---|
| Database relazionale | Relazioni esatte progetto/articolo, metadati, permessi | Non indicizza di per sé i contenuti documentali |
| Database documentale | Metadati flessibili, schemi eterogenei | La ricerca semantica resta assente senza componenti aggiuntive |
| RAG (indicizzazione vettoriale + LLM) | Domande in linguaggio naturale sui contenuti | La governance degli accessi va progettata con cura; le risposte possono risultare non tracciabili alla fonte se il sistema è mal configurato |
| Knowledge graph / LLM-Wiki | Navigazione guidata, relazioni fra entità (sonda ↔ controller ↔ articolo) | Comporta un onere non trascurabile di costruzione e manutenzione della base di conoscenza |

## La tesi dell'architettura incrementale

L'ipotesi che orienta l'intero progetto, e che i capitoli successivi verificano nella pratica, è che la soluzione non sia un singolo approccio ma un'architettura a livelli, costruita per accumulo:

```
[Archivio file esistente]
        │  ingestione + estrazione testo
        ▼
[Pipeline di scomposizione e classificazione]
   (unità informative + metadati + livello di riservatezza)
        │
        ├──► [Catalogo strutturato]  ← evoluzione del file Excel progetti/articoli
        │      entità, relazioni, permessi
        │
        ├──► [Indice full-text + vettoriale]
        │      con applicazione dei permessi in fase di recupero
        │
        └──► (fase 2) [Knowledge graph delle caratteristiche tecniche]

[Interfaccia guidata]
   ricerca esatta (catalogo) + ricerca semantica (indice) + profili di accesso
```

Il catalogo strutturato è il livello che si costruisce per primo, perché è indispensabile a qualunque sviluppo successivo e perché è l'unico, fra i tre, che risponde da solo già alla famiglia di domande prevalente. Il retrieval semantico e il knowledge graph sono evoluzioni previste, non urgenze: si aggiungono quando il livello sottostante è solido, non prima. È questa sequenza, non la scelta anticipata di una tecnologia, il criterio con cui il progetto è stato impostato e con cui, nei capitoli successivi, i moduli sono stati effettivamente realizzati.
