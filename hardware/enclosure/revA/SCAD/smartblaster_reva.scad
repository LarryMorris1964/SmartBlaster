//
// SmartBlaster Rev A — Parametric OpenSCAD Model
// Enclosure with snap-fit, alignment, vents, and hardware mounting features.
//

//////////////////////////////
// EXPORT SELECTOR
//////////////////////////////

// Options: "assembly", "front_shell", "back_shell", "camera_bracket", "ir_mount", "mating_preview"
export_part = "assembly";

// Fast-fit preview controls (used by "mating_preview")
preview_gap = 0.8;
preview_section_cut = true;
preview_section_offset_x = 10;
preview_show_voids = true;
preview_show_back_attached = true;


//////////////////////////////
// CORE PARAMETERS
//////////////////////////////

// Overall enclosure footprint
enclosure_width = 120;
enclosure_height = 80;
corner_radius = 8;
preview_back_attached_offset_x = enclosure_width * 0.68;

// Wall/interface
wall = 2;
fit_clearance = 0.3;
feature_attach_eps = 0.2;

// Depth stack (ADR 0003)
target_internal_depth = 61;
front_shell_depth = 20;
back_shell_depth = target_internal_depth - (front_shell_depth - wall) + wall;

// Front face shaping
front_curve_height = 2.2;


//////////////////////////////
// FEATURE PARAMETERS
//////////////////////////////

// Camera
cam_diameter = 27;
cam_clearance = 1;
cam_hole = cam_diameter + cam_clearance;
cam_offset_x = 0;
cam_offset_y = 0;
cam_chamfer_d = cam_hole + 6;
cam_chamfer_depth = 1.5;

// IR
ir_diameter = 6;
ir_offset_x = 25;
ir_offset_y = 0;

// Lip/groove interface
lip_margin = 5;
lip_thickness = 1.8;
lip_depth = 2.4;
groove_depth = lip_depth + 0.4;

// Alignment tabs
align_tab_w = 8;
align_tab_h = 4;
align_tab_depth = 3;
align_tab_edge_inset = 1.2;
mating_feature_y = enclosure_height / 2 - wall / 2;

// Snap-fit tabs and slots
snap_tab_w = 10;
snap_tab_t = 1.8;
snap_tab_l = 7;
snap_bump = 0.7;
snap_y_offset = mating_feature_y - align_tab_edge_inset;

// Screw posts
screw_post_d = 8;
screw_post_h = 10;
screw_hole_d = 2.6;
screw_head_relief_d = 5.6;
screw_head_relief_h = 2;
screw_offset_x = enclosure_width / 2 - 14;
screw_offset_y = enclosure_height / 2 - 14;

// Blink-style flush snap-in wall-mount socket
// Dimensions reverse-engineered from sockel-blink-orig.3mf reference geometry
// z=8 outerD=39.9  z=9-11 snapRing innerD=20 outerD=24  z=15 stemD=12.9
blink_socket_d   = 40.0;  // entry bore OD through back wall (bracket collar)
blink_snap_d     = 23.0;  // snap ring inner D (22mm measured + 0.5 clearance)
blink_snap_depth = 10.0;  // depth socket ring protrudes inward from back wall
blink_stem_d     = 13.0;  // ball-joint stem clearance bore

// Pi standoffs (Zero 2 W)
standoff_height = 6;
standoff_radius = 3;
pi_mount_spacing_x = 58;
pi_mount_spacing_y = 23;

// Honeycomb vents
vent_hex_r = 2.8;
vent_pitch_x = vent_hex_r * 3.0;
vent_pitch_y = vent_hex_r * 2.6;
vent_rows = 5;
vent_cols = 9;
vent_region_w = 58;
vent_region_h = 34;


//////////////////////////////
// DERIVED INTERFACE GEOMETRY
//////////////////////////////

interface_w = enclosure_width - 2 * wall;
interface_h = enclosure_height - 2 * wall;

