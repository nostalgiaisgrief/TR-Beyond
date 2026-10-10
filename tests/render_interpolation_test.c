#include "render_interpolation.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
static void matrix(float *m,double angle,float x,float y,float z){
    memset(m,0,16*sizeof *m);m[0]=m[10]=(float)cos(angle);m[2]=-(float)sin(angle);m[8]=(float)sin(angle);m[5]=m[15]=1;m[12]=x;m[13]=y;m[14]=z;
}
int main(void){
    TombRenderTrack track={0};float a[16],b[16],child[16],out[16],root[16];
    matrix(a,0,100,200,300);tomb_render_begin(&track,1,a+12,3);tomb_render_record(&track,1,0,-1,10,a);
    assert(tomb_render_sample(&track,1,0,10,.25,out));assert(!memcmp(a,out,sizeof a));
    matrix(child,0,200,200,300);tomb_render_record(&track,1,1,0,11,child);
    matrix(b,3.14159265358979323846/2,160,200,300);tomb_render_begin(&track,2,b+12,4);tomb_render_record(&track,2,0,-1,10,b);
    matrix(child,3.14159265358979323846/2,160,200,200);tomb_render_record(&track,2,1,0,11,child);
    assert(track.previous_room==3 && track.room==4 && !track.reset);
    for(int frame=0;frame<=144;frame++){
        double t=frame/144.0;assert(tomb_render_sample(&track,2,0,10,t,root));assert(fabs(root[12]-(100+60*t))<.0001);
        assert(tomb_render_sample(&track,2,1,11,t,out));
        double bone_length=0;for(int i=12;i<15;i++)bone_length+=(out[i]-root[i])*(out[i]-root[i]);
        assert(fabs(sqrt(bone_length)-100)<.001);
        for(int col=0;col<3;col++){double norm=0;for(int row=0;row<3;row++)norm+=out[col*4+row]*out[col*4+row];assert(fabs(norm-1)<.00001);}
        /* A camera moving by the same distance keeps a constant relative offset. */
        assert(fabs((root[12]-(50+60*t))-50)<.0001);
    }
    /* Missing ticks/spawn, changed mesh and teleports must not blend stale data. */
    tomb_render_begin(&track,4,b+12,4);tomb_render_record(&track,4,0,-1,10,b);
    assert(tomb_render_sample(&track,4,0,10,0,out) && !memcmp(b,out,sizeof b));
    matrix(b,0,9000,0,0);tomb_render_begin(&track,5,b+12,5);tomb_render_record(&track,5,0,-1,10,b);
    assert(track.reset && tomb_render_sample(&track,5,0,10,0,out) && !memcmp(b,out,sizeof b));
    b[12]+=10;tomb_render_begin(&track,6,b+12,5);tomb_render_record(&track,6,0,-1,12,b);
    assert(tomb_render_sample(&track,6,0,12,0,out) && !memcmp(b,out,sizeof b));assert(!tomb_render_sample(&track,6,0,10,.5,out));
    /* Wrap through 360 degrees follows the short arc, not a full spin. */
    memset(&track,0,sizeof track);matrix(a,6.27,0,0,0);matrix(b,.01,0,0,0);
    tomb_render_begin(&track,1,a+12,0);tomb_render_record(&track,1,0,-1,0,a);
    tomb_render_begin(&track,2,b+12,0);tomb_render_record(&track,2,0,-1,0,b);
    assert(tomb_render_sample(&track,2,0,0,.5,out) && out[0]>.999);
    puts("PASS: render interpolation endpoints, 144 Hz fractions, rigid hierarchy, camera phase, portal crossings, wrap and discontinuities");return 0;
}
