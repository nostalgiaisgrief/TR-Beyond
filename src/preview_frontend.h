/* Win32/GL adapter for the original option ring and passport.
   Included after font/ring helpers; all gameplay remains in the C runtime. */
static void frontend_free(void){
 if(title_visual){glDeleteTextures((GLsizei)(title_visual->tile_count*2+1),title_tiles);glDeleteTextures((GLsizei)title_visual->tile_count,title_font_tiles);}
 free(title_tiles);free(title_font_tiles);tomb_visual_free(title_visual);tomb_level_free(title_level);glDeleteTextures(1,&title_backdrop);
}
static int frontend_assets(void){
 if(title_visual)return 1;
 char path[MAX_PATH],error[256];asset_path(path,"TITLE.PHD");
 title_level=tomb_level_load(path,error,sizeof error);if(!title_level)return 0;
 title_visual=tomb_visual_load(title_level,error,sizeof error);if(!title_visual)return 0;
 TombLevel *saved_level=level;TombVisual *saved_visual=visual;GLuint *saved_tiles=tiles,*saved_font=font_tiles;
 level=title_level;visual=title_visual;int ok=make_tiles();title_tiles=tiles;title_font_tiles=font_tiles;
 level=saved_level;visual=saved_visual;tiles=saved_tiles;font_tiles=saved_font;if(!ok)return 0;
 asset_path(path,"TITLEH.PCX");FILE *f=fopen(path,"rb");if(!f)return 0;
 unsigned char header[128],palette[768];if(fread(header,1,128,f)!=128 || header[0]!=10 || header[3]!=8 || header[65]!=1){fclose(f);return 0;}
 int w=u16(header+8)-u16(header+4)+1,h=u16(header+10)-u16(header+6)+1,stride=u16(header+66);
 if(w!=640 || h!=480 || stride<w || stride>2048 || fseek(f,-768,SEEK_END) || fread(palette,1,768,f)!=768 || fseek(f,128,SEEK_SET)){fclose(f);return 0;}
 unsigned char *rgb=calloc(1024*512,3);if(!rgb){fclose(f);return 0;}
 int remaining=0,value=0;
 for(int y=0;y<h && ok;y++)for(int x=0;x<stride;x++){
  if(!remaining){value=fgetc(f);if(value<0){ok=0;break;}if((value&192)==192){remaining=value&63;value=fgetc(f);if(!remaining || value<0){ok=0;break;}}else remaining=1;}
  remaining--;if(x<w)memcpy(rgb+((size_t)y*1024+x)*3,palette+value*3,3);
 }
 fclose(f);if(ok){glGenTextures(1,&title_backdrop);glBindTexture(GL_TEXTURE_2D,title_backdrop);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);glTexImage2D(GL_TEXTURE_2D,0,GL_RGB,1024,512,0,GL_RGB,GL_UNSIGNED_BYTE,rgb);}free(rgb);return ok;
}
static void frontend_backdrop(void){
 glEnable(GL_TEXTURE_2D);glDisable(GL_ALPHA_TEST);glBindTexture(GL_TEXTURE_2D,title_backdrop);glColor3f(1,1,1);
 glBegin(GL_QUADS);glTexCoord2f(0,0);glVertex2d((width-height*4.0/3)/2,0);glTexCoord2f(640.f/1024,0);glVertex2d((width+height*4.0/3)/2,0);glTexCoord2f(640.f/1024,480.f/512);glVertex2d((width+height*4.0/3)/2,height);glTexCoord2f(0,480.f/512);glVertex2d((width-height*4.0/3)/2,height);glEnd();glDisable(GL_TEXTURE_2D);
}
static const char *frontend_name(int id){if(level_number==3 && id==114)return "Machine Cog";switch(id){case 71:case 81:return "Game";case 73:return "Lara's Home";case 95:return "Detail Levels";case 96:return "Sound";case 97:return "Controls";default:return tomb_inventory_name(id);}}
static void refresh_slots(void){char path[MAX_PATH];for(int i=0;i<16;i++){save_path(path,i);save_levels[i]=tomb_save_level(path);}}
static void frontend_title(void){
 audio_stop();title_mode=1;death_menu=0;play.quest_request=0;inventory_begin();options_ring=1;tomb_ring_init_options(&inventory_ring,1);inventory_sound();refresh_slots();
}
static void frontend_execute(int id){
 char path[MAX_PATH];int action=menu_action;menu_action=0;
 if(id==73){load_game_level(0,0,NULL);return;}
 if(action==1){save_path(path,slot_current);if(!load_game_level(save_levels[slot_current],0,path)){inventory_begin();options_ring=1;tomb_ring_init_options(&inventory_ring,title_mode);}}
 else if(action==2){if(title_mode || level_number==0){if(!load_game_level(new_game_level,0,NULL)){inventory_begin();options_ring=1;tomb_ring_init_options(&inventory_ring,title_mode);}}else{save_path(path,slot_current);if(!tomb_save_write(path,level_number,&play,&objects,&camera,&level_inventory)){inventory_begin();strcpy(menu_error,"Could not save game");}}}
 else if(action==3){if(title_mode)running=0;else frontend_title();}
}
static const int frontend_binding_order[13]={0,1,2,3,4,5,6,7,8,9,11,10,12};
static int frontend_input(unsigned *input){
 TombRing *r=&inventory_ring;TombRingItem *i=r->items+r->current;
 if(r->motion.status==1 && (*input&TOMB_RING_SELECT)){option_row=i->object==95?settings_detail:0;}
 if(death_menu && r->motion.status==1 && !r->rotating){r->current=0;*input=TOMB_RING_SELECT;}
 if(r->motion.status!=8 || !r->ready)return 0;
 if(i->object==71){
  int page=(i->frame-i->open_frame)/5;
  if(new_game_menu){
   if(*input&16 && new_game_level>0)new_game_level--;
   if(*input&32 && new_game_level<LEVEL_CHOICE_COUNT-1)new_game_level++;
   if(*input&TOMB_RING_BACK)new_game_menu=0;
   else if(*input&TOMB_RING_SELECT){new_game_menu=0;menu_action=2;tomb_ring_finish_item(r,71);}
   *input=0;return 0;
  }
  if(slot_menu){
   if(*input&16 && slot_current>0)slot_current--;if(*input&32 && slot_current<15)slot_current++;
   if(*input&TOMB_RING_BACK){slot_menu=0;menu_error[0]=0;}
  else if(*input&TOMB_RING_SELECT){if(page==1 || save_levels[slot_current]>0){menu_action=page+1;slot_menu=0;tomb_ring_finish_item(r,71);}else strcpy(menu_error,"Empty Slot");}
   *input=0;return 0;
  }
  /* When there are no saves DOS skips the load page. */
  int any=0;for(int n=0;n<16;n++)if(save_levels[n]>0)any=1;
  if(page==0 && !any){i->goal=death_menu?24:19;i->direction=1;r->ready=0;*input=0;return 0;}
  int direction=(*input&TOMB_RING_RIGHT)?1:(*input&TOMB_RING_LEFT)?-1:0;
  if(direction){int next=page+direction;if(next>=(!any?1:0) && next<=2 && !(death_menu && next==1)){i->goal=(int16_t)(14+next*5);i->direction=(int16_t)direction;r->ready=0;r->sound=115;inventory_sound();}else if(death_menu && next==1){i->goal=(int16_t)(direction>0?24:14);i->direction=(int16_t)direction;r->ready=0;}*input=0;}
  else if(death_menu && (*input&TOMB_RING_BACK)){*input=0;}
  else if(*input&TOMB_RING_SELECT){
   if(page==0 || (page==1 && !title_mode && level_number!=0)){slot_menu=1;slot_current=0;menu_error[0]=0;refresh_slots();}
   else if(page==1 && (title_mode || level_number==0)){new_game_menu=1;new_game_level=1;menu_error[0]=0;}
   else{menu_action=page+1;tomb_ring_finish_item(r,71);}*input=0;
  }
 }else if(i->object==73){
  if(*input&TOMB_RING_SELECT){tomb_ring_finish_item(r,73);*input=0;}
 }
 else if(i->object>=95 && i->object<=97){
  int rows=i->object==95?3:i->object==96?2:13;
  if(i->object==95){if(*input&16 && option_row<2)option_row++;if(*input&32 && option_row>0)option_row--;}
  else if(i->object==97){
   int row=0;while(row<12 && frontend_binding_order[row]!=option_row)row++;
   if(*input&16 && row>0)row--;if(*input&32 && row<12)row++;
   if(*input&(TOMB_RING_LEFT|TOMB_RING_RIGHT))row=row<7?(row==6?12:row+7):(row==12?6:row-7);
   option_row=frontend_binding_order[row];
  }else {if(*input&16 && option_row>0)option_row--;if(*input&32 && option_row<rows-1)option_row++;}
  if(i->object==95){settings_detail=option_row;}
  if(i->object==96){int *v=option_row?&settings_sound:&settings_music;if(*input&TOMB_RING_LEFT && *v>0)--*v;if(*input&TOMB_RING_RIGHT && *v<10)++*v;}
  if(i->object==97 && (*input&TOMB_RING_SELECT)){binding_wait=1;*input=0;return 0;}
  if(*input&(TOMB_RING_SELECT|TOMB_RING_BACK)){settings_write();tomb_ring_finish_item(r,-1);option_row=0;}
  *input=0;
 }
 return 0;
}
/* DOS 1a21c maps a frozen indexed frame through light-map rows 16..24.
   The modern RGB framebuffer is quantized once to the original palette. */
