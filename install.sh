#!/usr/bin/bash
set -Eeuo pipefail

readonly SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SOURCE_FILE="$SOURCE_DIR/razer-blackshark-fix"
readonly INSTALL_DIR="/usr/local/sbin"
readonly INSTALL_FILE="$INSTALL_DIR/razer-blackshark-fix"

if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: Run this installer with sudo." >&2
    exit 1
fi

for command_name in dirname install; do
    command -v "$command_name" >/dev/null 2>&1 || {
        printf 'ERROR: Required command not found: %s\n' "$command_name" >&2
        exit 1
    }
done

if [[ ! -f "$SOURCE_FILE" ]]; then
    echo "ERROR: Missing source script: $SOURCE_FILE" >&2
    exit 1
fi

install -d -m 0755 "$INSTALL_DIR"
install -m 0755 "$SOURCE_FILE" "$INSTALL_FILE"
printf 'Installed %s\n' "$INSTALL_FILE"
