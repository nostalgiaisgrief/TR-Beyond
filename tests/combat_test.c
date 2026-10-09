#include "playtest.h"
#include "combat.h"
#include "enemies.h"
#include "hazards.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
static void tick(TombPlaytest *p,unsigned input) {
    if(!tomb_playtest_tick(p,input)){fprintf(stderr,"blocked: %s state=%d\n",p->status,p->lara.actor.current);assert(0);}
}
int main(int argc,char **argv) {
    assert(argc==3);char error[256];int16_t sine[1025];FILE *f=fopen(argv[2],"rb");assert(f && fread(sine,sizeof sine,1,f)==1);fclose(f);
    TombLevel *l=tomb_level_load(argv[1],error,sizeof error);assert(l);TombVisual *v=tomb_visual_load(l,error,sizeof error);assert(v);
    TombObjects w;assert(tomb_objects_init(&w,l,v));TombPlaytest p;
    for(int armed=0;armed<2;armed++) {
        tomb_objects_reset(&w);assert(tomb_playtest_init(&p,l,sine,v));p.objects=&w;p.movement_only=1;
        if(armed){tick(&p,32);for(int t=0;t<24;t++)tick(&p,0);assert(p.pistols.status==4);}
        TombActor start=p.lara.actor;
        for(int t=0;t<30;t++)tick(&p,512|8|1);
        assert(p.camera_request.flags==512 && p.lara.head_yaw==8008 && p.lara.head_pitch==-7644);
        assert(p.lara.actor.x==start.x && p.lara.actor.z==start.z && p.lara.actor.yaw==start.yaw);
        for(int t=0;t<70;t++)tick(&p,0);
        assert(!p.lara.head_yaw && !p.lara.head_pitch && p.camera_request.flags!=512);
        tick(&p,4096);assert(p.lara.actor.current==45);
        for(int t=0;t<60;t++)tick(&p,0);
        assert(p.lara.actor.current==2 && (uint16_t)(p.lara.actor.yaw-start.yaw)==32768);
        for(int t=0;t<12;t++)tick(&p,1);
        assert(p.lara.actor.current==1);tick(&p,4096|1);assert(p.lara.actor.current==45);
        for(int t=0;t<60;t++)tick(&p,0);assert(p.lara.actor.current==2);
    }
    for(int species=7;species<=9;species++) {
        int id=tomb_combat_fixture(&p,&w,sine,species);assert(id>=0);
        printf("fixture %d enemy=%d Lara=%d,%d,%d room=%d\n",species,id,p.lara.actor.x,p.lara.actor.y,p.lara.actor.z,p.lara.actor.room);fflush(stdout);
        int initial=w.enemies->items[id].health,fire_sound=0,combat_camera=0,damage=0;
        tick(&p,32);
        for(int t=0;t<900;t++) {
            tick(&p,64);combat_camera|=(p.camera_request.flags&TOMB_CAMERA_COMBAT)!=0;
            for(unsigned j=0;j<p.sound_count;j++)fire_sound+=p.sounds[j].id==8;
            if(w.enemies->items[id].health<=0 && !w.items[id].active)break;
        }
        printf("combat %d hits=%u kills=%u enemy_hp=%d active=%d Lara_hp=%d shots=%u\n",species,p.pistols.hits,p.pistols.kills,w.enemies->items[id].health,w.items[id].active,p.lara.health,p.pistols.shots);fflush(stdout);
        assert(p.pistols.hits>=(unsigned)initial && p.pistols.kills>=1 && combat_camera && fire_sound);
        assert(w.enemies->items[id].health<=0 && !w.items[id].active);
        tick(&p,32);for(int t=0;t<40;t++)tick(&p,0);assert(p.pistols.status==0 && !p.pistols.drawn);
        id=tomb_combat_fixture(&p,&w,sine,species);assert(id>=0);
        for(int t=0;t<1800 && p.lara.health>0;t++){tick(&p,0);damage=1000-p.lara.health;}
        printf("attacks %d damage=%d\n",species,damage);fflush(stdout);assert(damage>0);
        tomb_objects_reset(&w);assert(w.enemies->head==-1 && w.enemies->items[id].health==initial);
    }
    /* More than eight activated creatures exercises original AI slot eviction. */
    assert(tomb_combat_fixture(&p,&w,sine,7)>=0);
    for(size_t id=0;id<w.count;id++)if(tomb_enemy_object(w.items[id].object))tomb_enemies_trigger(&w,id,0,0x3e00);
    int occupied=0,invisible=0;
    for(int k=0;k<8;k++)occupied+=w.enemies->slots[k]>=0;
    for(size_t id=0;id<w.count;id++)invisible+=tomb_enemy_object(w.items[id].object) && (w.items[id].actor.flags&6)==6;
    assert(occupied==8 && invisible>=6);
    for(int t=0;t<300;t++)tick(&p,t==0?32:64);
    for(int room=0;room<(int)l->room_count;room++) {
        int count=0;for(int id=w.enemies->room_head[room];id>=0;id=w.enemies->room_next[id]){assert(++count<=(int)w.count);assert(w.items[id].actor.room==room);}
    }
    tomb_objects_free(&w);tomb_visual_free(v);tomb_level_free(l);
    puts("PASS: Caves weapon draw/aim/fire/holster, combat camera, wolf/bear/bat hits/deaths/attacks and reset");return 0;
}
