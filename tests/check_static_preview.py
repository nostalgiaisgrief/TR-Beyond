"""Reproducible table/staircase snapshots across camera angles."""
import subprocess,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'work/python-deps'))
from PIL import Image,ImageDraw
cases=[(1,a) for a in (3.9,4.3,4.7,5.1)]+[(2,a) for a in (-0.6,-0.3,0,0.3,0.6,2.7,3.1,3.5)]
sheet=Image.new('RGB',(1280,4*198));draw=ImageDraw.Draw(sheet)
for n,(scene,angle) in enumerate(cases):
 frames=[]
 for suffix in ('','_debug'):
  path=root/'build'/f'static-scene-{n}{suffix}.ppm'
  subprocess.run([str(root/'build'/f'tomb_preview{suffix}.exe'),'--render-test',str(scene),'--simulate','1','--orbit',str(angle),'--distance','2200','--capture',str(path)],cwd=root,check=True,timeout=20)
  frames.append(path.read_bytes())
 assert frames[0]==frames[1],(scene,angle)
 im=Image.open(root/'build'/f'static-scene-{n}.ppm');assert len(im.getcolors(im.width*im.height))>512
 im.thumbnail((426,175));x=(n%3)*426;y=(n//3)*198
 sheet.paste(im,(x,y+23));draw.text((x+8,y+6),f'{"Table" if scene==1 else "Staircase"} angle {angle}',fill='white')
sheet.save(root/'build/static-render-scenes.png')
(root/'analysis/static-render-validation.json').write_text(json.dumps(dict(captures=24,debug_optimized_identical=True,cases=cases,live_dos_screenshots=False),indent=2)+'\n')
print('PASS: 24 table/staircase captures across 12 camera angles; debug/optimized identical')
