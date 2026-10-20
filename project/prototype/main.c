// Standalone, asset-free side-on 3D fighting spike for OpenOMF.
#define SDL_MAIN_HANDLED
#include <SDL.h>
#include <epoxy/gl.h>
#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <direct.h>
#else
#include <sys/stat.h>
#endif

#include "source_replay.h"
#include "live_input.h"
#include "pose_catalog.h"
#include "model_meshes.h"
#include "meshy_meshes.h"

#ifdef _WIN32
// Ask Optimus to start this executable on the discrete GPU. Windows graphics
// preferences can still override the request on newer Windows releases.
__declspec(dllexport) unsigned long NvOptimusEnablement = 1;
#endif

#define WIDTH 960
#define HEIGHT 600
#define DT (1.0f / 60.0f)
#define VERT_CAP 400000

typedef struct { float x, y, vy, facing, hp, max_hp, cooldown, attack, stun; int kind; bool hit, guard;
                 int source_state, source_animation, source_sprite, source_animation_tick;
                 float pose_height, pose_stride, pose_reach, pose_lean, pose_depth, presentation_x; } Fighter;
typedef struct { float x, y, z, r, g, b; } Vertex;
typedef struct { char ch; unsigned char rows[7]; } Glyph;

static Vertex vertices[VERT_CAP];
static int vertex_count;
static float camera_x;
static float camera_y;
static int phase; // 0 briefing, 1 fight, 2 victory, 3 defeat
static int try_again_choice; // 0 yes, 1 no
static int source_live_winner = -1;
static bool restart_live_match;
static Fighter player, rival;
static float elapsed;
static float source_visual_time;
static float live_round_intro_time;
static float live_impact_time;
static float live_impact_x;
static int live_impact_kind; // 1 hit, 2 block
static float rival_attack_delay;
static bool jump_was_down;
static int win_width = WIDTH, win_height = HEIGHT;
static SourceReplay source_replay;
static SourceFollow source_follow;
static size_t source_replay_index;
static bool source_replay_mode;
static bool source_follow_mode;
static const char *source_input_path;
static bool source_input_enabled;
static Uint64 source_follow_arrival;
#ifdef _WIN32
static HANDLE source_input_mapping;
static Omf3kLiveInput *source_shared_input;
static const char *source_state_map_name;
static HANDLE source_state_mapping;
static Omf3kLiveState *source_shared_state;
static size_t source_shared_capacity;
#endif
static bool source_replay_paused;
static float source_tick_seconds = .028f;
static bool model_preview_mode;
static int model_preview_view; // 0 right side, 1 front, 2 back
static int model_preview_pose; // idle, punch, kick, guard, crouch, walk, jump, hit, special
static const char *source_live_pilot_name;
static const char *source_live_rival_name;
static bool selection_mode;
static const char *selection_path;
static int selection_har;
static int selection_pilot;

static const char *selection_pilot_names[] = {
    "CRYSTAL", "STEFFAN", "MILANO", "CHRISTIAN", "SHIRRO",
    "JEANPAUL", "IBRAHIM", "ANGEL", "COSSETTE", "RAVEN"
};
static const char *selection_har_names[] = {"JAGUAR", "SHADOW"};

static bool write_selection(void) {
    if(!selection_path || !*selection_path) return false;
    FILE *file=fopen(selection_path,"w");
    if(!file) return false;
    fprintf(file,"har=%s\npilot=%s\n",selection_har_names[selection_har],
            selection_pilot_names[selection_pilot]);
    fclose(file);
    return true;
}

static void request_live_restart(void) {
    restart_live_match = true;
#ifdef _WIN32
    if(source_shared_input) InterlockedExchange(&source_shared_input->restart_requested, 1);
#endif
}

static const Glyph font[] = {
    {'A',{14,17,17,31,17,17,17}}, {'B',{30,17,17,30,17,17,30}},
    {'C',{14,17,16,16,16,17,14}}, {'D',{30,17,17,17,17,17,30}},
    {'E',{31,16,16,30,16,16,31}}, {'F',{31,16,16,30,16,16,16}},
    {'G',{14,17,16,23,17,17,14}}, {'H',{17,17,17,31,17,17,17}},
    {'I',{14,4,4,4,4,4,14}}, {'J',{7,2,2,2,18,18,12}},
    {'K',{17,18,20,24,20,18,17}}, {'L',{16,16,16,16,16,16,31}},
    {'M',{17,27,21,21,17,17,17}}, {'N',{17,25,21,19,17,17,17}},
    {'O',{14,17,17,17,17,17,14}}, {'P',{30,17,17,30,16,16,16}},
    {'Q',{14,17,17,17,21,18,13}}, {'R',{30,17,17,30,20,18,17}},
    {'S',{15,16,16,14,1,1,30}}, {'T',{31,4,4,4,4,4,4}},
    {'U',{17,17,17,17,17,17,14}}, {'V',{17,17,17,17,17,10,4}},
    {'W',{17,17,17,21,21,21,10}}, {'X',{17,17,10,4,10,17,17}},
    {'Y',{17,17,10,4,4,4,4}}, {'Z',{31,1,2,4,8,16,31}},
    {'0',{14,17,19,21,25,17,14}}, {'1',{4,12,4,4,4,4,14}},
    {'2',{14,17,1,2,4,8,31}}, {'3',{30,1,1,14,1,1,30}},
    {'4',{2,6,10,18,31,2,2}}, {'5',{31,16,30,1,1,17,14}},
    {'6',{6,8,16,30,17,17,14}}, {'7',{31,1,2,4,8,8,8}},
    {'8',{14,17,17,14,17,17,14}}, {'9',{14,17,17,15,1,2,12}},
    {':',{0,4,4,0,4,4,0}}, {'.',{0,0,0,0,0,12,12}},
    {'-',{0,0,0,31,0,0,0}}, {'/',{1,1,2,4,8,16,16}},
    {'!',{4,4,4,4,4,0,4}}, {'?',{14,17,1,2,4,0,4}},
    {' ',{0,0,0,0,0,0,0}}
};

