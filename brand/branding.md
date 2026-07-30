# Wikify: Identità e materiali di brand

Materiale di riferimento per l'app e per la skill che guiderà la realizzazione del tool. Registrato il 26/07/2026 su indicazione di Carlo.

## Nome e claim

- Nome prodotto: **Wikify**
- Claim: **"Trasforma un archivio in una wiki"** (posizionato sotto il logo)

## Logo

- File master: `wikify_logo_bianco.png` (in questa cartella): logo bianco su fondo trasparente, scontornato dall'immagine originale generata (rimossi sfondo a scacchiera e artefatti), 1077x247 px.
- Versione header app: `app/static/wikify_logo_header.png` (altezza 96 px, resa a ~44 px CSS).
- Il logo è bianco: va usato SOLO su fondi scuri o colorati (blu della testata). Su fondo chiaro serve una variante scura (non ancora prodotta).
- Origine: immagine generata con AI fornita da Carlo (sessione 9), scontorno via luminanza → alpha.

## Layout applicazione (specifica approvata)

**Header** (fondo blu `var(--blu)` #1f4e8c):
- A sinistra in alto: logo Wikify; sotto il logo: il claim in corsivo.
- A destra: chip con il nome dell'utente connesso + link "Esci".

**Barra menu** (sotto l'header, blu più profondo #163a6b):
- Icona hamburger (&#9776;) che apre e chiude il menu; stato ricordato in localStorage.
- Voci: Dizionario, Nuova scansione, Storico, Utenti.

**Footer**:
- Nota di elaborazione locale.
- Disclaimer (testo esatto, da riportare identico):

> Questo prototipo è stato progettato e implementato tramite l'orchestrazione di sistemi AI e agenti intelligenti, sotto la direzione tecnica di Carlo Verdini ✉️ cverdini@gmail.com

(Testo definitivo del 26/07/2026, sostituisce le versioni precedenti; tutto su una riga.)

## Note per la skill

- La skill che guiderà l'utente nella realizzazione del tool dovrà applicare questa identità (nome Wikify, claim, logo, disclaimer nel footer) al prototipo generato.
- Contatto da usare nel disclaimer: cverdini@gmail.com (non l'indirizzo aziendale).
- Stile testi: registro professionale, accenti corretti, mai il trattino lungo.
