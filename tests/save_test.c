#include "save.h"
#include "city.h"
#include "combat.h"
#include "enemies.h"
#include "hazards.h"
#include "progression.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int same(const char *a,const char *b){FILE *x=fopen(a,"rb"),*y=fopen(b,"rb");assert(x && y);int c,d;do{c=fgetc(x);d=fgetc(y);if(c!=d){fclose(x);fclose(y);return 0;}}while(c!=EOF);fclose(x);fclose(y);return 1;}
static void ticks(TombPlaytest *p,int count,unsigned input){for(int t=0;t<count;t++)assert(tomb_playtest_tick(p,input));}
int main(int argc,char **argv){
 assert(argc==4);char err[256];int16_t sine[1025];FILE *f=fopen(argv[3],"rb");assert(f && fread(sine,sizeof sine,1,f)==1);fclose(f);
 for(int n=1;n<=2;n++){
  TombLevel *l=tomb_level_load(argv[n],err,sizeof err);assert(l);TombVisual *v=tomb_visual_load(l,err,sizeof err);assert(v);TombObjects w;assert(tomb_objects_init(&w,l,v));TombPlaytest p;
  for(int scenario=0;scenario<(n==1?4:8);scenario++){
   tomb_objects_reset(&w);assert(tomb_playtest_init(&p,l,sine,v));p.objects=&w;p.movement_only=1;TombInventory baseline=p.inventory;TombFollowCamera cam={0};unsigned input=0;
   if(n==1 && scenario>0){assert(tomb_combat_fixture(&p,&w,sine,scenario+6));ticks(&p,12,32);input=64;}
   if(n==2){assert(tomb_city_fixture(&p,&w,sine,scenario));if(scenario==0)ticks(&p,45,64);input=scenario==0?65:scenario==1 || scenario==2?64:0;ticks(&p,scenario==0?60:30,input);}
   p.inventory.quest[4]=1;p.inventory.counts[9]=2;p.inventory.ticks=712;p.inventory.pickups=4;w.progress->secrets=3;w.camera_once[2]=8;
   assert(tomb_save_write("build/save-test.tsv",n,&p,&w,&cam,&baseline));assert(tomb_save_level("build/save-test.tsv")==n);
   assert(tomb_save_read("build/save-test.tsv",n,&p,&w,&cam,&baseline));
   assert(tomb_save_write("build/save-roundtrip.tsv",n,&p,&w,&cam,&baseline));assert(same("build/save-test.tsv","build/save-roundtrip.tsv"));
   ticks(&p,90,input);if(p.lara.health<=0)p.lara.health=400;
   assert(tomb_save_write("build/save-expected.tsv",n,&p,&w,&cam,&baseline));
   tomb_objects_reset(&w);assert(tomb_playtest_init(&p,l,sine,v));p.objects=&w;p.movement_only=1;
   assert(tomb_save_read("build/save-test.tsv",n,&p,&w,&cam,&baseline));assert(p.inventory.ticks==712 && w.progress->secrets==3 && w.camera_once[2]==8);
   ticks(&p,90,input);if(p.lara.health<=0)p.lara.health=400;
   assert(tomb_save_write("build/save-actual.tsv",n,&p,&w,&cam,&baseline));assert(same("build/save-expected.tsv","build/save-actual.tsv"));
   TombLaraStart before=p.lara;
   assert(!tomb_save_read("build/save-test.tsv",3-n,&p,&w,&cam,&baseline));assert(!memcmp(&before,&p.lara,sizeof before));
   f=fopen("build/save-test.tsv","r+b");assert(f);assert(!fseek(f,64,SEEK_SET));int byte=fgetc(f);assert(!fseek(f,64,SEEK_SET));fputc(byte^128,f);fclose(f);
   assert(tomb_save_level("build/save-test.tsv")==-1);assert(!tomb_save_read("build/save-test.tsv",n,&p,&w,&cam,&baseline));assert(!memcmp(&before,&p.lara,sizeof before));
   printf("PASS save level=%d scenario=%d: exact roundtrip, deterministic continuation, wrong-level and corruption rejection\n",n,scenario);
  }
  tomb_objects_free(&w);tomb_visual_free(v);tomb_level_free(l);
 }
 return 0;
}
