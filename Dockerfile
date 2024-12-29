# Use Raspberry Pi compatible base image
FROM arm32v7/python:3.9-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
COPY install/system-requirements.txt /tmp/
RUN apt-get update && \
    xargs -a /tmp/system-requirements.txt apt-get install -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create radio user and set up directories
RUN useradd -m -r radio && \
    usermod -a -G audio,gpio radio && \
    mkdir -p /home/radio/radio/{src,config,web,install,sounds,data,logs} && \
    chown -R radio:radio /home/radio/radio

# Set working directory
WORKDIR /home/radio/radio

# Copy application files
COPY --chown=radio:radio . .

# Install Python dependencies
RUN python -m venv /home/radio/radio/venv && \
    . /home/radio/radio/venv/bin/activate && \
    pip install --no-cache-dir -r install/requirements.txt

# Switch to radio user
USER radio

# Expose ports
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/home/radio/radio/manage_radio.sh"]
CMD ["start"] 