static float clampf(float x, float a, float b) { return x < a ? a : (x > b ? b : x); }
static float distance_x(const Fighter *a, const Fighter *b) { return fabsf(a->x - b->x); }
static int facing_dir(const Fighter *f) { return f->facing < 0 ? 1 : -1; }
static bool source_standing_kick(int har, int animation) {
    return (har==0 && animation==41) || (har==1 && animation==42);
}
static bool source_standing_punch(int har, int animation) {
    return (har==0 && animation==42) || (har==1 && animation==43);
}
static bool source_close_contact_attack(int har, int animation) {
    return source_standing_punch(har,animation) || source_standing_kick(har,animation) ||
           (har==0 && animation==30) || (har==1 && animation==23);
}
static void reset_fight(void) {
    player = (Fighter){.x=-3.0f, .facing=-1.5707963f, .hp=100, .max_hp=100};
    rival = (Fighter){.x=3.0f, .facing=1.5707963f, .hp=100, .max_hp=100};
    elapsed = 0;
    rival_attack_delay = 2.5f;
    jump_was_down = false;
    try_again_choice = 0;
    phase = 1;
}
static void apply_source_fighter(Fighter *dest, const SourceFighter *source) {
    // OpenOMF's arena spans x=20..300 with a y=190 floor.
    // Match source screen spacing and apparent speed while allowing the
    // side-view meshes to fill the original sprites' horizontal silhouettes.
    const float x_scale = 7.6f / 280.0f, y_scale = 12.0f / 280.0f;
    dest->x = (source->x - 160.0f) * x_scale;
    dest->y = (190.0f - source->y) * y_scale;
    dest->vy = -source->vy * y_scale;
    dest->facing = source->facing == 1 ? -1.5707963f : 1.5707963f;
    dest->hp = fmaxf(0.0f, (float)source->health);
    dest->max_hp = (float)source->max_health;
    // Values mirror har.h states and animation.h's common animation IDs.
    dest->source_state = source->state;
    dest->source_animation = source->animation;
    dest->source_sprite = source->sprite;
    dest->source_animation_tick = source->animation_tick;
    dest->guard = source->state == 5 || source->state == 10 ||
                  source->animation == 5 || source->animation == 6;
    dest->stun = source->state == 7 || source->state == 9 || source->state == 10 ||
                 source->state == 12 ? 1.0f : 0.0f;
    bool kick=source_standing_kick(source->har,source->animation);
    bool punch=source_standing_punch(source->har,source->animation);
    dest->kind = kick ? 2 : 1;
    int duration = kick ? 15 : punch ? (source->har==0 ? 8 : 13) : 23;
    float progress = clampf((float)source->animation_tick / (float)duration,0,1);
    dest->attack = (kick || punch || source->animation == 20)
                       ? 1.0f : 0.0f;
    dest->pose_reach = dest->attack ? sinf(progress * 3.14159265f) : 0;
    const PoseFrame *pose=pose_catalog_lookup(source->har,source->animation,source->sprite);
    if(pose && (pose->flags&POSE_REACH)) dest->pose_reach=pose->reach;
    dest->pose_height = (source->state == 4 || source->state == 5 ||
                         source->animation == 4 || source->animation == 6) ? .68f : 1.0f;
    dest->pose_stride = (source->state == 2 || source->state == 3) ?
                         sinf((float)source->animation_tick * .75f) * .30f : 0;
}
static void apply_source_frame(size_t index) {
    const SourceFrame *frame = &source_replay.frames[index];
    source_replay_index = index;
    apply_source_fighter(&player, &frame->fighter[0]);
    apply_source_fighter(&rival, &frame->fighter[1]);
    if(frame->has_events && (frame->hit_mask || frame->block_mask)) {
        int hit=frame->hit_mask;
        int recipient=hit ? (hit&1 ? 0 : 1) : (frame->block_mask&1 ? 0 : 1);
        live_impact_x=recipient==0 ? player.x : rival.x;
        live_impact_kind=hit ? 1 : 2;
        live_impact_time=.20f;
    } else if(source_follow_mode && !frame->has_events && index>0) {
        const SourceFrame *previous=&source_replay.frames[index-1];
        if(frame->fighter[0].health<previous->fighter[0].health) {
            live_impact_x=player.x;
            live_impact_kind=1;
            live_impact_time=.20f;
        } else if(frame->fighter[1].health<previous->fighter[1].health) {
            live_impact_x=rival.x;
            live_impact_kind=1;
            live_impact_time=.20f;
        }
    }
    elapsed = frame->tick * source_tick_seconds;
    phase = 1;
    if(source_follow_mode && frame->has_match_result) {
        if(source_live_winner < 0 && frame->match_winner >= 0) {
            source_live_winner = frame->match_winner;
            try_again_choice = 0;
        } else if(restart_live_match && frame->match_winner < 0) {
            source_live_winner = -1;
            restart_live_match = false;
            try_again_choice = 0;
        }
    }
}
static void interpolate_live_fighters(Uint64 now, bool exact) {
    if(!source_follow_mode || source_replay_index == 0 || !source_follow_arrival) return;
    const SourceFrame *previous = &source_replay.frames[source_replay_index-1];
    const SourceFrame *current = &source_replay.frames[source_replay_index];
    float blend = exact ? 1.0f : clampf((float)((double)(now-source_follow_arrival) /
                  (double)SDL_GetPerformanceFrequency() / source_tick_seconds),0,1);
    Fighter before, after;
    apply_source_fighter(&before,&previous->fighter[0]);
    apply_source_fighter(&after,&current->fighter[0]);
    player.x=before.x+(after.x-before.x)*blend;
    player.y=before.y+(after.y-before.y)*blend;
    apply_source_fighter(&before,&previous->fighter[1]);
    apply_source_fighter(&after,&current->fighter[1]);
    rival.x=before.x+(after.x-before.x)*blend;
    rival.y=before.y+(after.y-before.y)*blend;
    elapsed=((float)previous->tick+blend)*source_tick_seconds;
}
static void write_source_input(const unsigned char *keys) {
    if(!source_input_enabled) return;
    static int last_action = -1;
    static Uint64 last_write_ms;
    // Match src/controller/controller.h ACT flags; OpenOMF owns all move logic.
    int action = 0;
    if(keys) {
        if(keys[SDL_SCANCODE_A] && !keys[SDL_SCANCODE_D]) action |= 0x20;
        if(keys[SDL_SCANCODE_D] && !keys[SDL_SCANCODE_A]) action |= 0x40;
        if(keys[SDL_SCANCODE_W] && !keys[SDL_SCANCODE_S]) action |= 0x08;
        if(keys[SDL_SCANCODE_S] && !keys[SDL_SCANCODE_W]) action |= 0x10;
        if(keys[SDL_SCANCODE_J]) action |= 0x04;
        if(keys[SDL_SCANCODE_K]) action |= 0x02;
    }
    action = action ? action : 1;
#ifdef _WIN32
    if(source_shared_input) {
        InterlockedExchange(&source_shared_input->action,action);
        InterlockedExchange(&source_shared_input->heartbeat_ms,(LONG)GetTickCount());
        return;
    }
#endif
    Uint64 now=SDL_GetTicks64();
    if(keys && action==last_action && now-last_write_ms<250) return;
    FILE *file=fopen(source_input_path,"w");
    if(file) {
        fprintf(file,"%lld %d\n",(long long)time(NULL),action);
        fclose(file);
        last_action=action;
        last_write_ms=now;
    }
}
#ifdef _WIN32
static int poll_shared_source_state(char *error, size_t error_size) {
    if(!source_shared_state) {
        source_state_mapping=OpenFileMappingA(FILE_MAP_ALL_ACCESS,FALSE,source_state_map_name);
        if(!source_state_mapping) return 0;
        source_shared_state=MapViewOfFile(source_state_mapping,FILE_MAP_ALL_ACCESS,0,0,sizeof(Omf3kLiveState));
        if(!source_shared_state) {
            CloseHandle(source_state_mapping);
            source_state_mapping=NULL;
            return 0;
        }
    }
    Omf3kLiveState snapshot;
    bool consistent=false;
    for(int attempt=0;attempt<3;attempt++) {
        LONG first=InterlockedCompareExchange(&source_shared_state->sequence,0,0);
        if(first&1) continue;
        MemoryBarrier();
        memcpy(&snapshot,(const void *)source_shared_state,sizeof(snapshot));
        MemoryBarrier();
        LONG second=InterlockedCompareExchange(&source_shared_state->sequence,0,0);
        if(first==second && !(second&1)) { consistent=true; break; }
    }
    if(!consistent || snapshot.fighter[0].max_health<=0 || snapshot.fighter[1].max_health<=0 ||
       snapshot.match_winner < -1 || snapshot.match_winner > 1 ||
       snapshot.hit_mask < 0 || snapshot.hit_mask > 3 ||
       snapshot.block_mask < 0 || snapshot.block_mask > 3 ||
       snapshot.round_winner < -1 || snapshot.round_winner > 1 ||
       snapshot.projectile_count < 0 ||
       snapshot.projectile_count > OMF3K_LIVE_PROJECTILE_MAX) return 0;
    uint32_t tick=(uint32_t)snapshot.tick;
    if(source_replay.count && tick<=source_replay.frames[source_replay.count-1].tick) {
        // After a requested rematch, a fresh arena may restart the source tick count.
        if(!restart_live_match || snapshot.match_winner>=0 ||
           tick==source_replay.frames[source_replay.count-1].tick) return 0;
        source_replay.count=0;
        source_replay_index=0;
        source_follow_arrival=0;
    }
    if(source_replay.count==source_shared_capacity) {
        if(source_shared_capacity>=1000000) {
            snprintf(error,error_size,"Live source state exceeds one million frames");
            return -1;
        }
        size_t next_capacity=source_shared_capacity ? source_shared_capacity*2 : 256;
        SourceFrame *frames=realloc(source_replay.frames,next_capacity*sizeof(*frames));
        if(!frames) {
            snprintf(error,error_size,"Out of memory reading live source state");
            return -1;
        }
        source_replay.frames=frames;
        source_shared_capacity=next_capacity;
    }
    _Static_assert(sizeof(SourceFighter)==sizeof(Omf3kLiveFighter),"Live fighter layout mismatch");
    SourceFrame *frame=&source_replay.frames[source_replay.count++];
    frame->tick=tick;
    memcpy(frame->fighter,snapshot.fighter,sizeof(frame->fighter));
    frame->match_winner=snapshot.match_winner;
    frame->has_match_result=1;
    frame->hit_mask=snapshot.hit_mask;
    frame->block_mask=snapshot.block_mask;
    frame->round_winner=snapshot.round_winner;
    frame->has_events=1;
    _Static_assert(sizeof(SourceProjectile)==sizeof(Omf3kLiveProjectile),"Live projectile layout mismatch");
    frame->projectile_count=snapshot.projectile_count;
    memcpy(frame->projectile,snapshot.projectile,
           (size_t)frame->projectile_count*sizeof(*frame->projectile));
    return 1;
}
#endif
static const char *source_har_name(int id) {
    static const char *names[] = {"JAGUAR", "SHADOW", "THORN", "PYROS", "ELECTRA", "KATANA",
                                  "SHREDDER", "FLAIL", "GARGOYLE", "CHRONOS", "NOVA"};
    return id >= 0 && id < (int)(sizeof(names) / sizeof(names[0])) ? names[id] : "HAR";
}
static void strike(Fighter *a, Fighter *b, int kind) {
    if(a->cooldown > 0 || a->stun > 0 || a->hp <= 0) return;
    a->kind = kind;
    a->attack = kind == 1 ? .27f : .44f;
    a->cooldown = kind == 1 ? .48f : .78f;
    a->hit = false;
    (void)b;
}
static void update_fighter(Fighter *a, Fighter *b, float move, bool jumping) {
    a->cooldown = fmaxf(0, a->cooldown - DT);
    a->stun = fmaxf(0, a->stun - DT);
    if(a->attack > 0) {
        a->attack = fmaxf(0, a->attack - DT);
        float active = a->kind == 1 ? .17f : .27f;
        if(!a->hit && a->attack <= active) {
            a->hit = true;
            float reach = a->kind == 1 ? 2.2f : 2.8f;
            if(distance_x(a, b) <= reach && fabsf(a->y-b->y) < 1.35f &&
               (b->x-a->x)*facing_dir(a) > 0 && b->hp > 0) {
                float damage = a == &player ? (a->kind == 1 ? 11.0f : 19.0f)
                                            : (a->kind == 1 ? 5.0f : 9.0f);
                if(b->guard) damage *= .2f;
                else b->stun = a->kind == 1 ? .22f : .38f;
                b->hp = fmaxf(0, b->hp - damage);
                b->x = clampf(b->x + facing_dir(a)*(b->guard ? .08f : .36f), -7.2f, 7.2f);
            }
        }
    }
    if(a->stun <= 0) {
        if(jumping && a->y <= 0 && a->vy <= 0) a->vy = 8.2f;
        // Jaguar's AF file lists forward/reverse speeds as 5/4. The world-unit
        // scale remains provisional until the source match is measured.
        float speed = a->attack > 0 ? 1.2f : (move * facing_dir(a) < 0 ? 3.52f : 4.4f);
        a->x = clampf(a->x + move * speed * DT, -7.2f, 7.2f);
    }
    a->y = fmaxf(0, a->y + a->vy * DT);
    a->vy = a->y > 0 ? a->vy - 22.0f * DT : 0;
    // Facing is discrete. Screen directions never depend on which side a HAR occupies.
    a->facing = a->x <= b->x ? -1.5707963f : 1.5707963f;
}
static void tick(const unsigned char *keys) {
    if(phase != 1) return;
    // Resolve facing before reading directional actions, including the tick
    // when a jumping fighter crosses to the other side.
    player.facing = player.x <= rival.x ? -1.5707963f : 1.5707963f;
    rival.facing = rival.x <= player.x ? -1.5707963f : 1.5707963f;
    elapsed += DT;
    rival_attack_delay = fmaxf(0, rival_attack_delay - DT);
    // Holding an attack repeats it when ready; a missed key press during
    // recovery no longer leaves the player standing still.
    if(keys[SDL_SCANCODE_K]) strike(&player, &rival, 2);
    else if(keys[SDL_SCANCODE_J]) strike(&player, &rival, 1);
    float move = (float)(keys[SDL_SCANCODE_D] != 0) - (float)(keys[SDL_SCANCODE_A] != 0);
    bool jump_down = keys[SDL_SCANCODE_W] != 0;
    bool jump = jump_down && !jump_was_down;
    jump_was_down = jump_down;
    float dist = distance_x(&player, &rival);
    float ai_move = dist > 1.9f ? (float)(player.x > rival.x ? 1 : -1) : 0;
    if(dist < 2.6f && rival_attack_delay <= 0 && rival.cooldown <= 0 && rival.stun <= 0) {
        strike(&rival, &player, ((int)(elapsed * 1.7f) % 3) == 0 ? 2 : 1);
        rival_attack_delay = 1.4f;
    }
    player.guard = move * facing_dir(&player) < 0 && !jump && player.y <= 0 &&
                   player.stun <= 0 && player.attack <= 0;
    // The placeholder AI can defend without the player input mapping.
    rival.guard = dist < 2.7f && player.attack > .12f &&
                  ((int)(elapsed * 1.5f) % 4 == 0) && rival.y <= 0 &&
                  rival.stun <= 0 && rival.attack <= 0;
    update_fighter(&player, &rival, move, jump);
    update_fighter(&rival, &player, ai_move, false);
    // Grounded bodies push apart; a jump can cross over an opponent.
    float dx = rival.x - player.x;
    if(fabsf(dx) < 1.05f && player.y < 1.0f && rival.y < 1.0f) {
        float side = dx >= 0 ? 1.0f : -1.0f;
        float push = (1.05f - fabsf(dx)) * .5f;
        player.x = clampf(player.x - side*push, -7.2f, 7.2f);
        rival.x = clampf(rival.x + side*push, -7.2f, 7.2f);
    }
    player.facing = player.x <= rival.x ? -1.5707963f : 1.5707963f;
    rival.facing = rival.x <= player.x ? -1.5707963f : 1.5707963f;
    if(rival.hp <= 0) phase = 2;
    if(player.hp <= 0) phase = 3;
}

