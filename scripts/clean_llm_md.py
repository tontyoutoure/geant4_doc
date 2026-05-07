#!/usr/bin/env python3
import argparse
import re
from typing import List, Tuple

CONTAINER_RE = re.compile(r"^([ \t]*)(:{3,})\s*(.*?)\s*$")
HIGHLIGHT_ATTR_RE = re.compile(r"^\{[^}]*\.highlight-([A-Za-z0-9+_-]+)[^}]*\}$")


LANG_MAP = {
    "c++": "cpp",
    "cmake": "cmake",
    "bash": "bash",
    "sh": "bash",
    "csh": "bash",
    "shell": "bash",
    "none": "text",
    "default": "text",
    "fortran": "text",
}

MATH_IMG_RE = re.compile(r"!\[([^\]]*)\]\((images/_images/math/[^)\s]+\.svg)\)(\{[^}]*\})?")


def map_language(token: str) -> str:
    t = token.strip().lower()
    return LANG_MAP.get(t, "text")


def strip_common_indent(lines: List[str]) -> List[str]:
    nonblank = [ln for ln in lines if ln.strip()]
    if not nonblank:
        return lines
    min_indent = min(len(re.match(r"^[ \t]*", ln).group(0)) for ln in nonblank)
    if min_indent <= 0:
        return lines
    return [ln[min_indent:] if len(ln) >= min_indent else "" for ln in lines]


