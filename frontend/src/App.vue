<template>
  <div id="app">
    <button
      id="info-button"
      @click="toggleInfoBox"
    >
      <img src="/info.png" alt="Info" class="info-icon" />
    </button>

    <div v-if="showInfoBox" id="info-box-overlay">
      <div id="info-box">
        <h2>About This Project</h2>
        <p>This project was developed by Philip Paškov and Oskar Männik for the University of Tartu Student Project Contest 2025. Its primary goal is to offer students a new way of learning by allowing them to upload their lecture slides (PDF format) and convert them into podcasts for a more enjoyable studying process.</p>
        <p>The system operates in two main stages: first, a textual script is generated from the slides using Gemini. Then, leveraging the XTTS-v2 model, we apply voice cloning to produce a podcast narrated in our own voices.</p>
        <button @click="toggleInfoBox">Close</button>
      </div>
    </div>

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
        <div v-if="isProcessing" class="loading-animation">
          <div class="spinner">
            <div></div>
            <div></div>
            <div></div>
            <div></div>
          </div>
        </div>
      </section>

      <section v-if="downloadLink" class="result-section">
        <h2>Result</h2>
        <DownloadLink :link="downloadLink" />
      </section>
    </main>

    <img src="/ut-logo.svg" alt="Logo" id="top-left-logo">

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
      showHostsSection: false,
      API_BASE_URL: "https://tts-tudengiprojekt2025.onrender.com", // Ensure no trailing slash
      // Placeholder host data (assuming images are in /public/)
      host1ImageUrl: "/oskar.jpg",
      host1Text: "Oskar is preparing the script...",
      host1Info: "Meet Oskar, the analytical mind behind the podcast. He focuses on dissecting complex topics from the PDF, ensuring clarity and structure in the generated script.",
      host2ImageUrl: "/philip2.jpg",
      host2Text: "Philip is warming up his voice...",
      host2Info: "And here's Philip, the voice of the podcast. He brings the generated script to life with engaging delivery and clear narration, making complex ideas accessible.",
      showInfoBox: false,
    };
  },
  mounted() {
    this.adjustLogoPosition();
    window.addEventListener('resize', this.adjustLogoPosition);
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.adjustLogoPosition);
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

      // Call adjustLogoPosition when the button is pressed
      this.adjustLogoPosition();

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
    adjustLogoPosition() {
      const logo = document.getElementById("top-left-logo");
      const header = document.querySelector(".superbowl-header");

      if (window.innerWidth <= 768 && logo && header) {
        // Mobile view: Move logo above the headline
        header.style.display = "block";
        header.style.alignItems = "center";
        logo.style.position = "relative";
        logo.style.margin = "0 auto 10px auto";
        header.insertBefore(logo, header.firstChild);
      } else if (this.showHostsSection && logo && header) {
        // Desktop view with hosts section: Move logo to the left of the headline
        header.style.display = "flex";
        header.style.alignItems = "center";
        logo.style.position = "relative";
        logo.style.marginRight = "10px";
        header.insertBefore(logo, header.firstChild);
      } else if (logo && header) {
        // Default desktop view: Keep logo fixed in the top-left corner
        header.style.display = "block";
        logo.style.position = "fixed";
        logo.style.margin = "0";
      }
    },
    toggleInfoBox() {
      this.showInfoBox = !this.showInfoBox;
    },
  },
};
</script>

<style>
@import "./style.css";
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;700&display=swap');

/* Styles for Background Video */
#background-video {
  pointer-events: none; /* Disable user interaction */
  user-select: none; /* Prevent text selection or interaction */
  touch-action: none;
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
  text-align: center;
  padding: 30px;
  background: linear-gradient(90deg, #1f1f1f, #333333);
  color: #ffffff;
  font-size: 2.5rem;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 2px;
  text-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
  border-radius: 10px;
}
.superbowl-header h1 {
  margin: 0 auto;
}
@media (max-width: 768px) {
  .superbowl-header {
    display: block;
    text-align: center;
    padding: 15px;
  }
  .superbowl-header h1 {
    margin: 0 auto;
  }
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

/* Updated the generate-button color to light grey */
.generate-button {
  background-color: #d3d3d3; /* Light grey background */
  color: #000000; /* Black text for contrast */
  border: 1px solid #a9a9a9; /* Darker grey border for definition */
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
  outline: none;
  transition: background-color 0.3s, transform 0.2s;
}

.generate-button:hover {
  background-color: #c0c0c0; /* Slightly darker grey for hover effect */
  transform: scale(1.05);
  outline: none;
  box-shadow: none;
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
    margin-right: 6px; /* Decreased space between logo and h1 when sideways */
}

@media (max-width: 768px) {
  .superbowl-header {
    font-size: 1.5rem;
    padding: 15px;
  }

  .upload-section, .hosts-section, .status-section, .result-section {
    padding: 10px;
    margin-bottom: 10px;
  }

  .hosts-container {
    flex-direction: column;
    gap: 10px;
  }

  .host-column img {
    width: 100px;
    height: 100px;
  }

  .generate-button {
    font-size: 0.9rem;
    padding: 10px 20px;
  }

  #background-video {
    min-width: 100%;
    min-height: auto;
  }

  #top-left-logo {
    width: 150px;
    margin: 0 auto 10px auto; /* Keep margin for stacked (mobile) view */
  }
}

