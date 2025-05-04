#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
echo "Installing Python packages..."
pip install -r backend/requirements.txt

# Install system dependencies (ffmpeg for pydub)
echo "Updating apt and installing ffmpeg..."
apt-get update && apt-get install -y ffmpeg

echo "Build finished!"