// History Module - Design Version Management with Undo/Redo
const History = {
  // Version storage
  versions: [],
  currentIndex: -1,
  maxVersions: 50, // Keep last 50 versions

  // Initialize history with current design
  init(initialDesign) {
    this.versions = [];
    this.currentIndex = -1;
    if (initialDesign) {
      this.addVersion(initialDesign, "Initial design loaded");
    }
  },

  // Load history from backend
  async loadFromBackend() {
    console.log("📚 Loading history from backend...");
    const result = await API.getHistory();

    if (result.success && result.data) {
      // Convert backend format to frontend format
      this.versions = result.data.map((entry) => ({
        id: entry.id,
        version: entry.version, // Store version number for restoration
        timestamp: entry.timestamp,
        description: entry.description,
        design: {
          parameters: entry.parameters,
          analysis: null, // Analysis not stored in history
        },
        parameters: entry.parameters,
        analysis: null,
      }));

      this.currentIndex = this.versions.length - 1; // Set to latest
      console.log(`✅ Loaded ${this.versions.length} versions from backend`);
      this.updateUI();
      return true;
    } else {
      console.warn("Could not load history from backend:", result.error);
      return false;
    }
  },

  // Add a new version to history
  addVersion(design, description = "Design modified") {
    console.log("📚 addVersion called with:", description);
    console.log("  Design parameters:", design.parameters);

    const version = {
      id: this.generateVersionId(),
      timestamp: new Date().toISOString(),
      description: description,
      design: JSON.parse(JSON.stringify(design)), // Deep clone
      parameters: JSON.parse(JSON.stringify(design.parameters)),
      analysis: design.analysis
        ? JSON.parse(JSON.stringify(design.analysis))
        : null,
    };

    // If we're not at the end of history, remove future versions
    if (this.currentIndex < this.versions.length - 1) {
      console.log(
        `  Removing ${
          this.versions.length - this.currentIndex - 1
        } future versions`
      );
      this.versions = this.versions.slice(0, this.currentIndex + 1);
    }

    // Add new version
    this.versions.push(version);
    this.currentIndex = this.versions.length - 1;

    // Limit history size
    if (this.versions.length > this.maxVersions) {
      this.versions.shift();
      this.currentIndex--;
    }

    console.log(`✅ Version added: ${version.id} - ${description}`);
    console.log(
      `  Total versions: ${this.versions.length}, Current index: ${this.currentIndex}`
    );
    this.updateUI();
    return version;
  },

  // Generate unique version ID
  generateVersionId() {
    const date = new Date();
    const timestamp = date.getTime();
    const random = Math.floor(Math.random() * 1000);
    return `v${timestamp}_${random}`;
  },

  // Can undo?
  canUndo() {
    return this.currentIndex > 0;
  },

  // Can redo?
  canRedo() {
    return this.currentIndex < this.versions.length - 1;
  },

  // Undo to previous version
  undo() {
    if (!this.canUndo()) {
      console.warn("Cannot undo: at beginning of history");
      return null;
    }

    this.currentIndex--;
    const version = this.versions[this.currentIndex];
    console.log(`Undo to: ${version.id} - ${version.description}`);
    this.updateUI();
    return version;
  },

  // Redo to next version
  redo() {
    if (!this.canRedo()) {
      console.warn("Cannot redo: at end of history");
      return null;
    }

    this.currentIndex++;
    const version = this.versions[this.currentIndex];
    console.log(`Redo to: ${version.id} - ${version.description}`);
    this.updateUI();
    return version;
  },

  // Get current version
  getCurrentVersion() {
    if (this.currentIndex >= 0 && this.currentIndex < this.versions.length) {
      return this.versions[this.currentIndex];
    }
    return null;
  },

  // Get version by index
  getVersion(index) {
    if (index >= 0 && index < this.versions.length) {
      return this.versions[index];
    }
    return null;
  },

  // Jump to specific version
  jumpToVersion(index) {
    if (index >= 0 && index < this.versions.length) {
      this.currentIndex = index;
      const version = this.versions[index];
      console.log(`Jumped to: ${version.id} - ${version.description}`);
      this.updateUI();
      return version;
    }
    return null;
  },

  // Get all versions for display
  getAllVersions() {
    return this.versions.map((version, index) => ({
      ...version,
      index: index,
      isCurrent: index === this.currentIndex,
    }));
  },

  // Get formatted version name
  getVersionName(version) {
    const date = new Date(version.timestamp);
    const timeStr = date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
    const dateStr = date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
    return `${dateStr} ${timeStr} - ${version.description}`;
  },

  // Export version as JSON
  exportVersion(index = this.currentIndex) {
    const version = this.getVersion(index);
    if (!version) return null;

    const exportData = {
      version: version.id,
      timestamp: version.timestamp,
      description: version.description,
      parameters: version.parameters,
      analysis: version.analysis,
    };

    return exportData;
  },

  // Export all history
  exportAllHistory() {
    return {
      versions: this.versions,
      currentIndex: this.currentIndex,
      exportedAt: new Date().toISOString(),
    };
  },

  // Import history from export
  importHistory(historyData) {
    try {
      this.versions = historyData.versions || [];
      this.currentIndex = historyData.currentIndex || 0;
      console.log(`Imported ${this.versions.length} versions`);
      this.updateUI();
      return true;
    } catch (error) {
      console.error("Error importing history:", error);
      return false;
    }
  },

  // Clear all history
  clear() {
    this.versions = [];
    this.currentIndex = -1;
    this.updateUI();
    console.log("History cleared");
  },

  // Get statistics
  getStats() {
    return {
      totalVersions: this.versions.length,
      currentIndex: this.currentIndex,
      canUndo: this.canUndo(),
      canRedo: this.canRedo(),
      memoryUsage: JSON.stringify(this.versions).length,
    };
  },

  // Update UI (called after history changes)
  updateUI() {
    // Update undo/redo button states
    const undoBtn = document.getElementById("undo-btn");
    const redoBtn = document.getElementById("redo-btn");

    if (undoBtn) {
      undoBtn.disabled = !this.canUndo();
      undoBtn.title = this.canUndo()
        ? `Undo: ${this.versions[this.currentIndex - 1]?.description}`
        : "Nothing to undo";
    }

    if (redoBtn) {
      redoBtn.disabled = !this.canRedo();
      redoBtn.title = this.canRedo()
        ? `Redo: ${this.versions[this.currentIndex + 1]?.description}`
        : "Nothing to redo";
    }

    // Update history panel if visible
    if (UI && UI.updateHistoryPanel) {
      UI.updateHistoryPanel();
    }

    // Update version counter
    const versionCounter = document.getElementById("version-counter");
    if (versionCounter) {
      versionCounter.textContent = `Version ${this.currentIndex + 1}/${
        this.versions.length
      }`;
    }
  },

  // Generate downloadable filename
  generateFilename(version = null, extension = "json") {
    const ver = version || this.getCurrentVersion();
    if (!ver) return `design_export.${extension}`;

    const date = new Date(ver.timestamp);
    const dateStr = date.toISOString().replace(/:/g, "-").replace(/\..+/, "");
    const desc = ver.description
      .replace(/[^a-z0-9]/gi, "_")
      .toLowerCase()
      .substring(0, 30);

    return `design_${dateStr}_${desc}.${extension}`;
  },
};

// Export to global scope
window.History = History;
