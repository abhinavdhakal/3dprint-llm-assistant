// Three.js Viewer Module
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
    container.appendChild(renderer.domElement);
    AppState.setRenderer(renderer);

    // Lights
    this.setupLights(scene);

    // Grid and Axes
    this.setupHelpers(scene);

    // Controls
    this.setupOrbitControls(renderer.domElement);

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

  setupOrbitControls(canvas) {
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };

    canvas.addEventListener("mousedown", (e) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    canvas.addEventListener("mousemove", (e) => {
      if (!isDragging) return;

      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;

      const rotationSpeed = CONFIG.VIEWER.ROTATION_SPEED;
      const camera = AppState.camera;

      // Get current position in spherical coordinates (Y-up system)
      const radius = camera.position.length();
      let theta = Math.atan2(camera.position.x, camera.position.z); // Horizontal angle
      let phi = Math.acos(
        Math.max(-1, Math.min(1, camera.position.y / radius))
      ); // Vertical angle from Y-axis

      // Update angles based on mouse movement
      theta -= deltaX * rotationSpeed; // Left/right rotation
      phi = Math.max(
        0.1,
        Math.min(Math.PI - 0.1, phi - deltaY * rotationSpeed) // Up/down (already correct)
      );

      // Convert back to Cartesian coordinates
      camera.position.x = radius * Math.sin(phi) * Math.sin(theta);
      camera.position.y = radius * Math.cos(phi);
      camera.position.z = radius * Math.sin(phi) * Math.cos(theta);

      camera.lookAt(0, 0, 0);
      previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    canvas.addEventListener("mouseup", () => {
      isDragging = false;
    });

    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const delta =
        e.deltaY > 0 ? CONFIG.VIEWER.ZOOM_SPEED : -CONFIG.VIEWER.ZOOM_SPEED;
      const camera = AppState.camera;
      const direction = camera.position.clone().normalize();

      const newPosition = camera.position
        .clone()
        .addScaledVector(direction, delta);
      const distance = newPosition.length();

      if (
        distance > CONFIG.VIEWER.ZOOM_MIN_DISTANCE &&
        distance < CONFIG.VIEWER.ZOOM_MAX_DISTANCE
      ) {
        camera.position.copy(newPosition);
        camera.lookAt(0, 0, 0);
      }
    });

    canvas.addEventListener("mouseleave", () => {
      isDragging = false;
    });
  },

  animate() {
    requestAnimationFrame(() => this.animate());
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

  // Clear all meshes from scene
  clearScene() {
    if (AppState.currentMesh && AppState.scene) {
      AppState.scene.remove(AppState.currentMesh);
    }
    if (AppState.modifiedMesh && AppState.scene) {
      AppState.scene.remove(AppState.modifiedMesh);
    }
    console.log("🧹 Scene cleared");
  },
};

// Export to global scope
window.Viewer = Viewer;
