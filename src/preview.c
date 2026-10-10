#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <mmsystem.h>
#include <GL/gl.h>
#include <math.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "visual.h"
#include "lighting.h"
#include "object_contact.h"
#include "lara_start.h"
#include "fixed.h"
#include "preview_camera.h"
#include "follow_camera.h"
#include "hazards.h"
#include "enemies.h"
#include "combat.h"
#include "progression.h"
#include "peru.h"
#include "text.h"
#include "ring.h"
#include "room_visibility.h"
#include "preview_pose.h"
#include "render_interpolation.h"
#include "playtest.h"
#include "sound_win.h"
#include "level_select.h"
#include "city.h"
#include "save.h"

/* Modern presentation of reconstructed DOS simulation and lighting. */
static TombVisual *visual;
static TombLevel *level;
static TombLaraStart start;
static GLuint *tiles;
static TombPlaytest play;
static TombObjects objects;
static int16_t sine_table[1025];
static int pose_mode=0,caves=0;
static double accumulator=0,camera_alpha=1;
static int running=1, paused=0, animation=11, width=960, height=720;
static double orbit=0, distance=1536, elapsed=0, camera_hold=0;
static TombFollowCamera camera;
static int camera_bounce;
static TombScreenRect *room_rects;
static int manual_camera=0;
static int playing_track=0,audio_paused=0;
static char audio_error[128];
static TombSoundBank sound_bank;
static TombSoundMixer sound_mixer,ring_sound_mixer;
static TombSoundOutput *sound_output,*ring_sound_output;
static int sound_failed;
static int draw_requested;
static void render_reset(void);
static int inventory_key_only,inventory_ring_current[3];
static int inventory_open,inventory_selected,inventory_stats,inventory_keys,level_number=1;
static int inventory_capture,transition_test,peru_test;
static TombRing inventory_ring;
static double inventory_accumulator;
static unsigned inventory_input;
static int ring_capture=-1,ring_object=99;
static int16_t compass_angle,compass_velocity;
static GLuint *font_tiles;
static TombInventory level_inventory;
static int load_next_level(void);
static int title_mode,options_ring,death_menu,slot_menu,slot_current,menu_action,option_row;
static int new_game_menu,new_game_level=1;
static int save_levels[16],settings_music=10,settings_sound=10,settings_detail=2;
static int front_capture,front_test;
static int lighting_test,interpolation_test;
static char menu_error[128];
static TombLevel *title_level;
static TombVisual *title_visual;
static GLuint *title_tiles,*title_font_tiles,title_backdrop;
static unsigned bindings[13]={VK_NUMPAD8,VK_NUMPAD2,VK_NUMPAD4,VK_NUMPAD6,VK_NUMPAD7,VK_NUMPAD9,'A','D','S',VK_SPACE,'W',VK_NUMPAD0,'E'};
static const char *binding_names[13]={"Run","Back","Left","Right","Step Left","Step Right","Walk","Jump","Action","Draw Weapon","Roll","Look","Inventory"};
static int binding_wait;
static void inventory_begin(void);
static void refresh_slots(void);
static int backdrop_dirty,backdrop_shade;
static void frontend_title(void);
static void ui_text(int,int,const char *,unsigned);
static int load_game_level(int,int,const char *);
static void asset_path(char *path,const char *file){GetModuleFileNameA(NULL,path,MAX_PATH);char *end=strrchr(path,'\\');if(end)snprintf(end,(size_t)(path+MAX_PATH-end),"/../work/reference-assets/DATA/%s",file);}
static void save_path(char *path,int slot){GetModuleFileNameA(NULL,path,MAX_PATH);char *end=strrchr(path,'\\');if(end){strcpy(end,front_test?"/test-saves":"/../saves");CreateDirectoryA(path,NULL);snprintf(end,(size_t)(path+MAX_PATH-end),front_test?"/test-saves/slot%02d.tsv":"/../saves/slot%02d.tsv",slot+1);}}
static void settings_path(char *path){GetModuleFileNameA(NULL,path,MAX_PATH);char *end=strrchr(path,'\\');if(end)strcpy(end,"/../settings.ini");}
static void settings_write(void){if(front_test)return;char path[MAX_PATH],value[32],key[32];settings_path(path);int values[3]={settings_music,settings_sound,settings_detail};for(int i=0;i<16;i++){snprintf(key,sizeof key,"value%d",i);snprintf(value,sizeof value,"%u",i<3?(unsigned)values[i]:bindings[i-3]);WritePrivateProfileStringA("Tomb",key,value,path);}}
static void settings_read(void){char path[MAX_PATH],key[32];settings_path(path);for(int i=0;i<16;i++){snprintf(key,sizeof key,"value%d",i);unsigned def=i==2?2:i<3?10:bindings[i-3];unsigned v=GetPrivateProfileIntA("Tomb",key,(int)def,path);if(i<2 && v<=10){if(i==0)settings_music=(int)v;else settings_sound=(int)v;}else if(i==2 && v<=2)settings_detail=(int)v;else if(i>=3 && v>0 && v<256)bindings[i-3]=v;}}

static void sound_tick(void) {
    double listener[3]={play.lara.actor.x,play.lara.actor.y-450,play.lara.actor.z};
    int room=play.lara.actor.room;
    if(camera.ready){memcpy(listener,camera.target,sizeof listener);room=camera.room;}
    int wet=room>=0 && (size_t)room<level->room_count && (level->rooms[room].flags&1);
    for(unsigned i=0;i<play.sound_count;i++)tomb_sound_output_event(sound_output,play.sounds+i,wet,listener);
}