static void vertex(float x, float y, float z, float r, float g, float b) {
    if(vertex_count < VERT_CAP) vertices[vertex_count++] = (Vertex){x,y,z,r,g,b};
    else {
        static bool warned;
        if(!warned) { warned=true; fprintf(stderr,"vertex buffer full (%d); geometry is being dropped\n",VERT_CAP); }
    }
}
static void projected(float x, float y, float z, float r, float g, float b) {
    // Fixed side-on camera. Depth adds only a small vertical offset for 3D staging.
    float aspect = (float)win_width / (float)win_height;
    if(model_preview_mode) {
        vertex(x*.96f/(3.5f*aspect), (y-1.61f)*.88f/2.15f,
               (.50f*(10.0f-y)+.84f*(17.0f-z))/40.0f, r,g,b);
        return;
    }
    float sx = (x - camera_x) * .96f / ((source_replay_mode ? 3.0f : 4.8f) * aspect);
    float sy = source_replay_mode ? ((y - camera_y) * .84f - z * .16f) / 4.6f - .10f
                                  : ((y - camera_y) * .84f - z * .16f) / 4.2f - .20f;
    float depth = (.12f * (camera_x - x) + .50f * (10.0f - y) + .84f * (17.0f - z)) / 40.0f;
    vertex(sx, sy, depth, r, g, b);
}
static void face(float a[3], float b[3], float c[3], float d[3], float rgb[3], float light) {
    projected(a[0],a[1],a[2],rgb[0]*light,rgb[1]*light,rgb[2]*light);
    projected(b[0],b[1],b[2],rgb[0]*light,rgb[1]*light,rgb[2]*light);
    projected(c[0],c[1],c[2],rgb[0]*light,rgb[1]*light,rgb[2]*light);
    projected(a[0],a[1],a[2],rgb[0]*light,rgb[1]*light,rgb[2]*light);
    projected(c[0],c[1],c[2],rgb[0]*light,rgb[1]*light,rgb[2]*light);
    projected(d[0],d[1],d[2],rgb[0]*light,rgb[1]*light,rgb[2]*light);
}
static void box(float x,float y,float z,float sx,float sy,float sz,float yaw,float r,float g,float b) {
    float p[8][3], rgb[3] = {r,g,b};
    float co = cosf(yaw), si = sinf(yaw);
    for(int i=0;i<8;i++) {
        float lx = (i&1 ? .5f : -.5f)*sx, ly = (i&2 ? .5f : -.5f)*sy;
        float lz = (i&4 ? .5f : -.5f)*sz;
        p[i][0]=x+lx*co+lz*si; p[i][1]=y+ly; p[i][2]=z-lx*si+lz*co;
    }
    face(p[0],p[4],p[6],p[2],rgb,.52f); // left
    face(p[1],p[3],p[7],p[5],rgb,.72f); // right
    face(p[0],p[1],p[5],p[4],rgb,.76f); // bottom
    face(p[2],p[6],p[7],p[3],rgb,1.15f); // top
    face(p[0],p[2],p[3],p[1],rgb,.86f); // front
    face(p[4],p[5],p[7],p[6],rgb,.62f); // rear
}
static void part(const Fighter *f,float x,float y,float z,float sx,float sy,float sz,float r,float g,float b) {
    float co=cosf(f->facing), si=sinf(f->facing);
    float height=f->pose_height > 0 ? f->pose_height : 1.0f;
    z-=f->pose_lean*(y-1.38f);
    box(f->x+x*co+z*si,y*height+f->y,-x*si+z*co,sx,sy*height,sz,f->facing,r,g,b);
}
static void tapered_part(const Fighter *f,float y,float bottom_w,float top_w,float bottom_d,float top_d,
                         float height,float r,float g,float b) {
    float p[8][3], rgb[3]={r,g,b}, co=cosf(f->facing), si=sinf(f->facing);
    for(int i=0;i<8;i++) {
        bool top=(i&2)!=0;
        float lx=(i&1 ? .5f : -.5f)*(top ? top_w : bottom_w);
        float lz=(i&4 ? .5f : -.5f)*(top ? top_d : bottom_d);
        lz-=f->pose_lean*(y+(top ? height*.5f : -height*.5f)-1.38f);
        p[i][0]=f->x+lx*co+lz*si;
        float pose_height=f->pose_height > 0 ? f->pose_height : 1.0f;
        p[i][1]=f->y+(y+(top ? height*.5f : -height*.5f))*pose_height;
        p[i][2]=-lx*si+lz*co;
    }
    face(p[0],p[4],p[6],p[2],rgb,.55f);
    face(p[1],p[3],p[7],p[5],rgb,.80f);
    face(p[0],p[1],p[5],p[4],rgb,.58f);
    face(p[2],p[6],p[7],p[3],rgb,1.22f);
    face(p[0],p[2],p[3],p[1],rgb,.96f);
    face(p[4],p[5],p[7],p[6],rgb,.68f);
}
static void ring(float x,float z,float inner,float outer,float r,float g,float b) {
    for(int i=0;i<24;i++) {
        float a=(float)i*6.2831853f/24.0f, next=(float)(i+1)*6.2831853f/24.0f;
        float x0=x+cosf(a)*inner,z0=z+sinf(a)*inner;
        float x1=x+cosf(a)*outer,z1=z+sinf(a)*outer;
        float x2=x+cosf(next)*outer,z2=z+sinf(next)*outer;
        float x3=x+cosf(next)*inner,z3=z+sinf(next)*inner;
        projected(x0,.026f,z0,r,g,b); projected(x1,.026f,z1,r,g,b); projected(x2,.026f,z2,r,g,b);
        projected(x0,.026f,z0,r,g,b); projected(x2,.026f,z2,r,g,b); projected(x3,.026f,z3,r,g,b);
    }
}
static void robot_placeholder(Fighter *f, float r, float g, float b, float t) {
    float bob = f->stun > 0 ? -.13f : sinf(t * 4.0f) * .025f;
    float punch = f->source_animation ? f->pose_reach :
                  (f->attack > 0 ? (f->kind == 2 ? .78f : .56f) : 0);
    float kick = f->source_animation && f->kind == 2 ? punch : 0;
    float arm_reach = kick ? 0 : punch;
    float recoil = f->source_animation && f->stun > 0 ? .22f : 0;
    float armor = f->stun > 0 ? 1.35f : 1.0f;
    // Broad torso, narrow waist, separated armor plates and bright core.
    part(f,0,1.45f+bob,.02f,.76f,.43f,.52f,r*.40f,g*.48f,b*.53f);
    tapered_part(f,1.96f+bob,.80f,1.20f,.48f,.72f,.82f,r*armor,g*armor,b*armor);
    part(f,0,2.03f+bob,-.36f,.68f,.46f,.08f,r*.82f,g*.88f,b*.95f);
    part(f,0,2.10f+bob,-.43f,.30f,.27f,.06f,.97f,.84f,.45f);
    part(f,0,2.56f+bob,.01f,.28f,.24f,.30f,.15f,.22f,.33f);
    tapered_part(f,2.86f+bob,.65f,.48f,.54f,.41f,.48f,r*.8f,g*.85f,b*.9f);
    part(f,0,2.89f+bob,-.31f,.46f,.13f,.08f,.73f,.96f,1.0f);
    part(f,0,3.17f+bob,.03f,.32f,.15f,.42f,r*.57f,g*.63f,b*.69f);
    for(int side=-1;side<=1;side+=2) {
        float s=(float)side;
        float stride=f->pose_stride*s;
        float leg_kick=side == 1 ? kick : 0;
        part(f,s*.38f,.90f+bob,.04f-stride*.28f-leg_kick*.15f,.38f,.93f,.50f,r*.55f,g*.60f,b*.68f);
        part(f,s*.40f,.40f+bob,-.08f-stride*.55f-leg_kick*.60f,.43f,.61f,.53f,r*.81f,g*.85f,b*.88f);
        part(f,s*.41f,.13f+bob+leg_kick*.36f,-.22f-stride-leg_kick*1.08f,.56f,.22f,.77f,r*.48f,g*.53f,b*.61f);
        part(f,s*.73f,2.30f+bob,.01f,.58f,.32f,.74f,r*1.08f,g*1.08f,b*1.08f);
        float strike_arm=side == 1 ? arm_reach : 0;
        float guard_arm=f->guard ? .40f : 0;
        part(f,s*.73f,1.88f+bob,-.10f-strike_arm*.33f-guard_arm*.25f+recoil,.34f,.71f,.40f,r*.52f,g*.61f,b*.70f);
        part(f,s*.74f,1.44f+bob+guard_arm*.90f+strike_arm*.30f,
             -.22f-strike_arm*.90f-guard_arm*.60f+recoil,.41f,.48f,.53f,r*.88f,g*.94f,b);
        part(f,s*.74f,1.50f+bob+guard_arm*.90f+strike_arm*.30f,
             -.51f-strike_arm*1.12f-guard_arm*.60f+recoil,.30f,.20f,.08f,.88f,.93f,1.0f);
        part(f,s*.87f,2.57f+bob,.20f,.20f,.45f,.37f,r*.64f,g*.70f,b*.76f);
    }
    if(f->guard) {
        part(f,0,1.92f+bob,-.77f,1.26f,.64f,.07f,.19f,.55f,.75f);
        part(f,0,1.92f+bob,-.82f,1.12f,.53f,.035f,.60f,.93f,1.0f);
    }
    if(f->attack > 0) part(f,0,1.52f+bob+kick*.20f,-1.12f-punch*.65f,
                            .52f,.08f,.12f,1.0f,.85f,.48f);
}
typedef struct { float y,z; } RigPoint;
typedef struct { RigPoint shoulder,elbow,wrist,hip,knee,ankle; } RigSide;

static RigPoint rig_map(RigPoint p,RigPoint from_a,RigPoint from_b,
                        RigPoint to_a,RigPoint to_b) {
    float sy=from_b.y-from_a.y, sz=from_b.z-from_a.z;
    float ty=to_b.y-to_a.y, tz=to_b.z-to_a.z;
    float source_len=hypotf(sy,sz), target_len=hypotf(ty,tz);
    if(source_len<.0001f || target_len<.0001f) return p;
    float along=((p.y-from_a.y)*sy+(p.z-from_a.z)*sz)/source_len;
    float across=((p.y-from_a.y)*(-sz)+(p.z-from_a.z)*sy)/source_len;
    return (RigPoint){to_a.y+along*ty/source_len+across*(-tz)/target_len,
                      to_a.z+along*tz/source_len+across*ty/target_len};
}

// Tilt a rig point about the torso pivot (height 1.38, depth 0) by atan(lean): positive leans the
// top toward the opponent (negative z). Rotating, not shearing, keeps the torso its length at the
// large tilts of dives and rolls; for small leans it matches the old shear.
static RigPoint lean_rotate(float y,float z,float lean) {
    float theta=atanf(lean), s=sinf(theta), c=cosf(theta), h=y-1.38f;
    return (RigPoint){1.38f+h*c+z*s, z*c-h*s};
}

static void model_rig_sides(const Fighter *f,int har,float t,RigSide sides[2],
                            float *body_drop,float *body_lean,float *body_shift) {
    const PoseFrame *pose=pose_catalog_lookup(har,f->source_animation,f->source_sprite);
    // Keep the authored long-range silhouette, but fold the striking limb
    // toward a nearby opponent so it does not pass through their torso.
    float contact_distance=0;
    bool contact_pose=false;
    if(source_replay_mode && (f==&player || f==&rival)) {
        const Fighter *opponent=f==&player ? &rival : &player;
        float source_dx=opponent->x-f->x;
        float presentation_dx=(opponent->x+opponent->presentation_x)-
                              (f->x+f->presentation_x);
        contact_pose=source_dx*facing_dir(f)>=0;
        contact_distance=fabsf(presentation_dx);
    }
    float crouch=clampf((1.0f-(f->pose_height>0 ? f->pose_height : 1.0f))/.32f,0,1);
    float bob=f->stun>0 ? -.12f : sinf(t*4.0f)*.018f;
    float reach=f->source_animation ? f->pose_reach :
                (f->attack>0 ? (f->kind==2 ? .78f : .56f) : 0);
    float kick=f->source_animation ? (f->kind==2 ? reach : 0) :
               (f->attack>0 && f->kind==2 ? reach : 0);
    float arm_reach=kick ? 0 : reach;
    float recoil=f->source_animation && f->stun>0 ? .18f : 0;
    *body_drop=bob-crouch*.52f;
    // An authored body height replaces the state-derived crouch drop. Arm joint heights are
    // relative to it, leg joint heights are absolute.
    if(pose && (pose->flags&POSE_DROP)) *body_drop=bob+pose->body_y;
    *body_shift=pose && (pose->flags&POSE_BODY) ? pose->body_z : 0;
    *body_lean=har==0 && f->source_animation==30 && pose ?
                    .05f+.43f*pose->reach : 0;
    float shadow_punch_lunge=0;
    if(har==1 && f->source_animation==23 && pose) {
        // Shadow Punch starts with an extended arm; animate the body and legs to carry its source-keyed lunge.
        static const float lunge_by_sprite[]={.58f,.92f,.74f,.48f,.24f,0.0f};
        if(f->source_sprite>=0 && f->source_sprite<6)
            shadow_punch_lunge=lunge_by_sprite[f->source_sprite];
        *body_drop-=.16f*shadow_punch_lunge;
        *body_lean=.30f*shadow_punch_lunge;
    }
    // An authored lean (from the pose editor's two-point axis) overrides the hard-coded ones above.
    if(pose && (pose->flags&POSE_LEAN)) *body_lean=pose->lean;
    for(int i=0;i<2;i++) {
        int side=i==0 ? -1 : 1;
        float stride=f->pose_stride*(float)side;
        float leg_kick=side==1 ? kick : 0;
        float arm_forward=side==1 ? arm_reach : 0;
        float guard=f->guard ? .37f : 0;
        RigSide *r=&sides[i];
        r->hip=(RigPoint){1.38f+*body_drop,.02f+crouch*.10f+*body_shift};
        r->knee=(RigPoint){.57f+bob-crouch*.04f+leg_kick*.44f,
                           -.02f-crouch*.38f-stride*.32f-leg_kick*.55f};
        r->ankle=(RigPoint){.18f+bob+leg_kick*.92f,
                            -.03f-stride*.82f-leg_kick*1.28f};
        if(pose && (pose->flags&POSE_LEG) && side==pose->side) {
            r->knee=(RigPoint){pose->knee_y+bob,pose->knee_z};
            r->ankle=(RigPoint){pose->ankle_y+bob,pose->ankle_z};
            if(contact_pose && source_standing_kick(har,f->source_animation) &&
               pose->reach>.5f) {
                float ankle_z=-clampf(contact_distance-.50f,.28f,-pose->ankle_z);
                float fold=ankle_z-pose->ankle_z;
                r->ankle.z=ankle_z;
                r->knee.z+=fold*.35f;
            }
        } else if(pose && (pose->flags&POSE_LEG2) && side!=pose->side) {
            // The other leg, fitted from the same source sprite: planted, trailing, or bracing.
            r->knee=(RigPoint){pose->knee2_y+bob,pose->knee2_z};
            r->ankle=(RigPoint){pose->ankle2_y+bob,pose->ankle2_z};
        } else if(f->source_state==6 || f->y>.25f) {
            // Both robots tuck the near knee and draw the far foot underneath.
            r->knee.y+=side==1 ? .38f : .19f;
            r->knee.z+=side==1 ? -.27f : .24f;
            r->ankle.y+=side==1 ? .48f : .31f;
            r->ankle.z+=side==1 ? -.12f : .20f;
        }
        if(har==0 && f->source_animation==30 && pose) {
            float lunge=pose->reach;
            r->knee=(RigPoint){(side==1 ? .75f+.30f*lunge : .57f)+bob,
                                side==1 ? -.15f-.55f*lunge : .12f+.48f*lunge};
            r->ankle=(RigPoint){.18f+bob,
                                 side==1 ? -.15f-.35f*lunge : .15f+.85f*lunge};
        }
        if(shadow_punch_lunge>0) {
            float spread=.30f+.90f*shadow_punch_lunge;
            float leg_y=.68f-.10f*shadow_punch_lunge;
            r->knee=(RigPoint){leg_y+bob,side==1 ? -.38f-spread*.42f : .24f+spread*.42f};
            r->ankle=(RigPoint){.16f+bob,side==1 ? -.62f-spread : .62f+spread};
        }
        // The shoulder follows the torso lean (pivot 1.38, as in model_transform).
        RigPoint shoulder=lean_rotate(2.38f,0,*body_lean);
        r->shoulder=(RigPoint){shoulder.y+*body_drop,shoulder.z+*body_shift};
        r->elbow=(RigPoint){1.77f+*body_drop+guard*.27f+arm_forward*.20f,
                            -.10f-arm_forward*.37f-guard*.28f+recoil};
        r->wrist=(RigPoint){1.38f+*body_drop+guard*1.55f+arm_forward*.55f,
                            -.24f-arm_forward*1.04f-guard*.60f+recoil};
        if(pose && (pose->flags&POSE_ARM) && side==pose->side) {
            r->elbow=(RigPoint){pose->elbow_y+*body_drop,pose->elbow_z+recoil};
            r->wrist=(RigPoint){pose->wrist_y+*body_drop,pose->wrist_z+recoil};
            if(contact_pose && (source_standing_punch(har,f->source_animation) ||
                                (har==0 && f->source_animation==30)) &&
               pose->reach>.5f) {
                float wrist_z=-clampf(contact_distance-.20f,.38f,-pose->wrist_z);
                float fold=wrist_z-pose->wrist_z;
                r->wrist.z=wrist_z+recoil;
                r->elbow.z+=fold*.45f;
            }
        } else if(pose && (pose->flags&POSE_ARM2) && side!=pose->side) {
            // The other arm, fitted from the same source sprite.
            r->elbow=(RigPoint){pose->elbow2_y+*body_drop,pose->elbow2_z+recoil};
            r->wrist=(RigPoint){pose->wrist2_y+*body_drop,pose->wrist2_z+recoil};
        } else if(f->stun>0 && !f->guard) {
            r->elbow.y+=side==1 ? .35f : .20f;
            r->elbow.z+=.18f;
            r->wrist.y+=side==1 ? .70f : .28f;
            r->wrist.z+=side==1 ? .31f : .42f;
        }
    }
}

