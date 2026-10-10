#include "playtest.h"
#include "fixed.h"
#include "object_contact.h"
#include "city.h"
#include "peru.h"
#include "hazards.h"
#include "enemies.h"
#include "combat.h"
#include "progression.h"
#include "follow_camera.h"
#include <stdlib.h>
#include <string.h>
static int supported(int state) { return state==42 || state==43 || state==52 || state==53 || state==36 || state==37 || state==38 || state==21 || state==22 || state==23 || state==45 || state==39 || state==40 || state==41 || state==24 || state==32 || state==11 || state==55 || state==0 || state==1 || state==2 || state==3 || state==5 || state==6 || state==7 || state==12 || state==16 || state==20 || state==9 || state==29 || state==15 || state==28 || state==10 || state==19 || state==54 || state==30 || state==31 || (state>=25 && state<=27); }
static void sound_request(TombPlaytest *p,int kind,int id,int environment,const TombActor *a) {
    if(p->sound_count>=TOMB_SOUND_EVENTS){p->blocked=1;p->status="Sound event capacity exceeded";return;}
    p->sounds[p->sound_count++]=(TombSoundEvent){kind,id,environment,a->x,a->y,a->z};
}
static void event(void *user,int kind,int16_t id,TombActor *actor) {
    TombPlaytest *p=user;
    if(kind==5) {++p->sound_events;sound_request(p,5,id,actor==&p->lara.actor?2:0,actor);}
    else if(kind==7) {++p->sound_stops;sound_request(p,7,id,2,actor);}
    else if(kind==6 && id==3) {++p->bubble_events;sound_request(p,6,3,1,actor);}
    else if(kind==6 && id==0) actor->yaw=tomb_word((int)actor->yaw-32768); /* DOS 0x1de74 */
    else if(kind==6 && id==2){actor->current=actor->goal=2;actor->animation=11;actor->frame=185;if(p->objects)p->objects->peru->scion_item=-1;}
    else if(kind==6 && id==4 && p->objects)p->objects->progress->complete=1;
    else if(kind==6 && id==12) p->animation.weapon_status=0;
    else if(kind==6 && id==1) sound_request(p,8,1,0,actor); /* Ground impact, consumed by the camera. */
    else { p->blocked=1; p->status="Animation effect not reconstructed"; }
}
static void air_sound(void *user,int kind,int16_t id,TombActor *actor) {
    TombPlaytest *p=user;
    if(kind==5)++p->sound_events;else if(kind==7)++p->sound_stops;
    sound_request(p,kind,id,0,actor); /* DOS fast-fall scream: above-water environment. */
}
static void query(void *user,TombActor *a,TombContact *c,int32_t height) {
    TombPlaytest *p=user; TombStaticContact sc;
    TombActor probe=*a; int radius=100;
    if(height==400) { probe.y=tomb_long((int64_t)probe.y+200); radius=300; }
    else if(height==700) probe.y=tomb_long((int64_t)probe.y+700);
    if(!(p->objects?tomb_active_contact(p->level,&probe,c,height,radius,a->y,p->animation.sine_quarter,0,p->level->items,p->level->item_count,&p->terrain,&sc):tomb_world_contact(p->level,&probe,c,height,radius,a->y,p->animation.sine_quarter,0,&p->terrain,&sc))) {
        p->blocked=1; p->status="World query failed"; return;
    }
    p->static_hit=sc.hit;
    p->ledge=(TombLedgeSamples){p->terrain.samples[0].ceiling,p->terrain.samples[1].floor,p->terrain.samples[1].ceiling,p->terrain.samples[2].floor,p->terrain.samples[3].floor};
    p->collision.front_floor=p->terrain.samples[1].floor;
    p->collision.front_type=p->terrain.samples[1].type;
    if(p->terrain.object_references && !p->movement_only) { p->blocked=1; p->status="Dynamic object behaviour pending"; }
    p->slide.tilt_x=(int8_t)p->terrain.tilt_x; p->slide.tilt_z=(int8_t)p->terrain.tilt_z;
}
static int32_t prepare_query(void *user,TombActor *a,TombContact *c,int32_t height) {
    TombPlaytest *p=user; query(user,a,c,height); return p->terrain.samples[0].ceiling;
}
static int32_t probe_sine(const int16_t *table,int angle) {
    unsigned v=(unsigned)angle&65535; int sign=v>=32768?-1:1;
    v&=32767; if(v>16384) v=32768-v; return sign*table[v>>4];
}
static int16_t jump_floor(void *user,TombActor *a,int16_t angle,int32_t distance) {
    TombPlaytest *p=user; TombSectorRef ref; TombHeights h;
    int32_t x=tomb_long((int64_t)a->x+tomb_asr(distance*probe_sine(p->animation.sine_quarter,angle),14));
    int32_t z=tomb_long((int64_t)a->z+tomb_asr(distance*probe_sine(p->animation.sine_quarter,(int)angle+16384),14));
    if(!tomb_find_sector(p->level,x,tomb_long((int64_t)a->y-762),z,a->room,&ref) ||
       !tomb_item_heights(p->level,ref,x,a->y,z,0,p->level->items,p->level->item_count,&h) || (h.object_references && !p->movement_only)) {
        p->blocked=1; p->status="Jump floor service pending"; return -32512;
    }
    return h.floor==-32512?-32512:tomb_word(tomb_long((int64_t)h.floor-a->y));
}
static int16_t bounds_min_y(void *user,TombActor *a) {
    TombPlaytest *p=user; int16_t bounds[6];
    if(!tomb_visual_bounds(p->visual,a,bounds)) { p->blocked=1; p->status="Animation bounds unavailable"; return 0; }
    return bounds[2];
}
static int upward_grab(void *user,TombActor *a,TombContact *c) {
    TombPlaytest *p=user;
    TombGrabContext ctx={p->movement.input,p->animation.weapon_status,bounds_min_y,NULL,p};
    int caught=tomb_ledge_grab(a,c,&p->ledge,&ctx,0);
    p->animation.weapon_status=ctx.weapon_status;
    return caught;
}
static void hanging(TombPlaytest *p,TombActor *a,TombContact *c) {
    TombHangContext ctx={query,bounds_min_y,&p->ledge,p,p->movement.input,p->lara.health,p->animation.weapon_status,p->air.move_angle};
    int state=a->current;
    if(state==30 || state==31) tomb_shimmy_collision(a,c,&ctx,state==31);
    else {
        tomb_hang_maintain(a,c,&ctx);
        tomb_hang_pullup_goal(a,&p->ledge,p->movement.input,p->terrain.samples[2].ceiling,p->terrain.samples[3].ceiling,p->static_hit);
    }
    p->animation.weapon_status=ctx.weapon_status; p->air.move_angle=ctx.move_angle;
    if(!p->blocked) p->status=(a->current==10 || a->current==30 || a->current==31)?"Hanging: Ctrl hold, A/D move, W pull up, release Ctrl to drop":"Movement test";
}
typedef struct VaultAdvance { TombPlaytest *p; TombVaultContext *v; } VaultAdvance;
static int vault_advance(void *user,TombActor *a) {
    VaultAdvance *b=user; b->p->animation.fall_override=b->v->fall_override;
    return tomb_animate(a,&b->p->animation);
}
static int vault(void *user,TombActor *a,TombContact *c) {
    TombPlaytest *p=user;
    TombVaultContext v={p->movement.input,p->animation.weapon_status,p->animation.fall_override,
        p->terrain.samples[2].ceiling,p->terrain.samples[3].ceiling,vault_advance,NULL};
    VaultAdvance b={p,&v}; v.user=&b;
    int result=tomb_vault(a,c,&p->ledge,&v);
    p->animation.weapon_status=v.weapon_status;
    return result;
}
static int swing_space(void *user,TombActor *a,int16_t yaw) {
    TombPlaytest *p=user; TombSectorRef ref; TombHeights h;
    int32_t x=a->x,z=a->z;
    if(yaw==0) z+=256; else if(yaw==16384) x+=256; else if(yaw==-32768) z-=256; else x-=256;
    if(!tomb_find_sector(p->level,x,a->y,z,a->room,&ref) || !tomb_item_heights(p->level,ref,x,a->y,z,0,p->level->items,p->level->item_count,&h) || (h.object_references && !p->movement_only)) {
        p->blocked=1; p->status="Swing space unavailable"; return 0;
    }
    return h.floor!=-32512 && h.floor-a->y>0 && h.ceiling-a->y<-400;
}
static int forward_grab(void *user,TombActor *a,TombContact *c) {
    TombPlaytest *p=user; TombGrabContext ctx={p->movement.input,p->animation.weapon_status,bounds_min_y,swing_space,p};
    int caught=tomb_ledge_grab(a,c,&p->ledge,&ctx,1); p->animation.weapon_status=ctx.weapon_status; return caught;
}
static int slide(void *user,TombActor *a,TombContact *c) {
    TombPlaytest *p=user;
    p->slide.move_angle=p->collision.walk.move_angle;
    int result=tomb_slide_start(a,c,&p->slide);
    p->collision.walk.move_angle=p->slide.move_angle;
    return result;
}
/* Validate the whole ordinary presentation-only list before publishing it.
   DOS 0x17d2e consumes an extra flags/timer word for a camera action; its
   end bit, not the camera index word, terminates the list. Object actions remain guarded. This landing pass records requests; the
   successful gameplay tick dispatches tutorial/camera/completion behaviour. */
