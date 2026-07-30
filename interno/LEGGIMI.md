# Materiale interno, non si consegna

Questa cartella contiene i documenti di lavoro del progetto: restano vivi e vengono
alimentati man mano, ma **non fanno parte di ciò che si condivide** con allievi o clienti.

Lo script `strumenti/prepara_condivisione.sh` esclude questa cartella dalla copia destinata
alla consegna, e fallisce se per qualsiasi ragione dovesse ritrovarsela dentro.

## Contenuto

| File | Che cos'è | Come si usa |
|---|---|---|
| `registro_sessioni.md` | Il registro cronologico del lavoro: per ogni sessione, contesto, alternative discusse, decisione presa e motivazione. È una sintesi ragionata, non una trascrizione | **Si continua ad alimentare**: una voce per sessione di lavoro, in testa al registro |
| `assessment_originale.md` | Il piano operativo dell'assessment come fu redatto all'inizio, con le cinque fasi e le schede di rilevazione | Documento **storico**: alcune fasi sono state superate dai moduli realizzati. Non va aggiornato, va consultato per capire da dove si è partiti |

## Perché non si condivide

Non per riservatezza, ma per **finalità**. Sono documenti di processo: registrano
ripensamenti, alternative scartate, errori corretti e valutazioni ancora aperte. Utilissimi
a chi conduce il progetto, disorientanti per chi lo riceve: che ha bisogno di una linea
chiara, non della cronaca di come si è arrivati a tracciarla.

La documentazione destinata a terzi vive in `documentazione/`, è numerata secondo l'ordine
di lettura e non contiene cronologia.

## Regola pratica

Quando una decisione presa qui diventa stabile, va **travasata** nel documento di
`documentazione/` che le corrisponde: il registro conserva il come e il perché ci si è
arrivati, la documentazione condivisa espone il che cosa. Se le due versioni divergono, fa
fede la documentazione condivisa: è quella che qualcuno userà.