static void frontend_inventory_backdrop(void){
 static GLuint texture;static unsigned char *indices,*rgb;static int w,h,pw,ph,shade=-1;
 if(w!=width || h!=height || backdrop_dirty){
  free(indices);free(rgb);w=width;h=height;pw=ph=1;while(pw<w)pw*=2;while(ph<h)ph*=2;
  indices=malloc((size_t)w*h);rgb=calloc((size_t)pw*ph,3);unsigned char *pixels=malloc((size_t)w*h*3);
  if(!indices || !rgb || !pixels){free(pixels);return;}
  unsigned char lut[32768];
  for(int key=0;key<32768;key++){int best=0,dist=INT_MAX;for(int i=0;i<256;i++){int d=0;for(int c=0;c<3;c++){int value=((key>>(10-c*5))&31)*255/31-visual->palette[i*3+c]*255/63;d+=value*value;}if(d<dist){dist=d;best=i;}}lut[key]=(unsigned char)best;}
  glPixelStorei(GL_PACK_ALIGNMENT,1);glReadPixels(0,0,w,h,GL_RGB,GL_UNSIGNED_BYTE,pixels);
  for(size_t n=0;n<(size_t)w*h;n++)indices[n]=lut[((pixels[n*3]>>3)<<10)|((pixels[n*3+1]>>3)<<5)|(pixels[n*3+2]>>3)];free(pixels);
  if(!texture)glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
  glTexImage2D(GL_TEXTURE_2D,0,GL_RGB,pw,ph,0,GL_RGB,GL_UNSIGNED_BYTE,rgb);shade=-1;backdrop_dirty=0;
 }
 if(!indices || !rgb)return;
 int row=objects.progress->complete?24:backdrop_shade/2;
 glEnable(GL_TEXTURE_2D);glBindTexture(GL_TEXTURE_2D,texture);
 if(shade!=row){const unsigned char *light=level->file_data+level->item_parsed_bytes+row*256;
  for(int y=0;y<h;y++)for(int x=0;x<w;x++){int index=indices[y*w+x];if(row!=16)index=light[index];for(int c=0;c<3;c++)rgb[((size_t)y*pw+x)*3+c]=(unsigned char)(visual->palette[index*3+c]*255/63);}
  glPixelStorei(GL_UNPACK_ALIGNMENT,1);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,pw,ph,GL_RGB,GL_UNSIGNED_BYTE,rgb);shade=row;
 }
 glColor3f(1,1,1);glBegin(GL_QUADS);glTexCoord2f(0,(float)h/ph);glVertex2i(0,0);glTexCoord2f((float)w/pw,(float)h/ph);glVertex2i(w,0);glTexCoord2f((float)w/pw,0);glVertex2i(w,h);glTexCoord2f(0,0);glVertex2i(0,h);glEnd();glDisable(GL_TEXTURE_2D);
}
/* DOS translucent panels use light-map row 24 (1fa5c), not an opaque fill.
   Quantize the small RGB panel region to the supplied palette for that lookup. */
