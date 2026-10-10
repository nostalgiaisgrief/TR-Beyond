#ifndef TOMB_VISUAL_H
#define TOMB_VISUAL_H
#include "level.h"
/* Views borrow level file bytes; keep TombLevel alive and immutable until free. */
typedef struct TombMeshView {
    const unsigned char *vertices,*normals,*lights,*faces[4],*sprites;
    uint32_t vertex_count,normal_count,light_count,face_count[4],sprite_count,vertex_stride;
    int16_t centre[3];
    int32_t radius;
} TombMeshView;
typedef struct TombRoomPortals {
    const unsigned char *data;
    size_t count;
} TombRoomPortals;
typedef struct TombRoomLights {
    const unsigned char *data;
    size_t count;
    int16_t ambient;
} TombRoomLights;
typedef struct TombVisual {
    const TombLevel *level;
    TombMeshView *rooms,*meshes;
    size_t room_count,mesh_count;
    const unsigned char *tiles,*textures,*sprite_textures,*models,*trees,*frames,*animations,*palette;
    size_t tile_count,texture_count,sprite_texture_count,model_count,tree_words,frame_words,animation_count;
    TombRoomPortals *portals;
    TombRoomLights *lighting;
} TombVisual;
typedef struct TombModel {
    uint32_t id,tree_word,frame_offset;
    uint16_t mesh_count,mesh_start,animation;
} TombModel;
typedef struct TombPose {
    int16_t bounds[6],root[3];
    uint16_t count,rotation[64][3]; /* X,Y,Z angles in original 16-bit turn units */
} TombPose;
TOMB_EXPORT TombVisual *tomb_visual_load(const TombLevel *,char *error,size_t);
TOMB_EXPORT void tomb_visual_free(TombVisual *);
TOMB_EXPORT int tomb_visual_model(const TombVisual *,uint32_t id,TombModel *);
TOMB_EXPORT int tomb_visual_key(const TombVisual *,size_t animation,size_t key,TombPose *);
TOMB_EXPORT int tomb_visual_lara_meshes(const TombVisual *,int gym,uint16_t indices[15]);
TOMB_EXPORT int tomb_visual_bounds(const TombVisual *,const TombActor *,int16_t out[6]);
TOMB_EXPORT int tomb_visual_item_bounds(const TombVisual *,int object,const TombActor *,int16_t out[6]);
#endif
