from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - exercised on plain macOS Python.
    yaml = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_FILE = PROJECT_ROOT / "00_management" / "cncbook_manifest.yaml"
REPORT_FILE = PROJECT_ROOT / "00_management" / "cncbook_pipeline_report.md"
METADATA_FILE = PROJECT_ROOT / "brunch" / "02_article_metadata.csv"
PAGE_BREAK = "\\newpage"
IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)([^\n]*)")
IMAGE_COMMENT_PATTERN = re.compile(r"<!--\s*이미지 파일:\s*([^>]+?)\s*-->")
FENCED_IMAGE_COMMENT_PATTERN = re.compile(
    r"```(?:html)?\s*\n\s*<!--\s*이미지 파일:\s*([^>]+?)\s*-->\s*\n```",
    re.MULTILINE,
)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


@dataclass
class ChapterResult:
    order: int
    part: str
    title: str
    source_file: str
    book_file: str
    brunch_file: str
    image_count: int
    image_reference_count: int
    image_candidate_count: int
    image_candidates: list[str]
    needs_image: bool
    needs_review: bool
    status: str
    issues: list[str]


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if re.match(r"^-?\d+$", value):
        return int(value)
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def parse_simple_manifest(text: str) -> dict[str, Any]:
    """Small YAML subset parser used when PyYAML is not installed."""
    data: dict[str, Any] = {}
    section: str | None = None
    current_chapter: dict[str, Any] | None = None
    current_list_key: str | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0 and line.endswith(":"):
            section = line[:-1]
            current_chapter = None
            current_list_key = None
            data[section] = [] if section == "chapters" else {}
            continue

        if section == "chapters":
            if line.startswith("- "):
                current_chapter = {}
                data.setdefault("chapters", []).append(current_chapter)
                current_list_key = None
                rest = line[2:].strip()
                if rest and ":" in rest:
                    key, value = rest.split(":", 1)
                    current_chapter[key.strip()] = parse_scalar(value)
                continue

            if current_chapter is None:
                continue

            if line.startswith("- ") and current_list_key:
                current_chapter[current_list_key].append(parse_scalar(line[2:]))
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if value == "":
                    current_chapter[key] = []
                    current_list_key = key
                else:
                    current_chapter[key] = parse_scalar(value)
                    current_list_key = None
            continue

        if section in {"project", "defaults"}:
            target = data.setdefault(section, {})
            if line.startswith("- ") and current_list_key:
                target[current_list_key].append(parse_scalar(line[2:]))
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if value == "":
                    target[key] = []
                    current_list_key = key
                else:
                    target[key] = parse_scalar(value)
                    current_list_key = None

    return data


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_FILE}")
    text = MANIFEST_FILE.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text)
    else:
        data = parse_simple_manifest(text)
    if not isinstance(data, dict):
        raise ValueError("Manifest must be a YAML mapping.")
    data.setdefault("project", {})
    data.setdefault("defaults", {})
    data.setdefault("chapters", [])
    return data


def project_path(relative: str) -> Path:
    return (PROJECT_ROOT / relative).resolve()


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def resolve_source_file(source_dir: Path, source_file: str) -> Path:
    exact_path = source_dir / source_file
    if exact_path.exists():
        return exact_path

    wanted = nfc(source_file)
    for path in source_dir.glob("*.md"):
        if nfc(path.name) == wanted:
            return path
    return exact_path


def safe_filename(order: int, title: str) -> str:
    normalized = nfc(title)
    normalized = re.sub(r"[\\/:*?\"<>|]+", "_", normalized)
    normalized = re.sub(r"\s+", "_", normalized.strip())
    normalized = normalized.strip("._")
    if not normalized:
        normalized = f"chapter_{order:02d}"
    return f"{order:02d}_{normalized}.md"


def strip_frontmatter(content: str) -> str:
    lines = content.replace("\r\n", "\n").splitlines()
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                return "\n".join(lines[index + 1 :]).strip()
    return "\n".join(lines).strip()


def strip_numeric_prefix(title: str) -> str:
    title = title.strip()
    title = re.sub(r"^\d+\s*[.)]\s*", "", title)
    return title.strip()


def normalize_section_heading(text: str) -> str:
    text = text.strip()
    match = re.match(r"^(\d+)\s*[.)]\s*(.+)$", text)
    if match:
        return f"{match.group(1)}) {match.group(2).strip()}"
    return text


