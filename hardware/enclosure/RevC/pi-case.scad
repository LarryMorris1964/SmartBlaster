include <indexes.scad>;
use <fillets.scad>;

// TODO: Select which board type. Each -info.scad contains
// coordinates for each component to be cut out of the case.

// use <pi0-info.scad>;
// use <pi1B-info.scad>;
// use <pi3A+-info.scad>;
use <pi3B+-info.scad>;

// Camera board cutout diameter
camera_board_size = 38; // mm

// case sizes

board_w=board()[W];
board_d=board()[D];
board_t=board()[T];

// Use case_depth() from info file for overall case depth
case_depth = case_depth();

wall=wall();
post_t=post_base_t()-board()[T];

avg_lid_t=max_lid_t();
max_comp_t=max_comp_t();

total_case_t=avg_lid_t+wall+post_t;
lower_case_t=post_t+wall+board_t;
upper_case_t=total_case_t-lower_case_t;

wall_pad=tolerances()[WALL_PAD];
fi=tolerances()[FILLET_INNER];
fo=fi+wall;
bolt_d=tolerances()[BOLT_D];
bolt_pad_d=bolt_d*2;
bolt_nut_d=bolt_d / 0.538; // seems like a consistent ratio of metric bolt : nut diameters.

cut_projection=20;

module board_blank_flex(h=total_case_t){
  union(){
    difference(){
      fillet_box([board_w+2*wall+2*wall_pad, 
          case_depth+2*wall+2*wall_pad, 
          wall], fo);
      
      children();
    }

    difference(){
      fillet_box([board_w+2*wall+2*wall_pad, 
          case_depth+2*wall+2*wall_pad, 
          h], fo);
      
      translate([wall, wall, -0.01])
        fillet_box([board_w+2*wall_pad, 
            case_depth+2*wall_pad, 
            h-wall+0.02], fi); // hollow out the entire extended region
    }
  }
}

module board_vent_grid(){
    hd=8;
    interhd=10;

    for(xn=[1:9], yn=[1:6]){
      xoff = (yn % 2) == 1 ? 0 : -4;
      translate([xoff+xn*interhd-interhd/4, 
                 yn*interhd-interhd/2, -0.01])
        cylinder(d=hd, h=wall+0.02, $fn=20);
    }
}

module for_bolts(){
  translate([wall+wall_pad,wall+wall_pad,0])
  for(xy=bolts()){
    translate([xy[0], xy[1], 0])
      children();
  }
}

module bolt_pads(pad_h){
  intersection(){
    translate([wall+wall_pad,wall+wall_pad,0])
    for(xy=bolts()){
      translate([xy[0], xy[1], 0])
      {
        cylinder(d=3*bolt_pad_d, h=wall, $fn=40);

        translate([0,0,wall])
        {
          cylinder(d1=bolt_pad_d*2, d2=bolt_pad_d, h=pad_h/3, $fn=40);

          translate([0,0,pad_h/3])
            cylinder(d=bolt_pad_d, h=pad_h, $fn=40);
        }
      }
    }
    
    fillet_box([board_w+2*(wall+wall_pad),
          case_depth+2*(wall+wall_pad),
          pad_h], fo);
  }
}

module camera_mount_posts(){
  center = camera_center();
  spacing = camera_post_spacing();
  for(dx=[-spacing/2, spacing/2])
  for(dy=[-spacing/2, spacing/2]) {
    intersection() {
      translate([center[0] + dx, center[1] + dy, 0])
        difference() {
          union() {
            cylinder(d=3*bolt_pad_d, h=wall, $fn=40);
            translate([0,0,wall])
              cylinder(d1=bolt_pad_d*2, d2=bolt_pad_d, h=post_t/3, $fn=40);
            translate([0,0,wall+post_t/3])
              cylinder(d=bolt_pad_d, h=post_t, $fn=40);
          }
          // Subtract bolt hole through the entire lower case
          cylinder(d=bolt_d, h=lower_case_t+2, $fn=40);
          // Hex recess for captive nut at the bottom
          cylinder(d=bolt_nut_d, h=bolt_d, $fn=6);
        }
      fillet_box([board_w+2*(wall+wall_pad), case_depth+2*(wall+wall_pad), post_t], fo);
    }
  }
}

module front_edge_wall_cuts(){
  for(mod = front()){
    translate([mod[XOFF]-mod[WIDTH]/2, 
               -wall-wall_pad-cut_projection+mod[YOFF]-0.01, 
               -board_t+mod[ZOFF]-mod[HEIGHT]/2])
      cube([mod[WIDTH], 
            mod[DEPTH]+cut_projection+0.02, 
            mod[HEIGHT]+board_t]);
  }
}

module back_edge_wall_cuts(){
  for(mod = back()){
    translate([mod[XOFF]-mod[WIDTH]/2, 
               board_d-0.01, -board_t+mod[ZOFF]-mod[HEIGHT]/2])
      cube([mod[WIDTH], 
            wall+wall_pad+cut_projection+0.02, 
            mod[HEIGHT]+board_t]);
  }
}

