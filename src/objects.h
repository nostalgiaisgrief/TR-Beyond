#ifndef TOMB_OBJECTS_H
#define TOMB_OBJECTS_H
#include "visual.h"
typedef struct TombObject {
    TombActor actor;
    uint16_t flags;
    int16_t timer, object;
    int active;
} TombObject;
typedef struct TombDoorPart {
    TombSectorRef ref;
    TombSector saved;
    int box;
} TombDoorPart;
typedef struct TombDoor {
    TombDoorPart parts[4];
    unsigned count;
    int open;
} TombDoor;
typedef struct TombObjects {
    TombLevel *level;
    const TombVisual *visual;
    TombObject *items;
    TombDoor *doors;
    uint16_t *box_overlap;
    size_t count;
    unsigned deferred_actions;
    struct { int index,last,target,timer,speed,active; } camera;
    uint8_t camera_once[128]; /* Camera action IDs are ten bits. */
    struct TombHazards *hazards;
    struct TombEnemies *enemies;
    struct TombProgress *progress;
    int last_target;
} TombObjects;
TOMB_EXPORT int tomb_object_supported(int);
TOMB_EXPORT int tomb_trigger_active(TombObject *);
TOMB_EXPORT void tomb_object_trigger(TombObject *,int type,uint16_t flags);
TOMB_EXPORT int tomb_switch_trigger(TombObject *,int16_t timer);
/* -1 leaves sector data alone, otherwise 0 closes and 1 opens it. */
TOMB_EXPORT void tomb_trapdoor_control(TombObject *);
TOMB_EXPORT int tomb_key_trigger(TombObject *,int);
TOMB_EXPORT int tomb_door_control(TombObject *);
TOMB_EXPORT int tomb_object_animate(TombObject *,TombAnimContext *);
TOMB_EXPORT int tomb_object_animate_required(TombObject *,TombAnimContext *,int16_t *);
TOMB_EXPORT int tomb_switch_bounds(const TombActor *,const TombActor *,int16_t pitch,int16_t roll);
TOMB_EXPORT int tomb_objects_init(TombObjects *,TombLevel *,const TombVisual *);
TOMB_EXPORT void tomb_objects_reset(TombObjects *);
TOMB_EXPORT void tomb_objects_free(TombObjects *);
TOMB_EXPORT int tomb_objects_tick(TombObjects *,TombAnimContext *);
TOMB_EXPORT void tomb_objects_camera_begin(TombObjects *);
int tomb_objects_interact(TombObjects *,TombActor *,TombAnimContext *,uint32_t input,int16_t pitch,int16_t roll);
TOMB_EXPORT int tomb_objects_trigger_keys(TombObjects *,size_t,int,int);
TOMB_EXPORT int tomb_objects_trigger_heavy(TombObjects *,size_t);
TOMB_EXPORT int tomb_objects_trigger(TombObjects *,size_t trigger,int grounded);
#endif