.loading-animation {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 20px;
}

.spinner {
  display: inline-block;
  position: relative;
  width: 80px;
  height: 80px;
}

.spinner div {
  display: inline-block;
  position: absolute;
  left: 8px;
  width: 16px;
  background: #fff;
  animation: spinner-animation 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
}

.spinner div:nth-child(1) {
  left: 8px;
  animation-delay: -0.24s;
}

.spinner div:nth-child(2) {
  left: 32px;
  animation-delay: -0.12s;
}

.spinner div:nth-child(3) {
  left: 56px;
  animation-delay: 0;
}

@keyframes spinner-animation {
  0% {
    top: 8px;
    height: 64px;
  }
  50%, 100% {
    top: 24px;
    height: 32px;
  }
}

#info-button {
  position: fixed;
  top: 20px; /* Keep it further down */
  right: 10px; /* Ensure consistent distance from the right side */
  background-color: #d3d3d3;
  color: #000000;
  border: 1px solid #a9a9a9;
  border-radius: 50%; /* Make it circular */
  width: 70px; /* Increase size for a bigger button */
  height: 70px; /* Match width for a perfect circle */
  font-size: 1.5rem; /* Increase font size for better visibility */
  cursor: pointer;
  z-index: 1100;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 10px; /* Add consistent margin */
  transition: background-color 0.3s, transform 0.2s;
  outline: none;
}

#info-button:hover {
  background-color: #c0c0c0; /* Slightly darker grey for hover effect */
  transform: scale(1.05);
  outline: none;
  box-shadow: none;
}

.info-icon {
  width: 30px;
  height: 30px;
}

#info-box-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1100;
}

#info-box {
  background-color: #e1e9ea; /* Softer grey for a cleaner look */
  color: #333; /* Darker text for better readability */
  padding: 30px; /* Increased padding for a spacious layout */
  border-radius: 15px; /* Rounded corners for a modern look */
  width: 90%;
  max-width: 600px; /* Slightly wider for better content display */
  text-align: left; /* Align text to the left for better readability */
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2); /* Enhanced shadow for depth */
  font-family: 'Arial', sans-serif; /* Clean font for better aesthetics */
  line-height: 1.6; /* Improved line spacing for readability */
}

#info-box h2 {
  margin-top: 0;
  font-size: 1.8rem; /* Larger font size for the title */
  color: #222; /* Slightly darker title color */
  text-align: center; /* Center the title */
  margin-bottom: 20px; /* Add spacing below the title */
}

#info-box p {
  margin-bottom: 15px; /* Add spacing between paragraphs */
}

#info-box button {
  margin-top: 20px;
  padding: 12px 24px;
  background-color: #d3d3d3;
  color: #000000;
  border: none;
  border-radius: 8px;
  outline: none;
  cursor: pointer;
  transition: background-color 0.3s, transform 0.2s;

  background-color: #cccccc; /* Light grey background */
  color: #000000; /* Black text for contrast */
  border: 1px solid #a9a9a9; /* Darker grey border for definition */
padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
  transition: background-color 0.3s, transform 0.2s;
}

#info-box button:hover {
  background-color: #c0c0c0;
}

@media (max-width: 768px) {
  #info-button {
    width: 50px; /* Reduce size for smaller screens */
    height: 50px; /* Match width for a perfect circle */
    font-size: 1.2rem; /* Adjust font size for better fit */
    top: 30px; /* Move it slightly further down */
    right: 15px; /* Adjust position to avoid overlapping */
  }
}
</style>
