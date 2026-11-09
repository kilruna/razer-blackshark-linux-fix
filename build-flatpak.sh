#!/usr/bin/bash
set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly APP_ID="com.github.kilruna.razer-blackshark-linux-fix"
readonly MANIFEST="$SCRIPT_DIR/$APP_ID.yml"
readonly BUILD_DIR="$SCRIPT_DIR/_build"

if ! command -v flatpak >/dev/null 2>&1; then
    echo "ERROR: flatpak is not installed." >&2
    exit 1
fi

if ! flatpak remotes | awk '{print $1}' | grep -qx flathub; then
    echo "Adding the flathub remote..."
    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
fi

if ! command -v flatpak-builder >/dev/null 2>&1 &&
   [[ ! -x "$HOME/.local/bin/flatpak-builder" ]] &&
   ! flatpak info org.flatpak.Builder >/dev/null 2>&1; then
    echo "Installing flatpak-builder from flathub (one-time)..."
    flatpak install --user --noninteractive flathub org.flatpak.Builder
fi

if command -v flatpak-builder >/dev/null 2>&1; then
    FLATPAK_BUILDER=(flatpak-builder)
elif [[ -x "$HOME/.local/bin/flatpak-builder" ]]; then
    FLATPAK_BUILDER=("$HOME/.local/bin/flatpak-builder")
else
    FLATPAK_BUILDER=(flatpak run --command=flatpak-builder org.flatpak.Builder)
fi

echo "Building and installing $APP_ID..."
"${FLATPAK_BUILDER[@]}" --user --install --force-clean "$BUILD_DIR" "$MANIFEST"

echo
echo "Installed. Start it from the application menu (Razer BlackShark Linux Fix) or with:"
echo "  flatpak run $APP_ID"
