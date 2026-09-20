#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

DATASET="${DATASET:-}"
OUT=""

print_help() {
    cat << 'EOF'
Usage:
  ./scripts/archive/archive.sh [OPTIONS] [OUTPUT_ZIP]

Description:
  Archive untracked model weights and datasets into a zip file.
  Preserves relative directory structures and symlinks.

Options:
  -d, --dataset <name>   Archive only a specific dataset (e.g. sh17, sfchd, css)
                         and its corresponding run weights.
  -h, --help             Show this help message.

Environment Variables:
  DATASET                Optional dataset filter (alternative to -d/--dataset).

Default Output:
  tmp/_archives/<YYYY-MM-DD>[_<dataset>].zip
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -d|--dataset)
            DATASET="$2"
            shift 2
            ;;
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
            if [[ -z "$OUT" ]]; then
                OUT="$1"
            else
                echo "Error: Unexpected argument $1" >&2
                print_help
                exit 1
            fi
            shift
            ;;
    esac
done

DATE_TAG="$(date +%Y-%m-%d)"
if [[ -z "$OUT" ]]; then
    if [[ -n "$DATASET" ]]; then
        OUT="tmp/_archives/${DATE_TAG}_${DATASET}.zip"
    else
        OUT="tmp/_archives/${DATE_TAG}.zip"
    fi
fi

mkdir -p "$(dirname "$OUT")"

TARGETS=()

if [[ -n "$DATASET" ]]; then
    echo "=== Scanning for dataset: $DATASET ==="
    if [[ -d "data/$DATASET" ]]; then
        TARGETS+=("data/$DATASET")
    else
        echo "Warning: Directory data/$DATASET not found." >&2
    fi

    if [[ -d "ai/automation/runs" ]]; then
        for run_dir in ai/automation/runs/*; do
            [[ -d "$run_dir" ]] || continue
            matched=0
            if [[ -f "$run_dir/config.yaml" ]] && grep -Eq "^dataset:\s*['\"]?${DATASET}['\"]?\s*$" "$run_dir/config.yaml"; then
                matched=1
            elif [[ "$(basename "$run_dir")" =~ _${DATASET}(_|$) ]]; then
                matched=1
            fi

            if [[ $matched -eq 1 && -d "$run_dir/weights" ]]; then
                TARGETS+=("$run_dir/weights")
            fi
        done
    fi
else
    echo "=== Scanning all datasets and model weights ==="
    if [[ -d "data" ]]; then
        for d in data/*; do
            [[ -d "$d" ]] || continue
            if [[ "$(basename "$d")" != "_archives" ]]; then
                TARGETS+=("$d")
            fi
        done
    fi

    if [[ -d "ai/automation/runs" ]]; then
        for w in ai/automation/runs/*/weights; do
            [[ -d "$w" ]] || continue
            TARGETS+=("$w")
        done
    fi
fi

if [[ ${#TARGETS[@]} -eq 0 ]]; then
    echo "Error: No matching data or weights found to archive." >&2
    exit 1
fi

echo "Targets to archive:"
for t in "${TARGETS[@]}"; do
    echo "  - $t"
done

echo ""
echo "Creating archive: $OUT"
rm -f "$OUT"

zip -r -y -q "$OUT" "${TARGETS[@]}" \
    -x "data/_archives/*" \
    -x "tmp/*" \
    -x "*/__pycache__/*" \
    -x "*.pyc" \
    -x ".venv/*"

ARCHIVE_SIZE="$(du -h "$OUT" | cut -f1)"
echo "Archive completed successfully: $OUT ($ARCHIVE_SIZE)"
