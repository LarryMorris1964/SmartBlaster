//
// SmartBlaster Rev A — Parametric OpenSCAD Model
// Enclosure with snap-fit, alignment, vents, and hardware mounting features.
//

use <../../lib/blink_mount_socket.scad>

//////////////////////////////
// EXPORT SELECTOR
//////////////////////////////

// Options: "assembly", "front_shell", "back_shell", "camera_bracket", "ir_mount", "mating_preview"
export_part = "back_shell";

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
cam_clearance = 4;              // generous clearance — front aperture is a dust-cover hole only,
                                // lens is fully secured to back shell; no front contact intended
cam_hole = cam_diameter + cam_clearance;
cam_offset_x = -35.0;           // top-left corner placement with >=5mm wall border to camera posts
cam_offset_y = 15.0;
cam_chamfer_d = cam_hole + 6;
cam_chamfer_depth = 1.5;

// Camera mount — back shell is the sole structural support for the lens.
// Board sits on the 10mm posts; a raised square capture wall retains the PCB
// at post-top height while a center floor cutout leaves cable room.
// Front shell provides no lens support — it is a dust cover snapped on after calibration.
cam_plate_size   = 37.0;        // mounting plate outer dimension
cam_capture_inner = 32.4;       // clear interior span for camera PCB
cam_capture_wall  = 2.0;        // raised retaining wall thickness
cam_capture_h     = 2.0;        // retaining wall height above post tops
cam_capture_floor_t = 1.0;      // floor thickness at post-top plane
cam_capture_hole  = 30.0;       // central cable opening in capture floor
cam_mount_boss_d = 8.0;
cam_mount_boss_h = 10.0;
cam_mount_screw_d = 2.2;
cam_mount_boss_spacing = 27.0;  // measured from drawing: bolt C-C = 37mm plate - 2×5mm edge

// IR
ir_diameter = 6;
ir_from_edge_ratio = 0.30;          // 0=edge, 1=lens(center)
ir_offset_x = (enclosure_width / 2) * (1 - ir_from_edge_ratio);
ir_offset_y = 0;

// IR LED board mount (drawer-style shelf + side grooves + rear detent)
// First-pass defaults; tune after physical measurements.
led_board_w = 11.2;                 // board width (X), approx 7/16 in
led_board_thickness = 1.6;          // PCB thickness (Y)
led_mount_channel_length = 17.0;    // board insertion travel (Z)
led_mount_front_setback = 1.2;      // gap from inner front wall to board front edge
led_mount_fit_clearance = 0.25;     // clearance around board in grooves
led_mount_shelf_thickness = 1.8;    // shelf thickness
led_mount_rail_thickness = 1.4;     // side rail wall thickness
led_mount_rail_height = 4.0;        // rail height above shelf
led_mount_capture_lip_w = 0.8;      // inward wraparound lip width per side
led_mount_capture_lip_h = 0.8;      // inward wraparound lip height
led_mount_detent_t = 0.8;           // rear snap bump thickness (along Z)
led_mount_detent_h = 0.6;           // rear snap bump height (along Y)

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

// Blink camera snap-ring mount — collar now protrudes inward so exterior back stays flush.
// Bore measured at approx 5/16"–3/8" (~8–9.5 mm); collar OD gives ~2.75 mm wall each side.
blink_collar_od     = 14.0;   // raised collar outer diameter (mm)
blink_bore_d        =  8.5;   // snap through-bore diameter (mm)
blink_collar_h      =  2.0;   // collar height into enclosure interior from inner back wall (mm)
blink_vent_clear_r  = 10.0;   // vent exclusion radius around mount centre (mm)

// Pi standoffs (Zero 2 W)
standoff_height = 6;
standoff_radius = 3;
pi_standoff_hole_d = 2.2;         // Pi mounting pilot for M2.5 screw into printed post
pi_board_len = 65.0;              // Pi Zero 2 W board length (X when not rotated)
pi_board_wid = 30.0;              // Pi Zero 2 W board width
pi_mount_spacing_x = 58;
pi_mount_spacing_y = 23;
pi_mount_rotated = false;           // keep long axis aligned with Pi board X before applying angle
pi_mount_angle = 0;                 // landscape orientation
pi_offset_x = 24;                   // bottom-right placement (SCAD axes)
pi_offset_y = -22;