static TombSoundOutput *music_output;
static TombSoundMixer music_mixer;
static TombSoundBank music_bank;
static TombSoundSample music_sample;
static unsigned char *music_data;
static void audio_stop(void) {
    tomb_sound_output_close(music_output);music_output=NULL;free(music_data);music_data=NULL;playing_track=0;audio_paused=0;audio_error[0]=0;
}
static void audio_update(int suspended) {
    int track=title_mode?2:caves?objects.progress->music.current_track:play.gym.current_track;
    if(track!=playing_track) {
        audio_stop();playing_track=track;
        if(track) {
            char file[MAX_PATH],base[MAX_PATH];GetModuleFileNameA(NULL,base,MAX_PATH);char *end=strrchr(base,'\\');if(end)*end=0;
            int source=tomb_music_source(track);snprintf(file,sizeof file,"%s/../work/reference-assets/audio/%s%02d.wav",base,source>0?"cd":"track",source>0?source:track);
            FILE *f=fopen(file,"rb");long bytes=0;
            if(f){if(!fseek(f,0,SEEK_END))bytes=ftell(f);rewind(f);if(bytes>0 && bytes<100000000)music_data=malloc((size_t)bytes);if(music_data && fread(music_data,1,(size_t)bytes,f)!=(size_t)bytes){free(music_data);music_data=NULL;}fclose(f);}
            if(music_data && tomb_sound_sample(&music_sample,music_data,(size_t)bytes)){
                memset(&music_bank,0,sizeof music_bank);music_bank.samples=&music_sample;music_bank.sample_count=1;tomb_sound_init(&music_mixer,&music_bank);
                music_mixer.voices[0]=(TombSoundVoice){1,0,0,32767,100,source>0?2:0,0};music_output=tomb_sound_output_open(&music_mixer);
            }
            if(!music_output)snprintf(audio_error,sizeof audio_error,"Music track %d unavailable",track);
        }
    }
    tomb_sound_output_volume(music_output,settings_music);
    if(music_output)tomb_sound_output_update(music_output,title_mode?0:suspended);
    tomb_sound_output_volume(sound_output,settings_sound);tomb_sound_output_volume(ring_sound_output,settings_sound);
}
static void update_camera(double dt) {
    (void)dt;
    if(!caves) {
        tomb_objects_camera_begin(&objects);
        TombSectorRef ref;TombHeights h;const TombActor *a=&play.lara.actor;
        if(tomb_find_sector(level,a->x,a->y,a->z,a->room,&ref) && tomb_static_heights(level,ref,a->x,a->z,0,&h))
            tomb_objects_trigger(&objects,h.trigger_index,h.floor==a->y);
    }
    if(objects.peru && objects.peru->scion_item>=0){
        TombDosCamera shot={0};int fov,roll;
        if(tomb_scion_camera(&objects,sine_table,&shot,&fov,&roll)){
            int cut=!camera.ready || camera.fixed_target!=-2;
            for(int i=0;i<3;i++){camera.previous_eye[i]=camera.eye[i];camera.previous_target[i]=camera.target[i];}
            camera.eye[0]=shot.eye.x;camera.eye[1]=shot.eye.y;camera.eye[2]=shot.eye.z;
            camera.target[0]=shot.target.x;camera.target[1]=shot.target.y;camera.target[2]=shot.target.z;
            if(cut){memcpy(camera.previous_eye,camera.eye,sizeof camera.eye);memcpy(camera.previous_target,camera.target,sizeof camera.target);}
            camera.dos=shot;camera.room=shot.eye.room;camera.ready=1;camera.fixed_target=-2;
            return;
        }
    }
    if(camera.fixed_target==-2){camera.ready=0;camera.dos.ready=0;camera.fixed_target=0;}
    if(!camera.ready)camera_bounce=0;
    for(unsigned i=0;i<play.sound_count;i++)if(play.sounds[i].kind==8){
        TombActor impact={0};impact.x=play.sounds[i].x;impact.y=play.sounds[i].y;impact.z=play.sounds[i].z;
        camera_bounce=tomb_dos_camera_stomp(&camera.dos.eye,&impact,camera_bounce);
    }
    TombActor focus=play.lara.actor;int object=0;TombCameraRequest r=play.camera_request;
    r.pitch=play.lara.pitch;r.angle=tomb_word((int)r.angle+(int)(orbit*10430.378350470453));
    if(distance!=1536)r.distance=(int32_t)distance;
    if(objects.camera.active && !(r.flags&(TOMB_CAMERA_COMBAT|TOMB_CAMERA_LOOK))) {
        r.fixed_index=(int16_t)objects.camera.index;r.speed=objects.camera.speed;
        if(objects.camera.target>=0) {
            size_t id=(size_t)objects.camera.target;const TombItem *p=level->items+id;TombModel m;
            if(!tomb_visual_model(visual,p->object,&m))return;
            object=p->object;r.item_target=1;focus=(TombActor){0};focus.x=p->x;focus.y=p->y;focus.z=p->z;focus.room=p->room;focus.yaw=p->yaw;
            focus.animation=(int16_t)m.animation;focus.frame=level->animations[m.animation].first_frame;
            if(object==55 || (object>=57 && object<=64))focus=objects.items[id].actor;
        }
    }
    if(!tomb_camera_tick_effects(&camera,level,visual,&focus,object,sine_table,&r,&camera_bounce,&objects.enemies->random))play.status="DOS camera query failed";
    if(objects.enemies)for(int i=0;i<3;i++)objects.enemies->camera[i]=(int32_t)camera.eye[i];
    objects.peru->camera_target_y=(int32_t)camera.target[1];
}
static void pool_start(void) {
    tomb_objects_reset(&objects);
    audio_stop();tomb_sound_output_reset(sound_output);camera.ready=0;render_reset();paused=0;camera_hold=0;
    tomb_playtest_init(&play,level,sine_table,visual);
    play.lara.actor.x=40448; play.lara.actor.y=3328; play.lara.actor.z=57800;
    play.lara.actor.room=13; play.lara.actor.yaw=0;
    play.animation.move_angle=0;
}
/* Reproducible Caves slope fixture, also used by the native integration test. */
static void slope_start(int backward) {
    tomb_objects_reset(&objects);
    audio_stop();tomb_sound_output_reset(sound_output);camera.ready=0;render_reset();paused=0;camera_hold=0;
    orbit=0;distance=1536;elapsed=0;accumulator=0;pose_mode=0;
    tomb_playtest_init(&play,level,sine_table,visual);play.movement_only=1;play.objects=&objects;
    TombActor *a=&play.lara.actor;
    a->x=73216;a->y=1024;a->z=14848;a->room=0;a->yaw=backward?-16384:16384;
    play.animation.move_angle=a->yaw;
}
static void switch_start(int which) {
    static const unsigned switches[3]={10,42,52};
    tomb_objects_reset(&objects);
    audio_stop();tomb_sound_output_reset(sound_output);camera.ready=0;render_reset();paused=0;camera_hold=0;
    orbit=0;distance=1536;elapsed=0;accumulator=0;pose_mode=0;
    tomb_playtest_init(&play,level,sine_table,visual);play.movement_only=1;play.objects=&objects;
    const TombActor *s=&objects.items[switches[which]].actor;TombActor *a=&play.lara.actor;
    a->x=s->x+(s->yaw==16384?400:s->yaw==-16384?-400:0);
    a->z=s->z+(s->yaw==0?400:s->yaw==-32768?-400:0);
    a->y=s->y;a->room=s->room;a->yaw=s->yaw;play.animation.move_angle=a->yaw;
}
static void hazard_start(int which) {
    tomb_objects_reset(&objects);audio_stop();tomb_sound_output_reset(sound_output);
    camera.ready=0;render_reset();paused=0;camera_hold=0;orbit=0;distance=1536;elapsed=0;accumulator=0;pose_mode=0;
    tomb_playtest_init(&play,level,sine_table,visual);play.movement_only=1;play.objects=&objects;
    TombActor *a=&play.lara.actor;
    if(which==0){a->x=25088;a->y=4607;a->z=54784;a->room=14;a->yaw=-32768;}
    else if(which==1){a->x=36352;a->y=2048;a->z=74240;a->room=32;a->yaw=0;}
    else {a->x=74752;a->y=3072;a->z=22016;a->room=6;a->yaw=0;}
    play.animation.move_angle=a->yaw;
}
static void combat_start(int species) {
    audio_stop();tomb_sound_output_reset(sound_output);camera.ready=0;render_reset();paused=0;camera_hold=0;
    orbit=0;distance=1536;elapsed=0;accumulator=0;pose_mode=0;draw_requested=0;
    if(tomb_combat_fixture(&play,&objects,sine_table,species)<0)play.status="Combat fixture unavailable";
}
static void pickup_start(int large) {
    audio_stop();tomb_sound_output_reset(sound_output);camera.ready=0;render_reset();paused=0;camera_hold=0;
    orbit=0;distance=1536;elapsed=0;accumulator=0;pose_mode=0;draw_requested=0;inventory_open=0;
    if(tomb_pickup_fixture(&play,&objects,sine_table,large)<0)play.status="Pickup fixture unavailable";
}
static void city_start(int which) {
    audio_stop();tomb_sound_output_reset(sound_output);camera.ready=0;render_reset();paused=0;camera_hold=0;
    orbit=0;distance=1536;elapsed=0;accumulator=0;pose_mode=0;draw_requested=0;inventory_open=0;
    if(!tomb_city_fixture(&play,&objects,sine_table,which))play.status="City fixture unavailable";
}
static void interest_start(void){
    tomb_objects_reset(&objects);audio_stop();tomb_sound_output_reset(sound_output);camera.ready=0;render_reset();paused=0;camera_hold=0;accumulator=0;inventory_open=0;draw_requested=0;
    tomb_playtest_init(&play,level,sine_table,visual);play.objects=&objects;play.movement_only=1;
    play.lara.actor.x=78336;play.lara.actor.y=3072;play.lara.actor.z=32256;play.lara.actor.room=4;play.lara.actor.yaw=0;
}
static void finish_start(void) {
    tomb_objects_reset(&objects);audio_stop();tomb_sound_output_reset(sound_output);camera.ready=0;render_reset();paused=0;camera_hold=0;orbit=0;distance=1536;elapsed=0;accumulator=0;pose_mode=0;inventory_open=0;
    tomb_playtest_init(&play,level,sine_table,visual);play.movement_only=1;play.objects=&objects;
    if(level_number==2){play.lara.actor.x=9728;play.lara.actor.y=-1024;play.lara.actor.z=29184;play.lara.actor.room=87;}
    else if(level_number==3){const TombRoom *r=level->rooms+50;play.lara.actor.x=r->x+3*1024+512;play.lara.actor.z=r->z+512;play.lara.actor.room=50;TombSectorRef ref;TombHeights h;for(int j=0;j<r->nx*r->nz;j++){int x=r->x+j/r->nz*1024+512,z=r->z+j%r->nz*1024+512;if(tomb_find_sector(level,x,r->bottom,z,50,&ref) && tomb_static_heights(level,ref,x,z,0,&h) && (h.trigger_index==4238 || h.trigger_index==4241)){play.lara.actor.x=x;play.lara.actor.y=h.floor;play.lara.actor.z=z;break;}}}
    else {play.lara.actor.x=42496;play.lara.actor.y=7168;play.lara.actor.z=83456;play.lara.actor.room=11;}
}
static unsigned u16(const unsigned char *p) { return p[0]|((unsigned)p[1]<<8); }
static int s16(const unsigned char *p) { return tomb_word(u16(p)); }
static int32_t s32(const unsigned char *p) {
    return tomb_long((uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24));
}
static void colour(unsigned index,float shade) {
    const unsigned char *p=visual->palette+3*(index&255);
    glColor3f(p[0]/63.f*shade,p[1]/63.f*shade,p[2]/63.f*shade);
}
#include "preview_lighting.h"
#include "preview_interpolation.h"
#include "../tests/lighting_render.h"
static void mesh(const TombMeshView *m) {
    int interpolated=0;
    if(render_track<render_count){
        int slot=render_node++,identity=(int)(m-visual->meshes);float matrix[16];
        if(render_recording){glGetFloatv(GL_MODELVIEW_MATRIX,matrix);tomb_render_record(render_tracks+render_track,render_tick,slot,render_parent,identity,matrix);return;}
        if(tomb_render_sample(render_tracks+render_track,render_tick,slot,identity,camera_alpha,matrix)){
            glPushMatrix();glLoadMatrixd(lighting_view);glMultMatrixf(matrix);interpolated=1;
        }
    }
    GLdouble matrix[16];glGetDoublev(GL_MODELVIEW_MATRIX,matrix);
    int32_t rotation[9],local[3];
    for(int i=0;i<3;i++)for(int j=0;j<3;j++)rotation[i*3+j]=(int32_t)lround(matrix[j*4+i]*16384);
    tomb_light_vector(&model_light,rotation,local);
    light_UseProgram(shade_program);light_ActiveTexture(0x84c1);glBindTexture(GL_TEXTURE_2D,tiles[visual->tile_count*2]);light_ActiveTexture(0x84c0);
    for(int group=0;group<4;group++) {
        int n=(group%2)?3:4;
        for(size_t f=0;f<m->face_count[group];f++) {
            const unsigned char *face=m->faces[group]+f*(n+1)*2;
            unsigned material=u16(face+2*n);
            const unsigned char *texture=NULL;
            if(group<2) {
                texture=visual->textures+20*(material&32767);
                glEnable(GL_TEXTURE_2D);
                glBindTexture(GL_TEXTURE_2D,tiles[visual->tile_count+(u16(texture+2)&32767)]);
                if(u16(texture)==1) glEnable(GL_ALPHA_TEST); else glDisable(GL_ALPHA_TEST);
            } else { glDisable(GL_TEXTURE_2D); glDisable(GL_ALPHA_TEST); }
            light_Uniform1i(shade_material,texture?-1:(int)(material&255));
            glBegin(n==4?GL_QUADS:GL_TRIANGLES);
            for(int j=0;j<n;j++) {
                unsigned index=u16(face+2*j);
                const unsigned char *p=m->vertices+index*m->vertex_stride;
                int shade=tomb_light_vertex(m,index,&model_light,local);
                if(m->vertex_stride==8){
                    int depth=(int)floor(-(matrix[2]*s16(p)+matrix[6]*s16(p+2)+matrix[10]*s16(p+4)+matrix[14]));
                    shade=s16(p+6)+(depth>12288?depth-12288:0);
                }
                glColor3f((float)(shade<0?0:shade>8191?8191:shade)/8192.f,0,0);
                if(texture)glTexCoord2f(u16(texture+4+j*4)/65536.f,u16(texture+6+j*4)/65536.f);
                glVertex3f((float)s16(p),(float)s16(p+2),(float)s16(p+4));
            }
            glEnd();
        }
    }
    light_UseProgram(0);if(interpolated)glPopMatrix();
}
static void rotate_pose(const TombPose *a,const TombPose *b,int joint,float t) {
    GLfloat rotation[16];
    tomb_preview_rotation(a->rotation[joint],b->rotation[joint],t,rotation);
    glMultMatrixf(rotation);
}
static int pistol_pose(int frame,TombPose *p) {
    int an=play.weapon_type==4?(frame<13?164:frame<47?165:frame<80?166:frame<114?167:168):(frame<5?160:frame<13?161:frame<24?162:163);
    return tomb_visual_key(visual,(size_t)an,(size_t)(frame-level->animations[an].first_frame),p);
}
static void gun_flash(void) {
    TombModel flash;if(!tomb_visual_model(visual,166,&flash) || !flash.mesh_count)return;
    glPushMatrix();glTranslatef(0,155,55);glRotatef(-16380*(360.f/65536.f),1,0,0);
    /* Presentation RNG is separate from the original gameplay RNG. */
    int saved_node=render_node,saved_parent=render_parent;render_parent=saved_node-1;render_node=saved_node>11?63:62;
    TombLighting saved=model_light;tomb_light_static(0x1400,lighting_depth(),&model_light);
    glRotatef((float)fmod(elapsed*13871,360),0,0,1);mesh(visual->meshes+flash.mesh_start);model_light=saved;glPopMatrix();render_node=saved_node;render_parent=saved_parent;
}
static int lara(void) {
    TombModel model; TombPose a,b; uint16_t selected[15];
    if(!tomb_visual_model(visual,0,&model) || !tomb_visual_lara_meshes(visual,!caves,selected)) return 0;
    const TombActor *actor=pose_mode?&start.actor:&play.lara.actor;
    if(!pose_mode)render_select(0,actor);
    int selected_animation=pose_mode?animation:actor->animation;
    const TombAnim *anim=level->animations+selected_animation;
    int rate=visual->animations[32*selected_animation+4];
    double frame=pose_mode?fmod(elapsed*30,anim->last_frame-anim->first_frame+1):actor->frame-anim->first_frame;
    int key=(int)frame/rate;
    float fraction=(float)(frame-key*rate)/rate;
    if(!tomb_visual_key(visual,(size_t)selected_animation,(size_t)key,&a)) return 0;
    if(!tomb_visual_key(visual,(size_t)selected_animation,(size_t)key+1,&b)) b=a;
    if(!pose_mode && play.door_hit_ticks && play.door_hit_direction>=0 && play.door_hit_direction<4) {
        static const unsigned hits[4]={125,127,126,128};
        if(!tomb_visual_key(visual,hits[play.door_hit_direction],(size_t)play.door_hit_ticks,&a))return 0;
        b=a;fraction=0;
    }
    if(a.count!=15 || b.count!=15) return 0;
    TombPose left,right;int armed=!pose_mode && caves && play.pistols.status>=2 && play.pistols.status<=4;
    if(armed && (!pistol_pose(play.pistols.left.frame,&left) || !pistol_pose(play.pistols.right.frame,&right)))return 0;
    if(caves && !pose_mode) {
        TombModel guns,face;if(!tomb_visual_model(visual,1,&guns))guns=model;
        int pistol_drawn=play.weapon_type==4?0:play.pistols.drawn;
        selected[1]=(uint16_t)((pistol_drawn&1?model.mesh_start:guns.mesh_start)+1);
        selected[4]=(uint16_t)((pistol_drawn&2?model.mesh_start:guns.mesh_start)+4);
        if(pistol_drawn&1)selected[13]=(uint16_t)(guns.mesh_start+13);
        if(pistol_drawn&2)selected[10]=(uint16_t)(guns.mesh_start+10);
        TombModel shotgun;
        if(play.inventory.counts[1] && tomb_visual_model(visual,2,&shotgun)) {
            if(play.weapon_type==4 && play.pistols.drawn){selected[10]=(uint16_t)(shotgun.mesh_start+10);selected[13]=(uint16_t)(shotgun.mesh_start+13);}
            else selected[7]=(uint16_t)(shotgun.mesh_start+7);
        }
        if(play.pistols.status==4 && (play.last_input&64) && tomb_visual_model(visual,4,&face))selected[14]=(uint16_t)(face.mesh_start+14);
    }
    if(!pose_mode && ((actor->current==46 && actor->animation!=139) || (objects.peru && objects.peru->scion_item>=0))){
        TombModel extra;if(!tomb_visual_model(visual,5,&extra) || extra.mesh_count!=15)return 0;
        for(int i=0;i<15;i++)selected[i]=(uint16_t)(extra.mesh_start+i);
    }
    /* Explicit CPU copy of GL matrices avoids depending on driver stack depth. */
    GLfloat stack[15][16]; int depth=0,parents[15],parent=0;
    glPushMatrix();
    glTranslatef((float)actor->x,(float)actor->y,(float)actor->z);
    glRotatef(actor->yaw*(360.f/65536.f),0,1,0);
    if(!pose_mode) {
        glRotatef(play.lara.pitch*(360.f/65536.f),1,0,0);
        glRotatef(play.movement.lean*(360.f/65536.f),0,0,1);
    }
    int intensity=-1;for(size_t i=0;i<level->item_count;i++)if(level->items[i].object==0){intensity=level->items[i].intensity;break;}
    actor_lighting(actor,&a,intensity,pose_mode?0:play.lara.pitch,pose_mode?0:play.movement.lean);
    GLfloat base[16];glGetFloatv(GL_MODELVIEW_MATRIX,base);
    glTranslatef(a.root[0]+fraction*(b.root[0]-a.root[0]),a.root[1]+fraction*(b.root[1]-a.root[1]),a.root[2]+fraction*(b.root[2]-a.root[2]));
    rotate_pose(&a,&b,0,fraction); mesh(visual->meshes+selected[0]);
    for(int i=1;i<15;i++) {
        const unsigned char *bone=visual->trees+4*model.tree_word+(i-1)*16;
        int flags=s32(bone);
        if(flags&1) { if(!depth) { glPopMatrix(); return 0; } parent=parents[depth-1]; glLoadMatrixf(stack[--depth]); }
        if(flags&2) { if(depth>=15) { glPopMatrix(); return 0; } parents[depth]=parent; glGetFloatv(GL_MODELVIEW_MATRIX,stack[depth++]); }
        glTranslatef((float)s32(bone+4),(float)s32(bone+8),(float)s32(bone+12));
        if(armed && i>=8 && i<=13) {
            const TombGunArm *arm=i<11?&play.pistols.right:&play.pistols.left;
            const TombPose *pose=i<11?&right:&left;
            if(play.weapon_type!=4 && (i==8 || i==11)) {
                GLfloat matrix[16];glGetFloatv(GL_MODELVIEW_MATRIX,matrix);
                for(int col=0;col<3;col++)for(int row=0;row<3;row++)matrix[4*col+row]=base[4*col+row];
                glLoadMatrixf(matrix);glRotatef(arm->yaw*(360.f/65536.f),0,1,0);glRotatef(arm->pitch*(360.f/65536.f),1,0,0);glRotatef(arm->roll*(360.f/65536.f),0,0,1);
            }
            rotate_pose(pose,pose,i,0);
        } else rotate_pose(&a,&b,i,fraction);
        if(!pose_mode && (i==7 || i==14)) {
            glRotatef((i==7?play.lara.torso_yaw:play.lara.head_yaw)*(360.f/65536.f),0,1,0);
            glRotatef((i==7?play.lara.torso_pitch:play.lara.head_pitch)*(360.f/65536.f),1,0,0);
        }
        render_parent=parent;mesh(visual->meshes+selected[i]);parent=i;
        if(armed && play.weapon_type!=4 && ((i==10 && play.pistols.right.flash) || (i==13 && play.pistols.left.flash)))gun_flash();
    }
    glPopMatrix();render_track=SIZE_MAX; return 1;
}
static int draw_object(const TombObject *o) {
    TombModel m;TombPose a,b;const TombActor *actor=&o->actor;
    render_select(render_object_key(o),actor);
    const TombCreature *creature=NULL;
    if((tomb_enemy_object(o->object) || o->object==24) && objects.enemies)for(size_t i=0;i<objects.count;i++)if(o==objects.items+i){creature=objects.enemies->items+i;break;}
    if(!tomb_visual_model(visual,o->object,&m) || !m.mesh_count || m.mesh_count>64 || actor->animation<0 || (size_t)actor->animation>=level->animation_count)return 0;
    const TombAnim *anim=level->animations+actor->animation;
    int rate=visual->animations[32*actor->animation+4],frame=actor->frame-anim->first_frame;
    if(!rate || frame<0)return 0;
    size_t key=(size_t)(frame/rate);float t=(float)(frame%rate)/rate;
    if(!tomb_visual_key(visual,actor->animation,key,&a) || a.count!=m.mesh_count)return 0;
    if(!tomb_visual_key(visual,actor->animation,key+1,&b))b=a;
    glPushMatrix();glTranslatef((float)actor->x,(float)actor->y,(float)actor->z);
    glRotatef(actor->yaw*(360.f/65536.f),0,1,0);
    if(creature){glRotatef(creature->pitch*(360.f/65536.f),1,0,0);glRotatef(creature->roll*(360.f/65536.f),0,0,1);}
    int intensity=-1;for(size_t i=0;i<objects.count;i++)if(o==objects.items+i){intensity=level->items[i].intensity;break;}
    actor_lighting(actor,&a,intensity,creature?creature->pitch:0,creature?creature->roll:0);
    glTranslatef(a.root[0]+t*(b.root[0]-a.root[0]),a.root[1]+t*(b.root[1]-a.root[1]),a.root[2]+t*(b.root[2]-a.root[2]));
    rotate_pose(&a,&b,0,t);mesh(visual->meshes+m.mesh_start);
    GLfloat stack[64][16];int depth=0,parents[64],parent=0;
    for(unsigned i=1;i<m.mesh_count;i++) {
        const unsigned char *bone=visual->trees+4*m.tree_word+(i-1)*16;int flags=s32(bone);
        if(flags&1){if(!depth){glPopMatrix();return 0;}parent=parents[depth-1];glLoadMatrixf(stack[--depth]);}
        if(flags&2){if(depth>=64){glPopMatrix();return 0;}parents[depth]=parent;glGetFloatv(GL_MODELVIEW_MATRIX,stack[depth++]);}
        glTranslatef((float)s32(bone+4),(float)s32(bone+8),(float)s32(bone+12));rotate_pose(&a,&b,(int)i,t);
        if(creature && ((o->object==7 && i==3) || (o->object==8 && i==14) || (o->object==18 && (i==11 || i==12)) || (o->object==19 && i==22) || (o->object==24 && i==3) || (o->object==27 && i==7)))glRotatef(creature->head*(360.f/65536.f),0,1,0);
        render_parent=parent;if(o->object!=24 || i<11 || i>14 || render_recording)mesh(visual->meshes+m.mesh_start+i);else ++render_node;parent=(int)i;
    }
    glPopMatrix();render_track=SIZE_MAX;return 1;
}
static void draw_hazard_effect(const TombHazardEffect *e,size_t track) {
    if(e->id==166){TombModel m;if(!tomb_visual_model(visual,166,&m))return;
        glPushMatrix();glTranslatef((float)e->x,(float)e->y,(float)e->z);glRotatef(e->yaw*(360.f/65536.f),0,1,0);glRotatef(e->speed*(360.f/65536.f),0,0,1);
        TombLighting old=model_light;tomb_light_static(4096,lighting_depth(),&model_light);mesh(visual->meshes+m.mesh_start);model_light=old;glPopMatrix();return;
    }
    int sprite=tomb_hazard_sprite(visual,e->id,e->frame,NULL);if(sprite<0)return;
    const unsigned char *p=visual->sprite_textures+16*sprite;
    GLdouble view[16];glGetDoublev(GL_MODELVIEW_MATRIX,view);double v[3];
    float position[16]={0};position[12]=(float)e->x;position[13]=(float)e->y;position[14]=(float)e->z;
    if(track<render_count)tomb_render_sample(render_tracks+track,render_tick,0,e->id,camera_alpha,position);
    for(int i=0;i<3;i++)v[i]=view[i]*position[12]+view[4+i]*position[13]+view[8+i]*position[14]+view[12+i];
    if(v[2]>=-10 || v[2]<=-20480)return;
    float left=(float)s16(p+8),top=-(float)s16(p+10),right=(float)s16(p+12),bottom=-(float)s16(p+14);
    float u=p[2]/256.f,t=p[3]/256.f,du=(u16(p+4)+1)/65536.f,dv=(u16(p+6)+1)/65536.f;
    glPushMatrix();glLoadIdentity();glTranslatef((float)v[0],(float)v[1],(float)v[2]);glEnable(GL_TEXTURE_2D);glEnable(GL_ALPHA_TEST);glBindTexture(GL_TEXTURE_2D,tiles[u16(p)]);glColor3f(1,1,1);
    glBegin(GL_QUADS);glTexCoord2f(u,t);glVertex3f(left,top,0);glTexCoord2f(u+du,t);glVertex3f(right,top,0);glTexCoord2f(u+du,t+dv);glVertex3f(right,bottom,0);glTexCoord2f(u,t+dv);glVertex3f(left,bottom,0);glEnd();glPopMatrix();
}

