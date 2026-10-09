/* Independently reconstructed controllers: bat 0x11060, bear 0x111e8,
   wolf 0x3cdc4; head/tilt/turn 0x133c0..0x134fd. */
#include "creature.h"
#include "pistols.h"
#include "object_contact.h"
#include "fixed.h"
static int clamp(int n,int lo,int hi){return n<lo?lo:n>hi?hi:n;}
int16_t tomb_creature_turn(TombActor *a,const TombCreature *c,int16_t maximum) {
    if(!a->speed || !maximum)return 0;
    int32_t dx=c->target_x-a->x,dz=c->target_z-a->z;
    int16_t angle=tomb_word((int)tomb_object_angle(dz,dx)-a->yaw);
    int32_t radius=((int32_t)a->speed*16384)/maximum;
    if((angle>16384 || angle< -16384) && tomb_long((int64_t)dx*dx+(int64_t)dz*dz)<tomb_long((int64_t)radius*radius))maximum=tomb_word(tomb_asr(maximum,1));
    angle=(int16_t)clamp(angle,-maximum,maximum);a->yaw=tomb_word((int)a->yaw+angle);return angle;
}
TombCreatureDecision tomb_creature_control(TombObject *o,TombCreature *c,const TombCreatureInfo *i,int16_t turn,int16_t lara_health,uint32_t *random,const TombAnimContext *ctx) {
    TombActor *a=&o->actor;TombCreatureDecision d={0,turn,0,0};int head=c->health>0 && i->ahead?i->angle:0;
    if(o->object==9) {
        if(c->health<=0){d.turn=0;if(a->y<c->floor){a->goal=4;a->speed=0;a->flags|=8;}else{a->goal=5;a->flags&=(uint8_t)~8u;a->y=c->floor;}}
        else if(a->current==1)a->goal=2;
        else if(a->current==2){if(c->touch)a->goal=3;}
        else if(a->current==3){if(c->touch){d.damage=2;d.blood=1;}else{a->goal=2;c->mood=0;}}
        return d;
    }
    if(o->object==7) {
        if(c->health<=0) {
            d.turn=0;
            if(a->current!=11){a->animation=(int16_t)(192+tomb_control_random(random)/11000);a->frame=ctx->animations[a->animation].first_frame;a->current=11;}
        } else switch(a->current) {
        case 1:a->goal=c->required?c->required:2;break;
        case 2:c->maximum_turn=364;if(c->mood){a->goal=5;c->required=0;}else if(tomb_control_random(random)<32){c->required=8;a->goal=1;}break;
        case 3:c->maximum_turn=910;d.tilt=turn;
            if(i->ahead && i->distance<0x240000){if(i->distance>0x120000 && (i->enemy_facing>16384 || i->enemy_facing< -16384)){c->required=5;a->goal=9;}else{a->goal=6;c->required=0;}}
            else if(c->mood==3 && i->distance<0x900000){c->required=5;a->goal=9;}else if(!c->mood)a->goal=9;break;
        case 5:c->maximum_turn=364;
            if(c->mood==2)a->goal=3;
            else if(i->distance<0x1d0f1 && i->bite)a->goal=12;
            else if(i->distance>0x900000)a->goal=3;
            else if(c->mood==1){if(!i->ahead || i->distance>0x240000 || (i->enemy_facing<16384 && i->enemy_facing> -16384))a->goal=3;}
            else if(tomb_control_random(random)<384){c->required=7;a->goal=9;}else if(!c->mood)a->goal=9;break;
        case 6:d.tilt=turn;if(!c->required && (c->touch&0x774f)){d.damage=50;d.blood=1;c->required=3;}a->goal=3;break;
        case 8:head=0;if(c->mood==2 || i->zone==i->enemy_zone){c->required=9;a->goal=1;}else if(tomb_control_random(random)<32){c->required=2;a->goal=1;}break;
        case 9:if(c->required)a->goal=c->required;else if(c->mood==2)a->goal=3;else if(i->distance<0x1d0f1 && i->bite)a->goal=12;else if(c->mood==3)a->goal=5;else a->goal=c->mood?3:1;break;
        case 12:if(!c->required && (c->touch&0x774f) && i->ahead){d.damage=100;d.blood=1;c->required=9;}break;
        default:break;
        }
        c->roll=tomb_word((int)c->roll+clamp(tomb_word(4*d.tilt-c->roll),-546,546));
    } else if(o->object==8) {
        int touch=(c->touch&0x2406c)!=0,dead=lara_health<=0;
        if(c->health<=0) {
            switch(a->current){case 0:case 3:a->goal=1;break;case 1:c->flags=0;a->goal=9;break;case 2:a->goal=4;break;case 4:c->flags=1;a->goal=9;break;case 9:if(c->flags && touch){d.damage=200;c->flags=0;}break;default:break;}
        } else {
            if(a->flags&16)c->flags=1;
            switch(a->current) {
            case 0:c->maximum_turn=364;
                if(dead && touch && i->ahead)a->goal=1;
                else if(c->mood){a->goal=1;if(c->mood==2)c->required=0;}
                else if(tomb_control_random(random)<80){c->required=5;a->goal=1;}break;
            case 1:if(dead)a->goal=i->bite && i->distance<0x90000?8:0;else a->goal=c->required?c->required:c->mood?3:0;break;
            case 2:if(c->flags){c->required=0;a->goal=4;}
                else if(i->ahead && touch)a->goal=4;
                else if(c->mood==2){c->required=0;a->goal=4;}
                else if(!c->mood || tomb_control_random(random)<80){c->required=5;a->goal=4;}
                else if(i->distance>0x400000 || tomb_control_random(random)<1536){c->required=1;a->goal=4;}break;
            case 3:c->maximum_turn=910;if(touch)d.damage=3;
                if(!c->mood || dead)a->goal=1;
                else if(i->ahead && !c->required){if(!c->flags && i->distance<0x400000 && tomb_control_random(random)<768){c->required=4;a->goal=1;}else if(i->distance<0x100000)a->goal=6;}break;
            case 4:if(c->flags){c->required=0;a->goal=1;}else if(c->required)a->goal=c->required;else if(!c->mood || c->mood==2)a->goal=1;else a->goal=i->bite && i->distance<0x57e40?7:2;break;
            case 6:if(!c->required && touch){d.damage=200;d.blood=1;c->required=1;}break;
            case 7:if(!c->required && touch){d.damage=400;c->required=4;}break;
            default:break;
            }
        }
    }
    c->head=(int16_t)clamp(tomb_word((int)c->head+clamp(tomb_word(head-c->head),-910,910)),-16384,16384);
    return d;
}
