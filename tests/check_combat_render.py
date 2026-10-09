"""Deterministic native combat captures; no DOS pixel-equivalence claim."""
import subprocess,json
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sheet=Image.new('RGB',(1440,840));draw=ImageDraw.Draw(sheet);results=[]
for j,(fixture,ticks) in enumerate([(1,8),(1,25),(1,120),(2,8),(2,25),(2,160),(3,8),(3,25),(3,160)]):
    versions=[]
    for suffix in ['', '_debug']:
        out=ROOT/'build'/f'combat-{j}{suffix}.ppm';trace=out.with_suffix('.csv')
        subprocess.run([str(ROOT/'build'/f'tomb_preview{suffix}.exe'),'--caves','--combat-test',str(fixture),'--simulate',str(ticks),'--input','64','--capture',str(out),'--trace',str(trace)],cwd=ROOT,timeout=30,check=True)
        versions.append((out.read_bytes(),trace.read_bytes()))
        if not suffix:
            im=Image.open(out);assert len(im.getcolors(im.width*im.height))>512;im.save(out.with_suffix('.png'));im.thumbnail((480,255));sheet.paste(im,((j%3)*480,(j//3)*280+20));draw.text(((j%3)*480+5,(j//3)*280+2),f'{["wolf","bear","bat"][fixture-1]}, tick {ticks}',fill='white')
    assert versions[0]==versions[1],j
    results.append(dict(fixture=fixture,ticks=ticks,debug_release_identical=True))
sheet.save(ROOT/'build/combat-scenes.png');(ROOT/'analysis/combat-captures.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS: 18 combat captures/traces identical debug/release')
