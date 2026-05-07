#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
from typing import List, Tuple


H1_RE = re.compile(r"^#\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")


def normalize_title_for_display(raw_title: str) -> str:
    title = raw_title.strip()
    title = re.sub(r"^`(.+)`$", r"\1", title)
    # Drop common numeric prefixes: "1", "1.", "1 ", "1.2.3 ", "2) ", "3 - ".
    title = re.sub(r"^\(?\d+(?:\.\d+)*\)?(?:[.)-])?\s*", "", title)
    return title.strip() or "Untitled"


def slugify(title: str, fallback: str) -> str:
    s = title.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or fallback


def split_by_h1(lines: List[str]) -> Tuple[List[str], List[Tuple[str, List[str]]]]:
    preface: List[str] = []
    sections: List[Tuple[str, List[str]]] = []

    current_title = None
    current_lines: List[str] = []
    seen_first_h1 = False
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line in lines:
        fm = FENCE_RE.match(line)
        if fm:
            marker = fm.group(1)
            ch = marker[0]
            mlen = len(marker)
            if not in_fence:
                in_fence = True
                fence_char = ch
                fence_len = mlen
            elif ch == fence_char and mlen >= fence_len:
                in_fence = False
                fence_char = ""
                fence_len = 0

        if in_fence:
            if not seen_first_h1:
                preface.append(line)
            else:
                current_lines.append(line)
            continue

        m = H1_RE.match(line)
        if m:
            if current_title is not None:
                sections.append((current_title, current_lines))
            current_title = m.group(1).strip()
            current_lines = [line]
            seen_first_h1 = True
            continue

        if not seen_first_h1:
            preface.append(line)
        else:
            current_lines.append(line)

    if current_title is not None:
        sections.append((current_title, current_lines))

    return preface, sections


def is_toc_section(section_lines: List[str]) -> bool:
    # section_lines includes the H1 line at index 0
    body = section_lines[1:] if section_lines else []
    nonempty = [ln for ln in body if ln.strip()]
    if len(nonempty) < 5:
        return False

    list_like = sum(1 for ln in nonempty if LIST_ITEM_RE.match(ln))
    return list_like == len(nonempty)


def write_sections(
    preface: List[str],
    sections: List[Tuple[str, List[str]]],
    out_dir: Path,
    number_titles: bool,
    skip_toc_pages: bool,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0

    preface_content = "\n".join(preface).strip()
    if preface_content:
        preface_path = out_dir / "000_preface.md"
        preface_path.write_text(preface_content + "\n", encoding="utf-8")
        written += 1

    section_idx = 0
    for raw_title, section_lines in sections:
        if skip_toc_pages and is_toc_section(section_lines):
            continue

        section_idx += 1
        display_title = normalize_title_for_display(raw_title)
        heading = f"# {section_idx:03d} {display_title}" if number_titles else f"# {display_title}"

        body = section_lines[:]
        if body and H1_RE.match(body[0]):
            body[0] = heading
        else:
            body.insert(0, heading)

        fallback = f"section-{section_idx:03d}"
        slug = slugify(display_title, fallback)
        filename = f"{section_idx:03d}.{slug}.md"
        (out_dir / filename).write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")
        written += 1

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Split a markdown file into files by H1 headings.")
    parser.add_argument("-i", "--input", required=True, help="Input markdown file path")
    parser.add_argument("-o", "--output-dir", required=True, help="Output directory")
    parser.add_argument(
        "--number-titles",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Whether H1 titles in output files should include numeric prefixes",
    )
    parser.add_argument(
        "--skip-toc-pages",
        action="store_true",
        default=False,
        help="Skip H1 sections that look like table-of-contents pages",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.output_dir)
    lines = in_path.read_text(encoding="utf-8").splitlines()

    preface, sections = split_by_h1(lines)
    if not sections and not "\n".join(preface).strip():
        raise SystemExit("Input markdown is empty.")

    written = write_sections(preface, sections, out_dir, args.number_titles, args.skip_toc_pages)
    print(f"Wrote {written} files to: {out_dir}")


if __name__ == "__main__":
    main()
