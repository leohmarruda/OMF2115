#ifndef OMF3K_LIVE_INPUT_H
#define OMF3K_LIVE_INPUT_H

#define OMF3K_LIVE_PROJECTILE_MAX 4

typedef struct {
    int owner, animation, sprite, facing;
    float x, y;
} Omf3kLiveProjectile;

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

typedef struct {
    volatile LONG action;
    volatile LONG heartbeat_ms;
    volatile LONG restart_requested;
} Omf3kLiveInput;

typedef struct {
    int har, health, max_health;
    float x, y, vx, vy;
    int facing, state, move, animation, sprite, animation_tick;
} Omf3kLiveFighter;

typedef struct {
    volatile LONG sequence;
    LONG tick;
    Omf3kLiveFighter fighter[2];
    LONG match_winner; // -1 until OpenOMF declares the match winner
    LONG hit_mask, block_mask; // bit per player, for this tick
    LONG round_winner; // -1 unless a round ended this tick
    LONG projectile_count;
    Omf3kLiveProjectile projectile[OMF3K_LIVE_PROJECTILE_MAX];
} Omf3kLiveState;
#endif

#endif
