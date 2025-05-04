<template>
  <div id="app">
    <h1>PDF to Podcast Generator</h1>

    <p>Upload a PDF file to generate a podcast audio file.</p>

    <FileUploader @file-selected="onFileSelected" />

    <br />

    <button @click="generatePodcast" :disabled="isProcessing">Generate Podcast</button>

    <h2>Status</h2>
    <StatusDisplay :message="statusMessage" :statusClass="statusClass" />

    <h2>Result</h2>
    <DownloadLink :link="downloadLink" />
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
      statusMessage: "Upload a PDF and click 'Generate Podcast' to begin.",
      statusClass: "",
      downloadLink: "",
      isProcessing: false,
      API_BASE_URL: "https://tts-tudengiprojekt2025.onrender.com", // Use local backend for development, Render backend for production
    };
  },
  methods: {
    onFileSelected(file) {
      this.selectedFile = file;
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
body {
  font-family: sans-serif;
  padding: 2em;
  line-height: 1.6;
}
</style>
