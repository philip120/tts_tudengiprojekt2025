<template>
  <div id="app">
    <header class="superbowl-header">
      <h1>PDF to Podcast Generator</h1>
    </header>

    <main>
      <section class="upload-section">
        <h2>Upload Your PDF</h2>
        <p>Drag and drop your PDF file here or click to upload.</p>

        <div class="upload-area" @click="triggerFileInput" @drop.prevent="handleDrop" @dragover.prevent>
          <p>Click or drag PDF file to this area to upload</p>
          <input ref="fileInput" type="file" accept="application/pdf" @change="onFileSelected" />
        </div>

        <p v-if="selectedFile" class="file-name">Selected File: {{ selectedFile.name }}</p>

        <button
          v-if="selectedFile"
          @click="generatePodcast"
          :disabled="isProcessing"
          class="generate-button"
        >
          Generate Podcast
        </button>
      </section>

      <section v-if="statusMessage" class="status-section">
        <h2>Status</h2>
        <StatusDisplay :message="statusMessage" :statusClass="statusClass" />
      </section>

      <section v-if="downloadLink" class="result-section">
        <h2>Result</h2>
        <DownloadLink :link="downloadLink" />
      </section>
    </main>


  </div>
</template>

<script>
import FileUploader from "./components/FileUploader.vue";
import StatusDisplay from "./components/StatusDisplay.vue";
import DownloadLink from "./components/DownloadLink.vue";

export default {
  name: "App",
  components: {
    FileUploader,
    StatusDisplay,
    DownloadLink,
  },
  data() {
    return {
      selectedFile: null,
      statusMessage: "",
      statusClass: "",
      downloadLink: "",
      isProcessing: false,
      API_BASE_URL: "https://tts-tudengiprojekt2025.onrender.com", // Ensure no trailing slash
    };
  },
  methods: {
    onFileSelected(event) {
      this.selectedFile = event.target.files[0];
    },
    handleDrop(event) {
      const files = event.dataTransfer.files;
      if (files.length > 0) {
        this.selectedFile = files[0];
      }
    },
    triggerFileInput() {
      this.$refs.fileInput.click();
    },
    async generatePodcast() {
      if (!this.selectedFile) {
        this.updateStatus("Please select a PDF file first.", "error");
        return;
      }
      if (this.selectedFile.type !== "application/pdf") {
        this.updateStatus("Invalid file type. Please select a PDF.", "error");
        return;
      }

      this.updateStatus("Uploading PDF and starting job...");
      this.downloadLink = "";
      this.isProcessing = true;

      const formData = new FormData();
      formData.append("file", this.selectedFile);

      try {
        const response = await fetch(`${this.API_BASE_URL}/generate-podcast-async/`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        this.updateStatus(`Job started successfully! Job ID: ${data.job_id}. Checking status...`);
        this.pollStatus(data.job_id);
      } catch (error) {
        console.error("Error submitting job:", error);
        this.updateStatus(`Error submitting job: ${error.message}`, "error");
        this.isProcessing = false;
      }
    },
    async pollStatus(jobId) {
      try {
        const response = await fetch(`${this.API_BASE_URL}/job-status/${jobId}`);

        if (!response.ok) {
          throw new Error(`HTTP error checking status! Status: ${response.status}`);
        }

        const data = await response.json();
        this.updateStatus(data.message || `Status: ${data.status}`);

        if (data.status === "COMPLETED") {
          this.updateStatus("Podcast generation complete!", "success");
          this.downloadLink = `${this.API_BASE_URL}/download-result/${jobId}`;
          this.isProcessing = false;
        } else if (data.status === "FAILED") {
          this.updateStatus(`Job failed: ${data.error || "Unknown error"}`, "error");
          this.isProcessing = false;
        } else {
          setTimeout(() => this.pollStatus(jobId), 5000);
        }
      } catch (error) {
        console.error("Error polling status:", error);
        this.updateStatus(`Error checking job status: ${error.message}`, "error");
        this.isProcessing = false;
      }
    },
    updateStatus(message, type = "") {
      this.statusMessage = message;
      this.statusClass = type;
    },
  },
};
</script>

<style>
@import "./style.css";

.superbowl-header {
  background: linear-gradient(90deg, #1f1f1f, #333333);
  padding: 30px;
  text-align: center;
  color: #ffffff;
  font-size: 2.5rem;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 2px;
  text-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.upload-section {
  background-color: #2a2a2a;
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.upload-area {
  border: 2px dashed #444444;
  border-radius: 8px;
  padding: 20px;
  color: #cccccc;
  cursor: pointer;
  transition: background-color 0.3s;
}

.upload-area:hover {
  background-color: #333333;
}

.upload-area input {
  display: none;
}

.file-name {
  margin-top: 10px;
  color: #ffffff;
  font-size: 1rem;
}

.generate-button {
  background-color: #1f6feb;
  color: #ffffff;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
  transition: background-color 0.3s, transform 0.2s;
}

.generate-button:hover {
  background-color: #265dff;
  transform: scale(1.05);
}

.superbowl-footer {
  background: linear-gradient(90deg, #333333, #1f1f1f);
  padding: 20px;
  text-align: center;
  color: #cccccc;
  font-size: 0.9rem;
}
</style>
