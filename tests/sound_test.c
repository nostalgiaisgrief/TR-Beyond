#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "playtest.h"
#include "sound_win.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned heard[256],bubbles,stops;
static size_t frames_written;
static void tick(TombPlaytest *p,TombSoundMixer *m,unsigned input,FILE *wav) {
    assert(tomb_playtest_tick(p,input));assert(!p->blocked);
    double listener[3]={p->lara.actor.x,p->lara.actor.y-450,p->lara.actor.z};
    /* A dry listener hears water entry before the following camera enters. */
    int wet=p->lara.water_status==1;
    for(unsigned i=0;i<p->sound_count;i++) {
        TombSoundEvent *e=p->sounds+i;
        if(e->kind==5 && e->id>=0 && e->id<256)heard[e->id]++;
        if(e->kind==6)bubbles++;
        if(e->kind==7)stops++;
        tomb_sound_event(m,e, e->id==33?0:wet,listener);
    }
    int16_t pcm[1470*2];tomb_sound_mix(m,pcm,1470);
    if(wav){assert(fwrite(pcm,sizeof pcm,1,wav)==1);frames_written+=1470;}
}
static void word(FILE *f,unsigned v){fputc(v&255,f);fputc((v>>8)&255,f);}
static void dword(FILE *f,unsigned v){word(f,v&65535);word(f,v>>16);}
static void header(FILE *f,unsigned frames){rewind(f);fwrite("RIFF",4,1,f);dword(f,36+frames*4);fwrite("WAVEfmt ",8,1,f);dword(f,16);word(f,1);word(f,2);dword(f,44100);dword(f,176400);word(f,4);word(f,16);fwrite("data",4,1,f);dword(f,frames*4);}
int main(int argc,char **argv) {
    assert(argc==5 || argc==6);char error[256];int16_t sine[1025];
    TombLevel *l=tomb_level_load(argv[1],error,sizeof error);assert(l);
    TombSoundBank bank;assert(tomb_sound_bank_load(&bank,l));assert(bank.sample_count==76 && bank.detail_count==69);
    for(size_t i=0;i<bank.sample_count;i++)assert(bank.samples[i].rate>0 && bank.samples[i].bits==8 && bank.samples[i].channels==1);
    /* Malformed/truncated audio is rejected atomically. */
    size_t original_size=l->file_size;TombSoundBank bad;
    for(size_t n=l->item_parsed_bytes;n<original_size;n+=9973){l->file_size=n;assert(!tomb_sound_bank_load(&bad,l));}
    l->file_size=original_size;
    TombVisual *v=tomb_visual_load(l,error,sizeof error);assert(v);
    FILE *f=fopen(argv[2],"rb");assert(f && fread(sine,sizeof sine,1,f)==1);fclose(f);
    TombSoundMixer m;tomb_sound_init(&m,&bank);TombPlaytest p;
    FILE *wav=fopen(argv[3],"wb");assert(wav);header(wav,0);
    for(int mode=0;mode<3;mode++) {
        assert(tomb_playtest_init(&p,l,sine,v));tomb_sound_clear(&m);
        p.lara.actor.x=50688;p.lara.actor.y=0;p.lara.actor.z=46592;p.lara.actor.room=9;p.lara.actor.yaw=-32768;
        for(int t=0;t<120;t++)tick(&p,&m,mode==0?(t<45?129:0):mode==1?(t<45?1:0):(t<12?16:0),wav);
    }
    assert(tomb_playtest_init(&p,l,sine,v));tomb_sound_clear(&m);
    p.lara.actor.x=50076;p.lara.actor.y=2560;p.lara.actor.z=39424;p.lara.actor.room=9;p.lara.actor.yaw=16384;
    for(int t=0;t<15;t++)tick(&p,&m,80,wav);
    for(int t=0;t<60;t++)tick(&p,&m,64,wav);
    assert(p.lara.actor.current==10);
    for(int t=0;t<120;t++)tick(&p,&m,p.lara.actor.current==2?0:65,wav);
    assert(p.lara.actor.current==2 && p.lara.actor.y<2560);
    assert(tomb_playtest_init(&p,l,sine,v));tomb_sound_clear(&m);
    p.lara.actor.x=46592;p.lara.actor.y=-6000;p.lara.actor.z=41472;p.lara.actor.room=9;
    p.lara.actor.current=p.lara.actor.goal=9;p.lara.actor.animation=93;p.lara.actor.frame=1473;p.lara.actor.flags|=8;p.lara.actor.fall_speed=154;
    for(int t=0;t<100;t++)tick(&p,&m,0,wav);
    assert(p.lara.health<=0 && heard[30]>0 && stops>0);
    assert(heard[0]>0); /* Original footstep animation commands. */
    assert(tomb_playtest_init(&p,l,sine,v));tomb_sound_clear(&m);
    p.lara.actor.x=40448;p.lara.actor.y=3328;p.lara.actor.z=57800;p.lara.actor.room=13;p.lara.actor.yaw=0;
    for(int t=0;t<530;t++){unsigned in=p.lara.water_status==0?(t<35?1:0):p.lara.water_status==1?18:65;tick(&p,&m,in,wav);}
    /* Both entry/surface services and first animation frames request the sound; mode 0 prevents duplicate playback. */
    assert(p.gym.complete && heard[33]==2 && heard[36]==2 && bubbles>0);
    header(wav,(unsigned)frames_written);fclose(wav);
    FILE *report=fopen(argv[4],"w");assert(report);fprintf(report,"events:");for(int i=0;i<256;i++)if(heard[i])fprintf(report," %d=%u",i,heard[i]);fprintf(report,"\nbubble effects: %u\nplayed: %u\ndropped: %u\n",bubbles,m.played,m.dropped);fclose(report);assert(!m.dropped);
    double listener[3]={0,0,0};TombSoundEvent e={5,30,2,0,0,0};
    tomb_sound_clear(&m);tomb_sound_event(&m,&e,0,listener);unsigned first=m.played;
    tomb_sound_event(&m,&e,0,listener);assert(m.played==first); /* Mode 0 waits; no per-tick scream restart. */
    e.id=0;tomb_sound_event(&m,&e,0,listener);first=m.played;tomb_sound_event(&m,&e,0,listener);assert(m.played==first+1); /* Mode 1 restarts. */
    unsigned active=0;for(int i=0;i<TOMB_SOUND_CHANNELS;i++)active+=m.voices[i].active;assert(active==2);
    e.kind=7;e.id=30;tomb_sound_event(&m,&e,0,listener);for(int i=0;i<TOMB_SOUND_CHANNELS;i++)assert(!m.voices[i].active || m.voices[i].id!=30);
    tomb_sound_clear(&m);int16_t pcm[256*2];tomb_sound_mix(&m,pcm,256);for(int i=0;i<512;i++)assert(!pcm[i]);
    /* Original menu events produce PCM independently of the suspended world mixer. */
    TombSoundMixer ui;tomb_sound_init(&ui,&bank);
    const int menu_ids[]={108,111,112,113,114};
    for(unsigned n=0;n<sizeof menu_ids/sizeof *menu_ids;n++) {
        tomb_sound_clear(&ui);e=(TombSoundEvent){5,menu_ids[n],2,0,0,0};
        if(e.id==114 && bank.map[e.id]<0)continue; /* Gym has no weapon-selection sample. */
        unsigned played=ui.played;tomb_sound_event(&ui,&e,1,listener);assert(ui.played==played+1);
        int audible=0;for(int t=0;t<16;t++){tomb_sound_mix(&ui,pcm,256);for(int j=0;j<512;j++)audible|=pcm[j]!=0;}
        assert(audible);
    }
    assert(tomb_playtest_init(&p,l,sine,v));p.lara.actor.current=60;assert(!tomb_playtest_tick(&p,1) && !p.sound_count);
    if(argc==6) {
        TombSoundOutput *o=tomb_sound_output_open(&m);assert(o);
        assert(tomb_sound_output_update(o,0));
        Sleep(300);TombSoundOutputStats before=tomb_sound_output_stats(o);
        /* No render-thread update for three seconds: audio must keep feeding. */
        LARGE_INTEGER q0,q1,freq;QueryPerformanceFrequency(&freq);QueryPerformanceCounter(&q0);Sleep(3000);QueryPerformanceCounter(&q1);TombSoundOutputStats after=tomb_sound_output_stats(o);
        fprintf(stderr,"thread feed: blocks %u -> %u, starvations %u -> %u\n",before.blocks,after.blocks,before.starvations,after.starvations);
        fprintf(stderr,"elapsed %.4f samples %u -> %u\n",(double)(q1.QuadPart-q0.QuadPart)/freq.QuadPart,before.played_samples,after.played_samples);
        assert(after.blocks>=before.blocks+120 && after.played_samples-before.played_samples>=(unsigned)(44100*(double)(q1.QuadPart-q0.QuadPart)/freq.QuadPart)-1024 && after.starvations==before.starvations);
        assert(tomb_sound_output_update(o,1));before=tomb_sound_output_stats(o);
        Sleep(100);after=tomb_sound_output_stats(o);assert(after.blocks==before.blocks);
        TombSoundOutput *menu=tomb_sound_output_open(&ui);assert(menu);
        e=(TombSoundEvent){5,111,2,0,0,0};tomb_sound_output_event(menu,&e,0,listener);
        assert(tomb_sound_output_update(menu,0));Sleep(150);
        assert(tomb_sound_output_stats(menu).played_samples>0);
        assert(tomb_sound_output_stats(o).blocks==before.blocks);
        tomb_sound_output_close(menu);
        assert(tomb_sound_output_update(o,1));
        tomb_sound_output_reset(o);assert(tomb_sound_output_update(o,0));
        e.kind=5;e.id=0;tomb_sound_output_event(o,&e,0,listener);
        Sleep(100);assert(tomb_sound_output_update(o,1));tomb_sound_output_reset(o);
        tomb_sound_output_close(o);
        puts("PASS: native waveOut thread survives 3s render stall with no starvation; pause/resume/reset/close");
    }
    tomb_sound_bank_free(&bank);tomb_visual_free(v);tomb_level_free(l);
    puts("PASS: embedded PCM bank, malformed data, movement/pool sound events, mixing, simultaneous voices, repeat/stop/reset and rollback");return 0;
}
