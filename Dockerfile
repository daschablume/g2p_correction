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
    ca-certificates \
    curl \
    git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a working directory
WORKDIR /g2p_correction

# Copy the application code to the working directory
COPY . /g2p_correction

# Install Miniconda
ENV PATH /opt/conda/bin:$PATH
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda && \
    rm Miniconda3-latest-Linux-x86_64.sh

# Install the dependencies and activate the environment
COPY environment.yml /g2p_correction/environment.yml
RUN conda env create -f /g2p_correction/environment.yml

# Activate conda and set default environment
RUN echo "source activate g2p_env" >> ~/.bashrc
ENV PATH /opt/conda/envs/g2p_env/bin:$PATH

# Install espeak through sudo
RUN apt-get update && apt-get install -y espeak && \
    rm -rf /var/lib/apt/lists/*

# Copy models for Matcha
COPY matcha-models/ /root/.local/share/matcha_tts/

# Set environment variables for Flask
ENV FLASK_APP=/g2p_correction/g2p_correction.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# Expose the port that the app runs on
EXPOSE 5000

# Set the entry point to run the Flask app
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "g2p_env", "flask", "run", "--host=0.0.0.0"]
