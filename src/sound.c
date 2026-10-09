#include "sound.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
static unsigned word(const unsigned char *p){return p[0]|(unsigned)p[1]<<8;}
static uint32_t dword(const unsigned char *p){return (uint32_t)word(p)|(uint32_t)word(p+2)<<16;}
unsigned tomb_sound_random(uint32_t *seed) { *seed=*seed*UINT32_C(1103515245)+12345;return (*seed>>10)&32767; }
int tomb_sound_plan(const TombSoundDetail *d,int distance,int environment,int wet,uint32_t *seed,TombSoundPlan *out) {
    if(!d || !seed || !out || distance<0 || (environment!=2 && (environment&1)!=!!wet))return 0;
    if(d->chance && tomb_sound_random(seed)>d->chance)return 0;
    int volume=(int)d->volume-distance*4;
    if(d->flags&0x4000)volume-=(int)(tomb_sound_random(seed)>>2);
    int mode=d->flags&3;
    if(volume<=0 && mode!=2)return 0;
    int pitch=100;
    if(d->flags&0x2000)pitch=90+(int)(10*tomb_sound_random(seed)/16384);
    unsigned count=(d->flags>>2)&15;
    if(!count || mode==3)return 0;
    int sample=d->sample;
    if(count!=1)sample+=(int)(count*tomb_sound_random(seed)/32768);
    if(volume>32767)volume=32767;
    *out=(TombSoundPlan){sample,volume,pitch,mode};return 1;
}
static const unsigned char *take(const TombLevel *l,size_t *at,size_t count,size_t width) {
    if(*at>l->file_size || (width && count>(l->file_size-*at)/width))return NULL;
    const unsigned char *p=l->file_data+*at;*at+=count*width;return p;
}
int tomb_sound_sample(TombSoundSample *out,const unsigned char *p,size_t bytes) {
    if(bytes<12 || memcmp(p,"RIFF",4) || memcmp(p+8,"WAVE",4))return 0;
    size_t end=(size_t)dword(p+4)+8;if(end>bytes || end<12)return 0;
    unsigned align=0;const unsigned char *pcm=NULL;size_t pcm_bytes=0;
    for(size_t at=12;at+8<=end;) {
        size_t n=dword(p+at+4);if(n>end-at-8)return 0;
        if(!memcmp(p+at,"fmt ",4)) {
            if(n<16 || word(p+at+8)!=1)return 0;
            out->channels=word(p+at+10);out->rate=dword(p+at+12);align=word(p+at+20);out->bits=word(p+at+22);
        } else if(!memcmp(p+at,"data",4)){pcm=p+at+8;pcm_bytes=n;}
        at+=8+n+(n&1);
    }
    if(!pcm || !out->rate || out->rate>192000 || (out->bits!=8 && out->bits!=16) || !out->channels || out->channels>2 || align!=out->channels*out->bits/8 || pcm_bytes%align)return 0;
    out->pcm=pcm;out->frames=pcm_bytes/align;return out->frames>0;
}
void tomb_sound_bank_free(TombSoundBank *b){if(b){free(b->details);free(b->samples);memset(b,0,sizeof *b);}}
int tomb_sound_bank_load(TombSoundBank *b,const TombLevel *l) {
    if(!b || !l)return 0;
    memset(b,0,sizeof *b);size_t at=l->item_parsed_bytes;const unsigned char *p;
    if(!take(l,&at,8960,1))goto fail;
    for(unsigned width=16;width; width=width==16?1:0) {
        p=take(l,&at,1,2);if(!p)goto fail;
        if(!take(l,&at,word(p),width))goto fail;
    }
    p=take(l,&at,256,2);if(!p)goto fail;
    for(int i=0;i<256;i++)b->map[i]=(int16_t)word(p+2*i);
    p=take(l,&at,1,4);if(!p)goto fail;b->detail_count=dword(p);
    p=take(l,&at,b->detail_count,8);if(!p || !b->detail_count)goto fail;
    b->details=calloc(b->detail_count,sizeof *b->details);if(!b->details)goto fail;
    for(size_t i=0;i<b->detail_count;i++)b->details[i]=(TombSoundDetail){(uint16_t)word(p+i*8),(uint16_t)word(p+i*8+2),(uint16_t)word(p+i*8+4),(uint16_t)word(p+i*8+6)};
    p=take(l,&at,1,4);if(!p)goto fail;size_t bytes=dword(p);
    const unsigned char *blob=take(l,&at,bytes,1);if(!blob)goto fail;
    p=take(l,&at,1,4);if(!p)goto fail;b->sample_count=dword(p);
    p=take(l,&at,b->sample_count,4);if(!p || !b->sample_count || at!=l->file_size)goto fail;
    b->samples=calloc(b->sample_count,sizeof *b->samples);if(!b->samples)goto fail;
    for(size_t i=0;i<b->sample_count;i++) {size_t offset=dword(p+4*i);if(offset>=bytes || !tomb_sound_sample(b->samples+i,blob+offset,bytes-offset))goto fail;}
    for(int i=0;i<256;i++)if(b->map[i]<-1 || (b->map[i]>=0 && (size_t)b->map[i]>=b->detail_count))goto fail;
    for(size_t i=0;i<b->detail_count;i++) {TombSoundDetail *d=b->details+i;unsigned count=(d->flags>>2)&15;if(!count || d->sample>=b->sample_count || count>b->sample_count-d->sample)goto fail;}
    return 1;
fail:tomb_sound_bank_free(b);return 0;
}
void tomb_sound_init(TombSoundMixer *m,const TombSoundBank *b){memset(m,0,sizeof *m);m->bank=b;m->random=0x1234;}
void tomb_sound_clear(TombSoundMixer *m){if(m)memset(m->voices,0,sizeof m->voices);}
void tomb_sound_event(TombSoundMixer *m,const TombSoundEvent *e,int wet,const double listener[3]) {
    if(!m || !m->bank || !e)return;
    if(e->kind==7){for(int i=0;i<TOMB_SOUND_CHANNELS;i++)if(m->voices[i].id==e->id)m->voices[i].active=0;return;}
    int id=e->id,environment=e->environment;
    if(e->kind==6 && id==3) { /* DOS bubble effect emits sound only when its random bubble count is nonzero. */
        if(3*tomb_sound_random(&m->random)/32768==0)return;
        id=37;environment=1;
    } else if(e->kind!=5)return;
    if(id<0 || id>=256 || m->bank->map[id]<0)return;
    double dx=e->x-listener[0],dy=e->y-listener[1],dz=e->z-listener[2];
    if(fabs(dx)>8192 || fabs(dy)>8192 || fabs(dz)>8192)return;
    int distance=(int)sqrt(dx*dx+dy*dy+dz*dz);
    TombSoundPlan plan;if(!tomb_sound_plan(m->bank->details+m->bank->map[id],distance,environment,wet,&m->random,&plan))return;
    int slot=-1;
    for(int i=0;i<TOMB_SOUND_CHANNELS;i++) {
        TombSoundVoice *v=m->voices+i;
        if(v->active && v->id==id){if(plan.mode==0)return;slot=i;break;}
        if(!v->active)slot=i;
    }
    if(slot<0){m->dropped++;return;}
    m->voices[slot]=(TombSoundVoice){1,id,plan.sample,plan.volume,plan.pitch,plan.mode,0};m->played++;
}
static double value(const TombSoundSample *s,size_t frame,unsigned channel) {
    const unsigned char *p=s->pcm+(frame*s->channels+(s->channels==1?0:channel))*s->bits/8;
    return s->bits==8?((int)p[0]-128)*256:(int16_t)word(p);
}
void tomb_sound_mix(TombSoundMixer *m,int16_t *out,size_t frames) {
    for(size_t f=0;f<frames;f++) {
        double sum[2]={0,0};
        for(int i=0;i<TOMB_SOUND_CHANNELS;i++) {
            TombSoundVoice *v=m->voices+i;if(!v->active)continue;
            const TombSoundSample *s=m->bank->samples+v->sample;
            if(v->position>=s->frames){if(v->mode==2)v->position=fmod(v->position,s->frames);else {v->active=0;continue;}}
            size_t a=(size_t)v->position,b=a+1<s->frames?a+1:a;double t=v->position-a;
            for(unsigned c=0;c<2;c++)sum[c]+=(value(s,a,c)*(1-t)+value(s,b,c)*t)*v->volume/32767.0;
            v->position+=(double)s->rate*v->pitch/(100*TOMB_SOUND_RATE);
        }
        /* Modern stereo output, centred player effects, modest mix headroom. */
        for(int c=0;c<2;c++){double v=sum[c]*.65;if(v>32767)v=32767;if(v<-32768)v=-32768;out[f*2+c]=(int16_t)v;}
    }
}
