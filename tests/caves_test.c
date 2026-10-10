#include "playtest.h"
#include "follow_camera.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "object_contact.h"
#include "hazards.h"
static TombSoundBank bank;
static unsigned door_sounds;
static void tick(TombPlaytest *p,unsigned input) {
    if(!tomb_playtest_tick(p,input)){fprintf(stderr,"blocked state %d: %s\n",p->lara.actor.current,p->status);abort();}
    for(unsigned i=0;i<p->sound_count;i++) {
        int id=p->sounds[i].id;
        if(p->sounds[i].kind==5 && id==64)door_sounds++;
        if(p->sounds[i].kind==5 && id>=0 && id<256 && bank.map[id]>=0)
            assert((bank.details[bank.map[id]].flags&3)!=2); /* No unserviced ambient loops. */
    }
    assert(!p->gym.current_track && !p->gym.camera && !p->gym.complete);
    assert(p->lara.actor.room>=0 && (size_t)p->lara.actor.room<p->level->room_count);
}
static void init(TombPlaytest *p,TombLevel *l,TombVisual *v,const int16_t *sine) {
    assert(tomb_playtest_init(p,l,sine,v));p->movement_only=1;
}
static void camera_sequence(TombPlaytest *p,TombObjects *objects,int index,int target,int speed) {
    TombFollowCamera camera={0};int active=0;
    for(int i=0;i<180;i++) {
        tick(p,0);
        int previous_target=camera.fixed_target;
        TombFollowCamera fine=camera;
        assert(tomb_scene_camera(&camera,objects,&p->lara.actor,0,0,0,1800,1.0/30));
        assert(tomb_scene_camera(&fine,objects,&p->lara.actor,0,0,0,1800,1.0/60));
        assert(tomb_scene_camera(&fine,objects,&p->lara.actor,0,0,0,1800,1.0/60));
        if(objects->camera.active) {
            assert(objects->camera.index==index && objects->camera.target==target && objects->camera.speed==speed);
            active++;
            if(active>1)for(int j=0;j<3;j++)assert(fabs(camera.eye[j]-fine.eye[j])<1);
        }
        for(int j=0;j<3;j++) {
            assert(isfinite(camera.eye[j]) && isfinite(camera.target[j]));
            if(previous_target!=camera.fixed_target || (objects->camera.active && speed==1)) {
                assert(camera.previous_eye[j]==camera.eye[j]);
            }
            if(previous_target!=camera.fixed_target)assert(camera.previous_target[j]==camera.target[j]);
        }
    }
    assert(active==90 && !objects->camera.active && !camera.fixed_target);
    assert(fabs(camera.target[0]-p->lara.actor.x)<1 && fabs(camera.target[2]-p->lara.actor.z)<1);
}
static void contact_query(void *user,TombActor *a,TombContact *c,int32_t height) {
    TombPlaytest *p=user;TombTerrain terrain;TombStaticContact statics;
    assert(tomb_world_contact(p->level,a,c,height,100,a->y,p->animation.sine_quarter,0,&terrain,&statics));
}
int main(int argc,char **argv) {
    assert(argc==3);char error[256];int16_t sine[1025];
    FILE *f=fopen(argv[2],"rb");assert(f);assert(fread(sine,sizeof sine,1,f)==1);fclose(f);
    TombLevel *l=tomb_level_load(argv[1],error,sizeof error);assert(l);
    TombVisual *v=tomb_visual_load(l,error,sizeof error);assert(v);
    assert(tomb_sound_bank_load(&bank,l));
    TombPlaytest p;init(&p,l,v,sine);TombActor origin=p.lara.actor;
    for(int i=0;i<120;i++)tick(&p,0);
    assert(p.lara.actor.x==origin.x && p.lara.actor.z==origin.z);
    for(int i=0;i<180;i++)tick(&p,1);
    assert(p.lara.actor.z>origin.z+7000);

    for(int back=0;back<2;back++)for(int jump=0;jump<2;jump++) {
        init(&p,l,v,sine);TombActor *a=&p.lara.actor;
        a->x=73216;a->y=1024;a->z=14848;a->room=0;a->yaw=back?-16384:16384;
        p.animation.move_angle=a->yaw;
        tick(&p,0);assert(a->current==(back?32:24));
        int sliding=0,airborne=0,stopped=0;
        for(int i=0;i<100;i++) {
            tick(&p,jump && i<8?16:0);
            sliding+=a->current==24 || a->current==32;airborne+=(a->flags&8)!=0;stopped+=a->current==2;
        }
        printf("slope back=%d jump=%d: slide=%d air=%d stop=%d at %d,%d,%d state=%d\n",back,jump,sliding,airborne,stopped,a->x,a->y,a->z,a->current);
        assert(a->x>73216 && stopped>0);
        if(jump)assert(airborne>0);else assert(sliding>0);
    }
    TombObjects objects;assert(tomb_objects_init(&objects,l,v));
    assert(objects.doors[9].count==2);
    for(int pass=0;pass<2;pass++) {
        tomb_objects_reset(&objects);init(&p,l,v,sine);p.objects=&objects;
        TombActor *a=&p.lara.actor;
        a->x=49664;a->y=7680;a->z=57856;a->room=9;a->yaw=-16384;p.animation.move_angle=a->yaw;
        for(int i=0;i<90;i++)tick(&p,1);
        assert(a->x>=49152 && !objects.doors[9].open);
        init(&p,l,v,sine);p.objects=&objects;a=&p.lara.actor;
        a->x=49664;a->y=7680;a->z=58256;a->room=9;a->yaw=0;p.animation.move_angle=0;
        tick(&p,64);assert(a->current==40);
        for(int i=0;i<120;i++)tick(&p,0);
        printf("first switch: Lara=%d switch=%d flags=%u door=%d open=%d\n",a->current,objects.items[10].actor.current,objects.items[10].actor.flags,objects.items[9].actor.current,objects.doors[9].open);
        assert(objects.doors[9].open && a->current==2 && p.animation.weapon_status==0);
        a->x=49664;a->y=7680;a->z=57856;a->room=9;a->yaw=-16384;p.animation.move_angle=a->yaw;
        for(int i=0;i<60;i++)tick(&p,1);
        assert(a->x<49152);
    }
    tomb_objects_reset(&objects);init(&p,l,v,sine);p.objects=&objects;
    p.lara.actor.x=24464;p.lara.actor.y=6912;p.lara.actor.z=83456;p.lara.actor.room=26;p.lara.actor.yaw=16384;p.animation.move_angle=16384;
    double camera_probe[3]={24464,6462,83456};
    assert(tomb_camera_clear(l,camera_probe,26,96,NULL));
    tick(&p,64);assert(p.lara.actor.current==40);
    camera_sequence(&p,&objects,1,-1,17);
    assert(objects.doors[43].open && objects.doors[44].open);
    for(int i=0;i<720;i++)tick(&p,0);
    assert(!objects.doors[43].open && !objects.doors[44].open && objects.items[42].actor.current==1);
    tomb_objects_reset(&objects);init(&p,l,v,sine);p.objects=&objects;
    p.lara.actor.x=48240;p.lara.actor.y=4608;p.lara.actor.z=78336;p.lara.actor.room=33;p.lara.actor.yaw=-16384;p.animation.move_angle=-16384;
    tick(&p,64);assert(p.lara.actor.current==40);
    camera_sequence(&p,&objects,0,41,1);
    assert(objects.doors[35].open && objects.doors[36].open);
    /* This switch latches its doors one-shot: the antipad cannot undo it.
       Clear that latch only in this fixture to exercise the grounded antipad. */
    assert(tomb_objects_trigger(&objects,2416,1));assert((objects.items[35].flags&0x3e00)==0x3e00);
    objects.items[35].flags&=(uint16_t)~0x100;objects.items[36].flags&=(uint16_t)~0x100;
    assert(tomb_objects_trigger(&objects,2416,0));assert((objects.items[35].flags&0x3e00)==0x3e00);
    assert(tomb_objects_trigger(&objects,2416,1));assert((objects.items[35].flags&0x3e00)==0);
    for(int i=0;i<100;i++)tick(&p,0);
    assert(!objects.doors[35].open && !objects.doors[36].open);
    tomb_objects_reset(&objects);
    assert(tomb_objects_trigger(&objects,2854,0));assert(!objects.items[28].active);
    assert(tomb_objects_trigger(&objects,2854,1));assert(objects.items[28].active && objects.items[28].timer==60);
    for(int i=0;i<10;i++)assert(tomb_objects_tick(&objects,&p.animation));
    assert(objects.doors[28].open);
    /* Malformed camera trailer must not consume a completed switch. */
    tomb_objects_reset(&objects);objects.items[42].actor.flags=36;objects.items[42].actor.current=0;
    uint16_t bad=l->floor_data[3478];l->floor_data[3478]=0x83ff;
    assert(!tomb_objects_trigger(&objects,3474,1));assert(objects.items[42].actor.flags==36);
    l->floor_data[3478]=bad;
    /* Cardinal interaction bounds: exact position/yaw tolerances and no behind-wall activation. */
    TombActor sw=objects.items[10].actor,probe=sw;probe.z+=312;
    assert(tomb_switch_bounds(&probe,&sw,0,0));probe.z=sw.z+512;assert(tomb_switch_bounds(&probe,&sw,0,0));
    probe.z++;assert(!tomb_switch_bounds(&probe,&sw,0,0));probe.z=sw.z+400;probe.x+=201;assert(!tomb_switch_bounds(&probe,&sw,0,0));
    probe.x=sw.x;probe.yaw=5461;assert(!tomb_switch_bounds(&probe,&sw,0,0));
    assert(door_sounds>0);
    /* Closing leaves against actual terrain, from both sides. Sector opening
       still follows the door controller; contact may push or reject a wall. */
    tomb_objects_reset(&objects);init(&p,l,v,sine);p.objects=&objects;
    objects.items[43].flags=0x3e00;objects.items[43].active=1;
    objects.items[44].flags=0x3e00;objects.items[44].active=1;
    for(int i=0;i<70;i++)assert(tomb_objects_tick(&objects,&p.animation));
    TombObject *door=&objects.items[43];door->actor.animation=242;door->actor.current=1;door->actor.goal=0;
    int pushed=0,reacted=0;
    for(int fidx=1;fidx<=61;fidx+=5)for(int dx=-700;dx<=700;dx+=100)for(int dz=-700;dz<=700;dz+=100) {
        door->actor.frame=(int16_t)fidx;
        TombActor a=p.lara.actor;a.x=door->actor.x+dx;a.y=door->actor.y;a.z=door->actor.z+dz;a.room=door->actor.room;
        TombContact c={0};c.old_x=a.x;c.old_y=a.y;c.old_z=a.z;c.flags=24;
        int hit;assert(tomb_doors_collide(&objects,&a,&c,&p.animation,0,0,contact_query,&p,&hit));
        reacted+=hit!=0;pushed+=a.x!=door->actor.x+dx || a.z!=door->actor.z+dz;
        assert(abs(a.x-door->actor.x)<2000 && abs(a.z-door->actor.z)<2000);
    }
    assert(pushed && reacted);
    printf("PASS: moving-door terrain contact (%d pushes, %d reactions), camera shot lifetimes, targets, render rates and chase return\n",pushed,reacted);
    /* Real level floor triggers, object surfaces, falls, darts, damage and reset. */
    tomb_objects_reset(&objects);init(&p,l,v,sine);p.objects=&objects;
    p.lara.actor.x=36352;p.lara.actor.y=2048;p.lara.actor.z=74240;p.lara.actor.room=32;
    unsigned floor_sounds=0;int fell=0;
    for(int i=0;i<160;i++) {
        tick(&p,0);assert(!p.blocked);
        if(objects.items[50].actor.current==2)fell=1;
        for(unsigned j=0;j<p.sound_count;j++)if(p.sounds[j].id>=66 && p.sounds[j].id<=68)floor_sounds++;
    }
    fprintf(stderr,"floor state=%d y=%d Lara y=%d sounds=%u\n",objects.items[50].actor.current,objects.items[50].actor.y,p.lara.actor.y,floor_sounds);
    assert(fell && floor_sounds>=3 && objects.items[50].actor.current==3);
    tomb_objects_reset(&objects);assert(objects.items[50].actor.current==0 && l->items[50].state==0);
    for(size_t i=0;i<objects.count;i++)if(objects.items[i].object>=68 && objects.items[i].object<=70) {
        TombActor *b=&objects.items[i].actor;TombSectorRef ref;TombHeights h;
        assert(tomb_find_sector(l,b->x,b->y-1024,b->z,b->room,&ref));
        assert(tomb_item_heights(l,ref,b->x,b->y-1024,b->z,0,l->items,l->item_count,&h));
        assert(h.floor>=b->y && h.floor<b->y+512 && !h.object_references);
    }
    init(&p,l,v,sine);p.objects=&objects;p.lara.actor.x=74752;p.lara.actor.y=3072;p.lara.actor.z=22016;p.lara.actor.room=6;
    unsigned dart_sounds=0;int seen_effect=0;
    for(int i=0;i<180;i++){
        tick(&p,0);assert(!p.blocked);
        for(unsigned j=0;j<p.sound_count;j++)if(p.sounds[j].id==151)dart_sounds++;
        for(int j=0;j<256;j++)if(objects.hazards->effects[j].active)seen_effect=1;
    }
    assert(dart_sounds && seen_effect);
    fprintf(stderr,"darts spawned=%u hits=%u impacts=%u health=%d\n",objects.hazards->spawned,objects.hazards->hits,objects.hazards->impacts,p.lara.health);
    assert(objects.hazards->spawned && objects.hazards->hits && objects.hazards->impacts && p.lara.health<1000);
    tomb_objects_reset(&objects);assert(!objects.hazards->spawned && !objects.hazards->hits);
    for(int i=0;i<TOMB_DART_CAPACITY;i++)assert(!objects.hazards->darts[i].item.active);
    puts("PASS: Caves bridge surfaces, triggered collapsing floors/sounds, dart spawning/damage/impact and reset");
    tomb_objects_reset(&objects);init(&p,l,v,sine);p.objects=&objects;
    p.lara.actor.x=78336;p.lara.actor.y=3072;p.lara.actor.z=32256;p.lara.actor.room=4;p.lara.actor.yaw=0;
    tick(&p,0);assert(p.camera_request.flags==TOMB_CAMERA_LOOK && objects.camera.target==4 && (objects.items[4].actor.flags&64));
    assert(p.lara.head_yaw && p.lara.head_pitch && p.lara.head_yaw==p.lara.torso_yaw);
    for(int t=0;t<20;t++){tick(&p,0);assert(p.camera_request.flags==TOMB_CAMERA_LOOK);}
    p.lara.actor.x=73216;p.lara.actor.y=1024;p.lara.actor.z=14848;p.lara.actor.room=0;tick(&p,0);
    p.lara.actor.x=78336;p.lara.actor.y=3072;p.lara.actor.z=32256;p.lara.actor.room=4;tick(&p,0);
    assert(p.camera_request.flags!=TOMB_CAMERA_LOOK && objects.camera.target==-1);
    tomb_objects_reset(&objects);assert(!(objects.items[4].actor.flags&64));
    puts("PASS: Caves automatic point-of-interest look, head/torso turn, continuous cue, one-shot revisit and reset");
    tomb_objects_free(&objects);
    puts("PASS: closed-door collision, switch interaction, open-door traversal, timed double-door closure and reset");
    tomb_sound_bank_free(&bank);
    tomb_visual_free(v);tomb_level_free(l);
    puts("PASS: Caves start/run, forward/backward slides, jump-outs, flat-ground recovery, deferred non-door services and PCM bank");
    return 0;
}
