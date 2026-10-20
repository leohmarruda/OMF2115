#include "source_replay.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static const char *trace_header_v1 =
    "tick,player,har,health,max_health,x,y,vx,vy,facing,state,move,animation,sprite,animation_tick";
static const char *trace_header_v2 =
    "tick,player,har,health,max_health,x,y,vx,vy,facing,state,move,animation,sprite,animation_tick,match_winner";
static const char *trace_header_v3 =
    "tick,player,har,health,max_health,x,y,vx,vy,facing,state,move,animation,sprite,animation_tick,match_winner,hit_mask,block_mask,round_winner";
static const char *trace_header_v4 =
    "tick,player,har,health,max_health,x,y,vx,vy,facing,state,move,animation,sprite,animation_tick,match_winner,hit_mask,block_mask,round_winner,projectiles";

static int read_projectiles(const char *field, SourceProjectile out[SOURCE_PROJECTILE_MAX], int *count) {
    *count = 0;
    if(strcmp(field, "-") == 0) return 1;
    while(*field && *count < SOURCE_PROJECTILE_MAX) {
        SourceProjectile *p = &out[*count];
        int used = 0;
        if(sscanf(field, "%d:%d:%d:%f:%f:%d%n", &p->owner, &p->animation,
                  &p->sprite, &p->x, &p->y, &p->facing, &used) != 6 || used == 0 ||
           p->owner < 0 || p->owner > 1 || p->animation < 0 || p->sprite < -1 ||
           !isfinite(p->x) || !isfinite(p->y) || (p->facing != -1 && p->facing != 1)) return 0;
        field += used;
        (*count)++;
        if(*field == '|') field++;
        else return *field == '\0';
    }
    return *field == '\0';
}

static int same_projectiles(const SourceFrame *frame, const SourceProjectile *projectiles, int count) {
    if(frame->projectile_count != count) return 0;
    for(int i = 0; i < count; i++) {
        const SourceProjectile *a = &frame->projectile[i], *b = &projectiles[i];
        if(a->owner != b->owner || a->animation != b->animation || a->sprite != b->sprite ||
           a->facing != b->facing || a->x != b->x || a->y != b->y) return 0;
    }
    return 1;
}

void source_replay_free(SourceReplay *replay) {
    free(replay->frames);
    replay->frames = NULL;
    replay->count = 0;
}

static int read_fighter(const char *line, int trace_version, uint32_t *tick, int *player,
                        SourceFighter *fighter, int *match_winner, int *hit_mask,
                        int *block_mask, int *round_winner,
                        SourceProjectile projectiles[SOURCE_PROJECTILE_MAX], int *projectile_count) {
    int used = 0;
    int fields;
    *hit_mask = 0;
    *block_mask = 0;
    *round_winner = -1;
    *projectile_count = 0;
    if(trace_version >= 3) {
        fields = sscanf(line, "%u,%d,%d,%d,%d,%f,%f,%f,%f,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d%n", tick, player,
                        &fighter->har, &fighter->health, &fighter->max_health, &fighter->x, &fighter->y,
                        &fighter->vx, &fighter->vy, &fighter->facing, &fighter->state, &fighter->move,
                        &fighter->animation, &fighter->sprite, &fighter->animation_tick, match_winner,
                        hit_mask, block_mask, round_winner, &used);
    } else if(trace_version == 2) {
        fields = sscanf(line, "%u,%d,%d,%d,%d,%f,%f,%f,%f,%d,%d,%d,%d,%d,%d,%d%n", tick, player,
                        &fighter->har, &fighter->health, &fighter->max_health, &fighter->x, &fighter->y,
                        &fighter->vx, &fighter->vy, &fighter->facing, &fighter->state, &fighter->move,
                        &fighter->animation, &fighter->sprite, &fighter->animation_tick, match_winner, &used);
    } else {
        *match_winner = -1;
        fields = sscanf(line, "%u,%d,%d,%d,%d,%f,%f,%f,%f,%d,%d,%d,%d,%d,%d%n", tick, player,
                        &fighter->har, &fighter->health, &fighter->max_health, &fighter->x, &fighter->y,
                        &fighter->vx, &fighter->vy, &fighter->facing, &fighter->state, &fighter->move,
                        &fighter->animation, &fighter->sprite, &fighter->animation_tick, &used);
    }
    return fields == (trace_version >= 3 ? 19 : trace_version == 2 ? 16 : 15) &&
           used > 0 && (trace_version == 4 ? line[used] == ',' &&
                        read_projectiles(line + used + 1, projectiles, projectile_count) :
                        line[used] == '\0') &&
            *match_winner >= -1 && *match_winner <= 1 && fighter->max_health > 0 &&
            *hit_mask >= 0 && *hit_mask <= 3 && *block_mask >= 0 && *block_mask <= 3 &&
            *round_winner >= -1 && *round_winner <= 1 &&
            /* Preserve source overkill values; the presentation clamps health to zero. */
            fighter->health <= fighter->max_health &&
            (fighter->facing == -1 || fighter->facing == 1);
}

