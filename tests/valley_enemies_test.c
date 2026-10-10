#include "playtest.h"
#include "combat.h"
#include "enemies.h"
#include "save.h"
#include "object_contact.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void tick(TombPlaytest *p,unsigned input){if(!tomb_playtest_tick(p,input)){fprintf(stderr,"blocked: %s state=%d\n",p->status,p->lara.actor.current);assert(0);}}
static void init(TombPlaytest *p,TombObjects *w,const int16_t *s){tomb_objects_reset(w);assert(tomb_playtest_init(p,w->level,s,w->visual));p->objects=w;p->movement_only=1;}
int main(int argc,char **argv){
 assert(argc==3);char error[256];int16_t sine[1025];FILE *f=fopen(argv[2],"rb");assert(f && fread(sine,sizeof sine,1,f)==1);fclose(f);
 TombLevel *l=tomb_level_load(argv[1],error,sizeof error);assert(l);TombVisual *v=tomb_visual_load(l,error,sizeof error);assert(v);
 TombObjects w;assert(tomb_objects_init(&w,l,v));TombPlaytest p;int counts[20]={0};
 for(size_t id=0;id<w.count;id++)if(tomb_enemy_object(w.items[id].object)){
  init(&p,&w,sine);TombObject *o=w.items+id;TombCreature *c=w.enemies->items+id;TombModel m;assert(tomb_visual_model(v,o->object,&m));++counts[o->object];
  assert(o->actor.animation==m.animation && c->health==(o->object==7?6:o->object==18?100:20));
  if(o->object==7)assert(o->actor.frame==96);
  tomb_enemies_trigger(&w,id,0,0x3e00);assert(o->active);
  for(int t=0;t<180;t++){p.sound_count=0;assert(tomb_enemies_tick(&w,&p.animation,&p.lara));assert(!p.blocked);TombPose pose;assert(tomb_object_pose(v,&o->actor,&pose));}
  c->health=0;
  for(int t=0;t<600 && o->active;t++){p.sound_count=0;assert(tomb_enemies_tick(&w,&p.animation,&p.lara));assert(!p.blocked);if(o->object==7)assert(o->actor.animation>=m.animation+20 && o->actor.animation<=m.animation+22);}
  assert(!o->active && c->health==-16384);TombActor corpse=o->actor;
  for(int t=0;t<20;t++){p.sound_count=0;assert(tomb_enemies_tick(&w,&p.animation,&p.lara));}
  assert(!memcmp(&corpse,&o->actor,sizeof corpse));
 }
 assert(counts[7]==6 && counts[18]==1 && counts[19]==6);
 for(int species=7;species<=19;species++){if(!tomb_enemy_object(species) || species==8 || species==9)continue;
  for(int shotgun=0;shotgun<2;shotgun++){
   int id=tomb_combat_fixture(&p,&w,sine,species);assert(id>=0);
   if(shotgun){tomb_inventory_add(&p.inventory,85);p.inventory.ammo[1]=600;p.requested_weapon=4;}
   else assert(tomb_combat_tick(&p,32));
   for(int t=0;t<1800 && w.enemies->items[id].health>0;t++){p.sound_count=0;assert(tomb_combat_tick(&p,64));}
   printf("species=%d shotgun=%d hits=%u health=%d\n",species,shotgun,p.pistols.hits,w.enemies->items[id].health);fflush(stdout);
   assert(p.pistols.hits && p.pistols.kills==1 && w.enemies->items[id].health<=0);
  }
  int id=tomb_combat_fixture(&p,&w,sine,species);assert(id>=0);
  for(int t=0;t<1800 && p.lara.health==1000;t++)tick(&p,0);
  printf("species=%d attack health=%d\n",species,p.lara.health);fflush(stdout);assert(p.lara.health<1000);
 }
 int rex=tomb_combat_fixture(&p,&w,sine,18);assert(rex>=0);TombObject *o=w.items+rex;TombModel m;assert(tomb_visual_model(v,18,&m));
 o->actor.animation=(int16_t)(m.animation+6);o->actor.frame=l->animations[o->actor.animation].first_frame;o->actor.current=o->actor.goal=7;w.enemies->items[rex].touch=0x3000;
 TombFollowCamera cam={0};TombInventory baseline=p.inventory;
 assert(tomb_save_write("build/valley-enemies.tsv",3,&p,&w,&cam,&baseline));
 tick(&p,0);assert(p.lara.health==-1 && p.lara.actor.current==46 && p.lara.actor.goal==46 && p.lara.actor.room==o->actor.room);
 assert(tomb_visual_model(v,5,&m));assert(p.lara.actor.animation==m.animation+1 && !p.pistols.drawn);
 for(int t=0;t<90;t++)tick(&p,0);TombLaraStart expected=p.lara;TombActor expected_rex=o->actor;
 assert(tomb_save_read("build/valley-enemies.tsv",3,&p,&w,&cam,&baseline));for(int t=0;t<91;t++)tick(&p,0);
 assert(!memcmp(&p.lara,&expected,sizeof expected) && !memcmp(&o->actor,&expected_rex,sizeof expected_rex));
 assert(p.lara.actor.current==46 && p.camera_request.angle==30940 && p.camera_request.elevation==-4550);
 tomb_objects_free(&w);tomb_visual_free(v);tomb_level_free(l);
 puts("PASS: all 13 Valley enemies initialize, move and die; both weapons hit all species; attacks, fatal bite and save continuation");return 0;
}
