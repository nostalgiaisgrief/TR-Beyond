"""Extract the DOS gym tutorial RIFF samples, using the executable's track+148 map."""
from pathlib import Path
import struct,sys,wave,io,json,hashlib
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tests'))
from compare_level import parse
path=root/'work/reference-assets/DATA/GYM.PHD';fixture=parse(path);data=fixture['data']
at=fixture['item_parsed_bytes']+8192+768
for width in (16,1):
    count=struct.unpack_from('<H',data,at)[0];at+=2+count*width
mapping=struct.unpack_from('<256h',data,at);at+=512
count=struct.unpack_from('<I',data,at)[0];at+=4
details=[struct.unpack_from('<4H',data,at+i*8) for i in range(count)];at+=count*8
size=struct.unpack_from('<I',data,at)[0];at+=4;samples=data[at:at+size];at+=size
count=struct.unpack_from('<I',data,at)[0];at+=4
indices=struct.unpack_from('<'+'I'*count,data,at);assert at+count*4==len(data)
out=root/'work/reference-assets/audio';out.mkdir(exist_ok=True);report=[]
for track in range(26,51):
    detail=mapping[track+148];assert detail>=0
    index=details[detail][0];offset=indices[index]
    assert samples[offset:offset+4]==b'RIFF'
    size=struct.unpack_from('<I',samples,offset+4)[0]+8
    wav=samples[offset:offset+size]
    with wave.open(io.BytesIO(wav)) as w:
        assert w.getcomptype()=='NONE'
        seconds=w.getnframes()/w.getframerate()
    (out/f'track{track:02}.wav').write_bytes(wav)
    report.append(dict(track=track,sample=index,seconds=seconds,sha256=hashlib.sha256(wav).hexdigest()))
(root/'analysis/gym-audio-extraction.json').write_text(json.dumps(dict(source=str(path),mapping='DOS 0x38cf7: track+148 sound ID',tracks=report),indent=2)+'\n')
print('Extracted 25 original DOS gym voice samples (PCM RIFF)')
