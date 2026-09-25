#!/usr/bin/env bash
# Smoke-test an npm package exactly as consumers get it: `npm pack` the
# directory, install the tarball into an empty project, and import it under
# plain Node.js (no Bun, no TypeScript loader).
#
#   scripts/smoke-npm-pack.sh <package-dir> <package-name> <export> [<export> ...]
#
# Run after the package is built. Fails if the import throws (e.g. a
# main/exports entry pointing at .ts source, which Node refuses with
# ERR_UNSUPPORTED_NODE_MODULES_TYPE_STRIPPING) or a listed export is missing.
set -euo pipefail
pkg_dir=$(cd "$1" && pwd)
name=$2
shift 2
exports_json=$(printf '%s\n' "$@" | node -e 'console.log(JSON.stringify(require("fs").readFileSync(0,"utf8").split("\n").filter(Boolean)))')
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
(cd "$pkg_dir" && npm pack --silent --pack-destination "$tmp" >/dev/null)
cd "$tmp"
npm init -y >/dev/null
npm install --silent --no-audit --no-fund ./*.tgz >/dev/null
node --input-type=module -e "
const m = await import('$name');
const missing = $exports_json.filter((k) => !(k in m));
if (missing.length) throw new Error('missing exports: ' + missing.join(', '));
console.log('node ' + process.version + ': import(\"$name\") OK from npm pack output (' + Object.keys(m).length + ' exports)');
"
