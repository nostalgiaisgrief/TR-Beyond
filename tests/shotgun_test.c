#include "playtest.h"
#include "combat.h"
#include "save.h"
#include "enemies.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
static void gun(TombPlaytest *p,unsigned input){p->sound_count=0;assert(tomb_combat_tick(p,input));}
int main(int argc,char **argv){
 assert(argc==3 || argc==5);char error[256];int16_t sine[1025];FILE *f=fopen(argv[2],"rb");assert(f && fread(sine,sizeof sine,1,f)==1);fclose(f);
 TombLevel *l=tomb_level_load(argv[1],error,sizeof error);assert(l);TombVisual *v=tomb_visual_load(l,error,sizeof error);assert(v);
 TombObjects w;assert(tomb_objects_init(&w,l,v));TombPlaytest p;assert(tomb_playtest_init(&p,l,sine,v));p.objects=&w;p.movement_only=1;
 int pickup=-1;for(size_t id=0;id<w.count;id++)if(w.items[id].object==85)pickup=(int)id;assert(pickup>=0);
 TombActor *a=&p.lara.actor,*item=&w.items[pickup].actor;
 a->x=item->x;a->y=item->y;a->z=item->z-100;a->room=item->room;a->yaw=0;
 for(int t=0;t<90;t++)assert(tomb_playtest_tick(&p,64));
 assert(p.inventory.counts[1]==1 && p.inventory.ammo[1]==12 && (w.items[pickup].actor.flags&6)==6);
 p.requested_weapon=4;gun(&p,0);assert(p.weapon_type==4 && p.pistols.status==2);
 for(int t=0;t<40;t++)gun(&p,0);assert(p.pistols.status==4 && p.pistols.drawn==3);
 TombModel model;assert(tomb_visual_model(v,2,&model) && model.mesh_count==15);
 for(int frame=0;frame<127;frame++){int an=frame<13?164:frame<47?165:frame<80?166:frame<114?167:168;TombPose pose;assert(tomb_visual_key(v,(size_t)an,(size_t)(frame-l->animations[an].first_frame),&pose));assert(pose.count==15);}
 int firing=0,pump=0;
 for(int t=0;t<80 && p.pistols.shots==0;t++){gun(&p,64);for(unsigned j=0;j<p.sound_count;j++)firing+=p.sounds[j].id==3;}
 assert(p.pistols.shots==6 && p.inventory.ammo[1]==6 && firing==1);
 TombFollowCamera cam={0};TombInventory baseline=p.inventory;
 assert(tomb_save_write("build/shotgun-save.tsv",3,&p,&w,&cam,&baseline));
 for(int t=0;t<45;t++){gun(&p,0);for(unsigned j=0;j<p.sound_count;j++)pump+=p.sounds[j].id==9;}assert(pump==1);
 int end_frame=p.pistols.left.frame;
 assert(tomb_save_read("build/shotgun-save.tsv",3,&p,&w,&cam,&baseline));assert(p.weapon_type==4 && p.requested_weapon==4 && p.inventory.ammo[1]==6);
 for(int t=0;t<45;t++)gun(&p,0);assert(p.pistols.left.frame==end_frame);
 p.requested_weapon=1;for(int t=0;t<170;t++)gun(&p,0);assert(p.weapon_type==1 && p.pistols.status==4);
 p.requested_weapon=4;for(int t=0;t<170;t++)gun(&p,0);assert(p.weapon_type==4 && p.pistols.status==4);
 for(int t=0;t<160;t++)gun(&p,64);assert(p.inventory.ammo[1]==0 && p.requested_weapon==1);
 for(int t=0;t<170;t++)gun(&p,0);assert(p.weapon_type==1 && p.pistols.status==4);
 p.inventory.ammo[1]=12;p.requested_weapon=4;for(int t=0;t<170;t++)gun(&p,0);
 p.lara.water_status=1;for(int t=0;t<170;t++)gun(&p,0);assert(p.pistols.status==0 && !p.pistols.drawn);
 gun(&p,32);assert(p.pistols.status==0);p.lara.water_status=0;
 gun(&p,32);for(int t=0;t<40;t++)gun(&p,0);p.lara.health=0;gun(&p,64);assert(p.pistols.status==0);
 int enemy=tomb_combat_fixture(&p,&w,sine,7);assert(enemy>=0);
 tomb_inventory_add(&p.inventory,85);p.inventory.ammo[1]=120;p.requested_weapon=4;
 for(int t=0;t<40;t++)gun(&p,0);
 for(int t=0;t<240 && !p.pistols.kills;t++)gun(&p,64);
 assert(p.pistols.hits>0 && p.pistols.kills==1 && w.enemies->items[enemy].health<=0);
 assert(w.enemies->items[enemy].health==6-(int)p.pistols.hits*4);
 tomb_objects_free(&w);tomb_visual_free(v);tomb_level_free(l);
 if(argc==5){
  l=tomb_level_load(argv[3],error,sizeof error);assert(l);v=tomb_visual_load(l,error,sizeof error);assert(v);
  assert(tomb_objects_init(&w,l,v));assert(tomb_playtest_init(&p,l,sine,v));p.objects=&w;
  assert(tomb_save_level(argv[4])==2);assert(tomb_save_read(argv[4],2,&p,&w,&cam,&baseline));
  assert(p.weapon_type==1 && p.requested_weapon==1);
  tomb_objects_free(&w);tomb_visual_free(v);tomb_level_free(l);puts("PASS: legacy version-1 save loads with pistol defaults");
 }
 puts("PASS: Lost Valley shotgun pickup, 127 poses, draw, six-pellet ammo, fire/pump sounds, save/replay, weapon switching, empty fallback, water/death");return 0;
}
