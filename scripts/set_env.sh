#!/usr/bin/env sh
# Edit this file to set your Google Vision API key or service account path.
# Recommended: copy the export lines you need into your shell profile (~/.zshenv)
# and do NOT commit secrets into the repository.

# Example: set a simple API key for REST usage
# export GOOGLE_VISION_API_KEY="f16e157862849269a466cc2269e138038755c457"

# Example: set service account JSON path for SDK usage
# export GOOGLE_APPLICATION_CREDENTIALS="$HOME/path/to/service-account.json"

# Optional: remark able token (if you prefer storing here temporarily)
# export REMARKABLE_TOKEN="your_remarkable_token_here"

# To apply locally for this shell session:
#   . scripts/set_env.sh
# or
#   source scripts/set_env.sh

# NOTE: For persistent availability to GUI apps on macOS, place the exports in ~/.zshenv
# or use the macOS Keychain / secrets manager instead of storing plaintext in files.

echo "scripts/set_env.sh loaded - edit as needed then 'source ~/.zshenv' or source this file"
