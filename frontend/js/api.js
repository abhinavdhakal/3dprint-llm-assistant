// API Module - Handles all backend communication
const API = {
  // Get current design
  async getCurrentDesign() {
    const url = `${CONFIG.API_BASE}/current-design`;
    console.log("📡 API: GET", url);

    try {
      const response = await fetch(url);
      console.log("📡 Response status:", response.status, response.statusText);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log("📡 Response data:", data);
      return { success: true, data };
    } catch (error) {
      console.error("❌ Error loading design:", error);
      console.error("   URL was:", url);
      console.error("   CONFIG.API_BASE:", CONFIG.API_BASE);
      return { success: false, error: error.message };
    }
  },

  // Get version history from backend
  async getHistory() {
    const url = `${CONFIG.API_BASE}/history`;
    console.log("📡 API: GET", url);

    try {
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log("📚 History loaded:", data.count, "versions");
      return { success: true, data: data.history };
    } catch (error) {
      console.error("❌ Error loading history:", error);
      return { success: false, error: error.message };
    }
  },

  // Submit modification request
  async submitModification(input) {
    try {
      const response = await fetch(`${CONFIG.API_BASE}/modify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input }),
      });

      const data = await response.json();
      return { success: true, data };
    } catch (error) {
      console.error("Error submitting modification:", error);
      return { success: false, error: error.message };
    }
  },

  // Approve design
  async approveDesign(description = "Design approved") {
    try {
      const response = await fetch(`${CONFIG.API_BASE}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description }),
      });

      const data = await response.json();
      return { success: true, data };
    } catch (error) {
      console.error("Error approving design:", error);
      return { success: false, error: error.message };
    }
  },

  // Restore version from backup (for undo/redo)
  async restoreVersion(version) {
    console.log("↩️  API.restoreVersion called for version:", version);

    try {
      const response = await fetch(`${CONFIG.API_BASE}/restore-version`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version }),
      });

      console.log("   Response status:", response.status, response.statusText);

      const data = await response.json();
      console.log("   Response data:", data);

      if (!response.ok) {
        throw new Error(
          data.message || data.error || "Failed to restore version"
        );
      }

      return { success: true, data };
    } catch (error) {
      console.error("❌ Error restoring version:", error);
      return { success: false, error: error.message };
    }
  },

  // Update parameters (for undo/redo - DEPRECATED, use restoreVersion instead)
  async updateParameters(
    parameters,
    description = "Parameters updated",
    createBackup = false
  ) {
    console.log("📤 API.updateParameters called:");
    console.log("   Parameters:", parameters);
    console.log("   Description:", description);
    console.log("   Create backup:", createBackup);

    try {
      const payload = {
        parameters,
        description,
        create_backup: createBackup,
      };

      console.log("   Sending payload:", payload);

      const response = await fetch(`${CONFIG.API_BASE}/update-parameters`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      console.log("   Response status:", response.status, response.statusText);

      const data = await response.json();
      console.log("   Response data:", data);

      if (!response.ok) {
        throw new Error(
          data.message || data.error || "Failed to update parameters"
        );
      }

      return { success: true, data };
    } catch (error) {
      console.error("❌ Error updating parameters:", error);
      return { success: false, error: error.message };
    }
  },

  // Get STL file URL with cache buster
  getSTLUrl(filename) {
    // CONFIG.API_BASE already includes /api, so just append /models/filename
    const url = `${CONFIG.API_BASE}/models/${filename}?t=${Date.now()}`;
    console.log("🔗 STL URL:", url);
    return url;
  },

  // Upload SCAD file
  async uploadSCAD(file) {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${CONFIG.API_BASE}/upload-scad`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "Failed to upload SCAD file");
      }

      return { success: true, data };
    } catch (error) {
      console.error("Error uploading SCAD:", error);
      return { success: false, error: error.message };
    }
  },

  // Update version description in history
  async updateVersionDescription(versionId, description) {
    try {
      const response = await fetch(
        `${CONFIG.API_BASE}/update-version-description`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            version_id: versionId,
            description: description,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "Failed to update version description");
      }

      return { success: true, data };
    } catch (error) {
      console.error("Error updating version description:", error);
      return { success: false, error: error.message };
    }
  },

  // Save project as zip file
  async saveProject(projectName) {
    try {
      console.log("💾 API: Saving project:", projectName);

      const response = await fetch(`${CONFIG.API_BASE}/save-project`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: projectName }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || "Failed to save project");
      }

      // Get the blob
      const blob = await response.blob();

      // Extract filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get("Content-Disposition");
      let filename = `${projectName}_project.zip`;
      if (contentDisposition) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(
          contentDisposition
        );
        if (matches && matches[1]) {
          filename = matches[1].replace(/['"]/g, "");
        }
      }

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      console.log("✅ Project saved:", filename);
      return { success: true, filename };
    } catch (error) {
      console.error("❌ Error saving project:", error);
      return { success: false, error: error.message };
    }
  },

  // Load project from zip file
  async loadProject(file) {
    try {
      console.log("📂 API: Loading project:", file.name);

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${CONFIG.API_BASE}/load-project`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "Failed to load project");
      }

      console.log("✅ Project loaded:", data.manifest?.name);
      return { success: true, data };
    } catch (error) {
      console.error("❌ Error loading project:", error);
      return { success: false, error: error.message };
    }
  },

  // Clear project (backend)
  async clearProject() {
    try {
      console.log("🗑️ API: Clearing project on backend");

      const response = await fetch(`${CONFIG.API_BASE}/clear-project`, {
        method: "POST",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to clear project");
      }

      console.log("✅ Backend project cleared");
      return { success: true };
    } catch (error) {
      console.error("❌ Error clearing project:", error);
      return { success: false, error: error.message };
    }
  },
};

// Export to global scope
window.API = API;