static void model_transform(const Fighter *f,int har,const ModelPart *part,
                            const RigSide sides[2],float body_drop,float body_lean,float body_shift,
                            ModelPosition source,float out[3]) {
    RigPoint p={source.y,source.z};
    const RigSide *r=&sides[part->side==1 ? 1 : 0];
    if(part->group==0 || part->group==1 || part->group==2) {
        RigPoint tilted=lean_rotate(source.y,source.z,body_lean);
        p.y=tilted.y+body_drop;
        p.z=tilted.z+body_shift;
    } else {
        float shoulder_y=har==0 ? 2.24f : 2.25f;
        float elbow_y=har==0 ? 1.76f : 1.77f;
        float wrist_y=har==0 ? 1.13f : 1.11f;
        float hip_y=har==0 ? 1.30f : 1.27f;
        float knee_y=har==0 ? .75f : .76f;
        float ankle_y=har==0 ? .23f : .24f;
        switch(part->group) {
        case 3: p=rig_map(p,(RigPoint){shoulder_y,0},(RigPoint){elbow_y,-.02f},
                          r->shoulder,r->elbow); break;
        case 4: case 5:
            p=rig_map(p,(RigPoint){elbow_y,-.02f},(RigPoint){wrist_y,-.08f},
                      r->elbow,r->wrist); break;
        case 6: p=rig_map(p,(RigPoint){hip_y,0},(RigPoint){knee_y,har==0 ? -.01f : 0},
                          r->hip,r->knee); break;
        case 7: p=rig_map(p,(RigPoint){knee_y,har==0 ? -.01f : 0},
                          (RigPoint){ankle_y,-.02f},r->knee,r->ankle); break;
        case 8: p.y+=r->ankle.y-ankle_y; p.z+=r->ankle.z+.02f; break;
        }
    }
    float co=cosf(f->facing), si=sinf(f->facing);
    out[0]=f->x+f->presentation_x+source.x*co+p.z*si;
    out[1]=f->y+p.y;
    out[2]=-source.x*si+p.z*co+f->pose_depth;
}

// OMF3K_MESHY=1 swaps the blockouts for the decimated Meshy meshes: the Robot Mascot
// for Jaguar and the Rocket Jester for Shadow.
static bool use_meshy_model(void) {
    static int enabled=-1;
    if(enabled<0) {
        const char *v=getenv("OMF3K_MESHY");
        enabled=v && v[0] && v[0]!='0';
    }
    return enabled;
}

static void robot_loaded_model(Fighter *f,int har,float t,bool projection) {
    RigSide sides[2];
    float body_drop,body_lean,body_shift;
    model_rig_sides(f,har,t,sides,&body_drop,&body_lean,&body_shift);
    bool meshy=use_meshy_model();
    const ModelPart *parts=model_parts;
    const ModelPosition *positions=model_positions;
    const uint16_t *indices=model_indices;
    const ModelBlend *blend=NULL;
    size_t part_count=sizeof(model_parts)/sizeof(model_parts[0]);
    if(meshy && har==0) {
        parts=meshy_parts; positions=meshy_positions; indices=meshy_indices; blend=meshy_blend;
        part_count=sizeof(meshy_parts)/sizeof(meshy_parts[0]);
    } else if(meshy && har==1) {
        parts=jester_parts; positions=jester_positions; indices=jester_indices; blend=jester_blend;
        part_count=sizeof(jester_parts)/sizeof(jester_parts[0]);
    }
    for(size_t i=0;i<part_count;i++) {
        const ModelPart *part=&parts[i];
        if(part->har!=har) continue;
        for(unsigned j=part->first;j<part->first+part->count;j+=3) {
            float p[3][3];
            for(int k=0;k<3;k++) {
                unsigned vi=indices[j+k];
                model_transform(f,har,part,sides,body_drop,body_lean,body_shift,positions[vi],p[k]);
                // Vertices near a joint also follow the neighbouring group, which closes the seam.
                if(blend && blend[vi].weight) {
                    ModelPart other=*part;
                    other.group=blend[vi].group;
                    other.side=blend[vi].side;
                    float q[3],w=blend[vi].weight/255.0f;
                    model_transform(f,har,&other,sides,body_drop,body_lean,body_shift,positions[vi],q);
                    for(int a=0;a<3;a++) p[k][a]+=(q[a]-p[k][a])*w;
                }
            }
            float ux=p[1][0]-p[0][0], uy=p[1][1]-p[0][1], uz=p[1][2]-p[0][2];
            float vx=p[2][0]-p[0][0], vy=p[2][1]-p[0][1], vz=p[2][2]-p[0][2];
            float nx=uy*vz-uz*vy, ny=uz*vx-ux*vz, nz=ux*vy-uy*vx;
            float length=sqrtf(nx*nx+ny*ny+nz*nz);
            if(length<.00001f) continue;
            // Broad overhead light, with a cool edge that separates the armor plates.
            float top=fmaxf(0,ny/length);
            float side=fabsf(nz/length);
            float edge=fabsf(nx/length);
            float shade=clampf(.63f+.30f*top+.20f*side+.13f*edge,.60f,1.14f);
            float red=part->r/255.0f, green=part->g/255.0f, blue=part->b/255.0f;
            if(projection) {
                float bright=fmaxf(red,fmaxf(green,blue));
                if(green>red*1.5f) { red=.54f; green=.94f; blue=1.0f; }
                else if(bright<.25f) { red=.15f; green=.10f; blue=.34f; }
                else { red=.48f; green=.36f; blue=.86f; }
                shade=clampf(shade+.12f,.72f,1.25f);
            }
            for(int k=0;k<3;k++)
                projected(p[k][0],p[k][1],p[k][2],
                          red*shade,green*shade,blue*shade);
        }
    }
}

static void source_shadow_punch_effect(const Fighter *f,int har) {
    if(!source_replay_mode || har!=1 || f->source_animation!=23 ||
       f->source_sprite<0 || f->source_sprite>2) return;
    float direction=(float)facing_dir(f);
    float pulse=f->source_sprite==1 ? 1.0f : f->source_sprite==0 ? .78f : .88f;
    float x=f->x+f->presentation_x+direction*(1.58f+.12f*(float)f->source_sprite);
    float y=f->y+2.18f-.10f*(float)f->source_sprite;
    float z=.35f;
    box(x,y,z,.32f*pulse,.30f*pulse,.72f*pulse,f->facing,.04f,.48f,.70f);
    box(x+direction*.10f,y+.02f,z,.23f*pulse,.22f*pulse,.62f*pulse,f->facing,
        .10f,.78f,.95f);
    box(x+direction*.20f,y+.03f,z,.12f*pulse,.13f*pulse,.43f*pulse,f->facing,
        .76f,.98f,1.0f);
}
static void robot(Fighter *f, int har, float t) {
    if(har==0 || har==1) {
        robot_loaded_model(f,har,t,false);
        source_shadow_punch_effect(f,har);
    }
    else robot_placeholder(f,.56f,.61f,.68f,t);
}
static void source_projectiles(void) {
    if(!source_replay_mode || !source_replay.count) return;
    const SourceFrame *frame=&source_replay.frames[source_replay_index];
    for(int i=0;i<frame->projectile_count;i++) {
        const SourceProjectile *p=&frame->projectile[i];
        if(p->sprite<0) continue;
        float x=(p->x-160.0f)*(7.6f/280.0f);
        float y=(190.0f-p->y)*(12.0f/280.0f);
        if(p->owner<0 || p->owner>1) continue;
        int har=frame->fighter[p->owner].har;
        if(har==0 && (p->animation==38 || p->animation==37)) {
            float size=p->animation==37 ? .43f : .28f;
            float direction=p->facing>=0 ? 1.0f : -1.0f;
            float yaw=p->facing>=0 ? -1.5707963f : 1.5707963f;
            for(int trail=3;trail>=1;trail--)
                box(x-direction*(size*.45f+trail*.16f),y,0,
                    size*(.34f-trail*.06f),size*(.42f-trail*.08f),size*(.82f-trail*.13f),yaw,
                    .08f,.36f+trail*.08f,.48f+trail*.08f);
            box(x,y,0,size*.54f,size*.72f,size*1.48f,yaw,.08f,.42f,.68f);
            box(x+direction*size*.06f,y,0,size*.34f,size*.48f,size*1.30f,yaw,.20f,.74f,.96f);
            box(x+direction*size*.12f,y,0,size*.16f,size*.25f,size*1.08f,yaw,.85f,1.0f,1.0f);
        } else if(har==1 && (p->animation==54 || p->animation==60)) {
            Fighter ghost={.x=x,.y=y,.facing=p->facing>=0 ? -1.5707963f : 1.5707963f,
                           .pose_height=1,.pose_depth=.55f};
            ring(x,0,.48f,.55f,.34f,.24f,.74f);
            robot_loaded_model(&ghost,1,source_visual_time,true);
        }
    }
}
static void stadium_background(void) {
    static const float crowd_colors[][3] = {
        {.11f,.21f,.31f}, {.20f,.27f,.39f}, {.32f,.18f,.24f},
        {.27f,.34f,.39f}, {.40f,.29f,.18f}, {.13f,.31f,.29f}
    };
    const int crowd_color_count=(int)(sizeof(crowd_colors)/sizeof(crowd_colors[0]));

    // Roof and continuous back wall enclose the arena like a large indoor bowl.
    box(0,2.75f,-8.05f,19.0f,5.5f,.28f,0,.025f,.045f,.075f);
    box(0,4.23f,-7.55f,18.8f,.20f,.62f,0,.12f,.18f,.28f);
    box(0,3.98f,-7.18f,17.8f,.08f,.16f,0,.20f,.54f,.63f);
    box(0,3.80f,-6.98f,16.6f,.045f,.08f,0,.42f,.68f,.72f);
    for(int i=-4;i<=4;i++) {
        float x=(float)i*2.0f;
        box(x,3.33f,-7.45f,.10f,1.22f,.16f,0,.12f,.24f,.34f);
        box(x,3.93f,-7.10f,.45f,.10f,.48f,0,.19f,.28f,.36f);
    }

    // Stepped seating tiers and abstract spectator silhouettes use only new geometry.
    for(int row=0;row<4;row++) {
        float y=1.12f+(float)row*.43f;
        float z=-6.95f-(float)row*.19f;
        box(0,y-.15f,z,17.6f,.24f,.68f,0,.075f,.11f,.18f);
        box(0,y-.005f,z+.63f,17.5f,.055f,.08f,0,.17f,.32f,.39f);
        for(int column=0;column<36;column++) {
            float x=-8.25f+(float)column*.47f+(row%2 ? .23f : 0.0f);
            int color=(column*7+row*11+(column/3))%crowd_color_count;
            const float *c=crowd_colors[color];
            box(x,y+.055f,z+.45f,.25f,.30f,.14f,0,c[0],c[1],c[2]);
            box(x,y+.305f,z+.45f,.16f,.16f,.14f,0,
                clampf(c[0]+.12f,.10f,.52f),clampf(c[1]+.12f,.12f,.55f),clampf(c[2]+.12f,.14f,.60f));
        }
    }

    // A central arena board and high perimeter lights identify the venue.
    box(0,3.38f,-6.48f,3.35f,.76f,.20f,0,.025f,.055f,.095f);
    box(0,3.38f,-6.35f,3.05f,.52f,.035f,0,.055f,.12f,.18f);
    box(-1.10f,3.39f,-6.30f,.54f,.17f,.025f,0,.18f,.72f,.86f);
    box(-.36f,3.39f,-6.30f,.54f,.17f,.025f,0,.18f,.72f,.86f);
    box(.38f,3.39f,-6.30f,.54f,.17f,.025f,0,.92f,.30f,.44f);
    box(1.12f,3.39f,-6.30f,.54f,.17f,.025f,0,.92f,.30f,.44f);
    box(0,2.86f,-6.18f,8.4f,.045f,.08f,0,.26f,.60f,.64f);
}
static void quad(float x,float y,float w,float h,float r,float g,float b) {
    float x2=x+w,y2=y+h;
    vertex(x,y,-.99f,r,g,b); vertex(x2,y,-.99f,r,g,b); vertex(x2,y2,-.99f,r,g,b);
    vertex(x,y,-.99f,r,g,b); vertex(x2,y2,-.99f,r,g,b); vertex(x,y2,-.99f,r,g,b);
}
static const unsigned char *glyph(char ch) {
    for(size_t i=0;i<sizeof(font)/sizeof(font[0]);i++) if(font[i].ch==ch) return font[i].rows;
    return font[sizeof(font)/sizeof(font[0])-1].rows;
}
static void label(float x,float y,float size,const char *s,float r,float g,float b) {
    for(;*s;s++,x+=size*6.0f) {
        const unsigned char *rows=glyph(*s);
        for(int row=0;row<7;row++) for(int col=0;col<5;col++)
            if(rows[row] & (1 << (4-col))) quad(x+col*size,y-row*size,size*.85f,size*.85f,r,g,b);
    }
}

