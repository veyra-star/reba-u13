import re,json,pathlib
text=pathlib.Path('/mnt/data/u13.txt').read_text()
teams={'A':['OLIMPO BASKET ALBA','BANCA B.T.M.','PROMO CUNEO BASKET','GATORS','NEW BASKET ABET'],'B':['BEA CHIERI SSDRL','ERIDANIA BASKET','POLISPORTIVA PASTA','ALFIERI BASKET','AREA PRO 2020'],'C':['USAC RIVAROLO BK 2009','BASKET NOLE','BASKET VENARIA','LETTERA 22 A.S.D.','LAPOLISMILE'],'D':['POLISPORTIVA REBA','POLISPORTIVA REBA BIANCO','SAN MAURO BASKET','AVIGLIANA BASKET','VIRTUS BASKET SALUGGIA'],'E':['BASKET FEMM.LE ALESSANDRIA','NOVARA BASKET','BCC DERTHONA BASKET','A.S.D. OLYMPIA BASKET 2000','POLISPORTIVA SAN GIACOMO']}
# calendar fixture rows; separate column regions inferred by padding and known team labels
fixtures=[]; group=None; roundname=''
lines=text.splitlines()
for i,line in enumerate(lines):
 m=re.search(r'Girone : Girone ([A-E])',line)
 if m:group=m.group(1)
 m=re.search(r'(\d) Giornata di (andata|ritorno)',line)
 if m:roundname=m.group(1)+' '+m.group(2)
 m=re.match(r'^\s*(\d{4})\s+(.+?)\s+(Lun|Mar|Mer|Gio|Ven|Sab|Dom)\s+(\d\d/\d\d/20\d\d)\s+(\d\d:\d\d)',line)
 if not m or not group:continue
 num,raw,day,date,time=m.groups()
 # continuation before gym can complete names (e.g. VIRTUS BASKET / SALUGGIA)
 continuation=''
 for l in lines[i+1:i+3]:
  if re.search(r'Palestra|PALESTRA|PALAZZETTO|Palazzetto|Pala |PALAZZO|Istituto|Scuola|Centro |Impianto',l):break
  if l.strip() and not re.match(r'\s*(\d{4}|\d Giornata)',l):continuation+=' '+l.strip()
 normalized=re.sub(r'\s+',' ',raw+' '+continuation).upper()
 # best match via original fixed columns plus suffix completion; enumerate ordered pairs
 candidates=[]
 for a in teams[group]:
  for b in teams[group]:
   if a==b:continue
   # remove tokens by order with optional trailing continuation
   def words(s):return s.split()
   toks=words(normalized); aa=words(a);bb=words(b)
   # compare subsequence of tokens allowing wrapped suffix at end
   def subseq(needle,hay):
    it=iter(hay);return all(any(x==z for z in it) for x in needle)
   if subseq(aa,toks) and subseq(bb,toks):candidates.append((a,b))
 # choose match by matching first team's prefix in raw
 candidates.sort(key=lambda ab:(not raw.upper().lstrip().startswith(' '.join(ab[0].split()[:2])),-len(ab[0])-len(ab[1])))
 if candidates:
  a,b=candidates[0]
  fixtures.append(dict(id=num,girone=group,casa=a,trasferta=b,data=date,ora=time,giornata=roundname,risultato=None))
pathlib.Path('/mnt/data/reba-u13/data/campionato.json').write_text(json.dumps({'stagione':'2026/27','fonte':'FIP Piemonte, calendario definitivo 23/10/2026','squadre':teams,'partite':fixtures},ensure_ascii=False,indent=2))
from collections import Counter
print(Counter(f['girone'] for f in fixtures));print([f for f in fixtures if f['girone']=='D'][:5])
