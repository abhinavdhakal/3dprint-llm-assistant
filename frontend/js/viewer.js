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

    // Setup interactive measurement tool
    this.setupMeasurementTool(container, camera);

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
    // Simple grid
    const gridHelper = new THREE.GridHelper(
      CONFIG.VIEWER.GRID_SIZE,
      CONFIG.VIEWER.GRID_DIVISIONS,
      CONFIG.COLORS.GRID_CENTER,
      CONFIG.COLORS.GRID_LINES
    );
    scene.add(gridHelper);

    // Simple axes
    const axesHelper = new THREE.AxesHelper(CONFIG.VIEWER.AXES_SIZE);
    scene.add(axesHelper);

    // Add axis labels
    this.addAxisLabels(scene);
  },

  addAxisLabels(scene) {
    const labelDistance = (CONFIG.VIEWER.GRID_SIZE / 2) * 1.1;

    const createTextSprite = (text, color) => {
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");
      canvas.width = 256;
      canvas.height = 256;

      context.font = "Bold 100px Arial";
      context.fillStyle = color;
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.fillText(text, 128, 128);

      const texture = new THREE.CanvasTexture(canvas);
      const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
      const sprite = new THREE.Sprite(spriteMaterial);
      sprite.scale.set(400, 400, 1);
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
    const overlay = document.createElement("div");
    overlay.id = "measurement-overlay";
    overlay.style.cssText = `
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(30, 30, 30, 0.95);
      color: #fff;
      padding: 12px 16px;
      border-radius: 4px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 12px;
      line-height: 1.8;
      pointer-events: none;
      min-width: 180px;
      display: none;
      z-index: 1000;
      border: 1px solid rgba(255, 255, 255, 0.1);
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

    const volume = (size.x * size.y * size.z) / 1000000;

    overlay.innerHTML = `
      <div style="margin-bottom: 6px; font-weight: 600; opacity: 0.7; font-size: 11px;">DIMENSIONS</div>
      <div>Length: <span style="float: right; font-weight: 500;">${size.x.toFixed(
        0
      )} mm</span></div>
      <div>Height: <span style="float: right; font-weight: 500;">${size.y.toFixed(
        0
      )} mm</span></div>
      <div>Width: <span style="float: right; font-weight: 500;">${size.z.toFixed(
        0
      )} mm</span></div>
      <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.1);">
        Volume: <span style="float: right; font-weight: 500;">${volume.toFixed(
          2
        )} L</span>
      </div>
    `;
    overlay.style.display = "block";
  },

  setupMeasurementTool(container, camera) {
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    AppState.measurementPoints = [];
    AppState.measurementMode = false;

    // Create measurement info overlay
    const measureInfo = document.createElement("div");
    measureInfo.id = "measurement-info";
    measureInfo.style.cssText = `
      position: absolute;
      bottom: 10px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(30, 30, 30, 0.95);
      color: #fff;
      padding: 8px 16px;
      border-radius: 4px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 12px;
      display: none;
      z-index: 1000;
      border: 1px solid rgba(255, 255, 255, 0.1);
    `;
    measureInfo.textContent = "Click two points to measure distance";
    container.appendChild(measureInfo);
    AppState.measurementInfo = measureInfo;

    const canvas = AppState.renderer.domElement;

    const onClick = (event) => {
      if (!AppState.measurementMode) return;

      const rect = canvas.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);

      const meshes = [];
      if (AppState.currentMesh) meshes.push(AppState.currentMesh);
      if (AppState.modifiedMesh) meshes.push(AppState.modifiedMesh);

      const intersects = raycaster.intersectObjects(meshes);

      if (intersects.length > 0) {
        const point = intersects[0].point.clone();
        AppState.measurementPoints.push(point);

        // Add point marker
        const markerGeom = new THREE.SphereGeometry(30, 8, 8);
        const markerMat = new THREE.MeshBasicMaterial({ color: 0xff0000 });
        const marker = new THREE.Mesh(markerGeom, markerMat);
        marker.position.copy(point);
        AppState.scene.add(marker);

        if (AppState.measurementPoints.length === 1) {
          measureInfo.textContent = "Click second point";
        } else if (AppState.measurementPoints.length === 2) {
          // Calculate distance
          const distance = AppState.measurementPoints[0].distanceTo(
            AppState.measurementPoints[1]
          );

          // Draw line
          const lineGeom = new THREE.BufferGeometry().setFromPoints(
            AppState.measurementPoints
          );
          const lineMat = new THREE.LineBasicMaterial({
            color: 0xff0000,
            linewidth: 2,
          });
          const measurementLine = new THREE.Line(lineGeom, lineMat);
          AppState.scene.add(measurementLine);

          // Add label
          const midpoint = new THREE.Vector3()
            .addVectors(
              AppState.measurementPoints[0],
              AppState.measurementPoints[1]
            )
            .multiplyScalar(0.5);

          const measurementLabel = this.createMeasurementLabel(
            `${distance.toFixed(1)} mm`
          );
          measurementLabel.position.copy(midpoint);
          AppState.scene.add(measurementLabel);

          measureInfo.textContent = `Distance: ${distance.toFixed(
            1
          )} mm (Click to measure again)`;

          // Reset for next measurement
          AppState.measurementPoints = [];
        }
      }
    };

    canvas.addEventListener("click", onClick);
    AppState.measurementClickHandler = onClick;
  },

  createMeasurementLabel(text) {
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    canvas.width = 512;
    canvas.height = 128;

    context.fillStyle = "rgba(0, 0, 0, 0.8)";
    context.fillRect(0, 0, canvas.width, canvas.height);

    context.font = "Bold 60px Arial";
    context.fillStyle = "#ffffff";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(text, canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
    });
    const sprite = new THREE.Sprite(material);
    sprite.scale.set(800, 200, 1);
    return sprite;
  },

  toggleMeasurementMode() {
    const measureInfo = AppState.measurementInfo;
    if (!measureInfo) return false;

    AppState.measurementMode = !AppState.measurementMode;

    if (AppState.measurementMode) {
      // Enable measurement mode
      measureInfo.style.display = "block";
      measureInfo.textContent = "Click two points to measure distance";
      return true;
    } else {
      // Disable measurement mode
      measureInfo.style.display = "none";
      this.clearMeasurements();
      AppState.measurementPoints = [];
      return false;
    }
  },

  clearMeasurements() {
    // Remove all measurement objects from scene
    const objectsToRemove = [];
    AppState.scene.traverse((object) => {
      if (object.isMesh && object.geometry instanceof THREE.SphereGeometry) {
        if (
          object.geometry.parameters &&
          object.geometry.parameters.radius === 30
        ) {
          objectsToRemove.push(object);
        }
      }
      if (object.isLine && object.material.color.getHex() === 0xff0000) {
        objectsToRemove.push(object);
      }
      if (object.isSprite && object.scale.x === 800) {
        objectsToRemove.push(object);
      }
    });

    objectsToRemove.forEach((obj) => AppState.scene.remove(obj));
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

        // Show measurements
        this.updateMeasurementOverlay(bbox, true);

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

  // Toggle dimension overlay
  toggleDimensions() {
    const overlay = AppState.measurementOverlay;
    if (!overlay) return false;

    const isVisible = overlay.style.display !== "none";

    if (isVisible) {
      overlay.style.display = "none";
      return false;
    } else {
      const mesh = AppState.currentMesh || AppState.modifiedMesh;
      if (mesh) {
        const bbox = new THREE.Box3().setFromObject(mesh);
        this.updateMeasurementOverlay(bbox, true);
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
    console.log("Scene cleared");
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