static void selection_hud(void) {
    quad(-1,-1,2,2,.015f,.025f,.065f);
    quad(-.78f,.62f,1.56f,.20f,.04f,.10f,.18f);
    label(-.70f,.71f,.018f,"OMF2115 / CHOOSE YOUR FIGHTER",.65f,.92f,1);
    label(-.72f,.43f,.012f,"UP DOWN ROBOT",.55f,.70f,.84f);
    label(-.72f,.34f,.012f,"LEFT RIGHT PILOT",.55f,.70f,.84f);
    label(-.72f,.18f,.011f,"ROBOT",.48f,.60f,.72f);
    label(-.72f,.05f,.020f,selection_har_names[selection_har],.30f,.90f,1);
    label(.12f,.18f,.011f,"PILOT",.48f,.60f,.72f);
    label(.12f,.05f,.020f,selection_pilot_names[selection_pilot],1,.72f,.79f);
    quad(-.78f,-.20f,1.56f,.035f,.12f,.18f,.25f);
    quad(-.78f,-.20f,.78f,.035f,.16f,.83f,.94f);
    label(-.72f,-.42f,.013f,"ENTER START MATCH",.70f,.90f,.96f);
    label(-.72f,-.54f,.011f,"ESC CANCEL",.55f,.70f,.84f);
}
static void world(void) {
    if(model_preview_mode) {
        const float angle=model_preview_view==0 ? -1.5707963f :
                          model_preview_view==1 ? 3.14159265f : 0.0f;
        Fighter jaguar={.x=-1.55f,.facing=angle,.pose_height=1};
        Fighter shadow={.x=1.55f,.facing=angle,.pose_height=1};
        if(model_preview_pose==1 || model_preview_pose==2) {
            jaguar.source_animation=model_preview_pose==1 ? 42 : 41;
            shadow.source_animation=model_preview_pose==1 ? 43 : 42;
            jaguar.pose_reach=shadow.pose_reach=.9f;
            jaguar.kind=shadow.kind=model_preview_pose==2 ? 2 : 1;
            jaguar.source_sprite=3;
            shadow.source_sprite=model_preview_pose==1 ? 2 : 3;
        } else if(model_preview_pose==3) {
            jaguar.guard=shadow.guard=true;
        } else if(model_preview_pose==4) {
            jaguar.pose_height=shadow.pose_height=.68f;
        } else if(model_preview_pose==5) {
            jaguar.pose_stride=shadow.pose_stride=.28f;
        } else if(model_preview_pose==6) {
            jaguar.y=shadow.y=.72f;
            jaguar.source_state=shadow.source_state=6;
        } else if(model_preview_pose==7) {
            jaguar.stun=shadow.stun=1;
            jaguar.source_state=shadow.source_state=7;
        } else if(model_preview_pose==8) {
            jaguar.source_animation=21;
            shadow.source_animation=23;
            jaguar.source_sprite=3;
            shadow.source_sprite=2;
        }
        box(0,-.10f,0,7.0f,.12f,1.8f,0,.10f,.14f,.19f);
        box(-1.55f,.005f,0,1.3f,.012f,.03f,0,.15f,.46f,.30f);
        box(1.55f,.005f,0,1.3f,.012f,.03f,0,.15f,.46f,.30f);
        robot(&jaguar,0,0);
        robot(&shadow,1,0);
        return;
    }
    camera_x = source_replay_mode ? 0 : (player.x+rival.x)*.5f;
    camera_y = source_replay_mode ? clampf(fmaxf(player.y, rival.y) * .90f, 0, 2.9f) : 0;
    player.presentation_x = 0;
    rival.presentation_x = 0;
    if(source_replay_mode && source_replay.count) {
        const SourceFrame *frame=&source_replay.frames[source_replay_index];
        int player_har=frame->fighter[0].har;
        int rival_har=frame->fighter[1].har;
        float player_reach=source_close_contact_attack(player_har,player.source_animation) ? player.pose_reach : 0;
        float rival_reach=source_close_contact_attack(rival_har,rival.source_animation) ? rival.pose_reach : 0;
        float engagement=fmaxf(player_reach,rival_reach);
        float source_distance=distance_x(&player,&rival);
        float vertical_distance=fabsf(player.y-rival.y);
        if(engagement>.35f && vertical_distance<1.25f && source_distance<1.20f) {
            // Separate overlapping blockout torsos only during source-keyed contact poses.
            // Source positions, hit results, and projectile locations remain unchanged.
            float blend=clampf((engagement-.35f)/.65f,0,1);
            float offset=(1.20f-source_distance)*.5f*blend;
            if(player.x<=rival.x) {
                player.presentation_x=-offset;
                rival.presentation_x=offset;
            } else {
                player.presentation_x=offset;
                rival.presentation_x=-offset;
            }
        }
    }
    stadium_background();
    box(0,-.28f,0,17.0f,.42f,8.0f,0,.065f,.105f,.16f);
    box(0,-.045f,0,15.1f,.045f,6.5f,0,.10f,.16f,.24f);
    for(int i=-8;i<=8;i+=2) box((float)i,.002f,0,.027f,.012f,7.7f,0,.12f,.29f,.38f);
    for(int i=-4;i<=4;i+=2) box(0,.005f,(float)i,16.5f,.012f,.027f,0,.12f,.29f,.38f);
    box(0,.035f,0,.055f,.02f,7.7f,0,.21f,.63f,.70f);
    box(0,.035f,0,16.5f,.02f,.055f,0,.21f,.63f,.70f);
    ring(0,0,2.55f,2.60f,.20f,.43f,.53f);
    ring(0,0,3.50f,3.54f,.12f,.26f,.35f);
    for(int i=-4;i<=4;i+=2) {
        box(-8.3f,.57f,(float)i,.28f,1.13f,.28f,0,.18f,.44f,.56f);
        box(8.3f,.57f,(float)i,.28f,1.13f,.28f,0,.18f,.44f,.56f);
        box(-8.3f,1.18f,(float)i,.37f,.12f,.37f,0,.50f,.91f,.99f);
        box(8.3f,1.18f,(float)i,.37f,.12f,.37f,0,.50f,.91f,.99f);
    }
    box(0,.68f,4.2f,17,.08f,.12f,0,.22f,.63f,.73f);
    box(0,.68f,-4.2f,17,.08f,.12f,0,.22f,.63f,.73f);
    // The front apron gives the arena a visible edge below the fight plane.
    box(0,-1.38f,4.18f,17.0f,2.65f,.35f,0,.045f,.075f,.125f);
    box(0,-.16f,4.39f,17.0f,.12f,.08f,0,.15f,.37f,.46f);
    box(0,-2.53f,4.39f,17.0f,.12f,.08f,0,.12f,.25f,.34f);
    for(int i=-7;i<=7;i+=2) {
        float x=(float)i;
        box(x,-1.34f,4.40f,1.56f,1.74f,.035f,0,.075f,.12f,.19f);
        box(x,-.77f,4.44f,1.12f,.045f,.025f,0,.17f,.42f,.48f);
        box(x,-1.03f,4.44f,.86f,.035f,.025f,0,.11f,.27f,.34f);
        box(x,-1.30f,4.44f,.62f,.035f,.025f,0,.11f,.27f,.34f);
    }
    ring(player.x,0,.65f,.72f,.12f,.58f,.72f);
    ring(rival.x,0,.65f,.72f,.72f,.17f,.34f);
    if(source_replay_mode && live_impact_time>0) {
        float progress=1.0f-live_impact_time/.20f;
        float radius=.62f+progress*.62f;
        float brightness=1.0f-progress*.72f;
        if(live_impact_kind==2)
            ring(live_impact_x,0,radius,radius+.09f,brightness*.30f,brightness*.86f,brightness);
        else
            ring(live_impact_x,0,radius,radius+.09f,brightness,brightness*.79f,brightness*.32f);
    }
    float pose_time=source_follow_mode ? source_visual_time : elapsed;
    int player_har=source_replay_mode && source_replay.count ?
                   source_replay.frames[source_replay_index].fighter[0].har : 0;
    int rival_har=source_replay_mode && source_replay.count ?
                  source_replay.frames[source_replay_index].fighter[1].har : 1;
    robot(&player,player_har,pose_time);
    robot(&rival,rival_har,pose_time+1);
    source_projectiles();
}
static void hud(void) {
    if(model_preview_mode) {
        const char *view=model_preview_view==0 ? "RIGHT SIDE" :
                         model_preview_view==1 ? "FRONT" : "BACK";
        const char *pose[]={"IDLE","PUNCH","KICK","GUARD","CROUCH",
                            "WALK","JUMP","HIT","SPECIAL"};
        quad(-1,.80f,2,.20f,.02f,.04f,.10f);
        label(-.92f,.94f,.014f,"OMF2115 / MODEL BLOCKOUTS",.72f,.90f,1);
        label(-.92f,.85f,.012f,view,.60f,.95f,.67f);
        label(-.12f,.85f,.012f,pose[model_preview_pose],.60f,.95f,.67f);
        label(-.67f,-.64f,.015f,"JAGUAR",.80f,.87f,.94f);
        label(.24f,-.64f,.015f,"SHADOW",.80f,.87f,.94f);
        label(-.92f,-.76f,.009f,"8 WALK  9 JUMP  H HIT  M SPECIAL",.57f,.65f,.72f);
        label(-.92f,-.84f,.009f,"1 SIDE  2 FRONT  3 BACK  0 IDLE",.57f,.65f,.72f);
        label(-.92f,-.92f,.0085f,"4 PUNCH  5 KICK  6 GUARD  7 CROUCH",.57f,.65f,.72f);
        return;
    }
    quad(-1,.83f,2,.17f,.02f,.04f,.10f);
    label(-.94f,.95f,.0145f,source_follow_mode ? "OMF2115 / LIVE SOURCE" :
          (source_replay_mode ? "OMF2115 / SOURCE REPLAY" : "OMF2115 / SIDE ON SPIKE"),
          .62f,.89f,.96f);
    if(phase==1) {
        quad(-.94f,.78f,.78f,.035f,.14f,.18f,.25f);
        quad(-.94f,.78f,.78f*player.hp/player.max_hp,.035f,.16f,.83f,.94f);
        quad(.16f,.78f,.78f,.035f,.14f,.18f,.25f);
        quad(.16f,.78f,.78f*rival.hp/rival.max_hp,.035f,.94f,.30f,.47f);
        if(source_replay_mode) {
            char left[48], right[48];
            const SourceFrame *frame = &source_replay.frames[source_replay_index];
            const char *left_name = source_follow_mode && source_live_pilot_name ?
                                    source_live_pilot_name : source_har_name(frame->fighter[0].har);
            const char *right_name = source_follow_mode && source_live_rival_name ?
                                     source_live_rival_name : source_har_name(frame->fighter[1].har);
            snprintf(left,sizeof(left),"%s %d",left_name,
                     frame->fighter[0].health > 0 ? frame->fighter[0].health : 0);
            snprintf(right,sizeof(right),"%s %d",right_name,
                     frame->fighter[1].health > 0 ? frame->fighter[1].health : 0);
            label(-.94f,.72f,.011f,left,.72f,.90f,1);
            label(.16f,.72f,.011f,right,1,.72f,.79f);
        } else {
            const char *left = source_follow_mode && source_live_pilot_name ? source_live_pilot_name : "JAGUAR";
            const char *right = source_follow_mode && source_live_rival_name ? source_live_rival_name : "SHADOW";
            label(-.94f,.72f,.013f,left,.72f,.90f,1);
            label(.37f,.72f,.013f,right,1,.72f,.79f);
        }
        quad(-1,-1,2,.26f,.02f,.04f,.10f);
        label(-.94f,-.79f,.011f,source_input_enabled ? "A D MOVE  W JUMP  S DUCK" :
              (source_follow_mode ? "LIVE OPENOMF MATCH  ESC QUIT" :
              (source_replay_mode ? "SPACE PAUSE  LEFT RIGHT STEP" : "A D MOVE  W JUMP  J PUNCH")),
              .78f,.84f,.91f);
        if(source_replay_mode) {
            char replay_footer[64];
            snprintf(replay_footer,sizeof(replay_footer),source_input_enabled ? "J PUNCH  K KICK  TICK %u" :
                     (source_follow_mode ? "SOURCE TICK %u" :
                     "R RESTART  ESC QUIT  TICK %u"),
                     source_replay.frames[source_replay_index].tick);
            label(-.94f,-.91f,.011f,replay_footer,.78f,.84f,.91f);
        } else {
            label(-.94f,-.91f,.011f,"K KICK  HOLD BACK TO BLOCK",.78f,.84f,.91f);
        }
        if(source_replay_mode && source_replay.count) {
            const SourceFrame *frame=&source_replay.frames[source_replay_index];
            bool player_down=frame->fighter[0].health<=0;
            bool rival_down=frame->fighter[1].health<=0;
            bool match_decided=frame->has_match_result && frame->match_winner>=0;
            bool round_decided=frame->has_events && frame->round_winner>=0;
            if(source_follow_mode && source_live_winner >= 0) {
                const char *result=source_live_winner==0 ? "YOU WIN" : "YOU LOSE";
                float result_x=-(float)strlen(result)*.022f*3.0f;
                quad(-.67f,-.02f,1.34f,.72f,.025f,.045f,.10f);
                label(result_x,.25f,.022f,result,
                      source_live_winner==0?.67f:1.0f,
                      source_live_winner==0?.95f:.58f,
                      source_live_winner==0?.77f:.63f);
                label(-.68f,.10f,.015f,"TRY AGAIN?",.85f,.9f,.96f);
                label(-.40f,-.08f,.018f,"YES",try_again_choice==0?.38f:.48f,
                      try_again_choice==0?.92f:.55f,try_again_choice==0?1.0f:.64f);
                label(.12f,-.08f,.018f,"NO",try_again_choice==1?.38f:.48f,
                      try_again_choice==1?.92f:.55f,try_again_choice==1?1.0f:.64f);
                label(-.59f,-.23f,.009f,"LEFT/RIGHT SELECT  ENTER CONFIRM",.57f,.70f,.80f);
            } else if(match_decided || round_decided || player_down || rival_down) {
                bool player_won=match_decided ? frame->match_winner==0 :
                                round_decided ? frame->round_winner==0 : rival_down && !player_down;
                const char *result=match_decided ? (player_won ? "YOU WIN" : "YOU LOSE") :
                                   !round_decided && player_down && rival_down ? "ROUND DRAW" :
                                   player_won ? "ROUND WON" : "ROUND LOST";
                float size=match_decided ? .022f : .018f;
                float result_x=-(float)strlen(result)*size*3.0f;
                quad(-.67f,-.22f,1.34f,.48f,.025f,.045f,.10f);
                label(result_x,.14f,size,result,
                      player_won ? .67f : 1.0f,
                      player_won ? .95f : .58f,
                      player_won ? .77f : .63f);
                label(-.37f,-.08f,.012f,"PLAYER 1",.80f,.88f,.94f);
            }
        }
        if(source_follow_mode && live_round_intro_time>0) {
            const char *intro=live_round_intro_time>.75f ? "ROUND 1" : "FIGHT";
            float size=live_round_intro_time>.75f ? .026f : .030f;
            quad(-.65f,-.15f,1.30f,.34f,.025f,.045f,.10f);
            label(-(float)strlen(intro)*size*3.0f,.09f,size,intro,.72f,.95f,1.0f);
        }
    } else {
        quad(-.78f,-.39f,1.56f,.65f,.025f,.045f,.10f);
        if(phase==0) {
            label(-.68f,.15f,.021f,"OMF2115",.74f,.94f,1);
            label(-.68f,.00f,.015f,source_follow_mode ? "LIVE SOURCE VIEW" :
                  "SIDE ON FIGHTING SPIKE",.85f,.9f,.96f);
            label(-.68f,-.11f,.015f,source_follow_mode ? "STARTING OPENOMF MATCH" :
                  "DEFEAT THE RIVAL FRAME.",.85f,.9f,.96f);
            label(-.68f,-.28f,.017f,source_follow_mode ? "ESC TO QUIT" :
                  "ENTER TO DEPLOY",.38f,.88f,.98f);
        } else if(phase==2) {
            label(-.68f,.15f,.021f,"YOU WIN",.74f,.94f,1);
            label(-.68f,.04f,.015f,"TRY AGAIN?",.85f,.9f,.96f);
            label(-.40f,-.12f,.018f,"YES",try_again_choice==0?.38f:.48f,
                  try_again_choice==0?.92f:.55f,try_again_choice==0?1.0f:.64f);
            label(.12f,-.12f,.018f,"NO",try_again_choice==1?.38f:.48f,
                  try_again_choice==1?.92f:.55f,try_again_choice==1?1.0f:.64f);
            label(-.68f,-.24f,.009f,"LEFT/RIGHT SELECT  ENTER CONFIRM",.57f,.70f,.80f);
        } else {
            label(-.68f,.15f,.021f,"YOU LOSE",1,.52f,.62f);
            label(-.68f,.04f,.015f,"TRY AGAIN?",.85f,.9f,.96f);
            label(-.40f,-.12f,.018f,"YES",try_again_choice==0?.38f:.48f,
                  try_again_choice==0?.92f:.55f,try_again_choice==0?1.0f:.64f);
            label(.12f,-.12f,.018f,"NO",try_again_choice==1?.38f:.48f,
                  try_again_choice==1?.92f:.55f,try_again_choice==1?1.0f:.64f);
            label(-.68f,-.24f,.009f,"LEFT/RIGHT SELECT  ENTER CONFIRM",.57f,.70f,.80f);
        }
    }
}
static GLuint make_shader(GLenum type,const char *source) {
    GLuint s=glCreateShader(type); glShaderSource(s,1,&source,NULL); glCompileShader(s);
    GLint ok=0; glGetShaderiv(s,GL_COMPILE_STATUS,&ok);
    if(!ok) { char log[1024]; glGetShaderInfoLog(s,sizeof(log),NULL,log); fprintf(stderr,"Shader: %s\n",log); exit(1); }
    return s;
}
// Captures go to project/build, next to the files the OMF2115 tools generate, not into OpenOMF's build tree.
static void ensure_capture_dir(void) {
#ifdef _WIN32
    _mkdir("project");
    _mkdir("project/build");
#else
    mkdir("project",0755);
    mkdir("project/build",0755);
#endif
}

