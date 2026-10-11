from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.request,json
from PIL import Image,ImageOps,ImageDraw
root=Path(__file__).resolve().parents[1];out=root/'sources';out.mkdir(exist_ok=True)
def fetch(i):
 url=f'https://ssl.cdn-redfin.com/photo/8/bigphoto/426/ML82063426_{i}_1.jpg'
 p=out/f'{i:03}.jpg'
 try:
  if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=30).read())
  with Image.open(p) as im: im.verify()
  return {'index':i,'url':url,'file':p.name}
 except Exception as e:return {'index':i,'error':str(e)}
with ThreadPoolExecutor(max_workers=8) as pool: rows=list(pool.map(fetch,range(121)))
(out/'references.json').write_text(json.dumps(rows,indent=2))
for start in range(0,121,30):
 subset=rows[start:start+30];sheet=Image.new('RGB',(1500,((len(subset)+4)//5)*220),'#202020');draw=ImageDraw.Draw(sheet)
 for j,r in enumerate(subset):
  if 'file' not in r:continue
  im=Image.open(out/r['file']);im.thumbnail((294,192));x=(j%5)*300;y=(j//5)*220
  sheet.paste(im,(x+(300-im.width)//2,y));draw.text((x+8,y+196),str(r['index']),fill='white')
 sheet.save(out/f'contact-{start:03}.jpg')
print('Fetched',sum('file' in r for r in rows),'references')
print([r for r in rows if 'error' in r])
