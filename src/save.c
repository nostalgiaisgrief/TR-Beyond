/* Persist state, never callback addresses or allocation pointers. The payload
   uses this build's POD layouts; version/layout/level checks reject mismatches.
   All bytes and allocations are checked before committing a restore. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "save.h"
#include "enemies.h"
#include "hazards.h"
#include "progression.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define SAVE_LIMIT (16u*1024u*1024u)
typedef struct Header { char magic[8]; uint32_t version,layout,level,level_hash,bytes,checksum; } Header;
typedef struct Stream { unsigned char *data; size_t at,size; int mode,ok; } Stream;
static uint32_t hash(const void *data,size_t n){const unsigned char *p=data;uint32_t h=2166136261u;while(n--)h=(h^*p++)*16777619u;return h;}
static uint32_t layout(void){const size_t sizes[]={sizeof(TombPlaytest),sizeof(TombLaraStart),sizeof(TombMovement),sizeof(TombObject),sizeof(TombDoor),sizeof(TombCreature),sizeof(TombNavigation),sizeof(TombHazards),sizeof(TombProgress),sizeof(TombFollowCamera),sizeof(TombInventory)};return hash(sizes,sizeof sizes);}
static void chunk(Stream *s,void *p,size_t n){if(!s->ok || n>s->size-s->at){s->ok=0;return;}if(s->mode==0)memcpy(s->data+s->at,p,n);else if(s->mode==2)memcpy(p,s->data+s->at,n);s->at+=n;}
#define FIELD(v,f) chunk(s,&(v)->f,sizeof (v)->f)
static void state(Stream *s,TombPlaytest *p,TombObjects *w,TombFollowCamera *c,TombInventory *baseline){
 FIELD(p,ledge);FIELD(p,static_hit);FIELD(p,lara);FIELD(p,movement);FIELD(p,terrain);
 FIELD(p,animation.move_angle);FIELD(p,animation.fall_override);FIELD(p,animation.weapon_status);
 FIELD(p,collision.walk.move_angle);FIELD(p,collision.front_floor);FIELD(p,collision.front_type);FIELD(p,collision.lean);
 FIELD(p,air.move_angle);chunk(s,&p->water,offsetof(TombWater,query));FIELD(p,gym);
 FIELD(p,slide.move_angle);FIELD(p,slide.last_angle);FIELD(p,slide.tilt_x);FIELD(p,slide.tilt_z);
 FIELD(p,movement_only);FIELD(p,requested_camera_mode);FIELD(p,requested_camera_elevation);FIELD(p,dead_ticks);
 FIELD(p,door_hit_ticks);FIELD(p,door_hit_direction);FIELD(p,blocked);
 FIELD(p,deferred_cd_track);FIELD(p,deferred_camera);FIELD(p,deferred_camera_flags);FIELD(p,requested_camera_angle);
 FIELD(p,camera_request);FIELD(p,pistols);FIELD(p,last_input);FIELD(p,inventory);FIELD(p,hud);FIELD(p,quest_request);FIELD(p,quest_latch);
 chunk(s,c,sizeof *c);chunk(s,baseline,sizeof *baseline);
 FIELD(w,deferred_actions);FIELD(w,camera);FIELD(w,camera_once);FIELD(w,last_target);
 chunk(s,w->items,w->count*sizeof *w->items);chunk(s,w->doors,w->count*sizeof *w->doors);
 chunk(s,w->hazards,sizeof *w->hazards);chunk(s,w->progress,sizeof *w->progress);
 TombEnemies *e=w->enemies;FIELD(e,slots);FIELD(e,head);FIELD(e,random);FIELD(e,camera);
 chunk(s,e->items,w->count*sizeof *e->items);chunk(s,e->next,w->count*sizeof *e->next);
 chunk(s,e->room_head,w->level->room_count*sizeof *e->room_head);chunk(s,e->room_next,w->count*sizeof *e->room_next);chunk(s,e->room_id,w->count*sizeof *e->room_id);
 for(int i=0;i<8;i++){
  TombNavigation *n=e->navigation+i;uint32_t present=n->nodes!=NULL;
  if(s->mode && s->ok && s->size-s->at>=4)memcpy(&present,s->data+s->at,4);
  chunk(s,&present,4);if(present>1){s->ok=0;return;}
  chunk(s,&n->head,sizeof *n - offsetof(TombNavigation,head));
  if(present){if(s->mode==2 && !n->nodes){s->ok=0;return;}chunk(s,n->nodes,(w->level->box_count+1)*sizeof *n->nodes);}
  else if(s->mode==2){free(n->nodes);n->nodes=NULL;}
 }
 for(size_t i=0;i<w->level->room_count;i++){TombRoom *r=w->level->rooms+i;chunk(s,r->sectors,(size_t)r->nx*r->nz*sizeof *r->sectors);}
 chunk(s,w->level->boxes,w->level->box_count*sizeof *w->level->boxes);
 chunk(s,w->level->items,w->level->item_count*sizeof *w->level->items);
}
#undef FIELD
static unsigned char *read_file(const char *path,Header *h){
 FILE *f=fopen(path,"rb");if(!f)return NULL;
 if(fread(h,sizeof *h,1,f)!=1 || memcmp(h->magic,"TOMBSV1",8) || h->version!=1 || h->layout!=layout() || h->level<1 || h->level>15 || !h->bytes || h->bytes>SAVE_LIMIT){fclose(f);return NULL;}
 unsigned char *data=malloc(h->bytes);if(!data){fclose(f);return NULL;}
 int ok=fread(data,1,h->bytes,f)==h->bytes && fgetc(f)==EOF && hash(data,h->bytes)==h->checksum;fclose(f);if(!ok){free(data);return NULL;}return data;
}
int tomb_save_level(const char *path){Header h;unsigned char *data=read_file(path,&h);if(!data)return -1;free(data);return (int)h.level;}
int tomb_save_write(const char *path,int number,const TombPlaytest *p,const TombObjects *w,const TombFollowCamera *c,const TombInventory *baseline){
 if(number<1 || number>15 || !p || p->lara.health<=0 || !w || w->progress->complete)return 0;
 unsigned char *data=malloc(SAVE_LIMIT);if(!data)return 0;
 Stream s={data,0,SAVE_LIMIT,0,1};state(&s,(TombPlaytest *)p,(TombObjects *)w,(TombFollowCamera *)c,(TombInventory *)baseline);
 Header h={{'T','O','M','B','S','V','1',0},1,layout(),(uint32_t)number,hash(w->level->file_data,w->level->file_size),(uint32_t)s.at,hash(data,s.at)};
 char temp[MAX_PATH];if(snprintf(temp,sizeof temp,"%s.tmp",path)>=(int)sizeof temp){free(data);return 0;}
 FILE *f=s.ok?fopen(temp,"wb"):NULL;int ok=f && fwrite(&h,sizeof h,1,f)==1 && fwrite(data,1,s.at,f)==s.at;
 if(f && fclose(f))ok=0;free(data);if(ok)ok=MoveFileExA(temp,path,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;if(!ok)DeleteFileA(temp);return ok;
}
int tomb_save_read(const char *path,int number,TombPlaytest *p,TombObjects *w,TombFollowCamera *c,TombInventory *baseline){
 Header h;unsigned char *data=read_file(path,&h);if(!data)return 0;
 if(h.level!=(uint32_t)number || h.level_hash!=hash(w->level->file_data,w->level->file_size)){free(data);return 0;}
 Stream s={data,0,h.bytes,1,1};state(&s,p,w,c,baseline);
 if(!s.ok || s.at!=s.size){free(data);return 0;}
 TombNavNode *fresh[8]={0};
 for(int i=0;i<8;i++)if(!w->enemies->navigation[i].nodes){fresh[i]=calloc(w->level->box_count+1,sizeof *fresh[i]);if(!fresh[i]){for(int j=0;j<8;j++)free(fresh[j]);free(data);return 0;}}
 for(int i=0;i<8;i++)if(fresh[i])w->enemies->navigation[i].nodes=fresh[i];
 s.at=0;s.mode=2;state(&s,p,w,c,baseline);free(data);
 p->sound_count=0;p->status="Game loaded";return s.ok;
}
