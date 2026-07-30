# La skill del metodo: che cos'è e come si installa

*Risponde alla domanda: che cosa è la skill che accompagna il progetto, a che serve e come
si mette in funzione sul proprio computer.*

## Che cos'è

Nella cartella `skill/` del progetto si trova **`metodo-d21-analisi-dati`**, una *skill* per
Claude Code: un insieme di istruzioni che Claude carica quando serve, e che lo mette in
condizione di condurre l'analisi di un contesto informativo con il metodo seguito in questo
progetto, anziché rispondere a intuito.

Non è un programma e non elabora dati. È **conoscenza metodologica confezionata**: quando la
si interpella, Claude smette di proporre tecnologie e comincia a fare domande, nell'ordine in
cui hanno senso.

Che cosa contiene:

| File | Contenuto |
|---|---|
| `SKILL.md` | Il metodo in quattro fasi: ricostruire il contesto, restituire la lettura, proporre il livello architetturale, consegnare qualcosa di usabile. Con le domande da porre in ciascuna fase e gli errori da non commettere |
| `riferimenti/percorso-d21.md` | Sintesi delle cinque sessioni del corso: concetti, strumenti e criteri di scelta, in forma riusabile |
| `riferimenti/schede-operative.md` | Le schede da compilare: Catalogo Dati, Catalogo Obiettivi, dimensioni della qualità, registro di segregazione, checklist di fattibilità per un livello semantico in dodici punti |
| `riferimenti/caso-wikify.md` | Il caso completo dall'idea all'archivio logico, con le decisioni prese e quelle scartate |

Il vincolo che la caratterizza, e che è la ragione per cui esiste: **impone di intervistare
prima di proporre**, e vieta di nominare tecnologie finché il contesto non è stato
ricostruito. È la traduzione operativa del principio esposto nel documento
[01](01_contesto_e_problema.md): il sintomo dichiarato non è il requisito.

## Prerequisito

Serve **Claude Code** installato e funzionante. Se non lo si ha, la cartella `skill/` resta
comunque leggibile come documento: i quattro file sono normale testo in formato Markdown e si
possono consultare, o incollare in una conversazione con un altro assistente, senza perdere
il contenuto del metodo.

## Installazione su Mac

Le skill personali risiedono in `~/.claude/skills/`. Dal Terminale, portandosi nella cartella
del progetto:

```
mkdir -p ~/.claude/skills
cp -R skill/metodo-d21-analisi-dati ~/.claude/skills/
```

## Installazione su Windows

Le skill personali risiedono in `%USERPROFILE%\.claude\skills\`. Dal Prompt dei comandi,
nella cartella del progetto:

```
if not exist "%USERPROFILE%\.claude\skills" mkdir "%USERPROFILE%\.claude\skills"
xcopy /E /I "skill\metodo-d21-analisi-dati" "%USERPROFILE%\.claude\skills\metodo-d21-analisi-dati"
```

## Verifica

Chiudere e riaprire Claude Code, in modo che rilegga le skill disponibili. Poi, in una
sessione, verificare in uno dei due modi:

1. digitare `/metodo-d21-analisi-dati` e inviare: la skill viene richiamata
   esplicitamente;
2. oppure descrivere un problema che la riguarda, per esempio "abbiamo un archivio
   documentale disordinato e ci chiedono un motore di ricerca, da dove comincio": Claude
   dovrebbe riconoscere il contesto e cominciare a intervistare anziché proporre soluzioni.

Il secondo modo è anche la prova che la skill sia stata scritta bene: se non si attiva da
sola su un caso che le compete, il problema non è l'installazione ma la sua descrizione.

## Come si usa

Si usa conversando. Il comportamento atteso è questo:

- **prima fase**: Claude pone domande in gruppi di due o tre, non tutte insieme, su problema
  e persone coinvolte, domande che il sistema deve reggere, materia prima disponibile,
  governance e riservatezza, condizioni al contorno. Se si risponde con una soluzione, la
  riporta sul bisogno;
- **seconda fase**: restituisce per iscritto il problema riformulato in termini di domande, le
  tre dimensioni tenute separate, le aree di attenzione emerse e ciò che ancora non si sa.
  Chiede conferma prima di procedere;
- **terza fase**: propone il livello architetturale, dichiarando quale sarebbe già sufficiente
  e che cosa **non** conviene costruire ora;
- **quarta fase**: consegna un documento breve con il primo passo eseguibile e l'indicatore
  con cui si misurerà se ha funzionato.

Se Claude salta la prima fase e propone subito una tecnologia, la skill non si è attivata.

## Aggiornamento e rimozione

La copia installata in `~/.claude/skills/` è indipendente da quella del progetto: se la
cartella `skill/` viene aggiornata in una versione successiva, l'installazione va rifatta
sovrascrivendo la precedente con gli stessi comandi.

Per disinstallarla è sufficiente eliminare la cartella `metodo-d21-analisi-dati` da
`~/.claude/skills/` (su Windows da `%USERPROFILE%\.claude\skills\`). Non lascia
configurazioni residue altrove.

## Che cosa la skill non fa

Non legge l'archivio, non classifica documenti e non sostituisce Wikify: quello è il compito
dell'applicazione. Non produce nemmeno un progetto pronto. Conduce un'analisi e la
restituisce argomentata, lasciando le decisioni a chi le deve prendere. È il complemento
metodologico dello strumento, non una sua funzione.
