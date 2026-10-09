"""Native hazard render/trace comparisons, including all test shortcuts."""
import subprocess,json
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sheet=Image.new('RGB',(1440,570));draw=ImageDraw.Draw(sheet);results=[]
for j,(fixture,ticks,input) in enumerate([(1,1,0),(1,90,1),(2,1,0),(2,45,0),(2,85,0),(3,20,0)]):
    versions=[]
    for suffix in ['', '_debug']:
        out=ROOT/'build'/f'hazard-{j}{suffix}.ppm';trace=out.with_suffix('.csv')
        subprocess.run([str(ROOT/'build'/f'tomb_preview{suffix}.exe'),'--caves','--hazard-test',str(fixture),'--simulate',str(ticks),'--input',str(input),'--capture',str(out),'--trace',str(trace),'--follow-camera'],cwd=ROOT,timeout=30,check=True)
        versions.append((out.read_bytes(),trace.read_bytes()))
        if not suffix:
            im=Image.open(out);assert len(im.getcolors(im.width*im.height))>512;im.save(out.with_suffix('.png'));im.thumbnail((480,260));sheet.paste(im,((j%3)*480,(j//3)*285+20));draw.text(((j%3)*480+5,(j//3)*285+2),f'fixture {fixture}, tick {ticks}',fill='white')
    assert versions[0]==versions[1],j
    results.append(dict(fixture=fixture,ticks=ticks,debug_release_identical=True))
sheet.save(ROOT/'build/hazard-scenes.png');(ROOT/'analysis/hazard-captures.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS: 12 hazard captures/traces identical debug/release')
