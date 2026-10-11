"""Author a non-destructive OVRTX composition in a separate OpenUSD process."""
from pxr import Usd,UsdGeom,UsdLux,UsdRender,Gf,Sdf
from pathlib import Path
import json,math,argparse
R=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--size',type=int,default=1280);args=p.parse_args()
source=Usd.Stage.Open(str(R/'scene/house.usdc'))
views=json.loads((R/'scene/views.json').read_text());cats=['seating','tables','beds','decor'];jobs=[]
for v in views:
 masks=[15,0] if args.smoke else list(range(16))
 for mask in masks:jobs.append({**v,'mask':mask,'file':f"{v['id']}-{mask:02}.webp"})
if not args.smoke:
 for v in [v for v in views if v['id'] in ['exterior','mainplan','lowerplan']]:
  for i in range(1,24):
   a=math.tau*i/24;dx=v['eye'][0]-v['target'][0];dy=v['eye'][1]-v['target'][1]
   eye=[v['target'][0]+dx*math.cos(a)-dy*math.sin(a),v['target'][1]+dx*math.sin(a)+dy*math.cos(a),v['eye'][2]]
   for mask in [0,15]:jobs.append({**v,'eye':eye,'mask':mask,'orbit':i,'file':f"{v['id']}-{mask:02}-{i:02}.webp"})
if args.smoke:jobs=[j for j in jobs if j['id'] in ['living','kitchen','primary','mainplan','exterior']]
name='smoke' if args.smoke else 'tour';path=R/'scene'/f'{name}.usda'
if path.exists():path.unlink()
s=Usd.Stage.CreateNew(str(path));s.GetRootLayer().subLayerPaths=['house.usdc'];s.SetTimeCodesPerSecond(1);s.SetStartTimeCode(0);s.SetEndTimeCode(len(jobs)-1);UsdGeom.SetStageUpAxis(s,UsdGeom.Tokens.z);UsdGeom.SetStageMetersPerUnit(s,1)
cam=UsdGeom.Camera.Define(s,'/Tour/Camera');focal=cam.CreateFocalLengthAttr(20.5);cam.CreateHorizontalApertureAttr(36);cam.CreateVerticalApertureAttr(22.5);cam.CreateClippingRangeAttr(Gf.Vec2f(.035,300));xf=cam.AddTransformOp()
product=UsdRender.Product.Define(s,'/Tour/Product');product.CreateResolutionAttr(Gf.Vec2i(args.size,round(args.size/1.6)));product.CreateCameraRel().SetTargets(['/Tour/Camera']);product.CreateOrderedVarsRel().SetTargets(['/Tour/LdrColor'])
prim=product.GetPrim();prim.SetMetadata('apiSchemas',Sdf.TokenListOp.Create(prependedItems=['OmniRtxSettingsCommonAdvancedAPI_1','OmniRtxSettingsPtAdvancedAPI_1','OmniRtxSettingsRtAdvancedAPI_1']))
prim.CreateAttribute('omni:rtx:rendermode',Sdf.ValueTypeNames.Token).Set('PathTracing');prim.CreateAttribute('omni:rtx:pt:samplesPerPixel',Sdf.ValueTypeNames.UInt).Set(48 if args.smoke else 96)
UsdRender.Var.Define(s,'/Tour/LdrColor').CreateSourceNameAttr('LdrColor');UsdRender.Settings.Define(s,'/Tour/Settings').CreateProductsRel().SetTargets(['/Tour/Product'])
dome=UsdLux.DomeLight.Define(s,'/Tour/Sky');dome.CreateIntensityAttr(1800);dome.CreateColorAttr(Gf.Vec3f(.72,.83,1))
# Calibrated presentation lighting; independent of furniture state.
for prim in source.Traverse():
 if prim.IsA(UsdLux.DiskLight):
  UsdLux.DiskLight(s.OverridePrim(prim.GetPath())).CreateIntensityAttr(18000)
 elif prim.IsA(UsdLux.DistantLight):
  UsdLux.DistantLight(s.OverridePrim(prim.GetPath())).CreateIntensityAttr(2500)
# Child mesh visibility follows these stable group parents. Only the wrapper is authored.
vis={};categories={};supported_decor=[]
for prim in source.Traverse():
 pathstr=str(prim.GetPath());bits=pathstr.split('/')
 if '/Staging/' in pathstr and len(bits)==7:
  cat=prim.GetName().split('_')[0]
  if cat in cats:categories[pathstr]=cats.index(cat)
 if '/Staging/' in pathstr and len(bits)==8 and (prim.GetName().startswith('TableLamp') or prim.GetName().startswith('DiningFlowers')):supported_decor.append(pathstr)
fixed=['/World/House/Architecture/'+x for x in ['Main','MainCeilings','Lower','LowerCeilings','Roof']]+['/World/House/Site','/World/House/Staging/Main_001','/World/House/Staging/Lower_001','/World/House/Staging/Outdoor']
for pathstr in fixed+list(categories)+supported_decor:vis[pathstr]=UsdGeom.Imageable(s.OverridePrim(pathstr)).CreateVisibilityAttr()
for i,j in enumerate(jobs):
 focal.Set(37 if 'Plan' in j['level'] else 27 if j['level']=='Exterior' else 20.5,i)
 eye=Gf.Vec3d(*j['eye']);target=Gf.Vec3d(*j['target']);xf.Set(Gf.Matrix4d().SetLookAt(eye,target,Gf.Vec3d(0,0,1)).GetInverse(),i)
 hidden=set()
 if j['level'] in ['MainPlan','LowerPlan']:
  hidden|={'/World/House/Architecture/Roof','/World/House/Architecture/MainCeilings','/World/House/Architecture/LowerCeilings','/World/House/Site','/World/House/Staging/Outdoor'}
  if j['level']=='LowerPlan':hidden|={'/World/House/Architecture/Main','/World/House/Staging/Main_001'}
  else:hidden|={'/World/House/Architecture/Lower','/World/House/Staging/Lower_001'}
 for pathstr,attr in vis.items():
  invisible=pathstr in hidden or (pathstr in categories and not (j['mask']&(1<<categories[pathstr]))) or (pathstr in supported_decor and (not j['mask']&2 or not j['mask']&8))
  attr.Set(UsdGeom.Tokens.invisible if invisible else UsdGeom.Tokens.inherited,i)
s.GetRootLayer().Save();(R/'scene'/f'{name}-jobs.json').write_text(json.dumps(jobs,indent=2));print('Prepared',len(jobs),'renders;',len(categories),'category parents')
