/* Analytics-only extensions: never write to FIP data or original REBA site. */
(function(){
'use strict';
const byId=id=>document.getElementById(id);
const safe=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
const key=s=>s.g+'|'+s.name;
const elo=s=>rating[key(s)];
const shown=s=>displayName(s.name);
const avg=(s,k)=>s.played?s[k]/s.played:null;
const number=n=>n==null?'—':n.toLocaleString('it-IT',{maximumFractionDigits:1});
const allTeams=()=>Object.values(stats).filter(s=>byId('group').value==='ALL'||s.g===byId('group').value);
function fill(select,items,old){select.innerHTML=items.map(s=>'<option value="'+safe(s.g+'|'+s.name)+'">'+safe(shown(s))+' · '+s.g+'</option>').join('');if(items.some(s=>key(s)===old))select.value=old}
function comparison(){
const items=allTeams().sort((a,b)=>shown(a).localeCompare(shown(b),'it')),left=byId('compareA'),right=byId('compareB');
const oldA=left.value,oldB=right.value;fill(left,items,oldA);fill(right,items,oldB);
if(!oldA&&items.length)left.value=key(items.find(s=>s.name==='POLISPORTIVA REBA')||items[0]);
if(!oldB&&items.length>1)right.value=key(items.find(s=>key(s)!==left.value)||items[1]);
const a=stats[left.value],b=stats[right.value],out=byId('comparison');
if(!a||!b){out.innerHTML='<p class="empty">Seleziona due squadre.</p>';return}
const fields=[['Elo REBA',elo(a),elo(b)],['Gare',a.played,b.played],['Vittorie',a.w,b.w],['Vittorie %',a.played?100*a.w/a.played:null,b.played?100*b.w/b.played:null],['Punti segnati / gara',avg(a,'pf'),avg(b,'pf')],['Punti subiti / gara',avg(a,'pa'),avg(b,'pa')],['Distacco medio',a.played?(a.pf-a.pa)/a.played:null,b.played?(b.pf-b.pa)/b.played:null]];
let head='<table><thead><tr><th>Indicatore</th><th class="num">'+safe(shown(a))+'</th><th class="num">'+safe(shown(b))+'</th></tr></thead><tbody>';
out.innerHTML=head+fields.map(([n,x,y])=>'<tr><td>'+n+'</td><td class="num">'+number(x)+'</td><td class="num">'+number(y)+'</td></tr>').join('')+'</tbody></table>';
const meetings=source.partite.filter(p=>p.girone===a.g&&a.g===b.g&&((p.casa===a.name&&p.trasferta===b.name)||(p.casa===b.name&&p.trasferta===a.name))&&Array.isArray(p.risultato));
out.innerHTML+='<p class="note" style="margin-top:12px">'+(a.g!==b.g?'Gironi diversi: nessun confronto Elo diretto affidabile.':meetings.length?'Scontri diretti: '+meetings.map(p=>safe(p.data)+' · '+safe(displayName(p.casa))+' '+p.risultato[0]+'–'+p.risultato[1]+' '+safe(displayName(p.trasferta))).join(' | '):'Nessuno scontro diretto ancora disputato.')+'</p>';
}
function schedule(){
const teams=allTeams().sort((a,b)=>shown(a).localeCompare(shown(b),'it')),sel=byId('difficultyTeam'),old=sel.value;fill(sel,teams,old);if(!old&&teams.length)sel.value=key(teams.find(s=>s.name==='POLISPORTIVA REBA')||teams[0]);
const t=stats[sel.value],out=byId('difficulty');if(!t){out.innerHTML='<p class="empty">Nessuna squadra disponibile.</p>';return}
const games=source.partite.filter(p=>p.girone===t.g&&(p.casa===t.name||p.trasferta===t.name)).sort(gameSort);
const records=games.map(p=>{const opp=p.casa===t.name?p.trasferta:p.casa,other=stats[t.g+'|'+opp];return {p,other,opponent:opp,score:Array.isArray(p.risultato)?p.risultato:null,elo:other?elo(other):null}});
const valid=arr=>arr.filter(x=>x.elo!=null),mean=arr=>{let v=valid(arr);return v.length?v.reduce((n,x)=>n+x.elo,0)/v.length:null};
const done=records.filter(x=>x.score),future=records.filter(x=>!x.score);
out.innerHTML='<div class="metrics" style="grid-template-columns:repeat(2,1fr);margin:12px 0"><div class="metric"><strong>'+number(mean(done))+'</strong><span>Elo medio avversari affrontati</span></div><div class="metric"><strong>'+number(mean(future))+'</strong><span>Elo medio avversari futuri</span></div></div><div class="scroll"><table><thead><tr><th>Data</th><th>Avversario</th><th>Stato</th><th class="num">Elo avversario</th></tr></thead><tbody>'+records.sort((a,b)=>gameSort(a.p,b.p)).map(x=>'<tr><td>'+safe(x.p.data)+'</td><td>'+safe(displayName(x.opponent))+'</td><td>'+(x.score?'Giocata':'Da giocare')+'</td><td class="num accent">'+number(x.elo)+'</td></tr>').join('')+'</tbody></table></div><p class="note">Partite in ordine cronologico. Difficoltà stimata usando l’Elo attuale REBA degli avversari. Non è una misura storica del loro Elo al momento della partita. Le medie escludono i rating non disponibili.</p>';
}
const TEAM_MARKERS={
'OLIMPO BASKET ALBA':['ALB','#d69a44'],'BANCA B.T.M.':['CAR','#8cb7e5'],'PROMO CUNEO BASKET':['CUN','#d982a9'],'GATORS':['SAV','#79b77d'],'NEW BASKET ABET':['BRA','#d2a06a'],
'BEA CHIERI SSDRL':['CHI','#f4a15c'],'ERIDANIA BASKET':['ERI','#d88775'],'POLISPORTIVA PASTA':['RPA','#86a4d8'],'ALFIERI BASKET':['ALF','#b9a0d8'],'AREA PRO 2020':['RAP','#d4c16b'],
'USAC RIVAROLO BK 2009':['RIV','#a8c16c'],'BASKET NOLE':['NOL','#85c6b2'],'BASKET VENARIA':['VEN','#c1a7e0'],'LETTERA 22 A.S.D.':['IVR','#d7aa75'],'LAPOLISMILE':['LAP','#8ab4d6'],
'POLISPORTIVA REBA':['REB','#b7ff4a'],'POLISPORTIVA REBA BIANCO':['RBI','#f2f2e8'],'SAN MAURO BASKET':['SMU','#f2ae85'],'AVIGLIANA BASKET':['AVI','#7fc98b'],'VIRTUS BASKET SALUGGIA':['SAL','#a8a6dc'],
'BASKET FEMM.LE ALESSANDRIA':['ALE','#d2a16d'],'NOVARA BASKET':['NOV','#83bad2'],'BCC DERTHONA BASKET':['DER','#db879e'],'A.S.D. OLYMPIA BASKET 2000':['CAS','#b9ad76'],'POLISPORTIVA SAN GIACOMO':['NSG','#8cbd9a']
};
function scatter(){
const teams=allTeams().filter(s=>s.played).sort((a,b)=>shown(a).localeCompare(shown(b),'it')),out=byId('scatter');if(!teams.length){out.innerHTML='<p class="empty">Non ci sono risultati per questo filtro.</p>';return}
const w=760,h=430,pad={l:64,r:25,t:24,b:58},xmax=Math.max(20,...teams.map(s=>s.pa/s.played))*1.12,ymax=Math.max(20,...teams.map(s=>s.pf/s.played))*1.12;
const x=v=>pad.l+(v/xmax)*(w-pad.l-pad.r),y=v=>h-pad.b-(v/ymax)*(h-pad.t-pad.b);
let svg='<svg viewBox="0 0 '+w+' '+h+'" role="img" aria-label="Mappa squadre numerata: punti subiti medi sull’asse orizzontale e punti segnati medi sull’asse verticale" style="width:100%;height:auto;display:block">';
for(let i=0;i<=4;i++){let xv=xmax*i/4,yv=ymax*i/4;svg+='<line x1="'+x(xv)+'" y1="'+pad.t+'" x2="'+x(xv)+'" y2="'+(h-pad.b)+'" stroke="#2a3b30"/><line x1="'+pad.l+'" y1="'+y(yv)+'" x2="'+(w-pad.r)+'" y2="'+y(yv)+'" stroke="#2a3b30"/><text x="'+x(xv)+'" y="'+(h-pad.b+22)+'" text-anchor="middle" fill="#a6b7aa" font-size="12">'+Math.round(xv)+'</text><text x="'+(pad.l-12)+'" y="'+(y(yv)+4)+'" text-anchor="end" fill="#a6b7aa" font-size="12">'+Math.round(yv)+'</text>'}
svg+='<text x="'+(w/2)+'" y="'+(h-9)+'" text-anchor="middle" fill="#a6b7aa" font-size="13">Punti subiti / gara →</text><text transform="translate(17 '+h/2+') rotate(-90)" text-anchor="middle" fill="#a6b7aa" font-size="13">Punti segnati / gara →</text>';
teams.forEach((s,i)=>{const cx=x(s.pa/s.played),cy=y(s.pf/s.played),focus=s.name==='POLISPORTIVA REBA',label=shown(s),marker=TEAM_MARKERS[s.name]||[shown(s).slice(0,3).toUpperCase(),'#7fa9c9'],color=marker[1],textX=cx+9,textY=cy-5;svg+='<g tabindex="0" aria-label="'+safe(label)+': '+number(avg(s,'pf'))+' punti segnati e '+number(avg(s,'pa'))+' subiti per gara"><circle cx="'+cx+'" cy="'+cy+'" r="5" fill="'+color+'" stroke="#0a0e0c" stroke-width="1"/><text x="'+textX+'" y="'+textY+'" text-anchor="start" fill="'+color+'" stroke="#0a0e0c" stroke-width="3" paint-order="stroke" font-weight="'+(focus?'800':'650')+'" font-size="12">'+safe(marker[0])+'</text><title>'+safe(label)+' · '+number(avg(s,'pf'))+' segnati / '+number(avg(s,'pa'))+' subiti</title></g>'});
svg+='</svg>';
const legend=teams.map((s,i)=>{const marker=TEAM_MARKERS[s.name]||[shown(s).slice(0,3).toUpperCase(),'#7fa9c9'];return '<div style="display:flex;align-items:center;gap:9px;padding:7px 8px;border-bottom:1px solid #2a3b30"><span style="background:'+marker[1]+';color:#0a0e0c;border-radius:8px;min-width:42px;height:25px;display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:11px;flex-shrink:0">'+safe(marker[0])+'</span><span style="flex:1;font-weight:'+(s.name==='POLISPORTIVA REBA'?'800':'500')+'">'+safe(shown(s))+'</span><span class="note" style="white-space:nowrap">'+number(avg(s,'pf'))+' PF · '+number(avg(s,'pa'))+' PS</span></div>'}).join('');
const wasOpen=out.querySelector('details.scatter-legend')?.open||false;out.innerHTML=svg+'<details class="scatter-legend" '+(wasOpen?'open':'')+' style="margin-top:12px"><summary style="cursor:pointer;color:#b7ff4a;font-weight:700;padding:8px 0">Mostra legenda squadre</summary><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:0 16px;margin-top:12px">'+legend+'</div></details>';
}
let busy=false;
window.renderExtensions=function(){if(!source||busy)return;busy=true;try{comparison();schedule();scatter()}finally{busy=false}};
for(const id of ['compareA','compareB','difficultyTeam'])byId(id).addEventListener('change',()=>{if(id==='difficultyTeam')schedule();else comparison()});
})();