lip_outer_w = interface_w + 2 * feature_attach_eps;
lip_outer_h = interface_h + 2 * feature_attach_eps;
lip_inner_w = lip_outer_w - 2 * lip_thickness;
lip_inner_h = lip_outer_h - 2 * lip_thickness;
align_tab_y_offset = mating_feature_y - align_tab_edge_inset;

groove_outer_w = lip_outer_w + 2 * fit_clearance;
groove_outer_h = lip_outer_h + 2 * fit_clearance;
groove_inner_w = lip_inner_w - 2 * fit_clearance;
groove_inner_h = lip_inner_h - 2 * fit_clearance;


//////////////////////////////
// HELPER GEOMETRY
//////////////////////////////

module rounded_rect_2d(w, h, r) {
    rr = min(r, min(w, h) / 2 - 0.01);
    hull() {
        translate([ w / 2 - rr,  h / 2 - rr]) circle(r = rr, $fn = 36);
        translate([-w / 2 + rr,  h / 2 - rr]) circle(r = rr, $fn = 36);
        translate([ w / 2 - rr, -h / 2 + rr]) circle(r = rr, $fn = 36);
        translate([-w / 2 + rr, -h / 2 + rr]) circle(r = rr, $fn = 36);
    }
}

module rounded_prism(w, h, d, r, center = true) {
    if (center)
        translate([0, 0, -d / 2])
            linear_extrude(height = d)
                rounded_rect_2d(w, h, r);
    else
        linear_extrude(height = d)
            rounded_rect_2d(w, h, r);
}

module ring_prism(outer_w, outer_h, inner_w, inner_h, d, r_outer, r_inner, center = true) {
    difference() {
        rounded_prism(outer_w, outer_h, d, r_outer, center = center);
        rounded_prism(inner_w, inner_h, d + 0.2, r_inner, center = center);
    }
}

module screw_positions() {
    for (sx = [-1, 1])
        for (sy = [-1, 1])
            translate([sx * screw_offset_x, sy * screw_offset_y, 0])
                children();
}

module pi_standoff_positions() {
    for (sx = [-1, 1])
        for (sy = [-1, 1])
            translate([sx * pi_mount_spacing_x / 2, sy * pi_mount_spacing_y / 2, 0])
                children();
}

module alignment_tab_positions() {
    for (sy = [-1, 1])
        translate([0, sy * align_tab_y_offset, 0])
            children();
}

module snap_positions() {
    for (sx = [-1, 1])
        for (sy = [-1, 1])
            translate([sx * (enclosure_width / 2 - wall - snap_tab_w / 2 - 0.6), sy * snap_y_offset, 0])
                children();
}

module curved_front_skin() {
    intersection() {
        translate([0, 0, front_shell_depth / 2 - front_curve_height])
            scale([enclosure_width / 2, enclosure_height / 2, front_curve_height])
                sphere(r = 1, $fn = 96);
        translate([0, 0, front_shell_depth / 2 - front_curve_height / 2])
            cube([enclosure_width, enclosure_height, front_curve_height], center = true);
    }
}

module vent_hex_hole(h) {
    cylinder(h = h, r = vent_hex_r, $fn = 6, center = true);
}

module preview_clip() {
    if (preview_section_cut)
        intersection() {
            children();
            translate([preview_section_offset_x, 0, 0])
                cube([enclosure_width + 20, enclosure_height + 20, 120], center = true);
        }
    else
        children();
}

module front_mating_features() {
    // Mating plane at z = 0, with front features extending mostly in -z.
    color("lightgray")
        translate([0, 0, -lip_depth / 2])
            ring_prism(
                lip_outer_w,
                lip_outer_h,
                lip_inner_w,
                lip_inner_h,
                lip_depth,
                max(corner_radius - wall - lip_margin, 1),
                max(corner_radius - wall - lip_margin - lip_thickness, 0.8),
                center = true
            );

