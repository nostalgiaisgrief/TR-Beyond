/* Pistol targeting and FireWeapon 0x2a8c0..0x2b130. */
#include "combat.h"
#include "playtest.h"
#include "enemies.h"
#include "object_contact.h"
#include "hazards.h"
#include "fixed.h"
#include <limits.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
void tomb_gun_angles(int32_t x,int32_t y,int32_t z,int16_t out[2]) {
    out[0]=tomb_object_angle(z,x);
    while(x!=(int16_t)x || y!=(int16_t)y || z!=(int16_t)z){x=tomb_asr(x,2);y=tomb_asr(y,2);z=tomb_asr(z,2);}
    int32_t horizontal=(int32_t)sqrt((double)((int64_t)x*x+(int64_t)z*z));
    int16_t pitch=tomb_object_angle(horizontal,y);if((y>0 && pitch>0) || (y<0 && pitch<0))pitch=tomb_word(-(int)pitch);out[1]=pitch;
}
int tomb_gun_target_point(const TombVisual *v,const TombActor *a,const int16_t *s,TombCameraPoint *p) {
    TombPose pose;if(!tomb_object_pose(v,a,&pose))return 0;
    int x=(pose.bounds[0]+pose.bounds[1])/2,z=(pose.bounds[4]+pose.bounds[5])/2;
    int si=tomb_hazard_sine(s,a->yaw),co=tomb_hazard_sine(s,a->yaw+16384);
    *p=(TombCameraPoint){a->x+tomb_asr(x*co+z*si,14),a->y+pose.bounds[2]+(pose.bounds[3]-pose.bounds[2])/3,a->z+tomb_asr(z*co-x*si,14),a->room};return 1;
}
static int gun_ray(int scatter,const TombVisual *v,const TombObject *o,const TombCreature *c,TombCameraPoint origin,int16_t yaw,int16_t pitch,uint32_t *random,const int16_t *s,TombCameraPoint *hit) {
    pitch=tomb_word((int)pitch+((int)tomb_control_random(random)-16384)*scatter/65536);
    yaw=tomb_word((int)yaw+((int)tomb_control_random(random)-16384)*scatter/65536);
    int32_t p[3]={origin.x,origin.y,origin.z};TombSphere spheres[64];
    int count=o?tomb_object_spheres_view(v,o->object,&o->actor,c->pitch,c->roll,c->head,p,yaw,pitch,s,spheres):0;
    int distance=INT_MAX;
    for(int i=0;i<count;i++) {
        TombSphere b=spheres[i];if(abs(b.x)>=b.radius || abs(b.y)>=b.radius || b.z<=b.radius)continue;
        if((int64_t)b.x*b.x+(int64_t)b.y*b.y<=(int64_t)b.radius*b.radius && b.z-b.radius<distance)distance=b.z-b.radius;
    }
    int found=distance!=INT_MAX;if(!found)distance=16384;
    int sy=tomb_hazard_sine(s,yaw),cy=tomb_hazard_sine(s,yaw+16384),sp=tomb_hazard_sine(s,pitch),cp=tomb_hazard_sine(s,pitch+16384);
    int vx=tomb_asr(cp*sy,14),vy=-sp,vz=tomb_asr(cp*cy,14);
    *hit=(TombCameraPoint){origin.x+tomb_asr(tomb_long((int64_t)distance*vx),14),origin.y+tomb_asr(tomb_long((int64_t)distance*vy),14),origin.z+tomb_asr(tomb_long((int64_t)distance*vz),14),origin.room};return found;
}
int tomb_pistol_ray(const TombVisual *v,const TombObject *o,const TombCreature *c,TombCameraPoint origin,int16_t yaw,int16_t pitch,uint32_t *random,const int16_t *s,TombCameraPoint *hit) {
    return gun_ray(1456,v,o,c,origin,yaw,pitch,random,s,hit);
}
int tomb_shotgun_ray(const TombVisual *v,const TombObject *o,const TombCreature *c,TombCameraPoint origin,int16_t yaw,int16_t pitch,uint32_t *random,const int16_t *s,TombCameraPoint *hit) {
    return gun_ray(0,v,o,c,origin,yaw,pitch,random,s,hit);
}
void tomb_shotgun_spread(uint32_t *random,int16_t yaw,int16_t pitch,int16_t out[2]) {
    out[0]=tomb_word(yaw+((int)tomb_control_random(random)-16384)*3640/65536);
    out[1]=tomb_word(pitch+((int)tomb_control_random(random)-16384)*3640/65536);
}
static void target_info(TombPlaytest *p) {
    TombPistols *g=&p->pistols;TombObjects *w=p->objects;TombActor *a=&p->lara.actor;
    if(g->target<0 || (size_t)g->target>=w->count){g->target=-1;g->left.lock=g->right.lock=0;g->target_yaw=g->target_pitch=0;return;}
    TombCameraPoint target,origin={a->x,a->y-650,a->z,a->room};
    if(!tomb_gun_target_point(p->visual,&w->items[g->target].actor,p->animation.sine_quarter,&target)){g->target=-1;return;}
    int16_t angles[2];tomb_gun_angles(target.x-origin.x,target.y-origin.y,target.z-origin.z,angles);
    int yaw=tomb_word((int)angles[0]-a->yaw),pitch=tomb_word((int)angles[1]-p->lara.pitch);
    if(tomb_dos_camera_los(p->level,&origin,&target,0)) {
        if(yaw>=-10920 && yaw<=10920 && pitch>=-(p->weapon_type==4?10010:10920) && pitch<=(p->weapon_type==4?10010:10920))g->left.lock=g->right.lock=1;
        else if(p->weapon_type==4){if(yaw< -14560 || yaw>14560 || pitch< -11830 || pitch>11830)g->left.lock=g->right.lock=0;}
        else {if(yaw< -30940 || yaw>10920 || pitch< -14560 || pitch>14560)g->left.lock=0;if(yaw< -10920 || yaw>30940 || pitch< -14560 || pitch>14560)g->right.lock=0;}
    } else g->left.lock=g->right.lock=0;
    g->target_yaw=(int16_t)yaw;g->target_pitch=(int16_t)pitch;
}
static void acquire(TombPlaytest *p) {
    TombPistols *g=&p->pistols;TombEnemies *e=p->objects->enemies;TombActor *a=&p->lara.actor;TombCameraPoint origin={a->x,a->y-650,a->z,a->room};
    int best=32767;g->target=-1;
    for(int id=e->head;id>=0;id=e->next[id]) {
        const TombObject *o=p->objects->items+id;if(e->items[id].health<=0)continue;
        int64_t dx=(int64_t)o->actor.x-origin.x,dy=(int64_t)o->actor.y-origin.y,dz=(int64_t)o->actor.z-origin.z;
        if(llabs(dx)>8192 || llabs(dy)>8192 || llabs(dz)>8192 || dx*dx+dy*dy+dz*dz>=8192*8192)continue;
        TombCameraPoint t;if(!tomb_gun_target_point(p->visual,&o->actor,p->animation.sine_quarter,&t) || !tomb_dos_camera_los(p->level,&origin,&t,0))continue;
        int16_t angles[2];tomb_gun_angles(t.x-origin.x,t.y-origin.y,t.z-origin.z,angles);
        int yaw=tomb_word((int)angles[0]-a->yaw-g->torso_yaw),pitch=tomb_word((int)angles[1]-p->lara.pitch-g->torso_pitch);
        if(yaw< -10920 || yaw>10920 || pitch< -(p->weapon_type==4?10010:10920) || pitch>(p->weapon_type==4?10010:10920) || abs(yaw)>=best)continue;
        best=abs(yaw);g->target=id;
    }
    target_info(p);
}
static void sound(void *user,int id) {
    TombPlaytest *p=user;if(p->sound_count>=TOMB_SOUND_EVENTS){p->blocked=1;return;}
    TombActor *a=&p->lara.actor;p->sounds[p->sound_count++]=(TombSoundEvent){5,id,0,a->x,a->y,a->z};++p->sound_events;
}
void tomb_combat_target(TombPlaytest *p,int action) {
    if(action)target_info(p);else p->pistols.target=-1;
    if(p->pistols.target<0)acquire(p);
}
static int fire(void *user,int16_t yaw,int16_t pitch) {
    TombPlaytest *p=user;TombPistols *g=&p->pistols;TombObjects *w=p->objects;TombEnemies *e=w->enemies;TombActor *a=&p->lara.actor;
    TombObject *o=g->target>=0?w->items+g->target:NULL;TombCreature *c=g->target>=0?e->items+g->target:NULL;
    TombCameraPoint origin={a->x,a->y-(p->weapon_type==4?500:650),a->z,a->room},hit;
    int got=gun_ray(p->weapon_type==4?0:1456,p->visual,o,c,origin,tomb_word((int)yaw+a->yaw),pitch,&e->random,p->animation.sine_quarter,&hit);
    if(got){int damage=p->weapon_type==4?4:1;++g->hits;if(c->health>0 && c->health<=damage)++g->kills;c->health=tomb_word(c->health-damage);o->actor.flags|=16;}
    else tomb_dos_camera_los(p->level,&origin,&hit,0);
    TombActor point={0};point.x=hit.x;point.y=hit.y;point.z=hit.z;point.room=got?o->actor.room:hit.room;
    int effect=tomb_effect_spawn(w,got?158:164,&point,got?o->actor.speed:0,got?o->actor.yaw:0);
    if(!got && effect>=0) {
        w->hazards->effects[effect].counter=4;
        if(p->sound_count<TOMB_SOUND_EVENTS){p->sounds[p->sound_count++]=(TombSoundEvent){5,10,0,hit.x,hit.y,hit.z};++p->sound_events;}
        else p->blocked=1;
    }
    return got?1:-1;
}
static int fire_shotgun(void *user,int16_t yaw,int16_t pitch) {
    TombPlaytest *p=user;uint32_t *random=&p->objects->enemies->random;int fired=0;
    for(int pellet=0;pellet<6;pellet++) {
        int16_t angles[2];tomb_shotgun_spread(random,yaw,pitch,angles);
        if(p->inventory.ammo[1]<=0){p->inventory.ammo[1]=0;p->requested_weapon=1;sound(p,48);continue;}
        --p->inventory.ammo[1];++p->pistols.shots;fire(p,angles[0],angles[1]);fired=1;
    }
    return fired;
}
int tomb_combat_tick(TombPlaytest *p,uint32_t input) {
    if(!p->objects || !p->objects->enemies)return 1;
    TombPistols *g=&p->pistols;g->status=p->animation.weapon_status;
    int toggle=(input&32)!=0;
    if(p->lara.health>0 && !p->lara.water_status && p->weapon_type!=p->requested_weapon) {
        if(!g->status){
            p->weapon_type=p->requested_weapon;
            memset(&g->left,0,sizeof g->left);memset(&g->right,0,sizeof g->right);g->target=-1;g->drawn=0;toggle=1;
        } else if(g->status==4)toggle=1;
    }
    int looking=p->camera_request.flags==TOMB_CAMERA_LOOK;
    g->head_yaw=p->lara.head_yaw;g->head_pitch=p->lara.head_pitch;
    g->torso_yaw=p->lara.torso_yaw;g->torso_pitch=p->lara.torso_pitch;
    if(g->status==4 && p->lara.health>0 && !p->lara.water_status && !toggle) {
        tomb_combat_target(p,(input&64)!=0);
    }
    int combat=g->status==2 || g->status==4 || (!g->status && toggle && !p->lara.water_status);
    if(p->weapon_type==4)tomb_shotgun_tick(g,toggle,(input&64)!=0,p->lara.health>0,p->lara.water_status,fire_shotgun,sound,p);
    else tomb_pistols_tick(g,toggle,(input&64)!=0,p->lara.health>0,p->lara.water_status,fire,sound,p);
    p->animation.weapon_status=g->status;
    p->lara.head_yaw=g->head_yaw;p->lara.head_pitch=g->head_pitch;p->lara.torso_yaw=g->torso_yaw;p->lara.torso_pitch=g->torso_pitch;
    if(looking) {
        p->camera_request.angle=tomb_word(g->head_yaw+g->torso_yaw);
        p->camera_request.elevation=tomb_word(g->head_pitch+g->torso_pitch);
    }
    if(!looking && combat && g->status!=3 && p->lara.health>0) {
        p->camera_request=(TombCameraRequest){2560,TOMB_CAMERA_COMBAT,8,g->target>=0?g->target_yaw:tomb_word(g->head_yaw+g->torso_yaw),g->target>=0?g->target_pitch:tomb_word(g->head_pitch+g->torso_pitch),p->lara.pitch,-1,0};
    }
    return !p->blocked;
}
