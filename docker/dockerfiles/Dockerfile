# Use Raspberry Pi compatible base image
FROM arm32v7/python:3.9-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install build dependencies first
RUN apt-get update && \
    apt-get install -y \
    git \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    pkg-config \
    curl \
    cargo \
    rustc

# Set Rust version
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH

# Install specific Rust version
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain 1.72.0 && \
    rustup default 1.72.0

# Install pigpio from source
RUN cd /tmp && \
    git clone https://github.com/joan2937/pigpio.git && \
    cd pigpio && \
    make && \
    make install && \
    rm -rf /tmp/pigpio

# Create radio user and set up directories
RUN useradd -m -r radio && \
    (groupadd -r gpio 2>/dev/null || true) && \
    (groupadd -r audio 2>/dev/null || true) && \
    (groupadd -r dialout 2>/dev/null || true) && \
    usermod -a -G audio,gpio,dialout radio && \
    mkdir -p /home/radio/radio/{src,config,web,install,sounds,data,logs} && \
    chown -R radio:radio /home/radio/radio

# Set working directory
WORKDIR /home/radio/radio

# Copy installation files first
COPY --chown=radio:radio install/install.sh install/
COPY --chown=radio:radio install/system-requirements.txt install/
COPY --chown=radio:radio install/requirements.txt install/

# Debug: Show contents and permissions
RUN ls -la install/ && \
    cat install/system-requirements.txt && \
    cat install/requirements.txt && \
    chmod +x install/install.sh

# Install system dependencies
RUN echo "Installing system dependencies..." && \
    apt-get update && \
    # Filter out comments, empty lines, and pigpio, then install packages
    grep -v '^#\|^$\|^pigpio' install/system-requirements.txt | \
    xargs apt-get install -y

# Install Python dependencies
RUN echo "Installing Python dependencies..." && \
    python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install wheel && \
    # Install cryptography with specific version
    pip install --no-cache-dir cryptography==41.0.7 && \
    pip install --no-cache-dir -r install/requirements.txt

# Copy remaining application files
COPY --chown=radio:radio . .

# Clean up
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Switch to radio user
USER radio

# Expose ports
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/home/radio/radio/manage_radio.sh"]
CMD ["start"] 