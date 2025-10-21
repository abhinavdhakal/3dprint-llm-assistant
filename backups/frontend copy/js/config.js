// Configuration and Constants
const CONFIG = {
  API_BASE: "http://127.0.0.1:5000/api",

  // Viewer settings
  VIEWER: {
    CAMERA_FOV: 75,
    CAMERA_NEAR: 1,
    CAMERA_FAR: 100000,
    CAMERA_INITIAL_POSITION: { x: 5000, y: 5000, z: 5000 },

    ZOOM_SPEED: 200, // More sensitive zoom
    ZOOM_MIN_DISTANCE: 100, // Allow closer zoom
    ZOOM_MAX_DISTANCE: 80000,

    ROTATION_SPEED: 0.005,

    GRID_SIZE: 10000,
    GRID_DIVISIONS: 20,
    AXES_SIZE: 2000,
  },

  // Colors
  COLORS: {
    BACKGROUND: 0xf5f5f5,
    CURRENT_MESH: 0x667eea,
    MODIFIED_MESH: 0x4caf50,
    GRID_CENTER: 0x667eea,
    GRID_LINES: 0xe0e0e0,
  },

  // Lighting
  LIGHTS: {
    AMBIENT_INTENSITY: 0.6,
    DIRECTIONAL_INTENSITY: 0.8,
  },
};

// Export for use in other modules
window.CONFIG = CONFIG;