static int deferred_presentation(const TombLevel *l,size_t index,unsigned *last_track,
                                 unsigned *camera,uint16_t *camera_flags) {
    if(index>=l->floor_count || l->floor_data[index]!=0x8004 ||
       l->floor_count-index<3) return 0;
    size_t cursor=index+2;
    unsigned track=0,shot=0;uint16_t flags=0;
    while(cursor<l->floor_count) {
        uint16_t action=l->floor_data[cursor++];
        unsigned value=action&0x3ff,type=(action&0x3fff)>>10;
        if(type==8) {
            if(value<2 || value>=64)return 0;
            track=value;
        } else if(type==1) {
            if(value>=l->camera_count || cursor>=l->floor_count)return 0;
            action=l->floor_data[cursor++];shot=value+1;flags=action;
        } else if(type!=7)return 0;
        if(action&0x8000) { *last_track=track;*camera=shot;*camera_flags=flags;return 1; }
    }
    return 0;
}
static int landing(void *user,TombActor *a,TombContact *c) {
    TombPlaytest *p=user; TombSectorRef ref; TombHeights h; (void)c;
    /* Original landing service queries the current sector before dispatching
       its trigger. Structural landings and presentation-only triggers are supported;
       other trigger behaviour remains guarded. */
    if(!tomb_find_sector(p->level,a->x,a->y,a->z,a->room,&ref) ||
       !tomb_item_heights(p->level,ref,a->x,a->y,a->z,0,p->level->items,p->level->item_count,&h) || h.floor==-32512) {
        p->blocked=1; p->status="Landing geometry unavailable"; return 0;
    }
    unsigned track=0,camera=0;uint16_t camera_flags=0;
    if(!p->movement_only && (h.object_references || (h.trigger_index && !deferred_presentation(p->level,h.trigger_index,&track,&camera,&camera_flags)))) {
        p->blocked=1; p->status="Landing trigger service pending"; return 0;
    }
    if(track) p->deferred_cd_track=track;
    if(camera) {p->deferred_camera=camera;p->deferred_camera_flags=camera_flags;}
    p->lara.sector_floor=h.floor;
    return tomb_landing_damage(&p->lara.health,a->fall_speed);
}
static int landing_advance(void *user,TombActor *a) {
    TombPlaytest *p=user;
    p->animation.move_angle=p->air.move_angle;
    return tomb_animate(a,&p->animation);
}
static void water_room(void *user,TombActor *a,int32_t offset) {
    TombPlaytest *p=user; TombSectorRef ref;
    if(!tomb_find_sector(p->level,a->x,tomb_long((int64_t)a->y+offset),a->z,a->room,&ref)) {
        p->blocked=1; p->status="Water room update failed";
    } else a->room=(int16_t)ref.room;
}
static int16_t water_height(void *user,TombActor *a) {
    TombPlaytest *p=user; return tomb_water_height(p->level,a->x,a->z,a->room);
}
static void water_save(TombPlaytest *p) {
    p->lara.pitch=p->water.pitch; p->lara.lean=p->water.lean; p->movement.lean=p->water.lean;
    p->lara.health=p->water.health; p->lara.air=p->water.air; p->lara.water_status=p->water.status;
    p->animation.weapon_status=p->water.weapon_status; p->animation.move_angle=p->water.move_angle;
}
static int water_tick(TombPlaytest *p,uint32_t input) {
    p->camera_request=tomb_camera_control(p->lara.actor.current,p->water.status,p->water.pitch);
    TombActor *a=&p->lara.actor; TombWater *w=&p->water;
    int surface=w->status==2;
    w->input=input&(1|2|4|8|16|64|128|1024|2048);
    if(w->health>=0) {
        if(surface) { w->air=tomb_word(w->air+10); if(w->air>1800) w->air=1800; }
        else { w->air=tomb_word(w->air-1); if(w->air<0) { w->air=-1; w->health=tomb_word(w->health-5); } }
    }
    TombContact c={0}; c.old_x=a->x; c.old_y=a->y; c.old_z=a->z;
    c.positive_limit=32512; c.negative_limit=surface?-100:-400; c.ceiling_limit=surface?100:400;
    if(surface && a->current==33 && (input&512) && w->health>0) {
        TombMovement *m=&p->movement;m->input=input;m->head_yaw=p->lara.head_yaw;m->head_pitch=p->lara.head_pitch;
        tomb_surface_look(m);a->fall_speed=tomb_word(a->fall_speed-4);if(a->fall_speed<0)a->fall_speed=0;
        p->lara.head_yaw=m->head_yaw;p->lara.head_pitch=m->head_pitch;p->lara.torso_yaw=m->torso_yaw;p->lara.torso_pitch=m->torso_pitch;
        p->camera_request=(TombCameraRequest){1536,TOMB_CAMERA_LOOK,4,tomb_word(m->head_yaw+m->torso_yaw),m->head_pitch,p->lara.pitch,-1,0};
    } else if(!tomb_water_control(a,w,surface)) { p->blocked=1; p->status="Water control pending"; return 0; }
    tomb_water_damping(w,surface);
    if(!tomb_animate(a,&p->animation)) { p->blocked=1; p->status="Water animation unavailable"; return 0; }
    w->weapon_status=p->animation.weapon_status; /* Preserve animation end commands. */
    tomb_water_motion(a,w,surface);
    if(a->current==13 || a->current==17 || a->current==18 || a->current==35) tomb_underwater_collision(a,&c,w);
    else if(a->current==33 || a->current==34 || (a->current>=47 && a->current<=49)) {
        w->move_angle=tomb_word(a->yaw+(a->current==47?-32768:a->current==48?-16384:a->current==49?16384:0));
        tomb_surface_collision(a,&c,&p->ledge,w);
    } else if(a->current==39 || a->current==40) {c.positive_limit=384;c.negative_limit=-384;c.ceiling_limit=0;c.flags|=3;w->move_angle=c.facing=a->yaw;query(p,a,&c,762);}
    else if(a->current==44) {w->health=-1;}
        else { p->blocked=1; p->status="Water state pending"; }
    water_room(p,a,surface?100:0); water_save(p);
    if(!p->blocked) p->status=w->status==0?"Climbing out of water":w->status==1?"Underwater: J/Alt swim, W/S pitch, A/D turn":"Surface: W/S swim, J/Alt dive, Ctrl at edge to climb out";
    return !p->blocked;
}
static int gym_tick(TombPlaytest *p) {
    if(p->movement_only)return 1;
    TombSectorRef ref;TombHeights h;TombActor *a=&p->lara.actor;
    tomb_gym_begin_tick(&p->gym);
    if(tomb_find_sector(p->level,a->x,a->y,a->z,a->room,&ref) &&
       tomb_item_heights(p->level,ref,a->x,a->y,a->z,0,p->level->items,p->level->item_count,&h)) {
        if(!tomb_gym_trigger(&p->gym,p->level,h.trigger_index,a->current)) {
            p->status="Unsupported gym trigger";return 0;
        }
    }
    if(p->gym.complete)p->status="Gym complete! Press R to restart";
    return 1;
}
static void dead_contact(TombPlaytest *p){
    TombActor *a=&p->lara.actor;
        /* DOS dead collision uses a wider 400-unit radius and 384 step limits. */
        TombContact c={0};TombTerrain terrain;TombStaticContact statics;
        c.old_x=a->x;c.old_y=a->y;c.old_z=a->z;c.facing=a->yaw;
        c.positive_limit=384;c.negative_limit=-384;c.ceiling_limit=0;
        if(tomb_world_contact(p->level,a,&c,762,400,a->y,p->animation.sine_quarter,0,&terrain,&statics)) {
            a->x+=c.shift_x;a->y+=c.shift_y;a->z+=c.shift_z;
            if(c.floor!=-32512)a->y+=c.floor;
        }
        a->flags&=(uint8_t)~8u;a->speed=a->fall_speed=0;
}
static int death_tick(TombPlaytest *p) {
    TombActor *a=&p->lara.actor;
    p->blocked=0;p->lara.health=-1;p->lara.air=-1;p->dead_ticks++;
    p->gym.camera=0;
    if(p->gym.current_track){p->gym.current_track=0;p->gym.audio_serial++;}
    if(a->current==46){
        a->goal=46;p->movement.lean=0;p->door_hit_ticks=0;
        p->lara.head_yaw=p->lara.head_pitch=p->lara.torso_yaw=p->lara.torso_pitch=0;
        p->camera_request=tomb_camera_control(46,0,0);
        tomb_animate(a,&p->animation);p->status="Lara died";
    } else if(p->lara.water_status) {
        a->goal=44;p->water.health=-1;p->water.air=-1;p->water.input=0;
        if(a->current==44) {
            a->fall_speed=tomb_word(a->fall_speed-8);if(a->fall_speed<0)a->fall_speed=0;
            if(p->lara.pitch>=-364 && p->lara.pitch<=364)p->lara.pitch=0;
            else p->lara.pitch=tomb_word(p->lara.pitch+(p->lara.pitch<0?364:-364));
        }
        p->water.pitch=p->lara.pitch;
        tomb_animate(a,&p->animation);tomb_water_motion(a,&p->water,0);
        int16_t height=water_height(p,a);if(height!=-32512 && height<a->y-100)a->y-=5;
        TombContact c={0};c.old_x=a->x;c.old_y=a->y;c.old_z=a->z;
        c.positive_limit=32512;c.negative_limit=-400;c.ceiling_limit=-400;
        tomb_underwater_collision(a,&c,&p->water);water_room(p,a,0);water_save(p);
        p->status="Drowned - press R to restart";
    } else {
        a->goal=8;tomb_animate(a,&p->animation);
        dead_contact(p);
        p->status="Lara died";
    }
    return !p->blocked;
}
int tomb_playtest_init(TombPlaytest *p,const TombLevel *l,const int16_t *sine,const TombVisual *visual) {
    if(!p || !l || !sine || !visual || visual->level!=l) return 0;
    memset(p,0,sizeof *p); p->level=l; p->visual=visual;
    tomb_pistols_init(&p->pistols);tomb_inventory_init(&p->inventory);p->weapon_type=p->requested_weapon=1;
    if(!tomb_lara_start(l,&p->lara)) return 0;
    tomb_hud_init(&p->hud,p->lara.health);
    p->movement.health=p->lara.health;
    p->animation=(TombAnimContext){l->animations,l->animation_count,l->changes,l->change_count,l->ranges,l->range_count,
        l->commands,l->command_count,sine,p->lara.move_angle,0,0,event,p};
    p->slide=(TombSlideContext){query,p,p->lara.move_angle,0,0,0};
    p->collision.walk=(TombWalkContext){query,vault,slide,p,p->lara.move_angle};
    p->air=(TombAirContext){query,landing,p,sine,p->lara.move_angle,air_sound,landing_advance};
    p->water=(TombWater){0,p->lara.health,0,0,p->lara.water_status,0,p->lara.move_angle,0,p->lara.air,query,water_room,water_height,p,sine};
    p->camera_request=tomb_camera_control(p->lara.actor.current,p->lara.water_status,p->lara.pitch);
    p->status="Movement test"; return 1;
}
static int playtest_tick(TombPlaytest *p,uint32_t input) {
    if(p->gym.complete){p->status="Gym complete! Press R to restart";return 1;}
    if(p->lara.health<=0 || p->lara.actor.current==8)return death_tick(p);
    TombLaraStart saved=p->lara;
    TombActor before=p->lara.actor, *a=&p->lara.actor;
    TombMovement *m=&p->movement;
    int16_t old_move=p->animation.move_angle;
    TombSlideContext saved_slide=p->slide;
    int16_t old_weapon=p->animation.weapon_status;
    unsigned old_cd_track=p->deferred_cd_track,old_camera=p->deferred_camera;
    uint16_t old_camera_flags=p->deferred_camera_flags;
    p->blocked=0; p->status="Movement test"; m->health=p->lara.health;
    TombWater saved_water=p->water;
    p->water.health=p->lara.health; p->water.pitch=p->lara.pitch; p->water.lean=p->lara.water_status?p->lara.lean:m->lean;
    p->water.status=p->lara.water_status; p->water.air=p->lara.air;
    p->water.weapon_status=p->animation.weapon_status; p->water.move_angle=p->animation.move_angle;
    int dive_entry=!p->water.status && (a->current==52 || a->current==53) && (p->level->rooms[a->room].flags&1);
    TombActor dive_before=*a;
    tomb_water_transition(a,&p->water,p->level->rooms[a->room].flags&1,water_height(p,a));
    if(dive_entry){
        a->fall_speed=dive_before.fall_speed;a->animation=dive_before.animation;a->frame=dive_before.frame;a->current=dive_before.current;a->goal=35;
        p->water.pitch=dive_before.current==52?-8190:-15470;
        if(!tomb_animate(a,&p->animation))return 0;a->fall_speed=tomb_word(a->fall_speed*2);
    }
    if(!saved.water_status && p->water.status==1) {
        sound_request(p,7,30,2,a); /* DOS 0x28435: stop fall scream. */
        sound_request(p,5,33,0,a); /* DOS splash 0x1dc50. */
    } else if(saved.water_status==1 && p->water.status==2) {
        sound_request(p,5,36,2,a); /* DOS 0x285c3: surfacing breath. */
    }
    if(saved.water_status || p->water.status) water_save(p);
    if(p->water.status) {
        if(water_tick(p,input)) {gym_tick(p);return 1;}
        p->sound_count=0;p->lara=saved; p->water=saved_water; p->animation.move_angle=old_move; p->animation.weapon_status=old_weapon; return 0;
    }
    p->lara.air=1800;
    p->camera_request=tomb_camera_control(a->current,0,p->lara.pitch);
    m->input=input & (1|2|4|8|16|64|128|512|1024|2048|4096);
    m->head_yaw=p->lara.head_yaw;m->head_pitch=p->lara.head_pitch;
    m->torso_yaw=p->lara.torso_yaw;m->torso_pitch=p->lara.torso_pitch;m->camera_mode=0;
    m->weapon_status=p->animation.weapon_status;
    /* Jump entry is implemented from standing and running. */
    if(a->current!=1 && a->current!=2 && a->current!=24 && a->current!=32) m->input&=~16u;
    m->current_state=a->current; m->goal_state=a->goal; m->animation=a->animation; m->frame=a->frame; m->item_flags=a->flags;
    TombContact c={0}; c.old_x=before.x; c.old_y=before.y; c.old_z=before.z; c.flags=0x18;
    if(a->current==52 || a->current==53){tomb_swan_control(a,&c);m->goal_state=a->goal;} else if(a->current==23 || a->current==45) { /* DOS null roll control 0x25cd8 */
    } else if(a->current==24 || a->current==32) {
        tomb_slide_control(a,m->input,&p->requested_camera_mode,&p->requested_camera_elevation);m->goal_state=a->goal;
    } else if(a->current==10 || a->current==30 || a->current==31) {
        TombHangControl control={m->input,0,0}; tomb_hang_control(a,&c,&control);
        p->requested_camera_angle=control.camera_angle; m->goal_state=a->goal;
    } else if(a->current>=36 && a->current<=38) {
        c.flags&=(uint8_t)~0x18u;if(a->current==38 && !(input&64))m->goal_state=2;
    } else if(a->current==19 || a->current==54 || a->current==55 || a->current==39 || a->current==40 || a->current==41 || a->current==42 || a->current==43) {
        /* Original shared null control 0x256d8 clears these collision flags. */
        c.flags&=(uint8_t)~0x18u;
    } else if(a->current==15) {
        tomb_jump_prepare_control(a,m->input,jump_floor,p,&p->animation.move_angle); m->goal_state=a->goal;
    } else if(a->current>=25 && a->current<=27) {
        tomb_directional_jump_control(a,&p->requested_camera_angle); m->goal_state=a->goal;
    } else if(a->current==28) {
        tomb_up_jump_control(a); m->goal_state=a->goal;
    } else if(a->current==11) {
        tomb_reach_control(a,&p->requested_camera_angle); m->goal_state=a->goal;
    } else if(a->current==3) {
        tomb_forward_air_control(a,m->input,p->animation.weapon_status,&m->turn_rate); m->goal_state=a->goal;
    } else if(a->current==9) {
        if(!tomb_fast_fall_control(a,air_sound,p)) { p->blocked=1; p->status="Fast fall sound service unavailable"; }
    } else if(a->current==29) {
        tomb_back_fall_control(a,m->input,p->animation.weapon_status); m->goal_state=a->goal;
    } else if(!supported(a->current) || !tomb_movement_control((enum TombControl)a->current,m)) {
        p->blocked=1; p->status="Control state pending"; return 0;
    }
    a->current=m->current_state; a->goal=m->goal_state; a->animation=m->animation; a->frame=m->frame; a->flags=m->item_flags;
    p->lara.head_yaw=m->head_yaw;p->lara.head_pitch=m->head_pitch;
    p->lara.torso_yaw=m->torso_yaw;p->lara.torso_pitch=m->torso_pitch;
    if(m->camera_mode==2)p->camera_request=(TombCameraRequest){1536,TOMB_CAMERA_LOOK,4,tomb_word(m->head_yaw+m->torso_yaw),tomb_word(m->head_pitch+m->torso_pitch),p->lara.pitch,-1,0};
    tomb_ground_damping(m,a);
    if(!tomb_animate(a,&p->animation)) { p->blocked=1; p->status="Animation service unavailable"; }
    if(p->objects && !p->blocked) {
        int hit=0;
        if(!tomb_hazards_contact(p->objects,a,&c,&p->animation,p->lara.pitch,m->lean,query,p) || !tomb_doors_collide(p->objects,a,&c,&p->animation,p->lara.pitch,m->lean,query,p,&hit)) {p->blocked=1;p->status="Door contact unavailable";}
        if(hit && !p->door_hit_ticks)sound_request(p,5,27,0,a);
        p->door_hit_ticks=hit?(p->door_hit_ticks<34?p->door_hit_ticks+1:34):0;
        p->door_hit_direction=hit-1;
    }
    p->collision.lean=m->lean;
    int air_collision=a->current==52 || a->current==53 || a->current==42 || a->current==43 || (a->current>=36 && a->current<=38) || a->current==40 || a->current==41 || a->current==11 || a->current==3 || a->current==29 || a->current==9 || a->current==28 || a->current==10 || a->current==30 || a->current==31 || a->current==19 || a->current==54 || a->current==55 || a->current==15 || (a->current>=25 && a->current<=27);
    p->air.move_angle=p->animation.move_angle;
    if(!p->blocked) {
        int ok;
        if(a->current==8){dead_contact(p);ok=1;}
        else if(a->current>=36 && a->current<=43) {
            c.positive_limit=384;c.negative_limit=-384;c.ceiling_limit=0;c.flags|=3;
            p->air.move_angle=c.facing=a->yaw;query(p,a,&c,762);ok=1;
        }
        else if(a->current==52 || a->current==53) {ok=tomb_swan_collision(a,&c,&p->air);}
        else if(a->current==24 || a->current==32) { tomb_slide_collision(a,&c,&p->slide);p->collision.walk.move_angle=p->slide.move_angle;ok=1; }
        else if(a->current==10 || a->current==30 || a->current==31) { hanging(p,a,&c); ok=1; }
        else if(a->current==19 || a->current==54 || a->current==55) { tomb_pullup_collision(a,&c,&p->air); ok=1; }
        else if(a->current==15) { tomb_jump_prepare_collision(a,&c,prepare_query,p,p->air.move_angle); ok=1; }
        else if(a->current==11) { ok=tomb_reach_collision(a,&c,&p->air,forward_grab); }
        else ok=(a->current>=25 && a->current<=27)?tomb_directional_jump_collision(a,&c,&p->air):a->current==28?tomb_up_jump_collision(a,&c,&p->air,upward_grab):a->current==3?tomb_forward_air_collision(a,&c,&p->air,m->input):
            a->current==9?tomb_fast_fall_collision(a,&c,&p->air):
            a->current==29?tomb_back_fall_collision(a,&c,&p->air):tomb_ground_collision(a->current,a,&c,&p->collision);
        if(!ok) { p->blocked=1; p->status="Collision state pending"; }
    }
    if((!supported(a->current) && a->current!=8) || ((a->flags&8) && a->current!=11 && a->current!=3 && a->current!=29 && a->current!=9 && a->current!=28 && a->current!=52 && a->current!=53 && !(a->current>=25 && a->current<=27)) ) { p->blocked=1; p->status="Traversal pending"; }
    TombSectorRef ref;
    if(!p->blocked) {
        if(!tomb_find_sector(p->level,a->x,a->y-381,a->z,a->room,&ref)) { p->blocked=1; p->status="Room update failed"; }
        else a->room=(int16_t)ref.room;
    }
    if(p->blocked) {
        p->sound_count=0;
        int16_t yaw=a->yaw; p->lara=saved; a->yaw=yaw;
        if(!(before.flags&8) && before.current!=10 && before.current!=30 && before.current!=31 && before.current!=19 && before.current!=54 && before.current!=55) { a->current=a->goal=2; a->animation=11; a->frame=185; a->speed=0; }
        m->lean=0; p->animation.move_angle=old_move; p->slide=saved_slide;
        p->deferred_cd_track=old_cd_track;p->deferred_camera=old_camera;p->deferred_camera_flags=old_camera_flags; p->animation.weapon_status=old_weapon;
        return 0;
    }
    if(p->lara.health<=0){p->status="Lara died";return 1;}
    gym_tick(p);
    p->animation.move_angle=air_collision?p->air.move_angle:p->collision.walk.move_angle; m->lean=p->collision.lean;
    return 1;
}

