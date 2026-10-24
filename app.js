const $ = s => document.querySelector(s);
let db, sim = {};
const date = s => { const [d,m,y] = s.split('/'); return new Date(`${y}-${m}-${d}T12:00:00`); };
const when = p => `${p.data} · ${p.ora}`;
const isReba = s => s === 'POLISPORTIVA REBA';
const short = s => s.replace('POLISPORTIVA ','').replace('A.S.D. ','');
const escapeHTML = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function results(p) { return sim[p.id] || p.risultato; }

// Per le gare in casa REBA: indirizzo comunicato per la prima gara.
// Se il JSON contiene l'indirizzo della singola partita, prevale sempre quello.
const REBA_FIRST_HOME_ADDRESS = 'Via Balla 13, 10137 Torino';
function venueFor(p) {
  const entry = db.palestre?.[p.casa] || db.impianti?.[p.casa] || db.indirizzi?.[p.casa];
  const obj = typeof entry === 'string' ? { indirizzo: entry } : (entry || {});
  const nome = p.palestra || p.impianto || p.nome_palestra || obj.nome || obj.palestra || obj.impianto || '';
  let indirizzo = p.indirizzo_palestra || p.indirizzo || p.campo_indirizzo || obj.indirizzo || obj.address || '';
  // Non attribuiamo Via Balla a tutte le partite in casa: sappiamo solo della prima.
  if (!indirizzo && isReba(p.casa)) {
    const homeGames = db.partite.filter(x => isReba(x.casa)).sort((a,b) => date(a.data)-date(b.data));
    if (homeGames[0]?.id === p.id) indirizzo = REBA_FIRST_HOME_ADDRESS;
  }
  return { nome, indirizzo };
}
function eloLabel(team, ratings) {
  const value = Math.round(ratings.get(team) ?? INITIAL_RATING);
  return `<span class="elo-rating" title="Coefficiente Elo stimato">(${value})</span>`;
}
function currentRatings() {
  const ratings = initialRatings();
  for (const p of orderedGames()) {
    const score = p.risultato || sim[p.id];
    if (score) updateRatings(p, score, ratings);
  }
  return ratings;
}
function renderNext(p, ratings) {
  $('#nextTitle').innerHTML = p ? `${escapeHTML(short(p.casa))} ${eloLabel(p.casa, ratings)} <span aria-hidden="true">—</span> ${escapeHTML(short(p.trasferta))} ${eloLabel(p.trasferta, ratings)}` : 'Nessuna prossima gara in calendario';
  $('#nextInfo').textContent = p ? `${when(p)} · Girone ${p.girone}` : '';
  let el = $('#nextVenue');
  if (!el) {
    el = document.createElement('div');
    el.id = 'nextVenue';
    el.style.marginTop = '12px';
    $('#nextInfo').insertAdjacentElement('afterend', el);
  }
  if (!p) { el.innerHTML = ''; return; }
  const {nome, indirizzo} = venueFor(p);
  const parts = [];
  if (nome) parts.push(`<div>🏟️ ${escapeHTML(nome)}</div>`);
  if (indirizzo) {
    const maps = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(indirizzo);
    parts.push(`<div>📍 ${escapeHTML(indirizzo)} · <a href="${escapeHTML(maps)}" target="_blank" rel="noopener noreferrer" style="color:inherit;text-decoration:underline">Indicazioni ↗</a></div>`);
  } else {
    parts.push('<div>📍 Indirizzo palestra da confermare</div>');
  }
  el.innerHTML = parts.join('');
}
// Coefficiente Elo: ogni squadra parte da 1000, senza favoriti.
// I risultati ufficiali e le simulazioni manuali aggiornano il coefficiente;
// le partite generate lo aggiornano una alla volta, in ordine di calendario.
const INITIAL_RATING = 1000;
const RATING_K = 28;
const HOME_ADVANTAGE = 30;
const orderedGames = () => [...db.partite].sort((a,b) =>
  date(a.data)-date(b.data) || String(a.ora||'').localeCompare(String(b.ora||'')) || String(a.girone).localeCompare(String(b.girone)) || String(a.id).localeCompare(String(b.id))
);
function initialRatings() {
  const ratings = new Map();
  for (const teams of Object.values(db.squadre)) for (const team of teams) ratings.set(team, INITIAL_RATING);
  return ratings;
}
function winProbability(home, away, ratings) {
  const difference = (ratings.get(home) ?? INITIAL_RATING) + HOME_ADVANTAGE - (ratings.get(away) ?? INITIAL_RATING);
  return 1 / (1 + Math.pow(10, -difference / 400));
}
function updateRatings(p, score, ratings) {
  if (!score || !Number.isFinite(Number(score[0])) || !Number.isFinite(Number(score[1]))) return;
  const [h,a] = score.map(Number);
  if (h === a) return;
  const probability = winProbability(p.casa, p.trasferta, ratings);
  const actual = h > a ? 1 : 0;
  // La differenza punti conta, ma e limitata per non premiare eccessivamente i divari ampi.
  const marginFactor = Math.min(1.6, 1 + Math.log1p(Math.abs(h-a))/10);
  const change = RATING_K * marginFactor * (actual-probability);
  ratings.set(p.casa, (ratings.get(p.casa) ?? INITIAL_RATING) + change);
  ratings.set(p.trasferta, (ratings.get(p.trasferta) ?? INITIAL_RATING) - change);
}
function normalNoise() {
  const u = Math.max(1e-9, Math.random()), v = Math.random();
  return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v);
}
function simulatedScore(p, ratings) {
  const probability = winProbability(p.casa, p.trasferta, ratings);
  const homeWins = Math.random() < probability;
  // Coefficienti simili producono gare piu equilibrate; differenze crescenti,
  // margini medi piu ampi. La casualita rimane anche a stagione avanzata.
  const gap = Math.abs((ratings.get(p.casa) ?? INITIAL_RATING) - (ratings.get(p.trasferta) ?? INITIAL_RATING));
  const margin = Math.max(1, Math.round(3 + gap/35 + Math.abs(normalNoise())*6));
  const losingScore = Math.max(8, Math.min(85, Math.round(35 + normalNoise()*10)));
  return homeWins ? [losingScore+margin, losingScore] : [losingScore, losingScore+margin];
}
function simulateRemaining() {
  const ratings = initialRatings();
  let count = 0;
  for (const p of orderedGames()) {
    // I risultati ufficiali hanno sempre precedenza. Le simulazioni manuali
    // gia inserite vengono rispettate, senza essere sovrascritte.
    let score = p.risultato || sim[p.id];
    if (!score) {
      score = simulatedScore(p, ratings);
      sim[p.id] = score;
      count++;
    }
    updateRatings(p, score, ratings);
  }
  render();
  const msg = document.querySelector('#simBulkNote');
  if (msg) msg.textContent = count ? `${count} gare simulate. Ogni squadra parte da coefficiente 1000; il coefficiente si aggiorna dopo ogni risultato.` : 'Nessuna gara rimasta da simulare. Premi Ripristina per ricominciare.';
}
function installBulkButton() {
  if (document.querySelector('#simulateAll')) return;
  const button = document.createElement('button');
  button.id = 'simulateAll';
  button.type = 'button';
  button.textContent = '🎲 Simula tutte le restanti';
  button.title = 'Simula le partite ancora senza punteggio, usando progressivamente i risultati precedenti';
  button.style.marginLeft = '8px';
  button.style.marginTop = '8px';
  document.querySelector('#simulate').insertAdjacentElement('afterend', button);
  const note = document.createElement('p');
  note.id = 'simBulkNote';
  note.style.fontSize = '0.85em';
  note.style.opacity = '0.8';
  note.textContent = 'Ogni squadra parte da coefficiente 1000. Vittorie, sconfitte e scarti aggiornano la forza stimata dopo ogni partita; la probabilità di vittoria cambia di conseguenza.';
  button.insertAdjacentElement('afterend', note);
  button.addEventListener('click', simulateRemaining);
}
function standings(g) {
  let rows = db.squadre[g].map(nome => ({nome,G:0,V:0,P:0,PF:0,PS:0,pts:0}));
  for (const p of db.partite.filter(x => x.girone === g)) {
    let r = results(p); if (!r) continue;
    let a = rows.find(x => x.nome === p.casa), b = rows.find(x => x.nome === p.trasferta);
    if (!a || !b) continue;
    const [h,v] = r;
    for (const [t,forp,against] of [[a,h,v],[b,v,h]]) {
      t.G++; t.PF += forp; t.PS += against;
      if (forp > against) { t.V++; t.pts += 2; }
      else if (forp < against) { t.P++; t.pts += 1; }
    }
  }
  return rows.sort((a,b) => b.pts-a.pts || (b.PF-b.PS)-(a.PF-a.PS) || a.nome.localeCompare(b.nome));
}
function matchHTML(p) {
  let r = results(p);
  return `<div class="match ${isReba(p.casa)||isReba(p.trasferta)?'reba':''}"><span class="date">${when(p)}</span><span>${short(p.casa)}</span><span class="score">${r?r.join(' : '):'—'}</span><span class="away">${short(p.trasferta)}</span><span class="meta date">Girone ${p.girone}</span></div>`;
}
function render() {
  let all = [...db.partite].sort((a,b) => date(a.data)-date(b.data));
  const today = new Date(new Date().toDateString());
  let upcoming = all.filter(p => date(p.data) >= today && (isReba(p.casa) || isReba(p.trasferta)) && !p.risultato);
  const ratings = currentRatings();
  renderNext(upcoming[0], ratings);
  let grp = $('#matchGroup').value;
  let filtered = all.filter(p => grp === 'all' || p.girone === grp);
  $('#matches').innerHTML = filtered.map(matchHTML).join('');
  $('#rebaGames').innerHTML = all.filter(p => isReba(p.casa)||isReba(p.trasferta)).map(matchHTML).join('');
  $('#tables').innerHTML = Object.keys(db.squadre).map(g => `<div class="table-card"><h3>GIRONE ${g}</h3><div class="table-scroll"><table><thead><tr><th>SQUADRA</th><th>G</th><th>V</th><th>P</th><th>PF</th><th>PS</th><th>PT</th></tr></thead><tbody>${standings(g).map((t,i) => `<tr class="${isReba(t.nome)?'highlight':''}"><td>${i+1}. ${escapeHTML(short(t.nome))} ${eloLabel(t.nome, ratings)}</td><td>${t.G}</td><td>${t.V}</td><td>${t.P}</td><td>${t.PF}</td><td>${t.PS}</td><td>${t.pts}</td></tr>`).join('')}</tbody></table></div></div>`).join('');
  let gs = 'ABCDE';
  $('#bracket').innerHTML = [...gs].map((g,i) => { let other = gs[(i+1)%5], a = standings(g)[0], b = standings(other)[1]; return `<div class="playcard"><strong>0${i+1}</strong><div><small>1ª GIRONE ${g}</small>${a?.G?a.nome:'Da definire'}</div><span class="vs">VS</span><div><small>2ª GIRONE ${other}</small>${b?.G?b.nome:'Da definire'}</div></div>`; }).join('');
  let done = all.filter(p => results(p));
  $('#stats').innerHTML = `<div><b>${done.length}</b><p>Partite con risultato</p></div><div><b>${all.length}</b><p>Gare nel calendario importato</p></div><div><b>25</b><p>Squadre partecipanti</p></div>`;
  $('#teams').innerHTML = Object.entries(db.squadre).map(([g,teams]) => `<div><b>GIRONE ${g}</b>${teams.map(t => `<p>${t}</p>`).join('')}</div>`).join('');
  $('#simStatus').textContent = Object.keys(sim).length ? `${Object.keys(sim).length} simulazione/i attiva/e · risultati non ufficiali` : '';
}
fetch('data/campionato.json').then(r => r.json()).then(data => {
  db = data;
  // Controllo strutturale: ogni girone deve avere 20 gare, ogni squadra 8.
  const errors = [];
  const seenIds = new Set();
  for (const game of db.partite) {
    if (seenIds.has(String(game.id))) errors.push(`Gara duplicata: ${game.id}`);
    seenIds.add(String(game.id));
  }
  for (const [group, teams] of Object.entries(db.squadre)) {
    const games = db.partite.filter(p => p.girone === group);
    if (games.length !== 20) errors.push(`Girone ${group}: ${games.length}/20 gare`);
    for (const team of teams) {
      const n = games.filter(p => p.casa === team || p.trasferta === team).length;
      if (n !== 8) errors.push(`${team}: ${n}/8 gare`);
    }
  }
  if (errors.length) {
    console.error('Calendario non valido:', errors);
    $('#status').textContent = 'ATTENZIONE: calendario incompleto, controllare la console.';
    alert('Calendario incompleto o non valido: ' + errors.join('; '));
    return;
  }
  if (db.ultimo_aggiornamento_fip) {
    $('#sync').textContent = 'Risultati FIP aggiornati: ' + new Date(db.ultimo_aggiornamento_fip).toLocaleString('it-IT');
    $('#status').textContent = 'Risultati FIP sincronizzati.';
  }
  $('#matchGroup').innerHTML = '<option value="all">Tutti i gironi</option>' + Object.keys(db.squadre).map(g => `<option value="${g}">Girone ${g}</option>`).join('');
  $('#matchGroup').onchange = render;
  // Raggruppa per giornata ufficiale, quando disponibile nei dati.
  // In assenza del campo giornata, raggruppa per data senza inventare numeri di turno.
  const available = db.partite.filter(p => !p.risultato).sort((a,b) =>
    date(a.data) - date(b.data) || String(a.ora || '').localeCompare(String(b.ora || '')) || String(a.girone).localeCompare(String(b.girone))
  );
  const groups = new Map();
  for (const p of available) {
    const hasRound = p.giornata !== undefined && p.giornata !== null && String(p.giornata).trim() !== '';
    const key = hasRound ? `turno:${p.giornata}` : `data:${p.data}`;
    if (!groups.has(key)) groups.set(key, {label: hasRound ? `Giornata ${p.giornata}` : `Partite del ${p.data} (giornata non indicata)`, games: []});
    groups.get(key).games.push(p);
  }
  $('#simMatch').innerHTML = [...groups.values()].map(group =>
    `<optgroup label="${escapeHTML(group.label)}">${group.games.map(p =>
      `<option value="${escapeHTML(p.id)}">${escapeHTML(p.data)} · Girone ${escapeHTML(p.girone)} · ${escapeHTML(short(p.casa))} vs ${escapeHTML(short(p.trasferta))}</option>`
    ).join('')}</optgroup>`
  ).join('');
  $('#simulate').onclick = () => {
    let h = Number($('#scoreHome').value), a = Number($('#scoreAway').value);
    if ($('#scoreHome').value === '' || $('#scoreAway').value === '' || h === a || h < 0 || a < 0) { alert('Inserisci due punteggi validi e diversi.'); return; }
    if (!$('#simMatch').value) { alert('Nessuna partita disponibile per la simulazione'); return; }
    sim[$('#simMatch').value] = [h,a]; render();
  };
  $('#reset').onclick = () => { sim = {}; render(); const msg = $('#simBulkNote'); if (msg) msg.textContent = 'Simulazioni azzerate. Puoi avviare una nuova simulazione.'; };
  installBulkButton();
  render();
}).catch(e => { $('#nextTitle').textContent = 'Dati non caricati'; console.error(e); });

// Elo discreto, senza modificare il foglio di stile del sito.
(function installEloStyle(){
  if (document.getElementById("elo-rating-style")) return;
  const style = document.createElement("style");
  style.id = "elo-rating-style";
  style.textContent = ".elo-rating{font-size:.72em;font-weight:400;opacity:.55;white-space:nowrap;letter-spacing:0;color:inherit}#nextTitle .elo-rating{font-size:.48em;vertical-align:middle;opacity:.55}";
  document.head.appendChild(style);
})();