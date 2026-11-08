## v0.5.1 — Revisione simulazione Play-In — 08/11/2026
- Su conferma dell’utente, se le due REBA occupano i primi due posti e lo spareggio è risolto, la terza subentra nella proiezione al posto della REBA esclusa.
- Il subentro è esplicitamente segnalato come ipotesi della simulazione da confermare con FIP, senza modificare risultati o classifica sportiva.
- Nessun subentro per parità interna irrisolta o se solo una REBA è nelle prime due.
- Stato precedente conservato nel ramo archive/v0.5.1-pre-subentro-terza.

## v0.5.1 — 08/11/2026
- Play-In: una sola ammessa tra REBA e REBA Bianco, stessa società (PDF FIP, formula U13F 2026/27).
- Per le proiezioni, scelta della meglio classificata con gli spareggi esistenti a partire dagli scontri diretti; parità residue segnalate come da definire.
- Altra squadra indicata «Non ammessa – stessa società»; nessuna fusione di risultati o classifica e nessun ripescaggio automatico della terza.
- Regola applicata al tracker dopo risultati ufficiali, simulazioni manuali e simulazione completa; reset ripristina la proiezione dei risultati ufficiali.
- Archivio pre-release: ramo archive/pre-v0.5.1-2026-11-08, commit e8bdb29e718836abf9e679e76dd02a6e73d9b99c; indice nella cartella ARCHIVE su Drive.

## v0.4.4 — 03/11/2026
- Ridotta la finestra del centro partite da 12 a 8 righe, mantenendo lo scorrimento.
- Aggiunto il filtro Solo REBA in Risultati e partite, prima del selettore gironi.
- Con Solo REBA attivo, tutte le gare della squadra principale restano in ordine cronologico e il selettore gironi è disabilitato; disattivandolo si ripristina il girone precedente.
- Rimossi Calendario REBA, il collegamento di navigazione e il relativo rendering duplicato.
- Preservati evidenziazioni dei risultati recenti, simulatore, classifiche, layout responsive e automazione FIP.

## v0.3.8 - 25/10/2026
- Ripristinata cartella assets con logo WebP trasparente.
- Aggiornati riferimento e resa CSS del logo, senza alterare proporzioni.
- Dati sportivi e aggiornamento FIP invariati.

## v0.3.7 — 25/10/2026
- Sostituito il logo con il JPEG `Logo_037.jpeg` approvato, senza alterazioni di proporzioni o grafica.
- Ottimizzata la dimensione del logo su smartphone: massimo 210 px di larghezza e 170 px di altezza.
- Aggiunto il logo Ultras REBA (cobra verde neon) come `assets/logo037.png` e aggiornato il riferimento nella pagina.
- Mantenute le dimensioni grafiche e le regole CSS; aggiornato il footer a v0.3.7.
- Nessuna modifica a calendario, simulazione Elo, classifiche o sincronizzazione FIP.

## v0.3.6 — 24/10/2026
- Classifiche: 2 punti per vittoria e 0 per sconfitta; spareggi di parita' con scontri diretti e quozienti canestri (REG FIP 25/03/2026, artt. 60 e 62).
- Classifiche provvisorie durante la stagione; criteri che richiedono dati non presenti nel feed da verificare con FIP.
- Numero versione e data visibili nel footer.
- Colori dei riquadri sotto la mappa invariati rispetto a v0.3.4.

## v0.3.4 — 24/10/2026
- Cambiati esclusivamente i colori dei cinque riquadri delle squadre sotto la mappa: A rosso, B verde, C blu, D arancione, E viola.
- Sfondi scuri coordinati, bordi e titoli in tinta.
- Nessuna modifica a mappa, calendari, classifiche, simulatore o script FIP.

# REBA U13F — Registro release

## v03.2 — 24/10/2026
- Pubblicati su GitHub `app.js`, `style.css`, `data/campionato.json` e `scripts/update_fip.py` dalla release v03.2.
- Calendario strutturale: 100 gare, 20 per girone, 8 per squadra.
- Conservato il workflow GitHub Actions esistente `.github/workflows/update.yml`.
- Sincronizzazione risultati FIP ancora da validare con risultati ufficiali pubblicati.
- Il pacchetto integrale, compreso il logo, resta archiviato in Google Drive `REBA-U13F/CURRENT`.

## v03
Calendario corretto, simulazione Elo, logo aggiornato.

## v02
Versione archiviata.
