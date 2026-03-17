// ============================================================
// blink_mount_socket.scad
// Reusable Blink camera snap-ring mount — shallow raised collar
// ============================================================
//
// PROVENANCE
//   Dimensions sourced from:
//     1. User measurement: snap-bore approx 5/16"–3/8" (~8–9.5 mm)
//     2. User description: collar height "as deep as a circuit board" (~1.6 mm)
//     3. Reference model: "Blink Camera Mount" by TFL123, Printables #497067
//        File: sockel-blink-orig.3mf  (CC BY licence)
//        Camera-side snap feature at z=15–23:
//          z=15.74  radial cross-section OD=12.91, ID=8.92  (snap bore ~9 mm)
//          z=18.71  radial cross-section OD=16.45, ID=12.45 (outer collar ~16 mm)
//          z=23     bounding box 16.14 × 16.14               (top snap pad)
//
//   Design: a small annular collar protrudes OUTWARD from the enclosure
//   exterior back face by ~2 mm.  The Blink fixed-mount bracket peg
//   snaps through the bore and is retained by the surrounding flange.
//
// USAGE
//   use <blink_mount_socket.scad>
//
//   The feature is split into two modules so the caller controls placement
//   in the CSG tree:
//
//     blink_snap_collar(eps)   — positive annular ring, union into shell body
//     blink_snap_bore(eps)     — negative cylinder,     difference from shell
//
//   Typical pattern (back shell centred at origin, back face at z = -depth/2):
//
//     wall = 2.0;
//     eps  = 0.02;
//     collar_h = 2.0;
//
//     difference() {
//       union() {
//         my_shell_body();
//         translate([0, 0, -shell_depth/2 - collar_h])
//           blink_snap_collar(eps);
//       }
//       translate([0, 0, -shell_depth/2 - collar_h - eps])
//         blink_snap_bore(eps, wall, collar_h);
//     }
//
// PARAMETERS (all mm)
//   collar_od   — outer diameter of the raised ring
//   bore_d      — through-bore diameter (the hole the bracket peg snaps into)
//   collar_h    — height the collar protrudes proud of the exterior back face
//   fn_ring     — $fn for the collar cylinders
//   fn_bore     — $fn for the snap bore
// ============================================================

module blink_snap_collar(
    eps         = 0.02,
    collar_od   = 14.0,
    bore_d      =  8.5,
    collar_h    =  2.0,
    fn_ring     = 60,
    fn_bore     = 48
) {
    // Shallow annular ring.  Z=0 is the base of the collar (exterior wall face).
    difference() {
        cylinder(d = collar_od, h = collar_h + eps,       center = false, $fn = fn_ring);
        cylinder(d = bore_d,    h = collar_h + eps + 0.1, center = false, $fn = fn_bore);
    }
}

module blink_snap_bore(
    eps         = 0.02,
    wall        = 2.0,
    collar_h    = 2.0,
    bore_d      =  8.5,
    fn_bore     = 48
) {
    // Through-bore from the bottom of the collar to the inner wall face.
    // Z=0 should be placed at the base of the collar (collar_h below exterior face).
    cylinder(d = bore_d, h = wall + collar_h + 2 * eps, center = false, $fn = fn_bore);
}
