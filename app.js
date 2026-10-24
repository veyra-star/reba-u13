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
function renderNext(p) {
  $('#nextTitle').textContent = p ? `${short(p.casa)}  —  ${short(p.trasferta)}` : 'Nessuna prossima gara in calendario';
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
  renderNext(upcoming[0]);
  let grp = $('#matchGroup').value;
  let filtered = all.filter(p => grp === 'all' || p.girone === grp);
  $('#matches').innerHTML = filtered.map(matchHTML).join('');
  $('#rebaGames').innerHTML = all.filter(p => isReba(p.casa)||isReba(p.trasferta)).map(matchHTML).join('');
  $('#tables').innerHTML = Object.keys(db.squadre).map(g => `<div class="table-card"><h3>GIRONE ${g}</h3><div class="table-scroll"><table><thead><tr><th>SQUADRA</th><th>G</th><th>V</th><th>P</th><th>PF</th><th>PS</th><th>PT</th></tr></thead><tbody>${standings(g).map((t,i) => `<tr class="${isReba(t.nome)?'highlight':''}"><td>${i+1}. ${short(t.nome)}</td><td>${t.G}</td><td>${t.V}</td><td>${t.P}</td><td>${t.PF}</td><td>${t.PS}</td><td>${t.pts}</td></tr>`).join('')}</tbody></table></div></div>`).join('');
  let gs = 'ABCDE';
  $('#bracket').innerHTML = [...gs].map((g,i) => { let other = gs[(i+1)%5], a = standings(g)[0], b = standings(other)[1]; return `<div class="playcard"><strong>0${i+1}</strong><div><small>1ª GIRONE ${g}</small>${a?.G?a.nome:'Da definire'}</div><span class="vs">VS</span><div><small>2ª GIRONE ${other}</small>${b?.G?b.nome:'Da definire'}</div></div>`; }).join('');
  let done = all.filter(p => results(p));
  $('#stats').innerHTML = `<div><b>${done.length}</b><p>Partite con risultato</p></div><div><b>${all.length}</b><p>Gare nel calendario importato</p></div><div><b>25</b><p>Squadre partecipanti</p></div>`;
  $('#teams').innerHTML = Object.entries(db.squadre).map(([g,teams]) => `<div><b>GIRONE ${g}</b>${teams.map(t => `<p>${t}</p>`).join('')}</div>`).join('');
  $('#simStatus').textContent = Object.keys(sim).length ? `${Object.keys(sim).length} simulazione/i attiva/e · risultati non ufficiali` : '';
}
fetch('data/campionato.json').then(r => r.json()).then(data => {
  db = data;
  if (db.ultimo_aggiornamento_fip) {
    $('#sync').textContent = 'Risultati FIP aggiornati: ' + new Date(db.ultimo_aggiornamento_fip).toLocaleString('it-IT');
    $('#status').textContent = 'Risultati FIP sincronizzati.';
  }
  $('#matchGroup').innerHTML = '<option value="all">Tutti i gironi</option>' + Object.keys(db.squadre).map(g => `<option value="${g}">Girone ${g}</option>`).join('');
  $('#matchGroup').onchange = render;
  $('#simMatch').innerHTML = db.partite.filter(p => !p.risultato).map(p => `<option value="${p.id}">${p.data} · ${p.casa} / ${p.trasferta}</option>`).join('');
  $('#simulate').onclick = () => {
    let h = Number($('#scoreHome').value), a = Number($('#scoreAway').value);
    if ($('#scoreHome').value === '' || $('#scoreAway').value === '' || h === a || h < 0 || a < 0) { alert('Inserisci due punteggi validi e diversi.'); return; }
    if (!$('#simMatch').value) { alert('Nessuna partita disponibile per la simulazione'); return; }
    sim[$('#simMatch').value] = [h,a]; render();
  };
  $('#reset').onclick = () => { sim = {}; render(); };
  render();
}).catch(e => { $('#nextTitle').textContent = 'Dati non caricati'; console.error(e); });
