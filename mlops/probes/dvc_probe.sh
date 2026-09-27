#!/usr/bin/env bash
# DVC probe: версия эфемерно через uv run --with dvc. uv.lock не трогаем.
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "=== DVC probe ==="
echo "uv: $(uv --version)"
echo
echo "--- version ---"
uv run --with dvc python -c "import dvc; print('dvc', dvc.__version__)"
echo
echo "--- dvc hardlink support ---"
uv run --with dvc dvc version 2>&1 | head -3
echo
echo "--- filesystem ---"
FS=$(df -T "$(pwd)" | awk 'NR==2 {print $2}')
echo "fs: $FS"
case "$FS" in
    ext4|xfs|btrfs|ocfs2) echo "hardlink: SUPPORTED ($FS)" ;;
    *) echo "hardlink: UNKNOWN (FS=$FS)" ;;
esac
echo
echo "--- uv cache size for dvc (после первого резолва) ---"
uv cache dir 2>&1
du -sh "$(uv cache dir 2>/dev/null)" 2>&1 | head -1
echo
echo "=== probe done ==="
