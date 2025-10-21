// Three.js Viewer Module with Professional OrbitControls
const Viewer = {
  // Initialize the 3D viewer
  init() {
    const container = document.getElementById("viewer-container");
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(CONFIG.COLORS.BACKGROUND);
    AppState.setScene(scene);

    // Camera
    const camera = new THREE.PerspectiveCamera(
      CONFIG.VIEWER.CAMERA_FOV,
      width / height,
      CONFIG.VIEWER.CAMERA_NEAR,
      CONFIG.VIEWER.CAMERA_FAR
    );
    const { x, y, z } = CONFIG.VIEWER.CAMERA_INITIAL_POSITION;
    camera.position.set(x, y, z);
    camera.lookAt(0, 0, 0);
    AppState.setCamera(camera);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);
    AppState.setRenderer(renderer);

    // Lights
    this.setupLights(scene);

    // Grid and Axes
    this.setupHelpers(scene);

    // Controls - Using professional OrbitControls
    this.setupOrbitControls(camera, renderer.domElement);

    // Setup measurement overlay
    this.setupMeasurementOverlay(container);

    // Animation loop
    this.animate();

    // Handle window resize
    window.addEventListener("resize", () => this.handleResize(container));
  },

  setupLights(scene) {
    const ambientLight = new THREE.AmbientLight(
      0xffffff,
      CONFIG.LIGHTS.AMBIENT_INTENSITY
    );
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(
      0xffffff,
      CONFIG.LIGHTS.DIRECTIONAL_INTENSITY
    );
    directionalLight.position.set(1, 1, 1);
    scene.add(directionalLight);
  },

  setupHelpers(scene) {
    // Grid - keep it horizontal (XZ plane is default, which works for us)
    const gridHelper = new THREE.GridHelper(
      CONFIG.VIEWER.GRID_SIZE,
      CONFIG.VIEWER.GRID_DIVISIONS,
      CONFIG.COLORS.GRID_CENTER,
      CONFIG.COLORS.GRID_LINES
    );
    scene.add(gridHelper);

    // Axes helper
    const axesHelper = new THREE.AxesHelper(CONFIG.VIEWER.AXES_SIZE);
    scene.add(axesHelper);

    // Add axis labels
    this.addAxisLabels(scene);

    // Add grid scale labels
    this.addGridScaleLabels(scene);

    // Add orientation compass
    this.addOrientationCompass(scene);
  },

  addGridScaleLabels(scene) {
    const gridSize = CONFIG.VIEWER.GRID_SIZE;
    const divisions = CONFIG.VIEWER.GRID_DIVISIONS;
    const step = gridSize / divisions;

    // Add scale markers along X and Z axes every 1000mm (1m)
    const markerInterval = 1000;
    const numMarkers = Math.floor(gridSize / 2 / markerInterval);

    for (let i = 1; i <= numMarkers; i++) {
      const distance = i * markerInterval;

      // X axis markers (along positive X)
      const xLabel = this.createTextSprite(`${distance}mm`, "#888888", 48);
      xLabel.position.set(distance, 50, -200);
      xLabel.scale.set(300, 150, 1);
      scene.add(xLabel);

      // Z axis markers (along positive Z)
      const zLabel = this.createTextSprite(`${distance}mm`, "#888888", 48);
      zLabel.position.set(-200, 50, distance);
      zLabel.scale.set(300, 150, 1);
      scene.add(zLabel);
    }
  },

  addOrientationCompass(scene) {
    // Create a small compass in the corner
    const compassGroup = new THREE.Group();
    compassGroup.name = "orientationCompass";

    // Position it at a fixed location (will need CSS overlay for true corner positioning)
    // For now, position it in world space
    const compassSize = 500;

    // X arrow (Red)
    const xArrow = new THREE.ArrowHelper(
      new THREE.Vector3(1, 0, 0),
      new THREE.Vector3(0, 0, 0),
      compassSize,
      0xff0000,
      compassSize * 0.3,
      compassSize * 0.2
    );
    compassGroup.add(xArrow);

    // Y arrow (Green)
    const yArrow = new THREE.ArrowHelper(
      new THREE.Vector3(0, 1, 0),
      new THREE.Vector3(0, 0, 0),
      compassSize,
      0x00ff00,
      compassSize * 0.3,
      compassSize * 0.2
    );
    compassGroup.add(yArrow);

    // Z arrow (Blue)
    const zArrow = new THREE.ArrowHelper(
      new THREE.Vector3(0, 0, 1),
      new THREE.Vector3(0, 0, 0),
      compassSize,
      0x0000ff,
      compassSize * 0.3,
      compassSize * 0.2
    );
    compassGroup.add(zArrow);

    // Position compass in bottom-left of view
    const gridEdge = CONFIG.VIEWER.GRID_SIZE / 2;
    compassGroup.position.set(-gridEdge * 0.8, 100, -gridEdge * 0.8);

    scene.add(compassGroup);
  },

  addAxisLabels(scene) {
    // Position labels just outside the grid edge
    // Grid is GRID_SIZE total, so edge is at GRID_SIZE/2 from center
    const labelDistance = (CONFIG.VIEWER.GRID_SIZE / 2) * 1.1;

    // Create text sprites for X, Y, Z
    const createTextSprite = (text, color) => {
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");
      canvas.width = 256;
      canvas.height = 256;

      context.font = "Bold 120px Arial";
      context.fillStyle = color;
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.fillText(text, 128, 128);

      const texture = new THREE.CanvasTexture(canvas);
      const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
      const sprite = new THREE.Sprite(spriteMaterial);
      sprite.scale.set(500, 500, 1);
      return sprite;
    };

    // X axis - Red
    const xLabel = createTextSprite("X", "#ff0000");
    xLabel.position.set(labelDistance, 0, 0);
    scene.add(xLabel);

    // Y axis - Green
    const yLabel = createTextSprite("Y", "#00ff00");
    yLabel.position.set(0, labelDistance, 0);
    scene.add(yLabel);

    // Z axis - Blue
    const zLabel = createTextSprite("Z", "#0000ff");
    zLabel.position.set(0, 0, labelDistance);
    scene.add(zLabel);
  },

  setupOrbitControls(camera, domElement) {
    // Use the professional OrbitControls from Three.js examples
    // Import: import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    // OR via CDN script tag in your HTML

    const controls = new THREE.OrbitControls(camera, domElement);

    // Configure controls for professional feel
    controls.enableDamping = true; // Smooth inertia
    controls.dampingFactor = 0.05;
    controls.screenSpacePanning = false; // Pan in XZ plane
    controls.minDistance = CONFIG.VIEWER.ZOOM_MIN_DISTANCE || 500;
    controls.maxDistance = CONFIG.VIEWER.ZOOM_MAX_DISTANCE || 50000;
    controls.maxPolarAngle = Math.PI; // Allow viewing from any angle

    // Optional: Restrict rotation if needed
    // controls.minPolarAngle = 0;
    // controls.maxPolarAngle = Math.PI / 2;

    // Enable panning with right-click or two-finger drag
    controls.enablePan = true;
    controls.panSpeed = 1.0;

    // Mouse button configuration
    controls.mouseButtons = {
      LEFT: THREE.MOUSE.ROTATE,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.PAN,
    };

    // Touch controls for mobile
    controls.touches = {
      ONE: THREE.TOUCH.ROTATE,
      TWO: THREE.TOUCH.DOLLY_PAN,
    };

    // Rotation speed
    controls.rotateSpeed = 1.0;
    controls.zoomSpeed = 1.0;

    // Store controls in AppState for access elsewhere
    AppState.controls = controls;

    console.log("✅ Professional OrbitControls initialized");
  },

  setupMeasurementOverlay(container) {
    // Create overlay div for measurements
    const overlay = document.createElement("div");
    overlay.id = "measurement-overlay";
    overlay.style.cssText = `
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(0, 0, 0, 0.8);
      color: #fff;
      padding: 15px;
      border-radius: 8px;
      font-family: 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.6;
      pointer-events: none;
      min-width: 200px;
      display: none;
      z-index: 1000;
    `;
    container.style.position = "relative";
    container.appendChild(overlay);
    AppState.measurementOverlay = overlay;
  },

  updateMeasurementOverlay(bbox, visible = true) {
    const overlay = AppState.measurementOverlay;
    if (!overlay) return;

    if (!visible || !bbox) {
      overlay.style.display = "none";
      return;
    }

    const size = new THREE.Vector3();
    bbox.getSize(size);

    overlay.innerHTML = `
      <div style="font-weight: bold; margin-bottom: 8px; color: #4CAF50;">📐 Dimensions</div>
      <div><span style="color: #ff6b6b;">Length (X):</span> ${size.x.toFixed(
        0
      )} mm</div>
      <div><span style="color: #4ecdc4;">Height (Y):</span> ${size.y.toFixed(
        0
      )} mm</div>
      <div><span style="color: #95a5a6;">Width (Z):</span> ${size.z.toFixed(
        0
      )} mm</div>
      <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #555;">
        <div><span style="color: #f7b731;">Volume:</span> ${(
          (size.x * size.y * size.z) /
          1000000
        ).toFixed(2)} L</div>
      </div>
    `;
    overlay.style.display = "block";
  },

  animate() {
    requestAnimationFrame(() => this.animate());

    // Update controls (required for damping)
    if (AppState.controls) {
      AppState.controls.update();
    }

    AppState.renderer.render(AppState.scene, AppState.camera);
  },

  handleResize(container) {
    const width = container.clientWidth;
    const height = container.clientHeight;
    AppState.camera.aspect = width / height;
    AppState.camera.updateProjectionMatrix();
    AppState.renderer.setSize(width, height);
  },

  // Load STL and add to scene
  loadSTL(url, color, onLoad) {
    const loader = new THREE.STLLoader();

    console.log(`Loading STL from: ${url}`);

    loader.load(
      url,
      (geometry) => {
        console.log("STL loaded successfully, processing geometry...");

        // Compute normals for proper lighting
        geometry.computeVertexNormals();

        // Center the model
        geometry.computeBoundingBox();
        const center = new THREE.Vector3();
        geometry.boundingBox.getCenter(center);
        geometry.translate(-center.x, -center.y, -center.z);

        // Recompute bounding box after translation
        geometry.computeBoundingBox();

        const material = new THREE.MeshPhongMaterial({
          color: color,
          transparent: true,
          opacity: 0.9,
          side: THREE.DoubleSide,
          flatShading: false,
        });

        const mesh = new THREE.Mesh(geometry, material);

        // OpenSCAD uses Z-up, Three.js uses Y-up
        // Rotate model: X becomes X, Y becomes -Z, Z becomes Y
        mesh.rotation.x = -Math.PI / 2;

        // Position model so it sits on the ground (bottom at y=0)
        // Need to compute bbox AFTER rotation
        const bbox = new THREE.Box3().setFromObject(mesh);
        const yMin = bbox.min.y;
        mesh.position.y = -yMin; // Move up so bottom is at y=0

        console.log(
          "Mesh created, vertices:",
          geometry.attributes.position.count
        );
        console.log("Bounding box (after rotation):", bbox);
        console.log("Positioned at y =", mesh.position.y);

        // Auto-fit camera to model - use 90% of view
        if (!AppState.currentMesh && !AppState.modifiedMesh) {
          this.fitCameraToModel(mesh, 0.9);
        }

        if (onLoad) onLoad(mesh);
      },
      (progress) => {
        if (progress.lengthComputable) {
          const percentComplete = (progress.loaded / progress.total) * 100;
          console.log(`Loading STL: ${percentComplete.toFixed(1)}%`);
        }
      },
      (error) => {
        console.error("Error loading STL:", error);
        console.error("URL:", url);
        UI.addMessage(
          "Error loading 3D model. Check console for details.",
          "error"
        );
      }
    );
  },

  // Fit camera to view the entire model
  // fillFactor: how much of the screen to fill (0.9 = 90%)
  fitCameraToModel(mesh, fillFactor = 0.9) {
    const boundingBox = new THREE.Box3().setFromObject(mesh);
    const size = new THREE.Vector3();
    const center = new THREE.Vector3();
    boundingBox.getSize(size);
    boundingBox.getCenter(center);

    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = AppState.camera.fov * (Math.PI / 180);
    let cameraDistance = Math.abs(maxDim / Math.sin(fov / 2));

    // Adjust for fill factor (0.9 = 90% of screen)
    cameraDistance *= 1 / fillFactor;

    // Position camera at an angle to see the model well
    const distance = cameraDistance * 1.2;
    AppState.camera.position.set(
      distance * 0.7,
      distance * 0.7,
      distance * 0.7
    );

    // Update OrbitControls target to the model center
    if (AppState.controls) {
      AppState.controls.target.copy(center);
      AppState.controls.update();
    }

    // Look at the center of the model
    AppState.camera.lookAt(center);
    AppState.camera.updateProjectionMatrix();

    console.log(`Camera positioned at distance: ${distance.toFixed(2)}`);
    console.log(
      `Model size: ${size.x.toFixed(2)} x ${size.y.toFixed(
        2
      )} x ${size.z.toFixed(2)}`
    );
  },

  // Switch view mode
  switchView(mode) {
    AppState.setViewerMode(mode);

    // Update button states
    document.querySelectorAll(".viewer-controls .btn").forEach((btn) => {
      btn.classList.remove("active");
    });

    if (mode === "current") {
      document.getElementById("show-current").classList.add("active");
      if (AppState.currentMesh) {
        AppState.currentMesh.visible = true;
        AppState.currentMesh.position.x = 0; // Reset position
        AppState.currentMesh.material.opacity = 0.9; // Reset opacity
      }
      if (AppState.modifiedMesh) {
        AppState.modifiedMesh.visible = false;
      }
    } else if (mode === "modified") {
      document.getElementById("show-modified").classList.add("active");
      if (AppState.currentMesh) {
        AppState.currentMesh.visible = false;
      }
      if (AppState.modifiedMesh) {
        AppState.modifiedMesh.visible = true;
        AppState.modifiedMesh.position.x = 0; // Reset position
      }
    } else if (mode === "both") {
      document.getElementById("show-both").classList.add("active");

      // Calculate spacing based on model size
      let spacing = 3000; // Default spacing
      if (AppState.currentMesh) {
        const bbox = new THREE.Box3().setFromObject(AppState.currentMesh);
        const size = new THREE.Vector3();
        bbox.getSize(size);
        spacing = Math.max(size.x, size.z) * 1.5; // 1.5x model width for nice spacing
      }

      if (AppState.currentMesh) {
        AppState.currentMesh.visible = true;
        AppState.currentMesh.position.x = -spacing / 2; // Left side
        AppState.currentMesh.material.opacity = 0.9; // Keep solid
      }
      if (AppState.modifiedMesh) {
        AppState.modifiedMesh.visible = true;
        AppState.modifiedMesh.position.x = spacing / 2; // Right side
      }
    }
  },

  // Add dimension lines to a mesh
  addDimensionLines(mesh) {
    // Remove old dimension lines if they exist
    this.removeDimensionLines();

    const bbox = new THREE.Box3().setFromObject(mesh);
    const size = new THREE.Vector3();
    bbox.getSize(size);
    const center = new THREE.Vector3();
    bbox.getCenter(center);

    const dimensionGroup = new THREE.Group();
    dimensionGroup.name = "dimensionLines";

    // Create dimension line material
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0xffaa00,
      linewidth: 2,
      opacity: 0.8,
      transparent: true,
    });

    const textColor = "#ffaa00";
    const offset = Math.max(size.x, size.y, size.z) * 0.15;

    // X dimension (length) - front bottom
    this.createDimensionLine(
      new THREE.Vector3(bbox.min.x, bbox.min.y - offset, bbox.max.z + offset),
      new THREE.Vector3(bbox.max.x, bbox.min.y - offset, bbox.max.z + offset),
      `${size.x.toFixed(0)} mm`,
      lineMaterial,
      textColor,
      dimensionGroup
    );

    // Y dimension (height) - right side
    this.createDimensionLine(
      new THREE.Vector3(bbox.max.x + offset, bbox.min.y, bbox.max.z + offset),
      new THREE.Vector3(bbox.max.x + offset, bbox.max.y, bbox.max.z + offset),
      `${size.y.toFixed(0)} mm`,
      lineMaterial,
      textColor,
      dimensionGroup
    );

    // Z dimension (width) - right bottom
    this.createDimensionLine(
      new THREE.Vector3(bbox.max.x + offset, bbox.min.y - offset, bbox.min.z),
      new THREE.Vector3(bbox.max.x + offset, bbox.min.y - offset, bbox.max.z),
      `${size.z.toFixed(0)} mm`,
      lineMaterial,
      textColor,
      dimensionGroup
    );

    AppState.scene.add(dimensionGroup);
    AppState.dimensionGroup = dimensionGroup;
  },

  // Create a single dimension line with label
  createDimensionLine(start, end, label, lineMaterial, textColor, group) {
    // Main dimension line
    const points = [start, end];
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const line = new THREE.Line(geometry, lineMaterial);
    group.add(line);

    // End caps
    const capSize = Math.max(100, start.distanceTo(end) * 0.02);
    const direction = new THREE.Vector3().subVectors(end, start).normalize();
    const perpendicular = new THREE.Vector3(
      -direction.z,
      0,
      direction.x
    ).normalize();

    // Start cap
    const startCap1 = start
      .clone()
      .add(perpendicular.clone().multiplyScalar(capSize));
    const startCap2 = start
      .clone()
      .add(perpendicular.clone().multiplyScalar(-capSize));
    const startCapGeom = new THREE.BufferGeometry().setFromPoints([
      startCap1,
      startCap2,
    ]);
    group.add(new THREE.Line(startCapGeom, lineMaterial));

    // End cap
    const endCap1 = end
      .clone()
      .add(perpendicular.clone().multiplyScalar(capSize));
    const endCap2 = end
      .clone()
      .add(perpendicular.clone().multiplyScalar(-capSize));
    const endCapGeom = new THREE.BufferGeometry().setFromPoints([
      endCap1,
      endCap2,
    ]);
    group.add(new THREE.Line(endCapGeom, lineMaterial));

    // Text label
    const midpoint = new THREE.Vector3()
      .addVectors(start, end)
      .multiplyScalar(0.5);
    const textSprite = this.createTextSprite(label, textColor, 64);
    textSprite.position.copy(midpoint);
    textSprite.scale.set(400, 200, 1);
    group.add(textSprite);
  },

  // Create text sprite for labels
  createTextSprite(text, color, fontSize = 120) {
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    canvas.width = 512;
    canvas.height = 256;

    // Background
    context.fillStyle = "rgba(0, 0, 0, 0.7)";
    context.fillRect(0, 0, canvas.width, canvas.height);

    // Text
    context.font = `Bold ${fontSize}px Arial`;
    context.fillStyle = color;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(text, canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMaterial = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      opacity: 0.9,
    });
    return new THREE.Sprite(spriteMaterial);
  },

  // Remove dimension lines
  removeDimensionLines() {
    if (AppState.dimensionGroup) {
      AppState.scene.remove(AppState.dimensionGroup);
      AppState.dimensionGroup = null;
    }
  },

  // Toggle dimension lines
  toggleDimensions() {
    if (AppState.dimensionGroup) {
      this.removeDimensionLines();
      return false;
    } else {
      const mesh = AppState.currentMesh || AppState.modifiedMesh;
      if (mesh) {
        this.addDimensionLines(mesh);
        return true;
      }
    }
    return false;
  },

  // Clear all meshes from scene
  clearScene() {
    if (AppState.currentMesh && AppState.scene) {
      AppState.scene.remove(AppState.currentMesh);
    }
    if (AppState.modifiedMesh && AppState.scene) {
      AppState.scene.remove(AppState.modifiedMesh);
    }
    this.removeDimensionLines();
    console.log("🧹 Scene cleared");
  },

  // Helper method to reset camera view
  resetCamera() {
    if (AppState.controls) {
      const mesh = AppState.currentMesh || AppState.modifiedMesh;
      if (mesh) {
        this.fitCameraToModel(mesh, 0.9);
      } else {
        // Reset to default position
        const { x, y, z } = CONFIG.VIEWER.CAMERA_INITIAL_POSITION;
        AppState.camera.position.set(x, y, z);
        AppState.controls.target.set(0, 0, 0);
        AppState.controls.update();
      }
    }
  },
};

// Export to global scope
window.Viewer = Viewer;
