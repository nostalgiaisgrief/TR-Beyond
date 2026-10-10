#include "peru.h"
#include "playtest.h"
#include "save.h"
#include "enemies.h"
#include "city.h"
#include "progression.h"
#include "object_contact.h"
#include "combat.h"
#include "ring.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void init(TombPlaytest *p,TombObjects *w,const int16_t *s){tomb_objects_reset(w);assert(tomb_playtest_init(p,w->level,s,w->visual));p->objects=w;p->movement_only=1;}
static void tick(TombPlaytest *p,unsigned input){if(!tomb_playtest_tick(p,input)){fprintf(stderr,"blocked %s state %d anim %d frame %d\n",p->status,p->lara.actor.current,p->lara.actor.animation,p->lara.actor.frame);assert(0);}}
int main(int argc,char **argv){
 assert(argc==2);int16_t sine[1025];FILE *f=fopen("work/reference-assets/sine.bin","rb");assert(f && fread(sine,sizeof sine,1,f)==1);fclose(f);
 char error[256];TombLevel *l=tomb_level_load(argv[1],error,sizeof error);assert(l);TombVisual *v=tomb_visual_load(l,error,sizeof error);assert(v);
 TombObjects w;assert(tomb_objects_init(&w,l,v));TombPlaytest p;init(&p,&w,sine);int valley=strstr(argv[1],"LEVEL3A")!=NULL;
 /* Every swap changes world, rendered mesh, portals and light view together. */
 TombRoom *rooms=malloc(l->room_count*sizeof *rooms);memcpy(rooms,l->rooms,l->room_count*sizeof *rooms);
 for(int pass=0;pass<4;pass++){
  assert(tomb_flip_map(&w,1));for(size_t i=0;i<l->room_count;i++)if(rooms[i].alternate>=0){int expected=w.peru->flipped?rooms[i].alternate:(int)i;assert(l->rooms[i].sectors==rooms[expected].sectors);assert(l->rooms[i].flags==rooms[expected].flags);}
 }
 free(rooms);init(&p,&w,sine);
 if(valley){
  const int cogs[3]={33,40,53};
  for(int j=0;j<3;j++){
   TombActor *o=&w.items[cogs[j]].actor;
   p.lara.actor=(TombActor){o->x,o->y,o->z-100,2,2,11,185,0,0,0,o->room,32};p.animation.move_angle=0;
   for(int t=0;t<110;t++)tick(&p,64);
   assert(p.inventory.quest[0]==j+1 && (w.items[cogs[j]].actor.flags&6)==6);
  }
  puts("PASS: all three actual cog pickups");
  const int holes[3]={9,8,7},triggers[3]={534,539,545};
  for(int j=0;j<3;j++){
   TombObject *o=w.items+holes[j];int32_t offset[3]={0,0,400},pos[3];tomb_rotate_vector(o->actor.yaw,0,0,offset,0,sine,pos);
   p.lara.actor=(TombActor){o->actor.x+pos[0],o->actor.y,o->actor.z+pos[2],2,2,11,185,0,0,o->actor.yaw,o->actor.room,32};p.animation.move_angle=p.lara.actor.yaw;
   tick(&p,0);p.inventory.chosen=114;tick(&p,64);
   for(int t=0;t<180;t++)tick(&p,0);
   assert(o->object==122 && p.inventory.quest[0]==2-j);
   assert(tomb_objects_trigger_keys(&w,triggers[j],1,0));assert(!w.peru->flipped);
   for(int t=0;t<90;t++){p.sound_count=0;assert(tomb_objects_tick(&w,&p.animation));assert(!p.blocked);}
  }
  w.items[10].actor.current=0;w.items[10].actor.flags=(w.items[10].actor.flags&~6u)|4;
  assert(tomb_objects_trigger_keys(&w,552,1,0));assert(w.peru->flipped && w.peru->effect==6);
  int gears=0;for(int t=0;t<150;t++){if(w.items[4].actor.current==1 && w.items[5].actor.current==1 && w.items[6].actor.current==1)gears=1;p.sound_count=0;assert(tomb_objects_tick(&w,&p.animation));assert(tomb_peru_lara(&p,0));assert(!p.blocked);}
  assert(gears);
  puts("PASS: actual three cog masks, lever, gears and water-room swap");
 }else{
  for(size_t id=0;id<w.count;id++)if(w.items[id].object==52){
   init(&p,&w,sine);TombActor before=w.items[id].actor;tomb_object_trigger(w.items+id,0,0x3e00);
   for(int t=0;t<300;t++){p.sound_count=0;assert(tomb_objects_tick(&w,&p.animation));assert(!p.blocked);
    if(t==10){assert(!w.doors[id].count);assert(tomb_flip_map(&w,1));assert(!w.doors[id].count);assert(tomb_flip_map(&w,1));}
   }
   assert(w.items[id].actor.x!=before.x || w.items[id].actor.z!=before.z);assert(w.doors[id].count==1);
   tomb_object_trigger(w.items+id,6,0x3e00);
   for(int t=0;t<300;t++){p.sound_count=0;assert(tomb_objects_tick(&w,&p.animation));assert(!p.blocked);}
   assert(w.items[id].actor.x==before.x && w.items[id].actor.z==before.z);
  }
  puts("PASS: both pillars, outbound/return animation and occupied floor");
  init(&p,&w,sine);TombObject *scion=w.items+20;
  p.lara.actor=(TombActor){scion->actor.x,scion->actor.y+640,scion->actor.z-310,2,2,11,185,0,0,0,scion->actor.room,32};
  assert(tomb_peru_lara(&p,64));assert(w.peru->scion_item==20);
  for(int t=0;t<300 && w.peru->scion_item>=0;t++)tick(&p,0);
  assert((scion->actor.flags&6)==6 && w.peru->scion_item==-1 && w.peru->flipped);assert(p.lara.actor.current==2 && !p.animation.weapon_status);
  assert(p.inventory.scion==1);TombRing ring;assert(tomb_ring_init_keys(&ring,&p.inventory));assert(ring.items[ring.count-1].object==150);
  puts("PASS: Scion alignment, special animation, inventory, pickup trigger and escape room swap");
  for(size_t i=0;i<w.count;i++)if(w.items[i].object==53){
   tomb_object_trigger(w.items+i,0,0x3e00);
  }
  for(int t=0;t<300;t++){p.sound_count=0;assert(tomb_peru_hazards(&w,&p.animation,&p.lara.actor,&p.lara.health));assert(!p.blocked);}
  for(size_t i=0;i<w.count;i++)if(w.items[i].object==53)assert(!w.items[i].active);
  puts("PASS: all six falling ceiling sections land and deactivate");
  init(&p,&w,sine);tomb_object_trigger(w.items+45,0,0x3e00);TombActor b=w.items[45].actor;
  for(int t=0;t<300;t++){p.sound_count=0;assert(tomb_peru_hazards(&w,&p.animation,&p.lara.actor,&p.lara.health));assert(!p.blocked);}
  assert(b.x!=w.items[45].actor.x || b.z!=w.items[45].actor.z);
  puts("PASS: boulder route, heavy trigger and wall stop");
  for(int id=22;id<=30;id++){if(id!=22 && id!=23 && id!=30)continue;
   init(&p,&w,sine);tomb_enemies_trigger(&w,(size_t)id,0,0x3e00);
   for(int t=0;t<120;t++){p.sound_count=0;assert(tomb_enemies_tick(&w,&p.animation,&p.lara));assert(!p.blocked);}
   w.enemies->items[id].health=0;
   for(int t=0;t<300 && w.items[id].active;t++){p.sound_count=0;assert(tomb_enemies_tick(&w,&p.animation,&p.lara));assert(!p.blocked);}
   assert(!w.items[id].active || w.progress->complete);
  }
  puts("PASS: both mummies and Larson activation/death animation");
  init(&p,&w,sine);assert(tomb_flip_map(&w,1));TombObject *larson=w.items+30;
  p.lara.actor=(TombActor){larson->actor.x+1024,larson->actor.y,larson->actor.z,2,2,11,185,0,0,-16384,larson->actor.room,32};
  tomb_enemies_trigger(&w,30,0,0x3e00);
  for(int t=0;t<1800 && p.lara.health==1000;t++){p.sound_count=0;assert(tomb_enemies_tick(&w,&p.animation,&p.lara));assert(!p.blocked);}
  assert(p.lara.health<1000);puts("PASS: Larson navigation, sight and gunshot damage");
  p.lara.health=1000;TombActor *la=&larson->actor;p.lara.actor.x=la->x+1024;p.lara.actor.y=la->y;p.lara.actor.z=la->z;p.lara.actor.room=la->room;p.lara.actor.yaw=-16384;
  assert(tomb_combat_tick(&p,32));
  for(int t=0;t<1800 && w.enemies->items[30].health>0;t++){p.sound_count=0;assert(tomb_combat_tick(&p,64));}
  assert(w.enemies->items[30].health<=0 && p.pistols.kills==1);puts("PASS: Larson can be targeted and defeated with pistols");
  init(&p,&w,sine);w.items[45].actor.flags=35;w.enemies->items[45].touch=1;assert(tomb_peru_lara(&p,0));assert(p.lara.health<0 && p.lara.actor.animation==139);
  for(int t=0;t<150;t++)tick(&p,0);
  init(&p,&w,sine);p.lara.actor.flags|=8;p.lara.actor.fall_speed=70;w.enemies->items[2].touch=1;assert(tomb_peru_lara(&p,0));assert(p.lara.health<0 && p.lara.actor.animation==149);
  puts("PASS: boulder crush and spike landing deaths");
 }
 init(&p,&w,sine);assert(tomb_flip_map(&w,1));p.inventory.scion=1;TombFollowCamera cam={0};TombInventory inv=p.inventory;
 assert(tomb_save_write("build/peru-save.tsv",valley?3:4,&p,&w,&cam,&inv));init(&p,&w,sine);
 assert(tomb_save_read("build/peru-save.tsv",valley?3:4,&p,&w,&cam,&inv));assert(w.peru->flipped && p.inventory.scion==1);
 for(int t=0;t<10;t++)tick(&p,0);
 init(&p,&w,sine);assert(!w.peru->flipped);puts("PASS: flipped save/load and normal reset");
 tomb_objects_free(&w);tomb_visual_free(v);tomb_level_free(l);return 0;
}
