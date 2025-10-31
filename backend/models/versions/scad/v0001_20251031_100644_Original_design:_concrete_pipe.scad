
// General underground concrete pipe
// Units in millimeters

$fn = 150; // smoothness

pipe_length = 1000;
outer_diameter = 900;
wall_thickness = 90;
bell_length = 150;
bell_outer_diameter = outer_diameter + 100;
spigot_length = 100;
spigot_outer_diameter = outer_diameter - 40;

// Derived
inner_diameter = outer_diameter - 2 * wall_thickness;
bell_inner_diameter = inner_diameter + 60;

// Main pipe
difference() {
    union() {
        // Main cylinder
        cylinder(h = pipe_length, d = outer_diameter, center = false);

        // Bell end (flared)
        translate([0, 0, pipe_length])
            cylinder(h = bell_length, d1 = outer_diameter, d2 = bell_outer_diameter, center = false);

        // Spigot end (narrowed)
        translate([0, 0, -spigot_length])
            cylinder(h = spigot_length, d1 = spigot_outer_diameter, d2 = outer_diameter, center = false);
    }

    // Hollow out interior
    translate([0, 0, -spigot_length - 1])
        cylinder(h = pipe_length + bell_length + spigot_length + 2, d = inner_diameter, center = false);

    // Hollow out bell cavity
    translate([0, 0, pipe_length])
        cylinder(h = bell_length + 1, d1 = inner_diameter, d2 = bell_inner_diameter, center = false);
}
