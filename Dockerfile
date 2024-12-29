# Use Raspberry Pi compatible base image
FROM arm32v7/python:3.9-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Create radio user and set up directories
RUN useradd -m -r radio && \
    # In Docker, we'll simulate the groups if they don't exist
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

# Make install script executable
RUN chmod +x install/install.sh

# Run installation script
RUN ./install/install.sh

# Copy remaining application files
COPY --chown=radio:radio . .

# Switch to radio user
USER radio

# Expose ports
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/home/radio/radio/manage_radio.sh"]
CMD ["start"] 