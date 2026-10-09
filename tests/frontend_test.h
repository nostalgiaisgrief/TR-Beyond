/* Exercises the actual menu adapter and transactional cross-level loads. */
static void frontend_frames(int count){for(int t=0;t<count;t++)inventory_tick(0);}
static int frontend_check(void){
#define CHECK(x) do{if(!(x)){FILE *f=fopen("build/frontend-test.txt","w");if(f){fprintf(f,"Failed line %d: %s (title=%d options=%d status=%d frame=%d ready=%d slot=%d action=%d)\n",__LINE__,#x,title_mode,options_ring,inventory_ring.motion.status,inventory_ring.items[inventory_ring.current].frame,inventory_ring.ready,slot_menu,menu_action);fclose(f);}return 0;}}while(0)
 char path[MAX_PATH];for(int i=0;i<16;i++){save_path(path,i);DeleteFileA(path);}
 frontend_title();frontend_frames(20);CHECK(title_mode && inventory_ring.count==5 && inventory_ring.motion.status==1);
 inventory_tick(TOMB_RING_SELECT);frontend_frames(90);CHECK(inventory_ring.ready && inventory_ring.items[0].object==71 && inventory_ring.items[0].frame==19);
 inventory_tick(TOMB_RING_SELECT);frontend_frames(100);CHECK(!title_mode && !inventory_open && level_number==1 && play.lara.health==1000);
 CHECK(objects.progress->music.current_track==57);
 /* Exercise the real CD asset/device adapter, with playback suspended. */
 audio_update(1);CHECK(playing_track==57 && music_output && !audio_error[0]);
 CHECK(music_sample.channels==2 && music_sample.bits==16 && music_sample.rate==44100 && music_mixer.voices[0].mode==2);
 audio_stop();
 play.inventory.counts[9]=3;play.lara.health=650;int x=play.lara.actor.x;
 inventory_begin();frontend_frames(20);inventory_tick(32);frontend_frames(30);CHECK(options_ring && inventory_ring.count==4 && inventory_ring.motion.status==1);
 inventory_tick(TOMB_RING_SELECT);frontend_frames(90);CHECK(inventory_ring.items[0].frame==19);
 inventory_tick(TOMB_RING_SELECT);CHECK(slot_menu);inventory_tick(TOMB_RING_SELECT);frontend_frames(100);CHECK(!inventory_open);save_path(path,0);CHECK(tomb_save_level(path)==1);
 play.lara.actor.x+=100;play.inventory.counts[9]=0;frontend_title();frontend_frames(20);inventory_tick(TOMB_RING_SELECT);frontend_frames(90);CHECK(inventory_ring.items[0].frame==14);
 inventory_tick(TOMB_RING_SELECT);CHECK(slot_menu);inventory_tick(TOMB_RING_SELECT);frontend_frames(100);CHECK(!title_mode && !inventory_open && play.lara.actor.x==x && play.inventory.counts[9]==3 && play.lara.health==650);
 CHECK(load_game_level(2,0,NULL));CHECK(objects.progress->music.current_track==57);CHECK(tomb_city_fixture(&play,&objects,sine_table,0));for(int t=0;t<45;t++)CHECK(tomb_playtest_tick(&play,64));for(int t=0;t<30;t++)CHECK(tomb_playtest_tick(&play,65));x=objects.items[0].actor.z;
 save_path(path,1);CHECK(tomb_save_write(path,2,&play,&objects,&camera,&level_inventory));CHECK(load_game_level(1,0,NULL));CHECK(load_game_level(2,0,path));CHECK(objects.items[0].actor.z==x && play.lara.actor.current==36);
 play.lara.health=-1;death_menu=1;inventory_begin();frontend_frames(120);CHECK(options_ring && inventory_ring.items[0].object==71 && inventory_ring.items[0].frame==14);
 inventory_tick(TOMB_RING_BACK);frontend_frames(10);CHECK(inventory_open && inventory_ring.items[0].object==71);
 inventory_tick(TOMB_RING_RIGHT);frontend_frames(30);CHECK(inventory_ring.items[0].frame==24);
 inventory_tick(TOMB_RING_SELECT);frontend_frames(100);CHECK(title_mode && inventory_open);
 /* Dialog navigation follows displayed DOS row/column order. */
 frontend_title();frontend_frames(32);
 while(inventory_ring.items[inventory_ring.current].object!=95){inventory_tick(TOMB_RING_RIGHT);frontend_frames(32);}
 inventory_tick(TOMB_RING_SELECT);frontend_frames(90);CHECK(inventory_ring.ready);
 int detail_before=settings_detail;option_row=settings_detail=2;
 inventory_tick(32);CHECK(settings_detail==1);inventory_tick(16);CHECK(settings_detail==2);
 inventory_tick(TOMB_RING_BACK);frontend_frames(90);settings_detail=detail_before;
 while(inventory_ring.items[inventory_ring.current].object!=97){inventory_tick(TOMB_RING_RIGHT);frontend_frames(32);}
 inventory_tick(TOMB_RING_SELECT);frontend_frames(90);CHECK(inventory_ring.ready);
 option_row=9;inventory_tick(32);CHECK(option_row==11);inventory_tick(32);CHECK(option_row==10);
 option_row=0;inventory_tick(TOMB_RING_RIGHT);CHECK(option_row==7);inventory_tick(TOMB_RING_LEFT);CHECK(option_row==0);
 inventory_tick(TOMB_RING_SELECT);CHECK(binding_wait);
 /* Controls edit consumes the binding press instead of activating gameplay. */
 option_row=0;binding_wait=1;unsigned old=bindings[0];window_proc(NULL,WM_KEYDOWN,'T',1);CHECK(bindings[0]=='T' && !binding_wait);bindings[0]=old;
 for(int i=0;i<16;i++){save_path(path,i);DeleteFileA(path);}FILE *f=fopen("build/frontend-test.txt","w");if(f){fputs("PASS: title/new game, options transfer, passport/save/load, cross-level block restore, death passport/exit, binding capture\n",f);fclose(f);}return 1;
#undef CHECK
}
