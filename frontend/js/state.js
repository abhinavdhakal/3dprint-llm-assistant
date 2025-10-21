// Application State Management
const AppState = {
  // Design data
  currentDesign: null,
  modifiedDesign: null,

  // View mode: 'current', 'modified', 'both'
  viewerMode: "current",

  // Three.js objects
  scene: null,
  camera: null,
  renderer: null,
  controls: null,
  currentMesh: null,
  modifiedMesh: null,
  dimensionGroup: null,
  measurementOverlay: null,
  measurementInfo: null,
  measurementMode: false,
  measurementPoints: [],
  measurementClickHandler: null,

  // Methods
  setCurrentDesign(design) {
    this.currentDesign = design;
  },

  setModifiedDesign(design) {
    this.modifiedDesign = design;
  },

  clearModifiedDesign() {
    this.modifiedDesign = null;
  },

  setViewerMode(mode) {
    this.viewerMode = mode;
  },

  setScene(scene) {
    this.scene = scene;
  },

  setCamera(camera) {
    this.camera = camera;
  },

  setRenderer(renderer) {
    this.renderer = renderer;
  },

  setCurrentMesh(mesh) {
    if (this.currentMesh && this.scene) {
      this.scene.remove(this.currentMesh);
    }
    this.currentMesh = mesh;
    if (mesh && this.scene) {
      this.scene.add(mesh);
    }
  },

  setModifiedMesh(mesh) {
    if (this.modifiedMesh && this.scene) {
      this.scene.remove(this.modifiedMesh);
    }
    this.modifiedMesh = mesh;
    if (mesh && this.scene) {
      this.scene.add(mesh);
    }
  },

  removeModifiedMesh() {
    if (this.modifiedMesh && this.scene) {
      this.scene.remove(this.modifiedMesh);
    }
    this.modifiedMesh = null;
  },
};

// Export to global scope
window.AppState = AppState;