// Honeycomb vents
vent_hex_r = 2.8;
vent_pitch_x = vent_hex_r * 3.0;
vent_pitch_y = vent_hex_r * 2.6;
vent_rows = 11;                     // portrait field: many rows (Y), fewer columns (X)
vent_cols = 4;
vent_region_w = 22;                 // keep vent block narrow to preserve Pi post area on the right
vent_region_h = 68;                 // nearly full usable inner height
vent_offset_x = 30;                 // near Pi region (right side), similar X zone as earlier layout intent
vent_offset_y = -8;                 // slight downward bias toward Pi heat source
vent_cam_clear_r = 6.0;             // exclusion radius around each camera mount boss


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

module pi_standoff_positions() {
    pi_span_x = pi_mount_rotated ? pi_mount_spacing_y : pi_mount_spacing_x;
    pi_span_y = pi_mount_rotated ? pi_mount_spacing_x : pi_mount_spacing_y;
    for (sx = [-1, 1])
        for (sy = [-1, 1])
            let(
                local_x = sx * pi_span_x / 2,
                local_y = sy * pi_span_y / 2,
                world_x = pi_offset_x + local_x * cos(pi_mount_angle) - local_y * sin(pi_mount_angle),
                world_y = pi_offset_y + local_x * sin(pi_mount_angle) + local_y * cos(pi_mount_angle)
            )
            translate([
                world_x,
                world_y,
                0
            ])
                children();
}

module camera_mount_bosses() {
    base_z = -back_shell_depth / 2 + wall - feature_attach_eps;

    // 4-point boss cluster.
    for (sx = [-1, 1])
        for (sy = [-1, 1])
            translate([
                cam_offset_x + sx * cam_mount_boss_spacing / 2,
                cam_offset_y + sy * cam_mount_boss_spacing / 2,
                base_z
            ])
                difference() {
                    cylinder(d = cam_mount_boss_d, h = cam_mount_boss_h + feature_attach_eps, center = false, $fn = 48);
                    cylinder(d = cam_mount_screw_d, h = cam_mount_boss_h + feature_attach_eps + 0.2, center = false, $fn = 32);
                }

    post_top_z = base_z + cam_mount_boss_h;
    capture_outer = cam_capture_inner + 2 * cam_capture_wall;

    // Raised 32x32 capture box (2mm wall, 2mm high) with a 30x30 center cutout in the floor.
    // Positioned so the FLOOR TOP is flush with post-top height.
    translate([cam_offset_x, cam_offset_y, post_top_z])
        difference() {
            union() {
                // Capture floor slab
                translate([0, 0, -cam_capture_floor_t / 2])
                    cube([cam_capture_inner, cam_capture_inner, cam_capture_floor_t], center = true);

                // Raised retaining walls
                translate([0, 0, cam_capture_h / 2 - feature_attach_eps / 2])
                    difference() {
                        cube([capture_outer, capture_outer, cam_capture_h + feature_attach_eps], center = true);
                        cube([cam_capture_inner, cam_capture_inner, cam_capture_h + feature_attach_eps + 0.2], center = true);
                    }
            }

            // Cable/connector relief opening through the floor slab
            translate([0, 0, -cam_capture_floor_t / 2])
                cube([cam_capture_hole, cam_capture_hole, cam_capture_floor_t + 0.2], center = true);
        }
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

module led_board_mount() {
    inner_front_z = front_shell_depth / 2 - wall;
    slot_w = led_board_w + 2 * led_mount_fit_clearance;
    slot_h = led_board_thickness + 2 * led_mount_fit_clearance;
    z_front = inner_front_z - led_mount_front_setback;
    z_back = z_front - led_mount_channel_length;
    z_mid = (z_front + z_back) / 2;
    shelf_top_y = ir_offset_y - slot_h / 2;
    shelf_mid_y = shelf_top_y - led_mount_shelf_thickness / 2;

    // Base shelf
    translate([ir_offset_x, shelf_mid_y, z_mid])
        cube([
            slot_w + 2 * led_mount_rail_thickness,
            led_mount_shelf_thickness,
            led_mount_channel_length
        ], center = true);

