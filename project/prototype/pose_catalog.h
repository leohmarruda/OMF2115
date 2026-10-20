#ifndef OMF3K_POSE_CATALOG_H
#define OMF3K_POSE_CATALOG_H

enum {
    POSE_REACH = 1 << 0,
    POSE_ARM = 1 << 1,
    POSE_LEG = 1 << 2,
    POSE_FIST = 1 << 3,
    POSE_LEG2 = 1 << 4,   // the other leg, measured from the same sprite
    POSE_BODY = 1 << 5,   // torso shift along the fight plane (negative faces the opponent)
    POSE_LEAN = 1 << 6,   // torso lean: forward shift per unit of height above the hip (1.38); positive leans toward the opponent
    POSE_ARM2 = 1 << 7,   // the other arm, measured from the same sprite
    POSE_DROP = 1 << 8    // body height relative to standing (negative is lower); replaces the crouch drop
};

// A catalog entry overrides only the listed parts of the shared blockout rig.
// Keys are OpenOMF HAR, animation, and sprite IDs, not elapsed wall time.
typedef struct {
    int har, animation, sprite, side, flags;
    float reach;
    float elbow_y, elbow_z, wrist_y, wrist_z;
    float knee_y, knee_z, ankle_y, ankle_z;
    float knee2_y, knee2_z, ankle2_y, ankle2_z;
    float body_z;
    float lean;
    float elbow2_y, elbow2_z, wrist2_y, wrist2_z;
    float body_y;
} PoseFrame;

const PoseFrame *pose_catalog_lookup(int har, int animation, int sprite);

#endif
