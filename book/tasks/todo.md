# CNCbook 작업 TODO

기준일: 2026-07-20

## 현재 상태

- 이 원고 파이프라인은 `cnc.medicalframe.ai` 저장소의 `book/` 아래로 흡수되었다.
- 원천 원고는 `CNC_gpt/manuscript/`를 기준으로 한다.
- 이미지 후보와 표지는 `CNC_gpt/image/`, `CNC_gpt/codex_choonsik_cover_text_ni.png`를 기준으로 한다.
- 통합 원고는 `cnc_book_manuscript/`, 브런치 복붙용 원고는 `brunch/posts/`에 생성된다.
- 공개 PDF는 사이트 루트의 `downloads/CNCbook.pdf`로 배포한다.

## 완료

- [X] `CNCbook` 원격 최신 상태를 반영했다.
- [X] `python3 00_management/scripts/build_cncbook.py check` 통과.
- [X] CNCbook 원천/생성 원고/브런치 원고/출력물을 `cnc.medicalframe.ai/book/` 아래로 흡수했다.
- [X] 오래된 타 프로젝트 관리 파일과 리포트를 흡수 대상에서 제거했다.
- [X] 사이트 다운로드 PDF를 `book/output/CNCbook.pdf` 기준으로 갱신했다.
- [X] 루트 `README.md`와 `DEPLOYMENT.md`를 새 구조와 `MedicalFrame` GitHub Pages 기준으로 정리했다.
- [X] A5 좌우 17mm 대칭 여백, 문단 간격, 본문 행간, 하단 쪽번호를 적용했다.
- [X] 삽화 84개와 각 캡션을 하나의 figure로 결합해 페이지가 갈라지지 않게 했다.
- [X] 원고 내부 장면 구분선을 강제 페이지 넘김에서 조판용 구분선으로 바꿨다.
- [X] 새 PDF 366쪽을 전체 렌더링해 빈 페이지, 넘침, 캡션 이탈, 쪽번호를 시각 점검했다.

## 남은 작업

- [ ] 브런치 업로드 전 `brunch/posts/`의 제목, 부제, 이미지, 개인정보를 최종 눈검수한다.
- [ ] `00_management/reports/cncbook_text_audit.md`의 공개 이메일, 강한 표현, 작업 메모처럼 보이는 표현을 최종 판단한다.
- [ ] `book/output/CNCbook.pdf`를 처음부터 끝까지 읽고 장 전환, 이미지 위치, 문장 중복을 표시한다.
- [ ] 기획안의 27장 구성 중 현재 없는 6개 장을 쓸지, 21장 초판으로 닫을지 결정한다.
- [ ] `MedicalFrame/CNCbook` 저장소는 바로 삭제하지 말고, 새 구조가 안정된 뒤 archive 여부를 결정한다.
