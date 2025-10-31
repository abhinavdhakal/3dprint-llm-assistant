/**
 * Concrete Printer Slicer Integration
 * Handles G-code generation and toolpath visualization
 */

const Slicer = {
  toolpathsVisible: false,
  gcodeGenerated: false,
  presets: {}, // Will be loaded from JSON file
  presetsLoaded: false,

  /**
   * Load printer presets from JSON file
   */
  async loadPresets() {
    try {
      const response = await fetch("/printer_presets.json");
      const data = await response.json();

      // Convert array to object keyed by id
      this.presets = {};
      data.presets.forEach((preset) => {
        this.presets[preset.id] = preset.settings;
      });

      // Populate the dropdown with presets
      this.populatePresetDropdown(data.presets);

      this.presetsLoaded = true;
      console.log("[SLICER] Loaded presets:", Object.keys(this.presets));

      return true;
    } catch (error) {
      console.error("[ERROR] Failed to load printer presets:", error);
      UI.addMessage("Failed to load printer presets", "error");
      return false;
    }
  },

  /**
   * Populate preset dropdown with options from JSON
   */
  populatePresetDropdown(presets) {
    const presetSelect = document.getElementById("printer-preset");
    if (!presetSelect) return;

    // Clear existing options except "Custom"
    presetSelect.innerHTML = '<option value="custom">Custom Settings</option>';

    // Add presets from JSON
    presets.forEach((preset) => {
      const option = document.createElement("option");
      option.value = preset.id;
      option.textContent = preset.name;
      option.title = preset.description; // Tooltip
      presetSelect.appendChild(option);
    });
  },

  /**
   * Initialize slicer (setup event listeners)
   */
  async init() {
    // Load presets from JSON file
    await this.loadPresets();

    // Setup preset selector
    const presetSelect = document.getElementById("printer-preset");
    if (presetSelect) {
      presetSelect.addEventListener("change", (e) => {
        this.applyPreset(e.target.value);
      });
    }

    // Setup input change listeners to auto-switch to custom
    const settingInputs = [
      "layer-height",
      "nozzle-diameter",
      "print-speed",
      "travel-speed",
      "concrete-density",
      "waste-factor",
    ];

    settingInputs.forEach((inputId) => {
      const input = document.getElementById(inputId);
      if (input) {
        input.addEventListener("input", () => {
          this.switchToCustom();
        });
      }
    });

    // Setup simulation controls
    this.setupSimulationControls();
  },

  /**
   * Setup simulation control event listeners
   */
  setupSimulationControls() {
    // Play simulation
    const playBtn = document.getElementById("simulate-print-btn");
    if (playBtn) {
      playBtn.addEventListener("click", () => {
        const speed = parseFloat(
          document.getElementById("animation-speed").value
        );
        Viewer.startPrintSimulation(speed);
        UI.addMessage(
          "<i class='fas fa-play'></i> Started print simulation",
          "system",
          true
        );
      });
    }

    // Stop simulation
    const stopBtn = document.getElementById("stop-simulation-btn");
    if (stopBtn) {
      stopBtn.addEventListener("click", () => {
        Viewer.stopPrintSimulation();
        UI.addMessage(
          "<i class='fas fa-stop'></i> Stopped print simulation",
          "system",
          true
        );
      });
    }

    // Show all layers
    const showAllBtn = document.getElementById("show-all-layers-btn");
    if (showAllBtn) {
      showAllBtn.addEventListener("click", () => {
        Viewer.showAllLayers();
        UI.addMessage(
          "<i class='fas fa-layer-group'></i> Showing all layers",
          "system",
          true
        );
      });
    }

    // Layer slider
    const layerSlider = document.getElementById("layer-slider");
    const layerDisplay = document.getElementById("layer-display");
    if (layerSlider && layerDisplay) {
      layerSlider.addEventListener("input", (e) => {
        const layer = parseInt(e.target.value);
        layerDisplay.textContent = layer;
        Viewer.showLayerRange(0, layer);
      });
    }

    // Speed slider
    const speedSlider = document.getElementById("animation-speed");
    const speedDisplay = document.getElementById("speed-display");
    if (speedSlider && speedDisplay) {
      speedSlider.addEventListener("input", (e) => {
        const speed = parseFloat(e.target.value);
        speedDisplay.textContent = speed.toFixed(1);
        if (AppState.toolpathData) {
          AppState.toolpathData.animationSpeed = speed;
        }
      });
    }
  },

  /**
   * Switch preset selector to "Custom"
   */
  switchToCustom() {
    const presetSelect = document.getElementById("printer-preset");
    if (presetSelect && presetSelect.value !== "custom") {
      presetSelect.value = "custom";
    }
  },

  /**
   * Apply printer preset to settings
   */
  applyPreset(presetName) {
    if (presetName === "custom") return;

    const preset = this.presets[presetName];
    if (!preset) return;

    // Temporarily remove event listeners to prevent triggering switchToCustom
    const settingInputs = [
      "layer-height",
      "nozzle-diameter",
      "print-speed",
      "travel-speed",
      "concrete-density",
      "waste-factor",
    ];

    // Store the old values and handlers
    const inputs = settingInputs.map((id) => document.getElementById(id));

    // Remove event listeners by cloning and replacing
    inputs.forEach((input, index) => {
      if (input) {
        const newInput = input.cloneNode(true);
        input.parentNode.replaceChild(newInput, input);
      }
    });

    // Apply preset values
    document.getElementById("layer-height").value = preset.layerHeight;
    document.getElementById("nozzle-diameter").value = preset.nozzleDiameter;
    document.getElementById("print-speed").value = preset.printSpeed;
    document.getElementById("travel-speed").value = preset.travelSpeed;
    document.getElementById("concrete-density").value = preset.concreteDensity;
    document.getElementById("waste-factor").value = preset.wasteFactor;

    // Re-attach event listeners
    settingInputs.forEach((inputId) => {
      const input = document.getElementById(inputId);
      if (input) {
        input.addEventListener("input", () => {
          this.switchToCustom();
        });
      }
    });

    UI.addMessage(
      `<i class="fas fa-print"></i> Applied ${presetName.toUpperCase()} printer preset`,
      "system",
      true
    );
  },

  /**
   * Get current printer settings from UI
   */
  getSettings() {
    return {
      layer_height: parseFloat(document.getElementById("layer-height").value),
      nozzle_diameter: parseFloat(
        document.getElementById("nozzle-diameter").value
      ),
      print_speed: parseFloat(document.getElementById("print-speed").value),
      travel_speed: parseFloat(document.getElementById("travel-speed").value),
      concrete_density: parseFloat(
        document.getElementById("concrete-density").value
      ),
      waste_factor: parseFloat(document.getElementById("waste-factor").value),
    };
  },

  /**
   * Open the slicer modal
   */
  openModal() {
    const modal = document.getElementById("slicer-modal");
    if (modal) {
      modal.style.display = "flex";
    }
  },

  /**
   * Close the slicer modal
   */
  closeModal() {
    const modal = document.getElementById("slicer-modal");
    if (modal) {
      modal.style.display = "none";
    }
  },

  /**
   * Generate G-code from current STL
   */
  async generateGcode() {
    try {
      UI.updateStatus("Slicing for concrete printing...");

      // Get custom settings from UI
      const settings = this.getSettings();

      const response = await fetch(`${CONFIG.API_BASE}/slice-for-printing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          stl_file: "current.stl",
          settings: settings,
        }),
      });

      const result = await response.json();

      if (!result.success) {
        UI.addMessage(`Slicing failed: ${result.error}`, "error");
        UI.updateStatus("Slicing failed");
        return null;
      }

      console.log("[SLICER] G-code generated:", result);

      // Display slicing results
      this.displaySlicingResults(result);

      // Enable visualize button
      this.gcodeGenerated = true;
      document.getElementById("visualize-toolpaths-btn").disabled = false;

      UI.updateStatus("G-code ready for download");
      return result;
    } catch (error) {
      console.error("[ERROR] Error generating G-code:", error);
      UI.addMessage("Error generating G-code: " + error.message, "error");
      UI.updateStatus("Error");
      return null;
    }
  },

  /**
   * Display slicing results in UI
   */
  displaySlicingResults(result) {
    const container = document.getElementById("slicing-results");
    if (!container) return;

    const { layer_count, estimates, settings } = result;

    container.innerHTML = `
      <div class="results-section">
        <h4><i class="fas fa-check-circle"></i> Concrete Print Ready</h4>
        
        <div class="result-row">
          <span class="label"><i class="fas fa-layer-group"></i> Layers:</span>
          <span class="value">${layer_count}</span>
        </div>
        
        <div class="result-row">
          <span class="label"><i class="fas fa-arrows-alt-v"></i> Layer Height:</span>
          <span class="value">${settings.layer_height}mm</span>
        </div>
        
        <div class="result-row">
          <span class="label"><i class="fas fa-circle"></i> Nozzle Diameter:</span>
          <span class="value">${settings.nozzle_diameter}mm</span>
        </div>
        
        <div class="result-row">
          <span class="label"><i class="fas fa-tachometer-alt"></i> Print Speed:</span>
          <span class="value">${settings.print_speed}mm/s</span>
        </div>
        
        <h5><i class="fas fa-chart-bar"></i> Estimates</h5>
        
        <div class="result-row">
          <span class="label"><i class="fas fa-clock"></i> Print Time:</span>
          <span class="value">${estimates.time.estimated_time_hours}h (${
      estimates.time.estimated_time_minutes
    }min)</span>
        </div>
        
        <div class="result-row">
          <span class="label"><i class="fas fa-route"></i> Print Distance:</span>
          <span class="value">${estimates.time.print_distance_m.toFixed(
            2
          )}m</span>
        </div>
        
        <div class="result-row">
          <span class="label"><i class="fas fa-cube"></i> Material Volume:</span>
          <span class="value">${estimates.material.volume_liters}L (${
      estimates.material.volume_m3
    }m³)</span>
        </div>
        
        <div class="result-row">
          <span class="label"><i class="fas fa-weight"></i> Concrete Weight:</span>
          <span class="value">${
            estimates.material.weight_with_waste_kg
          }kg (with 10% waste)</span>
        </div>
        
        <div class="result-actions">
          <button onclick="Slicer.downloadGcode()" class="btn btn-primary">
            <i class="fas fa-download"></i> Download G-code
          </button>
        </div>
        
        <div class="gcode-preview">
          <h5><i class="fas fa-code"></i> G-code Preview (first 50 lines):</h5>
          <pre>${result.gcode_preview}</pre>
        </div>
      </div>
    `;

    container.style.display = "block";
  },

  /**
   * Download generated G-code file
   */
  async downloadGcode() {
    try {
      const response = await fetch(`${CONFIG.API_BASE}/download-gcode`);

      if (!response.ok) {
        throw new Error("Failed to download G-code");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "concrete_print.gcode";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      UI.addMessage("G-code downloaded successfully", "success");
    } catch (error) {
      console.error("Error downloading G-code:", error);
      UI.addMessage("Error downloading G-code: " + error.message, "error");
    }
  },

  /**
   * Toggle toolpath visualization
   */
  async toggleToolpaths() {
    try {
      if (this.toolpathsVisible) {
        // Hide toolpaths and floating controls
        Viewer.clearToolpaths();
        this.toolpathsVisible = false;
        document.getElementById("visualize-toolpaths-btn").innerHTML =
          '<i class="fas fa-eye"></i> Show Toolpaths';
        document.getElementById("simulation-controls").style.display = "none";
        UI.addMessage("Toolpaths hidden", "system");
      } else {
        // Show toolpaths
        UI.updateStatus("Loading toolpath visualization...");

        const response = await fetch(
          `${CONFIG.API_BASE}/toolpath-visualization`
        );
        const result = await response.json();

        if (!result.success) {
          throw new Error(result.error);
        }

        // Pass visualization data to viewer
        Viewer.renderToolpaths(result.data);
        this.toolpathsVisible = true;
        document.getElementById("visualize-toolpaths-btn").innerHTML =
          '<i class="fas fa-eye-slash"></i> Hide Toolpaths';

        // Show simulation controls in right panel and configure layer slider
        const simControls = document.getElementById("simulation-controls");
        if (simControls) {
          simControls.style.display = "block";

          // Configure layer slider max value
          const layerSlider = document.getElementById("layer-slider");
          const layerCount = result.data.layers.length;
          if (layerSlider) {
            layerSlider.max = layerCount - 1;
            layerSlider.value = layerCount - 1;
            document.getElementById("layer-display").textContent =
              layerCount - 1;
          }
        }

        UI.updateStatus("Toolpaths visualized");
        UI.addMessage(
          "<i class='fas fa-info-circle'></i> Use simulation controls in the Concrete Printer panel",
          "success",
          true
        );
      }
    } catch (error) {
      console.error("Error toggling toolpaths:", error);
      UI.addMessage("Error: " + error.message, "error");
      UI.updateStatus("Error");
    }
  },
};
