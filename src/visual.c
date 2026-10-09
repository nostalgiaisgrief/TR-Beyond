#include "visual.h"
#include "fixed.h"
#include <stdlib.h>
#include <stdio.h>

typedef struct Read { const unsigned char *p; size_t n,at; int bad; } Read;
static uint16_t u16(const unsigned char *p) { return (uint16_t)(p[0]|(uint16_t)p[1]<<8); }
static uint32_t u32(const unsigned char *p) { return u16(p)|(uint32_t)u16(p+2)<<16; }
static const unsigned char *take(Read *r,size_t n,size_t size)
{
    if(r->bad || !size || n>(r->n-r->at)/size) { r->bad=1; return NULL; }
    const unsigned char *p=r->p+r->at; r->at+=n*size; return p;
}
static uint32_t count(Read *r,int width)
{ const unsigned char *p=take(r,1,(size_t)width); return p?(width==2?u16(p):u32(p)):0; }
static int mesh(Read *r,TombMeshView *m,int room)
{
    if(!room) {
        const unsigned char *p=take(r,1,10); if(!p) return 0;
        for(int i=0;i<3;++i) m->centre[i]=tomb_word(u16(p+i*2));
        m->radius=tomb_long(u32(p+6));
    }
    m->vertex_count=count(r,2); if(m->vertex_count>32767) return 0;
    m->vertex_stride=room?8:6; m->vertices=take(r,m->vertex_count,m->vertex_stride);
    if(!room) {
        int32_t n=tomb_word(count(r,2));
        if(n>0) { m->normal_count=(uint32_t)n; m->normals=take(r,m->normal_count,6); }
        else { m->light_count=(uint32_t)-n; m->lights=take(r,m->light_count,2); }
    }
    for(int group=0;group<(room?2:4);++group) {
        m->face_count[group]=count(r,2); if(m->face_count[group]>32767) return 0;
        m->faces[group]=take(r,m->face_count[group],(group&1)?8:10);
    }
    if(room) { m->sprite_count=count(r,2); m->sprites=take(r,m->sprite_count,4); }
    return !r->bad;
}
static int validate_mesh(const TombVisual *v,const TombMeshView *m)
{
    for(int group=0;group<4;++group) for(size_t i=0;i<m->face_count[group];++i) {
        size_t vertices=(group&1)?3:4; const unsigned char *p=m->faces[group]+i*(vertices+1)*2;
        for(size_t j=0;j<vertices;++j) if(u16(p+2*j)>=m->vertex_count) return 0;
        if(group<2 && (u16(p+2*vertices)&32767)>=v->texture_count) return 0;
    }
    for(size_t i=0;i<m->sprite_count;++i) {
        if(u16(m->sprites+i*4)>=m->vertex_count || u16(m->sprites+i*4+2)>=v->sprite_texture_count) return 0;
    }
    return 1;
}
void tomb_visual_free(TombVisual *v)
{ if(v) { free(v->portals); free(v->rooms); free(v->meshes); free(v); } }
int tomb_visual_model(const TombVisual *v,uint32_t id,TombModel *out)
{
    if(!v || !out) return 0;
    for(size_t i=0;i<v->model_count;++i) {
        const unsigned char *p=v->models+i*18;
        if(u32(p)==id) { *out=(TombModel){id,u32(p+8),u32(p+12),u16(p+4),u16(p+6),u16(p+16)}; return 1; }
    }
    return 0;
}
int tomb_visual_key(const TombVisual *v,size_t animation,size_t key,TombPose *out)
{
    if(!v || !out || animation>=v->animation_count) return 0;
    const unsigned char *a=v->animations+animation*32;
    size_t off=u32(a); int rate=a[4],first=tomb_word(u16(a+16)),last=tomb_word(u16(a+18));
    if(!rate || last<first || key>(size_t)((last-first+rate-1)/rate) || (off&1) || off>v->frame_words*2) return 0;
    if(v->frame_words*2-off<20) return 0;
    size_t n=u16(v->frames+off+18),stride=20+4*n;
    if(n>64 || key>(v->frame_words*2-off)/stride) return 0;
    off+=key*stride;
    if(v->frame_words*2-off<stride || u16(v->frames+off+18)!=n) return 0;
    const unsigned char *p=v->frames+off; TombPose pose={0}; pose.count=(uint16_t)n;
    for(int i=0;i<6;++i) pose.bounds[i]=tomb_word(u16(p+2*i));
    for(int i=0;i<3;++i) pose.root[i]=tomb_word(u16(p+12+2*i));
    for(size_t i=0;i<n;++i) {
        uint32_t angles=u32(p+20+4*i);
        pose.rotation[i][0]=(uint16_t)(((angles>>20)&1023)<<6);
        pose.rotation[i][1]=(uint16_t)(((angles>>10)&1023)<<6);
        pose.rotation[i][2]=(uint16_t)((angles&1023)<<6);
    }
    *out=pose; return 1;
}
int tomb_visual_lara_meshes(const TombVisual *v,int gym,uint16_t indices[15])
{
    TombModel m;
    if(!indices || !tomb_visual_model(v,gym?5:0,&m) || m.mesh_count!=15 || (size_t)m.mesh_start+15>v->mesh_count) return 0;
    uint16_t selected[15];
    for(int i=0;i<15;++i) selected[i]=(uint16_t)(m.mesh_start+i);
    if(gym) {
        TombModel standard;
        if(!tomb_visual_model(v,0,&standard) || standard.mesh_count!=15 || (size_t)standard.mesh_start+15>v->mesh_count) return 0;
        selected[14]=(uint16_t)(standard.mesh_start+14);
    }
    for(int i=0;i<15;++i) indices[i]=selected[i];
    return 1;
}
TombVisual *tomb_visual_load(const TombLevel *l,char *error,size_t cap)
{
    TombVisual *v=NULL; const char *why="invalid visual asset data";
    if(error && cap) error[0]=0;
    if(!l || !l->file_data) goto fail;
    v=calloc(1,sizeof *v); if(!v) goto fail; v->level=l;
    Read r={l->file_data,l->file_size,0,0};
    if(count(&r,4)!=32) goto fail;
    v->tile_count=count(&r,4); v->tiles=take(&r,v->tile_count,65536); take(&r,1,4);
    v->room_count=count(&r,2); if(r.bad || v->room_count!=l->room_count) goto fail;
    v->rooms=calloc(v->room_count?v->room_count:1,sizeof *v->rooms); if(!v->rooms) goto fail;
    v->portals=calloc(v->room_count?v->room_count:1,sizeof *v->portals);if(!v->portals)goto fail;
    for(size_t i=0;i<v->room_count;++i) {
        take(&r,1,16); size_t words=count(&r,4); const unsigned char *p=take(&r,words,2); if(!p) goto fail;
        Read data={p,words*2,0,0}; if(!mesh(&data,v->rooms+i,1) || data.at!=data.n) goto fail;
        size_t n=count(&r,2); v->portals[i].count=n;v->portals[i].data=take(&r,n,32);
        if(r.bad)goto fail;
        for(size_t j=0;j<n;j++)if(u16(v->portals[i].data+j*32)>=v->room_count)goto fail;
        size_t nz=count(&r,2),nx=count(&r,2); take(&r,nz*nx,8); take(&r,1,2);
        n=count(&r,2); take(&r,n,18); n=count(&r,2); take(&r,n,18); take(&r,1,4);
    }
    size_t n=count(&r,4); take(&r,n,2);
    size_t mesh_words=count(&r,4); const unsigned char *mesh_data=take(&r,mesh_words,2);
    v->mesh_count=count(&r,4); const unsigned char *pointers=take(&r,v->mesh_count,4); if(!pointers) goto fail;
    v->meshes=calloc(v->mesh_count?v->mesh_count:1,sizeof *v->meshes); if(!v->meshes) goto fail;
    for(size_t i=0;i<v->mesh_count;++i) {
        size_t off=u32(pointers+4*i),end=mesh_words*2;
        if((off&1) || off>=end) goto fail;
        for(size_t j=0;j<v->mesh_count;++j) { size_t next=u32(pointers+4*j); if(next>off && next<end) end=next; }
        Read data={mesh_data+off,end-off,0,0}; if(!mesh(&data,v->meshes+i,0)) goto fail;
    }
    v->animation_count=count(&r,4); v->animations=take(&r,v->animation_count,32);
    n=count(&r,4); take(&r,n,6); n=count(&r,4); take(&r,n,8); n=count(&r,4); take(&r,n,2);
    v->tree_words=count(&r,4); v->trees=take(&r,v->tree_words,4);
    v->frame_words=count(&r,4); v->frames=take(&r,v->frame_words,2);
    v->model_count=count(&r,4); v->models=take(&r,v->model_count,18);
    n=count(&r,4); take(&r,n,32);
    v->texture_count=count(&r,4); v->textures=take(&r,v->texture_count,20);
    v->sprite_texture_count=count(&r,4); v->sprite_textures=take(&r,v->sprite_texture_count,16);
    if(r.bad || l->item_parsed_bytes>l->file_size) goto fail;
    r.at=l->item_parsed_bytes; take(&r,1,8192); v->palette=take(&r,256,3); if(r.bad) goto fail;
    for(size_t i=0;i<v->texture_count;++i) if((u16(v->textures+i*20+2)&32767)>=v->tile_count) goto fail;
    for(size_t i=0;i<v->sprite_texture_count;++i) if(u16(v->sprite_textures+i*16)>=v->tile_count) goto fail;
    for(size_t i=0;i<l->static_def_count;++i) if(l->static_defs[i].mesh>=v->mesh_count) goto fail;
    for(size_t i=0;i<v->room_count;++i) if(!validate_mesh(v,v->rooms+i)) goto fail;
    for(size_t i=0;i<v->mesh_count;++i) if(!validate_mesh(v,v->meshes+i)) goto fail;
    for(size_t i=0;i<v->model_count;++i) {
        const unsigned char *p=v->models+i*18;
        size_t meshes=u16(p+4),start=u16(p+6),tree=u32(p+8);
        if(start>v->mesh_count || meshes>v->mesh_count-start || tree>v->tree_words ||
           (meshes && meshes-1>(v->tree_words-tree)/4)) goto fail;
        /* Unanimated models may point to the end of the frame block (Lost Valley). */
        if((u16(p+16)!=65535?u32(p+12)>=v->frame_words*2:u32(p+12)>v->frame_words*2) || (u32(p+12)&1)) goto fail;
    }
    for(size_t i=0;i<v->animation_count;++i) {
        const unsigned char *p=v->animations+i*32; int rate=p[4];
        int first=tomb_word(u16(p+16)),last=tomb_word(u16(p+18)); if(!rate || last<first) goto fail;
        size_t keys=(size_t)((last-first+rate-1)/rate)+1;
        for(size_t k=0;k<keys;++k) { TombPose pose; if(!tomb_visual_key(v,i,k,&pose)) goto fail; }
    }
    return v;
fail:
    tomb_visual_free(v); if(error && cap) snprintf(error,cap,"%s",why); return NULL;
}

