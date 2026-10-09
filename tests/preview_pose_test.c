#include "preview_pose.h"
#include "visual.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <math.h>
#include <stdio.h>
/* Independent Euler matrix composition, preserving the renderer's Y-X-Z order. */
static void endpoint(const uint16_t a[3],float out[16]) {
    double m[3][3]={{1,0,0},{0,1,0},{0,0,1}};
    const int order[]={1,0,2};
    for(int k=0;k<3;k++) {
        int axis=order[k],i=(axis+1)%3,j=(axis+2)%3;
        double angle=a[axis]*(6.28318530717958647692/65536.0),c=cos(angle),s=sin(angle);
        for(int row=0;row<3;row++) {double x=m[row][i],y=m[row][j];m[row][i]=c*x+s*y;m[row][j]=-s*x+c*y;}
    }
    for(int i=0;i<16;i++)out[i]=0;
    for(int row=0;row<3;row++)for(int col=0;col<3;col++)out[col*4+row]=(float)m[row][col];
    out[15]=1;
}
static double distance(const float *a,const float *b) {
    double dot=0;for(int row=0;row<3;row++)for(int col=0;col<3;col++)dot+=a[col*4+row]*b[col*4+row];
    double c=(dot-1)*.5;if(c>1)c=1;if(c<-1)c=-1;return acos(c);
}
static void check(const uint16_t *a,const uint16_t *b,double t) {
    float ma[16],mb[16],m[16],end[16];endpoint(a,ma);endpoint(b,mb);
    tomb_preview_rotation(a,b,0,end);for(int i=0;i<16;i++)assert(fabs(end[i]-ma[i])<0.000001);
    tomb_preview_rotation(a,b,1,end);for(int i=0;i<16;i++)assert(fabs(end[i]-mb[i])<0.000001);
    tomb_preview_rotation(a,b,t,m);
    double angle=distance(ma,mb);
    assert(fabs(distance(ma,m)-t*angle)<0.0015);
    assert(fabs(distance(m,mb)-(1-t)*angle)<0.0015);
    for(int i=0;i<3;i++)for(int j=0;j<3;j++) {
        double dot=0;for(int k=0;k<3;k++)dot+=m[i*4+k]*m[j*4+k];
        assert(fabs(dot-(i==j))<0.000001);
    }
    double determinant=m[0]*(m[5]*m[10]-m[9]*m[6])-m[4]*(m[1]*m[10]-m[9]*m[2])+m[8]*(m[1]*m[6]-m[5]*m[2]);
    assert(fabs(determinant-1)<0.000001);
}
int main(int argc,char **argv) {
    assert(argc==3);size_t count=0;
    /* Equivalent gimbal representations of the same rotation must not twist. */
    const uint16_t a[3]={49152,32768,32768},b[3]={49152,0,0};
    for(int i=0;i<=10;i++)check(a,b,i/10.0);
    for(int file=1;file<argc;file++) {
        char error[256];TombLevel *l=tomb_level_load(argv[file],error,sizeof error);assert(l);
        TombVisual *v=tomb_visual_load(l,error,sizeof error);assert(v);
        for(size_t anim=0;anim<v->animation_count;anim++) {
            int rate=v->animations[anim*32+4],length=l->animations[anim].last_frame-l->animations[anim].first_frame;
            for(int frame=0;frame<=length;frame++) {
                TombPose p,q;int key=frame/rate;
                assert(tomb_visual_key(v,anim,(size_t)key,&p));
                if(!tomb_visual_key(v,anim,(size_t)key+1,&q))q=p;
                if(p.count!=15 || q.count!=15)continue;
                for(int joint=0;joint<15;joint++){check(p.rotation[joint],q.rotation[joint],(double)(frame%rate)/rate);count++;}
            }
        }
        tomb_visual_free(v);tomb_level_free(l);
    }
    printf("PASS: %zu real-asset joint interpolations, endpoints, shortest paths and rigid matrices\n",count);
    return 0;
}
