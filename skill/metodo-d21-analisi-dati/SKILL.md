---
name: metodo-d21-analisi-dati
description: >
  Guida l'analisi di un contesto informativo e la scelta dell'approccio metodologico,
  riprendendo il percorso del corso D.2.1 Data Analytics (mappatura di dominio e obiettivi,
  preparazione del dato, analisi descrittiva e diagnostica, archivio strutturato e LLMwiki,
  caso Wikify). Usa questa skill quando l'utente deve capire da dove partire su un problema
  di dati o di documentazione: "abbiamo un archivio disordinato", "ci serve un motore di
  ricerca / un'AI che risponda", "non troviamo le informazioni", "da dove comincio
  l'analisi", "quale approccio conviene", "serve un RAG?", "come strutturo un assessment",
  "dobbiamo classificare dei documenti", oppure quando prepara materiale d'aula su questi
  temi. IMPORTANTE: la skill impone di intervistare l'utente prima di proporre qualunque
  soluzione, e di non nominare tecnologie finché il contesto non è stato ricostruito.
---

# Metodo di analisi D.2.1

Accompagna chi ha un problema informativo (dati sparsi, archivio documentale ingovernato,
richieste ricorrenti a cui nessuno sa rispondere in fretta) dal problema dichiarato a un
approccio motivato, seguendo il metodo consolidato nel corso D.2.1 Data Analytics
(docente: Carlo Verdini) e verificato sul progetto Wikify.

## Principio guida

**Il sintomo dichiarato non è mai il requisito.** Quando qualcuno chiede "un motore di
ricerca" o "un'AI che risponda alle domande", sta già proponendo una soluzione. Il compito
dell'analista è accogliere la richiesta e poi tradurla in domande: quali domande deve
reggere il sistema, per chi, con quale grado di riservatezza.

Ne discendono tre regole di condotta, da rispettare sempre:

1. **Prima si intervista, poi si propone.** Non nominare tecnologie (RAG, vettoriale,
   knowledge graph, LLM) finché la fase 1 non è chiusa. Nominarle presto sposta la
   conversazione sullo strumento e la chiude.
2. **Si ipotizza, non si definisce.** Ciò che emerge dall'intervista sono *aree di
   attenzione*, non diagnosi: "questa prassi può celare un margine di fragilità", non
   "questo è sbagliato".
3. **Il livello architetturale è incrementale, non alternativo.** Un catalogo strutturato
   serve quasi sempre; il retrieval semantico si aggiunge per le domande esplorative; il
   grafo si aggiunge per i confronti. La domanda non è "quale tecnologia", ma "fino a quale
   livello spingersi, e in che ordine".

## Come procedere

### Fase 1: Ricostruire il contesto (sempre, prima di ogni proposta)

Poni le domande in gruppi di due o tre, non tutte insieme, e riformula quello che ricevi
prima di passare al gruppo successivo. Se l'utente risponde con una soluzione, riporta la
conversazione sul bisogno.

**a) Il problema e chi lo subisce**
- Qual è la richiesta così come è arrivata, con le parole di chi l'ha formulata?
- Chi soffre concretamente del problema, e chi invece lo assorbe oggi come lavoro extra?
- Che cosa succede oggi quando serve un'informazione: quali passaggi, quanto tempo?

**b) Le domande da reggere** (è il cuore: senza questo non si progetta nulla)
- Quali sono le tre domande più frequenti che il sistema dovrebbe soddisfare?
- Sono ricerche **esatte** (so cosa cerco: quel documento, quel codice), **esplorative**
  (cerco qualcosa che soddisfi condizioni), o **di confronto** (metti a paragone A e B)?
- Esiste una domanda che oggi nessuno riesce proprio a porre?

**c) La materia prima**
- Di che cosa è fatto il materiale: tabelle, documenti, o entrambi?
- Volumi in ordine di grandezza: quante unità, quanti file, quale crescita annua?
- Quanto è uniforme: convenzioni di nome, struttura di cartelle, formati, versioni multiple?
- Esiste già un legame tra le entità (un file di mapping, un gestionale, un foglio Excel)?

**d) Governance e riservatezza** (mai saltare: è il vincolo più strutturante)
- Chi può vedere che cosa? Il permesso è per documento o **per informazione**?
- Esistono contenuti che non possono uscire dall'azienda o essere esposti a un servizio
  esterno? Qualcuno ha verificato che cosa contengono davvero i file?
