/* Read-only renderer snapshots, captured once per simulation tick in world
   space. Keeping the joint hierarchy preserves bone lengths between ticks. */
static int lara(void);
static int draw_object(const TombObject *);
static TombRenderTrack *render_tracks;
static size_t render_count,render_track=SIZE_MAX;
static uint64_t render_tick;
static int render_recording,render_node,render_parent;
static void render_reset(void){free(render_tracks);render_tracks=NULL;render_count=0;render_tick=0;render_track=SIZE_MAX;}
static void render_select(size_t track,const TombActor *actor){
    render_track=track;render_node=0;render_parent=-1;
    if(render_recording && track<render_count){
        float origin[3]={(float)actor->x,(float)actor->y,(float)actor->z};
        tomb_render_begin(render_tracks+track,render_tick,origin,actor->room);
    }
}
static size_t render_object_key(const TombObject *o){
    for(size_t i=0;i<objects.count;i++)if(o==objects.items+i)return 1+i;
    if(objects.hazards)for(size_t i=0;i<TOMB_DART_CAPACITY;i++)if(o==&objects.hazards->darts[i].item)return 1+objects.count+i;
    return SIZE_MAX;
}
static int render_visible(size_t key,int room){
    TombScreenRect clip=room_rects[room];if(clip.left<clip.right && clip.bottom<clip.top)return 1;
    if(key<render_count && render_tracks[key].tick==render_tick){
        int previous=render_tracks[key].previous_room;
        if(previous>=0 && (size_t)previous<level->room_count){clip=room_rects[previous];return clip.left<clip.right && clip.bottom<clip.top;}
    }
    return 0;
}
static int render_capture(void){
    size_t count=1+objects.count+TOMB_DART_CAPACITY+256;
    if(render_count!=count){render_reset();render_tracks=calloc(count,sizeof *render_tracks);if(!render_tracks)return 0;render_count=count;}
    render_tick++;render_recording=1;
    TombLighting saved_light=model_light;GLdouble saved_view[16];memcpy(saved_view,lighting_view,sizeof saved_view);
    glMatrixMode(GL_MODELVIEW);glPushMatrix();glLoadIdentity();glGetDoublev(GL_MODELVIEW_MATRIX,lighting_view);
    int ok=lara();
    if(caves)for(size_t i=0;i<objects.count;i++){
        const TombObject *o=objects.items+i;
        if(tomb_object_supported(o->object) && !tomb_pickup_object(o->object) && (o->actor.flags&6)!=6)ok=draw_object(o) && ok;
    }
    if(caves && objects.hazards){
        for(size_t i=0;i<TOMB_DART_CAPACITY;i++){
            const TombObject *o=&objects.hazards->darts[i].item;if(o->active)ok=draw_object(o) && ok;
        }
        for(size_t i=0;i<256;i++){
            const TombHazardEffect *e=objects.hazards->effects+i;if(!e->active)continue;
            float m[16]={1,0,0,0,0,1,0,0,0,0,1,0,(float)e->x,(float)e->y,(float)e->z,1};
            TombRenderTrack *r=render_tracks+1+objects.count+TOMB_DART_CAPACITY+i;
            tomb_render_begin(r,render_tick,m+12,e->room);tomb_render_record(r,render_tick,0,-1,e->id,m);
        }
    }
    glPopMatrix();model_light=saved_light;memcpy(lighting_view,saved_view,sizeof saved_view);
    render_track=SIZE_MAX;render_recording=0;return ok;
}
