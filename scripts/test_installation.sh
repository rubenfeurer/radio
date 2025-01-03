#!/bin/bash
set -e

echo "Testing installation..."

# Run installation with test mode
TEST_MODE=1 bash install/install.sh

echo "Verifying installation..."

# 1. Check user and groups
if ! id radio >/dev/null 2>&1; then
    echo "❌ Radio user not created"
    exit 1
fi

# 2. Check directories
DIRS_TO_CHECK=(
    "/home/radio/radio/src"
    "/home/radio/radio/config"
    "/home/radio/radio/web"
    "/home/radio/radio/sounds"
    "/home/radio/radio/data"
    "/home/radio/radio/logs"
    "/home/radio/radio/install"
    "/home/radio/radio/venv"
    "/tmp/mpv-socket"
)

for dir in "${DIRS_TO_CHECK[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "❌ Directory not found: $dir"
        exit 1
    fi
done

# 3. Check critical files
FILES_TO_CHECK=(
    "/home/radio/radio/manage_radio.sh"
    "/home/radio/radio/config/config.py"
    "/home/radio/radio/install/requirements.txt"
    "/home/radio/radio/install/system-requirements.txt"
)

for file in "${FILES_TO_CHECK[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ File not found: $file"
        exit 1
    fi
done

# 4. Check permissions
if ! groups radio | grep -q "audio"; then
    echo "❌ Radio user not in audio group"
    exit 1
fi

# 5. Check Python venv
if [ ! -f "/home/radio/radio/venv/bin/activate" ]; then
    echo "❌ Python virtual environment not set up"
    exit 1
fi

# 6. Check MPV socket directory permissions
if [ ! -w "/tmp/mpv-socket" ]; then
    echo "❌ MPV socket directory not writable"
    exit 1
fi

# 7. Check service configuration (skip in Docker)
if [ ! -f "/.dockerenv" ]; then
    if ! systemctl is-active --quiet NetworkManager; then
        echo "❌ NetworkManager service not running"
        exit 1
    fi
fi

echo "✅ All checks passed!"
