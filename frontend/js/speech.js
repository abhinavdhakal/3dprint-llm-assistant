// Speech Recognition Module using MediaRecorder + Whisper API
const Speech = {
  mediaRecorder: null,
  audioChunks: [],
  isListening: false,
  stream: null,
  recordingTimeout: null,
  recordingStartTime: null,
  MAX_RECORDING_DURATION: 15000, // 15 seconds
  currentAudioBlob: null,
  currentAudioUrl: null,
  recordingInterval: null,

  init() {
    // Check if MediaRecorder is supported
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      console.warn("Media recording not supported in this browser");
      return false;
    }

    console.log("✅ Audio recording initialized");
    this.setupVoiceButton();
    return true;
  },

  setupVoiceButton() {
    const voiceBtn = document.getElementById("voice-btn");
    if (!voiceBtn) return;

    voiceBtn.addEventListener("click", () => {
      if (this.isListening) {
        this.stopRecording();
      } else {
        this.startRecording();
      }
    });
  },

  async startRecording() {
    // Prevent multiple recordings
    if (this.isListening) return;

    try {
      // Clean up any previous recording
      this.cleanup();

      // Request microphone access
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Create MediaRecorder
      this.mediaRecorder = new MediaRecorder(this.stream);
      this.audioChunks = [];
      this.recordingStartTime = Date.now();

      // Collect audio data
      this.mediaRecorder.ondataavailable = (event) => {
        this.audioChunks.push(event.data);
      };

      // When recording stops, show playback controls
      this.mediaRecorder.onstop = async () => {
        const recordingDuration = Date.now() - this.recordingStartTime;

        // Check if recording was too short (less than 0.5 seconds)
        if (recordingDuration < 500) {
          UI.addMessage("⚠️ Recording too short. Please try again.", "system");
          this.cleanup();
          return;
        }

        // Create audio blob
        this.currentAudioBlob = new Blob(this.audioChunks, {
          type: "audio/webm",
        });
        this.currentAudioUrl = URL.createObjectURL(this.currentAudioBlob);

        // Show playback controls
        this.showPlaybackControls();
      };

      // Start recording
      this.mediaRecorder.start();
      this.isListening = true;
      this.updateVoiceButton(true);

      UI.addMessage("🎤 Recording... (max 15 seconds)", "system");

      // Update timer display
      let elapsedSeconds = 0;
      this.recordingInterval = setInterval(() => {
        elapsedSeconds++;
        const remaining = 15 - elapsedSeconds;
        if (remaining > 0) {
          this.updateRecordingTimer(elapsedSeconds, remaining);
        }
      }, 1000);

      // Set timeout to auto-stop after 15 seconds
      this.recordingTimeout = setTimeout(() => {
        if (this.isListening) {
          UI.addMessage(
            "⏱️ 15 second limit reached - stopped recording",
            "system"
          );
          this.stopRecording();
        }
      }, this.MAX_RECORDING_DURATION);
    } catch (error) {
      console.error("Error starting recording:", error);
      UI.addMessage(
        "Could not access microphone. Please allow microphone access.",
        "error"
      );
      this.cleanup();
    }
  },

  stopRecording() {
    if (!this.isListening) return;

    // Clear the timeout and interval
    if (this.recordingTimeout) {
      clearTimeout(this.recordingTimeout);
      this.recordingTimeout = null;
    }
    if (this.recordingInterval) {
      clearInterval(this.recordingInterval);
      this.recordingInterval = null;
    }

    // Stop the MediaRecorder
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
    }

    // Stop the microphone stream
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }

    this.isListening = false;
    this.updateVoiceButton(false);
  },

  updateRecordingTimer(elapsed, remaining) {
    const voiceBtn = document.getElementById("voice-btn");
    if (voiceBtn && this.isListening) {
      voiceBtn.textContent = `⏺️ ${elapsed}s (${remaining}s left)`;
    }
  },

  showPlaybackControls() {
    // Create playback controls container
    const controlsHtml = `
      <div id="voice-controls" style="display: flex; gap: 10px; align-items: center; padding: 10px; background: #f0f0f0; border-radius: 5px; margin: 10px 0;">
        <audio id="voice-preview" controls style="flex: 1;">
          <source src="${this.currentAudioUrl}" type="audio/webm">
        </audio>
        <button id="voice-send-btn" class="btn" style="background: #28a745; color: white;">
          ✓ Send
        </button>
        <button id="voice-cancel-btn" class="btn btn-secondary">
          ✗ Cancel
        </button>
      </div>
    `;

    // Insert controls into the UI (after the chat history)
    const chatHistory = document.getElementById("chat-history");
    if (chatHistory) {
      const controlsDiv = document.createElement("div");
      controlsDiv.innerHTML = controlsHtml;
      chatHistory.appendChild(controlsDiv.firstElementChild);
      chatHistory.scrollTop = chatHistory.scrollHeight;

      // Setup button event listeners
      document
        .getElementById("voice-send-btn")
        .addEventListener("click", () => {
          this.sendRecording();
        });

      document
        .getElementById("voice-cancel-btn")
        .addEventListener("click", () => {
          this.cancelRecording();
        });
    }

    UI.addMessage("🎧 Preview your recording, then Send or Cancel", "system");
  },

  async sendRecording() {
    if (!this.currentAudioBlob) return;

    // Remove playback controls
    const controls = document.getElementById("voice-controls");
    if (controls) controls.remove();

    UI.addMessage("🔄 Transcribing speech...", "system");

    await this.transcribeAudio(this.currentAudioBlob);
    this.cleanup();
  },

  cancelRecording() {
    // Remove playback controls
    const controls = document.getElementById("voice-controls");
    if (controls) controls.remove();

    UI.addMessage("❌ Recording cancelled", "system");
    this.cleanup();
  },

  cleanup() {
    // Revoke object URL to free memory
    if (this.currentAudioUrl) {
      URL.revokeObjectURL(this.currentAudioUrl);
      this.currentAudioUrl = null;
    }
    this.currentAudioBlob = null;
    this.audioChunks = [];

    // Stop any ongoing recording
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }

    if (this.recordingTimeout) {
      clearTimeout(this.recordingTimeout);
      this.recordingTimeout = null;
    }

    if (this.recordingInterval) {
      clearInterval(this.recordingInterval);
      this.recordingInterval = null;
    }

    this.isListening = false;
    this.updateVoiceButton(false);
  },

  async transcribeAudio(audioBlob) {
    try {
      // Get API key from localStorage or prompt
      let OPENAI_API_KEY = localStorage.getItem("openai_api_key");

      if (!OPENAI_API_KEY) {
        OPENAI_API_KEY = prompt(
          "Please enter your OpenAI API key:\n\n" +
            "1. Go to https://platform.openai.com/api-keys\n" +
            "2. Create a new API key\n" +
            "3. Paste it here (it will be saved locally)"
        );

        if (!OPENAI_API_KEY) {
          UI.addMessage("❌ API key required for transcription", "error");
          return;
        }

        localStorage.setItem("openai_api_key", OPENAI_API_KEY);
      }

      // Send to Whisper API
      const formData = new FormData();
      formData.append("file", audioBlob, "recording.webm");
      formData.append("model", "whisper-1");

      const response = await fetch(
        "https://api.openai.com/v1/audio/transcriptions",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${OPENAI_API_KEY}`,
          },
          body: formData,
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem("openai_api_key");
          UI.addMessage("❌ Invalid API key. Please try again.", "error");
          return;
        }
        throw new Error(`Whisper API error: ${response.status}`);
      }

      const data = await response.json();
      const transcript = data.text;

      if (transcript) {
        // Insert transcript into textarea
        const textarea = document.getElementById("operator-input");
        if (textarea.value && !textarea.value.endsWith(" ")) {
          textarea.value += " ";
        }
        textarea.value += transcript;
        textarea.focus();

        UI.addMessage(`✅ Transcribed: "${transcript}"`, "system");
      } else {
        UI.addMessage("⚠️ No speech detected. Please try again.", "system");
      }
    } catch (error) {
      console.error("Transcription error:", error);
      UI.addMessage(`❌ Transcription failed: ${error.message}`, "error");
    }
  },

  updateVoiceButton(isActive) {
    const voiceBtn = document.getElementById("voice-btn");
    if (!voiceBtn) return;

    if (isActive) {
      voiceBtn.classList.add("active");
      voiceBtn.textContent = "⏺️ Recording...";
    } else {
      voiceBtn.classList.remove("active");
      voiceBtn.textContent = "🎤 Voice";
    }
  },
};