int source_replay_load(const char *path, SourceReplay *replay, char *error, size_t error_size) {
    *replay = (SourceReplay){0};
    FILE *file = fopen(path, "r");
    if(!file) {
        snprintf(error, error_size, "Cannot open source trace: %s", path);
        return 0;
    }

    char line[512];
    size_t capacity = 0;
    unsigned long line_number = 0;
    int next_player = 0;
    if(!fgets(line, sizeof(line), file)) {
        snprintf(error, error_size, "Source trace is empty");
        goto fail;
    }
    line_number++;
    line[strcspn(line, "\r\n")] = '\0';
    int trace_version = strcmp(line, trace_header_v4) == 0 ? 4 :
                        strcmp(line, trace_header_v3) == 0 ? 3 :
                        strcmp(line, trace_header_v2) == 0 ? 2 :
                        strcmp(line, trace_header_v1) == 0 ? 1 : 0;
    if(!trace_version) {
        snprintf(error, error_size, "Source trace has an unexpected header");
        goto fail;
    }

    while(fgets(line, sizeof(line), file)) {
        line_number++;
        if(!strchr(line, '\n') && !feof(file)) {
            snprintf(error, error_size, "Source trace line %lu is too long", line_number);
            goto fail;
        }
        line[strcspn(line, "\r\n")] = '\0';
        SourceFighter fighter;
        SourceProjectile projectiles[SOURCE_PROJECTILE_MAX];
        uint32_t tick;
        int player, match_winner, hit_mask, block_mask, round_winner, projectile_count;
        if(!read_fighter(line, trace_version, &tick, &player, &fighter, &match_winner,
                         &hit_mask, &block_mask, &round_winner, projectiles, &projectile_count) ||
           player != next_player) {
            snprintf(error, error_size, "Invalid source trace row %lu", line_number);
            goto fail;
        }
        if(player == 0) {
            if(replay->count && tick != replay->frames[replay->count - 1].tick + 1) {
                snprintf(error, error_size, "Source trace has a missing or repeated tick at row %lu", line_number);
                goto fail;
            }
            if(replay->count == capacity) {
                if(capacity >= 1000000) {
                    snprintf(error, error_size, "Source trace exceeds one million frames");
                    goto fail;
                }
                size_t next_capacity = capacity ? capacity * 2 : 256;
                SourceFrame *frames = realloc(replay->frames, next_capacity * sizeof(*frames));
                if(!frames) {
                    snprintf(error, error_size, "Out of memory reading source trace");
                    goto fail;
                }
                replay->frames = frames;
                capacity = next_capacity;
            }
            replay->frames[replay->count].tick = tick;
            replay->frames[replay->count].fighter[0] = fighter;
            replay->frames[replay->count].match_winner = match_winner;
            replay->frames[replay->count].has_match_result = trace_version >= 2;
            replay->frames[replay->count].hit_mask = hit_mask;
            replay->frames[replay->count].block_mask = block_mask;
            replay->frames[replay->count].round_winner = round_winner;
            replay->frames[replay->count].has_events = trace_version >= 3;
            replay->frames[replay->count].projectile_count = projectile_count;
            memcpy(replay->frames[replay->count].projectile, projectiles,
                   (size_t)projectile_count * sizeof(*projectiles));
            next_player = 1;
        } else {
            if(tick != replay->frames[replay->count].tick ||
               match_winner != replay->frames[replay->count].match_winner ||
               hit_mask != replay->frames[replay->count].hit_mask ||
               block_mask != replay->frames[replay->count].block_mask ||
               round_winner != replay->frames[replay->count].round_winner ||
               !same_projectiles(&replay->frames[replay->count], projectiles, projectile_count)) {
                snprintf(error, error_size, "Mismatched source trace tick at row %lu", line_number);
                goto fail;
            }
            replay->frames[replay->count].fighter[1] = fighter;
            replay->count++;
            next_player = 0;
        }
    }
    if(ferror(file) || next_player || !replay->count) {
        snprintf(error, error_size, "Source trace ended with an incomplete fight frame");
        goto fail;
    }
    fclose(file);
    return 1;

fail:
    fclose(file);
    source_replay_free(replay);
    return 0;
}

size_t source_replay_find_tick(const SourceReplay *replay, uint32_t tick) {
    size_t low = 0, high = replay->count;
    while(low < high) {
        size_t mid = low + (high - low) / 2;
        if(replay->frames[mid].tick < tick) low = mid + 1;
        else high = mid;
    }
    return low < replay->count && replay->frames[low].tick == tick ? low : replay->count;
}

