// General underground concrete pipe
// Units in millimeters

$fn = 150; // smoothness

pipe_length = 1500;
outer_diameter = 900;
wall_thickness = 90;

// Derived
inner_diameter = outer_diameter - 2 * wall_thickness;

difference() {
    union() {
        // Main cylinder
        cylinder(h = pipe_length, d = outer_diameter, center = false);
    }

    // Hollow out interior
    translate([0, 0, -1])
        cylinder(h = pipe_length + 2, d = inner_diameter, center = false);
}