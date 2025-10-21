// Concrete 3D Printed Room - Parametric Design
// All measurements in millimeters (mm)

// === ROOM DIMENSIONS ===
room_length = 6500;        // 5 meters
room_width = 5500;         // 4 meters  
wall_height = 2800;        // 2.8 meters (standard ceiling height)
wall_thickness = 200;      // 20 cm (typical concrete 3D print)

// === DOOR ===
door_width = 800;          // 90 cm (standard door)
door_height = 2100;        // 2.1 meters
door_position = 1000;      // 1 meter from left corner

// === WINDOW ===
window_width = 1500;       // 1.5 meters wide
window_height = 1200;      // 1.2 meters tall
window_position = 3000;    // 3 meters from left corner
window_sill_height = 900;  // 90 cm from floor

// === GEOMETRY ===
module room() {
    difference() {
        // Outer walls (solid block)
        cube([room_length, room_width, wall_height]);
        
        // Interior cavity (hollow out the room)
        translate([wall_thickness, wall_thickness, 0])
            cube([
                room_length - 2*wall_thickness,
                room_width - 2*wall_thickness,
                wall_height + 100  // Extra height to ensure clean cut
            ]);
        
        // Door opening (front wall - Y=0 side)
        translate([door_position, -10, 0])
            cube([door_width, wall_thickness + 20, door_height]);
        
        // Window opening (front wall)
        translate([window_position, -10, window_sill_height])
            cube([window_width, wall_thickness + 20, window_height]);
    }
}

// Generate the room
room();