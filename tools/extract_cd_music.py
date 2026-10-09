from pathlib import Path
import re,wave
root=Path('F:/TombRaiG/cd');text=(root/'tombeng.cue').read_text();tracks=[]
for number,kind,body in re.findall(r'TRACK (\d+) (\S+)(.*?)(?=\s+TRACK|\Z)',text,re.S):
 indexes={}
 for ix,m,s,f in re.findall(r'INDEX (\d+) (\d+):(\d+):(\d+)',body): indexes[int(ix)]=(int(m)*60+int(s))*75+int(f)
 tracks.append((int(number),kind,indexes))
with (root/'tombeng.bin').open('rb') as source:
 for n,kind,ix in tracks:
  if not 2<=n<=10:continue
  nextix=tracks[n][2] if n<len(tracks) else {1:(root/'tombeng.bin').stat().st_size//2352}
  begin=ix[1]*2352;end=nextix.get(0,nextix[1])*2352
  source.seek(begin);data=source.read(end-begin)
  with wave.open(f'work/reference-assets/audio/cd{n:02}.wav','wb') as w:w.setparams((2,2,44100,0,'NONE','not compressed'));w.writeframes(data)
  print(n,len(data)/176400)
