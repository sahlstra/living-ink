#!/bin/bash
PLIST_NAME="com.aaron.remarkable.sync.plist"
DEST_DIR="$HOME/Library/LaunchAgents"
SOURCE_PLIST="$(pwd)/$PLIST_NAME"

echo "Installing LaunchAgent..."
cp "$SOURCE_PLIST" "$DEST_DIR/"

echo "Loading LaunchAgent..."
launchctl unload "$DEST_DIR/$PLIST_NAME" 2>/dev/null
launchctl load "$DEST_DIR/$PLIST_NAME"

echo "Done! The sync script will now run automatically every hour."
echo "Logs are located at: ./logs/launchd.log"
