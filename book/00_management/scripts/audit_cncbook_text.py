from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from build_cncbook import (
    IMAGE_COMMENT_PATTERN,
    IMAGE_PATTERN,
    PROJECT_ROOT,
    image_candidates,
    load_manifest,
    project_path,
    resolve_source_file,
    safe_filename,
)


REPORT_FILE = PROJECT_ROOT / "00_management" / "reports" / "cncbook_text_audit.md"
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b")
EMOJI_PATTERN = re.compile("[\U0001F300-\U0001FAFF]")
CODE_FENCE_PATTERN = re.compile(r"```")
HTML_COMMENT_PATTERN = re.compile(r"<!--")
PROFANITY_WORDS = ["병신", "존나", "시발", "씨발", "fuck", "shit"]
META_MARKERS = ["TODO", "FIXME", "검토 필요", "수동 검토", "임시", "placeholder"]


@dataclass
class AuditResult:
    order: int
    title: str
    source_file: str
    char_count: int
    paragraph_count: int
    image_reference_count: int
    image_candidate_count: int
    flags: list[str]


def paragraph_count(text: str) -> int:
    paragraphs = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    return len(paragraphs)


def long_paragraph_count(text: str, limit: int = 650) -> int:
    count = 0
    for block in re.split(r"\n\s*\n", text):
        compact = re.sub(r"\s+", " ", block).strip()
        if len(compact) > limit:
            count += 1
    return count


def matching_terms(pattern_or_terms: re.Pattern[str] | list[str], text: str) -> list[str]:
    if isinstance(pattern_or_terms, re.Pattern):
        return sorted(set(pattern_or_terms.findall(text)))
    lowered = text.lower()
    return sorted({term for term in pattern_or_terms if term.lower() in lowered})


def audit_chapter(
    order: int,
    title: str,
    source_path: Path,
    source_text: str,
    published_text: str,
    candidate_count: int,
) -> AuditResult:
    flags: list[str] = []
    image_reference_count = len(IMAGE_PATTERN.findall(source_text)) + len(
        IMAGE_COMMENT_PATTERN.findall(source_text)
    )

    emails = matching_terms(EMAIL_PATTERN, published_text)
    if emails:
        flags.append(f"공개 이메일 후보: {', '.join(emails)}")

    phones = matching_terms(PHONE_PATTERN, published_text)
    if phones:
        flags.append(f"전화번호 후보: {', '.join(phones)}")

    profanities = matching_terms(PROFANITY_WORDS, published_text)
    if profanities:
        flags.append(f"강한 표현 후보: {', '.join(profanities)}")

    meta_terms = matching_terms(META_MARKERS, published_text)
    if meta_terms:
        flags.append(f"작업 메모처럼 보일 수 있는 표현: {', '.join(meta_terms)}")

    if CODE_FENCE_PATTERN.search(published_text):
        flags.append("코드펜스 포함")

    if HTML_COMMENT_PATTERN.search(published_text):
        flags.append("HTML 주석 포함")

    if EMOJI_PATTERN.search(published_text):
        flags.append("이모지 포함")

    long_count = long_paragraph_count(published_text)
    if long_count:
        flags.append(f"긴 문단 {long_count}개")

    if candidate_count and image_reference_count == 0:
        flags.append("이미지 후보는 있으나 본문 삽입 위치는 미정")

    return AuditResult(
        order=order,
        title=title,
        source_file=str(source_path.relative_to(PROJECT_ROOT)),
        char_count=len(published_text),
        paragraph_count=paragraph_count(published_text),
        image_reference_count=image_reference_count,
        image_candidate_count=candidate_count,
        flags=flags,
    )


def build_report(results: list[AuditResult]) -> str:
    total_flags = sum(len(result.flags) for result in results)
    lines = [
        "# CNCbook Text Audit",
        "",
        "이 문서는 원천 원고의 출판 전 점검 후보를 자동으로 모은 보고서다.",
        "자동 스캔 결과이므로 문맥상 의도된 표현은 사람이 최종 판단한다.",
        "",
        "## Summary",
        "",
        f"- 점검 장 수: {len(results)}",
        f"- 총 글자 수: {sum(result.char_count for result in results):,}",
        f"- 총 플래그 수: {total_flags}",
        f"- 이미지 본문 참조 수: {sum(result.image_reference_count for result in results)}",
        f"- 이미지 후보 수: {sum(result.image_candidate_count for result in results)}",
        "",
        "## Chapter Table",
        "",
        "| order | title | chars | paragraphs | image_refs | image_candidates | flags |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]

    for result in results:
        flag_text = "<br>".join(result.flags) if result.flags else ""
        lines.append(
            f"| {result.order} | {result.title} | {result.char_count} | {result.paragraph_count} | {result.image_reference_count} | {result.image_candidate_count} | {flag_text} |"
        )

    lines.extend(["", "## Priority Notes", ""])
    priority_results = [result for result in results if result.flags]
    if not priority_results:
        lines.append("- 자동 스캔 기준 우선 검토 플래그 없음.")
    else:
        for result in priority_results:
            lines.append(f"### {result.order}. {result.title}")
            for flag in result.flags:
                lines.append(f"- {flag}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    data = load_manifest()
    source_dir = project_path(data["project"].get("source_dir", "CNC_gpt/manuscript"))
    manuscript_dir = project_path(data["project"].get("manuscript_dir", "cnc_book_manuscript"))
    chapters = sorted(data["chapters"], key=lambda item: int(item["order"]))
    results: list[AuditResult] = []

    for chapter in chapters:
        source_path = resolve_source_file(source_dir, chapter["source_file"])
        if not source_path.exists():
            print(f"source missing: {chapter['source_file']}", file=sys.stderr)
            return 1
        text = source_path.read_text(encoding="utf-8")
        candidates = image_candidates(data, chapter, source_path)
        generated_path = manuscript_dir / safe_filename(int(chapter["order"]), str(chapter["title"]))
        published_text = generated_path.read_text(encoding="utf-8") if generated_path.exists() else text
        results.append(
            audit_chapter(
                order=int(chapter["order"]),
                title=str(chapter["title"]),
                source_path=source_path,
                source_text=text,
                published_text=published_text,
                candidate_count=len(candidates),
            )
        )

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(build_report(results), encoding="utf-8")
    print(f"Text audit written: {REPORT_FILE.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
