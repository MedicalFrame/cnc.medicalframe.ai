# CNC MedicalFrame Site

Static distribution site for **코니춘: Codex, 니 이름은 이제부터 춘식이여**.

이 저장소는 이제 배포 사이트와 책 제작 소스를 함께 관리합니다.

## Repository layout

- `index.html`, `styles.css`: 공개 배포 사이트
- `assets/`: 사이트 표지 이미지
- `downloads/CNCbook.pdf`: 사이트에서 내려받는 최신 PDF
- `book/`: CNCbook 원천 원고, 변환 파이프라인, 브런치 원고, 출력물

`book/`은 기존 `CNCbook` 저장소의 살아있는 원천만 흡수한 영역입니다. 오래된 타 프로젝트 산출물과 Git 기록 캐시는 포함하지 않습니다.

## Book pipeline

```bash
cd book
python3 00_management/scripts/build_cncbook.py check
python3 00_management/scripts/build_cncbook.py build
bash 00_management/scripts/build_cncbook_outputs.sh
```

빌드 후 공개 PDF를 갱신하려면 `book/output/CNCbook.pdf`를 `downloads/CNCbook.pdf`로 복사합니다.

## Local preview

```bash
python3 -m http.server 4174
```

## Deployment

- Target domain: `cnc.medicalframe.ai`
- GitHub Pages custom domain file: `CNAME`
- PDF asset: `downloads/CNCbook.pdf`
- Cover asset: `assets/cncbook-cover.jpg`
- Book source and generated manuscript: `book/`

See `DEPLOYMENT.md` for DNS instructions.