    if (preview_show_voids) {
        color([0.9, 0.3, 0.3, 0.55])
            alignment_tab_positions()
                translate([0, 0, -align_tab_depth / 2 + 0.1])
                    cube([
                        align_tab_w + 2 * fit_clearance,
                        align_tab_h + 2 * fit_clearance,
                        align_tab_depth + 0.2
                    ], center = true);

        color([0.9, 0.3, 0.3, 0.55])
            snap_positions()
                translate([0, 0, -snap_tab_l / 2 + 0.1])
                    cube([
                        snap_tab_w + 2 * fit_clearance,
                        snap_tab_t + 2 * fit_clearance,
                        snap_tab_l + 0.2
                    ], center = true);
    }
}

module back_mating_features() {
    // Mating plane at z = 0, with back features extending in +z and groove in -z.
    color("gainsboro")
        translate([0, 0, -groove_depth / 2])
            ring_prism(
                groove_outer_w,
                groove_outer_h,
                groove_inner_w,
                groove_inner_h,
                groove_depth,
                max(corner_radius - wall - lip_margin + fit_clearance, 1),
                max(corner_radius - wall - lip_margin - lip_thickness - fit_clearance, 0.8),
                center = true
            );

    color([0.2, 0.4, 0.9, 0.9])
        alignment_tab_positions()
            translate([0, 0, align_tab_depth / 2])
                cube([align_tab_w, align_tab_h, align_tab_depth], center = true);

    color([0.2, 0.4, 0.9, 0.9])
        snap_positions()
            union() {
                translate([0, 0, snap_tab_l / 2])
                    cube([snap_tab_w, snap_tab_t, snap_tab_l], center = true);
                translate([0, 0, snap_tab_l - 0.55])
                    cube([snap_tab_w, snap_tab_t + snap_bump, 1.1], center = true);
            }
}

module back_attached_features_preview() {
    // Isolated view of features that must remain attached to the back wall.
    color([0.7, 0.7, 0.7, 0.35])
        rounded_prism(
            enclosure_width - 2 * wall,
            enclosure_height - 2 * wall,
            wall,
            max(corner_radius - wall, 1),
            center = true
        );

    color([0.2, 0.7, 0.3, 0.9])
        pi_standoff_positions()
            translate([0, 0, wall / 2 - feature_attach_eps])
                cylinder(h = standoff_height + feature_attach_eps, r = standoff_radius, center = false, $fn = 40);

    color([0.95, 0.55, 0.15, 0.9])
        screw_positions()
            translate([0, 0, wall / 2 - feature_attach_eps])
                cylinder(h = screw_post_h + feature_attach_eps, d = screw_post_d, center = false, $fn = 48);

    color([0.25, 0.45, 0.9, 0.9])
        translate([0, 0, wall / 2 - feature_attach_eps])
            difference() {
                cylinder(d = blink_socket_d, h = blink_snap_depth + feature_attach_eps, center = false, $fn = 80);
                cylinder(d = blink_snap_d,    h = blink_snap_depth + feature_attach_eps + 0.2, center = false, $fn = 80);
            };
}

module mating_preview() {
    union() {
        preview_clip() {
            translate([0, 0, preview_gap / 2])
                front_mating_features();
            translate([0, 0, -preview_gap / 2])
                back_mating_features();
        }

        if (preview_show_back_attached)
            translate([preview_back_attached_offset_x, 0, 0])
                back_attached_features_preview();
    }
}


//////////////////////////////
// FRONT SHELL
//////////////////////////////