static bool save_frame_bmp(const char *path) {
    ensure_capture_dir();
    SDL_Surface *shot=SDL_CreateRGBSurfaceWithFormat(0,win_width,win_height,32,SDL_PIXELFORMAT_RGBA32);
    if(!shot) return false;
    glReadPixels(0,0,win_width,win_height,GL_RGBA,GL_UNSIGNED_BYTE,shot->pixels);
    unsigned char *tmp=malloc((size_t)shot->pitch);
    if(!tmp) { SDL_FreeSurface(shot); return false; }
    for(int y=0;y<win_height/2;y++) {
        unsigned char *top=(unsigned char*)shot->pixels+y*shot->pitch;
        unsigned char *bottom=(unsigned char*)shot->pixels+(win_height-1-y)*shot->pitch;
        memcpy(tmp,top,(size_t)shot->pitch);
        memcpy(top,bottom,(size_t)shot->pitch);
        memcpy(bottom,tmp,(size_t)shot->pitch);
    }
    free(tmp);
    bool saved=SDL_SaveBMP(shot,path)==0;
    SDL_FreeSurface(shot);
    return saved;
}
static int self_test(void) {
    reset_fight();
    unsigned char keys[SDL_NUM_SCANCODES]={0};
    keys[SDL_SCANCODE_J]=1;
    for(int i=0;i<900 && phase==1;i++) tick(keys);
    if(phase != 2 || player.hp <= 0) {
        fprintf(stderr,"Expected a reachable win with held light attack; phase=%d player=%.0f rival=%.0f\n",
                phase,player.hp,rival.hp);
        return 1;
    }
    float remaining=player.hp;
    reset_fight(); player.x=3.0f; rival.x=-3.0f;
    tick((unsigned char[SDL_NUM_SCANCODES]){0});
    if(fabsf(player.facing-1.5707963f)>.05f || fabsf(rival.facing+1.5707963f)>.05f) {
        fputs("Fighters failed to turn toward one another after crossing\n",stderr);
        return 1;
    }
    reset_fight();
    unsigned char jump_keys[SDL_NUM_SCANCODES]={0};
    jump_keys[SDL_SCANCODE_W]=1;
    tick(jump_keys);
    if(player.y <= 0 || player.vy <= 0) {
        fputs("Jump did not leave the fighting plane\n",stderr);
        return 1;
    }
    for(int i=0;i<90;i++) tick((unsigned char[SDL_NUM_SCANCODES]){0});
    if(player.y != 0 || player.vy != 0) {
        fputs("Jump did not land on the fighting plane\n",stderr);
        return 1;
    }
    reset_fight();
    unsigned char back_keys[SDL_NUM_SCANCODES]={0};
    back_keys[SDL_SCANCODE_A]=1;
    tick(back_keys);
    if(!player.guard) {
        fputs("Holding back failed to guard while facing right\n",stderr);
        return 1;
    }
    reset_fight(); player.x=3.0f; rival.x=-3.0f;
    back_keys[SDL_SCANCODE_A]=0;
    back_keys[SDL_SCANCODE_D]=1;
    tick(back_keys);
    if(!player.guard) {
        fputs("Holding back failed to guard after crossing\n",stderr);
        return 1;
    }
    printf("3D side-on spike OK: win, facing, jump, and back-to-block verified; %.0f HP left\n",remaining);
    return 0;
}
int main(int argc,char **argv) {
    if(argc>1 && strcmp(argv[1],"--self-test")==0) return self_test();
    selection_mode=argc>1 && strcmp(argv[1],"--select")==0;
    selection_path=selection_mode && argc==3 ? argv[2] : NULL;
    if(selection_mode && !selection_path) {
        fputs("Usage: omf3d_prototype --select selection.txt\n",stderr);
        return 1;
    }
    model_preview_mode=argc>1 && (strcmp(argv[1],"--model-preview")==0 ||
                                  strcmp(argv[1],"--model-preview-capture")==0);
    bool model_preview_capture=argc>1 && strcmp(argv[1],"--model-preview-capture")==0;
    if(model_preview_mode && argc!=2) {
        fputs("Usage: omf3d_prototype --model-preview | --model-preview-capture\n",stderr);
        return 1;
    }
    bool smoke = argc>1 && strcmp(argv[1],"--smoke")==0;
    bool capture = argc>1 && strcmp(argv[1],"--capture")==0;
    bool sandbox = argc==2 && strcmp(argv[1],"--sandbox")==0;
    bool source_check = argc>1 && strcmp(argv[1],"--source-replay-check")==0;
    source_follow_mode = argc>1 && strcmp(argv[1],"--source-live")==0;
    if(source_follow_mode) {
        source_live_pilot_name = getenv("OMF3K_LIVE_PILOT_NAME");
        source_live_rival_name = getenv("OMF3K_LIVE_RIVAL_NAME");
    }
    source_replay_mode = source_follow_mode || (argc>1 && strcmp(argv[1],"--source-replay")==0);
    if(!selection_mode && !model_preview_mode && !smoke && !capture && !sandbox && !source_check && !source_replay_mode) {
        // Real fights come from OpenOMF (the original-game engine). The built-in combat
        // loop is a provisional placeholder kept only for rendering and self-tests.
        fputs("OMF2115 fights run on the OpenOMF engine. Start one with:\n"
              "  powershell -ExecutionPolicy Bypass -File project/prototype/run-live-jaguar.ps1\n"
              "Other modes: --source-live trace.csv | --source-replay trace.csv | --source-replay-check trace.csv\n"
              "             --model-preview | --select selection.txt | --self-test | --sandbox (provisional non-OMF combat)\n",stderr);
        return 1;
    }
    bool source_capture = false;
    const char *capture_tick_arg = NULL;
    bool bad_source_args = !selection_mode && source_replay_mode && (argc < 3 || argc % 2 == 0);
    if(source_replay_mode && !bad_source_args) {
        for(int i=3; i<argc; i+=2) {
            if(strcmp(argv[i],"--capture-tick")==0 && !source_capture) {
                source_capture=true;
                capture_tick_arg=argv[i+1];
            } else if(strcmp(argv[i],"--input-file")==0 && source_follow_mode && !source_input_path) {
                source_input_path=argv[i+1];
            } else {
                bad_source_args=true;
            }
        }
    }
    if(!selection_mode && ((source_check && argc!=3) || bad_source_args)) {
        fputs("Usage: omf3d_prototype --source-replay-check trace.csv | --source-replay trace.csv [--capture-tick N] | --source-live trace.csv [--input-file input.txt] [--capture-tick N]\n",stderr);
        return 1;
    }
    source_input_enabled=source_input_path!=NULL;
#ifdef _WIN32
    const char *source_input_map_name=source_follow_mode ? getenv("OMF3K_INPUT_MAP") : NULL;
    if(source_input_map_name && *source_input_map_name) source_input_enabled=true;
    source_state_map_name=source_follow_mode ? getenv("OMF3K_STATE_MAP") : NULL;
#endif
    if(source_check || (source_replay_mode && !source_follow_mode)) {
        char error[256];
        if(!source_replay_load(argv[2],&source_replay,error,sizeof(error))) {
            fprintf(stderr,"%s\n",error);
            return 1;
        }
        if(source_check) {
            printf("Source replay OK: %zu frames, ticks %u..%u, HARs %d and %d\n",source_replay.count,
                   source_replay.frames[0].tick,source_replay.frames[source_replay.count-1].tick,
                   source_replay.frames[0].fighter[0].har,source_replay.frames[0].fighter[1].har);
            source_replay_free(&source_replay);
            return 0;
        }
    }
    uint32_t capture_tick=0;
    if(source_capture) {
        char *end;
        unsigned long tick_value=strtoul(capture_tick_arg,&end,10);
        if(!capture_tick_arg[0] || *end || tick_value>UINT32_MAX ||
           (!source_follow_mode &&
            (source_replay_index=source_replay_find_tick(&source_replay,(uint32_t)tick_value))==source_replay.count)) {
            fprintf(stderr,"Invalid or unavailable source tick: %s\n",capture_tick_arg);
            source_replay_free(&source_replay);
            return 1;
        }
        capture_tick=(uint32_t)tick_value;
        if(!source_follow_mode) source_replay_paused=true;
    }
    SDL_SetMainReady();
    if(SDL_Init(SDL_INIT_VIDEO|SDL_INIT_EVENTS)!=0) { fprintf(stderr,"SDL: %s\n",SDL_GetError()); return 1; }
#ifdef _WIN32
    if(source_input_map_name && *source_input_map_name) {
        source_input_mapping=CreateFileMappingA(INVALID_HANDLE_VALUE,NULL,PAGE_READWRITE,0,
                                                sizeof(Omf3kLiveInput),source_input_map_name);
        if(source_input_mapping) source_shared_input=MapViewOfFile(source_input_mapping,FILE_MAP_ALL_ACCESS,0,0,
                                                                   sizeof(Omf3kLiveInput));
        if(!source_shared_input) {
            fprintf(stderr,"Cannot create live input channel\n");
            if(source_input_mapping) CloseHandle(source_input_mapping);
            SDL_Quit();
            return 1;
        }
    }
#endif
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION,3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION,3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,SDL_GL_CONTEXT_PROFILE_CORE);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE,24);
    SDL_GL_SetAttribute(SDL_GL_MULTISAMPLEBUFFERS,1);
    SDL_GL_SetAttribute(SDL_GL_MULTISAMPLESAMPLES,4);
    SDL_Window *window=SDL_CreateWindow("OMF2115 / PROTOTYPE",SDL_WINDOWPOS_CENTERED,SDL_WINDOWPOS_CENTERED,
                                       WIDTH,HEIGHT,SDL_WINDOW_OPENGL|SDL_WINDOW_RESIZABLE|
                                       ((smoke || capture || source_capture || model_preview_capture) ? SDL_WINDOW_HIDDEN : SDL_WINDOW_SHOWN));
    if(!window) { fprintf(stderr,"Window: %s\n",SDL_GetError()); SDL_Quit(); return 1; }
    SDL_GLContext context=SDL_GL_CreateContext(window);
    if(!context) { fprintf(stderr,"OpenGL: %s\n",SDL_GetError()); SDL_DestroyWindow(window); SDL_Quit(); return 1; }
    // Live mode has its own 60 Hz pacing below. Driver vsync can block a
    // hidden or hybrid-GPU window for hundreds of milliseconds.
    SDL_GL_SetSwapInterval(source_follow_mode || model_preview_capture ? 0 : 1);
    const char *vs="#version 330 core\nlayout(location=0) in vec3 p;layout(location=1) in vec3 c;out vec3 color;void main(){gl_Position=vec4(p,1);color=c;}";
    const char *fs="#version 330 core\nin vec3 color;out vec4 outColor;void main(){outColor=vec4(color,1);}";
    GLuint v=make_shader(GL_VERTEX_SHADER,vs), f=make_shader(GL_FRAGMENT_SHADER,fs), program=glCreateProgram();
    glAttachShader(program,v); glAttachShader(program,f); glLinkProgram(program);
    GLint linked=0; glGetProgramiv(program,GL_LINK_STATUS,&linked);
    if(!linked) { fprintf(stderr,"OpenGL program link failed\n"); return 1; }
    glDeleteShader(v); glDeleteShader(f);
    GLuint vao,vbo; glGenVertexArrays(1,&vao); glGenBuffers(1,&vbo);
    glBindVertexArray(vao); glBindBuffer(GL_ARRAY_BUFFER,vbo);
    glBufferData(GL_ARRAY_BUFFER,sizeof(vertices),NULL,GL_STREAM_DRAW);
    glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)0); glEnableVertexAttribArray(0);
    glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,sizeof(Vertex),(void*)(3*sizeof(float))); glEnableVertexAttribArray(1);
    glUseProgram(program); glEnable(GL_DEPTH_TEST); glDepthFunc(GL_LESS);
    reset_fight();
    if(selection_mode) phase=1;
    else if(model_preview_mode) phase=1;
    else if(source_follow_mode) phase=0;
    else if(source_replay_mode) apply_source_frame(source_replay_index);
    else phase=capture ? 1 : 0;
    bool running=true, capture_ok=true; int frames=0, model_preview_capture_index=0;
    Uint64 last=SDL_GetPerformanceCounter(); double accumulator=0;
    Uint64 live_start_ms=SDL_GetTicks64();
    bool profile_live=source_follow_mode && getenv("OMF3K_PROFILE_LIVE")!=NULL;
    if(profile_live) printf("OpenGL renderer: %s (swap interval %d)\n",
                            glGetString(GL_RENDERER),SDL_GL_GetSwapInterval());
    double max_input_ms=0,max_poll_ms=0,max_draw_ms=0,max_swap_ms=0,max_frame_ms=0,max_source_gap_ms=0;
    double max_build_ms=0,max_upload_ms=0,max_gpu_ms=0;
    unsigned int profile_frames=0,slow_frames=0,source_gaps=0,max_tick_advance=0;
    Uint64 last_source_arrival=0;
    while(running) {
        Uint64 profile_begin=SDL_GetPerformanceCounter();
        double profile_frequency=(double)SDL_GetPerformanceFrequency();
        SDL_Event e;
        while(SDL_PollEvent(&e)) {
            if(e.type==SDL_QUIT) running=false;
            if(e.type==SDL_KEYDOWN && !e.key.repeat) {
                if(selection_mode) {
                    if(e.key.keysym.scancode==SDL_SCANCODE_ESCAPE) {
                        FILE *cancel=fopen(selection_path,"w");
                        if(cancel) { fputs("cancelled\n",cancel); fclose(cancel); }
                        running=false;
                    } else if(e.key.keysym.scancode==SDL_SCANCODE_UP ||
                              e.key.keysym.scancode==SDL_SCANCODE_DOWN) {
                        selection_har=(selection_har+1)%2;
                    } else if(e.key.keysym.scancode==SDL_SCANCODE_LEFT) {
                        selection_pilot=(selection_pilot+9)%10;
                    } else if(e.key.keysym.scancode==SDL_SCANCODE_RIGHT) {
                        selection_pilot=(selection_pilot+1)%10;
                    } else if(e.key.keysym.scancode==SDL_SCANCODE_RETURN) {
                        if(!write_selection()) {
                            fprintf(stderr,"Unable to write fighter selection: %s\n",selection_path);
                            running=false;
                            capture_ok=false;
                        } else {
                            running=false;
                        }
                    }
                } else if(e.key.keysym.scancode==SDL_SCANCODE_ESCAPE) running=false;
                else if(model_preview_mode) {
                    if(e.key.keysym.scancode>=SDL_SCANCODE_1 && e.key.keysym.scancode<=SDL_SCANCODE_3)
                        model_preview_view=e.key.keysym.scancode-SDL_SCANCODE_1;
                    if(e.key.keysym.scancode==SDL_SCANCODE_0) model_preview_pose=0;
                    if(e.key.keysym.scancode>=SDL_SCANCODE_4 && e.key.keysym.scancode<=SDL_SCANCODE_7)
                        model_preview_pose=e.key.keysym.scancode-SDL_SCANCODE_4+1;
                    if(e.key.keysym.scancode==SDL_SCANCODE_8) model_preview_pose=5;
                    if(e.key.keysym.scancode==SDL_SCANCODE_9) model_preview_pose=6;
                    if(e.key.keysym.scancode==SDL_SCANCODE_H) model_preview_pose=7;
                    if(e.key.keysym.scancode==SDL_SCANCODE_M) model_preview_pose=8;
                } else if(source_follow_mode) {
                    if(source_live_winner >= 0) {
                        if(e.key.keysym.scancode==SDL_SCANCODE_LEFT || e.key.keysym.scancode==SDL_SCANCODE_A)
                            try_again_choice=0;
                        else if(e.key.keysym.scancode==SDL_SCANCODE_RIGHT || e.key.keysym.scancode==SDL_SCANCODE_D)
                            try_again_choice=1;
                        else if(e.key.keysym.scancode==SDL_SCANCODE_Y) request_live_restart();
                        else if(e.key.keysym.scancode==SDL_SCANCODE_N) running=false;
                        else if(e.key.keysym.scancode==SDL_SCANCODE_RETURN) {
                            if(try_again_choice==0) request_live_restart();
                            else running=false;
                        }
                    }
                } else if(source_replay_mode) {
                    if(e.key.keysym.scancode==SDL_SCANCODE_SPACE) {
                        source_replay_paused=!source_replay_paused;
                        accumulator=0;
                    }
                    if(e.key.keysym.scancode==SDL_SCANCODE_R) {
                        apply_source_frame(0);
                        source_replay_paused=false;
                        accumulator=0;
                    }
                    if(source_replay_paused && e.key.keysym.scancode==SDL_SCANCODE_RIGHT &&
                       source_replay_index+1<source_replay.count) apply_source_frame(source_replay_index+1);
                    if(source_replay_paused && e.key.keysym.scancode==SDL_SCANCODE_LEFT && source_replay_index>0)
                        apply_source_frame(source_replay_index-1);
                } else if(phase==2 || phase==3) {
                    if(e.key.keysym.scancode==SDL_SCANCODE_LEFT || e.key.keysym.scancode==SDL_SCANCODE_A)
                        try_again_choice=0;
                    if(e.key.keysym.scancode==SDL_SCANCODE_RIGHT || e.key.keysym.scancode==SDL_SCANCODE_D)
                        try_again_choice=1;
                    if(e.key.keysym.scancode==SDL_SCANCODE_Y) reset_fight();
                    if(e.key.keysym.scancode==SDL_SCANCODE_N) running=false;
                    if(e.key.keysym.scancode==SDL_SCANCODE_RETURN) {
                        if(try_again_choice==0) reset_fight();
                        else running=false;
                    }
                } else if(e.key.keysym.scancode==SDL_SCANCODE_RETURN && phase==0) reset_fight();
            }
        }
        if(source_follow_mode && source_replay.count)
            write_source_input(source_live_winner >= 0 ? NULL : SDL_GetKeyboardState(NULL));
        Uint64 profile_after_input=SDL_GetPerformanceCounter();
        Uint64 now=SDL_GetPerformanceCounter();
        double frame=(double)(now-last)/(double)SDL_GetPerformanceFrequency(); last=now;
        if(source_replay_mode) {
            float visual_step=(float)fmin(frame,.10);
            if(source_follow_mode) source_visual_time+=visual_step;
            live_impact_time=fmaxf(0,live_impact_time-visual_step);
            live_round_intro_time=fmaxf(0,live_round_intro_time-visual_step);
        }
        if(selection_mode) {
            // The selection screen waits for Enter and does not advance a fight.
        } else if(source_follow_mode) {
            char error[256];
            size_t old_count=source_replay.count;
            int follow_result;
#ifdef _WIN32
            if(source_state_map_name && *source_state_map_name) {
                follow_result=poll_shared_source_state(error,sizeof(error));
            } else
#endif
            {
                follow_result=source_replay_follow_poll(argv[2],&source_replay,&source_follow,error,sizeof(error));
            }
            if(follow_result<0) {
                fprintf(stderr,"%s\n",error);
                running=false;
                capture_ok=false;
            } else if(follow_result>0) {
                apply_source_frame(source_replay.count-1);
                if(!old_count) live_round_intro_time=1.5f;
                source_follow_arrival=now;
                if(profile_live) {
                    unsigned int advance=(unsigned int)(source_replay.count-old_count);
                    if(advance>max_tick_advance) max_tick_advance=advance;
                    if(last_source_arrival) {
                        double gap=(now-last_source_arrival)*1000.0/profile_frequency;
                        if(gap>max_source_gap_ms) max_source_gap_ms=gap;
                        if(gap>60) {
                            source_gaps++;
                            const SourceFrame *latest=&source_replay.frames[source_replay.count-1];
                            printf("Source gap: tick=%u duration=%.1fms health=%d/%d animation=%d/%d\n",
                                   latest->tick,gap,latest->fighter[0].health,latest->fighter[1].health,
                                   latest->fighter[0].animation,latest->fighter[1].animation);
                        }
                    }
                    last_source_arrival=now;
                }
            }
#ifdef _WIN32
            if(source_state_map_name && *source_state_map_name && !source_replay.count &&
               SDL_GetTicks64()-live_start_ms>10000) {
                fputs("Timed out waiting for OpenOMF live state\n",stderr);
                running=false;
                capture_ok=false;
            }
#endif
        } else if(model_preview_mode) {
            // A fixed inspection pose must not advance the fight simulation.
        } else if(source_replay_mode) {
            if(!source_replay_paused) {
                accumulator+=frame>.25 ? .25 : frame;
                while(accumulator>=source_tick_seconds && !source_replay_paused) {
                    accumulator-=source_tick_seconds;
                    if(source_replay_index+1<source_replay.count) apply_source_frame(source_replay_index+1);
                    else source_replay_paused=true;
                }
            }
        } else {
            accumulator+=frame>.25 ? .25 : frame;
            const unsigned char *keys=SDL_GetKeyboardState(NULL);
            while(accumulator>=DT) { tick(keys); accumulator-=DT; }
        }
        Uint64 profile_after_poll=SDL_GetPerformanceCounter();
        interpolate_live_fighters(now,source_capture && source_replay.count &&
                                  source_replay.frames[source_replay_index].tick>=capture_tick);
        SDL_GetWindowSize(window,&win_width,&win_height);
        if(win_height<1) win_height=1;
        glViewport(0,0,win_width,win_height);
        glClearColor(.015f,.025f,.065f,1); glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
        vertex_count=0;
        int world_count;
        if(selection_mode) {
            selection_hud();
            world_count=0;
        } else {
            world();
            world_count=vertex_count;
            hud();
        }
        Uint64 profile_after_build=SDL_GetPerformanceCounter();
        // Give each upload fresh storage, avoiding waits on the prior draw.
        glBindBuffer(GL_ARRAY_BUFFER,vbo);
        glBufferData(GL_ARRAY_BUFFER,sizeof(vertices),NULL,GL_STREAM_DRAW);
        glBufferSubData(GL_ARRAY_BUFFER,0,(size_t)vertex_count*sizeof(Vertex),vertices);
        Uint64 profile_after_upload=SDL_GetPerformanceCounter();
        glEnable(GL_DEPTH_TEST); glDrawArrays(GL_TRIANGLES,0,world_count);
        glDisable(GL_DEPTH_TEST); glDrawArrays(GL_TRIANGLES,world_count,vertex_count-world_count);
        Uint64 profile_after_gpu=SDL_GetPerformanceCounter();
        bool capture_now=capture || (source_capture && (!source_follow_mode ||
                         (source_replay.count && source_replay.frames[source_replay_index].tick>=capture_tick)));
        if(model_preview_capture) {
            const char *paths[]={"project/build/omf3d_model_side.bmp","project/build/omf3d_model_front.bmp",
                                 "project/build/omf3d_model_back.bmp","project/build/omf3d_model_punch.bmp",
                                 "project/build/omf3d_model_kick.bmp","project/build/omf3d_model_guard.bmp",
                                 "project/build/omf3d_model_crouch.bmp","project/build/omf3d_model_walk.bmp",
                                 "project/build/omf3d_model_jump.bmp","project/build/omf3d_model_hit.bmp",
                                 "project/build/omf3d_model_special.bmp"};
            capture_ok=save_frame_bmp(paths[model_preview_capture_index]);
            if(!capture_ok) fprintf(stderr,"Could not save %s: %s\n",
                                    paths[model_preview_capture_index],SDL_GetError());
        } else if(capture_now) {
            const char *path=source_capture ? "project/build/omf3d_source_replay_capture.bmp" : "project/build/omf3d_sideon_capture.bmp";
            capture_ok=save_frame_bmp(path);
            if(!capture_ok) fprintf(stderr,"Could not save %s: %s\n",path,SDL_GetError());
        }
        Uint64 profile_after_draw=SDL_GetPerformanceCounter();
        // Hidden batch captures read the back buffer directly. Swapping the
        // hidden window between views can invalidate its surface on Windows.
        if(!model_preview_capture) SDL_GL_SwapWindow(window);
        Uint64 profile_after_swap=SDL_GetPerformanceCounter();
        if(profile_live && !capture_now) {
            double input_ms=(profile_after_input-profile_begin)*1000.0/profile_frequency;
            double poll_ms=(profile_after_poll-profile_after_input)*1000.0/profile_frequency;
            double draw_ms=(profile_after_draw-profile_after_poll)*1000.0/profile_frequency;
            double build_ms=(profile_after_build-profile_after_poll)*1000.0/profile_frequency;
            double upload_ms=(profile_after_upload-profile_after_build)*1000.0/profile_frequency;
            double gpu_ms=(profile_after_gpu-profile_after_upload)*1000.0/profile_frequency;
            double swap_ms=(profile_after_swap-profile_after_draw)*1000.0/profile_frequency;
            double frame_ms=(profile_after_swap-profile_begin)*1000.0/profile_frequency;
            if(input_ms>max_input_ms) max_input_ms=input_ms;
            if(poll_ms>max_poll_ms) max_poll_ms=poll_ms;
            if(draw_ms>max_draw_ms) max_draw_ms=draw_ms;
            if(build_ms>max_build_ms) max_build_ms=build_ms;
            if(upload_ms>max_upload_ms) max_upload_ms=upload_ms;
            if(gpu_ms>max_gpu_ms) max_gpu_ms=gpu_ms;
            if(swap_ms>max_swap_ms) max_swap_ms=swap_ms;
            if(frame_ms>max_frame_ms) max_frame_ms=frame_ms;
            if(frame_ms>25) {
                slow_frames++;
                printf("Slow live frame: tick=%u total=%.1fms input=%.1f poll=%.1f draw=%.1f build=%.1f upload=%.1f gpu=%.1f swap=%.1f vertices=%d\n",
                       source_replay.count ? source_replay.frames[source_replay_index].tick : 0,
                       frame_ms,input_ms,poll_ms,draw_ms,build_ms,upload_ms,gpu_ms,swap_ms,vertex_count);
            }
            profile_frames++;
        }
        if(source_follow_mode && !capture_now) {
            double draw_seconds=(double)(SDL_GetPerformanceCounter()-now)/(double)SDL_GetPerformanceFrequency();
            if(draw_seconds<DT-.001) SDL_Delay((Uint32)((DT-draw_seconds)*1000));
        }
        if(model_preview_capture) {
            if(!capture_ok || ++model_preview_capture_index>=11) running=false;
            else if(model_preview_capture_index<3) model_preview_view=model_preview_capture_index;
            else {
                model_preview_view=0;
                model_preview_pose=model_preview_capture_index-2;
            }
        } else if((smoke && ++frames >= 10) || capture_now) running=false;
    }
    write_source_input(NULL);
    glDeleteBuffers(1,&vbo); glDeleteVertexArrays(1,&vao); glDeleteProgram(program);
    SDL_GL_DeleteContext(context); SDL_DestroyWindow(window); SDL_Quit();
