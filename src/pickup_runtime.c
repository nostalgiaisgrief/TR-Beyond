#include "inventory.h"
#include "playtest.h"
#include "enemies.h"
#include <stdlib.h>
int tomb_pickups_tick(TombPlaytest *p,uint32_t input) {
    TombObjects *w=p->objects;if(!w || p->lara.health<=0)return 1;
    const TombRoomPortals *portals=w->visual->portals+p->lara.actor.room;int first=p->lara.actor.room;
    for(size_t pass=0;pass<=portals->count;pass++) {
        int room=first;if(pass){const unsigned char *r=portals->data+32*(pass-1);room=r[0]|r[1]<<8;}
        for(int id=w->enemies->room_head[room];id>=0;id=w->enemies->room_next[id]) {
            TombObject *o=w->items+id;if(!tomb_pickup_object(o->object))continue;
            if(llabs((long long)p->lara.actor.x-o->actor.x)>=4096 || llabs((long long)p->lara.actor.y-o->actor.y)>=4096 || llabs((long long)p->lara.actor.z-o->actor.z)>=4096)continue;
            int result=tomb_pickup_contact(o,&p->lara.actor,&p->animation,input,p->lara.water_status,&p->lara.pitch,&p->movement.lean);
            if(result<0)return 0;
            if(p->lara.water_status){p->lara.lean=p->movement.lean;p->water.pitch=p->lara.pitch;p->water.lean=p->lara.lean;}
            if(result==2){tomb_inventory_add(&p->inventory,o->object);p->inventory.pickups=(p->inventory.pickups+1)&255;p->inventory.last_pickup=o->object;p->inventory.pickup_ticks=75;tomb_hud_pickup(&p->hud,o->object);}
        }
    }
    return 1;
}
int tomb_pickup_fixture(TombPlaytest *p,TombObjects *w,const int16_t *s,int large) {
    tomb_objects_reset(w);if(!tomb_playtest_init(p,w->level,s,w->visual))return -1;p->objects=w;p->movement_only=1;
    for(size_t id=0;id<w->count;id++)if(w->items[id].object==(large?94:93)) {
        TombActor *a=&p->lara.actor,*o=&w->items[id].actor;a->x=o->x;a->y=o->y;a->z=o->z-100;a->room=o->room;a->yaw=0;p->animation.move_angle=0;return (int)id;
    }
    return -1;
}
