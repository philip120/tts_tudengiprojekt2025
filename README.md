# TTS Podcast Generator

This project was developed by Philip Paškov and Oskar Männik for the University of Tartu Student Project Contest 2025. The primary goal is to provide students with an innovative way to study by converting their lecture slides (PDF format) into engaging podcasts.

## Overview
The TTS Podcast Generator operates in two main stages:
1. **Script Generation**: Using Gemini, the system processes uploaded PDFs to generate a structured textual script.
2. **Voice Cloning and Podcast Creation**: Leveraging the XTTS-v2 model, the script is transformed into a podcast narrated in the voices of the authors, Philip and Oskar.

## Features
- **PDF to Podcast**: Converts PDFs (e.g. lecture slides) into audio content for easier studying.
- **Voice Cloning**: Realistic narration using cloned voices of the authors.
- **Automated Workflow**: End-to-end automation from script generation to podcast creation.

## Technologies
- **Frontend**: Vue 3 and Vite for a modern user interface. Deployed with Vercel.
- **Backend**: FastAPI, Redis, and FFmpeg for processing and audio handling. Deployed with Render.
- **AI Models**: Gemini for script generation and XTTS-v2 for voice synthesis.

## Deployment
The project is live and accessible at [www.tts-ut.ee](https://www.tts-ut.ee).