    // Side rails and upper capture lips create a drawer-like slide channel.
    for (sx = [-1, 1]) {
        rail_x = ir_offset_x + sx * (slot_w / 2 + led_mount_rail_thickness / 2);

        translate([rail_x, shelf_top_y + led_mount_rail_height / 2, z_mid])
            cube([
                led_mount_rail_thickness,
                led_mount_rail_height,
                led_mount_channel_length
            ], center = true);

        lip_x = ir_offset_x + sx * (slot_w / 2 - led_mount_capture_lip_w / 2);
        translate([lip_x, shelf_top_y + led_mount_rail_height - led_mount_capture_lip_h / 2, z_mid])
            cube([
                led_mount_capture_lip_w,
                led_mount_capture_lip_h,
                led_mount_channel_length
            ], center = true);
    }

    // Rear detent bump helps retain the board once fully seated.
    translate([ir_offset_x, shelf_top_y + led_mount_detent_h / 2, z_back + led_mount_detent_t / 2])
        cube([slot_w, led_mount_detent_h, led_mount_detent_t], center = true);
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

    color([0.25, 0.45, 0.9, 0.9])
        translate([cam_offset_x, cam_offset_y, wall / 2 - feature_attach_eps])
            difference() {
                cylinder(d = blink_collar_od, h = blink_collar_h, center = false, $fn = 60);
                cylinder(d = blink_bore_d,    h = blink_collar_h + 0.1, center = false, $fn = 48);
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
    union() {
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

        }

        led_board_mount();
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

                // Blink snap collar — centred on camera lens, protrudes inward for flush exterior back
                translate([cam_offset_x, cam_offset_y, -back_shell_depth / 2 + wall - feature_attach_eps])
                    difference() {
                        cylinder(d = blink_collar_od, h = blink_collar_h + feature_attach_eps, center = false, $fn = 60);
                        cylinder(d = blink_bore_d,    h = blink_collar_h + feature_attach_eps + 0.1, center = false, $fn = 48);
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

            // Blink snap bore — through back wall and collar (centred on camera lens)
            translate([cam_offset_x, cam_offset_y, -back_shell_depth / 2 - blink_collar_h - feature_attach_eps])
                cylinder(d = blink_bore_d, h = wall + blink_collar_h + 2 * feature_attach_eps, center = false, $fn = 48);

            // Honeycomb vent field — offset toward Pi, excluded around Blink collar and camera bosses
            for (row = [0 : vent_rows - 1])
                for (col = [0 : vent_cols - 1])
                    let(
                        x = vent_offset_x + (col - (vent_cols - 1) / 2) * vent_pitch_x + (row % 2) * vent_pitch_x / 2,
                        y = (row - (vent_rows - 1) / 2) * vent_pitch_y,
                        half = cam_mount_boss_spacing / 2,
                        cr2 = vent_cam_clear_r * vent_cam_clear_r
                    )
                    if (abs(x - vent_offset_x) < vent_region_w / 2
                            && abs(y) < vent_region_h / 2
                            && ((x-cam_offset_x)*(x-cam_offset_x)+(y-cam_offset_y)*(y-cam_offset_y)) > blink_vent_clear_r * blink_vent_clear_r
                            && ((x-(cam_offset_x+half))*(x-(cam_offset_x+half))+(y-(cam_offset_y+half))*(y-(cam_offset_y+half))) > cr2
                            && ((x-(cam_offset_x+half))*(x-(cam_offset_x+half))+(y-(cam_offset_y-half))*(y-(cam_offset_y-half))) > cr2
                            && ((x-(cam_offset_x-half))*(x-(cam_offset_x-half))+(y-(cam_offset_y+half))*(y-(cam_offset_y+half))) > cr2
                            && ((x-(cam_offset_x-half))*(x-(cam_offset_x-half))+(y-(cam_offset_y-half))*(y-(cam_offset_y-half))) > cr2)
                        translate([x, y, -back_shell_depth / 2 + wall / 2])
                            vent_hex_hole(wall + 0.6);
        }
    }

    difference() {
        union() {
            back_shell_body();

            // Camera mount bosses (4-point square, rise from back wall)
            camera_mount_bosses();

            // Pi standoffs
            pi_standoff_positions()
                translate([0, 0, -back_shell_depth / 2 + wall - feature_attach_eps])
                    cylinder(h = standoff_height + feature_attach_eps, r = standoff_radius, center = false, $fn = 40);

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

        // Pi mounting pilot holes through standoffs
        pi_standoff_positions()
            translate([0, 0, -back_shell_depth / 2 + wall - feature_attach_eps - 0.1])
                cylinder(d = pi_standoff_hole_d, h = standoff_height + feature_attach_eps + 0.4, center = false, $fn = 32);
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
    led_board_mount();
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