void source_replay_follow_close(SourceFollow *follow) {
    if(follow->file) fclose(follow->file);
    *follow = (SourceFollow){0};
}

int source_replay_follow_poll(const char *path, SourceReplay *replay, SourceFollow *follow,
                              char *error, size_t error_size) {
    char line[512];
    int added = 0;
    if(!follow->file) {
        follow->file = fopen(path, "r");
        if(!follow->file) return 0; // The match may not have started yet.
        if(!fgets(line, sizeof(line), follow->file)) {
            source_replay_follow_close(follow);
            return 0;
        }
        if(!strchr(line, '\n')) {
            source_replay_follow_close(follow);
            return 0;
        }
        line[strcspn(line, "\r\n")] = '\0';
        follow->trace_version = strcmp(line, trace_header_v4) == 0 ? 4 :
                                strcmp(line, trace_header_v3) == 0 ? 3 :
                                strcmp(line, trace_header_v2) == 0 ? 2 :
                                strcmp(line, trace_header_v1) == 0 ? 1 : 0;
        if(!follow->trace_version) {
            snprintf(error, error_size, "Live source trace has an unexpected header");
            return -1;
        }
        follow->line_number = 1;
    }
    clearerr(follow->file);
    for(;;) {
        if(follow->pending_length >= sizeof(follow->pending_line) - 1) {
            snprintf(error, error_size, "Live source trace row is too long");
            return -1;
        }
        char *row = follow->pending_line;
        char *piece = row + follow->pending_length;
        if(!fgets(piece, (int)(sizeof(follow->pending_line) - follow->pending_length), follow->file)) {
            if(ferror(follow->file)) {
                snprintf(error, error_size, "Cannot read live source trace");
                return -1;
            }
            clearerr(follow->file);
            break;
        }
        follow->pending_length += strlen(piece);
        if(!strchr(row, '\n')) {
            clearerr(follow->file);
            break; // Keep a partial row until the writer completes it.
        }
        follow->line_number++;
        row[strcspn(row, "\r\n")] = '\0';
        SourceFighter fighter;
        SourceProjectile projectiles[SOURCE_PROJECTILE_MAX];
        uint32_t tick;
        int player, match_winner, hit_mask, block_mask, round_winner, projectile_count;
        if(!read_fighter(row, follow->trace_version, &tick, &player, &fighter, &match_winner,
                         &hit_mask, &block_mask, &round_winner, projectiles, &projectile_count) ||
           player != follow->next_player) {
            snprintf(error, error_size, "Invalid live source trace row %lu", follow->line_number);
            return -1;
        }
        follow->pending_length = 0;
        row[0] = '\0';
        if(player == 0) {
            if(replay->count && tick != replay->frames[replay->count - 1].tick + 1) {
                snprintf(error, error_size, "Missing or repeated live source tick at row %lu", follow->line_number);
                return -1;
            }
            if(replay->count == follow->capacity) {
                if(follow->capacity >= 1000000) {
                    snprintf(error, error_size, "Live source trace exceeds one million frames");
                    return -1;
                }
                size_t next_capacity = follow->capacity ? follow->capacity * 2 : 256;
                SourceFrame *frames = realloc(replay->frames, next_capacity * sizeof(*frames));
                if(!frames) {
                    snprintf(error, error_size, "Out of memory following source trace");
                    return -1;
                }
                replay->frames = frames;
                follow->capacity = next_capacity;
            }
            replay->frames[replay->count].tick = tick;
            replay->frames[replay->count].fighter[0] = fighter;
            replay->frames[replay->count].match_winner = match_winner;
            replay->frames[replay->count].has_match_result = follow->trace_version >= 2;
            replay->frames[replay->count].hit_mask = hit_mask;
            replay->frames[replay->count].block_mask = block_mask;
            replay->frames[replay->count].round_winner = round_winner;
            replay->frames[replay->count].has_events = follow->trace_version >= 3;
            replay->frames[replay->count].projectile_count = projectile_count;
            memcpy(replay->frames[replay->count].projectile, projectiles,
                   (size_t)projectile_count * sizeof(*projectiles));
            follow->next_player = 1;
        } else {
            if(tick != replay->frames[replay->count].tick ||
               match_winner != replay->frames[replay->count].match_winner ||
               hit_mask != replay->frames[replay->count].hit_mask ||
               block_mask != replay->frames[replay->count].block_mask ||
               round_winner != replay->frames[replay->count].round_winner ||
               !same_projectiles(&replay->frames[replay->count], projectiles, projectile_count)) {
                snprintf(error, error_size, "Mismatched live source tick at row %lu", follow->line_number);
                return -1;
            }
            replay->frames[replay->count].fighter[1] = fighter;
            replay->count++;
            follow->next_player = 0;
            added = 1;
        }
    }
    return added;
}
