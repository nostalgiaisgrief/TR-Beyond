#include "city.h"
#include "object_contact.h"
#include "hazards.h"
#include "progression.h"
#include "enemies.h"
#include "fixed.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
static void tick(TombPlaytest *p,unsigned input){if(!tomb_playtest_tick(p,input)){fprintf(stderr,"%s state=%d frame=%d\n",p->status,p->lara.actor.current,p->lara.actor.frame);assert(0);}}
static void init(TombPlaytest *p,TombObjects *w,const int16_t *s){tomb_objects_reset(w);assert(tomb_playtest_init(p,w->level,s,w->visual));p->objects=w;p->movement_only=1;}
int main(int argc,char **argv){
 assert(argc==3);char err[256];int16_t sine[1025];FILE *f=fopen(argv[2],"rb");assert(f && fread(sine,sizeof sine,1,f)==1);fclose(f);
 TombLevel *l=tomb_level_load(argv[1],err,sizeof err);assert(l);TombVisual *v=tomb_visual_load(l,err,sizeof err);assert(v);TombObjects w;assert(tomb_objects_init(&w,l,v));TombPlaytest p;
 const int dx[4]={0,1,0,-1},dz[4]={1,0,-1,0};
 for(int q=0;q<4;q++){
  init(&p,&w,sine);TombActor *a=&p.lara.actor,*b=&w.items[0].actor;
  a->x=b->x-dx[q]*612;a->y=b->y;a->z=b->z-dz[q]*612;a->room=b->room;a->yaw=tomb_word(q*16384);p.animation.move_angle=a->yaw;
  TombSectorRef ref;if(tomb_find_sector(l,a->x,a->y,a->z,a->room,&ref))a->room=(int16_t)ref.room;
  printf("block q=%d room=%d can push=%d pull=%d\n",q,a->room,tomb_block_can_move(&w,a,0,q,0),tomb_block_can_move(&w,a,0,q,1));fflush(stdout);
  if(!tomb_block_can_move(&w,a,0,q,0))continue;
  for(int t=0;t<45;t++)tick(&p,64);
  printf("ready state=%d frame=%d pos=%d,%d,%d block=%d,%d,%d\n",a->current,a->frame,a->x,a->y,a->z,b->x,b->y,b->z);fflush(stdout);assert(a->current==38);
  int x=b->x,z=b->z,seen=0,sound=0;
  for(int t=0;t<170;t++){tick(&p,65);seen|=a->current==36;for(unsigned j=0;j<p.sound_count;j++)sound|=p.sounds[j].id==63;}
  printf("push state=%d frame=%d block=%d,%d,%d active=%d\n",a->current,a->frame,b->x,b->y,b->z,w.items[0].active);fflush(stdout);
  assert(seen && sound && b->x==x+dx[q]*1024 && b->z==z+dz[q]*1024 && !w.items[0].active);
  for(int t=0;t<45;t++)tick(&p,0);assert(a->current==2 && !p.animation.weapon_status);
  break;
 }
 init(&p,&w,sine);assert(tomb_city_fixture(&p,&w,sine,0));
 TombActor *a=&p.lara.actor,*b=&w.items[0].actor;int original_z=b->z;
 for(int t=0;t<45;t++)tick(&p,64);assert(a->current==38);
 for(int t=0;t<200;t++)tick(&p,66);
 assert(b->z==original_z-1024 && !w.items[0].active);
 for(int t=0;t<45;t++)tick(&p,0);assert(a->current==2);
 printf("after pull Lara room=%d z=%d block room=%d z=%d\n",a->room,a->z,b->room,b->z);fflush(stdout);
 for(int t=0;t<45;t++)tick(&p,64);
 printf("second ready state=%d Lara room=%d block room=%d\n",a->current,a->room,b->room);fflush(stdout);
 assert(a->current==38);
 int crossed=0;
 for(int step=0;step<3;step++){
  printf("pull again %d permitted=%d\n",step,tomb_block_can_move(&w,a,0,0,1));fflush(stdout);
  if(!tomb_block_can_move(&w,a,0,0,1))break;
  for(int t=0;t<200;t++)tick(&p,66);for(int t=0;t<45;t++)tick(&p,0);
  printf("boundary Lara room=%d z=%d block room=%d z=%d\n",a->room,a->z,b->room,b->z);fflush(stdout);
  for(int t=0;t<45;t++)tick(&p,64);assert(a->current==38);
  if(a->room!=b->room){
   crossed=1;int z=b->z;assert(tomb_block_can_move(&w,a,0,0,0));
   for(int t=0;t<170;t++)tick(&p,65);for(int t=0;t<60;t++)tick(&p,0);
   assert(b->z==z+1024 && !w.items[0].active);
   for(int t=0;t<45;t++)tick(&p,64);for(int t=0;t<200;t++)tick(&p,66);
   for(int t=0;t<45;t++)tick(&p,0);assert(b->z==z);
   for(int t=0;t<45;t++)tick(&p,64);assert(a->current==38);
  }
 }
 assert(crossed);
 init(&p,&w,sine);assert(w.items[0].actor.z==original_z);
 assert(tomb_city_fixture(&p,&w,sine,0));for(int t=0;t<10;t++)tick(&p,64);
 for(int t=0;t<45;t++)tick(&p,0);assert(p.lara.actor.current==2 && w.items[0].actor.z==original_z);
 for(int id=30;id<=31;id++){
  init(&p,&w,sine);TombActor *a=&p.lara.actor,*b=&w.items[id].actor;
  a->x=b->x-300;a->y=b->y;a->z=b->z;a->room=b->room;a->yaw=b->yaw;a->current=a->goal=13;a->animation=108;a->frame=1736;a->flags=32;
  p.lara.water_status=p.water.status=1;p.lara.pitch=p.water.pitch=0;p.animation.move_angle=a->yaw;
  int old=b->current,seen=0;
  for(int t=0;t<220;t++){tick(&p,t<45?64:0);seen|=a->current==40;}
  printf("switch %d state %d -> %d flags=%u Lara=%d water=%d\n",id,old,b->current,b->flags,a->current,p.lara.water_status);fflush(stdout);
  assert(seen && b->current!=old && a->current==13);
  if(id==30)assert(w.doors[32].open);else assert(w.items[27].actor.current==1 && l->items[27].state==1);
  for(int t=0;t<15;t++)tick(&p,16);assert(a->current==17);
 }
 /* The actual two quest pickups are consumed once, then used at their own holes. */
 for(int variant=0;variant<2;variant++){
  assert(tomb_city_fixture(&p,&w,sine,3+variant));
  int slot=variant?0:4,id=variant?19:20,hole=variant?79:9,door=variant?78:8;
  for(int t=0;t<130;t++)tick(&p,64);
  assert(p.inventory.quest[slot]==1 && (w.items[id].actor.flags&6)==6 && p.inventory.pickups==1);
  for(int t=0;t<100;t++)tick(&p,64);assert(p.inventory.quest[slot]==1);
  TombActor *a=&p.lara.actor,*b=&w.items[hole].actor;
  int32_t local[3]={0,0,400},pos[3];tomb_rotate_vector(b->yaw,0,0,local,0,sine,pos);
  *a=(TombActor){b->x+pos[0],b->y,b->z+pos[2],2,2,11,185,0,0,b->yaw,b->room,32};p.animation.move_angle=a->yaw;
  tick(&p,0);tick(&p,64);assert(p.quest_request && !w.doors[door].open);
  p.quest_request=0;tick(&p,0);assert(p.inventory.quest[slot]==1 && a->current==2); /* cancel */
  p.inventory.chosen=variant?133:114;tick(&p,0);assert(a->current==2 && p.inventory.quest[slot]==1 && p.inventory.chosen==-1);
  assert(tomb_inventory_use(&p.inventory,variant?114:133,&p.lara.health)==2);tick(&p,0);
  assert(a->current==(variant?43:42) && !p.inventory.quest[slot] && !w.doors[door].open);
  int finished=0;
  for(int t=0;t<160;t++){tick(&p,0);if(a->current==2)finished=1;}
  printf("quest %d state=%d hole=%d flags=%d door=%d weapon=%d\n",variant,a->current,w.items[hole].object,w.items[hole].actor.flags,w.doors[door].open,p.animation.weapon_status);fflush(stdout);
  assert(finished && w.doors[door].open && (w.items[hole].actor.flags&6)==4 && !p.animation.weapon_status);
  if(variant)assert(w.items[hole].object==122);
  for(int t=0;t<45;t++)tick(&p,64);assert(!p.inventory.quest[slot]);
  init(&p,&w,sine);assert(!w.doors[door].open && w.items[hole].object==(variant?118:137));
 }
 /* Every City trapdoor changes both rendering state and floor/ceiling support. */
 for(int j=0;j<3;j++){
  const int ids[]={27,61,62};int id=ids[j];init(&p,&w,sine);TombObject *o=&w.items[id];TombItem *item=&l->items[id];
  int16_t floor=30000,ceiling=-30000;
  assert(tomb_item_height(item,item->x,item->y,item->z,0,&floor) && floor==item->y);
  assert(tomb_item_height(item,item->x,item->y+300,item->z,1,&ceiling) && ceiling==item->y+256);
  o->flags=0x3e00;o->active=1;
  for(int t=0;t<90;t++)assert(tomb_objects_tick(&w,&p.animation));assert(o->actor.current==1 && item->state==1);
  floor=30000;ceiling=-30000;
  assert(tomb_item_height(item,item->x,item->y,item->z,0,&floor) && floor==30000);
  assert(tomb_item_height(item,item->x,item->y+300,item->z,1,&ceiling) && ceiling==-30000);
  o->flags=0;for(int t=0;t<90;t++)assert(tomb_objects_tick(&w,&p.animation));assert(o->actor.current==0 && item->state==0);
 }
 init(&p,&w,sine);p.inventory.quest[4]=1;p.inventory.chosen=133;tick(&p,0);assert(p.inventory.chosen==-1 && p.inventory.quest[4]==1);
 /* Each real blade activates on its corridor trigger and can injure Lara. */
 for(int j=0;j<3;j++){
  init(&p,&w,sine);int id=56+j;TombObject *o=&w.items[id];
  p.lara.actor.x=25088+1024*j;p.lara.actor.y=-1024;p.lara.actor.z=29184;p.lara.actor.room=61;p.lara.actor.yaw=-16384;
  tick(&p,0);assert(o->active);
  int moving=0,sounds=0,damage=0;for(int t=0;t<180;t++){
   tick(&p,0);moving|=o->actor.current==2;sounds+=p.sound_count;
   if(o->actor.current==2){p.lara.actor.x=o->actor.x+512;p.lara.actor.z=o->actor.z;p.lara.actor.y=o->actor.y;}
   if(p.lara.health<1000){damage=1;break;}
  }
  printf("blade %d moving=%d damage=%d sound=%d health=%d\n",id,moving,damage,sounds,p.lara.health);fflush(stdout);
  assert(moving && damage && (p.lara.actor.flags&16));
  int blood=0;for(int k=0;k<256;k++)blood|=w.hazards->effects[k].active && w.hazards->effects[k].id==158;assert(blood);
  o->flags=0;for(int t=0;t<180;t++)assert(tomb_hazards_tick(&w,&p.animation,&p.lara.actor,&p.lara.health));assert(o->actor.current==0);
  init(&p,&w,sine);assert(!w.items[id].active && !w.enemies->items[id].touch);
 }
 init(&p,&w,sine);p.lara.actor.x=9728;p.lara.actor.y=-1024;p.lara.actor.z=29184;p.lara.actor.room=87;
 tick(&p,0);assert(w.progress->complete);TombActor ended=p.lara.actor;
 for(int t=0;t<30;t++)tick(&p,1);assert(p.lara.actor.x==ended.x && p.lara.actor.z==ended.z);
 tomb_objects_free(&w);tomb_visual_free(v);tomb_level_free(l);puts("PASS: City block, switches, quest pickups/insertion/doors, trapdoor surfaces/open/close/reset");return 0;
}
