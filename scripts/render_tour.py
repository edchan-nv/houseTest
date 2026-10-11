"""OVRTX/OVStage batch rendering. No pxr imports in renderer process."""
import os,contextlib,json,time,hashlib,argparse
from pathlib import Path
os.environ['OVRTX_SKIP_USD_CHECK']='1'
import numpy as np
import ovstage,ovrtx
from PIL import Image
R=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--views',default='');a=p.parse_args();name='smoke' if a.smoke else 'tour';out=R/('evidence/smoke' if a.smoke else 'public/renders');out.mkdir(parents=True,exist_ok=True)
jobs=json.loads((R/'scene'/f'{name}-jobs.json').read_text());original=hashlib.sha256((R/'scene/house.usdc').read_bytes()).hexdigest()
# This pinned build registers its bundled USD schemas at renderer construction.
renderer=ovrtx.Renderer(config=ovrtx.RendererConfig(sync_mode=True,active_cuda_gpus='0'));stage=None;report={'engine':'OVRTX','version':str(renderer.version),'mode':'PathTracing','samples':48 if a.smoke else 96,'frames':[]};started=time.monotonic()
try:
 stage=ovstage.Stage('millbrae.tour');ovstage.population.open_usd(stage,str(R/'scene'/f'{name}.usda'),ordinal=1,time_code=0);stage.advance_write_floor(1,ovstage.Scope.ALL).wait();renderer.attach_ovstage(stage)
 for i,j in enumerate(jobs):
  if a.views and j['id'] not in a.views.split(','):continue
  dest=out/j['file']
  if a.resume and dest.exists():continue
  begin=time.monotonic();ordinal=i+2
  ovstage.population.update_from_usd_time(stage,ordinal=ordinal,time_code=float(i));stage.advance_write_floor(ordinal,ovstage.Scope.ALL).wait();renderer.update_from_stage(ordinal);renderer.reset(time=0)
  outputs=renderer.step(render_products={'/Tour/Product'},delta_time=0,ordinal=ordinal)
  with (outputs if hasattr(outputs,'__enter__') else contextlib.nullcontext(outputs)) as ctx:
   frames=ctx['/Tour/Product'].frames
   frame=next(iter(frames));key=next(k for k in frame.render_vars.keys() if k=='LdrColor' or k.endswith('/LdrColor'));rv=frame.render_vars[key];mapped=rv.map(device=ovrtx.Device.CPU)
   try:pixels=np.from_dlpack(mapped).copy()
   finally:mapped.unmap()
  del mapped,rv,frame,frames,ctx,outputs
  Image.fromarray(pixels[:,:,:3]).save(dest,quality=88,method=5)
  item={'file':j['file'],'seconds':round(time.monotonic()-begin,3),'std':float(pixels[:,:,:3].std()),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()};report['frames'].append(item);print(json.dumps(item),flush=True)
 report['asset_unchanged']=original==hashlib.sha256((R/'scene/house.usdc').read_bytes()).hexdigest();report['seconds']=time.monotonic()-started
finally:
 if stage is not None:renderer.detach_ovstage();stage.destroy()
 renderer.destroy();(R/'evidence'/(f'{name}-render-report'+('-selected' if a.views else '')+'.json')).write_text(json.dumps(report,indent=2))
