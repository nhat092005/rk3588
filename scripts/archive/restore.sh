#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

print_help() {
    cat << 'EOF'
Usage:
  ./scripts/archive/restore.sh [OPTIONS] [ARCHIVE_ZIP]

Description:
  Restore untracked model weights and datasets from a zip archive.
  Extracts files directly into the repository root with overwrite enabled.

Options:
  -h, --help             Show this help message.

Default Archive:
  The most recent .zip file in tmp/_archives/ if no archive is provided.
EOF
}

ARCHIVE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            print_help
            exit 0
            ;;
        -*)
            echo "Error: Unknown option $1" >&2
            print_help
            exit 1
            ;;
        *)
            if [[ -z "$ARCHIVE" ]]; then
                ARCHIVE="$1"
            else
                echo "Error: Unexpected argument $1" >&2
                print_help
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$ARCHIVE" ]]; then
    ARCHIVE="$(ls -t tmp/_archives/*.zip 2>/dev/null | head -n 1 || true)"
    if [[ -z "$ARCHIVE" || ! -f "$ARCHIVE" ]]; then
        echo "Error: No archive specified and no .zip file found in tmp/_archives/" >&2
        echo "Usage: ./scripts/archive/restore.sh [path/to/archive.zip]" >&2
        exit 1
    fi
    echo "No archive specified. Using latest archive: $ARCHIVE"
fi

if [[ ! -f "$ARCHIVE" ]]; then
    echo "Error: Archive file not found: $ARCHIVE" >&2
    exit 1
fi

echo "Restoring from archive: $ARCHIVE"
echo "Target directory: $REPO_ROOT"

unzip -o -q "$ARCHIVE" -d "$REPO_ROOT"

echo "Restore completed successfully."
