/* Original falling block 0x3a728, dart emitter 0x3ac80 and dart 0x3ae20. */
#include "hazards.h"
#include "enemies.h"
#include "pistols.h"
#include "object_contact.h"
#include "fixed.h"
#include <stdlib.h>
#include <string.h>
int tomb_hazard_sine(const int16_t *s,int angle) {
    unsigned a=(unsigned)angle&65535;int negative=a>=32768;if(negative)a-=32768;if(a>16384)a=32768-a;
    return negative?-s[a>>4]:s[a>>4];
}
int tomb_hazard_sprite(const TombVisual *v,int id,int frame,int *count) {
    const unsigned char *p=v->sprite_textures+16*v->sprite_texture_count,*end=v->level->file_data+v->level->file_size;
    if(p+4>end)return -1;unsigned n=p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24;p+=4;
    if(n>(size_t)(end-p)/8)return -1;
    for(unsigned i=0;i<n;i++,p+=8) {
        unsigned ident=p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24;
        if(ident!=(unsigned)id)continue;
        int frames=-tomb_word(p[4]|p[5]<<8),start=p[6]|p[7]<<8;
        if(frames<=0 || frame<0 || frame>=frames || (size_t)(start+frame)>=v->sprite_texture_count)return -1;
        if(count)*count=frames;return start+frame;
    }
    return -1;
}
void tomb_hazard_effect_tick(TombHazardEffect *e,int frames,const int16_t *sine) {
    if(!e->active)return;
    if(e->id==164){if(!--e->counter)e->active=0;return;}
    if(e->id==158){e->x+=tomb_asr(e->speed*tomb_hazard_sine(sine,e->yaw),14);e->z+=tomb_asr(e->speed*tomb_hazard_sine(sine,e->yaw+16384),14);}
    if(++e->counter>=(e->id==158?4:3)){e->counter=0;if(++e->frame>=frames)e->active=0;}
}
int tomb_effect_spawn(TombObjects *w,int id,const TombActor *a,int speed,int yaw) {
    int frames;if(tomb_hazard_sprite(w->visual,id,0,&frames)<0)return -1;
    for(int i=0;i<256;i++)if(!w->hazards->effects[i].active) {
        TombHazardEffect e={a->x,a->y,a->z,a->room,(int16_t)id,0,0,(int16_t)speed,(int16_t)yaw,1};
        if(id==164){w->hazards->random=w->hazards->random*1103515245u+12345u;e.frame=(int)((w->hazards->random>>10)&32767)*3/32768;e.counter=6;}
        w->hazards->effects[i]=e;return i;
    }
    return -1;
}
/* Pendulum controller 0x3a5d8; contacts are from the preceding Lara pass. */
int tomb_blade_control(TombObject *o,uint32_t touch){
 if(tomb_trigger_active(o)){if(o->actor.current==0)o->actor.goal=2;}
 else if(o->actor.current==2)o->actor.goal=0;
 return o->actor.current==2 && touch?100:0;
}
static int blade_random(TombHazards *h){h->random=h->random*1103515245u+12345u;return (int)((h->random>>10)&32767);}
int tomb_floor_control(TombObject *o,int32_t y) {
    if(o->actor.current==0){if(y!=o->actor.y-512){o->active=0;o->actor.flags&=(uint8_t)~7u;return 0;}o->actor.goal=1;}
    else if(o->actor.current==1)o->actor.goal=2;
    else if(o->actor.current==2 && o->actor.goal!=3)o->actor.flags|=8;
    return 1;
}
int tomb_dart_emit(TombObject *o,const TombAnimContext *c,TombActor *out) {
    if(tomb_trigger_active(o)){if(o->actor.current==0)o->actor.goal=1;}
    else if(o->actor.current==1)o->actor.goal=0;
    const TombActor *a=&o->actor;
    if(a->current!=1 || a->animation<0 || (size_t)a->animation>=c->animation_count || a->frame!=c->animations[a->animation].first_frame)return 0;
    *out=(TombActor){0};out->x=a->x;out->y=a->y-512;out->z=a->z;out->yaw=a->yaw;out->room=a->room;
    /* Retain DOS's 0x3fec (+89.89 degree) special case, not 0x4000. */
    if(a->yaw==0)out->z-=412;else if(a->yaw==16364)out->x-=412;else if(a->yaw==-32768)out->z+=412;else if(a->yaw==-16384)out->x+=412;
    return 1;
}
static int floor_at(TombObjects *w,TombActor *a,int32_t *height) {
    TombSectorRef ref;TombHeights h;
    if(!tomb_find_sector(w->level,a->x,a->y,a->z,a->room,&ref) || !tomb_item_heights(w->level,ref,a->x,a->y,a->z,0,w->level->items,w->count,&h))return 0;
    a->room=(int16_t)ref.room;*height=h.floor;return 1;
}
int tomb_hazards_tick(TombObjects *w,TombAnimContext *c,TombActor *lara,int16_t *health) {
    if(!w->hazards)return 1;
    for(int i=0;i<256;i++){TombHazardEffect *e=w->hazards->effects+i;int frames;
        if(e->active && e->id==166){if(!--e->counter)e->active=0;else e->speed=(int16_t)tomb_control_random(&w->enemies->random);}
        else if(e->active && tomb_hazard_sprite(w->visual,e->id,e->frame,&frames)>=0)tomb_hazard_effect_tick(e,frames,c->sine_quarter);
    }
    /* New darts enter the active list at its head, and first move next tick. */
    for(int i=TOMB_DART_CAPACITY-1;i>=0;i--) {
        TombDart *d=w->hazards->darts+i;if(!d->item.active)continue;
        if(d->touching){*health=tomb_word(*health-50);lara->flags|=16;w->hazards->hits++;tomb_effect_spawn(w,158,&d->item.actor,lara->speed,lara->yaw);}d->touching=0;
        if(!tomb_object_animate(&d->item,c))return 0;
        int32_t floor;if(!floor_at(w,&d->item.actor,&floor))return 0;
        if(d->item.actor.y>=floor){d->item.active=0;w->hazards->impacts++;tomb_effect_spawn(w,164,&d->item.actor,0,0);}
    }
    for(size_t i=0;i<w->count;i++) {
        TombObject *o=w->items+i;if(!o->active)continue;
        if(o->object==36){
            int damage=tomb_blade_control(o,w->enemies->items[i].touch);w->enemies->items[i].touch=0;
            if(damage){*health=tomb_word(*health-damage);lara->flags|=16;++w->hazards->hits;
                TombActor blood=*lara;blood.x+=(blade_random(w->hazards)-16384)/256;blood.z+=(blade_random(w->hazards)-16384)/256;blood.y-=blade_random(w->hazards)/44;
                int yaw=tomb_word(lara->yaw+(blade_random(w->hazards)-16384)/8);tomb_effect_spawn(w,158,&blood,lara->speed,yaw);
            }
            int32_t floor;if(!floor_at(w,&o->actor,&floor) || !tomb_object_animate(o,c))return 0;
            w->level->items[i].state=o->actor.current;
        } else if(o->object==35) {
            if(!tomb_floor_control(o,lara->y))continue;
            if(!tomb_object_animate(o,c))return 0;
            w->level->items[i].state=o->actor.current;
            if((o->actor.flags&6)==4){o->active=0;o->actor.flags&=(uint8_t)~1u;}
            else {int32_t floor;if(!floor_at(w,&o->actor,&floor))return 0;
                if(o->actor.current==2 && o->actor.y>=floor){o->actor.goal=3;o->actor.y=floor;o->actor.fall_speed=0;o->actor.flags&=(uint8_t)~8u;}}
            w->level->items[i].state=o->actor.current;
        } else if(o->object==40) {
            TombActor a;
            if(tomb_dart_emit(o,c,&a))for(int j=0;j<TOMB_DART_CAPACITY;j++)if(!w->hazards->darts[j].item.active) {
                TombModel model;if(!tomb_visual_model(w->visual,39,&model))return 0;
                a.animation=(int16_t)model.animation;a.frame=c->animations[a.animation].first_frame;a.current=a.goal=c->animations[a.animation].state;a.flags=35;
                TombDart *d=w->hazards->darts+j;memset(d,0,sizeof *d);d->item=(TombObject){a,0,0,39,1};w->hazards->spawned++;
                tomb_effect_spawn(w,160,&a,0,0);if(c->event)c->event(c->user,5,151,&a);break;
            }
            if(!tomb_object_animate(o,c))return 0;
        }
    }
    return 1;
}
int tomb_hazards_contact(TombObjects *w,TombActor *a,TombContact *c,TombAnimContext *ctx,int16_t pitch,int16_t roll,TombQuery query,void *user) {
    if(!w->hazards)return 1;
    TombPose lp;if(!tomb_object_pose(w->visual,a,&lp))return 0;
    TombSphere ls[64];int ln=tomb_object_spheres(w->visual,0,a,pitch,roll,ctx->sine_quarter,ls);if(!ln)return 0;
    for(int i=0;i<TOMB_DART_CAPACITY;i++) {
        TombDart *d=w->hazards->darts+i;TombActor *o=&d->item.actor;if(!d->item.active)continue;
        int nearby=o->room==a->room;
        const TombRoomPortals *p=w->visual->portals+a->room;
        for(size_t j=0;j<p->count;j++){const unsigned char *r=p->data+j*32;if(o->room==(r[0]|r[1]<<8))nearby=1;}
        if(!nearby || llabs((long long)a->x-o->x)>=4096 || llabs((long long)a->z-o->z)>=4096 || llabs((long long)a->y-o->y)>=4096)continue;
        TombPose pose;if(!tomb_object_pose(w->visual,o,&pose))return 0;
        if(a->y+lp.bounds[2]>=o->y+pose.bounds[3] || o->y+pose.bounds[2]>=a->y+lp.bounds[3])continue;
        int dx=a->x-o->x,dz=a->z-o->z,si=tomb_hazard_sine(ctx->sine_quarter,o->yaw),co=tomb_hazard_sine(ctx->sine_quarter,o->yaw+16384);
        int x=tomb_asr(dx*co-dz*si,14),z=tomb_asr(dz*co+dx*si,14);
        if(x<pose.bounds[0]-100 || x>pose.bounds[1]+100 || z<pose.bounds[4]-100 || z>pose.bounds[5]+100)continue;
        TombSphere ds[64];int dn=tomb_object_spheres(w->visual,39,o,0,0,ctx->sine_quarter,ds);if(!dn)return 0;
        for(int j=0;j<dn;j++)for(int k=0;k<ln;k++) {
            int64_t xx=ds[j].x-ls[k].x,yy=ds[j].y-ls[k].y,zz=ds[j].z-ls[k].z,rr=ds[j].radius+ls[k].radius;
            if(ds[j].radius>0 && ls[k].radius>0 && xx*xx+yy*yy+zz*zz<rr*rr)d->touching=1;
        }
        if(!d->touching || !(c->flags&8) || !tomb_object_push(o,pose.bounds,a,100,ctx->sine_quarter))continue;
        int16_t facing=c->facing;c->positive_limit=32512;c->negative_limit=-384;c->ceiling_limit=0;
        c->facing=tomb_object_angle(a->z-c->old_z,a->x-c->old_x);query(user,a,c,762);c->facing=facing;
        if(c->type){a->x=c->old_x;a->z=c->old_z;}else {c->old_x=a->x;c->old_y=a->y;c->old_z=a->z;TombSectorRef r;if(tomb_find_sector(w->level,a->x,a->y-10,a->z,a->room,&r))a->room=(int16_t)r.room;}
    }
    return 1;
}
