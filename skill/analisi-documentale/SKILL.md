---
name: analisi-documentale
description: >
  Guida l'analisi di un archivio documentale disordinato e la scelta dell'approccio con cui
  renderlo consultabile: ricostruzione del contesto, domande che l'archivio deve reggere,
  qualificazione della riservatezza, scelta del livello architetturale. Usa questa skill
  quando l'interlocutore ha documenti che non riesce a trovare o a governare: "abbiamo un
  archivio disordinato", "non troviamo le informazioni", "ci serve un motore di ricerca",
  "ci serve un'AI che risponda alle domande sui nostri documenti", "serve un RAG?",
  "dobbiamo classificare dei documenti", "chi puo' vedere cosa", "da dove comincio".
  IMPORTANTE: la skill impone di intervistare prima di proporre, e vieta di nominare
  tecnologie finche' il contesto non e' stato ricostruito.
---

# Analisi documentale

Accompagna chi ha un archivio documentale ingovernato, con richieste ricorrenti a cui nessuno
sa rispondere in fretta, dal problema dichiarato a un approccio motivato. Il metodo è quello
verificato sul progetto Wikify, che porta un archivio dallo stato grezzo allo stato di
archivio logico.

## Principio guida

**Il sintomo dichiarato non è mai il requisito.** Quando qualcuno chiede "un motore di
ricerca" o "un'AI che risponda alle domande", sta già proponendo una soluzione. Il compito è
accogliere la richiesta e poi tradurla in domande: quali domande deve reggere il sistema, per
chi, con quale grado di riservatezza.

Ne discendono tre regole di condotta, da rispettare sempre:

1. **Prima si intervista, poi si propone.** Non nominare tecnologie (RAG, indice vettoriale,
   knowledge graph, modelli linguistici) finché la fase 1 non è chiusa. Nominarle presto
   sposta la conversazione sullo strumento e la chiude.
2. **Si ipotizza, non si definisce.** Ciò che emerge dall'intervista sono *aree di
   attenzione*, non diagnosi: "questa prassi può celare un margine di fragilità", non
   "questo è sbagliato".
3. **Il livello architetturale è incrementale, non alternativo.** Un catalogo strutturato
   serve quasi sempre; il recupero semantico si aggiunge per le domande esplorative; il grafo
   si aggiunge per i confronti. La domanda non è "quale tecnologia", ma "fino a quale livello
   spingersi, e in che ordine".

## Come procedere

### Fase 1: ricostruire il contesto (sempre, prima di ogni proposta)

Poni le domande in gruppi di due o tre, non tutte insieme, e riformula quello che ricevi prima
di passare al gruppo successivo. Se l'interlocutore risponde con una soluzione, riporta la
conversazione sul bisogno.

**a) Il problema e chi lo subisce**
- Qual è la richiesta così come è arrivata, con le parole di chi l'ha formulata?
- Chi soffre concretamente del problema, e chi invece lo assorbe oggi come lavoro extra?
- Che cosa succede quando serve un documento: quali passaggi, quanto tempo?
- Quanto di ciò che permette di trovare le informazioni è conoscenza tacita di una persona?

**b) Le domande da reggere** (è il cuore: senza questo non si progetta nulla)
- Quali sono le tre domande più frequenti che il sistema dovrebbe soddisfare?
- Sono ricerche **esatte** (so quale documento voglio), **esplorative** (cerco qualcosa che
  soddisfi condizioni) o **di confronto** (metti a paragone A e B)?
- Esiste una domanda che oggi nessuno riesce proprio a porre?

**c) La materia prima**
- Di quali formati è fatto l'archivio? Esistono documenti solo scansionati, senza testo
  estraibile?
- Volumi in ordine di grandezza: quante cartelle, quanti documenti, quale crescita annua?
- Quanto è uniforme: convenzioni di nome, struttura ricorrente delle cartelle, versioni
  multiple dello stesso contenuto?
- Esiste già un legame fra i documenti e le entità del dominio (un file di mapping, un
  gestionale, un foglio di calcolo tenuto a parte)?

**d) Governance e riservatezza** (mai saltare: è il vincolo più strutturante)
- Chi può vedere che cosa? Il permesso è per documento o **per informazione**?
- Esistono contenuti che non possono uscire dall'organizzazione o essere esposti a un servizio
  esterno? Qualcuno ha verificato che cosa contengono davvero i documenti?
