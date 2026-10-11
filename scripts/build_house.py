"""Photo/floor-plan guided model. Run with Blender --background --python.
All dimensions inferred from listing floor plan unless explicitly recorded.
"""
import bpy, math, random, json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];random.seed(1172)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for m in list(bpy.data.materials):bpy.data.materials.remove(m)
def mat(n,c,rough=.5,metal=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
cream=mat('Warm_plaster',(.68,.60,.44),.85);white=mat('Ivory_trim',(.89,.87,.81));ceil=mat('Ceiling_white',(.88,.88,.86),.9);yellow=mat('Golden_siding',(.62,.48,.24),.7);dark=mat('Charcoal',(.022,.025,.024),.35);steel=mat('Brushed_steel',(.43,.47,.49),.28,.75);brass=mat('Antique_brass',(.42,.27,.10),.3,.75);linen=mat('Cream_linen',(.83,.80,.71),.96);grey=mat('Grey_upholstery',(.27,.29,.27),.95);rust=mat('Terracotta',(.43,.16,.065),.93);sage=mat('Sage',(.24,.32,.23),.9);blue=mat('Deck_blue',(.045,.14,.29),.9);purple=mat('Lilac_wall',(.43,.33,.46),.85);taupe=mat('Suite_taupe',(.39,.35,.30),.85);tile=mat('Pale_stone',(.69,.69,.65),.45);roofmat=mat('Grey_shingle',(.15,.17,.18),.95);wood=mat('Walnut',(.27,.14,.064),.55);deckwood=mat('Deck_cedar',(.36,.16,.085),.7);leaf=mat('Foliage',(.065,.17,.06),.8);soil=mat('Mulch',(.09,.06,.037));grass=mat('Landscape_green',(.17,.22,.09));glass=mat('Window_glass',(.64,.79,.82),.12)
# Slightly reflective transparent glass, kept subtle in architectural previews.
p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Transmission Weight'].default_value=1;p.inputs['IOR'].default_value=1.45
woods=[mat('Oak_%02d'%i,(.40+i*.009,.235+i*.006,.115+i*.004),.58) for i in range(14)]
darkwoods=[mat('Smoked_oak_%02d'%i,(.15+i*.006,.12+i*.005,.095+i*.004),.65) for i in range(10)]
roots={}
def empty(n,parent=None):
 o=bpy.data.objects.new(n,None);bpy.context.collection.objects.link(o);o.parent=parent;return o
world=empty('House');arch=empty('Architecture',world);stage=empty('Staging',world);site=empty('Site',world)
for level in ['Main','Lower']:
 roots[level]=empty(level,arch)
 roots[level+'Ceilings']=empty(level+'Ceilings',arch)
 roots[level+'F']=empty(level,stage)
roots['Roof']=empty('Roof',arch); roots['Outdoor']=empty('Outdoor',stage)
items=[]
def group(room,category,name,level='Main'):
 k=(level,room,category)
 if k not in roots:
  if (level,room) not in roots: roots[(level,room)]=empty(room,roots[level+'F'] if level!='Outdoor' else roots['Outdoor'])
  roots[k]=empty(category,roots[(level,room)])
 o=empty(name,roots[k]);items.append({'name':name,'room':room,'category':category,'level':level});return o
P=roots['Main']
def mesh_obj(n,verts,faces,m,parent):
 mesh=bpy.data.meshes.new(n);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(n,mesh);bpy.context.collection.objects.link(o);o.parent=parent or P
 if m:mesh.materials.append(m)
 return o

def cube(n,loc,size,m,parent=None,bevel=0):
 sx,sy,sz=[v/2 for v in size]
 verts=[(-sx,-sy,-sz),(-sx,-sy,sz),(-sx,sy,-sz),(-sx,sy,sz),(sx,-sy,-sz),(sx,-sy,sz),(sx,sy,-sz),(sx,sy,sz)]
 faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
 o=mesh_obj(n,verts,faces,m,parent);o.location=loc
 if bevel:
  mod=o.modifiers.new('Soft_edges','BEVEL');mod.width=bevel;mod.segments=3
 return o

def cyl(n,loc,r,depth,m,parent=None):
 verts=[(r*math.cos(i*math.tau/24),r*math.sin(i*math.tau/24),z) for z in [-depth/2,depth/2] for i in range(24)]
 faces=[tuple(reversed(range(24))),tuple(range(24,48))]+[(i,(i+1)%24,(i+1)%24+24,i+24) for i in range(24)]
 o=mesh_obj(n,verts,faces,m,parent);o.location=loc
 for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
 return o

def ell(n,loc,size,m,parent=None):
 verts=[]
 for j in range(9):
  t=math.pi*j/8
  for i in range(16):
   a=math.tau*i/16;verts.append((size[0]*math.sin(t)*math.cos(a),size[1]*math.sin(t)*math.sin(a),size[2]*math.cos(t)))
 faces=[(j*16+i,j*16+(i+1)%16,(j+1)*16+(i+1)%16,(j+1)*16+i) for j in range(8) for i in range(16)]
 o=mesh_obj(n,verts,faces,m,parent);o.location=loc
 for f in o.data.polygons:f.use_smooth=True
 return o
def beam(n,a,b,w,m,parent=None):
 d=Vector(b)-Vector(a);o=cube(n,(Vector(a)+Vector(b))/2,(w,w,d.length),m,parent);o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return o

def wall(n,a,b,z,h=2.85,openings=(),material=None,parent=None):
 # axis-aligned with openings expressed as distances from a along wall.
 ax=abs(b[0]-a[0])>abs(b[1]-a[1]);L=math.dist(a,b);s=1 if b[0 if ax else 1]>a[0 if ax else 1] else -1
 def part(lo,hi,zz,hh,ma,name):
  if hi-lo<.001 or hh<.001:return
  c=[a[0],a[1],zz+hh/2];c[0 if ax else 1]+=s*(lo+hi)/2;sz=(hi-lo,.15,hh) if ax else (.15,hi-lo,hh);cube(n+name,c,sz,ma,parent)
 cur=0
 for lo,hi,sill,top in sorted(openings):
  part(cur,lo,z,h,material or cream,'Wall');part(lo,hi,z,sill,material or cream,'SillWall');part(lo,hi,z+top,h-top,material or cream,'Header');cur=hi
  # perimeter trim for both sides of every opening
  for off in [-.085,.085]:
   for t in [lo,hi]:
    c=[a[0],a[1],z+(sill+top)/2];c[0 if ax else 1]+=s*t;c[1 if ax else 0]+=off;cube(n+'Casing',c,(.065,.065,top-sill+.10),white,parent)
   for v in [sill,top]:
    c=[a[0],a[1],z+v];c[0 if ax else 1]+=s*(lo+hi)/2;c[1 if ax else 0]+=off;cube(n+'Lintel',c,(hi-lo+.10,.065,.065) if ax else (.065,hi-lo+.10,.065),white,parent)
  if sill>.1:
   c=[a[0],a[1],z+(sill+top)/2];c[0 if ax else 1]+=s*(lo+hi)/2;cube(n+'Glass',c,(hi-lo,.012,top-sill) if ax else (.012,hi-lo,top-sill),glass,parent)
   count=max(2,round((hi-lo)/.48))
   for j in range(1,count):
    c=[a[0],a[1],z+(sill+top)/2];c[0 if ax else 1]+=s*(lo+(hi-lo)*j/count);cube(n+'Mullion',c,(.025,.045,top-sill) if ax else (.045,.025,top-sill),white,parent)
   for v in [.33,.66]:
    c=[a[0],a[1],z+sill+(top-sill)*v];c[0 if ax else 1]+=s*(lo+hi)/2;cube(n+'Muntin',c,(hi-lo,.04,.018) if ax else (.04,hi-lo,.018),white,parent)
 part(cur,L,z,h,material or cream,'Wall')
 # continuous skirting except door apertures
 cuts=[(lo,hi) for lo,hi,sill,top in openings if sill<.1];cur=0
 for lo,hi in sorted(cuts)+[(L,L)]:
  for off in [-.09,.09]:
   c=[a[0],a[1],z+.075];c[0 if ax else 1]+=s*(cur+lo)/2;c[1 if ax else 0]+=off
   if lo>cur:cube(n+'Skirting',c,(lo-cur,.035,.15) if ax else (.035,lo-cur,.15),white,parent)
  cur=hi

def floor(n,bounds,z,mats,parent):
 x0,y0,x1,y1=bounds
 cube(n+'Subfloor',((x0+x1)/2,(y0+y1)/2,z-.12),(x1-x0,y1-y0,.23),woods[0],parent)
 x=x0
 while x<x1-.01:
  w=min(.19,x1-x);y=y0
  first=random.uniform(.35,1.8)
  while y<y1-.01:
   l=min(first if y==y0 else random.uniform(1.0,2.1),y1-y);cube(n+'Plank',(x+w/2,y+l/2,z+.002),(w-.003,l-.003,.018),random.choice(mats),parent);y+=l
  x+=w

# Main level scale: 0.037 metres / source floor-plan pixel. Lower aligned by envelope.
for lv,z in [('Main',3.05),('Lower',0)]:
 P=roots[lv]
 floor(lv+'Rear',(0,8,11.77,16.2),z,woods,P)
 if lv=='Main':
  for bounds in [(1,0,8.7,4.6),(2.45,4.6,8.7,8),(1,7.7,2.45,8)]:floor(lv+'Front',bounds,z,woods,P)
 else:floor(lv+'Front',(1,0,8.70,8),z,woods,P)
 floor(lv+'Middle',(0,4.6,1,8),z,woods,P)
 wall('Front',(1,0),(8.7,0),z,openings=[(.6,2.8,.85,2.35),(5.6,7.2,0,2.4)])
 wall('EastFront',(8.7,0),(8.7,8),z,openings=[(.4,2.3,.85,2.3),(3.2,5.4,.75,2.4)])
 wall('EastRear',(11.77,8),(11.77,16.2),z,openings=([(0.7,2.9,.8,2.4),(4.0,6.3,.8,2.4)] if lv=='Main' else [(1.0,6.0,0,2.5)]))
 wall('Rear',(0,16.2),(11.77,16.2),z,openings=[(2.1,4.3,1.2,2.3),(8.6,10.7,.8,2.4)])
 wall('WestRear',(0,4.6),(0,16.2),z,openings=[(2.0,4.2,0,2.4),(5.0,7.6,.65,2.4)])
 wall('WestFront',(1,0),(1,4.6),z,openings=[])
 wall('NotchWest',(0,4.6),(1,4.6),z)
 wall('NotchEast',(8.7,8),(11.77,8),z,openings=[(.5,2.5,.8,2.4)] if lv=='Main' else [])
# Upper partitions
P=roots['Main'];z=3.05
wall('BedroomTwoEast',(4.3,0),(4.3,4.6),z,material=cream)
wall('BedroomTwoNorth',(1,4.6),(4.3,4.6),z,openings=[(2.0,2.95,0,2.15)])
wall('KitchenBath',(5.13,12),(5.13,16.2),z)
wall('EnsuiteEast',(7.3,12),(7.3,16.2),z,material=taupe)
wall('EnsuiteSouth',(5.13,12),(7.3,12),z,openings=[(1.0,1.85,0,2.1)])
wall('HallSouth',(4.3,10.7),(9.0,10.7),z,openings=[(3.3,4.2,0,2.15)])
wall('ClosetEast',(9,8),(9,10.7),z,material=taupe)
wall('LivingNorth',(4.3,8),(9,8),z)
wall('UtilityWest',(4.3,8),(4.3,10.7),z,openings=[(.25,1,0,2.1),(1.55,2.45,0,2.1)])
wall('PowderSouth',(4.3,9.2),(6.6,9.2),z)
wall('PowderEast',(6.6,9.2),(6.6,10.7),z)
wall('ClosetSide',(5.8,8),(5.8,9.2),z)
# Foyer screen below vaulted ceiling
wall('FoyerScreen',(5.45,2.1),(7.9,2.1),z,h=2.65)
wall('FoyerSide',(7.9,.45),(7.9,2.1),z,h=2.65)
# Main suite floor overlay
floor('PrimaryFloor',(7.38,10.8,11.67,16.1),z+.025,darkwoods,P)
floor('PrimaryFront',(9.08,8.1,11.67,10.8),z+.025,darkwoods,P)
# Lower rooms
P=roots['Lower'];z=0
wall('GarageWest',(4.3,8),(4.3,16.2),0,openings=[(.3,1.25,0,2.1),(4.7,5.8,0,2.1)])
wall('GarageFront',(4.3,8),(11.77,8),0,openings=[(6,7,0,2.15)])
wall('BedroomThreeWest',(4.3,4.4),(4.3,8),0,openings=[(.2,1.15,0,2.1)])
wall('BedroomFourWest',(4.3,0),(4.3,4.4),0,openings=[(2.95,3.9,0,2.1)],material=purple)
wall('BedroomDivider',(4.3,4.4),(8.7,4.4),0,material=purple)
wall('BathEast',(3.0,6.4),(3.0,9.5),0,openings=[(.25,1.2,0,2.1)])
wall('BathNorth',(0,9.5),(3.0,9.5),0)
wall('BathSouth',(0,6.4),(3.0,6.4),0)
# Garage door at east back; frame panel fills opening.
cube('GarageDoor',(11.78,11.5,1.2),(.10,5,2.4),yellow)
for zi in [.4,.8,1.2,1.6,2.0]:cube('GarageDoorSeam',(11.845,11.5,zi),(.008,4.9,.02),white)
# Permanent stairs, balusters and upper guard. Footprint follows plan.
for i in range(18):
 y=4.65+i*.17;zz=(i+1)*3.05/18
 cube('StairTread',(1.65,y,zz-.055),(1.4,.19,.11),woods[5],roots['Lower'])
 beam('StairSpindle',(2.37,y,zz),(2.37,y,zz+.88),.035,white,roots['Lower'])
beam('StairHandrail',(2.37,4.65,.95),(2.37,7.55,3.95),.075,wood,roots['Lower'])
for x in [0.35,2.5]:
 beam('UpperGuardRail',(x,4.8,4.08),(x,6.6,4.08),.065,wood,roots['Main'])
 for i in range(13):cube('UpperGuardSpindle',(x,4.8+i*.15,3.57),(.035,.035,1.03),white,roots['Main'])
# Vaulted main ceiling, in separately hideable group.
def slope(n,verts,m,parent):
 mesh=bpy.data.meshes.new(n);mesh.from_pydata(verts,[],[tuple(range(len(verts)))]);mesh.update();o=bpy.data.objects.new(n,mesh);bpy.context.collection.objects.link(o);o.parent=parent;mesh.materials.append(m);return o
for x0,x1,y0,y1 in [(0,5.13,8,16.2),(1,8.7,0,8),(7.3,11.77,8,16.2)]:
 mid=(x0+x1)/2
 for xa,xb,za,zb in [(x0,mid,5.90,7.15),(mid,x1,7.15,5.90)]:
  slope('VaultedCeiling',[(xa,y0,za),(xb,y0,zb),(xb,y1,zb),(xa,y1,za)],ceil,roots['MainCeilings'])
 for y in [y0+.2,y1-.2]:
  beam('VaultBeam',(x0,y,5.88),(mid,y,7.10),.15,white,roots['MainCeilings']);beam('VaultBeam',(mid,y,7.10),(x1,y,5.88),.15,white,roots['MainCeilings'])
for b in [(0,8,11.77,16.2),(2.45,4.6,8.7,8),(0,4.6,1,8),(1,7.7,2.45,8),(1,0,8.7,4.6)]:
 x0,y0,x1,y1=b;cube('LowerCeiling',((x0+x1)/2,(y0+y1)/2,2.78),(x1-x0,y1-y0,.12),ceil,roots['LowerCeilings'])
# Fill gables, roofs and exterior lap siding. Roof covers principal intersecting wings.
for x0,x1,y0,y1 in [(0,5.13,8,16.2),(1,8.7,-1.8,8),(7.3,11.77,8,16.2)]:
 mid=(x0+x1)/2
 for yy in [y0,y1]:slope('Gable',[(x0,yy,5.9),(x1,yy,5.9),(mid,yy,7.2)],yellow,roots['Roof'])
 for xa,xb,za,zb in [(x0-.3,mid,5.88,7.3),(mid,x1+.3,7.3,5.88)]:
  slope('Roof',[(xa,y0-.3,za),(xb,y0-.3,zb),(xb,y1+.3,zb),(xa,y1+.3,za)],roofmat,roots['Roof'])
  for yy in [y0-.3,y1+.3]:beam('RoofFascia',(xa,yy,za),(xb,yy,zb),.14,white,roots['Roof'])
# Outdoor platforms and railings
P=site
floor('Balcony',(8.7,3.5,11.5,8),3.02,[deckwood],site)
floor('Porch',(4.7,-1.8,8.7,0),3.02,[deckwood],site)
floor('RearTerrace',(-5,7,-.12,16.7),3.02,[tile],site)
floor('HighDeck',(-8,8,-5.1,17),4.45,[deckwood],site)
def railing(a,b,z):
 beam('Handrail',(a[0],a[1],z+1),(b[0],b[1],z+1),.09,white,site);L=math.dist(a,b)
 for i in range(int(L/.15)+1):
  t=i/max(1,int(L/.15));x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t;cube('Baluster',(x,y,z+.5),(.035,.035,1),white,site)
for a,b,z in [((11.5,3.5),(11.5,8),3.05),((8.7,3.5),(11.5,3.5),3.05),((-8,8),(-8,17),4.5),((4.7,-1.8),(6,-1.8),3.05),((8.3,-1.8),(8.7,-1.8),3.05)]:railing(a,b,z)
for x,y in [(11.4,3.6),(11.4,7.9),(4.8,-1.7),(8.6,-1.7)]:cube('PorchPost',(x,y,4.55),(.14,.14,3),white,site)
for i in range(17):cube('PorchSteps',(7.15,-1.9-i*.25,3.05-(i+1)*.18),(2.0,.27,.18),tile,site)
for x,y in [(-7.9,8.1),(-5.2,8.1),(-7.9,16.9),(-5.2,16.9)]:cube('DeckPier',(x,y,2.2),(.22,.22,4.4),wood,site)
# Ground landscaping and detached two-bay garage, approximate site placement.
cube('Driveway',(9,3,-.26),(17,31,.3),mat('Paving',(.26,.27,.25)),site)
cube('Garden',(-7,8,2.75),(4,24,.5),soil,site)
cube('RetainingWall',(-5.3,11,1.5),(.35,19,3),tile,site)
for x,y in [(-7,5),(-7,15),(-4,20),(2,21),(17,18)]:
 cyl('TreeTrunk',(x,y,3.5),.2,7,wood,site)
 for j in range(7):ell('Canopy',(x+random.uniform(-1.5,1.5),y+random.uniform(-1.5,1.5),7+random.uniform(-.5,1.5)),(2,2,1.5),leaf,site)
P=site
for a,b in [((14,18),(20,18)),((14,18),(14,24)),((20,18),(20,24)),((14,24),(20,24))]:wall('DetachedGarage',a,b,0,2.7,material=yellow,parent=site)
for x in [15.6,18.5]:cube('DetachedDoor',(x,17.90,1.1),(2.4,.08,2.2),white,site)
for xa,xb,za,zb in [(13.7,17,2.7,4.1),(17,20.3,4.1,2.7)]:slope('DetachedRoof',[(xa,17.7,za),(xb,17.7,zb),(xb,24.3,zb),(xa,24.3,za)],roofmat,site)
# Asset helpers; each furniture item has an independent transform parent.
def sofa(n,x,y,z,room,level='Main',rot=0,color=linen,width=2.25):
 g=group(room,'seating',n,level)
 cube('SofaBase',(0,0,.30),(width,.9,.35),color,g,.13)
 cube('Back',(0,.37,.73),(width,.25,.77),color,g,.12)
 for xx in [-width/2+.12,width/2-.12]:cube('Arm',(xx,0,.59),(.24,.95,.48),color,g,.10)
 for xx in [-width*.23,width*.23]:
  cube('SeatCushion',(xx,-.08,.54),(width*.40,.65,.18),color,g,.075)
  o=cube('ThrowPillow',(xx,.20,.85),(.42,.17,.42),rust if xx<0 else sage,g,.08);o.rotation_euler[1]=-.15 if xx<0 else .15
 g.location=(x,y,z);g.rotation_euler[2]=rot;return g

def chair(n,x,y,z,room,level='Main',rot=0,color=grey):
 g=group(room,'seating',n,level);cube('Seat',(0,0,.48),(.53,.52,.13),color,g,.07);cube('Back',(0,.22,.75),(.55,.14,.56),color,g,.08)
 for xx in [-.20,.20]:
  for yy in [-.19,.19]:beam('Leg',(xx,yy,.45),(xx*1.25,yy*1.25,.02),.035,dark,g)
 g.location=(x,y,z);g.rotation_euler[2]=rot

def table(n,x,y,z,room,level='Main',size=(1.5,.75),height=.43,round=False,material=wood):
 g=group(room,'tables',n,level)
 if round:
  cyl('Top',(0,0,height),size[0]/2,.07,material,g);cyl('Pedestal',(0,0,height/2),size[0]*.28,height,material,g)
 else:
  cube('TableTop',(0,0,height),(*size,.07),material,g,.025)
  for xx in [-size[0]*.4,size[0]*.4]:
   for yy in [-size[1]*.38,size[1]*.38]:cube('Leg',(xx,yy,height/2),(.055,.055,height),dark,g)
 g.location=(x,y,z);return g

def rug(n,x,y,z,sx,sy,room,level='Main'):
 g=group(room,'decor',n,level);cube('Rug',(x,y,z+.032),(sx,sy,.026),linen,g,.015)
 for xx in range(int(sx/.065)):
  cube('RugWeave',(x-sx/2+xx*.065,y,z+.047),(.014,sy-.03,.003),grey if xx%9==0 else tile,g)

def plant(n,x,y,z,room,level='Main',scale=1):
 g=group(room,'decor',n,level);cyl('Planter',(x,y,z+.20*scale),.22*scale,.40*scale,tile,g)
 for j in range(10):
  a=j*2.4;end=(x+math.cos(a)*.35*scale,y+math.sin(a)*.35*scale,z+(.6+j*.08)*scale);beam('Stem',(x,y,z+.3*scale),end,.012*scale,wood,g);o=ell('Leaf',end,(.16*scale,.075*scale,.27*scale),leaf,g);o.rotation_euler[1]=.55;o.rotation_euler[2]=a

def art(n,x,y,z,w,h,room,level='Main'):
 g=group(room,'decor',n,level);cube('Frame',(x,y,z),(w,.055,h),wood,g,.01);cube('Canvas',(x,y-.035,z),(w-.06,.018,h-.06),linen,g)
 for j in range(7):
  o=ell('AbstractShape',(x+random.uniform(-w*.35,w*.35),y-.05,z+random.uniform(-h*.3,h*.3)),(random.uniform(.10,.28),.006,random.uniform(.10,.3)),[taupe,rust,tile][j%3],g);o.rotation_euler[1]=j*.7

def bed(n,x,y,z,room,level='Main',width=1.85):
 g=group(room,'beds',n,level);cube('BedBase',(x,y,z+.23),(width,2.10,.4),taupe,g,.09);cube('Mattress',(x,y,z+.49),(width,2.1,.24),linen,g,.10);cube('Duvet',(x,y-.24,z+.65),(width+.09,1.6,.15),linen,g,.08);cube('Headboard',(x,y+1.0,z+.79),(width+.15,.14,1.42),linen,g,.10)
 for xx in [-width*.25,width*.25]:cube('Pillow',(x+xx,y+.63,z+.77),(width*.42,.47,.18),white,g,.10)
 cube('Throw',(x,y-.55,z+.745),(width+.11,.35,.04),rust,g,.018)
 for dx in [-width/2-.37,width/2+.37]:table(n+'Nightstand',x+dx,y+.65,z,room,level,size=(.55,.52),height=.55,material=wood)

def lamp(x,y,z,room,level='Main'):
 g=group(room,'decor','TableLamp',level);cyl('LampStem',(x,y,z+.23),.035,.45,brass,g);cyl('Shade',(x,y,z+.49),.20,.28,linen,g)
# Upper living, dining, kitchen and suite. Placement follows listing sight lines.
P=roots['Main'];z=3.05
sofa('LivingSofa',6.45,6.7,z,'Living');chair('LoungeChair',4.9,4.7,z,'Living',rot=math.radians(-60),color=wood)
table('CoffeeTable',6.45,5.1,z,'Living',size=(.90,.9),round=True,material=dark)
g=group('Living','seating','Ottoman');cyl('Ottoman',(7.7,4.9,z+.25),.39,.50,linen,g)
rug('LivingRug',6.3,5.2,z,3.35,3.35,'Living');plant('LivingTree',8.15,7.4,z,'Living');art('LivingArtwork',6.45,7.91,z+1.65,2.0,1.25,'Living')
cube('Fireplace',(6.5,7.78,z+.8),(1.45,.3,.38),dark,P);cube('FireplaceSurround',(6.5,7.95,z+.8),(1.65,.1,.65),white,P)
# Kitchen white cabinetry, walnut towers, black stone counters, red range hood.
for x in [.55,1.4,2.25,3.10,3.95,4.7]:
 cube('BaseCabinet',(x,15.83,z+.45),(.80,.64,.90),white,P,.02);cube('DoorPanel',(x,15.49,z+.47),(.74,.035,.74),white,P,.015);cube('CabinetPull',(x,15.455,z+.72),(.28,.025,.018),steel,P)
cube('RearCounter',(2.57,15.82,z+.94),(5.12,.71,.06),dark,P,.018)
cube('KitchenBacksplash',(2.57,16.10,z+1.27),(5.12,.045,.60),tile,P)
for y in [13.1,14.0,14.9]:
 cube('SideCabinet',(4.76,y,z+.45),(.62,.84,.9),white,P,.02);cube('SideCounter',(4.76,y,z+.94),(.70,.87,.06),dark,P)
cube('Refrigerator',(0.58,13.65,z+1.10),(1.04,.9,2.2),steel,P,.03)
for xx in [.06,1.10]:cube('WalnutTower',(xx,13.65,z+1.2),(.16,1,2.4),wood,P)
for xx in [.44,.72]:cube('FridgeHandle',(xx,13.17,z+1.1),(.025,.06,.70),steel,P)
cube('Island',(2.7,13.65,z+.46),(1.15,2.2,.92),white,P,.03);cube('IslandStone',(2.7,13.65,z+.96),(1.4,2.35,.065),dark,P,.025)
cube('Range',(4.75,14,z+.47),(.64,.83,.92),steel,P,.035);cube('OvenWindow',(4.405,14,z+.40),(.025,.62,.38),dark,P)
cube('RedRangeHood',(4.84,14,z+2.12),(.56,.88,.50),rust,P,.04)
for yy in [13.8,14.2]:
 for xx in [4.55,4.9]:cyl('Burner',(xx,yy,z+.952),.105,.015,dark,P)
cube('Sink',(2.7,15.82,z+.979),(.7,.45,.012),steel,P,.04);beam('Tap',(2.7,16.0,z+.98),(2.7,16,z+1.30),.035,steel,P);beam('Spout',(2.7,16,z+1.3),(2.7,15.85,z+1.3),.035,steel,P)
for y in [13.05,14.20]:chair('IslandStool',1.75,y,z+.21,'Kitchen',rot=math.pi/2,color=dark)
table('DiningTable',2.25,9.6,z,'Dining',size=(1.1,2.0),height=.77,material=taupe)
for yy in [9.0,10.2]:
 chair('DiningChair',1.25,yy,z,'Dining',rot=math.pi/2);chair('DiningChair',3.25,yy,z,'Dining',rot=-math.pi/2)
chair('DiningEndChair',2.25,8.25,z,'Dining',rot=math.pi);chair('DiningEndChair',2.25,10.95,z,'Dining')
rug('DiningRug',2.25,9.6,z,3.3,3.7,'Dining');plant('DiningFlowers',2.25,9.6,z+.8,'Dining',scale=.42)
# Pendant frames retained as fixtures.
for x,y in [(2.25,9.6),(2.7,13.15),(2.7,14.25),(6.45,4.0)]:
 beam('PendantStem',(x,y,z+2.4),(x,y,6.6),.015,brass,P)
 for dx in [-.20,.20]:
  for dy in [-.20,.20]:beam('PendantFrame',(x+dx,y+dy,z+2.25),(x+dx,y+dy,z+2.65),.017,dark,P)
 for zz in [z+2.25,z+2.65]:
  for dy in [-.2,.2]:beam('PendantFrame',(x-.2,y+dy,zz),(x+.2,y+dy,zz),.017,dark,P)
  for dx in [-.2,.2]:beam('PendantFrame',(x+dx,y-.2,zz),(x+dx,y+.2,zz),.017,dark,P)
# Beds orient their heads towards north, consistent with plan walls; approximate exact staging.
bed('PrimaryBed',9.75,14.7,z,'Primary');rug('PrimaryRug',9.7,14,z,3.4,3.6,'Primary');art('PrimaryArtwork',9.75,16.07,z+1.8,1.8,.75,'Primary')
table('PrimaryDesk',10.75,9.35,z,'Primary',size=(1.15,.6),height=.75);chair('PrimaryDeskChair',10.6,10.2,z,'Primary',rot=math.pi);plant('PrimaryPlant',11.1,11,z,'Primary');lamp(8.43,15.35,z+.57,'Primary');lamp(11.05,15.35,z+.57,'Primary')
bed('GuestBed',2.7,2.8,z,'Guest',width=1.5);rug('GuestRug',2.7,2.3,z,2.6,3.0,'Guest');art('GuestArt',2.7,4.47,z+1.85,1.25,.75,'Guest');plant('GuestPlant',1.4,.8,z,'Guest',scale=.75)
# Bathrooms and closet fittings permanent.
def bathroom(x,y,z,parent):
 cube('Vanity',(x,y,z+.42),(1.5,.55,.84),white,parent,.025);cube('VanityTop',(x,y,z+.88),(1.6,.6,.06),tile,parent,.02)
 for dx in [-.42,.42]:ell('Basin',(x+dx,y,z+.91),(.26,.19,.04),white,parent);cube('Mirror',(x+dx,y+.28,z+1.53),(.65,.03,.9),steel,parent)
 ell('ToiletBowl',(x+1.1,y-.45,z+.32),(.20,.30,.23),white,parent);cube('Cistern',(x+1.1,y-.19,z+.60),(.39,.17,.52),white,parent,.06)
bathroom(5.95,13.0,z,P);cube('ShowerTray',(6.2,15.4,z+.08),(1.85,1.3,.14),tile,P);cube('ShowerGlass',(6.2,14.77,z+1.15),(1.85,.025,2.15),glass,P)
bathroom(5.15,10.37,z,P)
for y in [8.5,9.1,9.7,10.3]:cube('ClosetShelf',(8.7,y,z+1.2),(.4,.55,.035),white,P)
# Lower staging.
z=0;P=roots['Lower']
sofa('FamilySofa',2.45,2.8,z,'Family','Lower');chair('FamilyArmchair',1.5,.9,z,'Family','Lower',rot=math.pi);table('FamilyCoffee',2.55,1.5,z,'Family','Lower',size=(1.2,.75));rug('FamilyRug',2.55,1.7,z,2.4,2.8,'Family','Lower');plant('FamilyPlant',1.4,3.8,z,'Family','Lower')
sofa('RecreationSofa',2.2,14.4,z,'Recreation','Lower');sofa('RecreationLoveseat',1.0,12.1,z,'Recreation','Lower',rot=math.pi/2,width=1.5);chair('RecreationChair',3.3,11.4,z,'Recreation','Lower',rot=math.pi)
table('RecreationTable',2.3,12.8,z,'Recreation','Lower',size=(1.25,.85));rug('RecreationRug',2.25,12.7,z,3.3,3.8,'Recreation','Lower');art('RecreationArt',2.2,16.08,1.7,1.8,.95,'Recreation','Lower');plant('RecreationPlant',.5,15.5,z,'Recreation','Lower')
bed('TwinBedOne',5.45,6.35,z,'Twins','Lower',width=.95);bed('TwinBedTwo',7.5,6.35,z,'Twins','Lower',width=.95);rug('TwinRug',6.5,6,z,3.6,2.9,'Twins','Lower')
bed('LowerGuestBed',6.5,2.65,z,'LowerGuest','Lower',width=1.65);rug('LowerGuestRug',6.5,2.3,z,3.3,3.4,'LowerGuest','Lower');art('LowerGuestArt',6.5,4.3,1.85,1.5,.8,'LowerGuest','Lower');plant('LowerGuestPlant',8.1,.5,z,'LowerGuest','Lower')
bathroom(1.1,9.1,0,P);cube('Bathtub',(0.75,7.8,.35),(1.3,.8,.65),white,P,.14);cube('LowerShower',(1,6.9,.05),(1.5,1,.10),tile,P)
# Outdoor seating and pergola kitchen.
for x,y,r in [(9.5,4.8,0),(10.6,6.8,math.pi)]:chair('BalconyChair',x,y,3.05,'Balcony','Outdoor',rot=r,color=blue)
table('BalconyTable',10.1,5.8,3.05,'Balcony','Outdoor',size=(.6,.6),height=.55,round=True)
sofa('TerraceSofa',-3,10,3.05,'Terrace','Outdoor',color=blue);table('TerraceTable',-3,8.6,3.05,'Terrace','Outdoor',size=(1.2,.8));chair('TerraceChair',-1.4,8,3.05,'Terrace','Outdoor',rot=math.pi,color=linen)
table('OutdoorDining',-2.8,14.2,3.05,'Terrace','Outdoor',size=(1.5,2.3),height=.77)
for y in [13.5,14.3,15.1]:chair('PatioDiningChair',-4,y,3.05,'Terrace','Outdoor',rot=math.pi/2,color=wood);chair('PatioDiningChair',-1.6,y,3.05,'Terrace','Outdoor',rot=-math.pi/2,color=wood)
for x in [-4.9,-.3]:
 for y in [12.5,16.5]:cube('PergolaPost',(x,y,4.45),(.12,.12,2.8),white,site)
for y in [12.5+i*.5 for i in range(9)]:cube('PergolaRafter',(-2.6,y,5.9),(4.8,.10,.16),white,site)
cube('OutdoorKitchen',(-2.8,16.25,3.55),(3.4,.7,1),tile,site);cube('BBQ',(-2.8,16.2,4.25),(1.2,.65,.5),steel,site,.05)
sofa('UpperDeckSofa',-6.5,14,4.5,'UpperDeck','Outdoor',color=blue);table('UpperDeckTable',-6.5,12.6,4.5,'UpperDeck','Outdoor',size=(1.2,.75))
# Lighting is separate from removable decor; furniture removal must not alter illumination.
lights=empty('Lighting',world)
def area(n,loc,power,size,target):
 d=bpy.data.lights.new(n,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(n,d);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.parent=lights
for level,z in [('Main',3.05),('Lower',0)]:
 for x,y in [(6.5,4.5),(2.3,9.6),(2.5,14),(9.7,13.5),(2.7,2.7),(6.5,2),(6.5,6),(2,13)]:area(level+'SoftFill',(x,y,z+2.7),180 if level=='Main' else 120,2.8,(x,y,z))
d=bpy.data.lights.new('Sun','SUN');d.energy=2.2;d.angle=.12;o=bpy.data.objects.new('Sun',d);bpy.context.collection.objects.link(o);o.rotation_euler=(.45,-.6,-.4);o.parent=lights
bpy.context.scene.world.color=(.3,.35,.45)
# Align the primary bed headboard and wall art to the photographed west wall.
for ob in list(bpy.data.objects):
 if ob.type=='EMPTY' and (ob.name.startswith('PrimaryBed') or ob.name.startswith('PrimaryArtwork') or ob.name.startswith('TableLamp')):
  oldx,oldy=ob.location.x,ob.location.y
  ob.rotation_euler[2]=math.pi/2;ob.location.x=8.7+14.7-oldy;ob.location.y=14.0-9.75+oldx
  if ob.name.startswith('PrimaryArtwork'):ob.location.x+=.12
# Saved authoring view and camera manifest. Coordinates are inferred viewpoints, not calibrated cameras.
views=[
 {'id':'living','name':'Living room','room':'Living','level':'Main','eye':[8.15,2.9,4.65],'target':[6.0,6.5,4.4],'refs':[14,15]},
 {'id':'dining','name':'Dining & kitchen','room':'Dining','level':'Main','eye':[3.9,6.9,4.70],'target':[2.35,13.8,4.35],'refs':[16,18]},
 {'id':'kitchen','name':'Kitchen','room':'Kitchen','level':'Main','eye':[1.05,11.0,4.70],'target':[3.1,15,4.3],'refs':[20,22]},
 {'id':'primary','name':'Primary suite','room':'Primary','level':'Main','eye':[11.15,11.1,4.70],'target':[9.5,14.8,4.0],'refs':[28,30]},
 {'id':'guest','name':'Main guest room','room':'Guest','level':'Main','eye':[4.0,.6,4.65],'target':[2.5,3.0,3.85],'refs':[39,41]},
 {'id':'recreation','name':'Recreation room','room':'Recreation','level':'Lower','eye':[3.6,10.1,1.6],'target':[2.0,14.0,1.05],'refs':[63,68]},
 {'id':'family','name':'Family room','room':'Family','level':'Lower','eye':[3.8,.4,1.65],'target':[2.25,3,1.0],'refs':[42,43]},
 {'id':'twins','name':'Twin bedroom','room':'Twins','level':'Lower','eye':[8.15,4.85,1.65],'target':[6.35,6.7,.85],'refs':[51,53]},
 {'id':'lowerguest','name':'Lower guest room','room':'LowerGuest','level':'Lower','eye':[8.1,.55,1.65],'target':[6.45,2.85,.85],'refs':[54,55]},
 {'id':'terrace','name':'Garden terrace','room':'Terrace','level':'Outdoor','eye':[-4.65,6.7,4.8],'target':[-2.4,13.7,4.15],'refs':[84,90]},
 {'id':'balcony','name':'Front balcony','room':'Balcony','level':'Outdoor','eye':[11.2,3.7,4.7],'target':[9.1,7.4,4.0],'refs':[76,78]},
 {'id':'exterior','name':'Exterior','room':None,'level':'Exterior','eye':[24,-16,11],'target':[5,8,3.4],'refs':[6,71]},
 {'id':'mainplan','name':'Main level dollhouse','room':None,'level':'MainPlan','eye':[22,-12,29],'target':[5.8,8,3.1],'refs':[120]},
 {'id':'lowerplan','name':'Lower level dollhouse','room':None,'level':'LowerPlan','eye':[22,-12,26],'target':[5.8,8,0],'refs':[120]},
]
(R/'scene/views.json').write_text(json.dumps(views,indent=2));(R/'scene/furniture.json').write_text(json.dumps(items,indent=2))
# Add camera for editable source.
d=bpy.data.cameras.new('ReviewCamera');o=bpy.data.objects.new('ReviewCamera',d);bpy.context.collection.objects.link(o);o.location=views[0]['eye'];o.rotation_euler=(Vector(views[0]['target'])-o.location).to_track_quat('-Z','Y').to_euler();d.lens=22;bpy.context.scene.camera=o
bpy.context.scene.unit_settings.system='METRIC'
import bmesh
for ob in bpy.data.objects:
 if ob.type=='MESH':
  bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
bpy.ops.wm.save_as_mainfile(filepath=str(R/'scene/house.blend'))
bpy.ops.wm.usd_export(filepath=str(R/'scene/house.usdc'),export_materials=True,generate_preview_surface=True,export_lights=True,export_cameras=False,selected_objects_only=False,root_prim_path='/World')
print('HOUSE_BUILT',len(bpy.data.objects),'objects',len(items),'furniture items')
