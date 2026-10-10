/* OpenGL compatibility shader: retain the PHD palette and 32 shade tables.
   Included by preview.c; all simulation-independent GPU state stays here. */
static GLuint shade_program;
static GLint shade_material;
#define GLFN(result,name,args) static result (APIENTRY *light_##name) args
GLFN(GLuint,CreateShader,(GLenum));
GLFN(void,ShaderSource,(GLuint,GLsizei,const char *const *,const GLint *));
GLFN(void,CompileShader,(GLuint));
GLFN(void,GetShaderiv,(GLuint,GLenum,GLint *));
GLFN(void,GetShaderInfoLog,(GLuint,GLsizei,GLsizei *,char *));
GLFN(GLuint,CreateProgram,(void));
GLFN(void,AttachShader,(GLuint,GLuint));
GLFN(void,LinkProgram,(GLuint));
GLFN(void,GetProgramiv,(GLuint,GLenum,GLint *));
GLFN(void,GetProgramInfoLog,(GLuint,GLsizei,GLsizei *,char *));
GLFN(void,DeleteShader,(GLuint));
GLFN(void,DeleteProgram,(GLuint));
GLFN(void,UseProgram,(GLuint));
GLFN(GLint,GetUniformLocation,(GLuint,const char *));
GLFN(void,Uniform1i,(GLint,GLint));
GLFN(void,ActiveTexture,(GLenum));
#undef GLFN
static int lighting_program(void){
    if(shade_program)return 1;
#define LOAD(name) do{PROC p=wglGetProcAddress("gl" #name);if(!p || (uintptr_t)p<=3 || (intptr_t)p==-1){fprintf(stderr,"OpenGL 2.0 lighting unavailable: gl%s\n",#name);return 0;}memcpy(&light_##name,&p,sizeof p);}while(0)
    LOAD(CreateShader);LOAD(ShaderSource);LOAD(CompileShader);LOAD(GetShaderiv);LOAD(GetShaderInfoLog);
    LOAD(CreateProgram);LOAD(AttachShader);LOAD(LinkProgram);LOAD(GetProgramiv);LOAD(GetProgramInfoLog);
    LOAD(DeleteShader);LOAD(DeleteProgram);LOAD(UseProgram);LOAD(GetUniformLocation);LOAD(Uniform1i);LOAD(ActiveTexture);
#undef LOAD
    const char *source[2]={
        "#version 110\nvarying float shade;void main(){gl_Position=ftransform();gl_TexCoord[0]=gl_MultiTexCoord0;shade=gl_Color.r;}",
        "#version 110\nuniform sampler2D indices;uniform sampler2D shades;uniform int material;varying float shade;"
        "void main(){float i=material<0?floor(texture2D(indices,gl_TexCoord[0].xy).r*255.0+0.5):float(material);"
        /* Perspective interpolation can put constant shades just below an exact
           palette boundary. Bias by 0.00256 shade units (one unit is 1/256 row),
           well below the original integer precision, before truncating. */
        "float row=clamp(floor(shade*32.0+0.00001),0.0,31.0);vec3 rgb=texture2D(shades,vec2((i+0.5)/256.0,(row+0.5)/32.0)).rgb;"
        "gl_FragColor=vec4(rgb,(material<0 && i<0.5)?0.0:1.0);}"};
    GLuint shaders[2]={0,0},program=light_CreateProgram();int ok=1;char log[2048];
    for(int i=0;i<2;i++){
        shaders[i]=light_CreateShader(i?0x8b30:0x8b31);light_ShaderSource(shaders[i],1,source+i,NULL);light_CompileShader(shaders[i]);
        GLint compiled=0;light_GetShaderiv(shaders[i],0x8b81,&compiled);
        if(!compiled){light_GetShaderInfoLog(shaders[i],sizeof log,NULL,log);fprintf(stderr,"Lighting shader: %s\n",log);ok=0;}
        light_AttachShader(program,shaders[i]);
    }
    light_LinkProgram(program);GLint linked=0;light_GetProgramiv(program,0x8b82,&linked);
    if(!linked){light_GetProgramInfoLog(program,sizeof log,NULL,log);fprintf(stderr,"Lighting link: %s\n",log);ok=0;}
    for(int i=0;i<2;i++)light_DeleteShader(shaders[i]);
    if(!ok){light_DeleteProgram(program);return 0;}
    shade_program=program;light_UseProgram(program);
    light_Uniform1i(light_GetUniformLocation(program,"indices"),0);light_Uniform1i(light_GetUniformLocation(program,"shades"),1);
    shade_material=light_GetUniformLocation(program,"material");light_UseProgram(0);return 1;
}
static void lighting_textures(void){
    for(size_t i=0;i<visual->tile_count;i++){
        glBindTexture(GL_TEXTURE_2D,tiles[visual->tile_count+i]);
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
        glTexImage2D(GL_TEXTURE_2D,0,GL_LUMINANCE8,256,256,0,GL_LUMINANCE,GL_UNSIGNED_BYTE,visual->tiles+i*65536);
    }
    unsigned char rgb[8192*3];const unsigned char *map=visual->level->file_data+visual->level->item_parsed_bytes;
    for(int i=0;i<8192;i++)for(int c=0;c<3;c++)rgb[3*i+c]=(unsigned char)(visual->palette[map[i]*3+c]*255/63);
    glBindTexture(GL_TEXTURE_2D,tiles[visual->tile_count*2]);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGB,256,32,0,GL_RGB,GL_UNSIGNED_BYTE,rgb);
}
static TombLighting model_light;
static GLdouble lighting_view[16];
static void light_in_view(void){
    int32_t world[3];memcpy(world,model_light.direction,sizeof world);
    for(int i=0;i<3;i++)model_light.direction[i]=(int32_t)(lighting_view[i]*world[0]+lighting_view[4+i]*world[1]+lighting_view[8+i]*world[2]);
}
static int lighting_depth(void){GLdouble m[16];glGetDoublev(GL_MODELVIEW_MATRIX,m);return (int)floor(-m[14]);}
static void actor_lighting(const TombActor *actor,const TombPose *pose,int intensity,int16_t pitch,int16_t roll){
    int depth=lighting_depth();
    if(intensity>=0){tomb_light_static(tomb_word(intensity),depth,&model_light);return;}
    int32_t centre[3],world[3];for(int i=0;i<3;i++)centre[i]=(pose->bounds[2*i]+pose->bounds[2*i+1])/2;
    tomb_rotate_vector(actor->yaw,pitch,roll,centre,0,sine_table,world);
    world[0]+=actor->x;world[1]+=actor->y;world[2]+=actor->z;
    tomb_light_room(visual->lighting+actor->room,world,depth,sine_table,&model_light);light_in_view();
}
