#include "playtest.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
static int ticks(TombPlaytest *p,unsigned input,int count) {
    int blocked=0;
    for(int i=0;i<count;i++) {
        TombActor before=p->lara.actor;
        tomb_playtest_tick(p,input); blocked+=p->blocked;
        TombActor *a=&p->lara.actor;
        assert(abs(a->x-before.x)<256 && abs(a->z-before.z)<256);
        assert(a->room>=0 && (size_t)a->room<p->level->room_count);
        assert(!(a->flags&8) || a->current==52 || a->current==53 || a->current==11 || a->current==3 || a->current==29 || a->current==9 || a->current==28 || (a->current>=25 && a->current<=27));
    }
    return blocked;
}
int main(int argc,char **argv) {
    assert(argc==3); char error[256]; int16_t sine[1025];
    FILE *f=fopen(argv[2],"rb"); assert(f); assert(fread(sine,sizeof sine,1,f)==1); fclose(f);
    TombLevel *l=tomb_level_load(argv[1],error,sizeof error); assert(l);
    TombVisual *visual=tomb_visual_load(l,error,sizeof error); assert(visual);
    TombPlaytest p; assert(tomb_playtest_init(&p,l,sine,visual));
    for(int side=0;side<2;side++) {
        assert(tomb_playtest_init(&p,l,sine,visual));
        p.lara.actor.x=50688;p.lara.actor.y=0;p.lara.actor.z=46592;p.lara.actor.room=9;p.lara.actor.yaw=0;
        int saw=0;for(int t=0;t<25;t++){assert(tomb_playtest_tick(&p,side?2048:1024));saw|=p.lara.actor.current==(side?21:22);}
        assert(saw && !p.lara.actor.yaw && (side?p.lara.actor.x>50688:p.lara.actor.x<50688));
        for(int t=0;t<40;t++)assert(tomb_playtest_tick(&p,0));assert(p.lara.actor.current==2);
    }
    assert(tomb_playtest_init(&p,l,sine,visual));
    TombActor origin=p.lara.actor;
    /* Complete standing roll: original turn effect, both phases and idle recovery. */
    assert(tomb_playtest_tick(&p,4096));assert(p.lara.actor.current==45);
    int continued=0;for(int t=0;t<60;t++){assert(tomb_playtest_tick(&p,0));continued|=p.lara.actor.current==23;}
    assert(continued && p.lara.actor.current==2 && (uint16_t)(p.lara.actor.yaw-origin.yaw)==32768);
    assert(tomb_playtest_init(&p,l,sine,visual));
    assert(ticks(&p,512|8|1,40)==0);
    assert(p.lara.actor.x==origin.x && p.lara.actor.z==origin.z && p.lara.actor.yaw==origin.yaw);
    assert(p.lara.head_yaw==8008 && p.lara.head_pitch==-7644 && p.camera_request.flags==512);
    assert(ticks(&p,0,70)==0);assert(!p.lara.head_yaw && !p.lara.head_pitch && !p.camera_request.flags);
    assert(tomb_playtest_init(&p,l,sine,visual));
    assert(ticks(&p,0,120)==0);
    assert(p.lara.actor.x==origin.x && p.lara.actor.y==origin.y && p.lara.actor.z==origin.z);
    assert(tomb_playtest_init(&p,l,sine,visual)); ticks(&p,129,45);
    int walk_distance=origin.x-p.lara.actor.x; assert(walk_distance>100);
    assert(tomb_playtest_init(&p,l,sine,visual)); ticks(&p,1,45);
    assert(origin.x-p.lara.actor.x>walk_distance);
    assert(tomb_playtest_init(&p,l,sine,visual)); ticks(&p,129,45); ticks(&p,0,90);
    TombActor stopped=p.lara.actor; assert(stopped.current==2);
    ticks(&p,0,60); assert(p.lara.actor.x==stopped.x && p.lara.actor.z==stopped.z);
    assert(tomb_playtest_init(&p,l,sine,visual)); ticks(&p,8,30); assert(p.lara.actor.yaw>origin.yaw);
    assert(tomb_playtest_init(&p,l,sine,visual)); ticks(&p,4,5); assert(p.lara.actor.yaw<origin.yaw);
    assert(tomb_playtest_init(&p,l,sine,visual)); ticks(&p,129,300);
    /* Starting room's window wall at x=35840, plus original radius 100. */
    assert(p.lara.actor.x>=35940 && p.lara.actor.x<36200);
    assert(tomb_playtest_init(&p,l,sine,visual));
    assert(ticks(&p,130,60)==0); /* slow + back */
    assert(p.lara.actor.x>origin.x+300 && p.lara.actor.yaw==origin.yaw);
    assert(p.lara.actor.current==16);
    assert(ticks(&p,0,90)==0); stopped=p.lara.actor; assert(stopped.current==2);
    assert(ticks(&p,0,30)==0); assert(p.lara.actor.x==stopped.x && p.lara.actor.z==stopped.z);
    assert(tomb_playtest_init(&p,l,sine,visual)); assert(ticks(&p,2,60)==0);
    assert(p.lara.actor.x>origin.x+500 && p.lara.actor.yaw==origin.yaw); /* Original bare-S hop. */
    assert(ticks(&p,0,90)==0); assert(p.lara.actor.current==2);
    assert(tomb_playtest_init(&p,l,sine,visual));
    int found=0;
    for(int i=0;i<120;i++) {
        assert(ticks(&p,1,1)==0);
        if(p.lara.actor.current==12) { found=1; break; }
    }
    assert(found && (p.lara.actor.animation==53 || p.lara.actor.animation==54));
    assert(ticks(&p,0,90)==0); assert(p.lara.actor.current==2);
    int wall_x=p.lara.actor.x; assert(wall_x>=35940);
    assert(ticks(&p,130,30)==0); assert(p.lara.actor.x>wall_x); /* Can retreat after recovery. */
    /* Exercise both original running-wall animation variants in real room geometry. */
    unsigned variants=0;
    for(int x=36100;x<=36600;x+=32) {
        assert(tomb_playtest_init(&p,l,sine,visual));
        p.lara.actor.x=x; p.lara.actor.y=-1536;
        p.lara.actor.current=p.lara.actor.goal=1; p.lara.actor.animation=0; p.lara.actor.frame=0;
        p.animation.move_angle=p.lara.actor.yaw;
        for(int i=0;i<60;i++) {
            assert(ticks(&p,1,1)==0);
            if(p.lara.actor.current==12) {
                if(p.lara.actor.animation==53) variants|=1;
                if(p.lara.actor.animation==54) variants|=2;
                break;
            }
        }
    }
    assert(variants==3);
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Backward hop must collide behind Lara, not in her facing direction. */
    p.lara.actor.x=36150; p.lara.actor.y=-1536; p.lara.actor.yaw=16384;
    assert(ticks(&p,2,60)==0); assert(p.lara.actor.x>=35940 && p.lara.actor.x<36200);
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Window ledge is 256 units above the room floor: the hop's >200 drop
       branch must transition to backward fall and land on the room floor. */
    p.lara.actor.x=36600; p.lara.actor.y=-1536;
    int saw_air=0,landed=0;
    for(int i=0;i<90;i++) {
        int blocked=ticks(&p,i<30?2:0,1); if(blocked) fprintf(stderr,"tick %d: %s (state %d, flags %u, y %d)\n",i,p.status,p.lara.actor.current,p.lara.actor.flags,p.lara.actor.y); assert(!blocked);
        if(p.lara.actor.flags&8) { saw_air=1; assert(p.lara.actor.current==29); }
        if(saw_air && !(p.lara.actor.flags&8) && p.lara.actor.y==-1280) landed=1;
    }
    assert(saw_air && landed && p.lara.actor.current==2);
    assert(p.lara.health==1000 && p.lara.sector_floor==-1280 && p.deferred_cd_track==26);
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Unsupported landing triggers must leave an airborne actor airborne,
       rather than resetting to an impossible standing pose in mid-air. */
    TombSectorRef landing_ref; TombHeights landing_heights;
    assert(tomb_find_sector(l,37000,-1280,51712,7,&landing_ref));
    assert(tomb_static_heights(l,landing_ref,37000,51712,0,&landing_heights));
    assert(landing_heights.trigger_index && landing_heights.trigger_index+2<l->floor_count);
    size_t action_index=landing_heights.trigger_index+2;
    uint16_t original_action=l->floor_data[action_index]; l->floor_data[action_index]=0xa400; /* secret action remains unsupported */
    p.lara.actor.x=36600; p.lara.actor.y=-1536;
    int guarded=0;
    for(int i=0;i<60;i++) {
        if(ticks(&p,2,1)) { guarded=1; break; }
    }
    assert(guarded && p.lara.actor.current==29 && (p.lara.actor.flags&8));
    assert(p.lara.health==1000 && !p.deferred_cd_track);
    l->floor_data[action_index]=original_action;
    /* Every supported CD request must permit all three landing paths. The
       old track-26 whitelist froze state 3/9/29 for every other track. */
    const int air_states[]={3,9,29},air_anims[]={34,93,93},air_frames[]={492,1473,1473};
    for(unsigned track=2;track<64;track++) {
        if(track==50) continue; /* Original level-completion side effect. */
        l->floor_data[action_index]=(uint16_t)(0xa000|track);
        for(int variant=0;variant<3;variant++) {
            assert(tomb_playtest_init(&p,l,sine,visual));
            p.lara.actor.x=37000; p.lara.actor.y=-1800;
            p.lara.actor.current=p.lara.actor.goal=(int16_t)air_states[variant];
            p.lara.actor.animation=(int16_t)air_anims[variant]; p.lara.actor.frame=(int16_t)air_frames[variant];
            p.lara.actor.flags|=8;
            assert(ticks(&p,0,120)==0);
            assert(p.lara.actor.current==2 && !(p.lara.actor.flags&8));
            assert(p.lara.actor.y==-1280 && p.lara.health==1000 && p.deferred_cd_track==track);
            assert(ticks(&p,130,10)==0); /* Controls recover after landing. */
        }
    }
    /* Validate the full list before publishing a request: a later gameplay
       action must not be hidden behind an audio action. Edits are in memory. */
    uint16_t tail=l->floor_data[action_index+1];
    l->floor_data[action_index]=0x201b;
    l->floor_data[action_index+1]=0xa01c;
    assert(tomb_playtest_init(&p,l,sine,visual));
    p.lara.actor.x=37000; p.lara.actor.y=-1280;
    p.air.land(&p,&p.lara.actor,NULL);
    assert(!p.blocked && p.deferred_cd_track==28);
    const uint16_t rejected[]={0x8000,0x8800,0xa001,0xa040};
    for(size_t i=0;i<sizeof rejected/sizeof rejected[0];i++) {
        l->floor_data[action_index+1]=rejected[i];
        assert(tomb_playtest_init(&p,l,sine,visual));
        p.lara.actor.x=37000; p.lara.actor.y=-1280;
        p.air.land(&p,&p.lara.actor,NULL);
        assert(p.blocked && !p.deferred_cd_track);
    }
    l->floor_data[action_index]=original_action;
    l->floor_data[action_index+1]=tail;
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Actual gym platform: audio 30 plus camera 0, ending on camera flags.
       All four original sectors must land, settle, and allow walking away. */
    for(int x=50688;x<=53760;x+=1024)for(int variant=0;variant<3;variant++) {
        assert(tomb_playtest_init(&p,l,sine,visual));
        p.lara.actor.x=x;p.lara.actor.y=-512;p.lara.actor.z=46592;p.lara.actor.room=9;
        p.lara.actor.current=p.lara.actor.goal=(int16_t)air_states[variant];
        p.lara.actor.animation=(int16_t)air_anims[variant];p.lara.actor.frame=(int16_t)air_frames[variant];
        p.lara.actor.flags|=8;
        assert(ticks(&p,0,120)==0);
        assert(p.lara.actor.current==2 && !(p.lara.actor.flags&8) && p.lara.actor.y==0);
        assert(p.deferred_cd_track==30 && p.deferred_camera==1 && p.deferred_camera_flags==0x8406);
        p.lara.actor.yaw=(int16_t)(x<52736?16384:-16384);
        int old_x=p.lara.actor.x;
        assert(ticks(&p,129,15)==0);assert(p.lara.actor.x!=old_x);
    }
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Reject missing camera records and gameplay actions after camera data
       without publishing the preceding audio/camera request. */
    assert(tomb_find_sector(l,50688,0,46592,9,&landing_ref));
    assert(tomb_static_heights(l,landing_ref,50688,46592,0,&landing_heights));
    size_t mixed=landing_heights.trigger_index;
    uint16_t saved_camera=l->floor_data[mixed+3],saved_flags=l->floor_data[mixed+4],saved_next=l->floor_data[mixed+5];
    for(int invalid=0;invalid<2;invalid++) {
        l->floor_data[mixed+3]=invalid?saved_camera:0x07ff;
        l->floor_data[mixed+4]=invalid?0x0406:saved_flags;
        l->floor_data[mixed+5]=0x8000;
        assert(tomb_playtest_init(&p,l,sine,visual));
        p.lara.actor.x=50688;p.lara.actor.y=0;p.lara.actor.z=46592;p.lara.actor.room=9;
        p.air.land(&p,&p.lara.actor,NULL);
        assert(p.blocked && !p.deferred_cd_track && !p.deferred_camera);
    }
    l->floor_data[mixed+3]=saved_camera;l->floor_data[mixed+4]=saved_flags;l->floor_data[mixed+5]=saved_next;
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Actual tall room: short backward fall -> fast fall -> nonfatal landing. */
    p.lara.actor.x=46592; p.lara.actor.y=-3000; p.lara.actor.z=41472; p.lara.actor.room=9;
    p.lara.actor.current=p.lara.actor.goal=29; p.lara.actor.animation=93; p.lara.actor.frame=1473;
    p.lara.actor.flags|=8;
    int saw_fast=0,saw_fast_land=0;
    for(int i=0;i<120;i++) {
        int blocked=ticks(&p,0,1);
        if(blocked) fprintf(stderr,"fast fall tick %d: %s\n",i,p.status);
        assert(!blocked);
        if(p.lara.actor.current==9) saw_fast=1;
        if(p.lara.actor.animation==24) saw_fast_land=1;
    }
    assert(saw_fast && saw_fast_land && p.lara.actor.current==2);
    assert(p.lara.actor.y==0 && !(p.lara.actor.flags&8));
    assert(p.lara.health>0 && p.lara.health<1000 && p.sound_stops==1);
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Backward fall into the window wall must enter state 9 and recover. */
    p.lara.actor.x=36000; p.lara.actor.y=-2000; p.lara.actor.yaw=16384;
    p.lara.actor.current=p.lara.actor.goal=29; p.lara.actor.animation=93; p.lara.actor.frame=1473;
    p.lara.actor.flags|=8; p.lara.actor.speed=42; p.animation.move_angle=-16384;
    int saw_impact=0;
    for(int i=0;i<90;i++) {
        assert(ticks(&p,0,1)==0);
        if(p.lara.actor.current==9) saw_impact=1;
    }
    assert(saw_impact && p.lara.actor.current==2 && !(p.lara.actor.flags&8));
    assert(p.lara.health==1000);
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Fatal falls commit damage and animate death instead of rolling back. */
    p.lara.actor.x=46592; p.lara.actor.y=-5400; p.lara.actor.z=41472; p.lara.actor.room=9;
    p.lara.actor.current=p.lara.actor.goal=29; p.lara.actor.animation=93; p.lara.actor.frame=1473;
    p.lara.actor.flags|=8;
    guarded=0;
    for(int i=0;i<180;i++)assert(ticks(&p,0,1)==0);
    assert(p.lara.health<=0 && p.lara.actor.current==8 && !(p.lara.actor.flags&8));
    assert(p.lara.actor.y==0 && p.sound_events>0);
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Actual room floor, starting from standing: run, take off, release and land. */
    p.lara.actor.x=46592; p.lara.actor.y=0; p.lara.actor.z=37000; p.lara.actor.room=9; p.lara.actor.yaw=0;
    assert(ticks(&p,1,20)==0); assert(p.lara.actor.current==1);
    int saw_jump=0,rose=0,landed_jump=0;
    for(int i=0;i<100;i++) {
        int blocked=ticks(&p,i<20?17:0,1);
        if(blocked) fprintf(stderr,"jump tick %d: %s state %d\n",i,p.status,p.lara.actor.current);
        assert(!blocked);
        if(p.lara.actor.current==3 && (p.lara.actor.flags&8)) saw_jump=1;
        if(p.lara.actor.y< -100) rose=1;
        if(saw_jump && !(p.lara.actor.flags&8) && p.lara.actor.current==2) landed_jump=1;
    }
    assert(saw_jump && rose && landed_jump && p.lara.health==1000 && p.lara.actor.y==0);
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Forward fall followed by a held-forward landing resumes running. */
    p.lara.actor.x=46592; p.lara.actor.y=-1000; p.lara.actor.z=40000; p.lara.actor.room=9; p.lara.actor.yaw=0;
    p.lara.actor.current=p.lara.actor.goal=3; p.lara.actor.animation=34; p.lara.actor.frame=492;
    p.lara.actor.flags|=8; p.lara.actor.speed=40;
    int resumed_run=0;
    for(int i=0;i<45;i++) {
        assert(ticks(&p,1,1)==0);
        if(!(p.lara.actor.flags&8) && p.lara.actor.current==1) resumed_run=1;
    }
    assert(resumed_run && p.lara.health==1000 && p.lara.actor.y==0);
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Standing jump: real animation preparation, takeoff and recovery. */
    for(int forward=0;forward<2;forward++) {
        assert(tomb_playtest_init(&p,l,sine,visual));
        p.lara.actor.x=46592; p.lara.actor.y=0; p.lara.actor.z=37000; p.lara.actor.room=9; p.lara.actor.yaw=0;
        int prepared=0,airborne=0;
        for(int i=0;i<130;i++) {
            int blocked=ticks(&p,i<15?(forward?17:16):0,1);
            if(blocked) fprintf(stderr,"standing jump %d tick %d: %s state %d\n",forward,i,p.status,p.lara.actor.current);
            assert(!blocked);
            if(p.lara.actor.current==15) prepared=1;
            if(p.lara.actor.flags&8) airborne=1;
        }
        assert(prepared && airborne && p.lara.actor.current==2 && p.lara.actor.y==0 && p.lara.health==1000);
        if(!forward) assert(abs(p.lara.actor.z-37000)<256); /* Original animation has root movement. */
        else assert(p.lara.actor.z>37500);
    }
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Face each tested direction into the same open gym corridor. This
       checks relative travel while avoiding unrelated unimplemented services. */
    const unsigned jump_inputs[]={18,24,20};
    const int16_t jump_yaws[]={-32768,-16384,16384};
    const int jump_states[]={25,26,27};
    for(int direction=0;direction<3;direction++) {
        assert(tomb_playtest_init(&p,l,sine,visual));
        p.lara.actor.x=46592; p.lara.actor.y=0; p.lara.actor.z=37000; p.lara.actor.room=9;
        p.lara.actor.yaw=jump_yaws[direction];
        int prepared=0,airborne=0;
        for(int i=0;i<130;i++) {
            int blocked=ticks(&p,i<15?jump_inputs[direction]:0,1);
            if(blocked) fprintf(stderr,"direction jump %d tick %d: %s state %d\n",direction,i,p.status,p.lara.actor.current);
            assert(!blocked);
            if(p.lara.actor.current==15) prepared=1;
            if(p.lara.actor.current==jump_states[direction] && (p.lara.actor.flags&8)) airborne=1;
        }
        assert(prepared && airborne && p.lara.actor.current==2 && p.lara.actor.y==0 && p.lara.health==1000);
        assert(p.lara.actor.z>37500 && p.lara.actor.yaw==jump_yaws[direction]);
        if(direction==0) assert(p.requested_camera_angle==24570);
        assert(ticks(&p,129,10)==0);
    }
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Each jump direction must also deflect from the actual window wall. */
    const int16_t impact_yaws[]={16384,-32768,0};
    for(int direction=0;direction<3;direction++) {
        assert(tomb_playtest_init(&p,l,sine,visual));
        p.lara.actor.x=36400; p.lara.actor.y=-1536; p.lara.actor.yaw=impact_yaws[direction];
        int impact=0;
        for(int i=0;i<130;i++) {
            assert(ticks(&p,i<15?jump_inputs[direction]:0,1)==0);
            if(p.lara.actor.current==9) impact=1;
            assert(p.lara.actor.x>=35840);
        }
        assert(impact && p.lara.actor.current==2 && !(p.lara.actor.flags&8) && p.lara.health==1000);
    }
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Artificial low ceiling: preparation must cancel before takeoff. */
    p.lara.actor.x=46592; p.lara.actor.y=0; p.lara.actor.z=37000; p.lara.actor.room=9; p.lara.actor.yaw=0;
    TombRoom *low_room=&l->rooms[9]; size_t sector_count=(size_t)low_room->nx*low_room->nz;
    int8_t *ceilings=malloc(sector_count); uint8_t *above=malloc(sector_count); assert(ceilings && above);
    for(size_t i=0;i<sector_count;i++) { ceilings[i]=low_room->sectors[i].ceiling; above[i]=low_room->sectors[i].above; low_room->sectors[i].above=255; low_room->sectors[i].ceiling=-2; }
    for(int i=0;i<30;i++) { assert(ticks(&p,16,1)==0); assert(!(p.lara.actor.flags&8) && p.lara.actor.y==0); }
    assert(p.lara.actor.current==2);
    for(size_t i=0;i<sector_count;i++) { low_room->sectors[i].ceiling=ceilings[i]; low_room->sectors[i].above=above[i]; }
    free(ceilings); free(above);
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Actual gym ledge: jump up, catch, hold, release and land. */
    p.lara.actor.x=47616; p.lara.actor.y=1024; p.lara.actor.z=35940;
    p.lara.actor.room=9; p.lara.actor.yaw=-32768;
    int caught=0;
    for(int i=0;i<75;i++) {
        assert(ticks(&p,i<15?80:64,1)==0);
        if(p.lara.actor.current==10) {
            caught=1; assert(!(p.lara.actor.flags&8) && p.animation.weapon_status==1);
        }
        if(i>20) assert(p.lara.actor.current==10);
    }
    assert(caught); TombActor held=p.lara.actor;
    assert(ticks(&p,64,30)==0);
    assert(p.lara.actor.x==held.x && p.lara.actor.y==held.y && p.lara.actor.z==held.z);
    /* The balcony railing is a static obstruction: do not pull through it. */
    assert(ticks(&p,65,45)==0); assert(p.lara.actor.current==10 && p.static_hit);
    assert(ticks(&p,0,1)==0);
    assert(p.lara.actor.current==28 && (p.lara.actor.flags&8) && p.animation.weapon_status==0);
    assert(ticks(&p,0,120)==0);
    assert(p.lara.actor.current==2 && p.lara.actor.y==1024 && p.lara.health==1000);
    assert(ticks(&p,2,10)==0);
    /* Same real ledge: both pull-up animations and both lateral directions. */
    const unsigned hang_inputs[]={65,193,68,72};
    for(int variant=0;variant<4;variant++) {
        assert(tomb_playtest_init(&p,l,sine,visual));
        p.lara.actor.x=50076; p.lara.actor.y=2560; p.lara.actor.z=39424;
        p.lara.actor.room=9; p.lara.actor.yaw=16384;
        assert(ticks(&p,80,15)==0); assert(ticks(&p,64,60)==0); assert(p.lara.actor.current==10);
        int saw_state=0; int wanted=variant==0?19:variant==1?54:variant==2?30:31;
        int start_z=p.lara.actor.z;
        for(int i=0;i<(variant<2?240:45);i++) {
            int blocked=ticks(&p,hang_inputs[variant],1);
            if(blocked) fprintf(stderr,"hang variant%d tick%d: %s state%d anim%d frame%d\n",variant,i,p.status,p.lara.actor.current,p.lara.actor.animation,p.lara.actor.frame);
            assert(!blocked);
            if(p.lara.actor.current==wanted) saw_state=1;
            if(variant<2 && saw_state && p.lara.actor.current==2) break;
        }
        assert(saw_state);
        if(variant<2) {
            assert(p.lara.actor.current==2 && p.lara.actor.y<2560 && p.animation.weapon_status==0);
            assert(ticks(&p,0,30)==0);
        } else {
            if(variant==2) assert(p.lara.actor.z>start_z); else assert(p.lara.actor.z<start_z);
            assert(ticks(&p,hang_inputs[variant],180)==0);
            assert(!(p.lara.actor.flags&8)); /* Stop at the platform edge, without falling through. */
            assert(ticks(&p,64,60)==0); assert(p.lara.actor.current==10);
            assert(ticks(&p,0,120)==0); assert(p.lara.actor.current==2);
        }
    }
    /* The same upward jump without Action must never catch. */
    assert(tomb_playtest_init(&p,l,sine,visual));
    p.lara.actor.x=47616; p.lara.actor.y=1024; p.lara.actor.z=35940;
    p.lara.actor.room=9; p.lara.actor.yaw=-32768;
    for(int i=0;i<120;i++) { assert(ticks(&p,i<15?16:0,1)==0); assert(p.lara.actor.current!=10); }
    assert(p.lara.actor.current==2 && p.animation.weapon_status==0);
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Running jump -> reach -> catch -> hang -> release on real gym geometry. */
    assert(tomb_playtest_init(&p,l,sine,visual));
    p.lara.actor.x=47616; p.lara.actor.y=768; p.lara.actor.z=38140; p.lara.actor.room=9; p.lara.actor.yaw=-32768;
    int reached=0,forward_caught=0;
    for(int i=0;i<110;i++) {
        assert(ticks(&p,i<20?1:i<40?81:64,1)==0);
        if(p.lara.actor.current==11) reached=1;
        if(reached && p.lara.actor.current==10) forward_caught=1;
    }
    assert(reached && forward_caught && p.animation.weapon_status==1);
    assert(ticks(&p,0,120)==0 && p.lara.actor.current==2 && p.animation.weapon_status==0);
    /* Two-click, three-click and high assisted jump-to-grab approaches. */
    const int vault_positions[3][5]={{42908,-1280,52736,7,16384},{49664,2560,40860,9,0},{47616,1024,35940,9,-32768}};
    for(int variant=0;variant<3;variant++) {
        assert(tomb_playtest_init(&p,l,sine,visual)); TombActor *a=&p.lara.actor;
        a->x=vault_positions[variant][0];a->y=vault_positions[variant][1];a->z=vault_positions[variant][2];a->room=(int16_t)vault_positions[variant][3];a->yaw=(int16_t)vault_positions[variant][4];
        int seen=0,done=0;
        for(int i=0;i<180;i++) {
            assert(ticks(&p,seen?64:65,1)==0);
            if(a->animation==(variant==0?50:variant==1?42:28) || (variant==2 && a->current==28)) seen=1;
            if(seen && a->current==(variant==2?10:2)) {done=1;break;}
        }
        assert(seen && done);
        if(variant<2) { assert(a->y==vault_positions[variant][1]-(variant==0?512:768));assert(p.animation.weapon_status==0); }
    }
    /* Enter the actual pool from dry ground, swim, surface and climb out. */
    assert(tomb_playtest_init(&p,l,sine,visual));
    p.lara.actor.x=40448;p.lara.actor.y=3328;p.lara.actor.z=57800;p.lara.actor.room=13;p.lara.actor.yaw=0;
    int entered=0,surfaced=0,exited=0;
    for(int i=0;i<350;i++) {
        unsigned in=p.lara.water_status==0?(i<35?1:0):p.lara.water_status==1?18:65;
        assert(ticks(&p,in,1)==0);
        if(p.lara.water_status==1)entered=1;
        if(p.lara.water_status==2)surfaced=1;
        if(p.lara.actor.current==55)exited=1;
    }
    assert(entered && surfaced && exited && p.lara.actor.current==2 && p.lara.actor.room==13 && p.lara.actor.y==3328 && p.lara.health==1000 && p.animation.weapon_status==0 && p.bubble_events>0);
    assert(ticks(&p,0,180)==0 && p.gym.complete);
    assert(tomb_playtest_init(&p,l,sine,visual));
    p.lara.actor.x=40448;p.lara.actor.y=3585;p.lara.actor.z=60928;p.lara.actor.room=14;p.lara.actor.yaw=0;
    p.lara.actor.current=p.lara.actor.goal=33;p.lara.actor.animation=110;p.lara.actor.frame=1808;p.lara.water_status=2;
    for(int t=0;t<30;t++)assert(tomb_playtest_tick(&p,512|8|1));
    assert(p.camera_request.flags==512 && p.lara.actor.current==33 && !p.lara.actor.yaw);
    assert(p.lara.actor.x==40448 && p.lara.actor.z==60928 && p.lara.head_yaw==9282 && p.lara.head_pitch==-7644);
    assert(p.lara.torso_yaw==4641 && !p.lara.torso_pitch);
    for(int t=0;t<70;t++)assert(tomb_playtest_tick(&p,0));assert(!p.lara.head_yaw && !p.lara.head_pitch);
    /* Surface controls: both lateral directions, backward, dive and resurface. */
    for(int variant=0;variant<4;variant++) {
        assert(tomb_playtest_init(&p,l,sine,visual)); TombActor *a=&p.lara.actor;
        a->x=40448;a->y=3585;a->z=60928;a->room=14;a->yaw=0;
        a->current=a->goal=33;a->animation=110;a->frame=1808;p.lara.water_status=2;
        int saw=0;unsigned in=variant==0?1024:variant==1?2048:variant==2?2:16;
        for(int i=0;i<50;i++){assert(ticks(&p,in,1)==0);if(a->current==(variant==0?48:variant==1?49:variant==2?47:35))saw=1;}
        assert(saw);
        if(variant==0)assert(a->x<40448);else if(variant==1)assert(a->x>40448);else if(variant==2)assert(a->z<60928);
        else {
            assert(p.lara.water_status==1);
            for(int i=0;i<220 && p.lara.water_status!=2;i++)assert(ticks(&p,18,1)==0);
            assert(p.lara.water_status==2 && p.lara.actor.y==3585 && p.lara.health==1000);
        }
    }
    /* End-to-end underwater pitch, in open water at rest. DOS uses 364 turn
       units per tick: approximately 60 degrees/second at the 30 Hz game clock. */
    assert(tomb_playtest_init(&p,l,sine,visual));
    p.lara.actor.x=40448;p.lara.actor.y=4800;p.lara.actor.z=60928;p.lara.actor.room=14;
    p.lara.actor.current=p.lara.actor.goal=13;p.lara.actor.animation=108;p.lara.actor.frame=1736;p.lara.water_status=1;
    for(int i=0;i<30;i++){assert(ticks(&p,2,1)==0);assert(p.lara.pitch==(i+1)*364);}
    for(int i=0;i<60;i++){assert(ticks(&p,1,1)==0);assert(p.lara.pitch==(29-i)*364);}
    /* Run out of air, transition through the original drown animation, float
       toward the surface, ignore movement inputs, then reset every latch. */
    assert(tomb_playtest_init(&p,l,sine,visual));
    p.lara.actor.x=40448;p.lara.actor.y=4800;p.lara.actor.z=60928;p.lara.actor.room=14;
    p.lara.actor.current=p.lara.actor.goal=13;p.lara.actor.animation=108;p.lara.actor.frame=1736;
    p.lara.water_status=1;p.lara.air=0;p.lara.health=5;
    for(int i=0;i<240;i++)assert(tomb_playtest_tick(&p,0));
    assert(p.lara.health==-1 && p.lara.actor.current==44 && p.dead_ticks>0);
    assert(p.lara.actor.y<4800 && p.lara.water_status==1);
    int dead_x=p.lara.actor.x,dead_z=p.lara.actor.z,dead_yaw=p.lara.actor.yaw;
    for(int i=0;i<120;i++)assert(tomb_playtest_tick(&p,1|4|16));
    assert(p.lara.actor.x==dead_x && p.lara.actor.z==dead_z && p.lara.actor.yaw==dead_yaw);
    assert(tomb_playtest_init(&p,l,sine,visual));
    assert(p.lara.health==1000 && p.lara.air==1800 && !p.dead_ticks && !p.gym.complete && !p.gym.current_track);
    /* Actual exit animation primes track 50; exactly 120 subsequent calls
       on that trigger complete the gym. Reset permits the tutorial again. */
    TombGym g={0};
    tomb_gym_audio(&g,50,0x3f00,0,2);assert(!g.current_track && !g.complete);
    tomb_gym_audio(&g,50,0x3f00,0,55);assert(g.current_track==50 && g.tracks[50]==0x3f00);
    for(int i=0;i<119;i++){tomb_gym_audio(&g,50,0x3f00,0,2);assert(!g.complete);}
    tomb_gym_audio(&g,50,0x3f00,0,2);assert(g.complete);
    p.gym=g;TombActor completed=p.lara.actor;
    assert(tomb_playtest_tick(&p,1|16));assert(p.lara.actor.x==completed.x && p.lara.actor.z==completed.z);
    assert(tomb_playtest_init(&p,l,sine,visual));assert(!p.gym.complete && !p.gym.tracks[50]);
    /* The actual mixed platform starts voice 30 and camera 0 once on entry. */
    p.lara.actor.x=50688;p.lara.actor.y=0;p.lara.actor.z=46592;p.lara.actor.room=9;
    assert(tomb_playtest_tick(&p,0));assert(p.gym.current_track==30 && p.gym.camera==1 && p.gym.camera_timer==180);
    unsigned serial=p.gym.audio_serial;
    for(int i=0;i<200;i++)assert(tomb_playtest_tick(&p,0));
    assert(p.gym.audio_serial==serial && !p.gym.camera);
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Walk + forward jump requests the swan dive; low landings recover. */
    assert(tomb_playtest_init(&p,l,sine,visual));
    p.lara.actor.x=40448;p.lara.actor.y=3328;p.lara.actor.z=57800;p.lara.actor.room=13;p.lara.actor.yaw=0;
    int swan_seen=0,swan_water=0;
    for(int i=0;i<100;i++){
        assert(ticks(&p,p.lara.water_status?16:145,1)==0);
        swan_seen|=p.lara.actor.current==52;swan_water|=p.lara.water_status==1;
    }
    assert(swan_seen && swan_water && p.lara.health==1000);
    for(int fatal=0;fatal<2;fatal++){
        assert(tomb_playtest_init(&p,l,sine,visual));TombActor *a=&p.lara.actor;
        a->x=49664;a->y=2300;a->z=40000;a->room=9;a->yaw=0;
        a->current=a->goal=fatal?53:52;a->flags|=8;a->fall_speed=fatal?160:30;
        for(size_t j=0;j<l->animation_count;j++)if(l->animations[j].state==a->current){a->animation=(int16_t)j;a->frame=l->animations[j].first_frame;break;}
        for(int i=0;i<140;i++){int blocked=ticks(&p,0,1);if(blocked)fprintf(stderr,"swan blocked %s state=%d goal=%d frame=%d\n",p.status,a->current,a->goal,a->frame);assert(!blocked);}
        printf("swan fatal=%d health=%d state=%d goal=%d y=%d frame=%d\n",fatal,p.lara.health,a->current,a->goal,a->y,a->frame);fflush(stdout);
        assert(fatal?(p.lara.health<0 && a->current==8):(p.lara.health==1000 && a->current==2));
    }
    assert(tomb_playtest_init(&p,l,sine,visual));
    /* Deliberately unsupported effect/traversal states are not silently simulated. */
    p.lara.actor.current=60; TombActor unsupported=p.lara.actor;
    assert(!tomb_playtest_tick(&p,1)); assert(p.lara.actor.x==unsupported.x);
    tomb_visual_free(visual);
    tomb_level_free(l);
    puts("PASS: gym idle, walk/run speed, release-to-stop, turning, window collision, backward walk/hop, both wall-hit variants/recovery, backward/fast/forward fall, running jump/landing, damage, 183 audio-trigger landings, 12 platform audio/camera landings, mixed-trigger guards, standing jumps, ledge catch/hold/release, pull-ups, shimmy/edge stops forward catches, standing vaults, complete pool traversal, surface directions/dive, fatal falls, drowning, tutorial/camera triggers, completion and reset");
    return 0;
}
