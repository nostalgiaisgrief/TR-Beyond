#include "step.h"
#include "combat.h"
#include "playtest.h"
TOMB_EXPORT void tomb_test_shotgun_target(TombObjects *w,TombLaraStart *lara,TombPistols *guns,const int16_t *sine,int action) {
    TombPlaytest p={0};p.level=w->level;p.visual=w->visual;p.objects=w;p.lara=*lara;p.pistols=*guns;p.animation.sine_quarter=sine;p.weapon_type=4;
    tomb_combat_target(&p,action);*guns=p.pistols;
}
TOMB_EXPORT void tomb_test_target(TombObjects *w,TombLaraStart *lara,TombPistols *guns,const int16_t *sine,int action) {
    TombPlaytest p={0};p.level=w->level;p.visual=w->visual;p.objects=w;p.lara=*lara;p.pistols=*guns;p.animation.sine_quarter=sine;
    tomb_combat_target(&p,action);*guns=p.pistols;
}
#include "level.h"
#include "lara_start.h"
#include "visual.h"
/* Confirm the test harness and compiled C agree about native struct layouts. */
TOMB_EXPORT size_t tomb_test_size(int which)
{
    switch (which) {
    case 0: return sizeof(TombActor);
    case 1: return sizeof(TombAnim);
    case 2: return sizeof(TombAnimContext);
    case 3: return sizeof(TombContact);
    case 4: return sizeof(TombWalkContext);
    case 5: return sizeof(TombLevel);
    case 6: return sizeof(TombRoom);
    case 7: return sizeof(TombSector);
    case 8: return sizeof(TombHeights);
    case 9: return sizeof(TombTerrain);
    case 10: return sizeof(TombStaticPlacement);
    case 11: return sizeof(TombStaticDef);
    case 12: return sizeof(TombStaticContact);
    case 13: return sizeof(TombItem);
    case 14: return sizeof(TombLaraStart);
    case 15: return sizeof(TombVisual);
    case 16: return sizeof(TombMeshView);
    case 17: return sizeof(TombPose);
    case 18: return sizeof(TombModel);
    default: return 0;
    }
}
