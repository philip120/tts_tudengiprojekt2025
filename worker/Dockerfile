# worker/Dockerfile

# 1. Base Image (Choose one matching your PyTorch CUDA requirement)
# Example for CUDA 12.1 - check compatibility with Runpod base images if possible
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# Prevent prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# 2. Install Python, pip, and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Make python3.10 the default python
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# 3. Set up Environment
WORKDIR /app
COPY worker/requirements_worker.txt .

# 4. Install Python Packages
# Explicitly install numpy first to satisfy TTS dependency, then others
RUN pip install --no-cache-dir numpy==1.22.0
# Install PyTorch matching the base image CUDA version
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
# Install remaining requirements
RUN pip install --no-cache-dir -r requirements_worker.txt

# 5. Copy Application Code
COPY worker/app.py .
COPY src/ /app/src/

# 6. Copy Model Files
COPY model/ /app/model/

# 7. Copy Reference Files 
COPY reference/ /app/reference/

# 8. Set Environment Variables (Optional but good practice)
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV PORT=8000

# Expose the port the app runs on
EXPOSE 8000

# 9. Define Entrypoint/Command
CMD ["python", "app.py"] 
# CMD ["echo", ">>> Container test command executed successfully <<<"] 
# CMD ["sh", "-c", "echo '>>> Container test output START <<<' && sleep 10 && echo '>>> Container test output END <<<'"] 