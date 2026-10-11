"""Publish relocatable editable model with furnishing variants and source provenance."""
from pathlib import Path
import json,zipfile,hashlib
from pxr import Usd,UsdGeom,UsdLux,Gf,Sdf
R=Path(__file__).resolve().parents[1];path=R/'scene/house.usda'
if path.exists():path.unlink()
s=Usd.Stage.CreateNew(str(path));s.GetRootLayer().subLayerPaths=['house.usdc'];s.SetDefaultPrim(s.GetPrimAtPath('/World'));UsdGeom.SetStageUpAxis(s,'Z');UsdGeom.SetStageMetersPerUnit(s,1)
s.GetRootLayer().documentation='1172 Millbrae Ave. Photo/floor-plan-guided approximation, not a measured survey. See provenance.json.'
variant=s.GetPrimAtPath('/World/House').GetVariantSets().AddVariantSet('furnishing')
for name,value in [('furnished','inherited'),('empty','invisible')]:
 variant.AddVariant(name);variant.SetVariantSelection(name)
 with variant.GetVariantEditContext():UsdGeom.Imageable(s.GetPrimAtPath('/World/House/Staging')).CreateVisibilityAttr(value)
variant.SetVariantSelection('furnished')
for p in s.Traverse():
 if p.IsA(UsdLux.DiskLight):UsdLux.DiskLight(p).CreateIntensityAttr(18000)
 elif p.IsA(UsdLux.DistantLight):UsdLux.DistantLight(p).CreateIntensityAttr(2500)
d=UsdLux.DomeLight.Define(s,'/World/PresentationSky');d.CreateIntensityAttr(1800);d.CreateColorAttr(Gf.Vec3f(.72,.83,1))
views=json.loads((R/'scene/views.json').read_text())
for v in views:
 c=UsdGeom.Camera.Define(s,'/World/ReviewCameras/'+v['id']);c.CreateFocalLengthAttr(37 if 'Plan' in v['level'] else 27 if v['level']=='Exterior' else 20.5);c.CreateHorizontalApertureAttr(36);c.CreateVerticalApertureAttr(22.5);c.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*v['eye']),Gf.Vec3d(*v['target']),Gf.Vec3d(0,0,1)).GetInverse())
s.GetRootLayer().Save()
items=[]
for p in s.Traverse():
 parts=str(p.GetPath()).split('/')
 if '/Staging/' in str(p.GetPath()) and len(parts)==8 and p.GetTypeName()=='Xform':items.append({'path':str(p.GetPath()),'name':p.GetName(),'room':parts[5],'category':parts[6].split('_')[0],'independently_removable':True})
(R/'scene/furniture-prims.json').write_text(json.dumps(items,indent=2))
provenance={'address':'1172 Millbrae Ave, Millbrae, CA 94030','listing':'https://www.redfin.com/CA/Millbrae/1172-Millbrae-Ave-94030/home/665972','source_floorplan':'https://ssl.cdn-redfin.com/photo/8/bigphoto/426/ML82063426_120_1.jpg','units':'metres','up_axis':'Z','plan_scale_metres_per_pixel':.037,'main_floor_elevation_estimated':3.05,'interior_wall_height_estimated':2.85,'method':'Manual interpretation of listing floorplan and photographs, procedural editable modeling. Not photogrammetry.','observed':['room adjacency and approximate proportions from floor plan','window/door appearance from listing photos','cream walls and oak floors','white/walnut kitchen with dark counters','vaulted ceiling character','two occupied levels, decks and detached garage'],'inferred':['wall thickness and heights','exact camera poses and scale calibration','roof junctions and construction','terrain, detached garage placement and vegetation','furniture shapes and unobserved surfaces'],'limitations':['Stylized furniture and materials, not a photoreal replica.','Dimensions have not been measured on site.','No engineering, structural, collision, or navigation certification.','Bathroom and service-area detail is schematic.'],'furniture_items':len(items),'reference_photos_not_redistributed':True}
(R/'scene/provenance.json').write_text(json.dumps(provenance,indent=2))
readme='''1172 MILLBRAE AVENUE — EDITABLE ARCHITECTURAL STUDY

Open house.usda with its adjacent house.usdc. Units: metres. Up axis: Z.
Select /World/House > furnishing variant: furnished or empty.
Individual items live below /World/House/Staging/<level>/<room>/<category>/<item>.
Hide, delete, or transform an item parent to remove or reposition it.
Architecture, fixed cabinetry, fixtures, and stairs remain separate.

house.blend is the native authoring source. Review cameras are in house.usda.
Dollhouse views require hiding roofs/ceilings and the opposite level; these
presentation overrides are in the render composition, not the base model.
Furniture-prims.json lists actual editable paths. Provenance.json records
sources and inferred dimensions. This is an approximate architectural study.
'''
(R/'scene/MODEL-README.txt').write_text(readme)
out=R/'public/downloads';out.mkdir(exist_ok=True)
with zipfile.ZipFile(out/'house-usd.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in ['house.usda','house.usdc','house.blend','views.json','furniture-prims.json','provenance.json','MODEL-README.txt']:z.write(R/'scene'/name,name)
 for f in (R/'scene/textures').rglob('*'):
  if f.is_file():z.write(f,f.relative_to(R/'scene'))
# Structural and composition checks, including actual inherited furniture visibility.
check=Usd.Stage.Open(str(path));v=check.GetPrimAtPath('/World/House').GetVariantSets().GetVariantSet('furnishing');v.SetVariantSelection('empty')
assert all(UsdGeom.Imageable(check.GetPrimAtPath(i['path'])).ComputeVisibility()=='invisible' for i in items)
assert UsdGeom.Imageable(check.GetPrimAtPath('/World/House/Architecture')).ComputeVisibility()=='inherited'
v.SetVariantSelection('furnished');assert all(UsdGeom.Imageable(check.GetPrimAtPath(i['path'])).ComputeVisibility()=='inherited' for i in items)
assert len(items)==74
report={'stage_opens':True,'metres_per_unit':UsdGeom.GetStageMetersPerUnit(check),'up_axis':UsdGeom.GetStageUpAxis(check),'furniture_items':len(items),'furnishing_variants_verified':True,'architecture_remains_visible':True,'zip_sha256':hashlib.sha256((out/'house-usd.zip').read_bytes()).hexdigest()}
(R/'evidence/model-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