static int make_tiles(void) {
    if(!lighting_program()){MessageBoxA(NULL,"Lighting requires OpenGL 2.0 support. Check the graphics driver. See stderr for shader diagnostics.","Renderer initialization",MB_ICONERROR);return 0;}
    tiles=calloc(visual->tile_count*2+1,sizeof *tiles); unsigned char *rgba=malloc(65536*4);
    if(!tiles || !rgba){free(tiles);free(rgba);tiles=NULL;return 0;}
    glGenTextures((GLsizei)(visual->tile_count*2+1),tiles);
    lighting_textures();
    for(size_t i=0;i<visual->tile_count;i++) {
        for(size_t j=0;j<65536;j++) {
            unsigned index=visual->tiles[i*65536+j];
            for(int c=0;c<3;c++) rgba[j*4+c]=(unsigned char)(visual->palette[index*3+c]*255/63);
            rgba[j*4+3]=index?255:0;
        }
        glBindTexture(GL_TEXTURE_2D,tiles[i]); glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,256,256,0,GL_RGBA,GL_UNSIGNED_BYTE,rgba);
    }
    font_tiles=calloc(visual->tile_count,sizeof *font_tiles);if(!font_tiles){free(rgba);return 0;}
    /* DOS screen sprites use shade 0x1000: light-map row 16. Index zero
       remains transparent even when the palette's black entry differs. */
    const unsigned char *light=level->file_data+level->item_parsed_bytes+4096;
    for(unsigned tile=0;tile<visual->tile_count;tile++) {
        glGenTextures(1,font_tiles+tile);
        for(size_t j=0;j<65536;j++) {
            unsigned index=visual->tiles[tile*65536+j],mapped=light[index];
            for(int c=0;c<3;c++)rgba[j*4+c]=(unsigned char)(visual->palette[mapped*3+c]*255/63);
            rgba[j*4+3]=index?255:0;
        }
        glBindTexture(GL_TEXTURE_2D,font_tiles[tile]);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,256,256,0,GL_RGBA,GL_UNSIGNED_BYTE,rgba);
    }
    free(rgba);
    return 1;
}
static int load_game_level(int next_number,int carry,const char *saved) {
    if(next_number<0 || next_number>=LEVEL_CHOICE_COUNT)return 0;
    char path[MAX_PATH],error[256]={0};GetModuleFileNameA(NULL,path,MAX_PATH);
    char *slash=strrchr(path,'\\');if(!slash)return 0;
    snprintf(slash,(size_t)(path+MAX_PATH-slash),"/../work/reference-assets/DATA/%s",level_choices[next_number].file);
    TombLevel *next=tomb_level_load(path,error,sizeof error);TombVisual *view=NULL;
    TombObjects world={0};TombPlaytest player;TombLaraStart spawn;TombScreenRect *rects=NULL;
    if(!next || !(view=tomb_visual_load(next,error,sizeof error)) || !tomb_lara_start(next,&spawn) ||
       !(rects=calloc(next->room_count,sizeof *rects)) || !tomb_objects_init(&world,next,view) ||
       !tomb_playtest_init(&player,next,sine_table,view)) {
        tomb_objects_free(&world);free(rects);tomb_visual_free(view);tomb_level_free(next);
        MessageBoxA(NULL,"Could not load the next level. Check that its PHD file is installed.","Next level",MB_ICONERROR);return 0;
    }
    TombFollowCamera saved_camera={0};TombInventory saved_baseline={0};
    player.objects=&world;player.movement_only=next_number!=0;
    if(saved && !tomb_save_read(saved,next_number,&player,&world,&saved_camera,&saved_baseline)){
        tomb_objects_free(&world);free(rects);tomb_visual_free(view);tomb_level_free(next);strcpy(menu_error,"Could not load this save");return 0;
    }
    TombInventory carried=carry?play.inventory:player.inventory;carried.pickups=carried.ticks=0;carried.pickup_ticks=0;carried.last_pickup=-1;memset(carried.quest,0,sizeof carried.quest);carried.chosen=-1;
    audio_stop();tomb_sound_output_close(ring_sound_output);ring_sound_output=NULL;tomb_sound_output_close(sound_output);sound_output=NULL;tomb_sound_bank_free(&sound_bank);
    glDeleteTextures((GLsizei)visual->tile_count,font_tiles);free(font_tiles);
    glDeleteTextures((GLsizei)(visual->tile_count*2+1),tiles);free(tiles);free(room_rects);
    tomb_objects_free(&objects);tomb_visual_free(visual);tomb_level_free(level);
    level=next;visual=view;objects=world;play=player;start=spawn;room_rects=rects;
    /* init installs callbacks pointing at the player itself, so rebuild after moving. */
    tomb_playtest_init(&play,level,sine_table,visual);play.objects=&objects;play.movement_only=1;
    if(saved){
        /* Re-read only after all level resources are ready. Callback pointers
           remain those installed at the final address by init above. */
        if(!tomb_save_read(saved,next_number,&play,&objects,&saved_camera,&saved_baseline)){running=0;return 0;}
        camera=saved_camera;level_inventory=saved_baseline;
    }else{play.inventory=carried;level_inventory=carried;}
    level_number=next_number;caves=next_number!=0;play.movement_only=caves;play.objects=caves?&objects:NULL;
    title_mode=death_menu=slot_menu=options_ring=new_game_menu=0;
    inventory_open=inventory_stats=inventory_selected=draw_requested=paused=0;
    render_reset();
    if(!saved){camera.ready=0;render_reset();objects.progress->music.current_track=tomb_music_level_track(next_number);}
    camera_bounce=0;pose_mode=0;orbit=0;distance=1536;camera_hold=elapsed=accumulator=0;
    if(!make_tiles()){running=0;return 0;}
    sound_failed=0;if(tomb_sound_bank_load(&sound_bank,level)){tomb_sound_init(&sound_mixer,&sound_bank);sound_output=tomb_sound_output_open(&sound_mixer);
            tomb_sound_init(&ring_sound_mixer,&sound_bank);ring_sound_output=tomb_sound_output_open(&ring_sound_mixer);}
    if(!sound_output || !ring_sound_output)sound_failed=1;if(!saved)update_camera(1.0/30);return 1;
}
static int load_next_level(void){if(level_number<1 || level_number>3){play.status="End of available progression test";return 0;}return load_game_level(level_number+1,1,NULL);
}
/* Menu effects have their own output so pausing world audio cannot mute them.
   DOS passes a null position and environment 2 for these SoundEffect calls. */
