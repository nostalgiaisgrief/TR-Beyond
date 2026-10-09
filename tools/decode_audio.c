#define COBJMACROS
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <stdio.h>
#include <stdint.h>
static void u16(FILE *f,unsigned v){fputc(v&255,f);fputc(v>>8&255,f);}
static void u32(FILE *f,unsigned v){u16(f,v&65535);u16(f,v>>16);}
#define CHECK(x) do { HRESULT r=(x); if(FAILED(r)){fprintf(stderr,"line %d HRESULT %08lx\n",__LINE__,(unsigned long)r);return 1;} } while(0)
int main(int argc,char **argv){
 if(argc!=3)return 1;
 wchar_t input[32768];MultiByteToWideChar(CP_UTF8,0,argv[1],-1,input,32768);
 CHECK(CoInitializeEx(NULL,COINIT_MULTITHREADED));CHECK(MFStartup(MF_VERSION,MFSTARTUP_FULL));
 IMFSourceReader *reader=NULL;CHECK(MFCreateSourceReaderFromURL(input,NULL,&reader));
 CHECK(IMFSourceReader_SetStreamSelection(reader,MF_SOURCE_READER_ALL_STREAMS,FALSE));
 CHECK(IMFSourceReader_SetStreamSelection(reader,MF_SOURCE_READER_FIRST_AUDIO_STREAM,TRUE));
 IMFMediaType *type=NULL;CHECK(MFCreateMediaType(&type));
 CHECK(IMFMediaType_SetGUID(type,&MF_MT_MAJOR_TYPE,&MFMediaType_Audio));
 CHECK(IMFMediaType_SetGUID(type,&MF_MT_SUBTYPE,&MFAudioFormat_PCM));
 CHECK(IMFSourceReader_SetCurrentMediaType(reader,MF_SOURCE_READER_FIRST_AUDIO_STREAM,NULL,type));IMFMediaType_Release(type);
 CHECK(IMFSourceReader_GetCurrentMediaType(reader,MF_SOURCE_READER_FIRST_AUDIO_STREAM,&type));
 UINT32 channels,rate,bits;CHECK(IMFMediaType_GetUINT32(type,&MF_MT_AUDIO_NUM_CHANNELS,&channels));CHECK(IMFMediaType_GetUINT32(type,&MF_MT_AUDIO_SAMPLES_PER_SECOND,&rate));CHECK(IMFMediaType_GetUINT32(type,&MF_MT_AUDIO_BITS_PER_SAMPLE,&bits));IMFMediaType_Release(type);
 FILE *f=fopen(argv[2],"wb");if(!f)return 1;for(int i=0;i<44;i++)fputc(0,f);unsigned total=0;
 for(;;){DWORD flags=0;IMFSample *sample=NULL;LONGLONG time;
 CHECK(IMFSourceReader_ReadSample(reader,MF_SOURCE_READER_FIRST_AUDIO_STREAM,0,NULL,&flags,&time,&sample));
 if(sample){IMFMediaBuffer *buffer=NULL;BYTE *pcm;DWORD n;CHECK(IMFSample_ConvertToContiguousBuffer(sample,&buffer));CHECK(IMFMediaBuffer_Lock(buffer,&pcm,NULL,&n));if(fwrite(pcm,1,n,f)!=n)return 1;total+=n;CHECK(IMFMediaBuffer_Unlock(buffer));IMFMediaBuffer_Release(buffer);IMFSample_Release(sample);}
 if(flags&MF_SOURCE_READERF_ENDOFSTREAM)break;
 }
 rewind(f);fwrite("RIFF",1,4,f);u32(f,total+36);fwrite("WAVEfmt ",1,8,f);u32(f,16);u16(f,1);u16(f,channels);u32(f,rate);u32(f,rate*channels*bits/8);u16(f,channels*bits/8);u16(f,bits);fwrite("data",1,4,f);u32(f,total);fclose(f);
 IMFSourceReader_Release(reader);MFShutdown();CoUninitialize();printf("Decoded %u Hz, %u channels, %u bits, %.3f seconds\n",rate,channels,bits,(double)total/(rate*channels*bits/8));return 0;
}
