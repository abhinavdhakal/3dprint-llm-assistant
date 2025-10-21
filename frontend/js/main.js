// Main Application Logic
const App = {
  // Initialize application
  init() {
    console.log("🚀 App initializing...");
    try {
      console.log("📐 Initializing viewer...");
      Viewer.init();

      console.log("📥 Loading current design...");
      this.loadCurrentDesign();

      console.log("🎯 Setting up event listeners...");
      this.setupEventListeners();

      console.log("✅ App initialized successfully");
    } catch (error) {
      console.error("❌ Error during initialization:", error);
      alert("Failed to initialize app: " + error.message);
    }
  },

  // Setup all event listeners
  setupEventListeners() {
    document
      .getElementById("submit-btn")
      .addEventListener("click", () => this.submitModification());
    document
      .getElementById("approve-btn")
      .addEventListener("click", () => this.approveDesign());
    document
      .getElementById("reject-btn")
      .addEventListener("click", () => this.rejectDesign());

    document
      .getElementById("show-current")
      .addEventListener("click", () => Viewer.switchView("current"));
    document
      .getElementById("show-modified")
      .addEventListener("click", () => Viewer.switchView("modified"));
    document
      .getElementById("show-both")
      .addEventListener("click", () => Viewer.switchView("both"));

    // Dimension toggle
    document
      .getElementById("toggle-dimensions")
      .addEventListener("click", () => {
        const showing = Viewer.toggleDimensions();
        const btn = document.getElementById("toggle-dimensions");
        if (showing) {
          btn.classList.add("active");
          UI.addMessage("Dimensions shown", "system");
        } else {
          btn.classList.remove("active");
          UI.addMessage("Dimensions hidden", "system");
        }
      });

    // Measurement tool toggle
    document
      .getElementById("toggle-measurement")
      .addEventListener("click", () => {
        const active = Viewer.toggleMeasurementMode();
        const btn = document.getElementById("toggle-measurement");
        if (active) {
          btn.classList.add("active");
          UI.addMessage(
            "Measurement mode: Click two points on the model",
            "system"
          );
        } else {
          btn.classList.remove("active");
          UI.addMessage("Measurement mode disabled", "system");
        }
      });

    // History controls
    document
      .getElementById("undo-btn")
      .addEventListener("click", () => this.handleUndo());
    document
      .getElementById("redo-btn")
      .addEventListener("click", () => this.handleRedo());
    document
      .getElementById("history-btn")
      .addEventListener("click", () => UI.toggleHistoryPanel());

    // Import/Export controls
    document
      .getElementById("import-export-btn")
      .addEventListener("click", () => UI.showImportExportMenu());

    // Import/Export menu buttons
    document
      .getElementById("import-scad-btn")
      .addEventListener("click", () => ImportExport.showImportDialog("scad"));

    // Project save/load buttons
    document
      .getElementById("new-project-btn")
      .addEventListener("click", () => ImportExport.newProject());
    document
      .getElementById("save-project-btn")
      .addEventListener("click", () => ImportExport.saveProject());
    document
      .getElementById("rename-project-btn")
      .addEventListener("click", () => ImportExport.renameProject());
    document
      .getElementById("open-project-btn")
      .addEventListener("click", () => ImportExport.showOpenProjectDialog());

    // Export buttons
    document
      .getElementById("export-stl-btn")
      .addEventListener("click", () => ImportExport.downloadSTL());
    document
      .getElementById("export-scad-btn")
      .addEventListener("click", () => ImportExport.exportCurrentSCAD());

    // Allow Enter to submit (with Shift+Enter for newline)
    document
      .getElementById("operator-input")
      .addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.submitModification();
        }
      });
  },

  // Load current design
  async loadCurrentDesign() {
    UI.updateStatus("Loading current design...");

    const result = await API.getCurrentDesign();

    if (!result.success) {
      UI.addMessage(`Failed to load current design: ${result.error}`, "error");
      UI.updateStatus("Error");
      return;
    }

    const data = result.data;

    // Check if no project is loaded
    if (data.status === "no_project") {
      // Clear UI to show empty state
      UI.displayParameters({}, "parameters-display");
      UI.displayAnalysis(null, "analysis-display");
      UI.updateProjectName(null);

      UI.updateStatus("No project loaded");
      UI.addMessage(
        "No project loaded. Import a SCAD file to begin.",
        "system"
      );
      return;
    }

    AppState.setCurrentDesign(data);
    UI.displayParameters(data.parameters, "parameters-display");
    UI.displayAnalysis(data.analysis, "analysis-display");

    // Restore project name from localStorage if available
    const savedProjectName = localStorage.getItem("currentProjectName");
    if (savedProjectName) {
      UI.updateProjectName(savedProjectName);
    }

    // Load history from backend first
    const historyLoaded = await History.loadFromBackend();

    if (!historyLoaded) {
      // If backend history doesn't exist, initialize with current design
      History.init(data);
      console.log("📚 Initialized new history with current design");
      UI.addMessage(
        "💡 Tip: History is only saved when you Approve designs",
        "system"
      );
    } else {
      console.log("📚 History loaded from backend");
      UI.addMessage(
        `📚 Loaded ${History.versions.length} saved versions from history`,
        "system"
      );
    }

    UI.updateStatus("Loading 3D model..."); // Load STL into viewer
    Viewer.loadSTL(
      API.getSTLUrl("current.stl"),
      CONFIG.COLORS.CURRENT_MESH,
      (mesh) => {
        AppState.setCurrentMesh(mesh);
        // Measurements shown automatically in loadSTL
        document.getElementById("toggle-dimensions").classList.add("active");
        UI.updateStatus("Ready");
        UI.addMessage("Current design loaded successfully", "system");
      }
    );
  },

  // Submit modification request
  async submitModification() {
    const input = document.getElementById("operator-input").value.trim();
    if (!input) return;

    UI.addMessage(input, "user");
    UI.updateStatus("Processing request...");
    UI.setSubmitButtonEnabled(false);
    document.getElementById("operator-input").value = "";

    const result = await API.submitModification(input);

    if (!result.success) {
      UI.addMessage("Error processing request", "error");
      UI.updateStatus("Error");
      UI.setSubmitButtonEnabled(true);
      UI.clearInput();
      return;
    }

    const data = result.data;

    if (data.status === "clarification_needed") {
      UI.addMessage(data.question, "assistant");
      UI.updateStatus("Awaiting clarification");
      UI.setSubmitButtonEnabled(true);
      UI.clearInput();
      return;
    }

    if (data.status === "success") {
      AppState.setModifiedDesign(data);

      UI.addMessage(`Understood: ${data.understood}`, "assistant");
      UI.addMessage(`Reasoning: ${data.reasoning}`, "assistant");

      // Display modifications
      UI.displayModificationInfo(data);

      // Load modified STL
      Viewer.loadSTL(
        API.getSTLUrl("modified.stl"),
        CONFIG.COLORS.MODIFIED_MESH,
        (mesh) => {
          mesh.visible = false;
          AppState.setModifiedMesh(mesh);

          // Enable view controls
          UI.enableViewButtons();

          // Show action buttons
          UI.showActionButtons();

          // Automatically switch to "both" view to show the comparison
          Viewer.switchView("both");

          UI.updateStatus("Review changes and approve/reject");
        }
      );
    } else {
      UI.addMessage(data.message || "No changes made", "assistant");
      UI.updateStatus("Ready");
    }

    UI.setSubmitButtonEnabled(true);
    UI.clearInput();
  },

  // Approve design
  async approveDesign() {
    UI.updateStatus("Approving design...");

    // Get description from current modification
    const description =
      AppState.modifiedDesign?.understood || "Design approved";

    const result = await API.approveDesign(description);

    if (!result.success) {
      UI.addMessage("Error approving design", "error");
      return;
    }

    const data = result.data;

    if (data.status === "approved") {
      // Show version info if available
      if (data.version) {
        UI.addMessage(
          `Design approved! (v${data.version}: ${data.backup})`,
          "system"
        );
      } else {
        UI.addMessage(
          "Design approved! This is now the current design.",
          "system"
        );
      }

      // Replace current with modified
      if (AppState.modifiedMesh) {
        // Reset position and opacity before making it current
        AppState.modifiedMesh.position.x = 0;
        AppState.modifiedMesh.position.y = 0;
        AppState.modifiedMesh.position.z = 0;
        AppState.modifiedMesh.material.opacity = 0.9;

        // Recompute correct position (sitting on ground)
        const bbox = new THREE.Box3().setFromObject(AppState.modifiedMesh);
        AppState.modifiedMesh.position.y = -bbox.min.y;
      }

      AppState.setCurrentMesh(AppState.modifiedMesh);
      AppState.setModifiedMesh(null);

      // Normalize the design object for currentDesign
      const normalizedDesign = {
        parameters:
          AppState.modifiedDesign.new_parameters ||
          AppState.modifiedDesign.parameters,
        analysis: AppState.modifiedDesign.analysis,
        understood: AppState.modifiedDesign.understood,
        reasoning: AppState.modifiedDesign.reasoning,
        modifications: AppState.modifiedDesign.modifications,
      };

      console.log("Approving design, adding to history:", description);
      console.log("Normalized design parameters:", normalizedDesign.parameters);

      AppState.setCurrentDesign(normalizedDesign);
      AppState.clearModifiedDesign();

      // Add to history
      History.addVersion(normalizedDesign, description);

      console.log("History now has", History.versions.length, "versions");
      console.log("Current history index:", History.currentIndex);

      // Reset UI
      UI.hideActionButtons();
      UI.hideModificationInfo();
      UI.disableViewButtons();

      Viewer.switchView("current");
      UI.displayParameters(normalizedDesign.parameters, "parameters-display");
      UI.displayAnalysis(normalizedDesign.analysis, "analysis-display");

      // Reload the current STL from server to ensure it's up to date
      UI.updateStatus("Loading approved design...");
      Viewer.loadSTL(
        API.getSTLUrl("current.stl"),
        CONFIG.COLORS.CURRENT_MESH,
        (mesh) => {
          AppState.setCurrentMesh(mesh);
          UI.updateStatus("Ready for next modification");
          UI.addMessage("Current design updated and displayed", "system");
        }
      );
    }
  },

  // Reject design
  async rejectDesign() {
    console.log("🚫 Rejecting design");

    UI.addMessage("Changes rejected. Keeping current design.", "system");

    UI.updateStatus("Reverting changes...");

    // Remove modified mesh from viewer
    AppState.removeModifiedMesh();

    // Clear modified design data
    AppState.clearModifiedDesign();

    // NO need to call backend - current design is already correct
    // Just reset the UI to show current design

    // Reset UI
    UI.hideActionButtons();
    UI.hideModificationInfo();
    UI.disableViewButtons();

    // Make sure current design is displayed
    if (AppState.currentDesign) {
      UI.displayParameters(
        AppState.currentDesign.parameters,
        "parameters-display"
      );
      UI.displayAnalysis(AppState.currentDesign.analysis, "analysis-display");
    }

    Viewer.switchView("current");
    UI.updateStatus("Ready");

    console.log("✅ Design rejected, showing current design");
  },

  // Handle undo
  handleUndo() {
    const previousVersion = History.undo();
    if (previousVersion) {
      this.loadVersionFromHistory(previousVersion);
      UI.addMessage("Reverted to previous version", "system");
    }
  },

  // Handle redo
  handleRedo() {
    const nextVersion = History.redo();
    if (nextVersion) {
      this.loadVersionFromHistory(nextVersion);
      UI.addMessage("Restored to next version", "system");
    }
  },

  // Load a version from history
  async loadVersionFromHistory(version) {
    console.log("📖 Loading version from history:", version.description);
    console.log("   Version object:", version);
    console.log("   Version number:", version.version);
    UI.updateStatus("Loading version...");

    // Clear any modified design first
    if (AppState.modifiedMesh) {
      AppState.removeModifiedMesh();
      AppState.clearModifiedDesign();
    }

    // Check if we have a version number (new method)
    if (version.version) {
      console.log(
        "   Using restore-version API with version:",
        version.version
      );
      const result = await API.restoreVersion(version.version);

      if (!result.success) {
        UI.addMessage("Error loading version: " + result.error, "error");
        UI.updateStatus("Error");
        return;
      }

      // Update display
      const data = result.data;
      UI.displayParameters(data.parameters || {}, "parameters-display");
      if (data.analysis) {
        UI.displayAnalysis(data.analysis, "analysis-display");
      }

      // Reload current STL
      Viewer.loadSTL(
        API.getSTLUrl("current.stl"),
        CONFIG.COLORS.CURRENT_MESH,
        (mesh) => {
          AppState.setCurrentMesh(mesh);
          Viewer.switchView("current");
          UI.updateStatus("Version restored");
        }
      );
      return;
    }

    // Fallback: Old method using parameters (deprecated)
    console.warn("⚠️ No version number - using legacy parameter update method");
    const parameters = version.design?.parameters || version.parameters;

    if (!parameters) {
      console.error("❌ No parameters found in version:", version);
      UI.addMessage("Error: Version has no parameters", "error");
      UI.updateStatus("Error");
      return;
    }

    const description = version.description || "version_loaded";
    console.log("📤 Using legacy updateParameters:", {
      parameters,
      description,
      createBackup: false,
    });

    const result = await API.updateParameters(
      parameters,
      description,
      false // createBackup = false
    );

    if (!result.success) {
      console.error("❌ Backend error:", result.error);
      UI.addMessage(`Failed to load version: ${result.error}`, "error");
      UI.updateStatus("Error");
      return;
    }

    // Update app state with version data
    AppState.setCurrentDesign(version.design || { parameters, analysis: null });

    // Update UI
    console.log("🎨 Updating UI with parameters:", parameters);
    UI.displayParameters(parameters, "parameters-display");
    if (version.design?.analysis) {
      UI.displayAnalysis(version.design.analysis, "analysis-display");
    }
    UI.hideActionButtons();
    UI.hideModificationInfo();
    UI.disableViewButtons();

    // Reload the regenerated STL
    console.log("🔄 Reloading STL from backend...");
    Viewer.loadSTL(
      API.getSTLUrl("current.stl"),
      CONFIG.COLORS.CURRENT_MESH,
      (mesh) => {
        console.log("✅ New mesh loaded, updating scene");
        AppState.setCurrentMesh(mesh);
        Viewer.switchView("current");
        UI.updateStatus("Ready");
        console.log("✅ Version loaded successfully");
      }
    );
  },

  // Regenerate STL from imported design
  async regenerateSTLFromImport(design) {
    UI.updateStatus("Generating 3D model from imported design...");

    // Send parameters to backend to generate STL
    const description =
      design.importedFrom || design.description || "imported_design";
    const result = await API.updateParameters(design.parameters, description);

    if (!result.success) {
      UI.addMessage(`Failed to generate model: ${result.error}`, "error");
      UI.updateStatus("Import complete (model generation failed)");
      return;
    }

    // Update app state
    AppState.setCurrentDesign(design);

    // Load the generated STL
    Viewer.loadSTL(
      API.getSTLUrl("current.stl"),
      CONFIG.COLORS.CURRENT_MESH,
      (mesh) => {
        AppState.setCurrentMesh(mesh);
        Viewer.switchView("current");
        UI.updateStatus("Import complete");
      }
    );
  },
};

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  console.log("📄 DOM loaded, starting app...");
  console.log("🔍 Checking required modules:");
  console.log("  - CONFIG:", typeof CONFIG);
  console.log("  - AppState:", typeof AppState);
  console.log("  - History:", typeof History);
  console.log("  - ImportExport:", typeof ImportExport);
  console.log("  - UI:", typeof UI);
  console.log("  - API:", typeof API);
  console.log("  - Viewer:", typeof Viewer);

  try {
    App.init();
  } catch (error) {
    console.error("❌ Fatal error:", error);
    alert(
      "Failed to start app: " + error.message + "\n\nCheck console for details."
    );
  }
});

// Export to global scope
window.App = App;