def strip_wrapping_bold(text: str) -> str:
    text = text.strip()
    while True:
        match = re.match(r"^\*\*(.+?)\*\*$", text)
        if not match:
            return text
        text = match.group(1).strip()


def heading_text(line: str) -> str:
    text = re.sub(r"^#{1,6}\s*", "", line.strip()).strip()
    text = strip_wrapping_bold(text)
    return text


def looks_like_plain_title(line: str) -> bool:
    stripped = strip_wrapping_bold(line.strip())
    if not stripped:
        return False
    if stripped.startswith(("-", "|", ">", "!", "<")):
        return False
    if len(stripped) > 80:
        return False
    return True


def find_source_title(content: str) -> str | None:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^#\s+", stripped):
            return strip_numeric_prefix(heading_text(stripped))
        if looks_like_plain_title(stripped):
            return strip_numeric_prefix(strip_wrapping_bold(stripped))
        return None
    return None


def remove_internal_sections(content: str, remove_sections: list[str]) -> str:
    if not remove_sections:
        return content.strip()

    lines = content.splitlines()
    output: list[str] = []
    skipping = False
    skip_level = 0
    remove_set = {section.strip() for section in remove_sections}

    for line in lines:
        stripped = line.strip()
        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = strip_numeric_prefix(strip_wrapping_bold(heading_match.group(2)))
            if skipping and level <= skip_level:
                skipping = False
            if not skipping and text in remove_set:
                skipping = True
                skip_level = level
                continue
        if not skipping:
            output.append(line)

    return "\n".join(output).strip()


def normalize_separators(content: str) -> str:
    """Preserve manuscript scene breaks without turning them into page breaks.

    Pagination belongs to the assembled book structure (cover, parts, and
    chapters). Internal ``---`` markers are thematic breaks inside a chapter.
    """
    content = re.sub(r"(?m)^\s*---\s*$", "\n\n---\n\n", content)
    content = re.sub(r"\n{5,}", "\n\n\n\n", content)
    return compact_page_breaks(content)


def compact_page_breaks(content: str) -> str:
    marker = re.escape(PAGE_BREAK)
    replacement = lambda _match: f"\n\n{PAGE_BREAK}\n\n"
    content = re.sub(rf"\n*{marker}\n*", replacement, content)
    content = re.sub(rf"(?:\n*{marker}\n*){{2,}}", replacement, content)
    content = re.sub(r"\n{5,}", "\n\n\n\n", content)
    return content.strip()


def visible_char_count(text: str) -> int:
    text = IMAGE_PATTERN.sub("", text)
    text = re.sub(r"[#*_`\[\]()>|~\-\s]", "", text)
    return len(text)


def normalize_images(content: str) -> str:
    def replace(match: re.Match[str]) -> str:
        alt = match.group(1).strip()
        path = match.group(2).strip()
        caption = match.group(3).strip()
        if caption:
            return f"![{alt}]({path}){caption}"
        return f"![{alt}]({path})"

    return IMAGE_PATTERN.sub(replace, content)


def source_image_reference_count(content: str) -> int:
    return len(IMAGE_PATTERN.findall(content)) + len(IMAGE_COMMENT_PATTERN.findall(content))


def source_image_key(source_path: Path, chapter: dict[str, Any]) -> str:
    if chapter.get("image_key") is not None:
        return str(chapter["image_key"]).zfill(2)
    match = re.match(r"^(\d+)", nfc(source_path.name))
    if match:
        return match.group(1).zfill(2)
    return str(int(chapter["order"]) - 1).zfill(2)


def image_dir(data: dict[str, Any]) -> Path | None:
    raw = data["project"].get("image_dir")
    if not raw:
        return None
    return project_path(str(raw))


def posix_relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def markdown_path_from_output(path: Path, output_dir: Path) -> str:
    return os.path.relpath(path, output_dir).replace(os.sep, "/")


def optimized_image_dir(data: dict[str, Any]) -> Path:
    raw = data["project"].get("optimized_image_dir") or "output/cncbook_images"
    return project_path(str(raw))


def image_optimization_enabled(data: dict[str, Any]) -> bool:
    return bool(data["project"].get("optimize_images", True))


def optimized_image_path(source: Path, data: dict[str, Any]) -> Path:
    try:
        relative = source.resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        relative = Path(source.name)
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", relative.with_suffix("").as_posix()).strip("_")
    if not stem:
        stem = "image"
    digest = hashlib.sha1(relative.as_posix().encode("utf-8")).hexdigest()[:10]
    return optimized_image_dir(data) / f"{stem[:80]}_{digest}.jpg"


