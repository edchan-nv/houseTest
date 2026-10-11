from pathlib import Path
from PIL import Image,ImageDraw
import json,hashlib
R=Path(__file__).resolve().parents[1]
pairs=[(15,'living'),(22,'kitchen'),(28,'primary'),(63,'recreation'),(90,'terrace'),(6,'exterior')]
sheet=Image.new('RGB',(1280,460*len(pairs)),(242,240,235));draw=ImageDraw.Draw(sheet)
for i,(ref,name) in enumerate(pairs):
 for col,path in enumerate([R/'sources'/f'{ref:03}.jpg',R/'public/renders'/f'{name}-15.webp']):
  im=Image.open(path).convert('RGB');im.thumbnail((636,409));x=col*640;y=i*460+35;sheet.paste(im,(x+(640-im.width)//2,y));draw.text((x+12,i*460+12),f'Listing photo {ref}' if col==0 else f'Approximate reconstruction: {name}',fill=(30,35,30))
sheet.save(R/'evidence/reference-comparison.jpg',quality=91)
# Record every delivered render and model file, excluding original listing photos.
files={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for d in ['public/renders','public/downloads'] for p in sorted((R/d).glob('*')) if p.is_file()}
(R/'evidence/release-checksums.json').write_text(json.dumps(files,indent=2))
for name,count in [('tour-render-report.json',362),('tour-render-report-selected.json',220)]:
 report=json.loads((R/'evidence'/name).read_text());assert report['asset_unchanged'];assert len(report['frames'])==count,(name,len(report['frames']))
print('PASS: complete renderer reports, immutable source during each batch, release hashes, local reference comparison.')
