#!/bin/sh
# Saves the `git log -p` stream read_added_code reads for a clone, runs both parsers on it, and checks they agree.
# Usage: spike/rust-diff/bench.sh PATH_TO_CLONE
set -e
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
GIT_ATTR_NOSYSTEM=1 git -C "$1" -c core.quotepath=off -c log.showRoot=true -c log.showSignature=false \
  -c core.attributesFile=/dev/null -c core.bigFileThreshold=512m -c mailmap.file=/dev/null \
  -c i18n.logOutputEncoding=UTF-8 -c diff.noprefix=false -c diff.mnemonicPrefix=false -c diff.interHunkContext=0 \
  -c diff.algorithm=myers -c diff.renameLimit=1000 -c diff.submodule=short \
  log --exclude=refs/heads/gh-pages --all --diff-merges=first-parent --reverse --topo-order -M -p -U0 --full-index \
  --no-color --no-ext-diff --no-textconv --src-prefix=a/ --dst-prefix=b/ '--format=%x00%H %P' > "$work/stream"
(cd "$here" && cargo build --release --quiet)
python3 "$here/reference.py" "$work/stream" "$work/py.out"
"$here/target/release/diffparse" "$work/stream" "$work/rs.out"
cmp "$work/py.out" "$work/rs.out" && echo "identical: $(wc -c < "$work/rs.out") bytes of records"
rm -rf "$work"