static void inventory_sound(void) {
    if(!inventory_ring.sound)return;
    const double origin[3]={0,0,0};
    TombSoundEvent event={5,inventory_ring.sound,2,0,0,0};
    tomb_sound_output_event(ring_sound_output,&event,0,origin);
}
static void inventory_begin(void) {
    backdrop_dirty=1;backdrop_shade=32;refresh_slots();
    options_ring=slot_menu=menu_action=binding_wait=new_game_menu=0;menu_error[0]=0;
    inventory_keys=inventory_key_only=play.quest_request;inventory_ring_current[0]=inventory_ring_current[1]=0;play.quest_request=0;play.inventory.chosen=-1;
    if(death_menu){options_ring=1;inventory_keys=inventory_key_only=0;tomb_ring_init_options(&inventory_ring,0);}
    else if(!(inventory_keys?tomb_ring_init_keys(&inventory_ring,&play.inventory):tomb_ring_init(&inventory_ring,&play.inventory)))return;
    inventory_sound();inventory_open=1;inventory_stats=inventory_selected=0;inventory_input=0;inventory_accumulator=accumulator=0;
}
static void font_glyph(void *user,const TombTextGlyph *g) {
    (void)user;int sprite=tomb_hazard_sprite(visual,190,g->glyph,NULL);if(sprite<0)return;
    const unsigned char *p=visual->sprite_textures+16*sprite;int tile=u16(p);
    float x0=(float)(g->x+((int64_t)s16(p+8)*g->scale_x>>16)),y0=(float)(g->y+((int64_t)s16(p+10)*g->scale_y>>16));
    float x1=(float)(g->x+((int64_t)s16(p+12)*g->scale_x>>16)),y1=(float)(g->y+((int64_t)s16(p+14)*g->scale_y>>16));
    float u=p[2]/256.f,v=p[3]/256.f,du=(u16(p+4)+1)/65536.f,dv=(u16(p+6)+1)/65536.f;
    glBindTexture(GL_TEXTURE_2D,font_tiles[tile]);glBegin(GL_QUADS);
    glTexCoord2f(u,v);glVertex2f(x0,y0);glTexCoord2f(u+du,v);glVertex2f(x1,y0);
    glTexCoord2f(u+du,v+dv);glVertex2f(x1,y1);glTexCoord2f(u,v+dv);glVertex2f(x0,y1);glEnd();
}
static void text_aligned(float x,float y,const char *text,unsigned flags) {
    double scale=fmin(width/640.0,height/480.0);if(scale<.5)scale=.5;
    TombTextStyle style={(int)x,(int)y,(int32_t)(scale*65536),(int32_t)(scale*65536),1,6,(uint16_t)flags};
    glEnable(GL_TEXTURE_2D);glEnable(GL_ALPHA_TEST);glColor3f(1,1,1);
    tomb_text_layout(text,&style,width,height,font_glyph,NULL);
    glDisable(GL_ALPHA_TEST);glDisable(GL_TEXTURE_2D);
}
#include "ui_dialog.h"
#include "preview_frontend.h"
static void inventory_tick(unsigned input) {
    if(inventory_ring.motion.status==2 && inventory_ring.motion.target==13){if(backdrop_shade>32)--backdrop_shade;}else if(backdrop_shade<48)++backdrop_shade;
    if(frontend_input(&input))return;
    if(!title_mode && !death_menu && !options_ring && !inventory_key_only && ((input&16 && !inventory_keys) || (input&32 && inventory_keys))){
        int owned=play.inventory.scion;for(int q=0;q<8;q++)owned+=play.inventory.quest[q];
        if((inventory_keys || owned) && tomb_ring_change_begin(&inventory_ring,!inventory_keys))inventory_ring_current[inventory_keys]=inventory_ring.current;
    }
    if(!title_mode && !death_menu && !inventory_key_only && !inventory_keys && ((input&32 && !options_ring) || (input&16 && options_ring))){
        if(tomb_ring_change_begin(&inventory_ring,options_ring)){inventory_ring.motion.target=options_ring?6:3;inventory_ring_current[options_ring?2:0]=inventory_ring.current;}
    }
    if((title_mode || death_menu) && inventory_ring.motion.status==1)input&=~TOMB_RING_BACK;
    tomb_ring_tick(&inventory_ring,input);inventory_sound();
    if(inventory_ring.motion.status==3 || inventory_ring.motion.status==6){
        options_ring=inventory_ring.motion.status==3;if(options_ring)tomb_ring_init_options(&inventory_ring,0);else tomb_ring_init(&inventory_ring,&play.inventory);
        tomb_ring_change_end(&inventory_ring,!options_ring,inventory_ring_current[options_ring?2:0]);
    }inventory_selected=inventory_ring.current;
    if(inventory_ring.motion.status==4 || inventory_ring.motion.status==5){
        inventory_keys=inventory_ring.motion.status==4;
        if(inventory_keys)tomb_ring_init_keys(&inventory_ring,&play.inventory);else tomb_ring_init(&inventory_ring,&play.inventory);
        tomb_ring_change_end(&inventory_ring,inventory_keys,inventory_ring_current[inventory_keys]);inventory_selected=inventory_ring.current;
    }
    tomb_ring_compass(inventory_ring.items[0].y,play.lara.actor.yaw,&compass_angle,&compass_velocity);
    inventory_stats=inventory_ring.motion.status==8 && inventory_ring.ready && inventory_ring.items[inventory_selected].object==72;
    if(inventory_ring.motion.status!=13)return;
    int id=inventory_ring.chosen;inventory_open=inventory_stats=0;accumulator=0;
    if(id==71 || id==73){frontend_execute(id);return;}
    if(title_mode || death_menu){inventory_begin();return;}
    if(id==99 || id==100){play.requested_weapon=id==100?4:1;if(play.pistols.status==0)draw_requested=1;}
    else if(tomb_inventory_use(&play.inventory,id,&play.lara.health)==1) {
        play.water.health=play.lara.health;play.movement.health=play.lara.health;
        play.sound_count=1;play.sounds[0]=(TombSoundEvent){5,116,2,play.lara.actor.x,play.lara.actor.y,play.lara.actor.z};sound_tick();play.sound_count=0;
    }
}
static void ring_item(const TombRingItem *item) {
    TombModel model;TombPose pose;if(!tomb_visual_model(visual,item->object,&model) || !tomb_visual_key(visual,model.animation,(size_t)item->frame,&pose))return;
    glTranslatef(0,(float)item->yoff,(float)item->zoff);glRotatef(item->y*360.f/65536,0,1,0);glRotatef(item->x*360.f/65536,1,0,0);
    glTranslatef(pose.root[0],pose.root[1],pose.root[2]);rotate_pose(&pose,&pose,0,0);
    if(item->meshes&1)mesh(visual->meshes+model.mesh_start);
    GLfloat stack[64][16];int depth=0;
    for(unsigned j=1;j<model.mesh_count;j++) {
        const unsigned char *bone=visual->trees+4*model.tree_word+(j-1)*16;int flags=s32(bone);
        if(flags&1){if(!depth)return;glLoadMatrixf(stack[--depth]);}
        if(flags&2){if(depth>=64)return;glGetFloatv(GL_MODELVIEW_MATRIX,stack[depth++]);}
        glTranslatef((float)s32(bone+4),(float)s32(bone+8),(float)s32(bone+12));rotate_pose(&pose,&pose,(int)j,0);
        if(tomb_ring_compass_bone(item->object,model.mesh_count,j))glRotatef(compass_angle*360.f/65536,0,1,0);
        if(item->meshes&(1u<<j))mesh(visual->meshes+model.mesh_start+j);
    }
}
static void draw_inventory_ring(void) {
    TombRing *r=&inventory_ring;
    glMatrixMode(GL_PROJECTION);glPushMatrix();glLoadIdentity();double focal=tomb_preview_aspect_focal(height);
    glFrustum(-10.0*width/(2*focal),10.0*width/(2*focal),-10.0*height/(2*focal),10.0*height/(2*focal),10,20480);
    glMatrixMode(GL_MODELVIEW);glPushMatrix();glLoadIdentity();glRotatef(r->pitch*360.f/65536,1,0,0);
    double eye[3]={0,r->camera_y,r->radius+598},target[3]={0,-96,r->radius};GLdouble view[16];
    tomb_preview_view(eye,target,view);glMultMatrixd(view);glGetDoublev(GL_MODELVIEW_MATRIX,lighting_view);
    const int32_t ring_light[3]={-1536,256,1024};model_light.divider=0x6000;tomb_light_direction(ring_light,sine_table,model_light.direction);light_in_view();
    glRotatef(r->angle*360.f/65536,0,1,0);
    glEnable(GL_DEPTH_TEST);glClear(GL_DEPTH_BUFFER_BIT);
    for(int j=0;j<r->count;j++) {
        model_light.adder=j==r->current?0x1000:0x1400;
        glPushMatrix();glRotatef(j*r->step*360.f/65536,0,1,0);glTranslatef(r->radius,0,0);
        glRotatef(90,0,1,0);glRotatef(r->items[j].pivot_now*360.f/65536,1,0,0);ring_item(r->items+j);glPopMatrix();
    }
    glPopMatrix();glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(GL_MODELVIEW);glDisable(GL_DEPTH_TEST);glDisable(GL_TEXTURE_2D);glDisable(GL_ALPHA_TEST);
}
static double ui_scale(void){return fmax(.5,fmin(width/640.0,height/480.0));}
static void ui_text(int x,int y,const char *text,unsigned flags){double scale=ui_scale();text_aligned((float)(x*scale),(float)(y*scale),text,flags);}
static void bar_line(void *user,int x1,int y1,int x2,int y2,int palette) {
    (void)user;double scale=ui_scale();colour((unsigned)palette,1);
    glBegin(GL_QUADS);glVertex2d(x1*scale,y1*scale);glVertex2d((x2+1)*scale,y1*scale);
    glVertex2d((x2+1)*scale,(y2+1)*scale);glVertex2d(x1*scale,(y2+1)*scale);glEnd();
}
static void pickup_icon(int object,int slot) {
    int sprite=tomb_hazard_sprite(visual,object,0,NULL);if(sprite<0)return;
    const unsigned char *p=visual->sprite_textures+16*sprite;double scale=ui_scale();
    int logical_width=(int)(width/scale),logical_height=(int)(height/scale),spacing=logical_width/10;
    double x=(logical_width-spacing-slot*(spacing*4/3))*scale,y=(logical_height-spacing)*scale;
    double factor=scale*0x3000/65536.0;
    double x0=x+s16(p+8)*factor,y0=y+s16(p+10)*factor,x1=x+s16(p+12)*factor,y1=y+s16(p+14)*factor;
    float u=p[2]/256.f,v=p[3]/256.f,du=(u16(p+4)+1)/65536.f,dv=(u16(p+6)+1)/65536.f;
    glEnable(GL_TEXTURE_2D);glEnable(GL_ALPHA_TEST);glColor3f(1,1,1);glBindTexture(GL_TEXTURE_2D,font_tiles[u16(p)]);
    glBegin(GL_QUADS);glTexCoord2f(u,v);glVertex2d(x0,y0);glTexCoord2f(u+du,v);glVertex2d(x1,y0);
    glTexCoord2f(u+du,v+dv);glVertex2d(x1,y1);glTexCoord2f(u,v+dv);glVertex2d(x0,y1);glEnd();
    glDisable(GL_TEXTURE_2D);glDisable(GL_ALPHA_TEST);
}
static void overlay(void) {
    int complete=caves && objects.progress->complete;
    TombVisual *game_visual=visual;GLuint *game_tiles=tiles,*game_font=font_tiles;
    if(title_mode && title_visual){visual=title_visual;tiles=title_tiles;font_tiles=title_font_tiles;complete=0;}
    glDisable(GL_SCISSOR_TEST);glDisable(GL_TEXTURE_2D);glDisable(GL_ALPHA_TEST);glDisable(GL_DEPTH_TEST);
    glMatrixMode(GL_PROJECTION);glPushMatrix();glLoadIdentity();glOrtho(0,width,height,0,-4096,4096);
    glMatrixMode(GL_MODELVIEW);glPushMatrix();glLoadIdentity();
    int medipack=0;
    if(inventory_open || complete) {
        if(!title_mode)frontend_inventory_backdrop();
        if(title_mode)frontend_backdrop();
        if(complete) {
            char lines[4][80];tomb_statistics(play.inventory.ticks,play.pistols.kills,play.inventory.pickups,objects.progress->secrets,3,lines);
            ui_text(0,-50,level_choices[level_number].name,TOMB_TEXT_CENTRE|TOMB_TEXT_MIDDLE);
            for(int i=0;i<4;i++)ui_text(0,-20+30*i,lines[i],TOMB_TEXT_CENTRE|TOMB_TEXT_MIDDLE);
        } else {
            draw_inventory_ring();
            if(inventory_ring.motion.status!=0 && inventory_ring.motion.status!=13)ui_text(0,26,title_mode?"":options_ring?"OPTIONS":inventory_keys?"ITEMS":"INVENTORY",TOMB_TEXT_CENTRE);
            if(!inventory_ring.rotating && inventory_ring.motion.status!=0 && inventory_ring.motion.status!=13) {
                int id=inventory_ring.items[inventory_selected].object;char amount[64];
                if(id!=71)ui_text(0,-16,frontend_name(id),TOMB_TEXT_CENTRE|TOMB_TEXT_BOTTOM);
                if(tomb_inventory_label(&play.inventory,id,amount))ui_text(64,-56,amount,TOMB_TEXT_CENTRE|TOMB_TEXT_BOTTOM);
                medipack=id==108 || id==109;
            }
        }
    }
    if(inventory_open)frontend_overlay();
    if(!title_mode && !complete && (!inventory_open || medipack)) {
        glDisable(GL_TEXTURE_2D);glDisable(GL_ALPHA_TEST);
        tomb_hud_bar(tomb_hud_health(&play.hud,play.lara.health,play.pistols.status,medipack),0,(int)(width/ui_scale()),bar_line,NULL);
        if(!inventory_open) {
            tomb_hud_bar(tomb_hud_air(play.lara.air,play.lara.water_status),1,(int)(width/ui_scale()),bar_line,NULL);
            /* Shotgun ammunition is stored per pellet; the HUD shows shells. */
            if(play.weapon_type==4 && play.pistols.status==4){char amount[64];tomb_ui_ammo(play.inventory.ammo[1],1,amount);ui_text(-24,48,amount,TOMB_TEXT_RIGHT);}
            for(int i=0;i<3;i++)if(play.hud.pickup_time[i]>0)pickup_icon(play.hud.pickup_id[i],i);
        }
    }
    glPopMatrix();glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(GL_MODELVIEW);glEnable(GL_DEPTH_TEST);
    visual=game_visual;tiles=game_tiles;font_tiles=game_font;
}
static int draw(void) {
    render_track=SIZE_MAX;
    glViewport(0,0,width,height); glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
    glMatrixMode(GL_PROJECTION); glLoadIdentity();
    double focal=tomb_preview_aspect_focal(height),shot_roll=0;
    if(objects.peru && objects.peru->scion_item>=0){
        TombDosCamera shot;int fov,roll;
        if(tomb_scion_camera(&objects,sine_table,&shot,&fov,&roll) && fov>0 && fov<32768){
            int half=fov/2,si=tomb_hazard_sine(sine_table,half),co=tomb_hazard_sine(sine_table,half+16384);
            if(si)focal=height*((320*co/si)/480.0);shot_roll=roll*(6.283185307179586/65536.0);
        }
    }
    double half_x=5.0*width/focal,half_y=5.0*height/focal;
    glFrustum(-half_x,half_x,-half_y,half_y,10,20480);
    glMatrixMode(GL_MODELVIEW); glLoadIdentity();
    const TombActor *actor=pose_mode?&start.actor:&play.lara.actor;
    double target[3]={actor->x,actor->y-450,actor->z};
    double eye[3]={target[0]+cos(orbit)*distance,target[1]-550,target[2]+sin(orbit)*distance};
    if(!pose_mode && !manual_camera && camera.ready) { for(int i=0;i<3;i++){double t=camera_alpha;target[i]=camera.previous_target[i]+t*(camera.target[i]-camera.previous_target[i]);eye[i]=camera.previous_eye[i]+t*(camera.eye[i]-camera.previous_eye[i]);} }
    GLdouble view[16];
    if(!tomb_preview_view(eye,target,view)){fprintf(stderr,"invalid view eye=%f,%f,%f target=%f,%f,%f\n",eye[0],eye[1],eye[2],target[0],target[1],target[2]);return 0;}
    if(shot_roll){double cs=cos(shot_roll),sn=sin(shot_roll);for(int j=0;j<4;j++){double x=view[j*4],y=view[j*4+1];view[j*4]=cs*x-sn*y;view[j*4+1]=sn*x+cs*y;}}
    glMultMatrixd(view);memcpy(lighting_view,view,sizeof view);
    int eye_room=(!manual_camera && camera.ready)?camera.room:actor->room;
    TombSectorRef eye_ref;
    if(tomb_find_sector(level,(int32_t)eye[0],(int32_t)eye[1],(int32_t)eye[2],eye_room,&eye_ref))eye_room=eye_ref.room;
    if(!tomb_room_visibility_focal(visual,eye_room,eye,view,width,height,focal,room_rects))return 0;
    for(size_t i=0;i<level->room_count;i++) {
        TombScreenRect clip=room_rects[i];
        if(clip.left>=clip.right || clip.bottom>=clip.top)continue;
        glEnable(GL_SCISSOR_TEST);
        glScissor(clip.left,clip.bottom,clip.right-clip.left,clip.top-clip.bottom);
        const TombRoom *room=level->rooms+i;
        glPushMatrix(); glTranslatef((float)room->x,0,(float)room->z);
        mesh(visual->rooms+i); glPopMatrix();
        glDisable(GL_SCISSOR_TEST); /* Static objects use the full viewport in DOS. */
        for(size_t j=0;j<room->static_count;j++) {
            const TombStaticPlacement *p=room->statics+j;
            for(size_t k=0;k<level->static_def_count;k++) {
                const TombStaticDef *def=level->static_defs+k;
                if(def->id!=p->id) continue;
                if(!(def->flags&2))break;
                glPushMatrix(); glTranslatef((float)p->x,(float)p->y,(float)p->z);
                glRotatef(p->rotation*(360.f/65536.f),0,1,0);
                GLdouble object_view[16];glGetDoublev(GL_MODELVIEW_MATRIX,object_view);
                tomb_light_static(tomb_word(p->intensity),lighting_depth(),&model_light);
                if(tomb_static_visible(def,object_view,width,height,clip))mesh(visual->meshes+def->mesh);
                glPopMatrix(); break;
            }
        }
    }
    glDisable(GL_SCISSOR_TEST);
    if(caves)for(size_t i=0;i<objects.count;i++) {
        const TombObject *o=objects.items+i;
        if(!tomb_object_supported(o->object) || (o->actor.flags&6)==6)continue;
        if(render_visible(1+i,o->actor.room)) {
            if(tomb_pickup_object(o->object)){TombHazardEffect e={0};e.id=o->object;e.x=o->actor.x;e.y=o->actor.y;e.z=o->actor.z;draw_hazard_effect(&e,SIZE_MAX);}
            else if(!draw_object(o)){fprintf(stderr,"object draw failed: %d animation %d frame %d\n",o->object,o->actor.animation,o->actor.frame);return 0;}
        }
    }
    if(caves && objects.hazards)for(int i=0;i<TOMB_DART_CAPACITY;i++) {
        const TombObject *o=&objects.hazards->darts[i].item;if(!o->active)continue;
        if(render_visible(1+objects.count+(size_t)i,o->actor.room)) {
            if(tomb_pickup_object(o->object)){TombHazardEffect e={0};e.id=o->object;e.x=o->actor.x;e.y=o->actor.y;e.z=o->actor.z;draw_hazard_effect(&e,SIZE_MAX);}
            else if(!draw_object(o)){fprintf(stderr,"object draw failed: %d animation %d frame %d\n",o->object,o->actor.animation,o->actor.frame);return 0;}
        }
    }
    if(caves && objects.hazards)for(int i=0;i<256;i++){const TombHazardEffect *e=objects.hazards->effects+i;if(e->active){if(render_visible(1+objects.count+TOMB_DART_CAPACITY+(size_t)i,e->room))draw_hazard_effect(e,1+objects.count+TOMB_DART_CAPACITY+(size_t)i);}}
    int lara_ok=lara(); GLenum gl_error=glGetError();
    if(!lara_ok || gl_error)fprintf(stderr,"draw error: Lara=%d GL=%u state=%d animation=%d frame=%d\n",lara_ok,(unsigned)gl_error,play.lara.actor.current,play.lara.actor.animation,play.lara.actor.frame);
    return lara_ok && gl_error==GL_NO_ERROR;
}

