<template>
  <div id="app">
      <!-- Background Video (Always present, controlled by class binding) -->
    <video :class="{ 'video-visible': showHostsSection }" id="background-video" ref="backgroundVideo" loop muted>
      <source src="/pointilism21.mp4" type="video/mp4">
      Your browser does not support the video tag.
    </video>

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

      <!-- NEW SECTION FOR HOSTS -->
      <section v-if="showHostsSection" class="hosts-section">
        <h2>Meet Your Hosts</h2>
        <div class="hosts-container">
          <div class="host-column">
            <img :src="host1ImageUrl" alt="Host 1">
            <p class="host-info">{{ host1Info }}</p>
            <p>{{ host1Text }}</p>
          </div>
          <div class="host-column">
            <img :src="host2ImageUrl" alt="Host 2">
            <p class="host-info">{{ host2Info }}</p>
            <p>{{ host2Text }}</p>
          </div>
        </div>
      </section>
      <!-- END NEW SECTION -->

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
  <img src="/ut-logo.svg" alt="Logo" id="top-left-logo">

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
      showHostsSection: false,
      API_BASE_URL: "https://tts-tudengiprojekt2025.onrender.com", // Ensure no trailing slash
      // Placeholder host data (assuming images are in /public/)
      host1ImageUrl: "/oskar.jpg",
      host1Text: "Oskar is preparing the script...",
      host1Info: "Meet Oskar, the analytical mind behind the podcast. He focuses on dissecting complex topics from the PDF, ensuring clarity and structure in the generated script.",
      host2ImageUrl: "/philip2.jpg",
      host2Text: "Philip is warming up his voice...",
      host2Info: "And here's Philip, the voice of the podcast. He brings the generated script to life with engaging delivery and clear narration, making complex ideas accessible.",
    };
  },
  methods: {
    onFileSelected(event) {
      this.selectedFile = event.target.files[0];
      this.resetStatus();
    },
    handleDrop(event) {
      const files = event.dataTransfer.files;
      if (files.length > 0) {
        this.selectedFile = files[0];
        this.resetStatus();
      }
    },
    triggerFileInput() {
      this.$refs.fileInput.click();
    },
    resetStatus() {
      this.statusMessage = "";
      this.statusClass = "";
      this.downloadLink = "";
      this.isProcessing = false;
      this.showHostsSection = false;
      if (this.$refs.backgroundVideo) {
        this.$refs.backgroundVideo.pause();
        this.$refs.backgroundVideo.currentTime = 0;
      }
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

      this.updateStatus("Generating podcast...");
      this.downloadLink = "";
      this.isProcessing = true;
      this.showHostsSection = true;

      const logo = document.getElementById("top-left-logo");
      const header = document.querySelector(".superbowl-header");
      if (logo && header) {
        header.style.display = "flex";
        header.style.alignItems = "center";
        logo.style.position = "relative";
        logo.style.marginRight = "10px";
        header.insertBefore(logo, header.firstChild);
      }

      // Play background video
      this.$nextTick(() => {
        if (this.$refs.backgroundVideo) {
          this.$refs.backgroundVideo.play().catch(error => {
             // Handle potential play errors (e.g., user interaction needed)
             console.error("Video play failed:", error);
          });
        }
      });

      // Comment out the actual API call and polling logic for now
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
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap');

/* Styles for Background Video */
#background-video {
  position: fixed;
  right: 0;
  bottom: 0;
  min-width: 100%;
  min-height: 100%;
  width: auto;
  height: auto;
  z-index: -100; /* Place it behind everything */
  object-fit: cover; /* Cover the entire area */
  opacity: 0; /* Start hidden */
  transition: opacity 0.5s ease-in-out; /* Add transition */
  /* Optional: Add a dark overlay for better text contrast */
  /* filter: brightness(0.5); */ 
}

/* Class to make the video visible */
#background-video.video-visible {
  opacity: 1;
}

/* Ensure app container allows z-index context and has initial background */
#app {
  position: relative; /* Needed for z-index */
  z-index: 1; /* Keep content above background */
  background-color: #1a1a1a; /* Initial dark background */
  min-height: 100vh; /* Ensure it covers viewport height */
  font-family: 'Montserrat', sans-serif;
}

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
  background-color: rgba(42, 42, 42, 0.8);
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 20px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
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

/* NEW HOST DISPLAY STYLES */
.hosts-section {
  background-color: rgba(42, 42, 42, 0.8);
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 20px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
  text-align: center;
}

.hosts-section h2 {
  margin-bottom: 15px;
  color: #ffffff;
}

.hosts-container {
  display: flex;
  justify-content: space-around; /* Adjust as needed */
  align-items: flex-start; /* Align items at the top */
  gap: 20px; /* Space between columns */
}

.host-column {
  flex: 1; /* Each column takes equal space */
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #cccccc;
}

/* Adjusted size for profile pictures */
.host-column img {
  width: 150px; /* Increased size */
  height: 150px;
  border-radius: 50%; /* Make images circular */
  object-fit: cover; /* Ensure image covers the area */
  margin-bottom: 10px;
  border: 2px solid #444444;
}

.host-info {
  font-size: 0.8rem;
  font-style: italic;
  color: #aaaaaa;
  margin-bottom: 5px;
}

.host-column p {
  font-size: 0.9rem;
}

#top-left-logo {
    position: fixed; /* Ensures it stays in the top-left corner even when scrolling */
    top: 0;
    left: 0;
    width: 200px; /* Adjusted size for better visibility */
    height: auto;
    z-index: 1000; /* Ensures it stays above other elements */
    margin: 0; /* Removes any default margin */
    padding: 0; /* Removes any default padding */
}

</style>