static void frontend_panel_shade(int x,int y,int w,int h) {
 static unsigned char lut[32768],palette[768];static int valid;static GLuint texture;
 if(!valid || memcmp(palette,visual->palette,sizeof palette)) {
  memcpy(palette,visual->palette,sizeof palette);valid=1;
  for(int key=0;key<32768;key++){int best=0,dist=INT_MAX;for(int n=0;n<256;n++){int d=0;for(int c=0;c<3;c++){int delta=((key>>(10-5*c))&31)*255/31-palette[3*n+c]*255/63;d+=delta*delta;}if(d<dist){dist=d;best=n;}}lut[key]=(unsigned char)best;}
 }
 if(x<0){w+=x;x=0;}if(y<0){h+=y;y=0;}if(x+w>width)w=width-x;if(y+h>height)h=height-y;if(w<=0 || h<=0)return;
 int pw=1,ph=1;while(pw<w)pw*=2;while(ph<h)ph*=2;
 unsigned char *pixels=malloc((size_t)w*h*3),*rgb=calloc((size_t)pw*ph,3);if(!pixels || !rgb){free(pixels);free(rgb);return;}
 glReadBuffer(GL_BACK);glPixelStorei(GL_PACK_ALIGNMENT,1);glReadPixels(x,height-y-h,w,h,GL_RGB,GL_UNSIGNED_BYTE,pixels);
 const TombLevel *panel_level=visual->level;
 const unsigned char *light=panel_level->file_data+panel_level->item_parsed_bytes+24*256;
 for(int yy=0;yy<h;yy++)for(int xx=0;xx<w;xx++){const unsigned char *p=pixels+((size_t)yy*w+xx)*3;int index=light[lut[((p[0]>>3)<<10)|((p[1]>>3)<<5)|(p[2]>>3)]];for(int c=0;c<3;c++)rgb[((size_t)yy*pw+xx)*3+c]=(unsigned char)(palette[index*3+c]*255/63);}
 if(!texture)glGenTextures(1,&texture);glEnable(GL_TEXTURE_2D);glBindTexture(GL_TEXTURE_2D,texture);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
 glPixelStorei(GL_UNPACK_ALIGNMENT,1);glTexImage2D(GL_TEXTURE_2D,0,GL_RGB,pw,ph,0,GL_RGB,GL_UNSIGNED_BYTE,rgb);glColor3f(1,1,1);
 glBegin(GL_QUADS);glTexCoord2f(0,(float)h/ph);glVertex2i(x,y);glTexCoord2f((float)w/pw,(float)h/ph);glVertex2i(x+w,y);glTexCoord2f((float)w/pw,0);glVertex2i(x+w,y+h);glTexCoord2f(0,0);glVertex2i(x,y+h);glEnd();glDisable(GL_TEXTURE_2D);free(pixels);free(rgb);
}
static void frontend_edge(double x,double y,double w,double h,int index) {
 double scale=fmax(.5,fmin(width/640.0,height/480.0));
 colour((unsigned)index,1);glBegin(GL_QUADS);glVertex2d(x,y);glVertex2d(x+w*scale,y);glVertex2d(x+w*scale,y+h*scale);glVertex2d(x,y+h*scale);glEnd();
}
static void frontend_panel(const TombDialogEntry *entry,const char *text) {
 TombTextStyle style={0,0,65536,65536,1,6,0};int bounds[4];tomb_dialog_bounds(entry,tomb_text_width(text,&style),bounds);
 double scale=fmax(.5,fmin(width/640.0,height/480.0)),x=(width-640*scale)/2+bounds[0]*scale;
 double y=(entry->flags&TOMB_TEXT_BOTTOM)?height-480*scale+bounds[1]*scale:(height-480*scale)/2+bounds[1]*scale;
 int w=bounds[2],h=bounds[3];frontend_panel_shade((int)x,(int)y,(int)(w*scale),(int)(h*scale));
 /* Eight one-pixel bevel lines, palette 15/31, from DOS 1f938. */
 frontend_edge(x,y-scale,w+1,1,15);frontend_edge(x,y,w,1,31);
 frontend_edge(x+w*scale,y,1,h+1,15);frontend_edge(x+(w+1)*scale,y,1,h+2,31);
 frontend_edge(x,y+h*scale,w+1,1,15);frontend_edge(x-scale,y+(h+1)*scale,w+2,1,31);
 frontend_edge(x-scale,y-scale,1,h+2,15);frontend_edge(x,y,1,h+1,31);
}
static void frontend_entry(const TombDialogEntry *entry,const char *text,int selected) {
 if(entry->panel_width || selected)frontend_panel(entry,text);
 if(entry->flags&TOMB_TEXT_CENTRE)ui_text(entry->x,entry->y,text,(unsigned)entry->flags);
 else {double scale=fmax(.5,fmin(width/640.0,height/480.0));text_aligned((float)((width-640*scale)/2+entry->x*scale),(float)(entry->y*scale),text,(unsigned)entry->flags);}
}
static void frontend_key_name(unsigned key,char out[40]) {
 if(key>=VK_NUMPAD0 && key<=VK_NUMPAD9){snprintf(out,40,"PAD%u",key-VK_NUMPAD0);return;}
 LONG scan=(LONG)(MapVirtualKeyA(key,MAPVK_VK_TO_VSC)<<16);if(key>=VK_PRIOR && key<=VK_DOWN)scan|=1L<<24;
 if(!GetKeyNameTextA(scan,out,40))snprintf(out,40,"%u",key);
}
static void frontend_overlay(void){
 TombRing *r=&inventory_ring;TombRingItem *i=r->items+r->current;
 if(r->motion.status!=8 || !r->ready)return;
 TombDialogEntry entries[32];
 if(i->object==71){
  if(new_game_menu){
   int first=new_game_level>=10?new_game_level-9:0;
   tomb_dialog_layout(71,new_game_level-first,1,entries);
   frontend_entry(entries," ",0);frontend_entry(entries+1,"Choose Starting Level",0);
   for(int row=0;row<10 && first+row<LEVEL_CHOICE_COUNT;row++)frontend_entry(entries+row+2,level_choices[first+row].name,0);
   if(first>0)ui_text(0,-282,"[",TOMB_TEXT_CENTRE|TOMB_TEXT_BOTTOM);
   if(first+10<LEVEL_CHOICE_COUNT)ui_text(0,-88,"]",TOMB_TEXT_CENTRE|TOMB_TEXT_BOTTOM);
   return;
  }
  int page=(i->frame-14)/5;
  const char *label=page==0?"Load Game":page==1?(title_mode || level_number==0?"New Game":"Save Game"):(title_mode?"Exit Game":"Exit to Title");
  int first=slot_current>=10?slot_current-9:0;
  tomb_dialog_layout(71,slot_current-first,slot_menu,entries);
  if(!slot_menu)frontend_entry(entries,label,0);
  else {
   frontend_entry(entries," ",0);frontend_entry(entries+1,label,0);
   for(int row=0;row<10;row++){int n=first+row;char line[96];snprintf(line,sizeof line,"%02d %s",n+1,save_levels[n]>0?level_choices[save_levels[n]].name:"Empty Slot");frontend_entry(entries+row+2,line,0);}
   if(first>0)ui_text(0,-282,"[",TOMB_TEXT_CENTRE|TOMB_TEXT_BOTTOM);
   if(first+10<16)ui_text(0,-88,"]",TOMB_TEXT_CENTRE|TOMB_TEXT_BOTTOM);
  }
 }else if(i->object==95 || i->object==96){
  int detail=i->object==95,rows=detail?3:2;
  tomb_dialog_layout(i->object,detail?2-option_row:option_row,0,entries);
  frontend_entry(entries," ",0);frontend_entry(entries+1,detail?"Select Detail":"Set Volumes",0);
  for(int row=0;row<rows;row++){char line[40];if(detail)snprintf(line,sizeof line,"%s",row==0?"High":row==1?"Medium":"Low");else snprintf(line,sizeof line,"%c %2d",row==0?'|':'}',row==0?settings_music:settings_sound);frontend_entry(entries+row+2,line,0);}
 }else if(i->object==97){
  /* Preserve user bindings; DOS puts Look before Roll in its right column. */
  tomb_dialog_layout(97,option_row,0,entries);frontend_entry(entries," ",0);frontend_entry(entries+1,"User Keys",0);
  for(int row=0;row<13;row++){int b=frontend_binding_order[row];char key[40];frontend_key_name(bindings[b],key);frontend_entry(entries+2+row,binding_names[b],b==option_row && !binding_wait);frontend_entry(entries+15+row,binding_wait && b==option_row?"?":key,b==option_row && binding_wait);}
 }
 if(menu_error[0])ui_text(0,-45,menu_error,TOMB_TEXT_CENTRE|TOMB_TEXT_BOTTOM);
}