/* Original bounds interpolation 0x1d380 / 0x1d444, for Lara's model. */
int tomb_visual_bounds(const TombVisual *v,const TombActor *actor,int16_t out[6]) {
    return tomb_visual_item_bounds(v,0,actor,out);
}
int tomb_visual_item_bounds(const TombVisual *v,int object,const TombActor *actor,int16_t out[6]) {
    if(!v || !actor || !out || actor->animation<0 || (size_t)actor->animation>=v->animation_count) return 0;
    TombModel model; if(!tomb_visual_model(v,(uint32_t)object,&model)) return 0;
    const unsigned char *a=v->animations+(size_t)actor->animation*32;
    int rate=tomb_word(u16(a+4)),first=tomb_word(u16(a+16)),last=tomb_word(u16(a+18));
    if(rate<=0 || actor->frame<first || actor->frame>last) return 0;
    int frame=actor->frame-first,key=frame/rate,fraction=frame%rate,denominator=rate;
    size_t stride=20+(size_t)model.mesh_count*4,base=u32(a),size=v->frame_words*2;
    if(base>size || (size_t)key>(size-base)/stride) return 0;
    base+=(size_t)key*stride;
    if(size-base<12 || (fraction && (size-base<stride || size-base-stride<12))) return 0;
    /* Preserve the original comparison with absolute last_frame. */
    if(fraction && (key+1)*rate>last) denominator=last-key*rate;
    if(denominator<=0) return 0;
    int16_t result[6];
    for(int i=0;i<6;i++) {
        int start=tomb_word(u16(v->frames+base+2*i));
        int end=fraction?tomb_word(u16(v->frames+base+stride+2*i)):start;
        result[i]=tomb_word(start+(end-start)*fraction/denominator);
    }
    for(int i=0;i<6;i++) out[i]=result[i];
    return 1;
}
