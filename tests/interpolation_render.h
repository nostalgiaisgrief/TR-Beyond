static int interpolation_render_check(void){
    size_t bytes=objects.count*sizeof *objects.items;
    void *copy=malloc(bytes?bytes:1);if(!copy)return 0;
    render_reset();int moved=0,fixed_checks=0;
    for(int tick=0;tick<80;tick++){
        if(tick){unsigned input=tick<40?1:caves?(tick==41?32:tick>62?64:0):0;if(!tomb_playtest_tick(&play,input)){free(copy);return 0;}
            TombFollowCamera old=camera;update_camera(1.0/30);
            if(old.ready && !old.fixed_target && objects.camera.active && objects.camera.speed==1 && objects.camera.target<0 && !(play.camera_request.flags&(TOMB_CAMERA_LOOK|TOMB_CAMERA_COMBAT))){
                for(int j=0;j<3;j++)if(camera.previous_target[j]!=old.target[j]){fprintf(stderr,"Fixed camera target lost interpolation history: level %d tick %d axis %d\n",level_number,tick,j);free(copy);return 0;}
                fixed_checks++;
            }
        }
        TombPlaytest before=play;memcpy(copy,objects.items,bytes);
        if(!render_capture() || memcmp(&before,&play,sizeof play) || memcmp(copy,objects.items,bytes)){free(copy);return 0;}
        float a[16],b[16],mid[16];int identity=render_tracks[0].nodes[0].identity;
        if(!tomb_render_sample(render_tracks,render_tick,0,identity,0,a) || !tomb_render_sample(render_tracks,render_tick,0,identity,1,b) || !tomb_render_sample(render_tracks,render_tick,0,identity,.5,mid)){free(copy);return 0;}
        for(int i=12;i<15;i++){if(fabsf(mid[i]-(a[i]+b[i])*.5f)>.02f){free(copy);return 0;}if(fabsf(a[i]-b[i])>1)moved++;}
        if(tick==20 || tick==40 || tick==70)for(int sub=0;sub<4;sub++){camera_alpha=sub/4.0;if(!draw() || memcmp(&before,&play,sizeof play) || memcmp(copy,objects.items,bytes)){free(copy);return 0;}}
    }
    if(level_number==13 && !fixed_checks){fprintf(stderr,"Natla fixed-camera fixture did not activate\n");free(copy);return 0;}
    /* Fixed viewpoints must retain DOS tick results while their moving target
       remains on the actor interpolation timeline. Exercise entry, tracking,
       item-target cuts and return to the chase camera. */
    if(level_number==12 || level_number==13){
        TombFollowCamera fixed={0};TombActor focus=play.lara.actor;
        for(int t=0;t<16;t++){
            TombCameraRequest r=tomb_camera_control(focus.current,0,0);r.fixed_index=t<12?0:-1;r.speed=1;r.item_target=t>=8 && t<12;
            focus.x+=t%2?16:-16;int16_t bounds[6];
            if(!tomb_visual_item_bounds(visual,0,&focus,bounds)){free(copy);return 0;}
            TombFollowCamera previous=fixed;TombDosCamera direct=fixed.dos;
            if(!tomb_dos_camera_tick(&direct,level,&focus,bounds,sine_table,&r) || !tomb_camera_tick(&fixed,level,visual,&focus,0,sine_table,&r) || memcmp(&direct,&fixed.dos,sizeof direct)){free(copy);return 0;}
            int cut=!previous.ready || previous.dos.fixed!=(r.fixed_index>=0 && r.item_target);
            for(int j=0;j<3;j++){
                if(fixed.previous_target[j]!=(cut?fixed.target[j]:previous.target[j])){free(copy);return 0;}
                if(r.fixed_index>=0 && fixed.previous_eye[j]!=fixed.eye[j]){free(copy);return 0;}
            }
        }
    }
    render_reset();if(!render_capture()){free(copy);return 0;}
    float first[16];int identity=render_tracks[0].nodes[0].identity;
    int ok=tomb_render_sample(render_tracks,render_tick,0,identity,0,first) && !memcmp(first,render_tracks[0].nodes[0].world,sizeof first) && moved;
    free(copy);printf("%s: live scene snapshots, pose movement, subframe drawing, reset and simulation immutability (%d moving coordinates)\n",ok?"PASS":"FAIL",moved);return ok;
}
