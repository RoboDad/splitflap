/*
   Copyright 2026 Phil Van Valkenberg, based on the work of Scott Bezek and the splitflap contributors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

	   http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/

use<../3d/28byj-48.scad>;
// Latest OpenSCAD complains about variables that begin with numbers...  Embedding and renaming 28byj-48.scad variables...
m28byj48_chassis_radius = 28/2;
m28byj48_chassis_height = 19;
m28byj48_shaft_offset = 8;
m28byj48_mount_center_offset = 35/2;
m28byj48_mount_bracket_height = 0.8;
m28byj48_shaft_collar_radius = 9.4/2;
m28byj48_shaft_radius = 5/2;
m28byj48_backpack_extent = 18; // seen values from 17-18

use<../3d/assert.scad>;
use<../3d/color_util.scad>;
use<../3d/flap.scad>;
use<../3d/flap_characters.scad>;
use<../3d/label.scad>;
use<../3d/pcb.scad>;
use<../3d/projection_renderer.scad>;
use<../3d/rough7380.scad>;
use<../3d/spool.scad>;
use<../3d/shapes.scad>;
use<../3d/splitflap.scad>;

include<../3d/flap_dimensions.scad>;
include<../3d/global_constants.scad>;
include<../3d/m4_dimensions.scad>;
include<../3d/sensor_pcb_dimensions.scad>;

chainlink_board_hole_pattern_space_x = 191.4;
chainlink_board_hole_pattern_space_y = 24;


layer_size_3dprint = 0.2; // This is the layer height used for printing.  It is used to round Z dimensions to multiples of this for better print quality.

// Round z height to layer boundaries for better 3D printing
function round_to_layer_floor(z) = floor(z / layer_size_3dprint) * layer_size_3dprint;
function round_to_layer_nearest(z) = round(z / layer_size_3dprint) * layer_size_3dprint;
function round_to_layer_ceil(z) = ceil(z / layer_size_3dprint) * layer_size_3dprint;


num_flaps = 52;
echo(num_flaps=num_flaps);

spool_thickness = round_to_layer_nearest(3.0);
spool_thickness_3dprint = spool_thickness; //round_to_layer_floor((num_flaps > 58) ? 2.9 : 3.0);
echo(spool_thickness_3dprint = spool_thickness_3dprint);

flap_width_slop = 0.5;  // amount of slop of the flap side to side between the 2 spools

spool_width_slop = 1.4;  // amount of slop for the spool assembly side-to-side inside the enclosure

spool_tab_clearance = 0;  // for the tabs connecting the struts to the spool ends (interference fit)
spool_retaining_clearance = 0.10;  // for the notches in the spool retaining wall
spool_joint_clearance = 0.10;  // for the notched joints on the spool struts


flap_hole_radius = (flap_pin_width + 0.8) / 2;
flap_hole_separation = 1.2;  // additional spacing between hole edges
flap_gap = (flap_hole_radius * 2 - flap_pin_width) + flap_hole_separation;
echo(flap_gap=flap_gap);

flap_spool_outset = 0.8;
flap_pitch_radius = flap_spool_pitch_radius(num_flaps, flap_hole_radius, flap_hole_separation); //num_flaps * (flap_hole_radius*2 + flap_hole_separation) / (2*PI);
spool_outer_radius = flap_spool_outer_radius(num_flaps, flap_hole_radius, flap_hole_separation, flap_spool_outset); //flap_pitch_radius + 2*flap_hole_radius;

// Radius where flaps are expected to flap in their *most collapsed* (90 degree) state
exclusion_radius = sqrt(flap_height*flap_height + flap_pitch_radius*flap_pitch_radius);
// Radius where flaps are expected to flap in their *most extended* state
outer_exclusion_radius = flap_pitch_radius + flap_height + 2;

front_forward_offset = flap_pitch_radius + flap_thickness/2;

spool_width = flap_width - flap_notch_depth*2 + flap_width_slop + spool_thickness*2;  // spool width, outside face (spool to spool)
spool_width_clearance = max(spool_width, flap_width + flap_width_slop);  // width clearance for the spool, either for the spool itself or the flaps


magnet_hole_offset = pcb_hole_to_sensor_x();

// Clearance between the motor chassis and the outside right wall of the previous module
m28byj48_chassis_height_clearance = 1.4;

motor_shaft_under_radius = 0.08;  // interference fit
motor_slop_radius = 3;

// Width of the front panel
front_window_upper_base = (flap_height - flap_pin_width/2);
front_window_overhang = 1;
front_window_upper = front_window_upper_base - front_window_overhang;
front_window_lower = sqrt(outer_exclusion_radius*outer_exclusion_radius - front_forward_offset*front_forward_offset);
front_window_height = front_window_lower+front_window_upper;
front_window_width = spool_width_slop + spool_width_clearance;
enclosure_vertical_clearance_top = 5; // gap between top of flaps and top of enclosure
enclosure_vertical_clearance_bottom = 1; // gap between bottom of flaps and bottom of enclosure
enclosure_vertical_inset = max(spool_thickness*1.5, m4_nut_width_corners_padded/2); // distance from top of sides to top of the top piece
enclosure_height_upper = exclusion_radius + enclosure_vertical_clearance_top + spool_thickness + enclosure_vertical_inset;
enclosure_height_lower = flap_pitch_radius + flap_height + enclosure_vertical_clearance_bottom + spool_thickness + enclosure_vertical_inset;
enclosure_height = enclosure_height_upper + enclosure_height_lower;

enclosure_horizontal_rear_margin = 2; // minumum distance between the farthest feature and the rear

enclosure_length = front_forward_offset + m28byj48_mount_center_offset + m4_hole_diameter/2 + enclosure_horizontal_rear_margin;

// distance from the outside spool face to the inside of the left enclosure
pcb_to_spool = 66 - front_window_width - spool_thickness + spool_width_slop/2;


echo(enclosure_height=enclosure_height);
echo(enclosure_height_upper=enclosure_height_upper);
echo(enclosure_height_lower=enclosure_height_lower);
echo(enclosure_length=enclosure_length);
echo(front_window_width=front_window_width);
echo(front_window_upper=front_window_upper);
echo(front_window_lower=front_window_lower);
echo(front_window_height=front_window_height);
echo(front_forward_offset=front_forward_offset);
echo(flap_exclusion_radius=exclusion_radius);
echo(flap_hole_radius=flap_hole_radius);
echo(flap_notch_height=flap_notch_height);


module tube(h, ir, or, ir1, or1, ir2, or2, id, od, id1, od1, id2, od2, center=false, pie_angle, $fn) 
{
    // Convert diameter parameters to radii if provided
    inner_r1 = ir1 != undef ? ir1 : 
               id1 != undef ? id1/2 : 
               ir != undef ? ir : 
               id != undef ? id/2 : undef;
    
    outer_r1 = or1 != undef ? or1 : 
               od1 != undef ? od1/2 : 
               or != undef ? or : 
               od != undef ? od/2 : undef;
    
    inner_r2 = ir2 != undef ? ir2 : 
               id2 != undef ? id2/2 : 
               ir != undef ? ir : 
               id != undef ? id/2 : 
               inner_r1;
    
    outer_r2 = or2 != undef ? or2 : 
               od2 != undef ? od2/2 : 
               or != undef ? or : 
               od != undef ? od/2 : 
               outer_r1;
    
    // Determine the maximum outer radius for pie slice calculations
    max_outer_r = max(outer_r1, outer_r2);
    
    // If pie_angle is specified, intersect the tube with a pie slice
    if (pie_angle != undef && pie_angle > 0 && pie_angle < 360)
    {
        intersection()
        {
            // Create the tube as a difference of two cylinders
            difference() 
            {
                cylinder(h=h, r1=outer_r1, r2=outer_r2, center=center, $fn=$fn);
                translate([0, 0, center ? -eps : -eps])
                    cylinder(h=h + 2*eps, r1=inner_r1, r2=inner_r2, center=center, $fn=$fn);
            }
            
            // Create pie slice by extruding a 2D wedge
            // Center the pie slice so it's symmetric about the +X axis
            rotate([0, 0, -pie_angle/2])
            {
                linear_extrude(height=h, center=center)
                {
                    polygon([
                        [0, 0],
                        [max_outer_r * 2, 0],
                        [max_outer_r * 2 * cos(pie_angle), max_outer_r * 2 * sin(pie_angle)]
                    ]);
                }
            }
        }
    }
    else
    {
        // Create the tube as a difference of two cylinders
        difference() 
        {
            cylinder(h=h, r1=outer_r1, r2=outer_r2, center=center, $fn=$fn);
            translate([0, 0, center ? -eps : -eps])
                cylinder(h=h + 2*eps, r1=inner_r1, r2=inner_r2, center=center, $fn=$fn);
        }
    }
}

module rounded_cube(size, r=0, center=false, $fn)
{
	// Handle size parameter (can be scalar or vector)
	dimensions = is_list(size) ? size : [size, size, size];
	x = dimensions[0];
	y = dimensions[1];
	z = dimensions[2];
	
	// Ensure radius doesn't exceed half of smallest dimension
	max_r = min(x, y, z) / 2;
	actual_r = min(r, max_r);
	
	// Calculate offset for centering
	offset = center ? [-x/2, -y/2, -z/2] : [0, 0, 0];
	
	translate(offset) 
	{
		if (actual_r <= 0) 
		{
			// No rounding, just create a regular cube
			cube([x, y, z]);
		} 
		else 
		{
			hull() 
			{
				// Place spheres at each corner
				translate([actual_r, actual_r, actual_r])
					sphere(r=actual_r, $fn=$fn);
				translate([x-actual_r, actual_r, actual_r])
					sphere(r=actual_r, $fn=$fn);
				translate([actual_r, y-actual_r, actual_r])
					sphere(r=actual_r, $fn=$fn);
				translate([x-actual_r, y-actual_r, actual_r])
					sphere(r=actual_r, $fn=$fn);
				translate([actual_r, actual_r, z-actual_r])
					sphere(r=actual_r, $fn=$fn);
				translate([x-actual_r, actual_r, z-actual_r])
					sphere(r=actual_r, $fn=$fn);
				translate([actual_r, y-actual_r, z-actual_r])
					sphere(r=actual_r, $fn=$fn);
				translate([x-actual_r, y-actual_r, z-actual_r])
					sphere(r=actual_r, $fn=$fn);
			}
		}
	}
}

module chamfered_cube(size, r=0, center=false)
{
	// Handle size parameter (can be scalar or vector)
	dimensions = is_list(size) ? size : [size, size, size];
	x = dimensions[0];
	y = dimensions[1];
	z = dimensions[2];
	
	// Ensure chamfer doesn't exceed half of smallest dimension
	max_r = min(x, y, z) / 2;
	actual_r = min(r, max_r);
	
	// Calculate offset for centering
	offset = center ? [-x/2, -y/2, -z/2] : [0, 0, 0];
	
	translate(offset) 
	{
		if (actual_r <= 0) 
		{
			// No chamfer, just create a regular cube
			cube([x, y, z]);
		} 
		else 
		{
			// Create chamfered cube by hulling three orthogonal prisms
			// Each prism has a square cross-section and extends along one axis
			hull()
			{
				// Prism along X axis: square cross-section in YZ plane
				translate([0, actual_r, actual_r])
					cube([x, y - 2*actual_r, z - 2*actual_r]);
				
				// Prism along Y axis: square cross-section in XZ plane
				translate([actual_r, 0, actual_r])
					cube([x - 2*actual_r, y, z - 2*actual_r]);
				
				// Prism along Z axis: square cross-section in XY plane
				translate([actual_r, actual_r, 0])
					cube([x - 2*actual_r, y - 2*actual_r, z]);
			}
		}
	}
}

module scalloped_cube(size, web_thickness, x_reveal, y_reveal, corner_radius=0, center=false, $fn) 
{
	// size: outer dimensions [x, y, z] or scalar of the cube before scalloping
	// web_thickness: thickness of the center "web" (solid material in Z middle)
	// x_reveal: distance from X edges where scallop starts (leaves solid rim)
	//           Can be scalar (same both sides) or [min_x_reveal, max_x_reveal]
	//           Negative values extend scallop beyond cube bounds on that edge
	// y_reveal: distance from Y edges where scallop starts (leaves solid rim)
	//           Can be scalar (same both sides) or [min_y_reveal, max_y_reveal]
	//           Negative values extend scallop beyond cube bounds on that edge
	// corner_radius: radius for rounded corners of the scalloped regions
	
	dimensions = is_list(size) ? size : [size, size, size];
	x = dimensions[0];
	y = dimensions[1];
	z = dimensions[2];
	
	// Parse x_reveal as either scalar or [min, max]
	x_reveal_list = is_list(x_reveal) ? x_reveal : [x_reveal, x_reveal];
	x_reveal_min = x_reveal_list[0];
	x_reveal_max = x_reveal_list[1];
	
	// Parse y_reveal as either scalar or [min, max]
	y_reveal_list = is_list(y_reveal) ? y_reveal : [y_reveal, y_reveal];
	y_reveal_min = y_reveal_list[0];
	y_reveal_max = y_reveal_list[1];
	
	// Calculate scallop dimensions
	scallop_depth = (z - web_thickness) / 2;
	scallop_x = x - x_reveal_min - x_reveal_max;
	scallop_y = y - y_reveal_min - y_reveal_max;
	
	// Z size needs to extend beyond cube boundaries to ensure clean subtraction
	scallop_z = max(scallop_depth + corner_radius + eps, 2 * corner_radius + eps);
	
	// Calculate scallop positions in absolute coordinates
	// When center=true, account for the offset caused by asymmetric reveals
	// The scallop should be offset by (reveal_max - reveal_min) / 2 from center
	scallop_x_pos = center ? -scallop_x / 2 + (x_reveal_max - x_reveal_min) / 2 : x_reveal_min;
	scallop_y_pos = center ? -scallop_y / 2 + (y_reveal_max - y_reveal_min) / 2 : y_reveal_min;
	
	// Z positions: scallops extend beyond cube boundaries
	// Top scallop starts at web edge and extends upward
	// Bottom scallop extends downward from bottom web edge
	top_z = center ? web_thickness / 2 : web_thickness;
	bottom_z = center ? -web_thickness / 2 - scallop_z : -scallop_z + scallop_depth;
	
	difference() 
	{
		// Main cube (centered or not based on center parameter)
		cube(size=[x, y, z], center=center);
		
		// Only create scallops if there's actually material to remove
		if (scallop_depth > 0)
		{
			// Top scallop (cut from +Z side) - extends above the cube
			translate([scallop_x_pos, scallop_y_pos, top_z]) 
			{
				rounded_cube([scallop_x, scallop_y, scallop_z], 
						   r=corner_radius, center=false, $fn=$fn);
			}
			
			// Bottom scallop (cut from -Z side) - extends below the cube
			translate([scallop_x_pos, scallop_y_pos, bottom_z]) 
			{
				rounded_cube([scallop_x, scallop_y, scallop_z], 
						   r=corner_radius, center=false, $fn=$fn);
			}
		}
	}
}

// Creates a recessed honeycomb cutout (for subtracting from a panel)
// Parameters:
//   size: [width, height] or scalar for the cutout area
//   corner_radius: radius for rounded corners of the cutout boundary (default: 5.0)
//   cell_radius: radius of the hexagonal cells (default: 5.0)
//   wall_size: thickness of the walls between cells (default: 1.2)
//   cell_corner_radius: corner rounding radius for honeycomb cells (default: 1.2)
//   recess_depth: depth of the shallow recess on the surface (default: 1.0)
//   cutout_depth: total depth of the through-hole honeycomb pattern (default: 20.0)
//   panel_thickness: thickness of the panel being cut (used to position the recess, default: 4.0)
//   window_position: [x, y] absolute position of this window in the panel's coordinate system
//                    Used to align honeycomb patterns across multiple windows (default: [0, 0])
//   global_origin: [x, y] offset to shift the entire honeycomb pattern grid (default: [0, 0])
//                  Adjusting this shifts all windows' patterns together
//   invert: if true, creates solid hexagons instead of holes (default: true)
//   $fn: resolution for corner rounding (default: 30)
module recessed_honeycomb_cutout(
	size, 
	corner_radius=5.0, 
	cell_radius=5.0, 
	wall_size=1.2, 
	cell_corner_radius=1.2, 
	recess_depth=1.0, 
	cutout_depth=20.0, 
	panel_thickness=4.0,
	window_position=[0, 0],
	global_origin=[0, 0],
	invert=true,
	$fn=30
) 
{
	// Surface recess (shallow cutout visible from outside)
	if (recess_depth > 0.0)
	{
		translate([0, 0, panel_thickness - recess_depth]) 
			linear_extrude(height=recess_depth + eps) 
			{
				pvv_rounded_square(size=size, center=false, cr=corner_radius, $fn=$fn);
			}
	}

	// Deep honeycomb cutout (through-hole pattern)
	translate([0, 0, -cutout_depth/2]) 
		linear_extrude(height=cutout_depth, convexity=3) 
		{
			honeycomb_square(
				size=size, 
				window_position=window_position - global_origin, 
				corner_radius=corner_radius, 
				cell_radius=cell_radius, 
				wall_size=wall_size, 
				cell_corner_radius=cell_corner_radius, 
				invert=invert, 
				$fn=$fn
			);
		}
}

// Creates a 2D square with rounded corners
// Parameters:
//   size: [width, height] or scalar for square
//   center: if true, centers the square
//   cr: corner radius (default: 0 for sharp corners)
//   $fn: resolution for corner rounding
module pvv_rounded_square(size, center=false, cr=0, $fn) 
{
	// Handle size parameter (can be scalar or vector)
	dimensions = is_list(size) ? size : [size, size];
	width = dimensions[0];
	height = dimensions[1];
	
	if (cr <= 0) 
	{
		// No rounding, just create a regular square
		square(size=size, center=center);
	}
	else
	{
		// Ensure corner radius doesn't exceed half of smallest dimension
		safe_cr = min(cr, min(width, height) / 2);
		
		// Create rounded square using offset
		translate(center ? [0, 0] : [width/2, height/2])
		{
			offset(r=safe_cr, $fn=$fn)
			{
				square([width - 2*safe_cr, height - 2*safe_cr], center=true);
			}
		}
	}
}

// Creates a 2D square with rounded corners and honeycomb pattern
// Parameters:
//   size: [width, height] or scalar for square
//   center: if true, centers the square
//   corner_radius: radius for rounded corners (default: 0 for sharp corners)
//   cell_radius: radius of the hexagonal cells/holes (distance from center to vertex)
//   wall_size: thickness of the walls between cells
//   cell_corner_radius: corner rounding radius for honeycomb cells (0 for regular hexagons)
//   invert: if true, creates solid hexagons instead of honeycomb holes (default: false)
//   window_position: [x, y] absolute position of this window for pattern alignment (default: [0, 0])
//   $fn: resolution for corner rounding
module honeycomb_square(size, center=false, corner_radius=0, cell_radius, wall_size, cell_corner_radius=0, invert=false, window_position=[0, 0], $fn) 
{
	// Handle size parameter (can be scalar or vector)
	dimensions = is_list(size) ? size : [size, size];
	
	intersection()
	{
		// Rounded square boundary
		pvv_rounded_square(size=size, center=center, cr=corner_radius, $fn=$fn);
		
		// Honeycomb pattern
		translate(center ? [-dimensions[0]/2, -dimensions[1]/2] : [0, 0])
			honeycomb_cell_tiling_2d(
				cell_radius=cell_radius, 
				wall_size=wall_size, 
				size=size, 
				cr=cell_corner_radius,
				invert=invert,
				window_position=window_position,
				$fn=$fn
			);
	}
}

// Given a circle of radius r and a chord of length c,
// returns the distance from the center of the circle to the center of the chord
// Returns undef if the chord length exceeds the diameter
// This uses the Pythagorean theorem: d = sqrt(r^2 - (c/2)^2)
function chord_center_distance(r, c) = 
	c > 2 * r ? undef : sqrt(r * r - (c / 2) * (c / 2));

// Creates a 2D honeycomb tiling pattern (walls with hexagonal holes, or inverted)
// Parameters:
//   cell_radius: radius of the hexagonal cells/holes (distance from center to vertex)
//   wall_size: thickness of the walls between cells
//   size: [width, height] or scalar for the tiling area
//   cr: corner rounding radius (0 for regular hexagons)
//   invert: if true, creates solid hexagons instead of holes (default: false)
//   window_position: [x, y] absolute position of this window in the panel coordinate system
//                    The pattern is aligned so hexagons at position [0,0] would be centered at
//                    the global origin. This ensures multiple windows show aligned patterns.
//   $fn: resolution for corner rounding
module honeycomb_cell_tiling_2d(cell_radius, wall_size, size, cr=0, invert=false, window_position=[0, 0], $fn) 
{
	// Handle size parameter (can be scalar or vector)
	dimensions = is_list(size) ? size : [size, size];
	width = dimensions[0];
	height = dimensions[1];
	
	// Honeycomb geometry: flat-topped hexagons
	// - Horizontal spacing between columns: sqrt(3) * cell_radius
	// - Vertical spacing between rows: 1.5 * cell_radius
	// - Every other row is offset by half the column spacing
	col_spacing = sqrt(3) * cell_radius;
	row_spacing = 1.5 * cell_radius;
	
	// Calculate which hexagon column and row the window's origin falls into
	// This determines the offset needed to align patterns across windows
	start_col = floor(window_position[0] / col_spacing);
	start_row = floor(window_position[1] / row_spacing);
	
	// Calculate offset from the nearest grid point to align the pattern
	offset_x = window_position[0] - start_col * col_spacing;
	offset_y = window_position[1] - start_row * row_spacing;
	
	// Number of cells needed to cover the window (with margin)
	num_cols = ceil((width + offset_x) / col_spacing) + 2;
	num_rows = ceil((height + offset_y) / row_spacing) + 2;
	
	if (invert) 
	{
		// Inverted: create solid hexagons (holes in the boundary)
		intersection()
		{
			union()
			{
				for (row = [-1 : num_rows]) 
				{
					for (col = [-1 : num_cols]) 
					{
						// Determine if this row gets the half-column offset
						// Use absolute row index to ensure global alignment
						abs_row = start_row + row;
						x_shift = (abs_row % 2 == 0) ? 0 : col_spacing / 2;
						
						// Position relative to window origin
						x = col * col_spacing + x_shift - offset_x;
						y = row * row_spacing - offset_y;
						
						translate([x, y]) 
							honeycomb_hexagon(cell_radius - wall_size/2, cr, $fn);
					}
				}
			}
			square(size);
		}
	}
	else
	{
		// Normal: subtract hexagonal holes from a solid base
		intersection()
		{
			difference()
			{
				square([width + col_spacing, height + row_spacing]);
				
				for (row = [-1 : num_rows]) 
				{
					for (col = [-1 : num_cols]) 
					{
						abs_row = start_row + row;
						x_shift = (abs_row % 2 == 0) ? 0 : col_spacing / 2;
						
						x = col * col_spacing + x_shift - offset_x;
						y = row * row_spacing - offset_y;
						
						translate([x, y]) 
							honeycomb_hexagon(cell_radius - wall_size/2, cr, $fn);
					}
				}
			}
			square(size);
		}
	}
}

// Helper module to create a single hexagon (regular or rounded)
// Parameters:
//   radius: circumradius of the hexagon
//   cr: corner rounding radius (0 for regular hexagon), negative values will use smooth circles
//   $fn: resolution for corner rounding
module honeycomb_hexagon(radius, cr=0, $fn) 
{
	// Rotate by 30 degrees so flat sides are horizontal (not points)
	rotate([0, 0, 30])
	{
		if (cr < 0.0)
		{
			circle(r=radius * 0.866025, $fn=$fn);
		}
		else if (cr == 0) 
		{
			// Regular hexagon
			circle(r=radius, $fn=6);
		}
		else
		{
			// Rounded hexagon using offset
			// Ensure corner radius doesn't exceed the size that would cause inversion
			safe_cr = min(cr, radius * 0.75);
			
			// The offset operation expands outward, so we shrink the inner hexagon
			// by the corner radius amount to maintain wall thickness
			offset(r=safe_cr, $fn=$fn)
			{
				circle(r = radius - 1.1547 * safe_cr, $fn = 6); // PVV: 1.1547 = 2 / sqrt(3)
			}
		}
	}
}

// Creates a cylinder with 45-degree taper between two radii
// The height is automatically calculated as the difference between the radii (for 45-degree angle)
// Parameters:
//   r1: radius at the bottom (z=0)
//   r2: radius at the top (z=h)
//   center: if true, centers the cylinder along the Z axis
//   $fn: resolution for the cylinder
module cylinder_tapered45(r1, r2, center=false, $fn) 
{
	// Height is the absolute difference between radii for a 45-degree taper
	h = abs(r2 - r1);
	
	// Create the tapered cylinder
	cylinder(h=h, r1=r1, r2=r2, center=center, $fn=$fn);
}

// Creates a rounding tool - a cube with a cylindrical cutout at the origin
// Used to create rounded internal corners when subtracted from geometry
// Parameters:
//   size: [width, height, depth] or scalar for the cube dimensions (not centered)
//   r: radius of the cylindrical cutout
//   $fn: resolution for the cylinder
module rounding_tool(size, r, $fn)
{
	// Handle size parameter (can be scalar or vector)
	dimensions = is_list(size) ? size : [size, size, size];
	
	difference()
	{
		// Cube (not centered)
		cube(dimensions);
		
		// Subtract cylinder centered at origin, extending through entire cube height
		translate([0, 0, -eps])
			cylinder(r=r, h=dimensions[2] + 2*eps, $fn=$fn);
	}
}


// Creates a cylinder with rounded caps/edges
// Parameters:
//   h: height of the cylinder (measured to center of end cap spheres)
//   r, d: radius or diameter of the cylinder body
//   r1, r2, d1, d2: bottom and top radii/diameters (for tapered cylinders)
//   cap_r: radius of the rounding on both caps (default: r/10, 0 = no rounding)
//          Ignored if cap_r1 or cap_r2 are specified
//   cap_r1: radius of the rounding on the bottom cap (overrides cap_r if specified)
//   cap_r2: radius of the rounding on the top cap (overrides cap_r if specified)
//   center: if true, centers the cylinder along the Z axis
//   $fn: resolution for the cylinder and spheres
module cylinder_rounded(h, r, d, r1, r2, d1, d2, cap_r, cap_r1, cap_r2, center=false, cr_fn = 15, $fn) 
{
	// Determine radii from parameters
	bottom_r = r1 != undef ? r1 :
			   d1 != undef ? d1/2 :
			   r != undef ? r :
			   d != undef ? d/2 : undef;
	
	top_r = r2 != undef ? r2 :
			d2 != undef ? d2/2 :
			r != undef ? r :
			d != undef ? d/2 :
			bottom_r;
	
	// Determine cap radii - cap_r1/cap_r2 override cap_r if specified
	avg_r = (bottom_r + top_r) / 2;
	default_cap_r = cap_r != undef ? cap_r : avg_r / 10;
	
	actual_cap_r1 = cap_r1 != undef ? cap_r1 : default_cap_r;
	actual_cap_r2 = cap_r2 != undef ? cap_r2 : default_cap_r;
	
	// Special case: if both cap radii are exactly 0, create a regular cylinder
	if (actual_cap_r1 == 0 && actual_cap_r2 == 0) 
	{
		cylinder(h=h, r1=bottom_r, r2=top_r, center=center, $fn=$fn);
	}
	else
	{
		// Ensure cap radii don't exceed body radius or available height
		safe_cap_r1 = actual_cap_r1 > 0 ? min(actual_cap_r1, bottom_r, h/2) : 0;
		safe_cap_r2 = actual_cap_r2 > 0 ? min(actual_cap_r2, top_r, h/2) : 0;
		
		// Calculate offset for centering
		z_offset = center ? -h/2 : 0;
		
		translate([0, 0, z_offset]) 
		{
			// Use hull to blend between the caps
			if (safe_cap_r1 > 0 && safe_cap_r2 > 0)
			{
				// Both caps rounded
				hull() 
				{
					// Bottom cap - ring of spheres
					translate([0, 0, safe_cap_r1])
						rotate_extrude(convexity=10, $fn=$fn)
							translate([bottom_r - safe_cap_r1, 0, 0])
								circle(r=safe_cap_r1, $fn=cr_fn);
					
					// Top cap - ring of spheres
					translate([0, 0, h - safe_cap_r2])
						rotate_extrude(convexity=10, $fn=$fn)
							translate([top_r - safe_cap_r2, 0, 0])
								circle(r=safe_cap_r2, $fn=cr_fn);
				}
			}
			else if (safe_cap_r1 > 0 && safe_cap_r2 == 0)
			{
				// Only bottom cap rounded
				hull()
				{
					// Bottom cap - ring of spheres
					translate([0, 0, safe_cap_r1])
						rotate_extrude(convexity=10, $fn=$fn)
							translate([bottom_r - safe_cap_r1, 0, 0])
								circle(r=safe_cap_r1, $fn=cr_fn);
					
					// Top cap - flat edge (sharp cylinder edge)
					translate([0, 0, h])
						cylinder(h=eps, r=top_r, center=false, $fn=$fn);
				}
			}
			else if (safe_cap_r1 == 0 && safe_cap_r2 > 0)
			{
				// Only top cap rounded
				hull()
				{
					// Bottom cap - flat edge (sharp cylinder edge)
					cylinder(h=eps, r=bottom_r, center=false, $fn=$fn);
					
					// Top cap - ring of spheres
					translate([0, 0, h - safe_cap_r2])
						rotate_extrude(convexity=10, $fn=$fn)
							translate([top_r - safe_cap_r2, 0, 0])
								circle(r=safe_cap_r2, $fn=cr_fn);
				}
			}
		}
	}
}


preview_eps = ($preview) ? 0.01 : 0.0;

echo(flap_pitch_radius=flap_pitch_radius);
echo(spool_outer_radius=spool_outer_radius);

fit_3dprint_flap_hole_radius           = 0.05;
fit_3dprint_bearing_3DPrint_rad        = 0.06;
fit_3dprint_bearing_3DPrint_z          = 0.02;
fit_3dprint_motor_shaft_radius         = 0.120;
fit_3dprint_motor_shaft_flats          = 0.120;
fit_3dprint_allen_key_rad              = 0.125;
fit_3dprint_28byj48_mount_outer_radius = 0.125;
fit_3dprint_motor_surround             = 0.06;
fit_3dprint_axel_nub_radius            = -0.025; // interference fit
fit_3dprint_locator_pin_radius         = 0.05;
fit_3dprint_spool_alignment_pin        = 0.04;
fit_3dprint_axel_pin_rad_gap           = -0.05; // interference fit
fit_3dprint_tower_pocket_expand_by     = 0.1;

coupler_flange_bore_gap       = 0.3;
coupler_flange_face_gap       = round_to_layer_nearest(0.0); // There is usually enough axial play in the motor shaft that this can be zero tolerance.
m3_torque_pin_radius_gap = 0.20; // There is a fair amount of error in the final assembled torque pins.

hardware_color = [0.75, 0.75, 0.75];
flange_color = [1.0, 0.0, 0.0];

outer_exclusion_gap = -1.0;
collapsed_exclusion_gap = 11.0;

// Adjustments for 3D printing filament shrinkage.  These are the (measured size / cad size) after printing a test model. 
// The compensating scale applied is scale([1/filament_shrink_compensation_xy, 1/filament_shrink_compensation_xy, 1/filament_shrink_compensation_z])
// These values were determined empirically for Bambu PLA-CF...
filament_shrink_compensation_xy = 0.998;
filament_shrink_compensation_z = 1.0; // Z isn't as succeptible to shrinkage as X and Y are.
module apply_filament_shrinkage_compensation()
{
	scale([1/filament_shrink_compensation_xy, 1/filament_shrink_compensation_xy, 1/filament_shrink_compensation_z])
	{
		children();
	}
}

m3x3_insert_rad = 4.5 / 2; // These are for the wider (5mm) 3m inserts.
m3x6_insert_rad = 4.5 / 2;
m3x6_insert_depth = 6.0;
m3_thru_hole_rad = 3.3 / 2;
m3_flathead_rad = 6.0 / 2;
m3_flathead_taper_depth = 3.0;
m3_flathead_counterbore_depth = 0.6;

// M3 socket head cap screw dimensions (ISO 4762 / DIN 912)
m3_cap_screw_head_diameter = 5.5;
m3_cap_screw_head_height = 3.0;
m3_cap_screw_shaft_diameter = 3.0;
m3_cap_screw_socket_diameter = 2.5;
m3_cap_screw_socket_depth = 1.5;

// M3 nylock nut dimensions (ISO 7040 / DIN 985)
m3_nylock_nut_width_flats = 5.5;        // Width across flats (wrench size)
m3_nylock_nut_width_corners = 6.35;     // Width across corners
m3_nylock_nut_height = 4.0;             // Total height including nylon insert
m3_nylock_nut_nylon_height = 1.5;       // Height of nylon insert portion
m3_nylock_nut_hole_diameter = 3.0;      // Through hole diameter

module m3_flathead_hole(depth)
{
	union()
	{
		cylinder(h=depth, r=m3_thru_hole_rad, center=false, $fn=30);
		translate([0, 0, -eps])
			cylinder(h=m3_flathead_counterbore_depth + 2.0*eps, r=m3_flathead_rad, center=false, $fn=30);
		translate([0, 0, m3_flathead_counterbore_depth])
			cylinder(h=m3_flathead_taper_depth, r1=m3_flathead_rad, r2=0, center=false, $fn=30);
	}
}


// Renders an M3 socket head cap screw
// Parameters:
//   length: total length of the screw (from bottom of head to tip of shaft)
//   $fn: resolution for cylinders
module m3_cap_screw(length)
{
	color(hardware_color)
	{
		// Socket head cap (with hex socket depression)
		difference()
		{
			cylinder(h=m3_cap_screw_head_height, r=m3_cap_screw_head_diameter/2, center=false, $fn=60);
			
			// Hex socket (simplified as circular depression)
			translate([0, 0, m3_cap_screw_head_height - m3_cap_screw_socket_depth])
				cylinder(h=m3_cap_screw_socket_depth + eps, r=m3_cap_screw_socket_diameter/2, center=false, $fn=6);
		}
		
		// Screw shaft
		translate([0, 0, -length])
			cylinder(h=length, r=m3_cap_screw_shaft_diameter/2, center=false, $fn=30);
	}
}

// Renders an M3 nylock nut (nylon insert lock nut)
// Parameters:
//   $fn: resolution for cylinders (hex is always rendered with 6 sides)
module m3_nylock_nut()
{
	difference()
	{
		union()
		{
			// Metal hex portion
			color(hardware_color)
			translate([0, 0, 0])
				cylinder(h=m3_nylock_nut_height - m3_nylock_nut_nylon_height, 
						r=m3_nylock_nut_width_corners/2, 
						center=false, 
						$fn=6);
			
			// Nylon insert portion (blue/white colored)
			color([0.7, 0.8, 1.0])
			translate([0, 0, m3_nylock_nut_height - m3_nylock_nut_nylon_height])
				cylinder(h=m3_nylock_nut_nylon_height, 
						r=m3_nylock_nut_width_corners/2, 
						center=false, 
						$fn=6);
		}
		
		// Through hole (no threads modeled)
		translate([0, 0, -eps])
			cylinder(h=m3_nylock_nut_height + 2*eps, 
					r=m3_nylock_nut_hole_diameter/2, 
					center=false, 
					$fn=30);
	}
}

m4_insert_rad = 5.5 / 2; // Heat-set insert for M4 screws
m4_insert_depth = 6.0;
m4_thru_hole_rad = 4.3 / 2;
m4_flathead_rad = 8.0 / 2;
m4_flathead_taper_depth = 4.0;
m4_flathead_counterbore_depth = 0.6;

module m4_flathead_hole(depth)
{
	union()
	{
		cylinder(h=depth, r=m4_thru_hole_rad, center=false, $fn=30);
		translate([0, 0, -eps])
			cylinder(h=m4_flathead_counterbore_depth + 2.0*eps, r=m4_flathead_rad, center=false, $fn=30);
		translate([0, 0, m4_flathead_counterbore_depth])
			cylinder(h=m4_flathead_taper_depth, r1=m4_flathead_rad, r2=0, center=false, $fn=30);
	}
}



per_flap_radial_elongation = 0.015; // This is how much to elongate the flap holes radially to create a capsule shape when num_flaps > 58.  Empirically determined.
flap_hole_capsule_elongation = (num_flaps > 58) ? (per_flap_radial_elongation * (num_flaps - 58)) : 0.0;

per_flap_extra_barrel_clearance = 0.1;
extra_barrel_clearance = (num_flaps > 58) ? (per_flap_extra_barrel_clearance * (num_flaps - 58)) : 0.0;

echo(spool_width = spool_width);
pvv_spool_width = round_to_layer_floor(spool_width);
echo(pvv_spool_width = pvv_spool_width);
spool_barrel_radius_clearance = 0.2;
spool_barrel_outer_radius = spool_barrel_radius_clearance + flap_pitch_radius - (spool_outer_radius - flap_pitch_radius) - extra_barrel_clearance;
echo(spool_barrel_outer_radius = spool_barrel_outer_radius);
spool_barrel_thickness = 0.8;
spool_barrel_inner_radius = spool_barrel_outer_radius - spool_barrel_thickness;
spool_barrel_od = 2 * spool_barrel_outer_radius;
spool_barrel_id = 2 * spool_barrel_inner_radius;
flap_hole_radius_3d_print = flap_hole_radius + fit_3dprint_flap_hole_radius;
//echo(flap_hole_radius_3d_print=flap_hole_radius_3d_print);
pvv_inner_panel_to_panel_width = round_to_layer_nearest(58.0); // (58.0) This is the distance between the inner faces of the left and right panels, which determines the maximum width of the spool that can fit inside.  It's a critical dimension for ensuring the spool fits properly.
echo(pvv_inner_panel_to_panel_width = pvv_inner_panel_to_panel_width);
centering_offset = (pvv_inner_panel_to_panel_width - pvv_spool_width) / 2.0;
echo(centering_offset = centering_offset);
spool_left_offset = round_to_layer_nearest(centering_offset);
echo(spool_left_offset = spool_left_offset);


bearing_MR1282RS_od = 12.0;
bearing_MR1282RS_id = 8.0;
bearing_MR1282RS_thickness = 3.5;
bearing_MR1282RS_retainer_od = bearing_MR1282RS_od - 0.2;
bearing_MR1282RS_retainer_or = bearing_MR1282RS_retainer_od / 2;
bearing_MR1282RS_retainer_z0 = bearing_MR1282RS_thickness + fit_3dprint_bearing_3DPrint_z;
bearing_MR1282RS_retainer_thickness = 1.0;
bearing_MR1282RS_retainer_z1 = bearing_MR1282RS_retainer_z0 + bearing_MR1282RS_retainer_thickness;
bearing_axle_clearance_radius = bearing_MR1282RS_id / 2 + 0.5;
bearing_axle_clearance_depth = 9.0; // abs depth of axle hole

m28byj48_mount_outer_radius = 3.5;
m28byj48_mount_hole_radius = 4.2/2;
m28byj48_shaft_collar_height = 1.5;
m28byj48_shaft_height = 10;
m28byj48_shaft_slotted_width = 3;
m28byj48_shaft_slotted_height = 6;
m28byj48_backpack_width = 14.6;
m28byj48_backpack_height = 16;

motor_coupler_flange_od = 22.0;
motor_coupler_height = 12.0;
motor_coupler_flange_thickness = 2.0;
motor_coupler_shank_height = 10.0;
motor_coupler_shank_od = 10.0;
motor_coupler_hole_pattern_radius = 8.0;
motor_coupler_hole_od = 3.0;
motor_coupler_height_off_motor_face = 14.0;
motor_coupler_center_hole_od = 5.0;
motor_coupler_center_hole_effective_depth = 4.0; // depth to the motor shaft (when fully inserted)
axel_pin_rad = motor_coupler_center_hole_od/2.0 - fit_3dprint_axel_pin_rad_gap;
axel_pin_height = 3.8;

// When set true, this uses a 22mm OD x 5mm ID x 12mm depth coupling with a 4-hole M3 screw pattern, and (4) M3x6mm cap screws and M3 nylocks.
// The flange couplers are readily available from multiple sellers online.  For example: https://www.amazon.com/dp/B08334MFVT?th=1
// When set false, it uses the "standard" press fit coupling.
// Using the flange coupling has several benefits: 1) no press-fit makes for quick and easy assembly and disassembly, 2) much longer torque arm than the motor shaft flats
// means (hopefully) never having to worry about the press-fit flats in the spool plastic getting rounded out over time.  And some negatives: 1) more expensive, adds
// a couple bucks to the per-module cost, and 2) slightly longer initial assembly time.
use_motor_coupler = true;

// When set true, this adds an access hole for a 2.5mm Allen key that can be used to back-drive the spool and motor assembly.  This was
// slightly useful during development as it made for an easy way to test the spool rotation without power.  However, it puts what feels like
// a substantial amount of stress on the plastic gears, so is probably not recommended for general use...
use_2p5_allen_key_access_hole = false;

frame_left_sidewall_thickness = round_to_layer_nearest(3.0);
echo(frame_left_sidewall_thickness = frame_left_sidewall_thickness);
frame_right_sidewall_thickness = round_to_layer_nearest(3.0);
echo(frame_right_sidewall_thickness = frame_right_sidewall_thickness);

pvv_module_width = pvv_inner_panel_to_panel_width + frame_left_sidewall_thickness + frame_right_sidewall_thickness;

num_spokes = 6;
spoke_thickness = 0.8;
spoke_hub_od = (use_motor_coupler) ? 25.2 : 22.0;
//spoke_hub_id = 18.0;
spoke_hub_radius = spoke_hub_od/2;
spoke_capital_base_thickness = 0.8;
spoke_capital_width = 3.0;
spoke_capital_od_thickness = spool_barrel_inner_radius - chord_center_distance(spool_barrel_inner_radius, spoke_capital_width);
motor_chasis_top_height = (m28byj48_chassis_height - frame_right_sidewall_thickness) + 0.2; // (16.2) distance from the inside right wall to the top of the motor chasis (0.2 is to inset the back of the motor slightly from the right outside wall)
echo(motor_chasis_top_height = motor_chasis_top_height);

offset_of_shaft_flats_from_motor_chasis_top = m28byj48_shaft_height - m28byj48_shaft_slotted_height;
motor_shaft_fitment_gap = 0.4; // gap between start of the shaft flats and the spool mating surface (when not using flange coupler).

// distance from the nub (left) side of the spool to the end of the spokes (also the mating surface when not using motor flange coupler)...
spool_motor_mating_depth = round_to_layer_nearest(pvv_inner_panel_to_panel_width - spool_left_offset - motor_chasis_top_height - offset_of_shaft_flats_from_motor_chasis_top - motor_shaft_fitment_gap);
spoke_size_z = spool_motor_mating_depth; //pvv_spool_width/2;
spoke_inner_chord_rad_offset = (spoke_hub_radius - chord_center_distance(spoke_hub_radius, spoke_capital_width));
spoke_radius = spool_barrel_inner_radius + spoke_inner_chord_rad_offset;
magnet_od = 4.0;
magnet_or = magnet_od / 2;
magnet_tight_or = magnet_or - 0.05;
magnet_recess = 0.4;
magnet_thruhole_or = magnet_tight_or - 0.15;
magnet_bottom_thruhole_or = magnet_tight_or - 0.25;
magnet_thickness = 2.5;
magnet_depth_fit = 0.1;
magnet_holder_fingers_thickness = 2.0;
magnet_holder_fingers_gap = 0.8;
magnet_holder_interfinger_gap = 0.3;
magnet_holder_outer_wall_thickness = 0.8;
magnet_holder_fingers_or = magnet_tight_or + magnet_holder_fingers_thickness;
magnet_holder_outer_body_ir = magnet_holder_fingers_or + magnet_holder_fingers_gap;
magnet_holder_body_or = magnet_holder_outer_body_ir + magnet_holder_outer_wall_thickness;
magnet_holder_body_floor_thickness = 1.0;
magnet_holder_body_inner_size_z = magnet_thickness * 3;
magnet_holder_body_size_z = magnet_holder_body_inner_size_z + magnet_holder_body_floor_thickness;
magnet_holder_overdrill_size_z = 4;
magnet_holder_num_fingers = 4;
echo(spool_barrel_inner_radius = spool_barrel_inner_radius);

max_motor_surround_nominal_radius = 28.8854; // when num_flaps == 58
motor_surround_outer_radius = min(spool_barrel_inner_radius, max_motor_surround_nominal_radius) - 0.8; // Some clearance between the motor surround and the inner surface of the spool barrel

spool_right_offset = pvv_inner_panel_to_panel_width - spool_left_offset - pvv_spool_width;
echo(spool_right_offset = spool_right_offset);

allen_key_size = 2.5;
allen_key_flat_rad = allen_key_size / 2;
allen_key_outer_radius = allen_key_flat_rad * 1.1547 + fit_3dprint_allen_key_rad;


//wtf = spool_motor_mating_offset;
//color([1,0,0]) translate([0,0,-wtf]) cylinder(r = 1, h = wtf, $fn=30);

module pvv_flap_spool_core_2d()
{
	difference() 
	{
		circle(r=spool_outer_radius, $fn=240);
		for (i = [0 : num_flaps - 1]) 
		{
			if (flap_hole_capsule_elongation > 0.0)
			{
				rotate([0, 0, 360/num_flaps*i])
				{
					hull()
					{
						translate([flap_pitch_radius, 0]) circle(r=flap_hole_radius_3d_print, $fn=30);
						translate([flap_pitch_radius - flap_hole_capsule_elongation, 0]) circle(r=flap_hole_radius_3d_print, $fn=30);
					}
				}
			}
			else
			{
				translate([cos(360/num_flaps*i)*flap_pitch_radius, sin(360/num_flaps*i)*flap_pitch_radius]) circle(r=flap_hole_radius_3d_print, $fn=30);
			}
		}
	}
}

module spool_alignment_pin(is_subtract=false)
{
	spool_circumference = 2 * PI * spool_barrel_outer_radius;
	fit_3dprint_spool_alignment_pin_angle = 360 * fit_3dprint_spool_alignment_pin / spool_circumference;
	fit_angle = ( is_subtract ) ? fit_3dprint_spool_alignment_pin_angle : 0.0;
	echo(fit_3dprint_spool_alignment_pin_angle = fit_3dprint_spool_alignment_pin_angle);
	cap_r = (is_subtract) ? 0.0 : 0.0;
	spool_alignment_pin_length = (is_subtract) ? (spool_barrel_thickness + 0.1) : spool_barrel_thickness;
	z = (is_subtract) ? (pvv_spool_width - spool_thickness_3dprint) + preview_eps : 0.0;
	spool_alignment_pin_rad = (is_subtract) ? 0.75 : 0.7;

	translate([0,0,z]) tube(h=spool_thickness_3dprint, ir = spool_barrel_outer_radius - spool_alignment_pin_length - preview_eps, or = spool_barrel_outer_radius + preview_eps, center=false, pie_angle=360/num_flaps + fit_angle, $fn=240);
}

module pvv_right_flap_spool()
{
	difference()
	{
		linear_extrude(spool_thickness_3dprint, convexity=10)
		{ 
			difference() 
			{
				pvv_flap_spool_core_2d();
				circle(r = spool_barrel_outer_radius, $fn = 240);
				//flap_spool_home_indicator(num_flaps, flap_hole_radius, flap_hole_separation, flap_spool_outset, height=0);
			}
		}
	}
	spool_alignment_pin(is_subtract=false);
}

module pvv_left_flap_spool()
{
	linear_extrude(spool_thickness_3dprint, convexity=10)
	{ 
		difference() 
		{
			pvv_flap_spool_core_2d();

			circle(r = spool_barrel_outer_radius, $fn = 240);

			//flap_spool_home_indicator(num_flaps, flap_hole_radius, flap_hole_separation, flap_spool_outset, height=0);
		}
	}

	difference()
	{
		tube(h=pvv_spool_width, 
			 ir=spool_barrel_inner_radius, 
			 or=spool_barrel_outer_radius, 
			 center=false, 
			 $fn = 240);
		spool_alignment_pin(is_subtract=true);
	}

	motor_shaft_radius = m28byj48_shaft_radius + fit_3dprint_motor_shaft_radius;

	motor_chasis_top_z = - spool_left_offset +  pvv_inner_panel_to_panel_width - motor_chasis_top_height;
	//echo (motor_chasis_top_z = motor_chasis_top_z);
	coupler_depth = motor_coupler_height_off_motor_face + coupler_flange_face_gap;
	coupler_pocket_bottom_z = round_to_layer_floor(motor_chasis_top_z - coupler_depth);
	echo (coupler_pocket_bottom_z = coupler_pocket_bottom_z);

	difference()
	{
		cylinder(r = spoke_hub_radius, h = spoke_size_z, $fn = 128);
		translate([0,0,-eps]) cylinder(r = bearing_MR1282RS_od / 2 + fit_3dprint_bearing_3DPrint_rad, h = bearing_MR1282RS_retainer_z0, $fn = 128);
		cylinder(r = bearing_MR1282RS_retainer_or, h = bearing_MR1282RS_retainer_z1, $fn = 128);
		translate([0,0,bearing_MR1282RS_retainer_z1]) cylinder_tapered45(r1 = bearing_MR1282RS_retainer_or, r2 = bearing_axle_clearance_radius, $fn = 128);
		cylinder(r = bearing_axle_clearance_radius, h = bearing_axle_clearance_depth, $fn = 64);
		echo(motor_shaft_radius = motor_shaft_radius);
		translate([0,0,bearing_axle_clearance_depth]) cylinder_tapered45(r1 = bearing_axle_clearance_radius, r2 = allen_key_outer_radius, $fn = 64);
		// motor shaft hole...
		motor_shaft_depth_extra = 1.0;
		motor_shaft_hole_depth = m28byj48_shaft_slotted_height + motor_shaft_depth_extra; // spoke_size_z + eps;
		if (use_motor_coupler)
		{
			translate([0, 0, coupler_pocket_bottom_z])
			{
				linear_extrude(motor_chasis_top_z - coupler_pocket_bottom_z, convexity=10)
				{
					flange_bore_negative_rad = motor_coupler_flange_od/2.0 + coupler_flange_bore_gap;
					circle(r=flange_bore_negative_rad, $fn=120);
				}
			}

			for (i = [0 : 3])
			{
				m3_torque_pin_pocket_depth = m3_cap_screw_head_height + 1.0;
				torque_pin_pocket_bottom_z = round_to_layer_floor(motor_chasis_top_z - motor_coupler_height_off_motor_face - m3_torque_pin_pocket_depth);
				rotate([0, 0, i * 90]) translate([motor_coupler_hole_pattern_radius, 0, torque_pin_pocket_bottom_z])
				{
					cylinder(r = m3_cap_screw_head_diameter / 2.0 + m3_torque_pin_radius_gap, h = m3_torque_pin_pocket_depth, $fn = 60);
				}
			}

		}
		else
		{
			translate([0, 0, spoke_size_z - motor_shaft_hole_depth]) rotate([0, 0, 90])
			{
				linear_extrude(motor_shaft_hole_depth, convexity=10)
				{ 
					intersection() 
					{
						circle(r=motor_shaft_radius, $fn=50);
						square([motor_shaft_radius*2, 3.0 + 2.0*fit_3dprint_motor_shaft_flats], center=true);
					}
				}
			}
		}

		// Allen key receiver...
		base_of_allen_key_receiver = abs(bearing_axle_clearance_radius - allen_key_outer_radius) + bearing_axle_clearance_depth;
		allen_key_receiver_depth = (use_motor_coupler) ? (10 - allen_key_outer_radius) : (spoke_size_z - base_of_allen_key_receiver - motor_shaft_hole_depth);
		allen_key_receiver_z_base = base_of_allen_key_receiver + allen_key_receiver_depth/2;
		translate([0, 0, allen_key_receiver_z_base]) cylinder(r = allen_key_outer_radius, h = allen_key_receiver_depth + 2*eps, center = true, $fn = 6);
		if (use_motor_coupler)
		{
			translate([0, 0, allen_key_receiver_z_base + allen_key_receiver_depth/2]) cylinder_tapered45(r1 = allen_key_outer_radius, r2 = 0, $fn = 6);
		}
	}

	if (use_motor_coupler)
	{
		translate([0, 0, coupler_pocket_bottom_z])
		{
			cylinder_rounded(r = axel_pin_rad, h = axel_pin_height, cap_r1=0, cap_r2=1, cr_fn=15, center = false, $fn = 60);
		}
	}

	difference()
	{
		union()
		{
			// Create multiple spokes distributed evenly around the hub
			for (i = [0 : num_spokes - 1]) 
			{
				rotate([0, 0, (i + 0.5) * 360 / num_spokes])
					translate([spoke_radius/2 + spoke_hub_radius/2 - spoke_inner_chord_rad_offset, 0, spoke_size_z/2]) 
					rotate([0,90,90])
						scalloped_cube([spoke_size_z, spoke_radius - spoke_hub_radius, spoke_capital_width],
							web_thickness=spoke_thickness,
							x_reveal=[spoke_capital_base_thickness,-10],
							y_reveal=[0,spoke_capital_od_thickness],
							corner_radius=(spoke_capital_width-spoke_thickness) / 2,
							center=true, $fn=64);
			}

			// Hole for press fit magnet, 90 degrees from home flap position
			linear_extrude(magnet_holder_body_size_z, convexity=10)
			{ 
				translate([0, -magnet_hole_offset]) 
				{
					// Magnet holder body
					circle(r=magnet_holder_body_or, $fn=64);
				}
			}
		}

		translate([0, -magnet_hole_offset, -eps]) 
		{
			// Magnet holder fingers...
			cylinder(r = magnet_bottom_thruhole_or, h = magnet_holder_body_size_z + magnet_holder_overdrill_size_z, $fn = 64);
			cylinder(r = magnet_thruhole_or, h = magnet_thickness, $fn = 64);
			translate([0,0,magnet_recess]) cylinder(r = magnet_tight_or, h = magnet_thickness + magnet_depth_fit, $fn = 64);
			
			tube(or=magnet_holder_outer_body_ir, ir=magnet_holder_fingers_or, h = magnet_holder_body_inner_size_z, $fn=64);
			
			// Cut out radial fingers
			for (i = [0 : magnet_holder_num_fingers - 1]) 
			{
				rotate([0, 0, i * 360 / magnet_holder_num_fingers])
					translate([0, -magnet_holder_interfinger_gap/2, 0])
						cube([magnet_holder_outer_body_ir - eps, magnet_holder_interfinger_gap, magnet_holder_body_inner_size_z]);
			}
		}
	}
}

echo(front_forward_offset = front_forward_offset); // This is the distance from the center of rotation to the back face of the front enclosure panel (where the hanging flaps rest vertically against the flap hold [back of the front panel])
//echo(enclosure_height_lower = enclosure_height_lower);
//echo(enclosure_height_upper = enclosure_height_upper);
//echo(enclosure_height = enclosure_height);
//echo(enclosure_length = enclosure_length);


module draw_motor()
{
	translate([0, 0, frame_left_sidewall_thickness - pcb_board_recess_depth]) rotate([0, 0, -90]) 
	{
		Stepper28BYJ48();
	}
}

module draw_flange_coupler()
{
	difference()
	{
		union()
		{
			cylinder(r = motor_coupler_flange_od / 2, h = motor_coupler_flange_thickness, $fn = 120);
			translate([0,0,motor_coupler_flange_thickness]) cylinder(r = motor_coupler_shank_od / 2, h = motor_coupler_shank_height, $fn = 120);
		}
		
		// 4 hole mounting pattern (evenly distributed at 90-degree intervals)
		for (i = [0 : 3])
		{
			rotate([0, 0, i * 90])
				translate([motor_coupler_hole_pattern_radius, 0, -eps])
					cylinder(r = motor_coupler_hole_od / 2, h = motor_coupler_flange_thickness + 2*eps, $fn = 30);
		}
		
		// Center hole for motor shaft access
		translate([0, 0, -eps])
			cylinder(r = motor_coupler_center_hole_od / 2, h = motor_coupler_height + 2*eps, $fn = 60);
	}
}

module draw_motor_coupler()
{
	color(flange_color) draw_flange_coupler();
	for (i = [0 : 3])
	{
		rotate([0, 0, i * 90]) translate([motor_coupler_hole_pattern_radius, 0, 0])
		{
			rotate([180,0,0]) m3_cap_screw(6);
			translate([0,0,motor_coupler_flange_thickness]) rotate([0, 0, 30]) m3_nylock_nut();
		}
	}
}


module draw_pcb()
{
	translate([0, 0, frame_left_sidewall_thickness - pcb_board_recess_depth]) rotate([0, 0, -90]) 
	{
		pcb(pcb_to_spool);
		//Stepper28BYJ48();

		//%linear_extrude(height=pcb_thickness) 
		//{
		//    difference() 
		//    {
		//        translate([-pcb_edge_to_hole_x, -pcb_height + pcb_edge_to_hole_y]) 
		//        {
		//            square([pcb_length, pcb_height]);
		//        }
		//        circle(r=pcb_hole_radius, $fn=30);
		//        translate([pcb_hole_to_bolt_hole_x, -pcb_hole_to_bolt_hole_y]) 
		//        {
		//            circle(r=pcb_bolt_hole_radius, $fn=30);
		//        }
		//    }
		//}
	}
}





front_panel_thickness = round_to_layer_nearest(3.0);
echo(front_panel_thickness = front_panel_thickness);
pvv_front_forward_offset = front_forward_offset; // This is distance from the origin to the INSIDE front panel surface!  front_forward_offset (28.5196)
pvv_enclosure_height = enclosure_height + 3.0; // enclosure_height (143.527 scott)
pvv_enclosure_length = enclosure_length + 10.0; // enclosure_length (50.2696 scott)
pvv_enclosure_height_lower = enclosure_height_lower - 1.0; // enclosure_height_lower (79.6386 scott)

pcb_board_recess_depth = 0.8;
pcb_pocket_offset = 1.0;           // Offset distance for PCB pocket
pcb_pocket_corner_radius = 1.0;    // Corner rounding radius for PCB pocket

// Accessory mounting blocks...
accessory_mounting_block_width  = 10;
accessory_mounting_block_height = 10;
accessory_mounting_block_depth  = 20;
accessory_middle_mounting_block_depth  = 7;

motor_shaft_collar_radius = m28byj48_shaft_collar_radius;

axel_nub_flange_size_z = round_to_layer_floor(spool_left_offset); // This is a critical dimension to ensure proper centering of the spool
echo(axel_nub_flange_size_z = axel_nub_flange_size_z);
axel_nub_flange_radius = bearing_MR1282RS_id / 2 + 0.25; // motor_shaft_collar_radius;
axel_nub_radius = bearing_MR1282RS_id / 2 - fit_3dprint_axel_nub_radius;
axel_nub_size_z = bearing_MR1282RS_thickness + 2.0;

pvv_front_window_width = round_to_layer_ceil(front_window_width); // (front_window_width, or 55.9) rounded to layer_size_3dprint
echo(pvv_front_window_width = pvv_front_window_width);

pvv_front_window_height = front_window_height; // (front_window_height, or 108.649)
pvv_front_window_lower = front_window_lower; // (front_window_lower, or 67.349)
pvv_front_window_left_bezel_size = round_to_layer_nearest(1.0); // 1.0 is centered
pvv_front_window_right_bezel_size = pvv_inner_panel_to_panel_width - pvv_front_window_width - pvv_front_window_left_bezel_size;
echo(pvv_front_window_right_bezel_size = pvv_front_window_right_bezel_size);
pvv_right_window_inset = pvv_front_window_right_bezel_size + frame_right_sidewall_thickness;            
pvv_left_window_inset = pvv_front_window_left_bezel_size + frame_left_sidewall_thickness;            
s_bUseFlapTopWindowReveal = false;

pvv_enclosure_width = pvv_inner_panel_to_panel_width + frame_left_sidewall_thickness + frame_right_sidewall_thickness; // enclosure_width;

// 58 mm inner width between sidewalls (pvv_inner_panel_to_panel_width)
// 55.2 mm measured window width, 1.8 mm offset from left (pvv_front_window_width in the original)
// 1.8mm nub flange offset
// 1.5 mm offset from left wall to spool
// spool width 54.1 mm
//pcb_hole_radius = 9.4/2;            // m28byj48_shaft_collar_radius
//pcb_bolt_hole_radius = 4.3/2;       // M4

//$vpf = 22.5; // FOV
//$vpd = 715; // viewport distance
//// viewport height of 1200 !!  with these setting, orthographic view, it's pretty close to 1:1, but not quite (I don't think the pixels on this monitor are prefectly square)

pvv_distance_to_back = pvv_enclosure_length - pvv_front_forward_offset;
echo(outer_exclusion_radius = outer_exclusion_radius);

pvv_left_panel_extension = outer_exclusion_radius - pvv_distance_to_back + accessory_middle_mounting_block_depth;
echo(pvv_left_panel_extension = pvv_left_panel_extension);

left_inside_wall_additional_reinforcement_thickness = round_to_layer_nearest(1.0);
left_sidewall_combined_thickness = frame_left_sidewall_thickness + left_inside_wall_additional_reinforcement_thickness;

right_inside_wall_additional_reinforcement_thickness = round_to_layer_nearest(1.0);
right_sidewall_combined_thickness = frame_right_sidewall_thickness + right_inside_wall_additional_reinforcement_thickness;

tower_width = 16.0;
tower_depth = 11.0;
tower_height = pvv_inner_panel_to_panel_width;

// pcb connector cutout...
pcb_connector_cutout_width = 32.0;
pcb_connector_right_panel_cutout_width = 35.0;
pcb_connector_cutout_height = 12.0;
pcb_connector_cutout_cr = 2.0;
pcb_connector_cutout_x = -23.0;
pcb_connector_right_panel_cutout_x = -30.5;
pcb_connector_cutout_y = -28;
pcb_locator_pin_inner_hole_rad = 2.1/2;

motor_surround_height = motor_chasis_top_height;

// List of M3 flathead hole positions [x, y]
hole_inset_x = 5;
hole_inset_y_front = 4.5;
hole_inset_y_back = 4.5;
hole_offset_x = - pvv_enclosure_height_lower;
hole_offset_y = - pvv_enclosure_length + pvv_front_forward_offset;
m3_flathead_hole_positions = 
[
	[ hole_offset_x + pvv_enclosure_height - hole_inset_x, hole_offset_y + pvv_enclosure_length - hole_inset_y_front],
	[ hole_offset_x + pvv_enclosure_height - hole_inset_x, hole_offset_y + hole_inset_y_back],
	[ hole_offset_x + hole_inset_x,                        hole_offset_y + pvv_enclosure_length - hole_inset_y_front],
	[ hole_offset_x + hole_inset_x,                        hole_offset_y + hole_inset_y_back]
];

mounting_hole_inset_y_front = 10.0;
mounting_hole_inset_y_back  = 10.0;
m3_mounting_insert_positions =
[
	[ hole_offset_x + pvv_enclosure_height - hole_inset_x, hole_offset_y + pvv_enclosure_length - mounting_hole_inset_y_front], // Front Top
	[ hole_offset_x + pvv_enclosure_height - hole_inset_x, hole_offset_y + mounting_hole_inset_y_back],                         // Rear Top
	[ hole_offset_x + hole_inset_x,                        hole_offset_y + pvv_enclosure_length - mounting_hole_inset_y_front], // Front Bottom
	[ hole_offset_x + hole_inset_x,                        hole_offset_y + mounting_hole_inset_y_back]                          // Rear Bottom
];


locator_pin_depth = 4.0;
locator_pin_receiver_hole_depth = locator_pin_depth + 1.0;
locator_pin_rad = 2.0;
locator_pin_receiver_hole_rad = locator_pin_rad + fit_3dprint_locator_pin_radius;
locator_pin_inset_x = 4;
locator_pin_inset_y_front = 12;
locator_pin_inset_y_back = 12;
locator_pin_positions = 
[
	[ hole_offset_x + pvv_enclosure_height - locator_pin_inset_x, hole_offset_y + pvv_enclosure_length - locator_pin_inset_y_front],
	[ hole_offset_x + pvv_enclosure_height - locator_pin_inset_x, hole_offset_y + locator_pin_inset_y_back],
	[ hole_offset_x + locator_pin_inset_x,                        hole_offset_y + pvv_enclosure_length - locator_pin_inset_y_front],
	[ hole_offset_x + locator_pin_inset_x,                        hole_offset_y + locator_pin_inset_y_back]
];



tower_offset_x = tower_width / 2.0;
tower_offset_y = tower_depth / 2.0;
tower_positions = 
[
	[pvv_enclosure_height - tower_offset_y, pvv_enclosure_length - tower_offset_x],
	[pvv_enclosure_height - tower_offset_y, tower_offset_x],
	[tower_offset_y,                        pvv_enclosure_length - tower_offset_x],
	[tower_offset_y,                        tower_offset_x]
];

motor_wire_channel_width = 8.0;
motor_wire_channel_offset_x = 25.5;

module pvv_frame_left_side_panel(use_B_mounting_pattern = false)
{
	axel_nub_flange_size_z_from_origin = axel_nub_flange_size_z + frame_left_sidewall_thickness;
	//echo(axel_nub_flange_size_z_from_origin = axel_nub_flange_size_z_from_origin);
	axel_nub_size_z_from_origin = axel_nub_size_z + axel_nub_flange_size_z_from_origin;

	difference()
	{
		translate([0, 0, -pvv_inner_panel_to_panel_width - frame_left_sidewall_thickness])
		{
			difference()
			{
				union()
				{
					// Main wall plate:
					linear_extrude(height=frame_left_sidewall_thickness) 
					{
						translate([-pvv_enclosure_height_lower, -pvv_enclosure_length + pvv_front_forward_offset - pvv_left_panel_extension])
						{
							square([pvv_enclosure_height, pvv_enclosure_length + pvv_left_panel_extension]);
						}
					}

					// Inset wall thickener:
					if (left_inside_wall_additional_reinforcement_thickness > 0.0)
					{
						translate([0,0,frame_left_sidewall_thickness]) linear_extrude(height=left_inside_wall_additional_reinforcement_thickness) 
						{
							translate([-pvv_enclosure_height_lower, -pvv_enclosure_length + pvv_front_forward_offset - pvv_left_panel_extension])
							{
								square([pvv_enclosure_height, pvv_enclosure_length + pvv_left_panel_extension]);
							}
						}
					}
				}

				// Receiving pockets for the towers...
				translate([0, 0, pvv_inner_panel_to_panel_width + frame_left_sidewall_thickness]) tower_cores(expand_by = fit_3dprint_tower_pocket_expand_by);

				// PCB Pocket...
				pcb_board_pocket_depth = pcb_board_recess_depth + left_inside_wall_additional_reinforcement_thickness;
				translate([0, 0, left_sidewall_combined_thickness - pcb_board_pocket_depth]) rotate([0, 0, -90]) 
				{
					//pcb(pcb_to_spool);
					//Stepper28BYJ48();

					linear_extrude(height=pcb_board_pocket_depth + eps) 
					{
						// Use pvv_rounded_square to create the PCB pocket with offset and rounded corners
						translate([-pcb_edge_to_hole_x - pcb_pocket_offset, 
								   -pcb_height + pcb_edge_to_hole_y - pcb_pocket_offset]) 
						{
							pvv_rounded_square(size=[pcb_length + 2*pcb_pocket_offset, 
												 pcb_height + 2*pcb_pocket_offset], 
										  center=false, 
										  cr=pcb_pocket_corner_radius, 
										  $fn=15);
						}
					}
				}

				// Threaded insert holes for PCB mounting...
				// NOTE!!  This m3x3 insert goes in upside down (with the larger radius flush with the outside of the panel.  In this configuration, it
				// makes a perfect locator pin for the PCB board...
				rotate([0, 0, -90]) 
				{
					translate([pcb_hole_to_bolt_hole_x, -pcb_hole_to_bolt_hole_y, 0]) 
					{
						m3x3_backwards_insert_rad = 4.8 / 2;
						cylinder(r=m3x3_backwards_insert_rad, h=20, center=true, $fn=30);
					}
				}

				// pcb connector cutout...
				translate([pcb_connector_cutout_x, pcb_connector_cutout_y, -1]) linear_extrude(height=10) 
				{
					pvv_rounded_square(size=[pcb_connector_cutout_width, pcb_connector_cutout_height], center=true, cr=pcb_connector_cutout_cr, $fn=30);
				}

				// holes for M3 flathead screws to hold the enclosure together...
				translate([0, 0])
				{
					for (pos = m3_flathead_hole_positions) 
					{
						translate([pos[0], pos[1], 0]) m3_flathead_hole(6);
					}
				}

				// channel for sensor wire...
				sensor_wire_channel_depth = 2.0;
				sensor_wire_channel_width = 8.0;
				sensor_wire_channel_cutout_depth = 20;
				sensor_wire_channel_cutout_length = 100;
				translate([-31-sensor_wire_channel_width, -25-sensor_wire_channel_cutout_length, -sensor_wire_channel_cutout_depth + sensor_wire_channel_depth])
					chamfered_cube([sensor_wire_channel_width, sensor_wire_channel_cutout_length, sensor_wire_channel_cutout_depth], r=1.0, center=false);

				// channel for motor wire...
				motor_wire_channel_depth = 2.0;
				motor_wire_channel_cutout_depth = 20;
				motor_wire_channel_cutout_length = 100;
				translate([motor_wire_channel_offset_x-motor_wire_channel_width, -34-motor_wire_channel_cutout_length, -motor_wire_channel_cutout_depth + motor_wire_channel_depth])
					chamfered_cube([motor_wire_channel_width, motor_wire_channel_cutout_length, motor_wire_channel_cutout_depth], r=1.0, center=false);

				// ============================================================
				// HONEYCOMB WINDOWS - Common parameters
				// ============================================================
				honeycomb_cell_radius = 5;           // Radius of hexagonal cells (all windows)
				honeycomb_wall_size = 1.2;           // Wall thickness between cells (all windows)
				honeycomb_cell_corner_radius = 1.2;  // Corner rounding for cells (all windows)
				honeycomb_recess_depth = left_inside_wall_additional_reinforcement_thickness;        // Surface recess depth (all windows)
				honeycomb_global_origin = [0, 0];    // Adjust to shift pattern across all windows

				// ============================================================
				// HONEYCOMB WINDOW 1: Bottom extension area
				// ============================================================
				honeycomb1_inset_x_left = 10.0;       // Distance from left edge of panel
				honeycomb1_inset_x_right = 10.0;      // Distance from right edge of panel
				honeycomb1_inset_y_top = 12.0;       // Distance from top of extension area
				honeycomb1_inset_y_bottom = 5.0;     // Distance from bottom edge of panel
				honeycomb1_size_x = pvv_enclosure_height - honeycomb1_inset_x_left - honeycomb1_inset_x_right;
				honeycomb1_size_y = pvv_left_panel_extension - honeycomb1_inset_y_bottom - honeycomb1_inset_y_top;
				honeycomb1_pos = [honeycomb1_inset_x_left - pvv_enclosure_height_lower, 
								 honeycomb1_inset_y_bottom - pvv_left_panel_extension - pvv_enclosure_length + pvv_front_forward_offset];
			
				translate(honeycomb1_pos)
					recessed_honeycomb_cutout(
						size=[honeycomb1_size_x, honeycomb1_size_y],
						corner_radius=5.0,
						cell_radius=honeycomb_cell_radius,
						wall_size=honeycomb_wall_size,
						cell_corner_radius=honeycomb_cell_corner_radius,
						recess_depth=honeycomb_recess_depth,
						panel_thickness=left_sidewall_combined_thickness,
						window_position=honeycomb1_pos,
						global_origin=honeycomb_global_origin,
						invert=true,
						$fn=30
					);

				// ============================================================
				// HONEYCOMB WINDOW 2: Upper area (above PCB board)
				// ============================================================
				//honeycomb2_size = [30.0, 20.0];      // Width x Height of the window
				//honeycomb2_pos = [18.0 - pvv_enclosure_height_lower, 
				//				 22.0 - pvv_enclosure_length + pvv_front_forward_offset];
			
				//translate(honeycomb2_pos)
				//	recessed_honeycomb_cutout(
				//		size=honeycomb2_size,
				//		corner_radius=4.0,
				//		cell_radius=honeycomb_cell_radius,
				//		wall_size=honeycomb_wall_size,
				//		cell_corner_radius=honeycomb_cell_corner_radius,
				//		recess_depth=honeycomb_recess_depth,
				//		panel_thickness=left_sidewall_combined_thickness,
				//		window_position=honeycomb2_pos,
				//		global_origin=honeycomb_global_origin,
				//		invert=true,
				//		$fn=30
				//	);

				// ============================================================
				// HONEYCOMB WINDOW 3: Lower area (below PCB board)
				// ============================================================
				//honeycomb3_size = [30.0, 20.0];      // Width x Height of the window
				//honeycomb3_pos = [95.0 - pvv_enclosure_height_lower, 
				//				 22.0 - pvv_enclosure_length + pvv_front_forward_offset];
			
				//translate(honeycomb3_pos)
				//	recessed_honeycomb_cutout(
				//		size=honeycomb3_size,
				//		corner_radius=4.0,
				//		cell_radius=honeycomb_cell_radius,
				//		wall_size=honeycomb_wall_size,
				//		cell_corner_radius=honeycomb_cell_corner_radius,
				//		recess_depth=honeycomb_recess_depth,
				//		panel_thickness=left_sidewall_combined_thickness,
				//		window_position=honeycomb3_pos,
				//		global_origin=honeycomb_global_origin,
				//		invert=true,
				//		$fn=30
				//	);
			}

			// Locator pins...
			for (pos = locator_pin_positions) 
			{
				pos_x = pos[0];
				pos_y = pos[1];
				translate([pos_x, pos_y, frame_left_sidewall_thickness])
				{
					cylinder_rounded(r = locator_pin_rad, h = locator_pin_depth, cap_r1=0, cap_r2=1, cr_fn=15, center = false, $fn = 30);
				}
			}

			// Axel nub...
			translate([0,0,frame_left_sidewall_thickness/2]) cylinder(r=pcb_hole_radius, h=frame_left_sidewall_thickness, center=true, $fn=64);
			translate([0,0,axel_nub_flange_size_z_from_origin/2]) cylinder(r=axel_nub_flange_radius, h=axel_nub_flange_size_z_from_origin, center=true, $fn=64);
			translate([0,0,axel_nub_size_z_from_origin/2]) cylinder_rounded(r = axel_nub_radius, h = axel_nub_size_z_from_origin, cap_r = 1.8, center = true, $fn = 64, cr_fn=30);

			// Accessory mounting blocks, positive...
			translate([0, -pvv_enclosure_length + pvv_front_forward_offset - pvv_left_panel_extension, 0])
			{
				translate([-pvv_enclosure_height_lower, 0, 0])
				{
					cube([accessory_mounting_block_width, accessory_mounting_block_depth, accessory_mounting_block_height]);
				}
				translate([pvv_enclosure_height-pvv_enclosure_height_lower - accessory_mounting_block_width, 0, 0])
				{
					cube([accessory_mounting_block_width, accessory_mounting_block_depth, accessory_mounting_block_height]);
				}

				cube([accessory_mounting_block_width, accessory_middle_mounting_block_depth, accessory_mounting_block_height]);

				translate([-chainlink_board_hole_pattern_space_y, 0, 0])
				{
					cube([accessory_mounting_block_width, accessory_middle_mounting_block_depth, accessory_mounting_block_height]);
				}
			}
		}

		// Accessory mounting blocks, negative...
		accessory_mounting_block_insert_hole_depth = 8.0;
		accessory_mounting_block_vertical_insert_offset_x = accessory_mounting_block_insert_hole_depth-accessory_mounting_block_width/2.0;
		accessory_mounting_block_vertical_insert_offset_y = accessory_mounting_block_insert_hole_depth + 3.0;
		translate([0, -pvv_enclosure_length + pvv_front_forward_offset - pvv_left_panel_extension, -pvv_inner_panel_to_panel_width - frame_left_sidewall_thickness])
		{
			translate([-pvv_enclosure_height_lower + accessory_mounting_block_width/2.0, 0, accessory_mounting_block_height/2.0])
			{
				rotate([-90,0,0]) cylinder(r = m3x6_insert_rad, h = accessory_mounting_block_insert_hole_depth, $fn = 30);
				translate([accessory_mounting_block_vertical_insert_offset_x, accessory_mounting_block_vertical_insert_offset_y, 0]) rotate([0,-90,0])
					cylinder(r = m3x6_insert_rad, h = accessory_mounting_block_insert_hole_depth, $fn = 30);
			}
			translate([pvv_enclosure_height-pvv_enclosure_height_lower - accessory_mounting_block_width + accessory_mounting_block_width/2.0, 0, accessory_mounting_block_height/2.0])
			{
				rotate([-90,0,0]) cylinder(r = m3x6_insert_rad, h = accessory_mounting_block_insert_hole_depth, $fn = 30);
				translate([-accessory_mounting_block_vertical_insert_offset_x, accessory_mounting_block_vertical_insert_offset_y, 0]) rotate([0,90,0])
					cylinder(r = m3x6_insert_rad, h = accessory_mounting_block_insert_hole_depth, $fn = 30);
			}

			chainlink_pcb_mount_AB_shift = (use_B_mounting_pattern) ? (3.0 * pvv_module_width - chainlink_board_hole_pattern_space_x) : 0.0;
			translate([accessory_mounting_block_width/2.0, 0, accessory_mounting_block_height/2.0 + chainlink_pcb_mount_AB_shift]) rotate([-90,0,0])
			{
				cylinder(r = m3x6_insert_rad, h = accessory_mounting_block_insert_hole_depth, $fn = 30);
			}

			translate([-chainlink_board_hole_pattern_space_y + accessory_mounting_block_width/2.0, 0, accessory_mounting_block_height/2.0 + chainlink_pcb_mount_AB_shift]) rotate([-90,0,0])
			{
				cylinder(r = m3x6_insert_rad, h = accessory_mounting_block_insert_hole_depth, $fn = 30);
			}
		}

		if (use_2p5_allen_key_access_hole)
		{
			// Allen key access hole...
			translate([0, 0, -pvv_inner_panel_to_panel_width - frame_left_sidewall_thickness])
			{
				allen_hole_radius = allen_key_outer_radius + 0.05;
				allen_hole_depth = axel_nub_size_z_from_origin;
				translate([0,0,allen_hole_depth/2]) cylinder(r = allen_hole_radius, h = allen_hole_depth, center = true, $fn = 30);
			}
		}
	}

	front_panel_for_left_side_panel();
	//draw_pcb();
}


module front_panel()
{
	// Front panel...
   translate([-pvv_enclosure_height_lower, pvv_front_forward_offset + front_panel_thickness, frame_right_sidewall_thickness]) rotate([0,90,-90])
	{
		linear_extrude(height=front_panel_thickness) difference()
		{
			square([pvv_enclosure_width, pvv_enclosure_height]);

			// Viewing window cutout
			translate([pvv_right_window_inset, pvv_enclosure_height_lower - pvv_front_window_lower])
				square([pvv_front_window_width, pvv_front_window_height]);

			if (s_bUseFlapTopWindowReveal)
			{
				window_reveal_side_tab_size = 4.0;
				window_flap_reveal_width = pvv_front_window_width - 2.0*window_reveal_side_tab_size;
				window_flap_reveal_height = 10.0;
				translate([window_reveal_side_tab_size + frame_left_sidewall_thickness, pvv_front_window_height + pvv_enclosure_height_lower - pvv_front_window_lower,0])
					square([window_flap_reveal_width, window_flap_reveal_height]);
			}
		}
	}
}

module front_panel_for_right_side_panel()
{
	color([0,0,1]) difference()
	{
		front_panel();
		translate([0, 0, -100 - pvv_inner_panel_to_panel_width + pvv_front_window_left_bezel_size])
			cube([200, 200, 200], center = true);
	}
}

module front_panel_for_left_side_panel()
{
	color([0,1,0]) difference()
	{
		front_panel();
		translate([0, 0, pvv_front_window_left_bezel_size - pvv_inner_panel_to_panel_width + 100])
			cube([200, 200, 200], center = true);
	}
}

module tower_cores(expand_by = 0.0)
{
	for (pos = tower_positions) 
	{
		pos_x = pos[0] - pvv_enclosure_height_lower;
		pos_y = pos[1] - pvv_enclosure_length + pvv_front_forward_offset;
		translate([pos_x,pos_y,0])
		{
			difference()
			{
				translate([0,0,-tower_height + preview_eps])
				{
					linear_extrude(height=tower_height) 
					{
						pvv_rounded_square(size=[tower_depth + expand_by, tower_width + expand_by], center=true, cr=0.0, $fn=30);
					}
				}

				// Exclusion radii...
				exclusion_rad = (pos_x < 0.0) ? outer_exclusion_radius + outer_exclusion_gap : exclusion_radius + collapsed_exclusion_gap;
				translate([-pos_x, -pos_y, -tower_height - preview_eps]) cylinder(r = exclusion_rad - expand_by, h = tower_height, center=false, $fn=240);
			}
		}
	}
}

module pvv_frame_right_side_panel()
{
	bp_cutout_width = m28byj48_backpack_width + 1.0;
	bp_cutout_extent = m28byj48_backpack_extent - 1.5;
	bp_cutout_size_z = 100;
	union()
	{
		difference()
		{
			union()
			{
				difference()
				{
					union()
					{
						linear_extrude(height=frame_right_sidewall_thickness) 
						{
							translate([-pvv_enclosure_height_lower, -pvv_enclosure_length + pvv_front_forward_offset])
							{
								square([pvv_enclosure_height, pvv_enclosure_length]);
							}
						}


						// Inside wall thickener:
						if (right_inside_wall_additional_reinforcement_thickness > 0.0)
						{
							translate([0,0,-right_inside_wall_additional_reinforcement_thickness]) linear_extrude(height=right_inside_wall_additional_reinforcement_thickness) 
							{
								translate([-pvv_enclosure_height_lower, -pvv_enclosure_length + pvv_front_forward_offset])
								{
									square([pvv_enclosure_height, pvv_enclosure_length]);
								}
							}
						}
					}

					// pcb connector cutout...
					translate([pcb_connector_right_panel_cutout_x, pcb_connector_cutout_y, -50]) linear_extrude(height=100) 
					{
						pvv_rounded_square(size=[pcb_connector_right_panel_cutout_width, pcb_connector_cutout_height], center=true, cr=pcb_connector_cutout_cr, $fn=30);
					}
				}

				// Motor surround positive body...
				difference()
				{
					motor_surround_height_from_outside_wall = motor_surround_height + frame_right_sidewall_thickness;
					translate([0, 0, -motor_surround_height]) cylinder_rounded(r = motor_surround_outer_radius, h = motor_surround_height_from_outside_wall, cap_r1=1, cap_r2=0, cr_fn=30, center = false, $fn = 240);
					// cr for sharp edge from backpack cutout...
					if (num_flaps <= 52)
					{
						for (sy = [1, -1])
						{
							cr_setback = sqrt(motor_surround_outer_radius * motor_surround_outer_radius - (bp_cutout_width/2) * (bp_cutout_width/2));
							scale([1,sy,1])
							translate([cr_setback - 1.35, -(bp_cutout_width/2+0.9),-50]) rotate([0,0,-20]) rounding_tool([2,2,100], r=1.0, $fn=45);
						}
					}
				}
			}

			// holes for M3 flathead screws to hold the enclosure together...
			translate([0, 0])
			{
				for (pos = m3_flathead_hole_positions) 
				{
					translate([pos[0], pos[1], -eps]) cylinder(h=10, r=m3_thru_hole_rad, center=true, $fn=30);
				}
			}

			// channel for motor wire...
			motor_wire_channel_depth = frame_right_sidewall_thickness - 2.0;
			motor_wire_channel_cutout_depth = 20;
			motor_wire_channel_cutout_length = 100;
			translate([motor_wire_channel_offset_x-motor_wire_channel_width, 7.8-motor_wire_channel_cutout_length, motor_wire_channel_depth])
				chamfered_cube([motor_wire_channel_width, motor_wire_channel_cutout_length, motor_wire_channel_cutout_depth], r=motor_wire_channel_depth, center=false);

			// Motor surround negative...
			translate([m28byj48_shaft_offset, 0, -1.5*motor_surround_height]) cylinder(r = m28byj48_chassis_radius + fit_3dprint_motor_surround, h = 3 * motor_surround_height, center = false, $fn = 240);
			translate([0, 0, -motor_chasis_top_height - eps]) rotate([0, 180, 90]) 
			{
				translate([0, -m28byj48_shaft_offset, 0]) 
				{
					translate([0, 0, -m28byj48_mount_bracket_height - eps]) 
					{
						// Motor mounting bracket tabs pocket (hull of two circles)...
						linear_extrude(height=m28byj48_mount_bracket_height) 
						{
							hull() 
							{
								translate([m28byj48_mount_center_offset, 0]) 
								{
									circle(r=m28byj48_mount_outer_radius + fit_3dprint_28byj48_mount_outer_radius, $fn = 60);
								}
								translate([-m28byj48_mount_center_offset, 0]) 
								{
									circle(r=m28byj48_mount_outer_radius + fit_3dprint_28byj48_mount_outer_radius, $fn = 60);
								}
							}
						}

						// M4 threaded insert holes for motor mounting bracket...
						threaded_insert_depth = m3x6_insert_depth + 5.0;
						translate([0,0,-threaded_insert_depth]) linear_extrude(height=20) 
						{
							translate([m28byj48_mount_center_offset, 0]) 
							{
								circle(r=m3x6_insert_rad, $fn = 60);
							}
							translate([-m28byj48_mount_center_offset, 0]) 
							{
								circle(r=m3x6_insert_rad, $fn = 60);
							}
						}
					}

					translate([-bp_cutout_width/2, -bp_cutout_extent, -bp_cutout_size_z/2]) 
					{
						rounded_cube([bp_cutout_width, bp_cutout_extent, bp_cutout_size_z], r=1.0, $fn=30);
						if (num_flaps <= 52)
						{
							// Extra cut to clear sliver of motor surround...
							translate([0, -2.0, bp_cutout_size_z/2 - motor_chasis_top_height + right_inside_wall_additional_reinforcement_thickness])
								cube([bp_cutout_width, bp_cutout_extent, bp_cutout_size_z]);
						}
					}
				}
			}
		}

		// Towers...
		difference()
		{
			tower_cores();
			
			// Insert holes in towers...
			for (pos = m3_flathead_hole_positions) 
			{
				pos_x = pos[0];
				pos_y = pos[1];
				translate([pos_x,pos_y,0])
				{
					// Insert holes for M3 flathead screws to hold the enclosure together...
					translate([0,0,-tower_height-eps]) cylinder(r = m3x6_insert_rad, h = m3x6_insert_depth + 7.0, center = false, $fn = 30);
					// 2.5 mm Allen key access holes in towers (for assembly/disassembly of the enclosure)...
					cylinder(r = 1.5, h = 200, center = true, $fn = 30);
				}

				// access channel...
				tower_channel_depth = 12;
				tower_channel_width = 7;
				tower_channel_height = 25;
				outset_shift_amount = 3.0;
				is_bottom = pos_x < 0.0;
				is_front = pos_y > 0.0;
				shift_x = (is_bottom) ? 6-outset_shift_amount : outset_shift_amount;
				tower_channel_cr = 2.5;
				translate([pos_x + shift_x,pos_y,-tower_channel_height]) linear_extrude(height=tower_channel_height) 
				{
					pvv_rounded_square(size=[tower_channel_depth, tower_channel_width], center=true, cr=tower_channel_cr, $fn=30);
				}
				shift_channel_x = shift_x - tower_channel_depth/2;
				intersection()
				{
					translate([pos_x + shift_channel_x,pos_y,-tower_channel_height + tower_channel_width/2]) rotate([-90, 0, -90]) rotate([0, 0, 45]) cube(size=[tower_channel_width / sqrt(2.0), tower_channel_width / sqrt(2.0), tower_channel_depth]);
					translate([pos_x + shift_x,pos_y,-2*tower_channel_height]) linear_extrude(height=2*tower_channel_height) 
					{
						pvv_rounded_square(size=[tower_channel_depth, tower_channel_width], center=true, cr=tower_channel_cr, $fn=30);
					}
				}
			}

			// mounting holes...
			for (pos = m3_mounting_insert_positions) 
			{
				pos_x = pos[0];
				pos_y = pos[1];

				is_bottom = pos_x < 0.0;
				is_front = pos_y > 0.0;

				mounting_hole_insert_hole_depth = m3x6_insert_depth + 0.5;
				mounting_holes_inset_x = is_bottom ? (-5 + mounting_hole_insert_hole_depth) : (5 - mounting_hole_insert_hole_depth);
				mounting_holes_inset_z = 22.0;
				translate([pos_x,pos_y,0])
				{
					translate([mounting_holes_inset_x, 0, -tower_height - eps + mounting_holes_inset_z]) rotate([0, (is_bottom) ? -90 : 90, 0])
						cylinder(r = m3x6_insert_rad, h = mounting_hole_insert_hole_depth, center = false, $fn = 30);
				}
			}

			// Locator pin receiver holes...
			for (pos = locator_pin_positions) 
			{
				pos_x = pos[0];
				pos_y = pos[1];
				translate([pos_x,pos_y,0])
				{
					translate([0,0,-tower_height-eps]) cylinder(r = locator_pin_receiver_hole_rad, h = locator_pin_receiver_hole_depth, center = false, $fn = 30);
				}
			}

			// Small relief undercut on the tower prevent interference with the left side panel (causing misalignment of the locator pins)...
			fit_3dprint_undercut_gap = 0.25;
			translate([0, 100 + pvv_front_forward_offset - fit_3dprint_undercut_gap, -100 - pvv_inner_panel_to_panel_width + pvv_front_window_left_bezel_size])
				cube([200, 200, 200], center = true);
		}

		// Front panel...
		front_panel_for_right_side_panel();
	}

	// Draw the motor for reference (not part of the actual panel)...
	translate([0, 0, -motor_chasis_top_height]) rotate([0, 180, 90]) 
	{
		//Stepper28BYJ48();
	}
}




//split_flap_3d(get_flap_index_for_letter("B"));

// For printing...
//apply_filament_shrinkage_compensation() pvv_left_flap_spool();
//apply_filament_shrinkage_compensation() pvv_right_flap_spool();

module spool_assembly()
{
	pvv_left_flap_spool();
	// pvv_spool_width is outside dimension including thickness
	translate([0, 0, pvv_spool_width - spool_thickness_3dprint])
	{
		pvv_right_flap_spool();
	}
}
//spool_assembly();


module motor_flange_alignment_jig()
{
	jig_support_plate_thickness = 5.0;
	jig_center_align_pin_rad = motor_coupler_center_hole_od/2.0 + 0.075; // interference fit
	jig_outer_rad = motor_surround_outer_radius + 3.5;
	allen_wrench_access_hole_rad = 8.0;
	grub_screw_z = 6.75;
	fit_3dprint_jig_outer_rad = 0.01;
	thin_wall_thickness = 2.0;

	difference()
	{
		union()
		{
			translate([0,0, - jig_support_plate_thickness])
				cylinder(r = jig_outer_rad, h = jig_support_plate_thickness, $fn=240);

			cylinder_rounded(r = jig_center_align_pin_rad, h = axel_pin_height, cap_r1=0, cap_r2=1, cr_fn=15, center = false, $fn = 60);
			tube(h=motor_coupler_height_off_motor_face + motor_chasis_top_height - right_inside_wall_additional_reinforcement_thickness,
				ir = motor_surround_outer_radius + fit_3dprint_jig_outer_rad, or = jig_outer_rad, center=false, $fn=240);
		}

		for (i = [0 : 3])
		{
			rotate([0, 0, i * 90]) translate([motor_coupler_hole_pattern_radius, 0, 0])
			{
				cylinder(h=100, r=m3_thru_hole_rad + 0.1, center=true, $fn=30);
			}
		}

		for (a = [0 : 45 : 359])
		{
			rotate([0, 0, a])
			{
				translate([10,0,motor_coupler_flange_thickness + grub_screw_z]) rotate([0, 90, 0])
					cylinder(h=100, r=allen_wrench_access_hole_rad, center=false, $fn=4);
			}
		}

		for (a = [0 : 90 : 359])
		{
			rotate([0, 0, a])
			{
				tube(h=motor_coupler_height_off_motor_face + motor_chasis_top_height, ir = motor_surround_outer_radius - 1.0, or = jig_outer_rad - thin_wall_thickness,
					pie_angle=50, center=false, $fn=240);
			}
		}
	}
}

module jig_cutaway()
{
	intersection()
	{
		union()
		{
			pvv_frame_right_side_panel();
			// Draw the motor for reference (not part of the actual panel)...
			translate([0, 0, -motor_chasis_top_height]) rotate([0, 180, 90]) 
			{
				Stepper28BYJ48();
			}

			translate([0,0,-motor_coupler_height_off_motor_face-motor_chasis_top_height])
			{
				color(flange_color) draw_flange_coupler();

				motor_flange_alignment_jig();
			}
		}

		translate([0,-500,0]) cube([1000,1000,1000], center=true);
	}
}


//rotate([0,-90,0])
//{
	apply_filament_shrinkage_compensation()
	{
		//pvv_frame_left_side_panel();
		//pvv_frame_right_side_panel();
		//translate([0,0,spool_left_offset + frame_left_sidewall_thickness + frame_right_sidewall_thickness - pvv_enclosure_width]) spool_assembly();
	}

	//// For reference, the original front panel with window cutout...
	////echo(enclosure_width = enclosure_width);
	////echo(front_window_width = front_window_width);
	////echo(enclosure_horizontal_inset = enclosure_horizontal_inset);
	//color([0,0,1]) apply_filament_shrinkage_compensation() translate([-pvv_enclosure_height_lower, pvv_front_forward_offset,
	//        front_window_right_inset + front_window_width/2 - pvv_inner_panel_to_panel_width/2]) rotate([0,90,-90])
	//{
	//    linear_extrude(height=front_panel_thickness) difference()
	//    {
	//        enclosure_front_base_2d();
	//        // Viewing window cutout
	//        translate([front_window_right_inset, enclosure_height_lower - front_window_lower])
	//            square([front_window_width, front_window_lower + front_window_upper]);
	//    }
	//}
//}

//draw_motor();


// CUTAWAY...
module cutaway()
{
	intersection()
	{
		union()
		{
			pvv_frame_left_side_panel();
			pvv_frame_right_side_panel();
			// Draw the motor for reference (not part of the actual panel)...
			translate([0, 0, -motor_chasis_top_height]) rotate([0, 180, 90]) 
			{
				Stepper28BYJ48();
			}

			if (use_motor_coupler)
			{
				translate([0,0,-motor_coupler_height_off_motor_face-motor_chasis_top_height]) draw_motor_coupler();
			}

			translate([0,0,spool_left_offset - pvv_inner_panel_to_panel_width]) spool_assembly();
		}

		translate([0,-500,0]) cube([1000,1000,1000], center=true);
	}
}
//cutaway();


module print_plate(use_B_mounting_pattern = false)
{
	apply_filament_shrinkage_compensation()
	{
		translate([0, 0, pvv_inner_panel_to_panel_width + frame_left_sidewall_thickness]) pvv_frame_left_side_panel(use_B_mounting_pattern = use_B_mounting_pattern);
		translate([-pvv_enclosure_height_lower - pvv_front_forward_offset - front_panel_thickness - 1,
			-pvv_distance_to_back + pvv_enclosure_height_lower - pvv_left_panel_extension,
			frame_right_sidewall_thickness])
				rotate([180,0,90]) pvv_frame_right_side_panel();
		translate([0,pvv_front_forward_offset + spool_outer_radius + front_panel_thickness + 1,0])
		{
		    translate([-spool_outer_radius - 1,0,0]) pvv_left_flap_spool();
		    translate([spool_outer_radius + 1,0,0]) pvv_right_flap_spool();
		}
	}
} 

//print_plate(use_B_mounting_pattern = false);


		//front_panel_for_left_side_panel();
		//front_panel_for_right_side_panel();


//jig_cutaway();
//apply_filament_shrinkage_compensation() motor_flange_alignment_jig();


// ==========================================================================================================================================================================
// EUFY MINIBED PROFILE - for cutting mats and similar accessories	
// 371mm x 69mm    6mm corner rad  22mm corner cut
// ==========================================================================================================================================================================

minibed_size_y = 371;
minibed_size_x = 97;
minibed_cr = 7.5;
minibed_corner_cut = 22;
minibed_printable_size_x = 88;
minibed_printable_size_y = 330;
minibed_printable_origin_x = 5.0;
minibed_printable_origin_y = 33.0;
module eufy_minibed_printable_area_profile()
{
	translate([minibed_printable_origin_x, minibed_printable_origin_y]) square([minibed_printable_size_x, minibed_printable_size_y], center=false);
}


module eufy_minibed_mat_profile(bUseCornerCut = true, bUsePrintableAreaCut = true)
{
	difference()
	{
		pvv_rounded_square([minibed_size_x, minibed_size_y], center=false, cr=minibed_cr, $fn = 30);
	
		// Remove corner at origin with diagonal cut
		if (bUseCornerCut)
		{
			polygon([
				[0, 0],
				[minibed_corner_cut, 0],
				[0, minibed_corner_cut]
			]);
		}
		// Remove printable area with diagonal cut
		if (bUsePrintableAreaCut)
		{
			eufy_minibed_printable_area_profile();
		}
	}
}

eufy_minibed_mat_profile();


// ==========================================================================================================================================================================
// Flap Jig for EUFY MINIBED
// ==========================================================================================================================================================================



//flap_number = 1;
module flap_lineup()
{
	for (flap_number = [0 : num_flaps - 1])
	{
		translate([flap_number * 55, 0, 0])
		{
			flap_with_letters([1,0,0], [1,1,0], flap_index=flap_number, flap_gap=flap_gap, bleed=2);
			// translate([0, -flap_pin_width-flap_gap, 0])
			// rotate([180, 0, 0])
			// {
			// 	flap_with_letters([1,0,0], [1,1,0], flap_index=((flap_number - 1) + num_flaps) % num_flaps, flap_gap=flap_gap, bleed=2);
			// }
		}
	}
}


module flap_jig_eufy_minibed()
{
	num_flaps_in_jig = 5;
	echo(flap_width = flap_width);
	flap_spacing = flap_width + 6;
	for (flap_number = [0 : num_flaps_in_jig - 1])
	{
		translate([flap_number * flap_spacing, 0, 0])
		{
			flap_2d();
			translate([0, -flap_pin_width-flap_gap, 0])
			rotate([180, 0, 0])
			{
				flap_2d();
			}
		}
	}
}

//flap_jig_eufy_minibed();