#include "../tests/interpolation_render.h"
/* Detail Levels retain Low/Medium/High; modern hardware uses resolution
   rather than DOS's software rasterizer perspective-correction thresholds. */
static int draw_frame(void){
 if(settings_detail==2 || width<=320)return draw();
 static GLuint texture;int full_w=width,full_h=height;int target=settings_detail?640:320;
 if(width<=target)return draw();width=target;height=(int)((int64_t)full_h*target/full_w);if(height<1)height=1;
 int ok=draw(),w=width,h=height,pw=1,ph=1;while(pw<w)pw*=2;while(ph<h)ph*=2;
 if(!texture)glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
 glTexImage2D(GL_TEXTURE_2D,0,GL_RGB,pw,ph,0,GL_RGB,GL_UNSIGNED_BYTE,NULL);glCopyTexSubImage2D(GL_TEXTURE_2D,0,0,0,0,0,w,h);
 width=full_w;height=full_h;glViewport(0,0,width,height);glDisable(GL_SCISSOR_TEST);glDisable(GL_DEPTH_TEST);glDisable(GL_ALPHA_TEST);glEnable(GL_TEXTURE_2D);glColor3f(1,1,1);
 glMatrixMode(GL_PROJECTION);glLoadIdentity();glOrtho(0,width,0,height,-1,1);glMatrixMode(GL_MODELVIEW);glLoadIdentity();
 glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2i(0,0);glTexCoord2f((float)w/pw,0);glVertex2i(width,0);glTexCoord2f((float)w/pw,(float)h/ph);glVertex2i(width,height);glTexCoord2f(0,(float)h/ph);glVertex2i(0,height);glEnd();glDisable(GL_TEXTURE_2D);glEnable(GL_DEPTH_TEST);return ok;
}
static int capture(const char *path) {
    size_t bytes=(size_t)width*height*3;
    unsigned char *pixels=malloc(bytes); if(!pixels) return 0;
    glPixelStorei(GL_PACK_ALIGNMENT,1); glReadBuffer(GL_BACK);
    glReadPixels(0,0,width,height,GL_RGB,GL_UNSIGNED_BYTE,pixels);
    FILE *f=fopen(path,"wb"); if(!f) { free(pixels); return 0; }
    /* PPM keeps deterministic captures independent of image libraries. */
    fprintf(f,"P6\n%d %d\n255\n",width,height);
    int ok=1;
    for(int y=height-1;y>=0;y--) if(fwrite(pixels+(size_t)y*width*3,1,(size_t)width*3,f)!=(size_t)width*3) ok=0;
    if(fclose(f)) ok=0;
    free(pixels); return ok;
}
#include "../tests/peru_render.h"
static unsigned menu_entries=0;
static unsigned char held_keys[256];
/* Use keypad scan codes so Num Lock does not change the movement bindings.
   Extended navigation keys remain distinct from their keypad equivalents. */
