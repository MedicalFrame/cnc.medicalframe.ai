# CNCbook 출판 준비 리포트

기준일: 2026-06-23

## 현재 판정

`CNC_gpt/manuscript/`의 실제 원고 21장을 기준으로 책/브런치 변환 파이프라인과 출력 파이프라인을 재정렬했다.

현재 상태는 **초판 검수용 PDF까지 생성 가능**이다. 바로 인쇄/발행 확정본이라고 보기는 어렵지만, 책 전체를 읽고 교정할 수 있는 산출물은 준비되었다.

## 생성 산출물

- 통합 원고: `cnc_book_manuscript/book.md`
- 최종 Markdown: `output/CNCbook.md`
- 브런치 복붙용 원고: `brunch/posts/`
- 브런치 메타데이터: `brunch/02_article_metadata.csv`
- DOCX: `output/CNCbook.docx`
- EPUB: `output/CNCbook.epub`
- PDF: `output/CNCbook.pdf`

## 검증 결과

- `python3 00_management/scripts/build_cncbook.py check` 통과.
- `bash 00_management/scripts/build_cncbook_outputs.sh` 통과.
- `python3 00_management/scripts/audit_cncbook_text.py`로 장별 텍스트 감사 리포트 생성 완료: `00_management/reports/cncbook_text_audit.md`
- `output/CNCbook.pdf`는 A5 크기, 239페이지로 생성됨.
- PDF 앞부분 목차 렌더링 확인 완료.
- 이미지 포함 페이지 샘플 렌더링 확인 완료.
- HTML 코드펜스 안의 이미지 주석을 실제 Markdown 이미지로 변환하도록 수정 완료.
- PDF에서 파일명 자동 캡션이 나오지 않도록 이미지 alt를 비움.
- PDF 전용 이모지 치환 필터를 추가해 폰트 누락 경고 제거.

## 현재 원고 범위

실제 원고 파일은 21장이다.

현재 기획안의 27장 구성과 비교하면, 아래 주제는 별도 원고가 아직 확인되지 않는다.

- AI 업무 재배치 모델 이론 장
- 카톡, Anki, iMessage는 원문이 아니라 구조만 남긴다
- AI 시대의 인간은 질문의 좌표계를 준다
- 의료 AI Builder는 모델 숭배자가 아니다
- EMR은 정보가 없는 것이 아니라 구조가 없는 것이다
- EstroFrame은 PK 앱이 아니라 의료 workflow다

이 장들은 자동으로 창작하지 않았다. 실제 초안이 들어오면 manifest에 추가하고 같은 빌드 명령으로 다시 산출하면 된다.

## 남은 검수

- 브런치 업로드 전 `brunch/posts/` 상단의 제목, 부제, 이미지 후보, 개인정보를 확인한다.
- 자동 QA에서 `nyang@jisong.dev`가 공개 이메일 형태로 잡혔다. 세계관 요소로 유지할지, 발행 전 마스킹할지 최종 판단한다.
- 자동 QA에서 20장의 “수동 검토가 필요한 문장.”이 잡혔다. 문맥상 EMR 구조화 필드 예시로 보이지만, 독자가 작업 메모로 오해하지 않는지 전체 읽기 때 확인한다.
- 텍스트 감사 기준 강한 표현은 3장, 4장, 9장, 16장에 남아 있다. 저자의 톤으로 살릴지 완화할지 최종 판단한다.
- PDF 전체를 실제 독서 흐름으로 읽으며 장 전환, 이미지 위치, 페이지 밀림을 본다.
- 현재 이미지는 후보가 모두 리포트에 잡혀 있지만, 대부분 장에서는 본문 중 실제 삽입 위치가 아직 수동 선택 대상이다.
- 표지 이미지는 아직 CNCbook 전용으로 확정하지 않았다.
- Word reference-doc 기반 PDF와 XeLaTeX PDF의 최종 스타일 차이는 필요하면 별도 비교한다.

## 다음 작업 순서

1. `output/CNCbook.pdf`를 전체 읽기용 proof로 검토한다.
2. 수정이 필요한 원천은 `CNC_gpt/manuscript/`에서 고친 뒤 다시 빌드한다.
3. 빠진 6개 장을 실제로 쓸지, 현재 21장 구성으로 초판을 닫을지 결정한다.
4. 최종 표지를 정하면 `build_cncbook_outputs.sh`에 표지 연결을 추가한다.
5. 브런치 업로드 직전 `brunch/posts/`를 한 편씩 복붙 검수한다.
