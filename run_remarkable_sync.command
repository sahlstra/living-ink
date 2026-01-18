#!/bin/zsh

# Navigate to the directory where this script resides
cd "$(dirname "$0")"

# Print start message
echo "Starting reMarkable to Apple Notes Sync..."
echo "-----------------------------------------"

# Execute the main sync script
./run_remarkable_to_apple_notes.sh

# Keep window open to show logs/status
echo ""
echo "-----------------------------------------"
echo "Process complete. Press any key to close this window."
read -n 1