module right_edge_wall_cuts(){
  for(mod = right()){
    translate([mod[XOFF]-mod[WIDTH]/2,
               mod[YOFF]-mod[DEPTH]/2, 
               -board_t+mod[ZOFF]-mod[HEIGHT]/2])
      cube([mod[WIDTH]+wall+wall_pad+cut_projection+0.02, mod[DEPTH], mod[HEIGHT]+board_t]);
  }
}

module left_edge_wall_cuts(){
  for(mod = left()){
    translate([-wall-wall_pad-cut_projection-0.01,
               mod[YOFF]-mod[DEPTH]/2, 
               -board_t+mod[ZOFF]-mod[HEIGHT]/2])
      cube([mod[WIDTH]+wall+wall_pad+cut_projection+0.02, 
            mod[DEPTH], 
            mod[HEIGHT]+board_t]);
  }
}

module wall_cuts(){
  translate([wall+wall_pad, 
             wall+wall_pad, 
             wall+lower_case_t-board_t])
  {
    front_edge_wall_cuts();
    back_edge_wall_cuts();
    left_edge_wall_cuts();
    right_edge_wall_cuts();
  }
}

module top_cuts(){
  for(mod=top()){
    translate([mod[XOFF]-mod[WIDTH]/2,
               mod[YOFF]-mod[DEPTH]/2,
               -wall-wall_pad-0.01])
      cube([mod[WIDTH], mod[DEPTH], wall+wall_pad+cut_projection+0.02]);
  }
  
  imprint();
}

module case_block(){
  t = total_case_t;
  difference(){
    union(){
      board_blank_flex(t){
        children();
      }
      bolt_pads(post_t);
    }

    for_bolts(){
      translate([0,0,-0.01])
      {
        cylinder(d=bolt_d, h=total_case_t+0.02, $fn=40);
        cylinder(d=bolt_nut_d, h=bolt_d, $fn=6);
      }
    }
    
    translate([wall+wall_pad, 
               wall+wall_pad, 
               wall+lower_case_t-board_t])
    {
      left_edge_wall_cuts();
      right_edge_wall_cuts();
      front_edge_wall_cuts();
      back_edge_wall_cuts();
    }
    
    translate([wall+wall_pad,
               wall+wall_pad,
               t])
      top_cuts();
  }
}

module lower_case(){
  intersection(){
    case_block(){
      children();
    }

        cube([board_w+2*(wall+wall_pad),
          case_depth+2*(wall+wall_pad),
          lower_case_t]);
  }
}

module lower_case_with_vents(){
  lower_case(){
    board_vent_grid();
  }
}

module upper_case(){
  translate([0,0,total_case_t])
  rotate([180,0,0])
  difference() {
    union(){
      intersection(){
        case_block();
        translate([0,0,lower_case_t])
          cube([board_w+2*(wall+wall_pad),
            case_depth+2*(wall+wall_pad),
            upper_case_t]);
      }
      difference(){
        upper_case_pegs();
        translate([0,0,-0.01])
        union(){
          linear_extrude(height=total_case_t+0.2){
            projection(cut=true)
            translate([0,0,-total_case_t+0.1])
              wall_cuts();
          }
          linear_extrude(height=lower_case_t+board_t){
            projection(cut=true)
            translate([0,0,-upper_case_t+0.1])
              wall_cuts();
          }
          linear_extrude(height=lower_case_t+2*board_t+0.1){
            projection(cut=true)
            translate([0,0,-upper_case_t-board_t-0.01])
              wall_cuts();
          }
        }
      }
      for_bolts(){
        translate([0,0,lower_case_t+0.8])
        difference(){
          cylinder(d=bolt_pad_d-0.8, h=upper_case_t-0.8, $fn=40);
          translate([0,0,-0.01])
            cylinder(d=bolt_d, h=upper_case_t, $fn=40);
        }
      }
    }
    // Camera lens cutout in upper case (subtract after rotation)
    center = camera_center();
    translate([center[0], center[1], total_case_t-upper_case_t-0.01])
      cylinder(d=camera_board_size, h=upper_case_t+1, $fn=80);
  }
}

// Place camera standoffs outside the lower_case void subtraction
difference() {
  union() {
    lower_case_with_vents();
    camera_mount_posts();
  }
  // Subtract through-holes and hex voids for camera standoffs
  for(dx=[-camera_post_spacing()/2, camera_post_spacing()/2])
  for(dy=[-camera_post_spacing()/2, camera_post_spacing()/2]) {
    center = camera_center();
    translate([center[0] + dx, center[1] + dy, -0.01]) {
      // Through-hole
      cylinder(d=bolt_d, h=lower_case_t+2, $fn=40);
      // Hex recess for captive nut at the bottom
      cylinder(d=bolt_nut_d, h=bolt_d, $fn=6);
    }
  }
}

translate([0,-5,0])
  upper_case();

//case_block();
