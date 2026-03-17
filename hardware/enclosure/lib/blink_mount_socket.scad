// ============================================================
// blink_mount_socket.scad
// Reusable Blink-style flush snap-in wall-mount socket
// ============================================================
//
// PROVENANCE
//   Dimensions reverse-engineered from the community reference model:
//     "Blink Camera Mount" by TFL123, Printables model #497067
//     File: sockel-blink-orig.3mf  (CC BY licence)
//   Geometric extraction method: bounding-box + radial cross-section
//   analysis of 3MF mesh vertices at structural Z-planes.
//
//   Key raw measurements (all in mm):
//     z= 8  barrel outer D = 39.9  → entry bore   = 40.0
//     z= 9  snap ring outer D = 38.4, inner D = 23.1
//     z=11  snap ring outer D = 24.0, inner D = 20.0  → snap_d = 23.0 (+0.5 clearance)
//     z=15  stem (ball-joint shaft) outer D = 12.9    → stem_d = 13.0
//     z= 0  base flange outer D = 55.4 x 57.4
//     Total socket depth: ~23 mm; functional snap depth: 10 mm
//
// USAGE
//   use <blink_mount_socket.scad>
//
//   The socket is split into two modules so the caller controls where
//   each ends up in their CSG tree:
//
//     blink_socket_boss(eps)      — positive ring material, union into your shell
//     blink_socket_bores(eps)     — negative cylinders,    difference from your shell
//
//   Typical pattern:
//
//     wall = 2.0;
//     eps  = 0.02;   // feature_attach_eps in your project
//
//     difference() {
//       union() {
//         my_shell_body();
//         // Socket ring is flush-inward, placed at inner wall surface
//         translate([0, 0, -shell_depth/2 + wall - eps])
//           blink_socket_boss(eps);
//       }
//       // Entry bore + stem bore
//       translate([0, 0, -shell_depth/2 - eps])
//         blink_socket_bores(eps, wall);
//     }
//
// PARAMETERS (all mm)
//   socket_entry_d   — collar bore OD in back wall (bracket arm slides through)
//   socket_snap_d    — inner bore of retention ring (holds the ball-joint collar)
//   socket_depth     — axial length of the inward-protruding ring boss
//   socket_stem_d    — clearance bore for ball-joint stem through wall+ring
//   fn_coarse        — $fn for the entry bore  (cosmetic accuracy vs render speed)
//   fn_fine          — $fn for the stem bore
// ============================================================

module blink_socket_boss(
    eps             = 0.02,
    socket_entry_d  = 40.0,
    socket_snap_d   = 23.0,
    socket_depth    = 10.0,
    fn_coarse       = 80
) {
    // Positive annular ring that the bracket collar snaps into.
    // Place with translate() so its Z=0 aligns with the inner wall surface.
    difference() {
        cylinder(d = socket_entry_d, h = socket_depth + eps,     center = false, $fn = fn_coarse);
        cylinder(d = socket_snap_d,  h = socket_depth + eps + 0.2, center = false, $fn = fn_coarse);
    }
}

module blink_socket_bores(
    eps             = 0.02,
    wall            = 2.0,
    socket_entry_d  = 40.0,
    socket_depth    = 10.0,
    socket_stem_d   = 13.0,
    fn_coarse       = 80,
    fn_fine         = 60
) {
    // Entry bore — clears the bracket collar through the shell wall.
    // Z=0 should be at the outer (exterior) wall face.
    cylinder(d = socket_entry_d, h = wall              + 2 * eps, center = false, $fn = fn_coarse);

    // Stem bore — clearance for the ball-joint shaft through wall and boss ring.
    cylinder(d = socket_stem_d,  h = wall + socket_depth + 2 * eps, center = false, $fn = fn_fine);
}
