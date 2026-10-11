"""Focused pixel checks: nonblank renders and visible furnishing removal."""
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json
R=Path(__file__).resolve().parents[1];views=json.loads((R/'public/views.json').read_text());rows=[];sheet=Image.new('RGB',(1200,220*((len(views)+2)//3)),(240,239,235));draw=ImageDraw.Draw(sheet)
for i,v in enumerate(views):
 a=np.array(Image.open(R/'public/renders'/f"{v['id']}-15.webp").convert('RGB'));b=np.array(Image.open(R/'public/renders'/f"{v['id']}-00.webp").convert('RGB'));d=np.abs(a.astype(float)-b.astype(float));fraction=float((d.max(axis=2)>20).mean())
 assert a.std()>5 and b.std()>5,v['id']
 assert fraction>.0005,(v['id'],fraction)
 rows.append({'view':v['id'],'furnished_empty_changed_fraction':round(fraction,4),'width':a.shape[1],'height':a.shape[0]})
 im=Image.fromarray(a);im.thumbnail((396,193));x=i%3*400;y=i//3*220;sheet.paste(im,(x,y));draw.text((x+8,y+199),v['name'],fill=(40,45,41))
sheet.save(R/'evidence/all-views.jpg',quality=92);(R/'evidence/pixel-validation.json').write_text(json.dumps({'passed':True,'views':rows},indent=2));print(json.dumps(rows))
