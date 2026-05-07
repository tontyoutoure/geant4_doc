#!/usr/bin/env bash
set -euo pipefail

EPUB_INPUT="${1:-BookForApplicationDevelopers.epub}"
RAW_MD="${2:-output.md}"
LLM_MD="${3:-output_llm.md}"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "pandoc is required but not found in PATH" >&2
  exit 1
fi

if [[ ! -f "$EPUB_INPUT" ]]; then
  echo "input epub not found: $EPUB_INPUT" >&2
  exit 1
fi

pandoc \
  "$EPUB_INPUT" \
  --from=epub \
  --to='markdown+fenced_divs+backtick_code_blocks' \
  --wrap=none \
  --extract-media=images \
  --output "$RAW_MD"

python3 scripts/clean_llm_md.py "$RAW_MD" "$LLM_MD"

echo "Wrote raw markdown: $RAW_MD"
echo "Wrote cleaned markdown: $LLM_MD"
