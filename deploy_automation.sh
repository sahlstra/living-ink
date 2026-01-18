#!/bin/bash
set -e

SOURCE_DIR="$(pwd)"
TARGET_DIR="$HOME/remarkable-mcp-automation"
PLIST_NAME="com.aaron.remarkable.sync.plist"

echo "=== Deploying Automation to $TARGET_DIR ==="

# 1. Create Target Directory
if [ -d "$TARGET_DIR" ]; then
    echo "Backing up existing automation folder..."
    mv "$TARGET_DIR" "${TARGET_DIR}_backup_$(date +%s)"
fi
mkdir -p "$TARGET_DIR"

# 2. Copy Files (exclusion list avoids copying massive caches or git history)
echo "Copying project files..."
rsync -av \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude 'logs/*' \
    --exclude 'remarkable_pngs_for_vision/*' \
    --exclude 'output/*' \
    "$SOURCE_DIR/" "$TARGET_DIR/"

# 3. Patch the plist in the TARGET directory
echo "Configuring permissions bypass..."
PLIST_PATH="$TARGET_DIR/$PLIST_NAME"

# Replace the source path with the target path in the plist
sed -i '' "s|$SOURCE_DIR|$TARGET_DIR|g" "$PLIST_PATH"

# Ensure WorkingDirectory is the target dir
# (We overwrite the 'Home' hack because now we are in a safe directory)
sed -i '' "s|<string>/Users/aaronmacbaron</string>|<string>$TARGET_DIR</string>|g" "$PLIST_PATH"

# 4. Initialize Environment
echo "Initializing Python environment in target..."
cd "$TARGET_DIR"
# Force uv to setup the environment
/opt/homebrew/bin/uv sync

# 5. Install the LaunchAgent
echo "Registering background job..."
./install_automation.sh

echo "=== Deployment Complete ==="
echo "The automation is now running from: $TARGET_DIR"
echo "You can continue developing in your Documents folder, but proper automation"
echo "will run from the copy in your Home folder to avoid macOS permission errors."