def prepare_image_for_output(source: Path, data: dict[str, Any]) -> Path:
    if not image_optimization_enabled(data) or not source.exists():
        return source

    target_dir = optimized_image_dir(data).resolve()
    try:
        source.resolve().relative_to(target_dir)
        return source
    except ValueError:
        pass

    target = optimized_image_path(source, data)
    target.parent.mkdir(parents=True, exist_ok=True)
    max_px = str(int(data["project"].get("optimized_image_max_px", 1600)))
    quality = str(int(data["project"].get("optimized_image_quality", 82)))

    sips = shutil.which("sips")
    if sips is None:
        return source

    try:
        subprocess.run(
            [
                sips,
                "-Z",
                max_px,
                "-s",
                "format",
                "jpeg",
                "-s",
                "formatOptions",
                quality,
                str(source),
                "--out",
                str(target),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return source

    return target if target.exists() and target.stat().st_size > 0 else source


def image_candidates(data: dict[str, Any], chapter: dict[str, Any], source_path: Path) -> list[Path]:
    raw_candidates = chapter.get("image_candidates")
    if isinstance(raw_candidates, list) and raw_candidates:
        paths: list[Path] = []
        for item in raw_candidates:
            candidate = project_path(str(item))
            paths.append(candidate)
        return paths

    base_dir = image_dir(data)
    if base_dir is None:
        return []
    folder = base_dir / source_image_key(source_path, chapter)
    if not folder.exists():
        return []
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS and not path.name.startswith(".")
    )


def caption_for_image(chapter: dict[str, Any], index: int, total: int) -> str:
    title = str(chapter["title"])
    if total == 1:
        return f"{title}의 핵심 장면을 한 컷으로 압축한 삽화."

    templates = [
        f"{title}의 문제의식이 처음 모습을 드러내는 장면.",
        "작업의 흐름이 구체적인 구조로 바뀌는 순간.",
        "사람의 판단과 AI의 실행이 나뉘는 지점을 보여주는 장면.",
        f"{title}의 결론을 이미지로 정리한 장면.",
    ]
    if index < len(templates):
        return templates[index]
    return f"{title}의 흐름을 보조하는 삽화 {index + 1}."


def image_markdown_block(path: Path, output_dir: Path, caption: str, data: dict[str, Any]) -> str:
    prepared = prepare_image_for_output(path, data)
    image_path = markdown_path_from_output(prepared, output_dir)
    return f"![]({image_path})\n\n_{caption}_"


def spread_indices(slot_count: int, item_count: int) -> list[int]:
    if slot_count <= 0:
        return [0 for _ in range(item_count)]
    indices: list[int] = []
    for index in range(item_count):
        slot = round(((index + 1) * slot_count) / (item_count + 1)) - 1
        indices.append(max(0, min(slot_count - 1, slot)))
    return indices


def insert_candidate_images(
    content: str,
    candidates: list[Path],
    chapter: dict[str, Any],
    output_dir: Path,
    existing_reference_count: int,
    data: dict[str, Any],
) -> str:
    if not candidates or existing_reference_count > 0:
        return content.strip()

    image_blocks = [
        image_markdown_block(path, output_dir, caption_for_image(chapter, index, len(candidates)), data)
        for index, path in enumerate(candidates)
    ]

    sections = [section.strip() for section in content.split(PAGE_BREAK)]
    if len(sections) > 1:
        section_images: dict[int, list[str]] = {}
        for target, block in zip(spread_indices(len(sections), len(image_blocks)), image_blocks):
            section_images.setdefault(target, []).append(block)
        rebuilt: list[str] = []
        for index, section in enumerate(sections):
            section_parts = [section] if section else []
            section_parts.extend(section_images.get(index, []))
            rebuilt.append("\n\n".join(part for part in section_parts if part).strip())
        return compact_page_breaks(f"\n\n{PAGE_BREAK}\n\n".join(rebuilt))

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", content) if paragraph.strip()]
    if not paragraphs:
        return "\n\n".join(image_blocks).strip()

    paragraph_images: dict[int, list[str]] = {}
    for target, block in zip(spread_indices(len(paragraphs), len(image_blocks)), image_blocks):
        paragraph_images.setdefault(target, []).append(block)

    rebuilt_paragraphs: list[str] = []
    for index, paragraph in enumerate(paragraphs):
        rebuilt_paragraphs.append(paragraph)
        rebuilt_paragraphs.extend(paragraph_images.get(index, []))
    return compact_page_breaks("\n\n".join(rebuilt_paragraphs))


def resolve_comment_image(
    filename: str,
    data: dict[str, Any],
    chapter: dict[str, Any],
    source_path: Path,
) -> Path:
    base_dir = image_dir(data)
    if base_dir is not None:
        return base_dir / source_image_key(source_path, chapter) / filename
    return source_path.parent / filename


def normalize_image_comments(
    content: str,
    data: dict[str, Any],
    chapter: dict[str, Any],
    source_path: Path,
    output_dir: Path,
) -> str:
    def to_markdown(filename: str) -> str:
        filename = filename.strip()
        resolved = resolve_comment_image(filename, data, chapter, source_path)
        prepared = prepare_image_for_output(resolved, data)
        return f"![]({markdown_path_from_output(prepared, output_dir)})"

    def replace_fenced(match: re.Match[str]) -> str:
        return to_markdown(match.group(1))

    def replace_comment(match: re.Match[str]) -> str:
        filename = match.group(1).strip()
        return to_markdown(filename)

    content = FENCED_IMAGE_COMMENT_PATTERN.sub(replace_fenced, content)
    return IMAGE_COMMENT_PATTERN.sub(replace_comment, content)


def optimize_markdown_images(content: str, data: dict[str, Any], output_dir: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        alt = match.group(1).strip()
        path = match.group(2).strip()
        suffix = match.group(3).strip()
        if is_remote_image(path) or path.startswith("/"):
            rewritten = path
        else:
            if path.startswith("assets/") or path.startswith("CNC_gpt/") or path.startswith("output/"):
                resolved = (PROJECT_ROOT / path).resolve()
            else:
                resolved = (output_dir / path).resolve()
            prepared = prepare_image_for_output(resolved, data)
            rewritten = markdown_path_from_output(prepared, output_dir)
        if suffix:
            return f"![{alt}]({rewritten}){suffix}"
        return f"![{alt}]({rewritten})"

    return IMAGE_PATTERN.sub(replace, content)


def normalize_book_body(
    content: str,
    remove_sections: list[str],
    data: dict[str, Any],
    chapter: dict[str, Any],
    source_path: Path,
    output_dir: Path,
    candidates: list[Path],
) -> str:
    existing_reference_count = source_image_reference_count(content)
    content = strip_frontmatter(content)
    source_title = find_source_title(content)
    lines = content.splitlines()
    body_lines: list[str] = []
    first_title_removed = False

    for line in lines:
        stripped = line.strip()
        if not first_title_removed:
            if re.match(r"^#\s+", stripped):
                first_title_removed = True
                continue
            if source_title and looks_like_plain_title(stripped):
                candidate = strip_numeric_prefix(strip_wrapping_bold(stripped))
                if nfc(candidate) == nfc(source_title):
                    first_title_removed = True
                    continue
        body_lines.append(line)

    body = "\n".join(body_lines).strip()
    body = remove_internal_sections(body, remove_sections)
    normalized_lines: list[str] = []

    for line in body.splitlines():
        stripped = line.strip()
        if re.match(r"^#{2,6}\s+", stripped):
            text = heading_text(stripped)
            text = normalize_section_heading(text)
            normalized_lines.append(f"### {text}")
        else:
            normalized_lines.append(line.rstrip())

    body = "\n".join(normalized_lines)
    body = normalize_image_comments(body, data, chapter, source_path, output_dir)
    body = normalize_images(body)
    body = optimize_markdown_images(body, data, output_dir)
    body = normalize_separators(body)
    body = insert_candidate_images(body, candidates, chapter, output_dir, existing_reference_count, data)
    return body.strip()


def build_book_article(
    chapter: dict[str, Any],
    defaults: dict[str, Any],
    data: dict[str, Any],
    source_text: str,
    source_path: Path,
    output_dir: Path,
) -> str:
    remove_sections = list(defaults.get("remove_sections") or [])
    title = chapter["title"]
    order = int(chapter["order"])
    candidates = image_candidates(data, chapter, source_path)
    body = normalize_book_body(
        source_text,
        remove_sections,
        data,
        chapter,
        source_path,
        output_dir,
        candidates,
    )
    if body:
        return f"## {order}. {title}\n\n{body}\n"
    return f"## {order}. {title}\n"


def is_remote_image(path: str) -> bool:
    return path.startswith("http://") or path.startswith("https://")


def convert_to_brunch(
    book_article: str,
    chapter: dict[str, Any],
    defaults: dict[str, Any],
    candidates: list[Path],
    book_output_dir: Path,
    brunch_output_dir: Path,
) -> str:
    lines = book_article.strip().splitlines()
    body_lines = lines[1:] if lines and re.match(r"^##\s+", lines[0].strip()) else lines
    body = "\n".join(body_lines).strip()
    body = re.sub(rf"(?m)^\s*{re.escape(PAGE_BREAK)}\s*$", "\n\n", body).strip()
    body = rewrite_image_paths(body, book_output_dir, brunch_output_dir)

    brunch_lines: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if re.match(r"^###\s+", stripped):
            text = heading_text(stripped)
            brunch_lines.append(f"### **{text}**")
        else:
            brunch_lines.append(line.rstrip())

    body_images = {path for _, path, _ in IMAGE_PATTERN.findall(body)}
    candidate_paths = {markdown_path_from_output(path, brunch_output_dir) for path in candidates}
    local_images = sorted(
        path for path in body_images | candidate_paths if not is_remote_image(path)
    )

    memo = chapter.get("upload_memo") or defaults.get("upload_memo") or ""
    if local_images:
        memo = f"{memo} 로컬 이미지 {len(local_images)}개는 브런치 업로드 후 URL 교체 필요."

    header = [
        f"브런치 제목: {chapter.get('brunch_title') or chapter['title']}",
        f"브런치 부제: {chapter.get('subtitle') or ''}",
        f"매거진: {chapter.get('magazine') or defaults.get('magazine') or ''}",
        f"업로드 메모: {memo}",
    ]
    if local_images:
        header.append(f"이미지 후보: {', '.join(local_images)}")
    header.extend(["---", ""])
    return "\n".join(header + brunch_lines).strip() + "\n"


def rewrite_image_paths(content: str, from_dir: Path, to_dir: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        alt = match.group(1).strip()
        path = match.group(2).strip()
        caption = match.group(3).strip()
        if is_remote_image(path) or path.startswith("/"):
            rewritten = path
        else:
            resolved = (from_dir / path).resolve()
            rewritten = markdown_path_from_output(resolved, to_dir)
        if caption:
            return f"![{alt}]({rewritten}){caption}"
        return f"![{alt}]({rewritten})"

    return IMAGE_PATTERN.sub(replace, content)


def resolve_image_path(path: str, source_path: Path) -> Path:
    if path.startswith("/"):
        return Path(path)
    if path.startswith("../"):
        return (source_path.parent / path).resolve()
    if path.startswith("assets/") or path.startswith("CNC_gpt/"):
        return PROJECT_ROOT / path
    return (source_path.parent / path).resolve()


def image_issues(
    content: str,
    data: dict[str, Any],
    chapter: dict[str, Any],
    source_path: Path,
    candidates: list[Path],
) -> list[str]:
    issues: list[str] = []
    for _, path, _ in IMAGE_PATTERN.findall(content):
        if is_remote_image(path):
            continue
        resolved = resolve_image_path(path, source_path)
        if not resolved.exists():
            issues.append(f"image missing: {path}")
    for filename in IMAGE_COMMENT_PATTERN.findall(content):
        resolved = resolve_comment_image(filename.strip(), data, chapter, source_path)
        if not resolved.exists():
            issues.append(f"image comment missing: {filename.strip()}")
    for path in candidates:
        if not path.exists():
            issues.append(f"image candidate missing: {posix_relative(path)}")
    return issues


def validate_manifest(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    project = data["project"]
    chapters = data["chapters"]
    source_dir = project_path(project.get("source_dir", "assets/07_AI"))
    cover_image = project.get("cover_image")
    if cover_image and not project_path(str(cover_image)).exists():
        issues.append(f"cover image missing: {cover_image}")

    if not isinstance(chapters, list) or not chapters:
        issues.append("manifest has no chapters")
        return issues

    seen_orders: set[int] = set()
    seen_sources: set[str] = set()
    for chapter in chapters:
        for key in ("order", "part", "source_file", "title"):
            if key not in chapter:
                issues.append(f"chapter missing key: {key}")
        if "order" in chapter:
            order = int(chapter["order"])
            if order in seen_orders:
                issues.append(f"duplicate order: {order}")
            seen_orders.add(order)
        source_file = chapter.get("source_file")
        if source_file:
            seen_sources.add(source_file)
            source_path = resolve_source_file(source_dir, source_file)
            if not source_path.exists():
                issues.append(f"source missing: {source_file}")
            else:
                source_text = source_path.read_text(encoding="utf-8")
                candidates = image_candidates(data, chapter, source_path)
                issues.extend(image_issues(source_text, data, chapter, source_path, candidates))

    if seen_orders:
        ordered = sorted(seen_orders)
        expected = list(range(ordered[0], ordered[-1] + 1))
        if ordered != expected:
            issues.append(f"order sequence has gaps: {ordered}")

    if source_dir.exists():
        actual_sources = {nfc(path.name) for path in source_dir.glob("*.md")}
        normalized_seen_sources = {nfc(source) for source in seen_sources}
        unlisted = sorted(actual_sources - normalized_seen_sources)
        for source in unlisted:
            issues.append(f"source not listed in manifest: {source}")
    else:
        issues.append(f"source_dir missing: {source_dir.relative_to(PROJECT_ROOT)}")

    return issues


def ensure_dirs(data: dict[str, Any]) -> tuple[Path, Path, Path]:
    project = data["project"]
    source_dir = project_path(project.get("source_dir", "assets/07_AI"))
    manuscript_dir = project_path(project.get("manuscript_dir", "cnc_book_manuscript"))
    brunch_dir = project_path(project.get("brunch_dir", "brunch/posts"))
    manuscript_dir.mkdir(parents=True, exist_ok=True)
    brunch_dir.mkdir(parents=True, exist_ok=True)
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    return source_dir, manuscript_dir, brunch_dir


def output_markdown_file(data: dict[str, Any]) -> Path | None:
    raw = data["project"].get("output_markdown")
    if not raw:
        return None
    return project_path(str(raw))


def clean_outputs(data: dict[str, Any]) -> None:
    _, manuscript_dir, brunch_dir = ensure_dirs(data)
    for directory in (manuscript_dir, brunch_dir):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
    optimized_dir = optimized_image_dir(data)
    if optimized_dir.exists():
        shutil.rmtree(optimized_dir)
    optimized_dir.mkdir(parents=True, exist_ok=True)
    for file_path in (REPORT_FILE, METADATA_FILE):
        if file_path.exists():
            file_path.unlink()
    output_file = output_markdown_file(data)
    if output_file and output_file.exists():
        output_file.unlink()


def build_cover_page(data: dict[str, Any], output_dir: Path) -> str:
    raw_cover_image = data["project"].get("cover_image")
    if raw_cover_image:
        cover_image = project_path(str(raw_cover_image))
        prepared = prepare_image_for_output(cover_image, data)
        cover_path = markdown_path_from_output(prepared, output_dir)
        return f"![]({cover_path}){{width=100%}}"

    title = data["project"].get("title", "CNCbook")
    subtitle = data["project"].get("subtitle", "")
    lines = [f"# {title}", ""]
    if subtitle:
        lines.extend([f"## {subtitle}", ""])
    lines.extend(["지송", "", "CNCbook 초판 원고"])
    return "\n".join(lines).strip()


def build_author_page() -> str:
    lines = [
        "# 저자 소개",
        "",
        "## 지송",
        "",
        "지송은 의학과 공학 사이에서 임상 현장의 불확실한 문제를 구조화하고, 모델 기반 의료 도구와 개인 AI 워크플로우로 번역하는 사람이다.",
        "",
        "건국대학교 의학전문대학원에서 의학을 공부하고 있으며, 고려대학교 건축사회환경공학부를 졸업했다. 의료를 단순히 암기할 대상이 아니라 데이터, 구조, 모델, 책임이 만나는 시스템으로 이해하려고 한다.",
        "",
        "주요 관심사는 임상 의사결정 보조 시스템, 약동학 및 위험도 모델링, 내분비 AI 프로토타입, 의무기록 텍스트 구조화, 개인 지식관리와 AI 운영체계다. DiaFrame, EstroFrame, AndroFrame, NeuroFrame, CleanText, CleanEMR 같은 연구·교육용 프로토타입을 만들며, 실제 의료 워크플로우 안에서 사람이 어디서 판단하고 AI가 어디서 실행을 도울 수 있는지 탐색한다.",
        "",
        "브런치와 GitHub, jisong.dev에 글과 프로젝트 기록을 남긴다. 이 책에 등장하는 의료 관련 도구들은 실제 진단이나 처방을 대체하기 위한 의료기기가 아니라, 의료 데이터를 구조화하고 모델링 사고를 설명하기 위한 개인 프로젝트 및 연구용 프로토타입이다.",
        "",
        "웹: jisong.dev  ·  GitHub: github.com/jsbang01357  ·  Brunch: brunch.co.kr/@jsbang",
    ]
    return "\n".join(lines).strip()


def build_manual_toc(chapters: list[dict[str, Any]]) -> str:
    lines = ["# 목차", ""]
    current_part: str | None = None
    for chapter in chapters:
        part = str(chapter["part"])
        if part != current_part:
            current_part = part
            if lines and lines[-1] != "":
                lines.append("")
            lines.extend([f"## {part}", ""])
        lines.append(f"- {int(chapter['order'])}. {chapter['title']}")
    return "\n".join(lines).strip()


def build(data: dict[str, Any]) -> tuple[list[ChapterResult], list[str]]:
    clean_outputs(data)
    source_dir, manuscript_dir, brunch_dir = ensure_dirs(data)
    defaults = data["defaults"]
    chapters = sorted(data["chapters"], key=lambda item: int(item["order"]))
    results: list[ChapterResult] = []
    book_blocks: list[str] = [
        build_cover_page(data, manuscript_dir),
        PAGE_BREAK,
        build_author_page(),
        PAGE_BREAK,
        build_manual_toc(chapters),
    ]
    current_part: str | None = None

    def append_page_break() -> None:
        if not book_blocks or book_blocks[-1] != PAGE_BREAK:
            book_blocks.append(PAGE_BREAK)

    for chapter in chapters:
        source_path = resolve_source_file(source_dir, chapter["source_file"])
        source_text = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
        source_title = find_source_title(strip_frontmatter(source_text))
        issues: list[str] = []
        if not source_text.strip():
            issues.append("empty source")
        if source_title is None:
            issues.append("source title missing")

        candidates = image_candidates(data, chapter, source_path)
        issues.extend(image_issues(source_text, data, chapter, source_path, candidates))

        book_article = build_book_article(
            chapter, defaults, data, source_text, source_path, manuscript_dir
        )
        brunch_article = convert_to_brunch(
            book_article, chapter, defaults, candidates, manuscript_dir, brunch_dir
        )
        output_name = safe_filename(int(chapter["order"]), chapter["title"])
        book_path = manuscript_dir / output_name
        brunch_path = brunch_dir / output_name
        book_path.write_text(book_article, encoding="utf-8")
        brunch_path.write_text(brunch_article, encoding="utf-8")

        if chapter["part"] != current_part:
            current_part = chapter["part"]
            append_page_break()
            book_blocks.extend(["", f"# {current_part}"])
            append_page_break()
        else:
            append_page_break()
        book_blocks.extend(["", book_article.strip()])

        image_reference_count = source_image_reference_count(source_text)
        image_candidate_count = len(candidates)
        image_count = image_reference_count or image_candidate_count
        needs_image = bool(chapter.get("needs_image", False)) and image_count == 0
        needs_review = bool(chapter.get("needs_review", False))
        status = str(chapter.get("status") or defaults.get("status") or "draft")
        results.append(
            ChapterResult(
                order=int(chapter["order"]),
                part=chapter["part"],
                title=chapter["title"],
                source_file=str(source_path.relative_to(PROJECT_ROOT)),
                book_file=str(book_path.relative_to(PROJECT_ROOT)),
                brunch_file=str(brunch_path.relative_to(PROJECT_ROOT)),
                image_count=image_count,
                image_reference_count=image_reference_count,
                image_candidate_count=image_candidate_count,
                image_candidates=[posix_relative(path) for path in candidates],
                needs_image=needs_image,
                needs_review=needs_review,
                status=status,
                issues=issues,
            )
        )

    assembled_blocks = [block.strip() for block in book_blocks if block.strip()]
    book_text = compact_page_breaks("\n\n".join(assembled_blocks)).strip() + "\n"
    (manuscript_dir / "book.md").write_text(book_text, encoding="utf-8")
    output_file = output_markdown_file(data)
    if output_file is not None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(book_text, encoding="utf-8")
    manifest_issues = validate_manifest(data)
    write_report(results, manifest_issues, data)
    write_metadata(results)
    return results, manifest_issues


def write_report(
    results: list[ChapterResult],
    manifest_issues: list[str],
    data: dict[str, Any],
) -> None:
    source_dir = data["project"].get("source_dir", "assets/07_AI")
    manuscript_dir = data["project"].get("manuscript_dir", "cnc_book_manuscript")
    brunch_dir = data["project"].get("brunch_dir", "brunch/posts")
    lines = [
        "# CNCbook Pipeline Report",
        "",
        f"이 문서는 `{source_dir}` 원천을 `{manuscript_dir}`와 `{brunch_dir}`로 변환한 결과다.",
        "",
        "## Summary",
        "",
        f"- 변환 장 수: {len(results)}",
        f"- 이미지 후보/참조 총수: {sum(result.image_count for result in results)}",
        f"- 이미지 보강 필요 장: {sum(1 for result in results if result.needs_image)}",
        f"- 검토 필요 장: {sum(1 for result in results if result.needs_review)}",
        f"- 이슈 수: {sum(len(result.issues) for result in results) + len(manifest_issues)}",
        "",
        "## Manifest / Source Issues",
        "",
    ]
    if manifest_issues:
        lines.extend(f"- {issue}" for issue in manifest_issues)
    else:
        lines.append("- 없음")

    lines.extend(
        [
            "",
            "## Chapter Results",
            "",
            "| order | part | title | source_file | book_file | brunch_file | images | refs | candidates | needs_image | needs_review | status | issues |",
            "|---:|---|---|---|---|---|---:|---:|---:|---|---|---|---|",
        ]
    )
    for result in results:
        issue_text = "<br>".join(result.issues) if result.issues else ""
        lines.append(
            "| {order} | {part} | {title} | `{source}` | `{book}` | `{brunch}` | {images} | {refs} | {candidates} | {needs_image} | {needs_review} | {status} | {issues} |".format(
                order=result.order,
                part=result.part,
                title=result.title,
                source=result.source_file,
                book=result.book_file,
                brunch=result.brunch_file,
                images=result.image_count,
                refs=result.image_reference_count,
                candidates=result.image_candidate_count,
                needs_image="YES" if result.needs_image else "NO",
                needs_review="YES" if result.needs_review else "NO",
                status=result.status,
                issues=issue_text,
            )
        )

    lines.extend(["", "## Image Candidates", ""])
    for result in results:
        if result.image_candidates:
            lines.append(f"### {result.order}. {result.title}")
            lines.extend(f"- `{path}`" for path in result.image_candidates)
            lines.append("")
    REPORT_FILE.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_metadata(results: list[ChapterResult]) -> None:
    with METADATA_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            lineterminator="\n",
            fieldnames=[
                "order",
                "part",
                "title",
                "status",
                "source_file",
                "book_file",
                "brunch_file",
                "image_count",
                "image_reference_count",
                "image_candidate_count",
                "image_candidates",
                "needs_image",
                "needs_review",
                "issues",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "order": result.order,
                    "part": result.part,
                    "title": result.title,
                    "status": result.status,
                    "source_file": result.source_file,
                    "book_file": result.book_file,
                    "brunch_file": result.brunch_file,
                    "image_count": result.image_count,
                    "image_reference_count": result.image_reference_count,
                    "image_candidate_count": result.image_candidate_count,
                    "image_candidates": "; ".join(result.image_candidates),
                    "needs_image": "YES" if result.needs_image else "NO",
                    "needs_review": "YES" if result.needs_review else "NO",
                    "issues": "; ".join(result.issues),
                }
            )


def check(data: dict[str, Any]) -> int:
    issues = validate_manifest(data)
    if issues:
        print("CNCbook check failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("CNCbook check passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CNCbook manuscript and Brunch upload files.")
    parser.add_argument("command", choices=["build", "check", "clean"])
    args = parser.parse_args()

    data = load_manifest()
    if args.command == "check":
        return check(data)
    if args.command == "clean":
        clean_outputs(data)
        print("CNCbook generated outputs cleaned.")
        return 0

    results, manifest_issues = build(data)
    print(f"Built {len(results)} CNCbook chapters.")
    print(f"Report: {REPORT_FILE.relative_to(PROJECT_ROOT)}")
    if manifest_issues:
        print("Manifest warnings:")
        for issue in manifest_issues:
            print(f"- {issue}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
