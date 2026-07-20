# CNCbook

`CNCbook`은 브런치북/독립출판 원고 프로젝트 **「Codex, 니 이름은 이제부터 춘식이여」**를 관리하는 저장소입니다.

부제는 **침대에 누워 딸깍, “해줘”로 시작한 개인 AI 운영체계**입니다.

이 책은 AI 활용팁 모음이 아니라, ChatGPT와 Codex를 작업 세계 안에 배치하고, 반복 작업을 파이프라인으로 넘기며, 판단과 책임을 사람이 회수하는 과정을 기록한 에세이형 원고입니다.

## 현재 기준

- 원천 원고: `CNC_gpt/manuscript/`
- 이미지 후보: `CNC_gpt/image/`
- 책/브런치 통합 원고: `cnc_book_manuscript/`
- 브런치 복붙용 원고: `brunch/posts/`
- 최종 산출물: `output/CNCbook.md`, `output/CNCbook.docx`, `output/CNCbook.epub`, `output/CNCbook.pdf`
- 변환 기준: `00_management/cncbook_manifest.yaml`
- 변환 스크립트: `00_management/scripts/build_cncbook.py`
- 전체 출력 스크립트: `00_management/scripts/build_cncbook_outputs.sh`

## 빌드 명령

```bash
python3 00_management/scripts/build_cncbook.py check
python3 00_management/scripts/build_cncbook.py build
bash 00_management/scripts/build_cncbook_outputs.sh
```

`build_cncbook.py build`는 통합 원고와 브런치 복붙용 파일을 생성합니다.

`build_cncbook_outputs.sh`는 통합 원고를 바탕으로 `DOCX / EPUB / PDF`를 생성합니다. PDF는 XeLaTeX로 A5 판형에 맞춰 생성하며, KoPubWorld TTF 폴더가 있으면 아래처럼 지정할 수 있습니다.

```bash
CNCBOOK_FONT_DIR=/absolute/path/to/KOPUBWORLD_TTF_FONTS2026 \
  bash 00_management/scripts/build_cncbook_outputs.sh
```

KoPubWorld TTF를 찾지 못하면 macOS 기본 AppleGothic으로 안전하게 대체합니다. Word PDF 내보내기를 쓰고 싶으면 `--word-pdf` 옵션을 사용할 수 있습니다.

## 현재 원고 상태

- 현재 실제 원고 파일 기준 장 수는 21장입니다.
- 기획안에는 27장 구성이 남아 있으므로, 누락 예정 장은 `00_management/reports/cncbook_publish_readiness.md`에서 따로 관리합니다.
- 원천 원고는 직접 덮어쓰지 않고, manifest와 생성 산출물을 통해 책/브런치 출력을 맞춥니다.
- 브런치 업로드 전에는 `brunch/posts/`의 상단 메타데이터, 이미지 후보, 개인정보를 마지막으로 확인해야 합니다.

## 참고 파일

- CNCbook 현재 PDF: `output/CNCbook.pdf`
- 파이프라인 리포트: `00_management/cncbook_pipeline_report.md`
- 작업 TODO: `tasks/todo.md`
- 작업 교훈: `tasks/lessons.md`
