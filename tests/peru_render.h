/* Real renderer/camera coverage of both room layouts and Scion animation. */
static int peru_render_check(void){
    if(level_number!=3 && level_number!=4)return 0;
    FILE *log=fopen("build/peru-render.txt","w");if(!log)return 0;
#define PERU_CHECK(x) do{if(!(x)){fprintf(log,"FAIL line %d: %s (%s)\n",__LINE__,#x,play.status);fclose(log);return 0;}}while(0)
    if(level_number==3){
        for(int j=7;j<=9;j++){objects.items[j].object=122;objects.items[j].actor.flags=34;}
        PERU_CHECK(tomb_objects_trigger_keys(&objects,534,1,0));PERU_CHECK(tomb_objects_trigger_keys(&objects,539,1,0));PERU_CHECK(tomb_objects_trigger_keys(&objects,545,1,0));
        TombActor *o=&objects.items[10].actor;
        play.lara.actor=(TombActor){o->x+600,o->y,o->z,2,2,11,185,0,0,-16384,o->room,32};
        for(int t=0;t<150;t++){
            if(t==30){objects.items[10].actor.current=0;objects.items[10].actor.flags=36;PERU_CHECK(tomb_objects_trigger_keys(&objects,552,1,0));}
            PERU_CHECK(tomb_playtest_tick(&play,0));update_camera(1.0/30);PERU_CHECK(render_capture());camera_alpha=.5;PERU_CHECK(draw());
        }
        PERU_CHECK(objects.peru->flipped);
    }else{
        TombActor *o=&objects.items[20].actor;
        play.lara.actor=(TombActor){o->x,o->y+640,o->z-310,2,2,11,185,0,0,0,o->room,32};
        PERU_CHECK(tomb_peru_lara(&play,64));
        for(int t=0;t<300;t++){
            PERU_CHECK(tomb_playtest_tick(&play,0));update_camera(1.0/30);PERU_CHECK(render_capture());camera_alpha=.5;PERU_CHECK(draw());
            if(t==30)PERU_CHECK(capture("build/qualopec-scion.ppm"));
        }
        PERU_CHECK(objects.peru->flipped && objects.peru->scion_item==-1);
    }
    fprintf(log,"PASS: level %d, real room swaps, object poses and camera interpolation\n",level_number);fclose(log);return 1;
#undef PERU_CHECK
}
