#ifndef OMF3K_SOURCE_REPLAY_H
#define OMF3K_SOURCE_REPLAY_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

typedef struct {
    int har, health, max_health;
    float x, y, vx, vy;
    int facing, state, move, animation, sprite, animation_tick;
} SourceFighter;

#define SOURCE_PROJECTILE_MAX 4
typedef struct {
    int owner, animation, sprite, facing;
    float x, y;
} SourceProjectile;

typedef struct {
    uint32_t tick;
    SourceFighter fighter[2];
    int match_winner; // -1 until OpenOMF declares a match winner
    int has_match_result; // old trace files contain no match result field
    int hit_mask, block_mask, round_winner;
    int has_events; // v3 traces contain source event fields
    int projectile_count; // v4 traces contain up to four source projectiles
    SourceProjectile projectile[SOURCE_PROJECTILE_MAX];
} SourceFrame;

typedef struct {
    SourceFrame *frames;
    size_t count;
} SourceReplay;

typedef struct {
    FILE *file;
    size_t capacity;
    int next_player;
    int trace_version;
    unsigned long line_number;
    char pending_line[512];
    size_t pending_length;
} SourceFollow;

int source_replay_load(const char *path, SourceReplay *replay, char *error, size_t error_size);
void source_replay_free(SourceReplay *replay);
size_t source_replay_find_tick(const SourceReplay *replay, uint32_t tick);
/* Returns -1 on malformed input, 0 while waiting, or 1 when new frames arrive. */
int source_replay_follow_poll(const char *path, SourceReplay *replay, SourceFollow *follow,
                              char *error, size_t error_size);
void source_replay_follow_close(SourceFollow *follow);

#endif