int tomb_playtest_tick(TombPlaytest *p,uint32_t input) {
    p->last_input=input;
    if(p->objects && p->objects->progress->complete){p->sound_count=0;return 1;}
    tomb_hud_tick(&p->hud,p->lara.health);
    ++p->inventory.ticks;if(p->inventory.pickup_ticks>0)--p->inventory.pickup_ticks;
    p->sound_count=0;
    p->camera_request=tomb_camera_control(p->lara.actor.current,p->lara.water_status,p->lara.pitch);
    if(p->objects)tomb_objects_camera_begin(p->objects);
    if(p->objects && !tomb_peru_hazards(p->objects,&p->animation,&p->lara.actor,&p->lara.health)){p->blocked=1;p->status="Peru object service unavailable";return 0;}
    if(p->objects && !tomb_hazards_tick(p->objects,&p->animation,&p->lara.actor,&p->lara.health)) {p->blocked=1;p->status="Hazard service unavailable";return 0;}
    if(p->objects && !tomb_objects_tick(p->objects,&p->animation)) {
        p->blocked=1;p->status="Object animation unavailable";return 0;
    }
    if(p->objects && !tomb_enemies_tick(p->objects,&p->animation,&p->lara)) {
        p->blocked=1;p->status="Enemy service unavailable";return 0;
    }
    int ok;
    if(p->objects && p->objects->peru->scion_item>=0){ok=tomb_animate(&p->lara.actor,&p->animation);p->status="Scion pickup";}else ok=playtest_tick(p,input);
    if(ok && p->objects)ok=tomb_peru_lara(p,input);
    if(ok && p->objects && p->lara.health>0) {
        ok=tomb_pickups_tick(p,input);
        if(ok)ok=tomb_city_interact(p,input);
        p->inventory.chosen=-1; /* DOS BaddieCollision tail 0x16277: one contact pass only. */
        if(ok)ok=tomb_objects_interact(p->objects,&p->lara.actor,&p->animation,input,p->lara.pitch,p->movement.lean);
        unsigned secret_before=p->objects->progress->secret_serial;
        p->objects->progress->lara_state=p->lara.actor.current;
        TombActor *a=&p->lara.actor;TombSectorRef ref;TombHeights h;
        if(ok && tomb_find_sector(p->level,a->x,a->y,a->z,a->room,&ref) && tomb_item_heights(p->level,ref,a->x,a->y,a->z,0,p->level->items,p->level->item_count,&h))
            ok=tomb_objects_trigger_keys(p->objects,h.trigger_index,h.floor==a->y,p->animation.weapon_status);
        if(p->objects->progress->secret_serial!=secret_before)sound_request(p,5,173,2,&p->lara.actor);
        if(!ok){p->blocked=1;p->status="Object service unavailable";}
    }
    if(ok) {
        TombMovement *m=&p->movement;m->head_yaw=p->lara.head_yaw;m->head_pitch=p->lara.head_pitch;
        m->torso_yaw=p->lara.torso_yaw;m->torso_pitch=p->lara.torso_pitch;
        m->camera_mode=p->camera_request.flags==TOMB_CAMERA_LOOK?2:0;tomb_look_relax(m);
        p->lara.head_yaw=m->head_yaw;p->lara.head_pitch=m->head_pitch;p->lara.torso_yaw=m->torso_yaw;p->lara.torso_pitch=m->torso_pitch;
        ok=tomb_combat_tick(p,input);
    }
    if(ok && p->lara.health>0 && p->objects && !p->objects->camera.active && p->objects->camera.target>=0 && !(p->camera_request.flags&(TOMB_CAMERA_LOOK|TOMB_CAMERA_COMBAT))){
        TombObject *o=p->objects->items+p->objects->camera.target;TombActor target=o->actor;TombModel model;TombPose lp,tp;
        if(tomb_visual_model(p->visual,o->object,&model) && model.animation<p->level->animation_count){
            if(!tomb_object_supported(o->object)){target.animation=(int16_t)model.animation;target.frame=p->level->animations[model.animation].first_frame;}
            if(tomb_object_pose(p->visual,&p->lara.actor,&lp) && tomb_object_pose(p->visual,&target,&tp) && tomb_camera_interest(&p->lara.actor,lp.bounds,&target,tp.bounds,&p->lara.head_yaw,&p->lara.head_pitch)){
                p->lara.torso_yaw=p->lara.head_yaw;p->lara.torso_pitch=p->lara.head_pitch;o->actor.flags|=64;
                p->camera_request=(TombCameraRequest){1536,TOMB_CAMERA_LOOK,4,tomb_word(2*p->lara.head_yaw),tomb_word(2*p->lara.head_pitch),p->lara.pitch,-1,0};
            }
        }
    }
    if(!ok || p->blocked)p->sound_count=0;
    return ok;
}

