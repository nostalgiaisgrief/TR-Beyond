#ifndef TOMB_PLAYTEST_H
#define TOMB_PLAYTEST_H
#include "lara_start.h"
#include "ground.h"
#include "air.h"
#include "ledge.h"
#include "visual.h"
#include "water.h"
#include "gym.h"
#include "sound.h"
#include "slide.h"
#include "objects.h"
#include "dos_camera.h"
#include "pistols.h"
#include "inventory.h"
#include "interface.h"
typedef struct TombPlaytest {
    const TombLevel *level;
    const TombVisual *visual;
    TombLedgeSamples ledge;
    int static_hit;
    TombLaraStart lara;
    TombMovement movement;
    TombAnimContext animation;
    TombTerrain terrain;
    TombGroundContext collision;
    TombAirContext air;
    TombWater water;
    TombGym gym;
    TombObjects *objects; /* Optional independent door/switch runtime. */
    TombSlideContext slide;
    int movement_only; /* Explicit sandbox: object/level triggers are inactive. */
    int32_t requested_camera_mode;
    int16_t requested_camera_elevation;
    int dead_ticks;
    int door_hit_ticks;
    int door_hit_direction;
    const char *status;
    int blocked;
    unsigned sound_events,sound_stops,bubble_events;
    TombSoundEvent sounds[TOMB_SOUND_EVENTS];
    unsigned sound_count; /* Transactional requests from the most recent tick. */
    unsigned deferred_cd_track; /* Latest deferred tutorial audio request. */
    unsigned deferred_camera; /* Camera index + 1; zero means no request. */
    uint16_t deferred_camera_flags;
    int16_t requested_camera_angle; /* DOS camera request; manual preview camera ignores it. */
    TombCameraRequest camera_request;
    TombPistols pistols;
    uint32_t last_input;
    TombInventory inventory;
    TombHud hud;
    int quest_request,quest_latch;
    int weapon_type,requested_weapon; /* DOS types: 1 pistols, 4 shotgun. */
} TombPlaytest;
int tomb_playtest_init(TombPlaytest *,const TombLevel *,const int16_t *sine,const TombVisual *);
/* Ground/air/climbing/water development harness. Unsupported services roll back movement. */
int tomb_playtest_tick(TombPlaytest *,uint32_t input);
#endif