def normalize_math_formula(formula: str) -> str:
    s = formula.strip()
    # Pandoc/markdown escaping back to plain TeX.
    s = s.replace("\\\\", "\\")
    s = s.replace(r"\*", "*")
    s = s.replace(r"\^", "^")
    s = s.replace(r"\_", "_")
    s = s.replace(r"\<", "<")
    s = s.replace(r"\>", ">")
    s = s.replace(r"\~", "~")
    s = re.sub(r"\\label\{[^}]*\}", "", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


def render_display_math(eq: str) -> str:
    e = eq.strip()
    if "&" in e or "\\\\" in e:
        e = f"\\begin{{aligned}}{e}\\end{{aligned}}"
    return f"$${e}$$"


def replace_math_images(line: str) -> str:
    def _sub(match: re.Match) -> str:
        formula = normalize_math_formula(match.group(1))
        return f"${formula}$" if formula else ""

    line = MATH_IMG_RE.sub(_sub, line)

    # If the full line is just an equation label + a single inline-math token, use display math.
    m = re.match(r"^\s*(\[\(\d+\)\])?\s*\$([^$]+)\$\s*$", line)
    if m:
        eq = m.group(2).strip()
        return render_display_math(eq)
    return line


def capture_highlight_block(lines: List[str], start: int, outer_indent: str, outer_delim: str) -> Tuple[List[str], int]:
    code_lines: List[str] = []
    i = start + 1
    in_inner_highlight = False
    inner_indent = ""
    inner_delim = ""

    while i < len(lines):
        line = lines[i]
        m = CONTAINER_RE.match(line)
        if m:
            indent, delim, rest = m.group(1), m.group(2), m.group(3).strip()

            if in_inner_highlight and indent == inner_indent and delim == inner_delim and rest == "":
                in_inner_highlight = False
                i += 1
                continue

            if (not in_inner_highlight) and indent == outer_indent and delim == outer_delim and rest == "":
                i += 1
                break

            if (not in_inner_highlight) and rest == "highlight":
                in_inner_highlight = True
                inner_indent = indent
                inner_delim = delim
                i += 1
                continue

            i += 1
            continue

        code_lines.append(line)
        i += 1

    while code_lines and not code_lines[0].strip():
        code_lines.pop(0)
    while code_lines and not code_lines[-1].strip():
        code_lines.pop()

    code_lines = strip_common_indent(code_lines)
    return code_lines, i


def clean_text_line(line: str) -> str:
    if re.match(r"^\s*\[\]\{#[^}]+\}\s*$", line):
        return ""

    line = line.replace("\\'", "'")
    line = replace_math_images(line)

    # Inline code attr cleanup: `x`{.docutils .literal .notranslate} -> `x`
    line = re.sub(r"(`[^`]+`)\{[^}]*\}", r"\1", line)

    # Remove inline footnote references
    line = re.sub(r"\[#?\d+\]\([^)]*\)\{[^}]*footnote-reference[^}]*\}", "", line)

    # Remove common raw HTML wrappers/tags left by pandoc or quoted HTML blocks
    line = re.sub(r"</?(?:div|span|a|code)[^>]*>", "", line)

    # Flatten [text]{.std .std-ref} and similar bracket attrs
    line = re.sub(r"\[([^\]]+)\]\{[^}]*\}", r"[\1]", line)

    # Normalize doubled brackets before link stripping
    line = line.replace("[[", "[").replace("]]", "]")

    if re.match(r"^\s*\[Listing\s+\d+[^\]]*\]\[.*\]\s*$", line):
        return ""

    # Keep image links, but drop trailing attrs
    line = re.sub(r"(!\[[^\]]*\]\([^)]*\))\{[^}]*\}", r"\1", line)

    # Convert all non-image links to plain text
    for _ in range(4):
        new_line = re.sub(r"(?<!!)\[([^\]]+)\]\([^)]*\)(\{[^}]*\})?", r"\1", line)
        if new_line == line:
            break
        line = new_line

    # Remove leftover class/id attrs like {.reference .internal}, {#id .section}
    line = re.sub(r"\{(?:#[^}\s]+)?(?:\s*\.[^}\s]+)+(?:\s+[^}]*)?\}", "", line)

    # Remove stray fenced-div markers that survived inside table cells/quotes.
    line = re.sub(r"\s*:::\s*highlight\s*", " ", line)
    line = re.sub(r"\s*:::\s*", " ", line)
    def _display_eq_sub(match: re.Match) -> str:
        return render_display_math(match.group(1))

    line = re.sub(r"^\s*\[\(\d+\)\]\s*\$([^$]+)\$\s*$", _display_eq_sub, line)

    return line.rstrip()


def collapse_blank_lines(lines: List[str]) -> List[str]:
    out: List[str] = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 1:
                out.append("")
            continue
        blank_run = 0
        out.append(line)

    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return out


def strip_quote_prefix(line: str) -> str:
    s = line.lstrip()
    if s.startswith(">"):
        s = s[1:]
        if s.startswith(" "):
            s = s[1:]
    return s


def is_grid_border(line: str) -> bool:
    s = line.rstrip()
    if not (s.startswith("+") and s.endswith("+")):
        return False
    if s.count("+") < 2:
        return False
    return bool(re.fullmatch(r"\+[=:\-+]+\+", s))


def is_grid_row(line: str) -> bool:
    s = line.rstrip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def split_grid_row(row: str, boundaries: List[int]) -> List[str]:
    r = row.rstrip()
    if len(r) < boundaries[-1] + 1:
        r = r.ljust(boundaries[-1] + 1)
    cells: List[str] = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i] + 1
        end = boundaries[i + 1]
        cells.append(r[start:end].strip())
    return cells