static unsigned input_key(WPARAM key,LPARAM flags) {
    if(!(flags&(1L<<24))) {
        switch((flags>>16)&255) {
        case 0x52:return VK_NUMPAD0;case 0x48:return VK_NUMPAD8;case 0x50:return VK_NUMPAD2;
        case 0x4b:return VK_NUMPAD4;case 0x4d:return VK_NUMPAD6;
        case 0x47:return VK_NUMPAD7;case 0x49:return VK_NUMPAD9;
        }
    }
    return (unsigned)key;
}
static unsigned game_input(void) {
 static const unsigned flags[13]={1,2,4,8,1024,2048,128,16,64,0,4096,512,0};unsigned input=held_keys[VK_RETURN]?64u:0;
 for(int i=0;i<13;i++)if(held_keys[bindings[i]])input|=flags[i];return input;
}
static int fullscreen,fullscreen_enter_held;
static WINDOWPLACEMENT windowed_placement;
static LONG_PTR windowed_style;
static void toggle_fullscreen(HWND w) {
    if(!fullscreen) {
        MONITORINFO monitor={0};monitor.cbSize=sizeof monitor;
        windowed_placement.length=sizeof windowed_placement;
        if(!GetWindowPlacement(w,&windowed_placement) ||
           !GetMonitorInfoA(MonitorFromWindow(w,MONITOR_DEFAULTTONEAREST),&monitor))return;
        windowed_style=GetWindowLongPtrA(w,GWL_STYLE);
        fullscreen=1;
        SetWindowLongPtrA(w,GWL_STYLE,windowed_style & ~(LONG_PTR)WS_OVERLAPPEDWINDOW);
        SetWindowPos(w,NULL,monitor.rcMonitor.left,monitor.rcMonitor.top,
            monitor.rcMonitor.right-monitor.rcMonitor.left,monitor.rcMonitor.bottom-monitor.rcMonitor.top,
            SWP_NOZORDER|SWP_NOOWNERZORDER|SWP_FRAMECHANGED);
    } else {
        fullscreen=0;
        SetWindowLongPtrA(w,GWL_STYLE,windowed_style);
        SetWindowPlacement(w,&windowed_placement);
        SetWindowPos(w,NULL,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_NOZORDER|SWP_NOOWNERZORDER|SWP_FRAMECHANGED);
    }
}
static LRESULT CALLBACK window_proc(HWND w,UINT msg,WPARAM wp,LPARAM lp) {
    /* Consume the chord before Enter can select a menu item or fire. */
    if(msg==WM_SYSKEYDOWN && wp==VK_RETURN && (lp&(1L<<29))) {
        if(!(lp&(1L<<30)))toggle_fullscreen(w);
        fullscreen_enter_held=1;held_keys[VK_RETURN]=0;return 0;
    }
    if(fullscreen_enter_held && wp==VK_RETURN && (msg==WM_KEYUP || msg==WM_SYSKEYUP)) {
        fullscreen_enter_held=0;held_keys[VK_RETURN]=0;return 0;
    }

    if(msg==WM_KILLFOCUS)memset(held_keys,0,sizeof held_keys);
    if(msg==WM_KEYDOWN || msg==WM_KEYUP || msg==WM_SYSKEYDOWN || msg==WM_SYSKEYUP) {
        wp=input_key(wp,lp);
        if(wp<256)held_keys[wp]=(msg==WM_KEYDOWN || msg==WM_SYSKEYDOWN);
    }
    if(msg==WM_ENTERMENULOOP) { ++menu_entries; return 0; }
    /* Alt is a gameplay key. Do not enter Windows' modal keyboard menu. */
    if(msg==WM_SYSCOMMAND && (wp&0xfff0)==SC_KEYMENU) return 0;
    if((msg==WM_SYSKEYDOWN || msg==WM_SYSKEYUP) && wp==VK_MENU) return 0;
    /* Windows sends F10 as a system key even without Alt. Route only this
       fixture shortcut through normal key handling; retain Alt+F4, etc. */
    if(wp==VK_F10 && msg==WM_SYSKEYUP)return 0;
    if(wp==VK_F10 && msg==WM_SYSKEYDOWN)msg=WM_KEYDOWN;
    if(msg==WM_CLOSE) { running=0; return 0; }
    if(msg==WM_SIZE) { width=LOWORD(lp); height=HIWORD(lp); if(!height) height=1; return 0; }
    if(msg==WM_KEYDOWN) {
        if(binding_wait && !(lp&(1L<<30))){if(wp!=VK_ESCAPE && wp>0 && wp<256){bindings[option_row]=(unsigned)wp;settings_write();}binding_wait=0;return 0;}
        if(caves && objects.progress->complete && !title_mode) {
            if(wp==VK_RETURN || wp=='S'){if(!(lp&(1L<<30)))load_next_level();return 0;}
            if(wp!='R')return 0;
        }
        if(wp==bindings[12] || wp==VK_ESCAPE) {
            if(!(lp&(1L<<30)) && (play.lara.health>0 || play.dead_ticks>60 || title_mode)){if(inventory_open)inventory_input|=TOMB_RING_BACK;else {death_menu=play.lara.health<=0;inventory_begin();}}
            return 0;
        }
        if(inventory_open) {
            if(!(lp&(1L<<30))) {
                if(wp==VK_UP || wp==VK_NUMPAD8)inventory_input|=16;
                if(wp==VK_DOWN || wp==VK_NUMPAD2)inventory_input|=32;
                if(wp==VK_LEFT || wp==VK_NUMPAD4)inventory_input|=TOMB_RING_LEFT;
                if(wp==VK_RIGHT || wp==VK_NUMPAD6)inventory_input|=TOMB_RING_RIGHT;
                if(wp==VK_RETURN || wp==bindings[8])inventory_input|=TOMB_RING_SELECT;
            }
            return 0;
        }
        if(wp==VK_ESCAPE) running=0;
        if(wp=='P') paused=!paused;
        if(wp==bindings[9] && !(lp&(1L<<30)))draw_requested=1;
        if(caves && level_number==1 && wp>=VK_F2 && wp<=VK_F4){if(wp==VK_F2 && held_keys['A'])interest_start();else hazard_start((int)(wp-VK_F2));}
        if(caves && level_number==1 && (wp==VK_F5 || wp==VK_F6 || wp==VK_F12))combat_start(wp==VK_F5?7:wp==VK_F6?8:9);
        if(caves && level_number==1 && wp>=VK_F9 && wp<=VK_F11)switch_start((int)(wp-VK_F9));
        if(caves && level_number==1 && (wp==VK_F7 || wp==VK_F8)) slope_start(wp==VK_F8);
        if(wp==VK_F6 && !caves) { pool_start(); orbit=0; distance=1536; elapsed=0; accumulator=0; pose_mode=0; }
        if(wp=='R') { tomb_objects_reset(&objects); audio_stop();tomb_sound_output_reset(sound_output);paused=0;camera_hold=0;camera.ready=0;render_reset(); orbit=0; distance=1536; elapsed=0; accumulator=0; pose_mode=0; tomb_playtest_init(&play,level,sine_table,visual); play.movement_only=caves;play.objects=caves?&objects:NULL; }
        if(wp=='R'){objects.progress->music.current_track=tomb_music_level_track(level_number);draw_requested=0;inventory_open=death_menu=slot_menu=0;play.inventory=level_inventory;}
        if(caves && level_number==2 && wp==VK_F8)city_start(7);
        if(caves && level_number==2 && wp==VK_F9)finish_start();
        if(caves && level_number==2 && wp>=VK_F1 && wp<=VK_F7)city_start((int)(wp-VK_F1));
        if(caves && level_number==1 && wp==VK_F1){if(held_keys['A'])finish_start();else pickup_start(held_keys['S'] || held_keys[VK_RETURN]);}
        return 0;
    }
    return DefWindowProcA(w,msg,wp,lp);
}
#include "../tests/frontend_test.h"
int main(int argc,char **argv) {
    int shotgun_test=0,city_test=0,combat_test=0,pickup_test=0,finish_test=0,select_level=0;
    char path[MAX_PATH],error[256]; const char *shot=NULL,*trace=NULL; double shot_time=0; int interest_test=0,quest_ui_test=0, simulate=0, ledge_test=0, fast_fall_test=0, jump_test=0, standing_test=0, grab_test=0, climb_test=0, window_input_test=0, pool_test=0, forward_test=0, vault_test=0,gym_test=0,render_test=0,slide_test=0,switch_test=0,hazard_test=0; uint32_t scripted_input=0;
    title_mode=argc==1;if(title_mode)caves=1;
    DWORD path_length=GetModuleFileNameA(NULL,path,MAX_PATH); if(!path_length || path_length>=MAX_PATH-64) return 1; char *slash=strrchr(path,'\\'); if(!slash) return 1;
    strcpy(slash,"\\..\\work\\reference-assets\\DATA\\GYM.PHD");
    for(int i=1;i<argc;i++) {
        if(!strcmp(argv[i],"--title")){title_mode=1;caves=1;}
        else if(!strcmp(argv[i],"--frontend-test")){front_test=1;caves=1;}
        else if(!strcmp(argv[i],"--lighting-test"))lighting_test=1;
        else if(!strcmp(argv[i],"--interpolation-test"))interpolation_test=1;
        else if(!strcmp(argv[i],"--frontend-capture") && i+1<argc){front_capture=atoi(argv[++i]);title_mode=1;caves=1;}
        else if(!strcmp(argv[i],"--capture") && i+1<argc) shot=argv[++i];
        else if(!strcmp(argv[i],"--level-menu-test"))return level_picker(1)==15 && level_picker(2)==-1?0:2;
        else if(!strcmp(argv[i],"--level-menu"))select_level=1;
        else if(!strcmp(argv[i],"--level") && i+1<argc){
            char *end=NULL;long n=strtol(argv[++i],&end,10);
            if(!end || *end || n<0 || n>=LEVEL_CHOICE_COUNT)return 1;
            level_number=(int)n;caves=n!=0;
        }
        else if(!strcmp(argv[i],"--caves")){caves=1;level_number=1;}
        else if(!strcmp(argv[i],"--interest-test"))interest_test=1;
        else if(!strcmp(argv[i],"--quest-ui-test"))quest_ui_test=1;
        else if(!strcmp(argv[i],"--city")){caves=1;level_number=2;}
        else if(!strcmp(argv[i],"--city-test") && i+1<argc)city_test=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--shotgun-test"))shotgun_test=1;
        else if(!strcmp(argv[i],"--pickup-test"))pickup_test=1;
        else if(!strcmp(argv[i],"--finish-test"))finish_test=1;
        else if(!strcmp(argv[i],"--combat-test") && i+1<argc) combat_test=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--hazard-test") && i+1<argc) hazard_test=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--switch-test") && i+1<argc) switch_test=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--slide-test") && i+1<argc) slide_test=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--render-test") && i+1<argc) render_test=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--gym-test") && i+1<argc) gym_test=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--pool-test")) pool_test=1;
        else if(!strcmp(argv[i],"--forward-test")) forward_test=1;
        else if(!strcmp(argv[i],"--vault-test") && i+1<argc) vault_test=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--window-input-test")) window_input_test=1;
        else if(!strcmp(argv[i],"--climb-test")) { climb_test=1; grab_test=1; }
        else if(!strcmp(argv[i],"--grab-test")) grab_test=1;
        else if(!strcmp(argv[i],"--standing-test")) standing_test=1;
        else if(!strcmp(argv[i],"--jump-test")) jump_test=1;
        else if(!strcmp(argv[i],"--fast-fall-test")) fast_fall_test=1;
        else if(!strcmp(argv[i],"--ledge-test")) ledge_test=1;
        else if(!strcmp(argv[i],"--simulate") && i+1<argc) simulate=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--input") && i+1<argc) scripted_input=(uint32_t)strtoul(argv[++i],NULL,0);
        else if(!strcmp(argv[i],"--inventory-screen"))inventory_capture=1;
        else if(!strcmp(argv[i],"--ring-object") && i+1<argc)ring_object=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--ring-test") && i+1<argc)ring_capture=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--peru-test"))peru_test=1;
        else if(!strcmp(argv[i],"--transition-test"))transition_test=1;
        else if(!strcmp(argv[i],"--trace") && i+1<argc) trace=argv[++i];
        else if(!strcmp(argv[i],"--time") && i+1<argc) shot_time=atof(argv[++i]);
        else if(!strcmp(argv[i],"--distance") && i+1<argc) distance=atof(argv[++i]);
        else if(!strcmp(argv[i],"--orbit") && i+1<argc) { orbit=atof(argv[++i]); manual_camera=1; }
        else if(!strcmp(argv[i],"--follow-camera")) manual_camera=0;
        else if(!strcmp(argv[i],"--animation") && i+1<argc) animation=atoi(argv[++i]);
        else { MessageBoxA(NULL,"Usage: tomb_preview [--caves] [--capture image.ppm] [--time seconds] [--animation 0|1|11]","Preview",MB_ICONERROR); return 1; }
    }
    if(select_level){level_number=level_picker(0);if(level_number<0)return 0;caves=level_number!=0;}
    if((animation!=0 && animation!=1 && animation!=11) || !isfinite(shot_time) || shot_time<0 || !isfinite(orbit) || !isfinite(distance) || distance<600 || distance>5000) return 1;
    if(slide_test && (!caves || slide_test<1 || slide_test>2))return 1;
    if(caves) {
        if(render_test || gym_test || pool_test || forward_test || vault_test || climb_test || grab_test || standing_test || jump_test || fast_fall_test || ledge_test)return 1;
        snprintf(slash,(size_t)(path+MAX_PATH-slash),"/../work/reference-assets/DATA/%s",level_choices[level_number].file);
    }
    level=tomb_level_load(path,error,sizeof error);
    if(!level || !(visual=tomb_visual_load(level,error,sizeof error)) || !tomb_lara_start(level,&start)) {
        if(shot){FILE *failure=fopen("build/level-load-error.txt","w");if(failure){fprintf(failure,"%s: %s (level=%d visual=%d)\n",path,error,level!=NULL,visual!=NULL);fclose(failure);}}
        else MessageBoxA(NULL,error[0]?error:"Lara start data is unavailable.","Cannot load level",MB_ICONERROR); return 1;
    }
    strcpy(slash,"\\..\\work\\reference-assets\\sine.bin");
    FILE *sine_file=fopen(path,"rb");
    if(!sine_file || fread(sine_table,sizeof sine_table,1,sine_file)!=1) return 1;
    fclose(sine_file);
    room_rects=calloc(level->room_count,sizeof *room_rects);if(!room_rects)return 1;
    if(!tomb_objects_init(&objects,level,visual))return 1;
    if(!tomb_playtest_init(&play,level,sine_table,visual)) return 1;
    play.movement_only=caves;play.objects=caves?&objects:NULL;level_inventory=play.inventory;
    objects.progress->music.current_track=tomb_music_level_track(level_number);
    if(interest_test){if(level_number!=1)return 1;interest_start();}
    if(city_test){if(level_number!=2 || city_test<1 || city_test>8 || !shot)return 1;city_start(city_test-1);}
    if(shotgun_test){if(!caves || !shot)return 1;tomb_inventory_add(&play.inventory,85);play.inventory.ammo[1]=120;play.requested_weapon=4;}
    if(pickup_test)pickup_start(0);
    if(finish_test)finish_start();
    if(combat_test){
        if(!caves || combat_test<1 || combat_test>6 || !shot)return 1;
        combat_start(combat_test<=3?combat_test+6:combat_test==4?19:18);
        if(combat_test==6){
            TombModel m;if(!tomb_visual_model(visual,18,&m))return 1;
            for(size_t j=0;j<objects.count;j++)if(objects.items[j].object==18 && objects.items[j].active){
                TombActor *a=&objects.items[j].actor;a->animation=(int16_t)(m.animation+6);a->frame=level->animations[a->animation].first_frame;a->current=a->goal=7;objects.enemies->items[j].touch=0x3000;
            }
        }
    }
    if(slide_test){if(!caves || slide_test<1 || slide_test>2 || !shot)return 1;slope_start(slide_test==2);}
    if(hazard_test){if(!caves || hazard_test<1 || hazard_test>3 || !shot)return 1;hazard_start(hazard_test-1);}
    if(switch_test){if(!caves || switch_test<1 || switch_test>3 || !shot)return 1;switch_start(switch_test-1);}
    if(render_test) {
        if(!shot || simulate<=0 || render_test<1 || render_test>2)return 1;
        play.lara.actor.x=render_test==1?44544:51712;
        play.lara.actor.y=render_test==1?-1280:1280;
        play.lara.actor.z=render_test==1?51000:40448;
        play.lara.actor.room=render_test==1?7:11;
        play.lara.actor.yaw=0;
    }
    if(ledge_test) {
        if(!shot || simulate<=0) return 1;
        play.lara.actor.x=36600; play.lara.actor.y=-1536;
    }
    if(fast_fall_test) {
        if(!shot || simulate<=0 || ledge_test) return 1;
        play.lara.actor.x=46592; play.lara.actor.y=-3000; play.lara.actor.z=41472; play.lara.actor.room=9;
        play.lara.actor.current=play.lara.actor.goal=29; play.lara.actor.animation=93; play.lara.actor.frame=1473;
        play.lara.actor.flags|=8;
    }
    if(jump_test || standing_test) {
        if(!shot || simulate<=0 || ledge_test || fast_fall_test) return 1;
        play.lara.actor.x=46592; play.lara.actor.y=0; play.lara.actor.z=37000; play.lara.actor.room=9; play.lara.actor.yaw=0;
    }
    if(standing_test) {
        /* Point each directional test into the same open corridor. */
        if(scripted_input==18) play.lara.actor.yaw=-32768;
        else if(scripted_input==24) play.lara.actor.yaw=-16384;
        else if(scripted_input==20) play.lara.actor.yaw=16384;
    }
    if(grab_test) {
        if(!shot || simulate<=0 || ledge_test || fast_fall_test || jump_test || standing_test) return 1;
        play.lara.actor.x=47616; play.lara.actor.y=1024; play.lara.actor.z=35940;
        play.lara.actor.room=9; play.lara.actor.yaw=-32768;
        if(climb_test) { play.lara.actor.x=50076; play.lara.actor.y=2560; play.lara.actor.z=39424; play.lara.actor.yaw=16384; }
    }
    if(pool_test) pool_start();
    if(forward_test) {
        play.lara.actor.x=47616;play.lara.actor.y=768;play.lara.actor.z=38140;play.lara.actor.room=9;play.lara.actor.yaw=-32768;
    }
    if(vault_test) {
        if(vault_test<1 || vault_test>3) return 1;
        const int pos[3][5]={{42908,-1280,52736,7,16384},{49664,2560,40860,9,0},{47616,1024,35940,9,-32768}};
        const int *v=pos[vault_test-1];play.lara.actor.x=v[0];play.lara.actor.y=v[1];play.lara.actor.z=v[2];play.lara.actor.room=(int16_t)v[3];play.lara.actor.yaw=(int16_t)v[4];
    }
    if(gym_test) {
        if(!shot || simulate<=0 || gym_test<1 || gym_test>3)return 1;
        TombActor *a=&play.lara.actor;
        if(gym_test==1){a->x=46592;a->y=-5400;a->z=41472;a->room=9;a->current=a->goal=29;a->animation=93;a->frame=1473;a->flags|=8;}
        if(gym_test==2){a->x=40448;a->y=4800;a->z=60928;a->room=14;a->current=a->goal=13;a->animation=108;a->frame=1736;play.lara.water_status=1;play.lara.air=0;play.lara.health=5;}
        if(gym_test==3){a->x=50688;a->y=0;a->z=46592;a->room=9;}
    }
    pose_mode=shot && !simulate && !interpolation_test;
    if(simulate<0 || simulate>100000) return 1;
    FILE *log=trace?fopen(trace,"w"):NULL;
    if(trace && !log) return 1;
    if(log) fprintf(log,"tick,x,y,z,yaw,state,animation,frame,blocked,flags,fall_speed,health,water,pitch,air\n");
    int climb_done=0,vault_started=0;
    if(!manual_camera && !pose_mode) update_camera(1.0/30);
    for(int tick=0;tick<simulate;tick++) {
        unsigned new_input=city_test==1 && tick<45?64:combat_test?(tick==0?32:scripted_input):switch_test?(tick==0?64:scripted_input):pool_test?(play.lara.water_status==0?(tick<35?1:0):play.lara.water_status==1?18:65):forward_test?(tick<20?1:tick<40?81:64):vault_test?(vault_started?64:65):scripted_input;
        tomb_playtest_tick(&play,grab_test?(tick<15?80:tick<75?64:climb_test && !climb_done && tick<200?scripted_input:0):standing_test?(tick<15?scripted_input:0):jump_test?(tick<20?1:tick<40?17:0):new_input);
        if(!manual_camera) update_camera(1.0/30);
        const TombActor *a=&play.lara.actor;
        if(vault_test && (a->current==19 || a->current==28)) vault_started=1;
        if(climb_test && tick>75 && a->current==2) climb_done=1;
        if(log) fprintf(log,"%d,%d,%d,%d,%d,%d,%d,%d,%d,%u,%d,%d,%d,%d,%d\n",tick,a->x,a->y,a->z,a->yaw,a->current,a->animation,a->frame,play.blocked,a->flags,a->fall_speed,play.lara.health,play.lara.water_status,play.lara.pitch,play.lara.air);
    }
    if(log) fclose(log);
    HINSTANCE instance=GetModuleHandleA(NULL);
    WNDCLASSA wc={0}; wc.style=CS_OWNDC; wc.lpfnWndProc=window_proc; wc.hInstance=instance;
    wc.lpszClassName="TombReconstructionPreview"; wc.hCursor=LoadCursor(NULL,IDC_ARROW);
    if(!RegisterClassA(&wc)) return 1;
    /* width/height describe the client area, excluding the title and borders. */
    RECT initial_window={0,0,width,height};
    if(!AdjustWindowRectEx(&initial_window,WS_OVERLAPPEDWINDOW,FALSE,0))return 1;
    HWND window=CreateWindowA(wc.lpszClassName,"Tomb Raider Beyond",WS_OVERLAPPEDWINDOW,CW_USEDEFAULT,CW_USEDEFAULT,initial_window.right-initial_window.left,initial_window.bottom-initial_window.top,NULL,NULL,instance,NULL);
    if(!window) return 1;
    if(window_input_test) {
        SendMessageA(window,WM_SYSKEYDOWN,VK_MENU,0x20380001);
        SendMessageA(window,WM_SYSKEYUP,VK_MENU,(LPARAM)0xc0380001u);
        SendMessageA(window,WM_SYSCOMMAND,SC_KEYMENU,0);
        SendMessageA(window,WM_SYSCOMMAND,SC_KEYMENU|3,'w');
        int passed=menu_entries==0 && !paused && running;
        RECT before,after,client_rect;GetWindowRect(window,&before);GetClientRect(window,&client_rect);
        passed=passed && client_rect.right*3==client_rect.bottom*4;
        MONITORINFO monitor={0};monitor.cbSize=sizeof monitor;
        GetMonitorInfoA(MonitorFromWindow(window,MONITOR_DEFAULTTONEAREST),&monitor);
        unsigned saved_inventory_input=inventory_input;
        SendMessageA(window,WM_SYSKEYDOWN,VK_RETURN,(LPARAM)(1u<<29));
        GetWindowRect(window,&after);GetClientRect(window,&client_rect);
        passed=passed && fullscreen && EqualRect(&after,&monitor.rcMonitor) &&
            client_rect.right==monitor.rcMonitor.right-monitor.rcMonitor.left &&
            client_rect.bottom==monitor.rcMonitor.bottom-monitor.rcMonitor.top &&
            !held_keys[VK_RETURN] && inventory_input==saved_inventory_input;
        SendMessageA(window,WM_SYSKEYDOWN,VK_RETURN,(LPARAM)((1u<<29)|(1u<<30)));
        passed=passed && fullscreen; /* Auto-repeat must not toggle again. */
        SendMessageA(window,WM_SYSKEYUP,VK_RETURN,(LPARAM)(1u<<29));
        SendMessageA(window,WM_SYSKEYDOWN,VK_RETURN,(LPARAM)(1u<<29));
        SendMessageA(window,WM_KEYUP,VK_RETURN,0); /* Alt may be released first. */
        GetWindowRect(window,&after);
        passed=passed && !fullscreen && EqualRect(&before,&after) && !held_keys[VK_RETURN];
        SendMessageA(window,WM_KEYDOWN,'P',1); passed=passed && paused;
        SendMessageA(window,WM_KEYDOWN,'P',1); passed=passed && !paused;
        orbit=1;camera.ready=1;camera_hold=1;
        SendMessageA(window,WM_KEYDOWN,'C',1);
        passed=passed && orbit==1 && camera_hold==1 && camera.ready;
        {
            const unsigned keys[]={VK_NUMPAD8,VK_NUMPAD2,VK_NUMPAD4,VK_NUMPAD6,VK_NUMPAD7,VK_NUMPAD9,'A','D','S',VK_RETURN,'W',VK_NUMPAD0};
            const unsigned bits[]={1,2,4,8,1024,2048,128,16,64,64,4096,512};
            memset(held_keys,0,sizeof held_keys);
            for(unsigned k=0;k<sizeof keys/sizeof *keys;k++) {
                SendMessageA(window,WM_KEYDOWN,keys[k],1);passed=passed && game_input()==bits[k];
                SendMessageA(window,WM_KEYUP,keys[k],1);passed=passed && !game_input();
            }
            const unsigned nav[]={VK_UP,VK_DOWN,VK_LEFT,VK_RIGHT,VK_HOME,VK_PRIOR};
            const unsigned scans[]={0x48,0x50,0x4b,0x4d,0x47,0x49};
            for(unsigned k=0;k<6;k++) {
                SendMessageA(window,WM_KEYDOWN,nav[k],(LPARAM)(scans[k]<<16));passed=passed && game_input()==bits[k];
                SendMessageA(window,WM_KEYUP,nav[k],(LPARAM)(scans[k]<<16));
                SendMessageA(window,WM_KEYDOWN,nav[k],(LPARAM)((scans[k]<<16)|(1u<<24)));passed=passed && !game_input();
                SendMessageA(window,WM_KEYUP,nav[k],(LPARAM)((scans[k]<<16)|(1u<<24)));
            }
            SendMessageA(window,WM_KEYDOWN,VK_INSERT,(LPARAM)(0x52u<<16));passed=passed && game_input()==512;
            SendMessageA(window,WM_KEYUP,VK_INSERT,(LPARAM)(0x52u<<16));passed=passed && !game_input();
            const unsigned removed[]={'Q','J',VK_MENU,VK_CONTROL,VK_SHIFT,VK_TAB,'C','1','2','3'};
            for(unsigned k=0;k<sizeof removed/sizeof *removed;k++) {
                SendMessageA(window,WM_KEYDOWN,removed[k],1);passed=passed && !game_input() && !pose_mode && !inventory_open;
                SendMessageA(window,WM_KEYUP,removed[k],1);
            }
            SendMessageA(window,WM_KEYDOWN,'A',1);SendMessageA(window,WM_KEYDOWN,VK_NUMPAD8,1);
            passed=passed && game_input()==129;SendMessageA(window,WM_KEYUP,'A',1);
            SendMessageA(window,WM_KEYDOWN,VK_NUMPAD8,1);SendMessageA(window,WM_KILLFOCUS,0,0);passed=passed && !game_input();
            unsigned previous=bindings[0];bindings[0]='T';
            SendMessageA(window,WM_KEYDOWN,'T',1);passed=passed && game_input()==1;
            SendMessageA(window,WM_KEYUP,'T',1);bindings[0]=previous;
            SendMessageA(window,WM_KEYDOWN,'E',1);passed=passed && inventory_open;
            SendMessageA(window,WM_KEYUP,'E',1);inventory_open=0;inventory_input=0;
        }
        if(caves) {
            const int combat_keys[3]={VK_F5,VK_F6,VK_F12};
            for(int fixture=0;fixture<3;fixture++) {
                SendMessageA(window,WM_KEYDOWN,(WPARAM)combat_keys[fixture],1);
                passed=passed && objects.enemies->head>=0 && objects.items[objects.enemies->head].object==fixture+7;
                SendMessageA(window,WM_KEYDOWN,VK_SPACE,1);passed=passed && draw_requested && !paused;
                passed=passed && tomb_playtest_tick(&play,draw_requested?32:0);draw_requested=0;
                for(int t=0;t<24;t++)passed=passed && tomb_playtest_tick(&play,64);
                passed=passed && play.pistols.status==4 && play.pistols.shots>0;
            }
            for(int fixture=0;fixture<3;fixture++) {
                SendMessageA(window,WM_KEYDOWN,VK_F2+fixture,1);
                static const int rooms[3]={14,32,6};passed=passed && play.lara.actor.room==rooms[fixture] && !paused && !camera.ready;
            }
            static const unsigned ids[3]={10,42,52};
            for(int i=0;i<3;i++) {
                SendMessageA(window,i==1?WM_SYSKEYDOWN:WM_KEYDOWN,VK_F9+i,1);
                const TombActor *s=&objects.items[ids[i]].actor;
                passed=passed && play.lara.actor.room==s->room && play.lara.actor.yaw==s->yaw;
                int saw_camera=0;
                for(int tick=0;tick<100;tick++) {
                    passed=passed && tomb_playtest_tick(&play,64);
                    update_camera(1.0/30);
                    if(objects.camera.active)saw_camera=1;
                }
                passed=passed && (saw_camera==(i!=0));
                SendMessageA(window,i==1?WM_SYSKEYUP:WM_KEYUP,VK_F9+i,(LPARAM)0xc0000001u);
            }
            passed=passed && !menu_entries;
            memset(held_keys,0,sizeof held_keys);
            SendMessageA(window,WM_KEYDOWN,VK_F1,1);
            for(int t=0;t<110;t++)passed=passed && tomb_playtest_tick(&play,64);
            SendMessageA(window,WM_KEYDOWN,'E',1);passed=passed && inventory_open;
            SendMessageA(window,WM_KEYUP,'E',1);
            for(int t=0;t<20;t++)inventory_tick(0);
            SendMessageA(window,WM_KEYDOWN,VK_RETURN,1);passed=passed && inventory_input==TOMB_RING_SELECT;
            SendMessageA(window,WM_KEYUP,VK_RETURN,1);inventory_input=0;
            /* Right moves to the previous entry, wrapping compass to medipack. */
            SendMessageA(window,WM_KEYDOWN,VK_RIGHT,1);inventory_tick(inventory_input);inventory_input=0;
            for(int t=0;t<14;t++)inventory_tick(0);
            play.lara.health=200;SendMessageA(window,WM_KEYDOWN,'S',1);inventory_tick(inventory_input);inventory_input=0;
            passed=passed && inventory_open && play.lara.health==200;
            for(int t=0;t<180 && inventory_open;t++)inventory_tick(0);
            passed=passed && !inventory_open && play.lara.health==700 && !play.inventory.counts[9];
            SendMessageA(window,WM_KEYDOWN,VK_ESCAPE,1);passed=passed && inventory_open && running;
            for(int t=0;t<20;t++)inventory_tick(0);
            SendMessageA(window,WM_KEYDOWN,VK_ESCAPE,1);inventory_tick(inventory_input);inventory_input=0;
            passed=passed && inventory_open;
            for(int t=0;t<18;t++)inventory_tick(0);passed=passed && !inventory_open;

        } else {
            SendMessageA(window,WM_KEYDOWN,VK_F6,1);
            passed=passed && play.lara.actor.room==13 && play.lara.actor.x==40448 && play.lara.actor.z==57800 && !play.lara.water_status;
        }
        SendMessageA(window,WM_KEYDOWN,'R',1);
        passed=passed && play.lara.actor.room==start.actor.room && play.lara.actor.x==start.actor.x;
        SendMessageA(window,WM_SYSCOMMAND,SC_CLOSE,0); passed=passed && !running;
        DestroyWindow(window); tomb_visual_free(visual); tomb_level_free(level);
        return passed?0:2;
    }
    if(quest_ui_test){
        if(level_number!=2)return 2;
        for(int variant=0;variant<2;variant++){
            city_start(5+variant);
            if(!tomb_playtest_tick(&play,64) || !play.quest_request)return 3;
            inventory_begin();for(int t=0;t<20;t++)inventory_tick(0);
            if(!inventory_keys || !inventory_open || inventory_ring.count!=1)return 4;
            SendMessageA(window,WM_KEYDOWN,variant?VK_RETURN:'S',1);inventory_tick(inventory_input);inventory_input=0;
            for(int t=0;t<100 && inventory_open;t++)inventory_tick(0);
            if(inventory_open || play.inventory.chosen!=(variant?114:133))return 5;
            for(int t=0;t<180;t++)if(!tomb_playtest_tick(&play,0))return 6;
            if(!objects.doors[variant?78:8].open)return 7;
        }
        city_start(5);inventory_begin();for(int t=0;t<20;t++)inventory_tick(0);
        SendMessageA(window,WM_KEYDOWN,VK_NUMPAD8,1);inventory_tick(inventory_input);inventory_input=0;
        for(int t=0;t<30;t++)inventory_tick(0);
        if(!inventory_keys || inventory_ring.motion.status!=1 || inventory_ring.radius!=688 || inventory_ring.pitch)return 8;
        SendMessageA(window,WM_KEYDOWN,VK_NUMPAD2,1);inventory_tick(inventory_input);inventory_input=0;
        for(int t=0;t<30;t++)inventory_tick(0);
        if(inventory_keys || inventory_ring.motion.status!=1 || inventory_ring.radius!=688 || inventory_ring.pitch)return 9;
        DestroyWindow(window);return 0;
    }
    RECT client; GetClientRect(window,&client); width=client.right; height=client.bottom;
    HDC dc=GetDC(window); PIXELFORMATDESCRIPTOR pfd={0}; pfd.nSize=sizeof pfd; pfd.nVersion=1;
    pfd.dwFlags=PFD_DRAW_TO_WINDOW|PFD_SUPPORT_OPENGL|PFD_DOUBLEBUFFER; pfd.iPixelType=PFD_TYPE_RGBA;
    pfd.cColorBits=24; pfd.cDepthBits=24;
    int format=ChoosePixelFormat(dc,&pfd);
    if(!format || !SetPixelFormat(dc,format,&pfd)) return 1;
    HGLRC context=wglCreateContext(dc);
    if(!context || !wglMakeCurrent(dc,context)) return 1;
    glEnable(GL_DEPTH_TEST); glAlphaFunc(GL_GREATER,.5f); glClearColor(.04f,.05f,.07f,1);
    if(!make_tiles())return 1;
    if(peru_test)return peru_render_check()?0:2;
    if(lighting_test)return lighting_render_check()?0:2;
    if(interpolation_test){int passed=interpolation_render_check();if(passed && shot)passed=capture(shot);return passed?0:2;}
    if(!frontend_assets())return 1;
    if(!shot && !front_test)settings_read();
    if(front_test)return frontend_check()?0:2;
    if(title_mode)frontend_title();
    if(front_capture){
        for(int t=0;t<32;t++)inventory_tick(0);
        if(front_capture>=3 && front_capture<=5){int object=front_capture==3?95:front_capture==4?96:97;while(inventory_ring.items[inventory_ring.current].object!=object){inventory_tick(TOMB_RING_RIGHT);for(int t=0;t<32;t++)inventory_tick(0);}}
        if(front_capture>1){inventory_tick(TOMB_RING_SELECT);for(int t=0;t<90;t++)inventory_tick(0);}
        if(front_capture==7){
            if(inventory_ring.items[0].frame==14){inventory_tick(TOMB_RING_RIGHT);for(int t=0;t<30;t++)inventory_tick(0);}
            inventory_tick(TOMB_RING_SELECT);
        }
        if(front_capture==6){
            if(!load_game_level(1,0,NULL))return 2;
            inventory_begin();for(int t=0;t<32;t++)inventory_tick(0);inventory_tick(32);for(int t=0;t<32;t++)inventory_tick(0);
            inventory_tick(TOMB_RING_SELECT);for(int t=0;t<90;t++)inventory_tick(0);
            inventory_tick(TOMB_RING_SELECT);slot_current=15;
        }
    }
    if(transition_test) {
        int expected_level=level_number+1;
        if(level_number==2 || level_number==3){finish_start();if(!tomb_playtest_tick(&play,0) || !objects.progress->complete)return 2;}
        tomb_inventory_add(&play.inventory,93);tomb_inventory_add(&play.inventory,89);play.lara.health=400;
        play.inventory.quest[4]=1;play.inventory.ticks=900;play.inventory.pickups=3;
        if(expected_level==3 || expected_level==4)SendMessageA(window,WM_KEYDOWN,VK_RETURN,1);
        else if(!load_next_level())return 2;
        if(level_number!=expected_level || play.inventory.quest[4] || play.inventory.ticks || play.inventory.pickups || play.inventory.counts[9]!=1 || play.inventory.counts[5]!=1 || play.lara.health!=1000 || objects.progress->secrets)return 2;
        for(int t=0;t<120;t++)if(!tomb_playtest_tick(&play,t<60?1:0))return 2;
        update_camera(1.0/30);
    }
    if(inventory_capture || ring_capture>=0){
        inventory_begin();int frames=ring_capture>=0?ring_capture:32;
        for(int t=0;t<frames;t++)inventory_tick(t==32?(ring_object==72?0:ring_object==108?TOMB_RING_RIGHT:TOMB_RING_LEFT):t==50?TOMB_RING_SELECT:0);
    }

    if(!shot) {
        if(!sound_output && tomb_sound_bank_load(&sound_bank,level)) {
            tomb_sound_init(&sound_mixer,&sound_bank);
            sound_output=tomb_sound_output_open(&sound_mixer);
            tomb_sound_init(&ring_sound_mixer,&sound_bank);ring_sound_output=tomb_sound_output_open(&ring_sound_mixer);
        }
        if(!sound_output || !ring_sound_output)sound_failed=1;
        ShowWindow(window,SW_SHOW);
    }
    LARGE_INTEGER frequency,last,now; QueryPerformanceFrequency(&frequency); QueryPerformanceCounter(&last);
    int ok=1,was_suspended=1;
    while(running) {
        MSG msg;
        while(PeekMessage(&msg,NULL,0,0,PM_REMOVE)) { TranslateMessage(&msg); DispatchMessage(&msg); }
        QueryPerformanceCounter(&now); double dt=(double)(now.QuadPart-last.QuadPart)/frequency.QuadPart; last=now;
        if(dt>.1) dt=.1;
        if(!paused) elapsed+=dt;
        int suspended=paused || inventory_open || title_mode || objects.progress->complete || GetActiveWindow()!=window;
        if(!shot && !pose_mode && !suspended){
            if(was_suspended)render_reset();
            if(!render_tick){
                if(camera.ready){memcpy(camera.previous_eye,camera.eye,sizeof camera.eye);memcpy(camera.previous_target,camera.target,sizeof camera.target);}
                if(!render_capture()){ok=0;break;}
            }
        }
        was_suspended=suspended;
        if(!shot && !pose_mode && !paused && !inventory_open && !objects.progress->complete && GetActiveWindow()==window) {
            uint32_t input=game_input();
            accumulator+=dt;
            while(accumulator>=1.0/30.0) { if(play.lara.health<=0 && tomb_death_menu_due(play.dead_ticks,input)){death_menu=1;inventory_begin();break;} if(tomb_playtest_tick(&play,input|(draw_requested?32:0)) && sound_output)sound_tick();draw_requested=0;if(objects.progress->complete)backdrop_dirty=1; update_camera(1.0/30); if(!render_capture()){ok=0;running=0;break;} accumulator-=1.0/30.0; if(play.quest_request){death_menu=play.lara.health<=0;inventory_begin();break;} }
        } else accumulator=0;
        if(!shot && inventory_open && GetActiveWindow()==window) {
            inventory_accumulator+=dt;
            while(inventory_accumulator>=1.0/30.0 && inventory_open) {
                unsigned input=inventory_input;inventory_input=0;
                if(inventory_ring.motion.status==1 && (held_keys[VK_LEFT] || held_keys[VK_NUMPAD4]))input|=TOMB_RING_LEFT;
                if(inventory_ring.motion.status==1 && (held_keys[VK_RIGHT] || held_keys[VK_NUMPAD6]))input|=TOMB_RING_RIGHT;
                inventory_tick(input);inventory_accumulator-=1.0/30.0;
            }
        } else inventory_accumulator=0;
        if(!shot) {
            char title[256];
            snprintf(title,sizeof title,"Tomb %s | Num 8/2 move, 4/6 turn, 7/9 sidestep | A walk, D jump, W roll, Num0 look, S/Enter action, Space weapons | E inventory, P pause, R reset | %s",level_choices[level_number].name,audio_error[0]?audio_error:sound_failed?"Sound effects unavailable":play.status);
            SetWindowTextA(window,title);
        }
        if(!shot && !pose_mode && !paused && !inventory_open && !objects.progress->complete && GetActiveWindow()==window)camera_alpha=accumulator*30;
        if(!shot) {
            int suspended=paused || inventory_open || objects.progress->complete || GetActiveWindow()!=window;
            audio_update(suspended);
            if(sound_output && !tomb_sound_output_update(sound_output,suspended))sound_failed=1;
            if(ring_sound_output && !tomb_sound_output_update(ring_sound_output,GetActiveWindow()!=window))sound_failed=1;
        }
        if(shot) elapsed=shot_time;
        if(title_mode){glViewport(0,0,width,height);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);}else if(!draw_frame()) { ok=0; break; }
        overlay();
        if(shot) { ok=capture(shot); break; }
        SwapBuffers(dc); Sleep(1);
    }
    render_reset();frontend_free();audio_stop();
    tomb_sound_output_close(ring_sound_output);tomb_sound_output_close(sound_output);tomb_sound_bank_free(&sound_bank);
    glDeleteTextures((GLsizei)visual->tile_count,font_tiles);free(font_tiles);glDeleteTextures((GLsizei)(visual->tile_count*2+1),tiles); free(tiles);
    light_DeleteProgram(shade_program);
    wglMakeCurrent(NULL,NULL); wglDeleteContext(context); ReleaseDC(window,dc); DestroyWindow(window);
    free(room_rects);tomb_objects_free(&objects);tomb_visual_free(visual); tomb_level_free(level);
    return ok?0:1;
}