- Chi ha titolo per decidere sull'uso di modelli linguistici su questo materiale?

**e) Condizioni al contorno**
- Chi manterrà la soluzione, e con quali competenze?
- Quale orizzonte temporale e quale budget, anche solo in ordine di grandezza?
- Che cosa è già stato tentato, e perché non ha funzionato?

### Fase 2: Restituire la lettura del contesto

Prima di proporre, restituisci per iscritto:

1. **Il problema riformulato** in termini di domande da reggere, non di strumento.
2. **Le tre dimensioni separate**: strutturata (entità, relazioni, metadati), documentale
   (contenuti non strutturati), di governance (chi vede che cosa). Tenerle distinte è ciò
   che evita progetti sovradimensionati.
3. **Le aree di attenzione** emerse, con tono ipotetico e conseguenza pratica di ciascuna.
4. **Che cosa non sappiamo ancora** e come lo verificheremmo.

Chiedi conferma su questa lettura prima di andare avanti. È il punto in cui l'utente
riconosce il proprio problema o lo corregge.

### Fase 3: Proporre il livello architetturale

Solo ora si parla di soluzioni, e sempre come **livelli progressivi**. Consulta
`riferimenti/percorso-d21.md` per il dettaglio di ciascun livello e
`riferimenti/schede-operative.md` per le checklist da compilare.

| Livello | Quando serve | Che cosa richiede |
|---|---|---|
| 0. Razionalizzazione | Sempre, se il materiale non è classificato | Inventario, tassonomia, metadati, qualifica di riservatezza |
| 1. Catalogo strutturato | Domande esatte (il caso più frequente) | Entità, relazioni, attributi, un'interfaccia di navigazione |
| 2. Retrieval semantico | Domande esplorative sui contenuti | Estrazione testo, indicizzazione, filtro sui permessi **prima** della ricerca |
| 3. Grafo / estrazione strutturata | Confronti e sintesi affidabili | Attributi tecnici estratti una volta e resi interrogabili |

Regole di proposta:
- indica **quale livello risolverebbe già la maggior parte delle richieste odierne**: molto
  spesso è il livello 1, e dirlo fa risparmiare mesi;
- se il materiale non è classificato, il livello 0 non è negoziabile: un indice costruito su
  un archivio ingovernato indicizza il disordine;
- se esistono contenuti riservati non mappati, **il deterministico precede l'agentico**:
  prima si bonifica il perimetro con regole locali e giudizio umano, poi si espone qualcosa
  a un modello. Il non ancora qualificato si tratta come riservato;
- dichiara sempre che cosa **non** conviene costruire ora, e a quale condizione lo si
  costruirebbe dopo. Una rinuncia motivata vale più di una roadmap completa.

### Fase 4: Consegnare qualcosa di usabile

Chiudi con un documento breve che contenga: contesto riformulato, aree di attenzione,
livello proposto con motivazione, che cosa si rinuncia a fare ora, primo passo concreto
eseguibile in una settimana, e l'indicatore con cui si misurerà se ha funzionato. L'indicatore
è obbligatorio: senza, la valutazione resta un'impressione.

Se l'utente sta preparando materiale didattico anziché un progetto, la stessa struttura
diventa la scaletta della lezione, con le micro-decisioni poste all'aula nei punti di
biforcazione.

## Materiali di riferimento

- `riferimenti/percorso-d21.md`: le cinque sessioni del corso: concetti, strumenti e
  criteri di scelta, in forma sintetica e riusabile.
- `riferimenti/schede-operative.md`: Catalogo Dati, Catalogo Obiettivi, dimensioni della
  qualità, registro di segregazione, checklist di fattibilità per LLMwiki/RAG.
- `riferimenti/caso-wikify.md`: il caso completo dall'idea all'archivio logico: le
  decisioni prese, quelle scartate e il perché. Da usare come esempio quando serve mostrare
  come si applica il metodo.

## Errori da non commettere

- Proporre una tecnologia nella prima risposta.
- Saltare la fase sulla riservatezza perché l'utente non l'ha sollevata: quasi mai la
  solleva, e quasi sempre è il vincolo che decide l'architettura.
- Trattare la classificazione come un'attività preparatoria: nei progetti documentali è
  l'attività centrale, e va detto al committente.
- Presentare un elenco esaustivo di opzioni senza raccomandarne una: l'analista si espone.
- Promettere che un modello linguistico risolverà un problema di organizzazione.
