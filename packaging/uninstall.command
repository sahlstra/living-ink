#!/bin/bash

APP_DIR="/Applications/Living Ink"
PLIST="com.aaron.livingink.plist"

echo "Stopping service..."
launchctl bootout gui/$(id -u) /Library/LaunchAgents/$PLIST 2>/dev/null || true

echo "Removing LaunchAgent..."
rm -f ~/Library/LaunchAgents/$PLIST
rm -f /Library/LaunchAgents/$PLIST

echo "Removing $APP_DIR..."
rm -rf "$APP_DIR"

echo "Removing Desktop Shortcut..."
rm -f ~/Desktop/"Living Ink Sync.command"
# Handle potential renamed shortcuts or varying user locations if run via sudo
if [ -n "$SUDO_USER" ]; then
    rm -f "/Users/$SUDO_USER/Desktop/Living Ink Sync.command"
fi

echo "Done. Living Ink has been uninstalled."

