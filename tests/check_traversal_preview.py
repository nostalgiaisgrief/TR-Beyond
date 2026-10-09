"""Native traversal frames and traces, compared between debug and optimized builds."""
import csv,json,subprocess,hashlib
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
results=[]
scenarios=[('forward-reach',43,['--forward-test'],11),('forward-catch',75,['--forward-test'],10),('vault-low',15,['--vault-test','1'],19),('vault-high',30,['--vault-test','2'],19),('vault-grab',40,['--vault-test','3'],10),('pool-enter',45,['--pool-test'],35),('pool-swim',90,['--pool-test'],17),('pool-surface',150,['--pool-test'],34),('pool-exit',250,['--pool-test'],55),('pool-stand',350,['--pool-test'],2)]
for name,ticks,args,expected in scenarios:
    copies=[]
    for suffix in ('','_debug'):
        base=ROOT/'build'/('traversal-'+name+suffix)
        subprocess.run([str(ROOT/'build'/('tomb_preview'+suffix+'.exe')),'--simulate',str(ticks),'--trace',str(base.with_suffix('.csv')),'--capture',str(base.with_suffix('.ppm')),'--orbit','0' if (name.startswith('forward') or name=='vault-high' or name.startswith('pool')) else '-1.57079633','--distance','600' if name=='vault-grab' or name.startswith('pool') else '1200']+args,cwd=ROOT,check=True,timeout=30)
        trace=base.with_suffix('.csv').read_bytes();frame=base.with_suffix('.ppm').read_bytes();copies.append((trace,frame))
        rows=list(csv.DictReader(trace.decode().splitlines()));assert len(rows)==ticks and all(r['blocked']=='0' for r in rows)
        assert int(rows[-1]['state'])==expected,(name,rows[-1])
        image=Image.open(base.with_suffix('.ppm'));assert len(image.getcolors(image.width*image.height))>512,name
        if not suffix:image.save(base.with_suffix('.png'))
    assert copies[0]==copies[1],name
    results.append(dict(name=name,ticks=ticks,last=rows[-1],trace_sha256=hashlib.sha256(copies[0][0]).hexdigest()))
(ROOT/'analysis/traversal-preview-validation.json').write_text(json.dumps(dict(builds=2,cases=results,scope='Native real-level integration, not whole-frame DOS equivalence'),indent=2)+'\n')
print('PASS: 20 native traversal captures; debug and optimized frames/traces identical')
