#include "enemies.h"
#include "pistols.h"
#include "hazards.h"
#include "fixed.h"
#include "object_contact.h"
#include <stdlib.h>
#include <string.h>
int tomb_enemy_object(int id){return id>=7 && id<=9;}
static int slot(const TombEnemies *e,size_t id){for(int k=0;k<8;k++)if(e->slots[k]==(int)id)return k;return -1;}
static int32_t distance(const TombEnemies *e,const TombActor *a) {
    int32_t x=tomb_asr(a->x-e->camera[0],8),y=tomb_asr(a->y-e->camera[1],8),z=tomb_asr(a->z-e->camera[2],8);
    return tomb_long((int64_t)x*x+(int64_t)y*y+(int64_t)z*z);
}
int tomb_enemies_activate(TombObjects *w,size_t id,int always) {
    TombEnemies *e=w->enemies;if(!e || id>=w->count || !tomb_enemy_object(w->items[id].object))return 0;
    if(slot(e,id)>=0)return 1;
    int use=-1;for(int k=0;k<8;k++)if(e->slots[k]<0){use=k;break;}
    if(use<0) {
        int32_t far=always?0:distance(e,&w->items[id].actor);
        for(int k=0;k<8;k++){int32_t d=distance(e,&w->items[e->slots[k]].actor);if(d>far){far=d;use=k;}}
        if(use<0)return 0;
        w->items[e->slots[use]].actor.flags|=6;tomb_navigation_free(e->navigation+use);e->slots[use]=-1;
    }
    TombCreature *c=e->items+id;c->head=c->flags=0;c->maximum_turn=182;c->mood=0;
    if(!tomb_navigation_init(e->navigation+use,w->level,&w->items[id].actor,w->items[id].object))return 0;
    e->slots[use]=(int)id;return 1;
}
static void add(TombObjects *w,size_t id) {
    TombEnemies *e=w->enemies;
    for(int at=e->head;at>=0;at=e->next[at])if(at==(int)id)return;
    e->next[id]=e->head;e->head=(int)id;w->items[id].active=1;w->items[id].actor.flags|=1;
}
void tomb_enemies_room_sync(TombObjects *w) {
    TombEnemies *e=w->enemies;if(!e)return;
    for(size_t id=0;id<w->count;id++) {
        int room=w->items[id].actor.room,old=e->room_id[id];if(room==old || room<0 || (size_t)room>=w->level->room_count)continue;
        int *link=e->room_head+old;while(*link>=0 && *link!=(int)id)link=e->room_next+*link;
        if(*link==(int)id)*link=e->room_next[id];
        e->room_next[id]=e->room_head[room];e->room_head[room]=(int)id;e->room_id[id]=room;
    }
}
void tomb_enemies_trigger(TombObjects *w,size_t id,int type,uint16_t flags) {
    TombObject *o=w->items+id;uint8_t before=o->actor.flags;int active=o->active;
    tomb_object_trigger(o,type,flags);
    if(active || !o->active)return;
    o->active=0;o->actor.flags=before;
    if((before&6)==0){o->actor.flags=(before&~6u)|2;w->enemies->items[id].touch=0;add(w,id);tomb_enemies_activate(w,id,1);}
    else if((before&6)==6){w->enemies->items[id].touch=0;if(tomb_enemies_activate(w,id,0))o->actor.flags=(before&~6u)|2;add(w,id);}
}
void tomb_enemies_reset(TombObjects *w) {
    TombEnemies *e=w->enemies;if(!e)return;
    for(int k=0;k<8;k++){tomb_navigation_free(e->navigation+k);e->slots[k]=-1;}
    e->head=-1;e->random=(uint32_t)-747505337;memset(e->items,0,w->count*sizeof *e->items);
    for(size_t j=0;j<w->level->room_count;j++)e->room_head[j]=-1;
    for(size_t j=0;j<w->count;j++) {
        e->next[j]=-1;TombObject *o=w->items+j;int room=o->actor.room;
        e->room_id[j]=room;e->room_next[j]=e->room_head[room];e->room_head[room]=(int)j;
        if(!tomb_enemy_object(o->object))continue;
        TombCreature *c=e->items+j;c->health=o->object==7?6:o->object==8?20:1;
        o->actor.yaw=tomb_word((int)o->actor.yaw+tomb_asr((int)tomb_control_random(&e->random)-16384,1));
        if(o->object==7)o->actor.frame=96;
        TombSectorRef ref;TombHeights h;if(tomb_find_sector(w->level,o->actor.x,o->actor.y,o->actor.z,o->actor.room,&ref) && tomb_static_heights(w->level,ref,o->actor.x,o->actor.z,0,&h))c->floor=h.floor;
        if(o->active){add(w,j);tomb_enemies_activate(w,j,1);}
    }
}
int tomb_enemies_init(TombObjects *w) {
    TombEnemies *e=calloc(1,sizeof *e);if(!e)return 0;w->enemies=e;
    e->items=calloc(w->count,sizeof *e->items);e->next=calloc(w->count,sizeof *e->next);
    e->room_head=calloc(w->level->room_count,sizeof(int));e->room_next=calloc(w->count,sizeof(int));e->room_id=calloc(w->count,sizeof(int));
    if(!e->items || !e->next || !e->room_head || !e->room_next || !e->room_id){tomb_enemies_free(w);return 0;}
    tomb_enemies_reset(w);return 1;
}
void tomb_enemies_free(TombObjects *w) {
    TombEnemies *e=w->enemies;if(!e)return;for(int k=0;k<8;k++)tomb_navigation_free(e->navigation+k);
    free(e->items);free(e->next);free(e->room_head);free(e->room_next);free(e->room_id);free(e);w->enemies=NULL;
}
int tomb_enemies_tick(TombObjects *w,TombAnimContext *ctx,TombLaraStart *lara) {
    TombEnemies *e=w->enemies;if(!e)return 1;
    tomb_enemies_room_sync(w);
    int previous=-1,index=e->head;
    while(index>=0) {
        TombObject *o=w->items+index;TombCreature *c=e->items+index;int next=e->next[index];
        if((o->actor.flags&6)==6) {
            if(!tomb_enemies_activate(w,(size_t)index,0)){previous=index;index=next;continue;}
            o->actor.flags=(o->actor.flags&~6u)|2;
        }
        int k=slot(e,(size_t)index);if(k<0){previous=index;index=next;continue;}
        TombNavigation *n=e->navigation+k;TombCreatureInfo info={0};int16_t turn=0;
        if(c->health>0) {
            int16_t bounds[6];if(!tomb_visual_bounds(w->visual,&lara->actor,bounds))return 0;
            tomb_creature_info(&info,c,n,w->level,&o->actor,o->object,&lara->actor,ctx->sine_quarter);
            tomb_creature_mood(c,n,w->level,&o->actor,o->object,&info,&lara->actor,lara->health,lara->water_status,bounds[2],&e->random);
            turn=tomb_creature_turn(&o->actor,c,o->object==9?3640:c->maximum_turn);
        } else if(o->object==8)turn=tomb_creature_turn(&o->actor,c,182);
        TombCreatureDecision d=tomb_creature_control(o,c,&info,turn,lara->health,&e->random,ctx);
        if(d.damage){lara->health=tomb_word(lara->health-d.damage);lara->actor.flags|=16;}
        if(d.blood){
            int32_t bite[3]={0,o->object==7?-14:o->object==8?96:16,o->object==7?174:o->object==8?335:45};
            if(!tomb_object_joint(w->visual,o->object,&o->actor,c->pitch,c->roll,c->head,o->object==7?6:o->object==8?14:4,bite,ctx->sine_quarter))return 0;
            TombActor point=o->actor;point.x=bite[0];point.y=bite[1];point.z=bite[2];tomb_effect_spawn(w,158,&point,o->actor.speed,o->actor.yaw);
        }
        int moved=tomb_creature_move(o,c,n,w,ctx,d.turn,d.tilt);if(moved<0)return 0;
        tomb_enemies_room_sync(w);
        w->level->items[index].state=o->actor.current;
        if(!moved){tomb_navigation_free(n);e->slots[k]=-1;if(previous<0)e->head=next;else e->next[previous]=next;e->next[index]=-1;}
        else previous=index;
        index=next;
    }
    return 1;
}
