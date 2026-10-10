#ifndef TOMB_ROOM_VISIBILITY_H
#define TOMB_ROOM_VISIBILITY_H
#include "visual.h"
typedef struct TombScreenRect {int left,bottom,right,top;} TombScreenRect;
/* Portal-bounded screen rectangles; caller provides room_count entries. */
int tomb_room_visibility(const TombVisual *,int room,const double eye[3],const double view[16],int width,int height,TombScreenRect *out);
int tomb_room_visibility_focal(const TombVisual *,int,const double[3],const double[16],int,int,double,TombScreenRect *);
/* DOS objects are bounds-tested against room visibility, then drawn against
   the full viewport. view includes the object placement/rotation. */
int tomb_static_visible(const TombStaticDef *,const double view[16],int width,int height,TombScreenRect room);
#endif
