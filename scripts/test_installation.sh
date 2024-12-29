#!/bin/bash
set -e

echo "Testing installation..."

# Run installation
bash install/install.sh

# Verify key components
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
    "/etc/systemd/system/radio.service"
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

echo "✅ All checks passed!" 