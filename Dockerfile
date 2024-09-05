FROM ubuntu:22.04

# Install necessary system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    bzip2 \
    build-essential \
    libffi-dev \
    libssl-dev \
    python3-dev \
    python3-pip \
    ca-certificates \
    curl \
    git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a working directory
WORKDIR /g2p_correction

# Copy the application code to the working directory
COPY . /g2p_correction

# Install Python dependencies using pip
RUN pip install --no-cache-dir -r /g2p_correction/requirements.txt

# Install espeak
RUN apt-get update && apt-get install -y espeak && \
    rm -rf /var/lib/apt/lists/*

# Set up the environment variable for matcha storage
ENV USER_DATA_DIR=/root/.local/share/matcha_tts

# Create the directory structure for matcha models
RUN mkdir -p $USER_DATA_DIR

# Download models directly into the container
RUN wget -O $USER_DATA_DIR/matcha_ljspeech.ckpt https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/matcha_ljspeech.ckpt && \
    wget -O $USER_DATA_DIR/hifigan_T2_v1 https://github.com/shivammehta25/Matcha-TTS-checkpoints/releases/download/v1.0/generator_v1

# Set environment variables for Flask
ENV FLASK_APP=/g2p_correction/g2p_correction.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Expose the port that the app runs on
EXPOSE 5000

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

# Set the entrypoint to the script
ENTRYPOINT ["/entrypoint.sh"]

# Set the entry point to run the Flask app
ENTRYPOINT ["flask", "run", "--host=0.0.0.0"]
