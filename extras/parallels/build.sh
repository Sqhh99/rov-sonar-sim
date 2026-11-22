#!/usr/bin/env bash
# Build a private Ogre 1 display plugin; keep sensor rendering on Ogre 2.
set -euo pipefail
recipe="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project="$(cd "$recipe/../.." && pwd)"
runtime="${ROV_SONAR_PARALLELS_RUNTIME:-$project/.local/runtime/virgl-compat}"
revision=574445fd7f614fcb70b6ea847ca8189485fdd09d
source_tree="${1:-/opt/posim/rendering-compat/src/gz-rendering-$revision}"
mkdir -p "$runtime"
if [[ ! -f "$source_tree/ogre/src/OgreMeshFactory.cc" ]]; then
    archive="$runtime/source.tar.gz"
    curl --http1.1 -fL --retry 3 "https://codeload.github.com/gazebosim/gz-rendering/tar.gz/$revision" -o "$archive"
    printf '%s  %s\n' 870f8420d364517cb251298de745e2297b51bbdf4251bd2a65cd9dafb72fe26f "$archive" | sha256sum -c -
    mkdir -p "$runtime/source"
    tar -xzf "$archive" -C "$runtime/source" --strip-components=1
    source_tree="$runtime/source"
fi
printf '%s  %s\n' 4eb2aeb31e24c617ec3b3f7902917e5ac989b4d116eee22851f0f75a3e89fcb9 "$source_tree/ogre/src/OgreMeshFactory.cc" | sha256sum -c -
python3 - "$source_tree/ogre" "$runtime/ogre" <<'PY'
import shutil
import sys
shutil.copytree(sys.argv[1], sys.argv[2], dirs_exist_ok=True)
PY
patch -d "$runtime" -p1 < "$recipe/ogre1-mesh-fix.patch"
if [[ -f "$HOME/.ros_ardusub_env/env" ]]; then
    set +u
    source "$HOME/.ros_ardusub_env/env"
    set -u
fi
export PKG_CONFIG_PATH="/usr/lib/aarch64-linux-gnu/pkgconfig:${PKG_CONFIG_PATH:-}"
cmake -S "$recipe" -B "$runtime/build" -DCMAKE_BUILD_TYPE=Release -DPOSIM_OGRE_SOURCE="$runtime/ogre"
cmake --build "$runtime/build" --parallel "${CMAKE_BUILD_PARALLEL_LEVEL:-2}"