#ifdef _WIN32
    if(source_shared_input) UnmapViewOfFile(source_shared_input);
    if(source_input_mapping) CloseHandle(source_input_mapping);
    if(source_shared_state) UnmapViewOfFile(source_shared_state);
    if(source_state_mapping) CloseHandle(source_state_mapping);
#endif
    source_replay_follow_close(&source_follow);
    source_replay_free(&source_replay);
    if(profile_live) printf("Live timing: frames=%u slow=%u max_frame=%.1fms input=%.1fms poll=%.1fms draw=%.1fms build=%.1fms upload=%.1fms gpu=%.1fms swap=%.1fms source_gaps=%u max_gap=%.1fms max_tick_advance=%u\n",
                            profile_frames,slow_frames,max_frame_ms,max_input_ms,max_poll_ms,max_draw_ms,
                            max_build_ms,max_upload_ms,max_gpu_ms,max_swap_ms,source_gaps,max_source_gap_ms,max_tick_advance);
    if(smoke) puts("3D prototype OpenGL smoke check OK");
    if(capture && capture_ok) puts("Saved project/build/omf3d_sideon_capture.bmp");
    if(source_capture && capture_ok) puts("Saved project/build/omf3d_source_replay_capture.bmp");
    if(model_preview_capture && capture_ok)
        puts("Saved project/build/omf3d_model_{side,front,back,punch,kick,guard,crouch,walk,jump,hit,special}.bmp");
    return capture_ok ? 0 : 1;
}