module front_shell() {
    difference() {
        union() {
            rounded_prism(enclosure_width, enclosure_height, front_shell_depth, corner_radius, center = true);
            curved_front_skin();

            // Male lip for front/back interface
            translate([0, 0, -front_shell_depth / 2 - lip_depth / 2 + feature_attach_eps])
                ring_prism(
                    lip_outer_w,
                    lip_outer_h,
                    lip_inner_w,
                    lip_inner_h,
                    lip_depth,
                    max(corner_radius - wall - lip_margin, 1),
                    max(corner_radius - wall - lip_margin - lip_thickness, 0.8),
                    center = true
                );
        }

        // Hollow interior: keep the front face closed and the rear side open for internal routing
        translate([0, 0, -wall / 2 - feature_attach_eps])
            rounded_prism(
                enclosure_width - 2 * wall,
                enclosure_height - 2 * wall,
                front_shell_depth - wall + 2 * feature_attach_eps,
                max(corner_radius - wall, 1),
                center = true
            );

        // Ensure rear pass-through remains open for camera/IR routing
        translate([0, 0, -front_shell_depth / 2 - lip_depth / 2 + feature_attach_eps])
            rounded_prism(
                lip_inner_w - 2 * fit_clearance,
                lip_inner_h - 2 * fit_clearance,
                lip_depth + wall + 0.6,
                max(corner_radius - wall - lip_margin - lip_thickness - fit_clearance, 0.8),
                center = true
            );

        // Camera and chamfered front opening
        translate([cam_offset_x, cam_offset_y, front_shell_depth / 2 - wall - 0.1])
            cylinder(d = cam_hole, h = wall + 0.3, center = false, $fn = 72);
        translate([cam_offset_x, cam_offset_y, front_shell_depth / 2 - cam_chamfer_depth])
            cylinder(d1 = cam_hole, d2 = cam_chamfer_d, h = cam_chamfer_depth + 0.1, center = false, $fn = 72);

        // IR opening
        translate([ir_offset_x, ir_offset_y, front_shell_depth / 2 - wall - 0.1])
            cylinder(d = ir_diameter, h = wall + 0.3, center = false, $fn = 48);

        // Alignment pockets
        alignment_tab_positions()
            translate([0, 0, -front_shell_depth / 2 - align_tab_depth / 2 + 0.1])
                cube([
                    align_tab_w + 2 * fit_clearance,
                    align_tab_h + 2 * fit_clearance,
                    align_tab_depth + 0.2
                ], center = true);

        // Snap slots to receive back tabs
        snap_positions()
            translate([0, 0, -front_shell_depth / 2 - snap_tab_l / 2 + 0.1])
                cube([
                    snap_tab_w + 2 * fit_clearance,
                    snap_tab_t + 2 * fit_clearance,
                    snap_tab_l + 0.2
                ], center = true);

        // Through-holes for screws
        screw_positions()
            translate([0, 0, -front_shell_depth / 2 - 0.1])
                cylinder(d = screw_hole_d + 0.2, h = wall + lip_depth + 0.4, center = false, $fn = 36);
    }
}


//////////////////////////////
// BACK SHELL
//////////////////////////////

module back_shell() {
    module back_shell_body() {
        difference() {
            union() {
                rounded_prism(enclosure_width, enclosure_height, back_shell_depth, corner_radius, center = true);

                // Blink socket ring boss (protrudes inward from back wall, no external protrusion)
                translate([0, 0, -back_shell_depth / 2 + wall - feature_attach_eps])
                    difference() {
                        cylinder(d = blink_socket_d, h = blink_snap_depth + feature_attach_eps, center = false, $fn = 80);
                        cylinder(d = blink_snap_d,    h = blink_snap_depth + feature_attach_eps + 0.2, center = false, $fn = 80);
                    }
            }

            // Hollow interior
            translate([0, 0, wall])
                rounded_prism(
                    enclosure_width - 2 * wall,
                    enclosure_height - 2 * wall,
                    back_shell_depth,
                    max(corner_radius - wall, 1),
                    center = true
                );

            // Female groove matching the front lip
            translate([0, 0, back_shell_depth / 2 - groove_depth / 2])
                ring_prism(
                    groove_outer_w,
                    groove_outer_h,
                    groove_inner_w,
                    groove_inner_h,
                    groove_depth,
                    max(corner_radius - wall - lip_margin + fit_clearance, 1),
                    max(corner_radius - wall - lip_margin - lip_thickness - fit_clearance, 0.8),
                    center = true
                );

            // Blink socket entry bore through back wall (flush with exterior)
            translate([0, 0, -back_shell_depth / 2 - feature_attach_eps])
                cylinder(d = blink_socket_d, h = wall + 2 * feature_attach_eps, center = false, $fn = 80);

            // Ball-joint stem bore through back wall and socket ring
            translate([0, 0, -back_shell_depth / 2 - feature_attach_eps])
                cylinder(d = blink_stem_d, h = wall + blink_snap_depth + 2 * feature_attach_eps, center = false, $fn = 60);

            // Honeycomb vent field through back wall
            for (row = [0 : vent_rows - 1])
                for (col = [0 : vent_cols - 1]) {
                    x = (col - (vent_cols - 1) / 2) * vent_pitch_x + (row % 2) * vent_pitch_x / 2;
                    y = (row - (vent_rows - 1) / 2) * vent_pitch_y;
                    if (abs(x) < vent_region_w / 2 && abs(y) < vent_region_h / 2)
                        translate([x, y, -back_shell_depth / 2 + wall / 2])
                            vent_hex_hole(wall + 0.6);
                }
        }
    }

