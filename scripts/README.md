# Geant4 EPUB Markdown Scripts

This directory contains the conversion and post-processing scripts for turning Geant4 EPUB docs into LLM-friendly Markdown.

## Requirements

- `python3`
- `pandoc` (only required for EPUB conversion)

## Scripts

### 1) `epub_to_llm_md.sh`

One-shot pipeline:

1. Convert EPUB to raw Markdown with Pandoc.
2. Clean raw Markdown with `clean_llm_md.py`.

Usage:

```bash
./scripts/epub_to_llm_md.sh [EPUB_INPUT] [RAW_MD] [LLM_MD]
```

Defaults:

- `EPUB_INPUT`: `BookForApplicationDevelopers.epub`
- `RAW_MD`: `output.md`
- `LLM_MD`: `output_llm.md`

Example:

```bash
./scripts/epub_to_llm_md.sh
```

---

### 2) `clean_llm_md.py`

Clean and normalize Pandoc-generated Markdown.

Usage:

```bash
python3 scripts/clean_llm_md.py <input_md> <output_md>
```

Example:

```bash
python3 scripts/clean_llm_md.py output.md output_llm.md
```

Main transformations:

- Normalize code blocks into fenced blocks with language tags.
- Remove most internal anchors/classes/link artifacts.
- Convert non-image links to plain text.
- Keep image links but remove noisy attrs.
- Convert `images/_images/math/*.svg` formula images into inline/display TeX math.
- Wrap display formulas containing `&` / `\\` in `aligned` for better editor compatibility.
- Convert Pandoc grid tables (`+---+`) into standard pipe tables.

---

### 3) `split_md_by_h1.py`

Split one Markdown file into multiple files by level-1 headings (`# ...`).

Usage:

```bash
python3 scripts/split_md_by_h1.py -i <input_md> -o <output_dir> [options]
```

Options:

- `--number-titles` / `--no-number-titles`
  - Control whether output H1 is rewritten as `# 001 Title` or `# Title`.
- `--skip-toc-pages`
  - Skip sections that look like table-of-contents pages (H1 body is almost entirely list items).

Behavior:

- Output filenames are ordered and slugged: `001.some-title.md`.
- If content exists before the first H1, it is written to `000_preface.md`.
- H1 detection ignores fenced code blocks, so code comments like `# ...` are not treated as section titles.

Examples:

```bash
# Keep all sections, no numbering in headings
python3 scripts/split_md_by_h1.py -i output_llm.md -o split_llm_md --no-number-titles

# Number headings and skip TOC-like pages
python3 scripts/split_md_by_h1.py -i output_llm.md -o split_llm_md_num --number-titles --skip-toc-pages
```

## Recommended Workflow

```bash
# 1) Convert EPUB -> cleaned single markdown
./scripts/epub_to_llm_md.sh

# 2) (Optional) split cleaned markdown by H1
python3 scripts/split_md_by_h1.py -i output_llm.md -o split_llm_md --skip-toc-pages
```
