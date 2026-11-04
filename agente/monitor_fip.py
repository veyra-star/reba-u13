#!/usr/bin/env python3
"""Independent FIP Piemonte U13F results monitor. Does not read REBA site data."""
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "stato.json"
RESULTS = ROOT / "risultati.json"
BASE = "https://fip.it/risultati/"
PARAMS = {"group":"campionati-regionali","regione_codice":"PI","comitato_codice":"RPI","sesso":"F","codice_campionato":"U13/F","codice_fase":"1"}
GROUPS = dict(zip("ABCDE",range(86095,86100)))
HEADERS = {"User-Agent":"Mozilla/5.0 (compatible; IndependentU13FMonitor/1.0)"}
# Independent list of clubs in the FIP group calendars; no REBA files are read.
TEAMS = {
"A":["OLIMPO BASKET ALBA","BANCA B.T.M.","PROMO CUNEO BASKET","GATORS","NEW BASKET ABET"],
"B":["BEA CHIERI SSDRL","ERIDANIA BASKET","POLISPORTIVA PASTA","ALFIERI BASKET","AREA PRO 2020"],
"C":["USAC RIVAROLO BK 2009","BASKET NOLE","BASKET VENARIA","LETTERA 22 A.S.D.","LAPOLISMILE"],
"D":["POLISPORTIVA REBA","POLISPORTIVA REBA BIANCO","SAN MAURO BASKET","AVIGLIANA BASKET","VIRTUS BASKET SALUGGIA"],
"E":["BASKET FEMM.LE ALESSANDRIA","NOVARA BASKET","BCC DERTHONA BASKET","A.S.D. OLYMPIA BASKET 2000","POLISPORTIVA SAN GIACOMO"]
}
def norm(s):
    return re.sub(r"[^A-Z0-9]","",s.upper())
def identify(s, group):
    n=norm(s)
    candidates=[]
    for team in TEAMS[group]:
        t=norm(team)
        if t in n or n in t and len(n)>8:
            candidates.append(team)
    return max(candidates,key=len) if candidates else None

def extract(html, group):
    soup=BeautifulSoup(html,"html.parser")
    text=soup.get_text(" ",strip=True)
    if len(text)<500:
        raise ValueError("FIP page too short")
    # Find scores only inside match-sized chunks preceding a FIP game identifier.
    # Deliberately conservative: ambiguous rows are omitted rather than guessed.
    datepat=r"(\\d{1,2}\\s+[A-Za-zÀ-ÿ]+\\s+20\\d{2}\\s+\\d{1,2}:\\d{2})"
    pattern=re.compile(r"(.{0,210}?)\\s+(\\d{1,3})\\s+(.{3,120}?)\\s+(\\d{1,3})\\s+"+datepat+r"\\s+(\\d{4,7})(?!\\d)",re.I)
    out={}
    for m in pattern.finditer(text):
        home=identify(m.group(1),group)
        away=identify(m.group(3),group)
        a,b=int(m.group(2)),int(m.group(4))
        if not home or not away or home==away or a==b:
            continue
        gameid=m.group(6)
        key=f"{group}:{gameid}"
        value={"girone":group,"id":gameid,"casa":home,"trasferta":away,"punteggio":[a,b],"data_fip":m.group(5)}
        if key in out and out[key]!=value:
            raise ValueError(f"Conflicting scores for {key}")
        out[key]=value
    if not any(norm(t) in norm(text) for t in TEAMS[group]):
        raise ValueError(f"No recognized FIP teams in group {group}")
    return out

def main():
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    old=json.loads(RESULTS.read_text()) if RESULTS.exists() else {"partite":{}}
    state=json.loads(STATE.read_text()) if STATE.exists() else {}
    collected={}
    errors=[]
    for group,code in GROUPS.items():
        url=BASE+"?"+urlencode({**PARAMS,"codice_girone":code})
        try:
            response=requests.get(url,headers=HEADERS,timeout=30)
            response.raise_for_status()
            found=extract(response.text,group)
            collected.update(found)
            print(f"Group {group}: HTTP {response.status_code}, {len(found)} scores")
        except Exception as e:
            errors.append(f"{group}: {type(e).__name__}: {e}")
    state["ultimo_tentativo_utc"]=now
    state["errori"]=errors
    if errors:
        state["esito"]="errore"
        STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n")
        raise SystemExit("FIP verification incomplete: "+"; ".join(errors))
    merged=dict(old.get("partite",{}))
    changed={}
    for k,v in collected.items():
        if merged.get(k)!=v:
            changed[k]=v
            merged[k]=v
    RESULTS.write_text(json.dumps({"fonte":"FIP Piemonte - acquisizione indipendente","partite":merged},ensure_ascii=False,indent=2)+"\n")
    state.update({"esito":"ok","ultimo_controllo_riuscito_utc":now,"nuovi_o_modificati":len(changed),"totale_risultati":len(merged)})
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n")
    print(f"Independent FIP check OK: {len(changed)} changed, {len(merged)} total")

if __name__=="__main__":
    main()
