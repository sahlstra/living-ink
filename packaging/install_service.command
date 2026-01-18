#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST="com.aaron.remarkable.sync.plist"
DEST="$HOME/Library/LaunchAgents/$PLIST"

echo "Installing Sync Service..."

# Copy Plist
cp "$DIR/$PLIST" "$DEST"

# Unload old if exists
launchctl unload "$DEST" 2>/dev/null

# Load new
launchctl load "$DEST"

echo "✅ Service Installed. It will check for notes every hour."
