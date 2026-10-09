"""Consecutive native backflip/swim captures; preserve gameplay traces across the rendering fix."""
import subprocess,json
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
results=[]
for name,ticks,args,orbit,distance in [('backflip',range(23,28),['--standing-test','--input','18'],'-1.57079633','1200'),('swim',range(57,62),['--pool-test'],'0','600')]:
    sheet=Image.new('RGB',(5*400,2*240),(20,20,20));draw=ImageDraw.Draw(sheet)
    for col,tick in enumerate(ticks):
        versions=[]
        for row,suffix in enumerate(('_before_pose_fix','','_debug')):
            base=ROOT/'build'/f'pose-{name}-{tick}{suffix}'
            subprocess.run([str(ROOT/'build'/f'tomb_preview{suffix}.exe'),'--simulate',str(tick),'--capture',str(base.with_suffix('.ppm')),'--trace',str(base.with_suffix('.csv')),'--orbit',orbit,'--distance',distance]+args,cwd=ROOT,check=True,timeout=30)
            versions.append((base.with_suffix('.csv').read_bytes(),base.with_suffix('.ppm').read_bytes()))
            if row<2:
                im=Image.open(base.with_suffix('.ppm'));im.thumbnail((400,216));sheet.paste(im,(col*400,row*240+24));draw.text((col*400+8,row*240+5),f'{"BEFORE" if row==0 else "AFTER"} tick {tick}',fill='white')
        assert versions[0][0]==versions[1][0]==versions[2][0],(name,tick,'gameplay changed')
        assert versions[1][1]==versions[2][1],(name,tick,'render differs between builds')
        results.append(dict(name=name,tick=tick,pixels_changed=versions[0][1]!=versions[1][1]))
    sheet.save(ROOT/'build'/f'pose-{name}-comparison.png')
assert any(r['pixels_changed'] for r in results)
(ROOT/'analysis/pose-preview-validation.json').write_text(json.dumps(dict(captures=30,cases=results,gameplay_traces_identical=True,debug_optimized_images_identical=True),indent=2)+'\n')
print('PASS: 30 consecutive native captures, unchanged gameplay, matching debug/optimized images')
