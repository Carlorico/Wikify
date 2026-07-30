# Materiale del docente: non si consegna

Questa cartella contiene i documenti di lavoro e di conduzione del progetto: restano vivi e
vengono alimentati man mano, ma **non fanno parte di ciò che si condivide** con allievi o
clienti.

Lo script `strumenti/prepara_condivisione.sh` esclude questa cartella dalla copia destinata
alla consegna, e si interrompe con errore se per qualsiasi ragione dovesse ritrovarsela
dentro.

## Contenuto

| File | Che cos'è | Come si usa |
|---|---|---|
| `percorso_workshop.md` | La traccia di conduzione della sessione: otto segmenti per due ore, cosa mostrare a schermo in ciascuno, le micro-decisioni da porre all'aula, il percorso della dimostrazione, l'esercizio con le sue alternative | Si usa mentre si conduce. Non va consegnato: contiene tempi, regie e risposte attese, cioè il materiale del docente e non quello dell'allievo |
| `registro_sessioni.md` | Il registro cronologico del lavoro: per ogni sessione, contesto, alternative discusse, decisione presa e motivazione. È una sintesi ragionata, non una trascrizione | **Si continua ad alimentare**: una voce per sessione di lavoro, in testa al registro |
| `assessment_originale.md` | Il piano operativo dell'assessment come fu redatto all'inizio, con le cinque fasi e le schede di rilevazione | Documento **storico**: alcune fasi sono state superate dai moduli realizzati. Non va aggiornato, va consultato per capire da dove si è partiti |

## Perché non si condivide

Non per riservatezza, ma per **finalità**. Sono documenti di processo e di regia:
registrano ripensamenti, alternative scartate, tempi di conduzione e valutazioni ancora
aperte. Utilissimi a chi conduce il progetto, disorientanti per chi lo riceve, che ha
bisogno di una linea chiara e non della cronaca di come si è arrivati a tracciarla.

La documentazione destinata a terzi vive in `documentazione/`, è numerata secondo l'ordine di
lettura e non contiene né cronologia né indicazioni di conduzione.

## Regola pratica

Quando una decisione presa qui diventa stabile, va **travasata** nel documento di
`documentazione/` che le corrisponde: il registro conserva il come e il perché ci si è
arrivati, la documentazione condivisa espone il che cosa. Se le due versioni divergono, fa
fede la documentazione condivisa: è quella che qualcuno userà.

## Preparare la cartella da consegnare

```
strumenti/prepara_condivisione.sh [cartella_di_destinazione]
```

Senza argomenti la destinazione è `../Wikify_da_consegnare`, cartella sorella del progetto.
Lo script produce una copia completa e funzionante di Wikify, **escludendo** questa cartella,
la cartella `strumenti/`, i dati di lavoro e le scorie tecniche. Al termine verifica la
copia e si interrompe con errore se un elemento escluso è sopravvissuto, così la consegna
non dipende dall'attenzione di chi la effettua.

Da ricordare in fase di consegna:

- **l'archivio di prova si consegna a parte** (`../Wikify_archivio_prova`): non è incluso nel
  pacchetto perché i documenti appartengono ai rispettivi produttori e non vanno
  ridistribuiti in un archivio unico. Se lo si consegna, va accompagnato dall'indicazione
  della fonte;
- i dati di lavoro non sono inclusi per costruzione: risiedono in `../Wikify_dati`;
- l'ambiente Python va ricreato sulla macchina di destinazione seguendo la guida di avvio
  (`documentazione/07` per Mac, `documentazione/08` per Windows).
