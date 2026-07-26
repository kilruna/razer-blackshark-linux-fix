#!/usr/bin/bash
set -Eeuo pipefail

readonly INSTALL_FILE="/usr/local/sbin/razer-blackshark-fix"

if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: Run this uninstaller with sudo." >&2
    exit 1
fi

if ! command -v rm >/dev/null 2>&1; then
    echo "ERROR: Required command not found: rm" >&2
    exit 1
fi

if [[ ! -e "$INSTALL_FILE" ]]; then
    printf 'Nothing to remove; %s is not installed.\n' "$INSTALL_FILE"
    exit 0
fi

rm -- "$INSTALL_FILE"
printf 'Removed %s\n' "$INSTALL_FILE"
