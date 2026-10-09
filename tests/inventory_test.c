#include "playtest.h"
#include "progression.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
static void tick(TombPlaytest *p,unsigned input){if(!tomb_playtest_tick(p,input)){fprintf(stderr,"%s state=%d frame=%d\n",p->status,p->lara.actor.current,p->lara.actor.frame);assert(0);}}
int main(int argc,char **argv){
    assert(argc==4);char err[256];int16_t sine[1025];FILE *f=fopen(argv[2],"rb");assert(f && fread(sine,sizeof sine,1,f)==1);fclose(f);
    TombLevel *l=tomb_level_load(argv[1],err,sizeof err);assert(l);TombVisual *v=tomb_visual_load(l,err,sizeof err);assert(v);TombObjects w;assert(tomb_objects_init(&w,l,v));TombPlaytest p;
    TombSoundBank bank;assert(tomb_sound_bank_load(&bank,l));TombSoundMixer mixer;tomb_sound_init(&mixer,&bank);
    const int menu_ids[]={108,111,112,113,114};const double origin[3]={0,0,0};int16_t pcm[512];
    for(unsigned i=0;i<sizeof menu_ids/sizeof *menu_ids;i++) {
        tomb_sound_clear(&mixer);TombSoundEvent e={5,menu_ids[i],2,0,0,0};
        unsigned before=mixer.played;tomb_sound_event(&mixer,&e,0,origin);assert(mixer.played==before+1);
        int audible=0;for(int t=0;t<16;t++){tomb_sound_mix(&mixer,pcm,256);for(int j=0;j<512;j++)audible|=pcm[j]!=0;}
        assert(audible);
    }
    tomb_sound_bank_free(&bank);
    for(int large=0;large<2;large++){
        int id=tomb_pickup_fixture(&p,&w,sine,large);assert(id>=0);int collected=0,started=0;
        for(int t=0;t<110;t++){tick(&p,64);started|=p.lara.actor.current==39;if(p.inventory.pickups && !collected){collected=1;assert(p.lara.actor.frame==3443);}}
        printf("pickup %d: state=%d frame=%d count=%d weapon=%d\n",large,p.lara.actor.current,p.lara.actor.frame,p.inventory.counts[large?10:9],p.animation.weapon_status);fflush(stdout);
        assert(p.hud.pickup_id[0]==(large?94:93) && p.hud.pickup_time[0]>0);
        assert(started && collected && p.inventory.pickups==1 && p.inventory.counts[large?10:9]==1 && (w.items[id].actor.flags&6)==6);
        assert(p.lara.actor.current==2 && p.animation.weapon_status==0);
        assert(!tomb_inventory_use(&p.inventory,large?94:93,&p.lara.health));p.lara.health=200;
        assert(tomb_inventory_use(&p.inventory,large?94:93,&p.lara.health));assert(p.lara.health==(large?1000:700));assert(!p.inventory.counts[large?10:9]);
    }
    tomb_objects_reset(&w);assert(tomb_playtest_init(&p,l,sine,v));p.objects=&w;p.movement_only=1;
    const int pos[3][4]={{68096,-2560,50688,28},{89600,1024,37376,36},{14848,6912,94720,37}};
    for(int i=0;i<3;i++){
        p.lara.actor.x=pos[i][0];p.lara.actor.y=pos[i][1];p.lara.actor.z=pos[i][2];p.lara.actor.room=(int16_t)pos[i][3];
        tick(&p,0);assert(w.progress->secrets==((1u<<(i+1))-1));int chime=0;for(unsigned j=0;j<p.sound_count;j++)chime+=p.sounds[j].id==173;assert(chime==1);
        tick(&p,0);assert(w.progress->secret_serial==(unsigned)i+1);
    }
    p.lara.actor.x=42496;p.lara.actor.y=7168;p.lara.actor.z=83456;p.lara.actor.room=11;tick(&p,0);assert(w.progress->complete);
    TombActor stopped=p.lara.actor;for(int t=0;t<30;t++)tick(&p,1);assert(p.lara.actor.x==stopped.x && p.lara.actor.z==stopped.z);
    TombInventory carry=p.inventory;tomb_inventory_add(&carry,93);tomb_inventory_add(&carry,89);
    tomb_objects_free(&w);tomb_visual_free(v);tomb_level_free(l);
    l=tomb_level_load(argv[3],err,sizeof err);assert(l);v=tomb_visual_load(l,err,sizeof err);assert(v);assert(tomb_objects_init(&w,l,v));assert(tomb_playtest_init(&p,l,sine,v));p.objects=&w;p.movement_only=1;p.inventory=carry;
    for(int t=0;t<120;t++)tick(&p,t<60?1:0);assert(p.inventory.counts[9]==1 && p.inventory.counts[5]==1 && !w.progress->complete && !w.progress->secrets);
    tomb_objects_free(&w);tomb_visual_free(v);tomb_level_free(l);
    puts("PASS: pickup frame, one-shot collection, animation recovery, medipack use, three secrets/chimes, completion freeze and City initialization");return 0;
}