    difference() {
        union() {
            back_shell_body();

            // Pi standoffs
            pi_standoff_positions()
                translate([0, 0, -back_shell_depth / 2 + wall - feature_attach_eps])
                    cylinder(h = standoff_height + feature_attach_eps, r = standoff_radius, center = false, $fn = 40);

            // Screw posts
            screw_positions()
                translate([0, 0, -back_shell_depth / 2 + wall - feature_attach_eps])
                    cylinder(h = screw_post_h + feature_attach_eps, d = screw_post_d, center = false, $fn = 48);

            // Alignment tabs
            alignment_tab_positions()
                translate([0, 0, back_shell_depth / 2 + align_tab_depth / 2 - feature_attach_eps])
                    cube([align_tab_w, align_tab_h, align_tab_depth], center = true);

            // Snap tabs with small latch bump
            snap_positions()
                union() {
                    translate([0, 0, back_shell_depth / 2 + snap_tab_l / 2 - feature_attach_eps])
                        cube([snap_tab_w, snap_tab_t, snap_tab_l], center = true);
                    translate([0, 0, back_shell_depth / 2 + snap_tab_l - 0.55 - feature_attach_eps])
                        cube([snap_tab_w, snap_tab_t + snap_bump, 1.1], center = true);
                }
        }

        // Screw pilot holes and head relief
        screw_positions()
            translate([0, 0, -back_shell_depth / 2 + wall - feature_attach_eps - 0.1])
                cylinder(d = screw_hole_d, h = screw_post_h + feature_attach_eps + 0.4, center = false, $fn = 36);
        screw_positions()
            translate([0, 0, back_shell_depth / 2 - screw_head_relief_h])
                cylinder(d = screw_head_relief_d, h = screw_head_relief_h + 0.1, center = false, $fn = 48);
    }
}


//////////////////////////////
// ACCESSORY PARTS
//////////////////////////////

module camera_bracket() {
    difference() {
        rounded_prism(40, 40, 3, 3, center = true);
        translate([0, 0, 0.2])
            cylinder(d = cam_hole, h = 4, center = true, $fn = 72);
    }
}

module ir_mount() {
    difference() {
        rounded_prism(25, 20, 3, 2, center = true);
        translate([0, 0, 0.2])
            cylinder(d = ir_diameter, h = 4, center = true, $fn = 48);
    }
}

module assembly_view() {
    color("lightgray")
        front_shell();
    translate([0, 0, -(front_shell_depth / 2 + back_shell_depth / 2 + 6)])
        color("gainsboro")
            back_shell();
}


//////////////////////////////
// EXPORT SWITCH
//////////////////////////////

if (export_part == "front_shell")
    front_shell();
else if (export_part == "back_shell")
    back_shell();
else if (export_part == "camera_bracket")
    camera_bracket();
else if (export_part == "ir_mount")
    ir_mount();
else if (export_part == "mating_preview")
    mating_preview();
else
    assembly_view();
