// Import/Export Module - Handles file import/export operations
const ImportExport = {
  // Export design as JSON
  async exportDesignJSON() {
    try {
      const design = AppState.currentDesign;
      if (!design) {
        UI.addMessage("No design to export", "error");
        return;
      }

      const exportData = {
        format: "concrete-design-v1",
        timestamp: new Date().toISOString(),
        parameters: design.parameters,
        analysis: design.analysis,
      };

      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: "application/json",
      });

      const version = History.getCurrentVersion();
      const filename = History.generateFilename(version, "json");

      this.downloadBlob(blob, filename);
      UI.addMessage(`Design exported: ${filename}`, "system");
      UI.showImportExportMenu(); // Close menu after export
    } catch (error) {
      console.error("Error exporting design:", error);
      UI.addMessage(`Export failed: ${error.message}`, "error");
    }
  },

  // Export history as JSON
  async exportHistoryJSON() {
    try {
      const history = History.getAll();

      const exportData = {
        format: "concrete-history-v1",
        timestamp: new Date().toISOString(),
        count: history.length,
        versions: history,
      };

      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: "application/json",
      });

      const timestamp = new Date()
        .toISOString()
        .replace(/[:.]/g, "-")
        .slice(0, -5);
      const filename = `concrete-history-${timestamp}.json`;

      this.downloadBlob(blob, filename);
      UI.addMessage(`History exported: ${filename}`, "system");
      UI.showImportExportMenu(); // Close menu after export
    } catch (error) {
      console.error("Error exporting history:", error);
      UI.addMessage(`Export failed: ${error.message}`, "error");
    }
  },

  // Import design from JSON file
  async importDesignJSON(file) {
    try {
      const text = await file.text();
      const data = JSON.parse(text);

      // Validate format
      if (data.format !== "concrete-design-v1") {
        throw new Error("Invalid design file format");
      }

      // Create design object
      const design = {
        parameters: data.parameters,
        analysis: data.analysis,
        imported: true,
        importedFrom: file.name,
      };

      // Add to history
      const description = `Imported: ${file.name}`;
      History.addVersion(design, description);

      // Update UI
      UI.displayParameters(design.parameters, "parameters-display");
      if (design.analysis) {
        UI.displayAnalysis(design.analysis, "analysis-display");
      }

      UI.addMessage(`Design imported from ${file.name}`, "system");
      UI.updateStatus("Imported design loaded");

      // Notify main app to regenerate STL
      if (App && App.regenerateSTLFromImport) {
        App.regenerateSTLFromImport(design);
      }

      return { success: true, design };
    } catch (error) {
      console.error("Error importing design:", error);
      UI.addMessage(`Import failed: ${error.message}`, "error");
      return { success: false, error: error.message };
    }
  },

  // Import history from JSON file
  async importHistoryJSON(file) {
    try {
      const text = await file.text();
      const data = JSON.parse(text);

      // Validate format
      if (data.format !== "concrete-history-v1") {
        throw new Error("Invalid history file format");
      }

      // Import all versions
      History.clear();
      for (const version of data.versions) {
        History.addVersion(version.design, version.description);
      }

      UI.addMessage(
        `History imported: ${data.count} versions restored`,
        "system"
      );
      UI.updateStatus("History restored");

      // Load the most recent version
      if (data.count > 0) {
        const latestVersion = History.getCurrentVersion();
        UI.displayParameters(
          latestVersion.design.parameters,
          "parameters-display"
        );
        if (latestVersion.design.analysis) {
          UI.displayAnalysis(latestVersion.design.analysis, "analysis-display");
        }
      }

      return { success: true };
    } catch (error) {
      console.error("Error importing history:", error);
      UI.addMessage(`Import failed: ${error.message}`, "error");
      return { success: false, error: error.message };
    }
  },

  // Import SCAD file
  async importSCADFile(file) {
    try {
      const result = await API.uploadSCAD(file);

      if (result.success) {
        const data = result.data;

        // Ask user to name the project
        const defaultName = (data.filename || file.name).replace(".scad", "");
        let projectName = prompt("Name this project:", defaultName);

        if (!projectName) {
          projectName = defaultName; // Use default if cancelled
        }

        // Clean up the name (remove special characters)
        projectName = projectName.replace(/[^a-zA-Z0-9_-]/g, "_");

        // Store project name in localStorage
        localStorage.setItem("lastSaveProject", projectName);
        localStorage.setItem("currentProjectName", projectName);
        console.log(`📝 Project named: ${projectName}`);

        // Send project name to backend for persistence
        try {
          if (typeof API !== "undefined" && API.setProjectName) {
            await API.setProjectName(projectName);
          } else {
            console.warn(
              "API.setProjectName not available - please refresh the page"
            );
          }
        } catch (error) {
          console.error("Failed to set project name on backend:", error);
          // Continue anyway - localStorage has the name
        }

        // Update project name display
        UI.updateProjectName(projectName);

        // Update the initial version description in history to use project name
        if (data.version_reset && data.initial_version) {
          // Wait for history to load, then update the first version description
          await History.loadFromBackend();
          const firstVersion = History.versions[0];
          if (firstVersion) {
            const newDescription = `Original design: ${projectName}`;
            firstVersion.description = newDescription;

            // Update backend history as well
            await API.updateVersionDescription(firstVersion.id, newDescription);

            console.log(
              `Updated initial version description to use project name: ${projectName}`
            );
          }
        }

        // Create design from parsed parameters
        const design = {
          parameters: data.parameters,
          analysis: data.analysis,
          imported: true,
          importedFrom: file.name,
        };

        // If backend reset version history (new file workflow), clear frontend history
        if (data.version_reset) {
          History.clear();
          console.log(
            `🆕 Version history reset for new file: ${
              data.filename || file.name
            }`
          );

          // Backend created initial version (v0001), reload from backend
          if (data.initial_version) {
            await History.loadFromBackend();
            console.log(
              `📚 Loaded initial version v${data.initial_version} from backend`
            );
          }
        } else {
          // Not a reset, just add to existing history
          const description = `Imported SCAD: ${data.filename || file.name}`;
          History.addVersion(design, description);
        }

        // Update UI
        UI.displayParameters(design.parameters, "parameters-display");
        if (design.analysis) {
          UI.displayAnalysis(design.analysis, "analysis-display");
        }

        // Load STL
        if (data.stl_path) {
          Viewer.loadSTL(
            `${CONFIG.API_BASE}${data.stl_path}?t=${Date.now()}`,
            CONFIG.COLORS.CURRENT_MESH,
            (mesh) => {
              AppState.setCurrentMesh(mesh);
              const fileName = data.filename || file.name;
              UI.updateStatus(`SCAD file imported: ${fileName}`);

              // Show version info if initial version was created
              if (data.initial_version) {
                UI.addMessage(
                  `SCAD imported: ${fileName} (${data.initial_backup})`,
                  "system"
                );
              } else {
                UI.addMessage(`SCAD imported: ${fileName}`, "system");
              }
            }
          );
        }

        return { success: true, design };
      } else {
        throw new Error(result.error || "Import failed");
      }
    } catch (error) {
      console.error("Error importing SCAD:", error);
      UI.addMessage(`SCAD import failed: ${error.message}`, "error");
      return { success: false, error: error.message };
    }
  },

  // Download current STL
  async downloadSTL(filename = "current") {
    try {
      const url = `${CONFIG.API_BASE}/models/${filename}.stl`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }

      const blob = await response.blob();
      const version = History.getCurrentVersion();
      const downloadFilename = History.generateFilename(version, "stl");

      this.downloadBlob(blob, downloadFilename);
      UI.addMessage(`STL downloaded: ${downloadFilename}`, "system");
      UI.showImportExportMenu(); // Close menu after download
    } catch (error) {
      console.error("Error downloading STL:", error);
      UI.addMessage(`STL download failed: ${error.message}`, "error");
    }
  },

  // Export current SCAD file
  async exportCurrentSCAD() {
    try {
      const url = `${CONFIG.API_BASE}/download-current-scad`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }

      const blob = await response.blob();

      // Get filename from Content-Disposition header or construct it
      const contentDisposition = response.headers.get("content-disposition");
      let filename = "design.scad";

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      this.downloadBlob(blob, filename);
      UI.addMessage(`SCAD exported: ${filename}`, "system");
      UI.showImportExportMenu(); // Close menu after download
    } catch (error) {
      console.error("Error exporting current SCAD:", error);
      UI.addMessage(`SCAD export failed: ${error.message}`, "error");
    }
  },

  // Export SCAD file from version history (kept for future use)
  async exportSCADVersion(versionNum) {
    try {
      const url = `${CONFIG.API_BASE}/download-scad-version/${versionNum}`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }

      const blob = await response.blob();

      // Get filename from Content-Disposition header or construct it
      const contentDisposition = response.headers.get("content-disposition");
      let filename = `version_${versionNum}.scad`;

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      this.downloadBlob(blob, filename);
      UI.addMessage(`SCAD exported: ${filename}`, "system");
    } catch (error) {
      console.error("Error exporting SCAD version:", error);
      UI.addMessage(`SCAD export failed: ${error.message}`, "error");
    }
  },

  // Save entire project as zip
  async saveProject() {
    try {
      // Get current project name from localStorage
      let projectName =
        localStorage.getItem("currentProjectName") || "concrete_project";

      UI.updateStatus("Saving project...");

      const result = await API.saveProject(projectName);

      if (result.success) {
        UI.addMessage(`Project saved: ${result.filename}`, "system");
        UI.updateStatus("Project saved");

        // Store last save time
        localStorage.setItem("lastSaveTime", Date.now());

        return { success: true, filename: result.filename };
      } else {
        throw new Error(result.error || "Save failed");
      }
    } catch (error) {
      console.error("Error saving project:", error);
      UI.addMessage(`Save failed: ${error.message}`, "error");
      return { success: false, error: error.message };
    }
  },

  // Rename the current project
  async renameProject() {
    try {
      const currentName =
        localStorage.getItem("currentProjectName") || "concrete_project";

      const newName = prompt("Rename project:", currentName);

      if (!newName || newName === currentName) {
        // User cancelled or no change
        return { success: false, cancelled: true };
      }

      // Clean up the name (remove special characters)
      const cleanName = newName.replace(/[^a-zA-Z0-9_-]/g, "_");

      // Store new project name
      localStorage.setItem("currentProjectName", cleanName);
      localStorage.setItem("lastSaveProject", cleanName);

      // Update project name display
      UI.updateProjectName(cleanName);

      UI.addMessage(`Project renamed to: ${cleanName}`, "system");
      console.log(`📝 Project renamed: ${currentName} → ${cleanName}`);

      return { success: true, name: cleanName };
    } catch (error) {
      console.error("Error renaming project:", error);
      UI.addMessage(`Rename failed: ${error.message}`, "error");
      return { success: false, error: error.message };
    }
  },

  // Create new project (clear everything)
  async newProject() {
    try {
      // Show warning
      const confirmed = confirm(
        "⚠️ WARNING: This will discard the current project and all unsaved changes!\n\n" +
          "Make sure you have saved your project first.\n\n" +
          "Are you sure you want to start a new project?"
      );

      if (!confirmed) {
        return { success: false, cancelled: true };
      }

      // Double confirmation for safety
      const doubleCheck = confirm(
        "This action cannot be undone!\n\n" +
          "Click OK to permanently discard the current project."
      );

      if (!doubleCheck) {
        return { success: false, cancelled: true };
      }

      UI.updateStatus("Creating new project...");

      // Clear backend first
      const backendResult = await API.clearProject();
      if (!backendResult.success) {
        throw new Error("Failed to clear backend: " + backendResult.error);
      }

      // Clear frontend state
      History.clear();
      AppState.setCurrentDesign(null);
      AppState.setModifiedDesign(null);

      // Clear meshes from scene
      if (AppState.currentMesh) {
        AppState.setCurrentMesh(null);
      }
      if (AppState.modifiedMesh) {
        AppState.setModifiedMesh(null);
      }

      // Clear toolpaths and gcode visualization
      if (typeof Viewer !== "undefined" && Viewer.clearToolpaths) {
        Viewer.clearToolpaths();
        console.log("🗑️  Cleared toolpaths and gcode");
      }

      // Clear localStorage
      localStorage.removeItem("currentProjectName");
      localStorage.removeItem("lastSaveProject");
      localStorage.removeItem("lastSaveTime");

      // Clear project name display
      UI.updateProjectName(null);

      // Clear UI
      UI.displayParameters({}, "parameters-display");
      UI.displayAnalysis(null, "analysis-display");
      document.getElementById("chat-history").innerHTML =
        '<div class="message system-message">New project started. Import a SCAD file to begin.</div>';

      UI.updateStatus("Ready - Import a SCAD file to start");
      UI.addMessage(
        "New project created. All previous data cleared.",
        "system"
      );

      console.log(
        "🆕 New project created - all state cleared (frontend + backend)"
      );

      return { success: true };
    } catch (error) {
      console.error("Error creating new project:", error);
      UI.addMessage(`Failed to create new project: ${error.message}`, "error");
      return { success: false, error: error.message };
    }
  },

  // Open project from zip file
  async openProject(file) {
    try {
      if (!file.name.endsWith(".zip")) {
        throw new Error("File must be a .zip project file");
      }

      UI.updateStatus("Loading project...");

      const result = await API.loadProject(file);

      if (result.success) {
        const data = result.data;

        // Clear current state
        History.clear();

        // Load history from backend
        await History.loadFromBackend();

        // Create design object
        const design = {
          parameters: data.parameters,
          analysis: data.analysis,
          imported: true,
          importedFrom: data.manifest?.scad_file || "project.scad",
        };

        // Update UI
        UI.displayParameters(design.parameters, "parameters-display");
        if (design.analysis) {
          UI.displayAnalysis(design.analysis, "analysis-display");
        }

        // Load STL
        if (data.stl_path) {
          Viewer.loadSTL(
            `${CONFIG.API_BASE}${data.stl_path}?t=${Date.now()}`,
            CONFIG.COLORS.CURRENT_MESH,
            (mesh) => {
              AppState.setCurrentMesh(mesh);
              const projectName = data.manifest?.name || "project";
              UI.updateStatus(`Project loaded: ${projectName}`);
              UI.addMessage(
                `Project loaded: ${projectName} (${data.version_count} versions)`,
                "system"
              );

              // Store project name
              localStorage.setItem("currentProjectName", projectName);
              localStorage.setItem("lastSaveProject", projectName);
            }
          );
        }

        return { success: true, data };
      } else {
        throw new Error(result.error || "Load failed");
      }
    } catch (error) {
      console.error("Error opening project:", error);
      UI.addMessage(`Load failed: ${error.message}`, "error");
      return { success: false, error: error.message };
    }
  },

  // Show file picker for opening project
  showOpenProjectDialog() {
    console.log("Opening project file picker");
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".zip";

    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      UI.showImportExportMenu(); // Close menu

      await this.openProject(file);
    };

    input.click();
  },

  // Helper: Download blob as file
  downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  // Show file picker for import
  showImportDialog(fileType = "json") {
    console.log(`Opening import dialog for: ${fileType}`);
    const input = document.createElement("input");
    input.type = "file";

    if (fileType === "json" || fileType === "history") {
      input.accept = ".json";
    } else if (fileType === "scad") {
      input.accept = ".scad";
    } else if (fileType === "any") {
      input.accept = ".json,.scad";
    }

    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      UI.showImportExportMenu(); // Close menu when import starts

      const extension = file.name.split(".").pop().toLowerCase();

      try {
        if (extension === "json") {
          // Try to determine if it's a design or history file
          const text = await file.text();
          const data = JSON.parse(text);

          if (data.format === "concrete-design-v1") {
            await this.importDesignJSON(file);
          } else if (data.format === "concrete-history-v1") {
            await this.importHistoryJSON(file);
          } else {
            UI.addMessage("Unknown JSON format", "error");
          }
        } else if (extension === "scad") {
          await this.importSCADFile(file);
        } else {
          UI.addMessage("Unsupported file type", "error");
        }
      } catch (error) {
        console.error("Error in import dialog:", error);
        UI.addMessage(`Import failed: ${error.message}`, "error");
      }
    };

    input.click();
  },
};

// Export to global scope
window.ImportExport = ImportExport;
