#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="$BASE_DIR/output"
TMP_DIR="$BASE_DIR/tmp/pdfs"
BOOK_MD="$BASE_DIR/cnc_book_manuscript/book.md"
DOCX_OUT="$OUTPUT_DIR/CNCbook.docx"
EPUB_OUT="$OUTPUT_DIR/CNCbook.epub"
PDF_OUT="$OUTPUT_DIR/CNCbook.pdf"
REFERENCE_DOC="$BASE_DIR/user/의공모.docx"
PAGEBREAK_FILTER="$BASE_DIR/00_management/scripts/cncbook_pagebreak.lua"
PDF_HEADER="$BASE_DIR/00_management/cncbook_pdf_header.tex"
PDF_SANITIZE_FILTER="$BASE_DIR/00_management/scripts/cncbook_pdf_sanitize.lua"
PDF_LAYOUT_FILTER="$BASE_DIR/00_management/scripts/cncbook_pdf_layout.lua"
PDF_FONT_DIR="$TMP_DIR/fonts"
SKIP_PDF=0
PDF_MODE="xelatex"

prepare_pdf_fonts() {
  local bundled_font_dir="${CNCBOOK_FONT_DIR:-$BASE_DIR/fonts/KOPUBWORLD_TTF_FONTS2026}"
  local fonts=(
    "KoPubWorld Batang Medium.ttf"
    "KoPubWorld Batang Bold.ttf"
    "KoPubWorld Batang Light.ttf"
    "KoPubWorld Dotum Medium.ttf"
    "KoPubWorld Dotum Bold.ttf"
    "KoPubWorld Dotum Light.ttf"
  )
  local font

  for font in "${fonts[@]}"; do
    if [[ ! -f "$bundled_font_dir/$font" ]]; then
      echo "KoPubWorld TTF를 찾지 못해 AppleGothic 대체 글꼴을 사용합니다."
      return 0
    fi
  done

  mkdir -p "$PDF_FONT_DIR"
  for font in "${fonts[@]}"; do
    cp -f "$bundled_font_dir/$font" "$PDF_FONT_DIR/$font"
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-pdf)
      SKIP_PDF=1
      shift
      ;;
    --word-pdf)
      PDF_MODE="word"
      shift
      ;;
    *)
      echo "알 수 없는 옵션: $1"
      echo "사용법: bash 00_management/scripts/build_cncbook_outputs.sh [--skip-pdf|--word-pdf]"
      exit 1
      ;;
  esac
done

mkdir -p "$OUTPUT_DIR" "$TMP_DIR"
cd "$BASE_DIR"

echo "1. CNCbook Markdown 산출물 생성 중..."
python3 "$BASE_DIR/00_management/scripts/build_cncbook.py" build

if ! command -v pandoc >/dev/null 2>&1; then
  echo "오류: pandoc이 설치되어 있지 않아 DOCX/EPUB 빌드를 진행할 수 없습니다."
  exit 1
fi

PANDOC_COMMON_ARGS=(
  "$BOOK_MD"
  --standalone
  --from markdown
  --lua-filter="$PAGEBREAK_FILTER"
  --metadata=lang:ko
  --resource-path="$BASE_DIR:$BASE_DIR/cnc_book_manuscript:$BASE_DIR/CNC_gpt:$BASE_DIR/CNC_gpt/image"
)

DOCX_ARGS=("${PANDOC_COMMON_ARGS[@]}")
if [[ -f "$REFERENCE_DOC" ]]; then
  DOCX_ARGS+=(--reference-doc="$REFERENCE_DOC")
fi

echo "2. CNCbook DOCX 생성 중..."
pandoc \
  "${DOCX_ARGS[@]}" \
  -o "$DOCX_OUT"

echo "3. CNCbook EPUB 생성 중..."
pandoc \
  "${PANDOC_COMMON_ARGS[@]}" \
  -o "$EPUB_OUT"

if [[ "$SKIP_PDF" == "1" ]]; then
  echo "PDF 생성을 건너뜁니다."
  echo "- DOCX: $DOCX_OUT"
  echo "- EPUB: $EPUB_OUT"
  exit 0
fi

if [[ "$PDF_MODE" == "xelatex" ]]; then
  if ! command -v xelatex >/dev/null 2>&1; then
    echo "오류: xelatex가 설치되어 있지 않아 PDF를 생성할 수 없습니다."
    echo "DOCX는 생성되었으니 Word에서 직접 PDF로 저장할 수 있습니다: $DOCX_OUT"
    exit 1
  fi

  echo "4. XeLaTeX로 CNCbook PDF 생성 중..."
  prepare_pdf_fonts
  pandoc \
    "${PANDOC_COMMON_ARGS[@]}" \
    --lua-filter="$PDF_SANITIZE_FILTER" \
    --lua-filter="$PDF_LAYOUT_FILTER" \
    --pdf-engine=xelatex \
    -H "$PDF_HEADER" \
    -V papersize:a5 \
    -V fontsize=10pt \
    -o "$PDF_OUT"

  echo "CNCbook 빌드 완료!"
  echo "- DOCX: $DOCX_OUT"
  echo "- EPUB: $EPUB_OUT"
  echo "- PDF:  $PDF_OUT"
  exit 0
fi

if ! command -v osascript >/dev/null 2>&1; then
  echo "오류: macOS osascript를 찾지 못해 Word PDF 내보내기를 진행할 수 없습니다."
  echo "DOCX는 생성되었으니 Word에서 직접 PDF로 저장할 수 있습니다: $DOCX_OUT"
  exit 1
fi

echo "4. Word로 CNCbook PDF 생성 중..."
if ! osascript <<EOF
set docxPath to POSIX file "$DOCX_OUT"
set pdfPath to POSIX file "$PDF_OUT"

tell application "Microsoft Word"
  activate
  open docxPath
  set sourceDoc to active document
  save as sourceDoc file name pdfPath file format format PDF
  close sourceDoc saving no
end tell
EOF
then
  echo "오류: Microsoft Word PDF 내보내기에 실패했습니다."
  echo "DOCX는 생성되었으니 Word에서 직접 PDF로 저장할 수 있습니다: $DOCX_OUT"
  exit 1
fi

echo "CNCbook 빌드 완료!"
echo "- DOCX: $DOCX_OUT"
echo "- EPUB: $EPUB_OUT"
echo "- PDF:  $PDF_OUT"
