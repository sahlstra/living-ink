#!/bin/bash
set -e

APP_ROOT="packaging/payload/Applications/Living Ink"
SCRIPTS="packaging/scripts"

# Clean payload first to avoid stale files
rm -rf packaging/payload

echo "Assembling Payload..."

# Create dirs
mkdir -p "$APP_ROOT/bin"
mkdir -p "$APP_ROOT/docs"
mkdir -p "$APP_ROOT/config"
mkdir -p "$APP_ROOT/logs"
mkdir -p "$APP_ROOT/remarkable_pngs_white"
mkdir -p "$APP_ROOT/remarkable_pngs_for_vision"
mkdir -p "$APP_ROOT/output"

# Copy Binary
cp dist/living-ink "$APP_ROOT/"

# Create friendly launcher
cat > "$APP_ROOT/Run Manual Sync.command" <<EOF
#!/bin/bash
cd "\$(dirname "\$0")"
./living-ink
echo
echo "---------------------------------------------------"
echo "Process completed. You can close this window."
EOF
chmod +x "$APP_ROOT/Run Manual Sync.command"

# Copy Config Template
cp config.yml.example "$APP_ROOT/config/config.yml"

# Copy License
cp LICENSE "$APP_ROOT/"

# Copy Docs
cp docs/SETUP_GUIDE.md "$APP_ROOT/docs/"
cp docs/USER_MANUAL.md "$APP_ROOT/docs/"

# Copy Service Installer and Plist
cp packaging/install_service.command "$APP_ROOT/"
cp packaging/uninstall.command "$APP_ROOT/"
cp packaging/com.aaron.livingink.plist "$APP_ROOT/"

# Create postinstall script
cat > "$SCRIPTS/postinstall" <<EOF
#!/bin/bash

APP_DIR="/Applications/Living Ink"
APP_PLIST="com.aaron.livingink.plist"

# Disable old launch agent if present (handle both old and new names during transition)
if launchctl print gui/"$UID"/com.aaron.remarkable.sync >/dev/null 2>&1; then
    launchctl bootout gui/"$UID" /Library/LaunchAgents/com.aaron.remarkable.sync.plist 2>/dev/null || true
fi
if launchctl print gui/"$UID"/com.aaron.livingink >/dev/null 2>&1; then
    launchctl bootout gui/"$UID" /Library/LaunchAgents/"$APP_PLIST" 2>/dev/null || true
fi
rm -f /Library/LaunchAgents/com.aaron.remarkable.sync.plist
rm -f /Library/LaunchAgents/"$APP_PLIST"

# Copy new plist
cp "\$APP_DIR/\$APP_PLIST" /Library/LaunchAgents/

# Fix ownership
chown root:wheel /Library/LaunchAgents/"$APP_PLIST"
chmod 644 /Library/LaunchAgents/"$APP_PLIST"

# Load the service
if [ -n "\$UID" ]; then
    launchctl bootstrap gui/"$UID" /Library/LaunchAgents/"$APP_PLIST"
fi

# Get the logged-in user (since installer runs as root)
LOGIN_USER=\$(scutil <<< "show State:/Users/ConsoleUser" | awk '/Name :/ && ! /loginwindow/ { print \$3 }')

# Fix permissions so the user can run it and write logs
chmod -R 777 "\$APP_DIR"

# Wait a moment for the filesystem to settle
sleep 1

# Open as the logged-in user
if [ -n "\$LOGIN_USER" ]; then
    # Create Desktop Shortcut
    USER_DESKTOP="/Users/\$LOGIN_USER/Desktop"
    if [ -d "\$USER_DESKTOP" ]; then
         TARGET_LINK="\$USER_DESKTOP/Living Ink Sync.command"
         ln -sf "\$APP_DIR/Run Manual Sync.command" "\$TARGET_LINK"
         chown "\$LOGIN_USER" "\$TARGET_LINK"
    fi

    sudo -u "\$LOGIN_USER" open "\$APP_DIR/docs/SETUP_GUIDE.md"
    sudo -u "\$LOGIN_USER" open "\$APP_DIR"
fi

exit 0
EOF

chmod +x "$SCRIPTS/postinstall"

echo "Payload Assembled."

# Create Resources for the Installer (Welcome Screen)
rm -rf packaging/resources
mkdir -p packaging/resources

cat > packaging/resources/Welcome.html <<EOF
<html>
<body>
    <h2>Welcome to Living Ink</h2>
    <p><b>Living Ink</b> is a powerful utility that seamlessly syncs your <br>
    reMarkable notebooks directly to Apple Notes.</p>
    
    <p>It preserves your handwriting as images while adding searchable text (OCR) <br>
    to the body of the note, giving you the best of both worlds.</p>
    
    <p><b>Features:</b></p>
    <ul>
        <li>Automatic background syncing</li>
        <li>Converts handwriting to searchable text</li>
        <li>Organizes notebooks into folders</li>
        <li>Filters out PDFs and EPUBs</li>
    </ul>
    
    <p><i>Created by <b>Aaron Sahlstrom</b>.</i></p>
</body>
</html>
EOF

echo "Building Component Package..."
pkgbuild --root packaging/payload \
         --identifier com.aaron.livingink \
         --version 1.2.0 \
         --scripts packaging/scripts \
         --install-location / \
         living-ink-component.pkg

echo "Building Product Archive..."
productbuild --distribution packaging/distribution.xml \
             --resources packaging/resources \
             --package-path . \
             LivingInkInstaller.pkg 2>/dev/null || \
productbuild --synthesize --package living-ink-component.pkg packaging/distribution.xml

# Insert title into generated distribution.xml to ensure it shows up nicel
sed -i '' 's/<installer-gui-script minSpecVersion="1">/<installer-gui-script minSpecVersion="1">\n    <title>Living Ink<\/title>/' packaging/distribution.xml

# Build the final product
productbuild --distribution packaging/distribution.xml \
             --resources packaging/resources \
             --package-path . \
             LivingInkInstaller.pkg

# Cleanup
rm living-ink-component.pkg
rm packaging/distribution.xml
rm -rf packaging/resources

echo "✅ Installer created: LivingInkInstaller.pkg"
