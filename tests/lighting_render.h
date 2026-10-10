/* Actual-driver check for all 8192 palette entries and masked texture indices. */
static int lighting_render_check(void){
    glViewport(0,0,256,32);glDisable(GL_DEPTH_TEST);glDisable(GL_ALPHA_TEST);glDisable(GL_SCISSOR_TEST);
    glMatrixMode(GL_PROJECTION);glLoadIdentity();glOrtho(0,256,0,32,-1,1);glMatrixMode(GL_MODELVIEW);glLoadIdentity();
    light_UseProgram(shade_program);light_ActiveTexture(0x84c1);glBindTexture(GL_TEXTURE_2D,tiles[visual->tile_count*2]);light_ActiveTexture(0x84c0);
    for(int i=0;i<256;i++){
        light_Uniform1i(shade_material,i);glBegin(GL_POINTS);
        for(int row=0;row<32;row++){glColor3f((row+.5f)/32,0,0);glVertex2f(i+.5f,row+.5f);}
        glEnd();
    }
    unsigned char pixels[256*32*3];glReadPixels(0,0,256,32,GL_RGB,GL_UNSIGNED_BYTE,pixels);
    const unsigned char *map=visual->level->file_data+visual->level->item_parsed_bytes;
    for(int i=0;i<8192;i++)for(int c=0;c<3;c++)if(pixels[i*3+c]!=visual->palette[map[i]*3+c]*255/63){
        fprintf(stderr,"Palette mismatch at %d channel %d: %d\n",i,c,pixels[i*3+c]);return 0;
    }
    glClearColor(1,0,1,1);glClear(GL_COLOR_BUFFER_BIT);glEnable(GL_ALPHA_TEST);glAlphaFunc(GL_GREATER,.5f);
    light_Uniform1i(shade_material,-1);glBindTexture(GL_TEXTURE_2D,tiles[visual->tile_count]);
    glBegin(GL_POINTS);
    for(int i=0;i<8192;i++){
        int row=i/256,x=i%256;glColor3f((row+.5f)/32,0,0);glTexCoord2f((x+.5f)/256,(row+.5f)/256);glVertex2f(x+.5f,row+.5f);
    }
    glEnd();glReadPixels(0,0,256,32,GL_RGB,GL_UNSIGNED_BYTE,pixels);
    for(int i=0;i<8192;i++)for(int c=0;c<3;c++){
        unsigned index=visual->tiles[i];int expected=index?visual->palette[map[(i/256)*256+index]*3+c]*255/63:(c==1?0:255);
        if(pixels[i*3+c]!=expected){fprintf(stderr,"Indexed texture mismatch at %d\n",i);return 0;}
    }
    /* Constant integer shades must stay constant across perspective triangles.
       Test exact row boundaries, rather than only the row centres above. */
    glDisable(GL_ALPHA_TEST);glMatrixMode(GL_PROJECTION);glLoadIdentity();
    for(int row=1;row<32;row++)for(int offset=-1;offset<=1;offset++){
        int index=0,best=-1;
        for(int k=0;k<256;k++){
            int difference=0;for(int c=0;c<3;c++)difference+=abs(visual->palette[map[row*256+k]*3+c]-visual->palette[map[(row-1)*256+k]*3+c]);
            if(difference>best){index=k;best=difference;}
        }
        int expected_row=offset<0?row-1:row;
        light_Uniform1i(shade_material,index);glColor3f((row*256+offset)/8192.f,0,0);
        glBegin(GL_QUADS);
        glVertex4f(-2,-2,0,2);glVertex4f(7,-7,0,7);glVertex4f(11,11,0,11);glVertex4f(-3,3,0,3);
        glEnd();glReadPixels(0,0,256,32,GL_RGB,GL_UNSIGNED_BYTE,pixels);
        int mismatches=0;
        for(int i=0;i<8192;i++)for(int c=0;c<3;c++)if(pixels[i*3+c]!=visual->palette[map[expected_row*256+index]*3+c]*255/63){mismatches++;break;}
        if(mismatches){fprintf(stderr,"Constant perspective shade %d: %d incorrect pixels (single non-overlapping quad)\n",row*256+offset,mismatches);return 0;}
    }
    light_UseProgram(0);if(glGetError()!=GL_NO_ERROR)return 0;
    puts("PASS: GPU palette/shade lookup, indexed transparency and 93 perspective boundary cases");return 1;
}
