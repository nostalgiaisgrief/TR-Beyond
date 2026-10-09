#include "room_visibility.h"
#include "preview_camera.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
static void portal(unsigned char *p,int room,int z) {
    int values[16]={room,0,0,-1,-100,-100,z,100,-100,z,100,100,z,-100,100,z};
    for(int i=0;i<16;i++){p[i*2]=(unsigned char)values[i];p[i*2+1]=(unsigned char)((unsigned)values[i]>>8);}
}
int main(void) {
    TombRoom rooms[4]={{0}};TombLevel l={0};l.rooms=rooms;l.room_count=4;
    unsigned char a[32],b[32],c[32];portal(a,1,1000);portal(b,2,2000);portal(c,0,3000);
    TombRoomPortals portals[4]={{a,1},{b,1},{c,1},{0}};
    TombVisual v={0};v.level=&l;v.room_count=4;v.portals=portals;
    double eye[3]={0,0,0},target[3]={0,0,1},view[16];assert(tomb_preview_view(eye,target,view));
    TombScreenRect rect[4];assert(tomb_room_visibility(&v,0,eye,view,1000,500,rect));
    assert(rect[0].left==0 && rect[0].right==1000);
    assert(rect[1].left==460 && rect[1].right==540);
    assert(rect[2].left==480 && rect[2].right==520);
    assert(rect[3].right==0); /* Overlapping but disconnected room. */
    /* Widening without changing height translates portal bounds horizontally
       but preserves their vertical framing and size. */
    TombScreenRect narrow[4],wide[4];
    assert(tomb_room_visibility(&v,0,eye,view,640,480,narrow));
    assert(tomb_room_visibility(&v,0,eye,view,1280,480,wide));
    for(int i=1;i<=2;i++) {
        assert(wide[i].bottom==narrow[i].bottom && wide[i].top==narrow[i].top);
        assert(wide[i].left==narrow[i].left+320 && wide[i].right==narrow[i].right+320);
    }
    portal(a,1,-1000);assert(tomb_room_visibility(&v,0,eye,view,1000,500,rect));assert(rect[1].right==0);
    portal(a,1,1);assert(tomb_room_visibility(&v,0,eye,view,1000,500,rect));assert(rect[1].right==1000); /* Inside near plane. */
    a[6]=1;a[7]=0;assert(tomb_room_visibility(&v,0,eye,view,1000,500,rect));assert(rect[1].right==0); /* Backface. */
    TombStaticDef def={0};def.flags=2;
    def.draw_bounds[0]=-200;def.draw_bounds[1]=200;def.draw_bounds[2]=-100;def.draw_bounds[3]=100;def.draw_bounds[4]=900;def.draw_bounds[5]=1100;
    TombScreenRect opening={490,240,510,260};
    assert(tomb_static_visible(&def,view,1000,500,opening)); /* Bounds cross all four portal edges. */
    def.flags=0;assert(!tomb_static_visible(&def,view,1000,500,opening));
    def.flags=1;assert(!tomb_static_visible(&def,view,1000,500,opening));
    def.flags=3;assert(tomb_static_visible(&def,view,1000,500,opening));
    assert(!tomb_static_visible(&def,view,1000,500,(TombScreenRect){0,0,0,0}));
    assert(!tomb_static_visible(&def,view,1000,500,(TombScreenRect){0,0,100,100}));
    /* Collision bounds are deliberately zero: rendering uses drawing bounds. */
    def.draw_bounds[4]=-1100;def.draw_bounds[5]=-900;
    assert(!tomb_static_visible(&def,view,1000,500,opening));
    puts("PASS: static visibility flags, drawing bounds, portal overlap and behind-eye rejection");
    puts("PASS: portal bounds, chained openings, cycles, disconnected rooms, behind-eye and near-plane cases");
}
