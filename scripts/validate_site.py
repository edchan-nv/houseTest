#!/usr/bin/env python3
"""Dependency-free packaging gate for static hosting and GitLab Pages."""
from pathlib import Path
import json,zipfile
r=Path(__file__).resolve().parents[1];p=r/'public';views=json.loads((p/'views.json').read_text());expected=[]
for v in views:
 for mask in range(16):expected.append(f"{v['id']}-{mask:02}.webp")
for name in ['exterior','mainplan','lowerplan']:
 for angle in range(1,24):
  for mask in [0,15]:expected.append(f'{name}-{mask:02}-{angle:02}.webp')
missing=[n for n in expected if not (p/'renders'/n).is_file()]
assert not missing,f'Missing renders: {missing[:8]}'
for n in expected:
 data=(p/'renders'/n).read_bytes();assert len(data)>100 and data[:4]==b'RIFF' and data[8:12]==b'WEBP',n
for n in ['index.html','style.css','app.js','views.json','downloads/house-usd.zip']:assert (p/n).stat().st_size>0,n
with zipfile.ZipFile(p/'downloads/house-usd.zip') as z:assert z.testzip() is None
print(f'PASS: {len(views)} viewpoints, {len(expected)} valid WebP files, source download, static entrypoints.')