int tomb_city_fixture(TombPlaytest *p,TombObjects *w,const int16_t *s,int which){
 if(which<0 || which>7)return 0;
 if(which==7){
  tomb_objects_reset(w);if(!tomb_playtest_init(p,w->level,s,w->visual))return 0;p->objects=w;p->movement_only=1;
  p->lara.actor.x=27600;p->lara.actor.y=-1024;p->lara.actor.z=29184;p->lara.actor.room=61;p->lara.actor.yaw=-16384;p->animation.move_angle=-16384;return 1;
 }
 if(which>=3){
  tomb_objects_reset(w);if(!tomb_playtest_init(p,w->level,s,w->visual))return 0;p->objects=w;p->movement_only=1;
  int ids[]={129,110,137,118};
  for(size_t i=0;i<w->count;i++)if(w->items[i].object==ids[which-3]){
   TombActor *a=&p->lara.actor,*o=&w->items[i].actor;*a=(TombActor){o->x,o->y,o->z,2,2,11,185,0,0,0,o->room,32};
   if(which<5)a->z-=100;
   else {int32_t local[3]={0,0,400},pos[3];tomb_rotate_vector(o->yaw,0,0,local,0,s,pos);a->x+=pos[0];a->z+=pos[2];a->yaw=o->yaw;tomb_inventory_add(&p->inventory,which==5?129:110);}
   p->animation.move_angle=a->yaw;return 1;
  }
  return 0;
 }
 tomb_objects_reset(w);if(!tomb_playtest_init(p,w->level,s,w->visual))return 0;p->objects=w;p->movement_only=1;
 int remaining=which?which-1:0;
 for(size_t i=0;i<w->count;i++)if(w->items[i].object==(which?56:48)){
  if(remaining-- >0)continue;
  TombActor *a=&p->lara.actor,*o=&w->items[i].actor;a->x=o->x;a->y=o->y;a->z=o->z;a->room=o->room;
  if(!which){a->z-=612;a->yaw=0;}
  else {int32_t offset[3]={0,0,300},pos[3];tomb_rotate_vector(o->yaw,0,0,offset,0,s,pos);a->x+=pos[0];a->z+=pos[2];a->yaw=o->yaw;
   a->current=a->goal=13;a->animation=108;a->frame=1736;a->flags=32;p->lara.water_status=p->water.status=1;p->lara.pitch=p->water.pitch=0;
  }
  p->animation.move_angle=a->yaw;TombSectorRef ref;if(tomb_find_sector(w->level,a->x,a->y,a->z,a->room,&ref))a->room=(int16_t)ref.room;return 1;
 }
 return 0;
}