- Chi ha titolo per decidere sull'uso di modelli linguistici su questo materiale?

**e) Condizioni al contorno**
- Chi manterrà la soluzione, e con quali competenze?
- Con quale frequenza cambiano i documenti?
- Che cosa è già stato tentato, e perché non ha funzionato?

### Fase 2: restituire la lettura del contesto

Prima di proporre, restituisci per iscritto:

1. **Il problema riformulato** in termini di domande da reggere, non di strumento.
2. **Le tre dimensioni separate**: strutturata (entità, relazioni, metadati), documentale
   (contenuti non strutturati), di governance (chi vede che cosa). Tenerle distinte è ciò che
   evita soluzioni sovradimensionate.
3. **Le aree di attenzione** emerse, con tono ipotetico e conseguenza pratica di ciascuna.
4. **Che cosa non sappiamo ancora** e come lo verificheremmo.

Chiedi conferma su questa lettura prima di andare avanti. È il punto in cui l'interlocutore
riconosce il proprio problema o lo corregge.

### Fase 3: proporre il livello architetturale

Solo ora si parla di soluzioni, e sempre come **livelli progressivi**. Le checklist da
compilare sono in `riferimenti/schede-operative.md`.

| Livello | Quando serve | Che cosa richiede |
|---|---|---|
| 0. Razionalizzazione | Sempre, se il materiale non è classificato | Inventario, tassonomia delle tipologie, metadati, qualifica di riservatezza |
| 1. Catalogo strutturato | Domande esatte (il caso più frequente) | Entità, relazioni, attributi, un'interfaccia di navigazione |
| 2. Recupero semantico | Domande esplorative sui contenuti | Estrazione del testo, indicizzazione, filtro sui permessi **prima** della ricerca |
| 3. Grafo o estrazione strutturata | Confronti e sintesi affidabili | Attributi tecnici estratti una volta e resi interrogabili |

Regole di proposta:

- indica **quale livello risolverebbe già la maggior parte delle richieste odierne**: molto
  spesso è il livello 1, e dirlo fa risparmiare mesi;
- se il materiale non è classificato, il livello 0 non è negoziabile: un indice costruito su un
  archivio ingovernato indicizza il disordine;
- se esistono contenuti riservati non mappati, **il deterministico precede l'agentico**: prima
  si bonifica il perimetro con regole locali e giudizio umano, poi si espone qualcosa a un
  modello. Il non ancora qualificato si tratta come riservato;
- **misura il volume prima di dimensionare**: su poche migliaia di documenti l'infrastruttura
  specialistica è un costo senza beneficio, e la validazione umana integrale diventa
  sostenibile; su centinaia di migliaia il ragionamento si capovolge;
- dichiara sempre che cosa **non** conviene costruire ora, e a quale condizione lo si
  costruirebbe dopo. Una rinuncia motivata vale più di una roadmap completa.

### Fase 4: consegnare qualcosa di usabile

Chiudi con un documento breve che contenga: contesto riformulato, aree di attenzione, livello
proposto con motivazione, che cosa si rinuncia a fare ora, primo passo concreto eseguibile in
una settimana, e l'indicatore con cui si misurerà se ha funzionato. L'indicatore è
obbligatorio: senza, la valutazione resta un'impressione. Per un archivio documentale gli
indicatori naturali sono la **copertura di classificazione** e la **completezza per entità**.

## Materiali di riferimento

- `riferimenti/schede-operative.md`: le schede da compilare durante l'analisi, cioè catalogo
  delle fonti, catalogo degli obiettivi, dimensioni della qualità, registro di segregazione e
  checklist di fattibilità in dodici punti per un livello semantico.
- `riferimenti/caso-wikify.md`: il caso completo dall'idea all'archivio logico, con le
  decisioni prese e quelle scartate. Da usare come esempio quando serve mostrare come si
  applica il metodo.

## Errori da non commettere

- Proporre una tecnologia nella prima risposta.
- Saltare la fase sulla riservatezza perché l'interlocutore non l'ha sollevata: quasi mai la
  solleva, e quasi sempre è il vincolo che decide l'architettura.
- Trattare la classificazione come attività preparatoria: nei progetti documentali è
  l'attività centrale, e va detto a chi commissiona.
- Presentare un elenco esaustivo di opzioni senza raccomandarne una.
- Promettere che un modello linguistico risolverà un problema di organizzazione.
