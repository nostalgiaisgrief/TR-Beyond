"""Actual GYM/LEVEL1 water-height queries against DOS 0x17570."""
from compare_level import *
def main():
    o=GeometryOracle();o.allowed.update(range(0xcc058,0xcc05c));count=0
    ds=[bind(ROOT/'build'/f'step_test{s}.dll') for s in ('','_debug')]
    for d in ds:d.tomb_water_height.argtypes=[C.POINTER(Level),I32,I32,C.c_int];d.tomb_water_height.restype=I16
    for name in ['GYM.PHD','LEVEL1.PHD']:
        path=ROOT/'work/reference-assets/DATA'/name;fixture=parse(path);o.install(fixture)
        for i,r in enumerate(fixture['rooms']):o.write(ROOMS+i*68+66,r['flags'],2)
        loaded=[]
        for d in ds:
            error=C.create_string_buffer(256);l=d.tomb_level_load(str(path).encode(),error,256);assert l;loaded.append((d,l))
        for ri,r in enumerate(fixture['rooms']):
            for ix in range(1,r['nx']-1):
                for iz in range(1,r['nz']-1):
                    for off in (0,512,1023):
                        x=r['x']+ix*1024+off;z=r['z']+iz*1024+off
                        expected=C.c_int16(o.call(0x17570,x,123,z,ri)).value
                        for d,l in loaded:assert d.tomb_water_height(l,x,z,ri)==expected,(name,ri,ix,iz,expected)
                        count+=1
        for d,l in loaded:d.tomb_level_free(l)
    (ROOT/'analysis/c-water-height-validation.json').write_text(json.dumps(dict(cases=count,builds=2,scope=__doc__),indent=2)+'\n');print('PASS:',count,'real-level water-height queries per build')
if __name__=='__main__':main()
