// UI Module - Handles all UI updates and display functions
const UI = {
  // Display parameters
  displayParameters(params, containerId) {
    console.log("🎨 UI.displayParameters called with:", params);
    const container = document.getElementById(containerId);

    if (!container) {
      console.error("❌ Container not found:", containerId);
      return;
    }

    // Handle null or empty parameters
    if (!params || Object.keys(params).length === 0) {
      container.innerHTML = '<div class="loading">No design parameters</div>';
      return;
    }

    let html = "";

    for (const [key, value] of Object.entries(params)) {
      const displayName = key
        .replace(/_/g, " ")
        .replace(/\b\w/g, (l) => l.toUpperCase());
      html += `
        <div class="param-row">
            <span class="param-name">${displayName}:</span>
            <span class="param-value">${value} mm</span>
        </div>
      `;
    }

    container.innerHTML = html;
    console.log("✅ Parameters displayed in", containerId);
  },

  // Display parameters with change highlighting
  displayParametersWithChanges(newParams, modifications) {
    const container = document.getElementById("parameters-display");
    let html =
      '<h3 style="margin-top: 0; color: #4caf50;">Modified Parameters</h3>';

    for (const [key, value] of Object.entries(newParams)) {
      const displayName = key
        .replace(/_/g, " ")
        .replace(/\b\w/g, (l) => l.toUpperCase());

      // Check if this parameter was modified
      const isModified = modifications.hasOwnProperty(key);
      const oldValue = AppState.currentDesign.parameters[key];

      if (isModified) {
        // Highlight changed parameters
        html += `
          <div class="param-row" style="background-color: #e8f5e9; border-left: 3px solid #4caf50; padding-left: 8px;">
              <span class="param-name">${displayName}:</span>
              <span class="param-value">
                  <span style="text-decoration: line-through; color: #999;">${oldValue} mm</span>
                  <span style="color: #4caf50; font-weight: bold;"> → ${value} mm</span>
              </span>
          </div>
        `;
      } else {
        // Unchanged parameters
        html += `
          <div class="param-row">
              <span class="param-name">${displayName}:</span>
              <span class="param-value">${value} mm</span>
          </div>
        `;
      }
    }

    container.innerHTML = html;
  },

  // Display analysis data
  displayAnalysis(analysis, containerId) {
    const container = document.getElementById(containerId);
    let html = "";

    // Handle null or empty analysis
    if (!analysis) {
      container.innerHTML = '<div class="loading">No analysis data</div>';
      return;
    }

    if (analysis.volume_liters) {
      html += `
        <div class="param-row">
            <span class="param-name">Volume:</span>
            <span class="param-value">${analysis.volume_liters.toFixed(
              2
            )} L</span>
        </div>
      `;
    }

    if (analysis.height_mm) {
      html += `
        <div class="param-row">
            <span class="param-name">Height:</span>
            <span class="param-value">${analysis.height_mm.toFixed(0)} mm</span>
        </div>
      `;
    }

    container.innerHTML = html || '<div class="loading">No analysis data</div>';
  },

  // Display modification information
  displayModificationInfo(data) {
    const container = document.getElementById("modification-info");
    const changesDiv = document.getElementById("changes-summary");
    const reasoningDiv = document.getElementById("reasoning");

    let changesHTML = "<ul>";
    // Use changes_summary array from the LLM response
    if (data.changes_summary && Array.isArray(data.changes_summary)) {
      data.changes_summary.forEach(change => {
        changesHTML += `<li>${change}</li>`;
      });
    } else if (typeof data.changes_summary === 'string') {
      // If it's a single string, just display it
      changesHTML += `<li>${data.changes_summary}</li>`;
    }
    changesHTML += "</ul>";

    changesDiv.innerHTML = changesHTML;
    reasoningDiv.innerHTML = `<p><strong>Reasoning:</strong> ${data.reasoning}</p>`;

    container.style.display = "block";

    // Display new analysis
    if (data.analysis) {
      this.displayAnalysis(data.analysis, "analysis-display");
    }
  },

  // Add message to chat
  addMessage(text, type) {
    const chatHistory = document.getElementById("chat-history");
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${type}-message`;
    messageDiv.textContent = text;
    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
  },

  // Update status bar
  updateStatus(text) {
    document.getElementById("status-text").textContent = `● ${text}`;
  },

  // Show/hide action buttons
  showActionButtons() {
    document.getElementById("action-buttons").style.display = "flex";
  },

  hideActionButtons() {
    document.getElementById("action-buttons").style.display = "none";
  },

  // Show/hide modification info
  showModificationInfo() {
    document.getElementById("modification-info").style.display = "block";
  },

  hideModificationInfo() {
    document.getElementById("modification-info").style.display = "none";
  },

  // Enable/disable view buttons
  enableViewButtons() {
    document.getElementById("show-modified").disabled = false;
    document.getElementById("show-both").disabled = false;
  },

  disableViewButtons() {
    document.getElementById("show-modified").disabled = true;
    document.getElementById("show-both").disabled = true;
  },

  // Clear input field
  clearInput() {
    document.getElementById("operator-input").value = "";
  },

  // Enable/disable submit button
  setSubmitButtonEnabled(enabled) {
    document.getElementById("submit-btn").disabled = !enabled;
  },

  // Update history panel
  updateHistoryPanel() {
    const container = document.getElementById("history-list");
    if (!container) return;

    const versions = History.getAllVersions();
    let html = "";

    if (versions.length === 0) {
      html = '<div class="history-empty">No version history yet</div>';
    } else {
      versions.reverse().forEach((version) => {
        const date = new Date(version.timestamp);
        const timeStr = date.toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
        });
        const dateStr = date.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        });

        const isCurrentClass = version.isCurrent ? "history-current" : "";

        html += `
          <div class="history-item ${isCurrentClass}" data-index="${
          version.index
        }">
            <div class="history-header">
              <span class="history-time">${dateStr} ${timeStr}</span>
              ${
                version.isCurrent
                  ? '<span class="history-badge">Current</span>'
                  : ""
              }
            </div>
            <div class="history-description">${version.description}</div>
            <div class="history-actions">
              <button class="btn-small history-load-btn" data-index="${
                version.index
              }">
                Load
              </button>
            </div>
          </div>
        `;
      });
    }

    container.innerHTML = html;

    // Add event listeners to history buttons
    container.querySelectorAll(".history-load-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const index = parseInt(e.target.dataset.index);
        const version = History.jumpToVersion(index);
        if (version && App && App.loadVersionFromHistory) {
          App.loadVersionFromHistory(version);
          // Close the history panel after loading
          UI.toggleHistoryPanel();
        }
      });
    });
  },

  // Toggle history panel visibility
  toggleHistoryPanel() {
    const panel = document.getElementById("history-panel");
    if (!panel) return;

    const isVisible = panel.style.display === "block";

    if (isVisible) {
      panel.style.display = "none";
      // Remove click outside listener
      document.removeEventListener("click", this._closeHistoryOnClickOutside);
    } else {
      panel.style.display = "block";
      this.updateHistoryPanel();
      // Add click outside listener after a brief delay to avoid immediate close
      setTimeout(() => {
        document.addEventListener("click", this._closeHistoryOnClickOutside);
      }, 100);
    }
  },

  // Close history panel when clicking outside
  _closeHistoryOnClickOutside(e) {
    const panel = document.getElementById("history-panel");
    const historyBtn = document.getElementById("history-btn");

    if (panel && !panel.contains(e.target) && e.target !== historyBtn) {
      panel.style.display = "none";
      document.removeEventListener("click", UI._closeHistoryOnClickOutside);
    }
  },

  // Show import/export menu
  showImportExportMenu() {
    const menu = document.getElementById("import-export-menu");
    if (!menu) return;

    const isVisible = menu.style.display === "block";

    if (isVisible) {
      menu.style.display = "none";
      // Remove click outside listener
      document.removeEventListener("click", this._closeMenuOnClickOutside);
    } else {
      menu.style.display = "block";
      // Add click outside listener after a brief delay to avoid immediate close
      setTimeout(() => {
        document.addEventListener("click", this._closeMenuOnClickOutside);
      }, 100);
    }
  },

  // Close menu when clicking outside
  _closeMenuOnClickOutside(e) {
    const menu = document.getElementById("import-export-menu");
    const importBtn = document.getElementById("import-btn");
    const exportBtn = document.getElementById("export-btn");

    if (
      menu &&
      !menu.contains(e.target) &&
      e.target !== importBtn &&
      e.target !== exportBtn
    ) {
      menu.style.display = "none";
      document.removeEventListener("click", UI._closeMenuOnClickOutside);
    }
  },

  // Update project name display
  updateProjectName(projectName) {
    const display = document.getElementById("project-name-display");
    if (display) {
      if (projectName) {
        display.textContent = projectName;
        display.style.color = "#667eea";
      } else {
        display.textContent = "No project loaded";
        display.style.color = "#999";
      }
    }
  },
};

// Export to global scope
window.UI = UI;
