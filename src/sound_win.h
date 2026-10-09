#ifndef TOMB_SOUND_WIN_H
#define TOMB_SOUND_WIN_H
#include "sound.h"
typedef struct TombSoundOutput TombSoundOutput;
typedef struct TombSoundOutputStats { unsigned blocks,starvations,played_samples; } TombSoundOutputStats;
TombSoundOutput *tomb_sound_output_open(TombSoundMixer *);
int tomb_sound_output_update(TombSoundOutput *,int paused);
/* All mixer access while the output is open must pass through this lock. */
void tomb_sound_output_event(TombSoundOutput *,const TombSoundEvent *,int camera_wet,const double listener[3]);
TombSoundOutputStats tomb_sound_output_stats(TombSoundOutput *);
void tomb_sound_output_reset(TombSoundOutput *);
void tomb_sound_output_close(TombSoundOutput *);
void tomb_sound_output_volume(TombSoundOutput *,int);
#endif
