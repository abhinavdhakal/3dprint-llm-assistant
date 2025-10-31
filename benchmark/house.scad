// Simple House SCAD Model for Benchmarking
// Basic concrete house structure

// House dimensions
wall_thickness = 200;  // 200mm thick concrete walls
wall_height = 3000;    // 3m high
wall_length = 8000;    // 8m long
wall_width = 6000;     // 6m wide

// Foundation
translate([0, 0, -300]) {
    cube([wall_length, wall_width, 300]);  // 300mm foundation
}

// Main structure
difference() {
    // Outer walls
    translate([0, 0, 0]) {
        cube([wall_length, wall_thickness, wall_height]);  // Front wall
    }
    translate([0, wall_width - wall_thickness, 0]) {
        cube([wall_length, wall_thickness, wall_height]);  // Back wall
    }
    translate([0, 0, 0]) {
        cube([wall_thickness, wall_width, wall_height]);  // Left wall
    }
    translate([wall_length - wall_thickness, 0, 0]) {
        cube([wall_thickness, wall_width, wall_height]);  // Right wall
    }

    // Door opening (front wall, center)
    translate([wall_length/2 - 1000, -1, 0]) {
        cube([2000, wall_thickness + 2, 2100]);  // 2m wide, 2.1m high door
    }

    // Window openings
    // Front wall windows
    translate([1000, -1, 800]) {
        cube([1000, wall_thickness + 2, 1000]);  // Left window
    }
    translate([wall_length - 2000, -1, 800]) {
        cube([1000, wall_thickness + 2, 1000]);  // Right window
    }

    // Back wall windows
    translate([2000, wall_width - wall_thickness - 1, 800]) {
        cube([1000, wall_thickness + 2, 1000]);  // Back left window
    }
    translate([wall_length - 3000, wall_width - wall_thickness - 1, 800]) {
        cube([1000, wall_thickness + 2, 1000]);  // Back right window
    }
}

// Roof (simple gable roof)
roof_height = 1000;
translate([0, 0, wall_height]) {
    polyhedron(
        points = [
            [0, 0, 0],                           // 0: front left bottom
            [wall_length, 0, 0],                  // 1: front right bottom
            [wall_length, wall_width, 0],         // 2: back right bottom
            [0, wall_width, 0],                   // 3: back left bottom
            [wall_length/2, wall_width/2, roof_height]  // 4: peak
        ],
        faces = [
            [0, 1, 4],  // front triangle
            [1, 2, 4],  // right triangle
            [2, 3, 4],  // back triangle
            [3, 0, 4],  // left triangle
            [0, 3, 2, 1] // bottom rectangle
        ]
    );
}