/* Batch protocol: 16 little-endian 32-bit words, specified in tests/README.md.
   The protocol is independent of native C struct padding and endianness. */
#include "movement.h"
#include <stdio.h>
#include <string.h>

static uint32_t get32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
        (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static int16_t get16(const unsigned char *p)
{
    uint32_t low = get32(p) & UINT32_C(65535);
    return (int16_t)(low < 32768 ? (int32_t)low : (int32_t)low - 65536);
}
static void put32(unsigned char *p, uint32_t n)
{
    p[0] = (unsigned char)n; p[1] = (unsigned char)(n >> 8);
    p[2] = (unsigned char)(n >> 16); p[3] = (unsigned char)(n >> 24);
}

int main(int argc, char **argv)
{
    if (argc == 1) {
        TombMovement s = {0};
        s.health = 1000; s.input = 0x85; s.current_state = TOMB_STOP;
        tomb_movement_control(TOMB_STOP, &s);
        printf("Tomb Raider reconstructed C control demo\n"
               "Standing + forward + slow + left: goal=%d, turn=%d\n"
               "This is a control test program, not the playable game.\n",
               (int)s.goal_state, (int)s.turn_rate);
        return s.goal_state == TOMB_WALK && s.turn_rate == -409 ? 0 : 1;
    }
    if (argc != 4 || strcmp(argv[1], "--batch")) {
        fprintf(stderr, "Usage: movement_test.exe [--batch input.bin output.bin]\n");
        return 2;
    }
    FILE *input = fopen(argv[2], "rb");
    if (!input) { perror("input"); return 2; }
    FILE *output = fopen(argv[3], "wb");
    if (!output) { perror("output"); fclose(input); return 2; }
    unsigned char record[64];
    size_t count;
    int status = 0;
    while ((count = fread(record, 1, sizeof record, input)) != 0) {
        if (count != sizeof record) { status = 3; break; }
        TombMovement s = {0};
        uint32_t handler = get32(record);
        s.input = get32(record+4);
        s.health = get16(record+8); s.current_state = get16(record+12);
        s.goal_state = get16(record+16); s.animation = get16(record+20);
        s.frame = get16(record+24); s.turn_rate = get16(record+28);
        s.lean = get16(record+32); s.item_flags = (uint8_t)get32(record+36);
        s.weapon_status = get16(record+40); s.head_yaw = get16(record+44);
        s.head_pitch = get16(record+48); s.torso_yaw = get16(record+52);
        s.torso_pitch = get16(record+56); s.camera_mode = (uint8_t)get32(record+60);
        if (handler > 22 || !tomb_movement_control((enum TombControl)handler, &s)) {
            status = 4; break;
        }
        int16_t fields[] = {s.health, s.current_state, s.goal_state, s.animation,
            s.frame, s.turn_rate, s.lean, (int16_t)s.item_flags, s.weapon_status,
            s.head_yaw, s.head_pitch, s.torso_yaw, s.torso_pitch, (int16_t)s.camera_mode};
        for (size_t i = 0; i < sizeof fields / sizeof fields[0]; ++i)
            put32(record+8+4*i, (uint32_t)(int32_t)fields[i]);
        if (fwrite(record, 1, sizeof record, output) != sizeof record) { status = 5; break; }
    }
    if (ferror(input)) status = 5;
    if (fclose(input)) status = 5;
    if (fclose(output)) status = 5;
    if (status) fprintf(stderr, "Batch failed (%d).\n", status);
    return status;
}