def finalize_grid_cells(cell_parts: List[List[str]]) -> List[str]:
    cells: List[str] = []
    for parts in cell_parts:
        text = " ".join(p for p in parts if p)
        text = re.sub(r"\s{2,}", " ", text).strip()
        text = clean_text_line(text).strip()
        text = re.sub(r"(^|\s)>(?=\s|$)", " ", text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        text = text.replace("|", r"\|")
        cells.append(text)
    return cells


def try_convert_grid_table(lines: List[str], start: int) -> Tuple[List[str], int]:
    first = strip_quote_prefix(lines[start]).rstrip()
    if not is_grid_border(first):
        return [], start

    block: List[str] = []
    i = start
    while i < len(lines):
        s = strip_quote_prefix(lines[i]).rstrip()
        if is_grid_border(s) or is_grid_row(s):
            block.append(s)
            i += 1
            continue
        break

    if len(block) < 3:
        return [], start

    boundaries = [idx for idx, ch in enumerate(block[0]) if ch == "+"]
    if len(boundaries) < 2:
        return [], start
    col_count = len(boundaries) - 1

    rows: List[List[str]] = []
    header_idx = -1
    current_parts: List[List[str]] | None = None

    for line in block:
        if is_grid_border(line):
            if current_parts is not None:
                rows.append(finalize_grid_cells(current_parts))
                current_parts = None

            if header_idx < 0 and "=" in line and rows:
                header_idx = len(rows) - 1
            continue

        if current_parts is None:
            current_parts = [[] for _ in range(col_count)]

        cells = split_grid_row(line, boundaries)
        if len(cells) != col_count:
            return [], start
        for cidx, cell in enumerate(cells):
            if cell:
                current_parts[cidx].append(cell)

    if current_parts is not None:
        rows.append(finalize_grid_cells(current_parts))

    if not rows:
        return [], start

    if header_idx < 0:
        header = rows[0]
        body = rows[1:]
    else:
        header = rows[header_idx]
        body = rows[:header_idx] + rows[header_idx + 1 :]

    if not header:
        return [], start

    def format_row(cols: List[str]) -> str:
        fixed = cols + [""] * (len(header) - len(cols))
        return "| " + " | ".join(fixed[: len(header)]) + " |"

    out = [format_row(header), "| " + " | ".join(["---"] * len(header)) + " |"]
    out.extend(format_row(r) for r in body)
    out.append("")
    return out, i


def transform(lines: List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    in_footnotes = False
    in_fence = False

    while i < len(lines):
        line = lines[i]

        if in_footnotes:
            if re.match(r"^\s*#", line):
                in_footnotes = False
            else:
                i += 1
                continue

        if line.strip() == "Footnotes":
            in_footnotes = True
            i += 1
            continue

        # Drop pandoc raw HTML passthrough fence blocks.
        if line.strip() == "```{=html}":
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                i += 1
            if i < len(lines):
                i += 1
            continue

        converted, new_i = try_convert_grid_table(lines, i)
        if converted:
            out.extend(converted)
            i = new_i
            continue

        m = CONTAINER_RE.match(line)
        if m:
            indent, delim, rest = m.group(1), m.group(2), m.group(3).strip()
            hm = HIGHLIGHT_ATTR_RE.match(rest)
            if hm:
                lang = map_language(hm.group(1))
                code, i = capture_highlight_block(lines, i, indent, delim)
                if code:
                    out.append(f"{indent}```{lang}")
                    out.extend(f"{indent}{ln}" if ln else "" for ln in code)
                    out.append(f"{indent}```")
                    out.append("")
                continue

            # Drop all non-code container markers (e.g., document wrappers, captions, admonitions)
            i += 1
            continue

        # Normalize existing fenced code block language labels.
        if line.startswith("```"):
            stripped = line.strip()
            if not in_fence:
                info = stripped[3:].strip()
                if info == "literal-block":
                    line = "```bash"
                elif info == "{=html}":
                    i += 1
                    continue
                elif info == "":
                    line = "```text"
                in_fence = True
            else:
                if stripped == "```":
                    in_fence = False
            out.append(line.rstrip())
            i += 1
            continue

        if in_fence:
            out.append(line.rstrip())
            i += 1
            continue

        cleaned = clean_text_line(line)
        if cleaned == "[]":
            cleaned = ""

        out.append(cleaned)
        i += 1

    return collapse_blank_lines(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean Pandoc EPUB markdown for LLM consumption")
    parser.add_argument("input", help="Input markdown file")
    parser.add_argument("output", help="Output cleaned markdown file")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]

    cleaned = transform(lines)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned) + "\n")


if __name__ == "__main__":
    main()
