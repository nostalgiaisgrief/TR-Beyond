#include "preview_camera.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <math.h>
#include <stdio.h>
static double component(const double m[16],const double p[3],int row) {
    return m[row]*p[0]+m[row+4]*p[1]+m[row+8]*p[2]+m[row+12];
}
int main(void) {
    const double targets[2][3]={{0,0,0},{37376,-1730,51712}};
    /* Cardinal original-world camera positions and expected screen-right. */
    const double offsets[4][3]={{0,0,-1800},{1800,0,0},{0,0,1800},{-1800,0,0}};
    const double rights[4][3]={{1,0,0},{0,0,1},{-1,0,0},{0,0,-1}};
    for(int t=0;t<2;t++) for(int c=0;c<4;c++) for(int elevated=0;elevated<2;elevated++) {
        double eye[3],m[16],right[3],up[3];
        for(int i=0;i<3;i++) { eye[i]=targets[t][i]+offsets[c][i]; right[i]=targets[t][i]+rights[c][i]*100; up[i]=targets[t][i]; }
        eye[1]-=elevated*550; up[1]-=100;
        assert(tomb_preview_view(eye,targets[t],m));
        assert(fabs(component(m,targets[t],0))<1e-8);
        assert(fabs(component(m,targets[t],1))<1e-8);
        assert(component(m,targets[t],2)<-1700);
        assert(component(m,right,0)>99.99);
        assert(component(m,up,1)>90);
        for(int i=0;i<3;i++) assert(fabs(component(m,eye,i))<1e-8);
        double determinant=m[0]*(m[5]*m[10]-m[9]*m[6])-m[4]*(m[1]*m[10]-m[9]*m[2])+m[8]*(m[1]*m[6]-m[5]*m[2]);
        assert(fabs(determinant-1)<1e-12); /* A mirror would be -1. */
    }
    /* Fixed vertical framing at 4:3, 16:9, ultrawide and portrait sizes.
       At the same depth, the top/bottom world extents remain identical;
       the horizontal extent grows in proportion to aspect ratio. */
    const int sizes[][2]={{640,480},{1280,960},{1280,720},{2560,1080},{480,640}};
    const double baseline=480.0/(2*tomb_preview_focal(640));
    assert(tomb_preview_aspect_focal(480)==tomb_preview_focal(640));
    assert(tomb_preview_aspect_focal(0)==0);
    for(unsigned i=0;i<sizeof sizes/sizeof sizes[0];i++) {
        double focal=tomb_preview_aspect_focal(sizes[i][1]);
        double vertical=sizes[i][1]/(2*focal),horizontal=sizes[i][0]/(2*focal);
        assert(fabs(vertical-baseline)<1e-12);
        assert(fabs(horizontal/baseline-(double)sizes[i][0]/sizes[i][1])<1e-12);
    }
    puts("PASS: DOS 4:3 vertical framing preserved across five viewport sizes");
    double invalid[16];
    assert(!tomb_preview_view(targets[0],targets[0],invalid));
    const double vertical_eye[3]={0,-100,0},vertical_target[3]={0,0,0};
    assert(tomb_preview_view(vertical_eye,vertical_target,invalid));
    for(int i=0;i<16;i++)assert(isfinite(invalid[i]));
    puts("PASS: 16 cardinal/translated/elevated camera orientation cases");
    return 0;
}
