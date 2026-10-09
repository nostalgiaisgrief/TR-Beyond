/* DOS behaviour is the specification: see compare_dos_camera.py.
   Legacy assertions demanding motionless bounds and custom static clearance
   were removed because they tested the superseded camera design. */
#include "follow_camera.h"
#include "playtest.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv) {
    assert(argc==3);char error[256];int16_t sine[1025];
    FILE *f=fopen(argv[2],"rb");assert(f);assert(fread(sine,sizeof sine,1,f)==1);fclose(f);
    TombLevel *l=tomb_level_load(argv[1],error,sizeof error);assert(l);TombVisual *v=tomb_visual_load(l,error,sizeof error);assert(v);
    FILE *log=fopen("build/dos-camera-route.csv","w");assert(log);
    fputs("scenario,tick,x,y,z,yaw,room,animation,frame,pitch,angle,elevation,distance,flags,eye_x,eye_y,eye_z,eye_room,target_x,target_y,target_z,target_room,shift\n",log);
    TombFollowCamera c={0};
    unsigned checks=0;
    for(int scenario=0;scenario<5;scenario++) {
        TombPlaytest p;assert(tomb_playtest_init(&p,l,sine,v));memset(&c,0,sizeof c);
        if(scenario==2){p.lara.actor.x=40448;p.lara.actor.y=3328;p.lara.actor.z=57800;p.lara.actor.room=13;p.lara.actor.yaw=0;p.animation.move_angle=0;}
        if(scenario==3){p.lara.actor.x=50076;p.lara.actor.y=2560;p.lara.actor.z=39424;p.lara.actor.room=9;p.lara.actor.yaw=16384;}
        if(scenario==4){p.lara.actor.x=49664;p.lara.actor.y=2560;p.lara.actor.z=40860;p.lara.actor.room=9;p.lara.actor.yaw=0;}
        for(int t=0;t<360;t++) {
            unsigned in=scenario==0?(t<90?129:0):scenario==1?(t<180?8:0):scenario==2?(p.lara.water_status==0?(t<35?1:0):p.lara.water_status==1?18:65):scenario==3?(t<15?80:t<75?64:t<200?65:0):(t<3?65:64);
            tomb_playtest_tick(&p,in);p.camera_request.pitch=p.lara.pitch;
            assert(tomb_camera_tick(&c,l,v,&p.lara.actor,0,sine,&p.camera_request));checks++;
            const TombActor *a=&p.lara.actor;const TombCameraRequest *r=&p.camera_request;
            fprintf(log,"%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n",scenario,t,a->x,a->y,a->z,a->yaw,a->room,a->animation,a->frame,r->pitch,r->angle,r->elevation,r->distance,r->flags,c.dos.eye.x,c.dos.eye.y,c.dos.eye.z,c.dos.eye.room,c.dos.target.x,c.dos.target.y,c.dos.target.z,c.dos.target.room,c.dos.shift);
            for(int i=0;i<3;i++)assert(isfinite(c.eye[i]) && isfinite(c.target[i]));
            assert(c.room>=0 && (size_t)c.room<l->room_count);

        }
    }

    fclose(log);tomb_visual_free(v);tomb_level_free(l);
    printf("PASS: %u gameplay/camera ticks; recorded for full DOS camera comparison\n",checks);
    return 0;
}
