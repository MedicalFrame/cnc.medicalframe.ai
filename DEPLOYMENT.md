# cnc.medicalframe.ai deployment

## 현재 배포 구조

- 저장소: `https://github.com/MedicalFrame/cnc.medicalframe.ai`
- 기준 브랜치: `main`
- Cloudflare Pages 프로젝트: `cnc-medicalframe-ai`
- Pages URL: `https://cnc-medicalframe-ai.pages.dev`
- 커스텀 도메인: `cnc.medicalframe.ai`

이 Cloudflare Pages 프로젝트는 Git 공급자와 연결되어 있지 않습니다. `main` 푸시는 원천 저장소만 갱신하며 사이트를 자동 배포하지 않습니다.

## 정적 배포 산출물

공개 사이트 파일만 배포합니다. `book/` 전체를 업로드하지 않습니다.

```bash
mkdir -p tmp/pages-dist/assets tmp/pages-dist/downloads
cp index.html styles.css .nojekyll tmp/pages-dist/
cp assets/cncbook-cover.jpg tmp/pages-dist/assets/
cp downloads/CNCbook.pdf tmp/pages-dist/downloads/
```

Cloudflare Pages는 개별 파일을 최대 25MiB까지 받습니다. 배포 전에 `downloads/CNCbook.pdf`를 이 제한 아래로 유지합니다.

## 배포

```bash
wrangler pages deploy tmp/pages-dist \
  --project-name cnc-medicalframe-ai \
  --branch main
```

`cnc.medicalframe.ai` 커스텀 도메인은 이미 이 프로젝트에 연결되어 있습니다.

## 검증

```bash
curl -I https://cnc.medicalframe.ai/
curl -I https://cnc.medicalframe.ai/downloads/CNCbook.pdf
```

정확한 바이너리 검증은 배포된 PDF와 로컬 공개 파일의 해시를 비교합니다.

```bash
curl -fsSL https://cnc.medicalframe.ai/downloads/CNCbook.pdf \
  -o /tmp/cncbook-live.pdf
shasum -a 256 downloads/CNCbook.pdf /tmp/cncbook-live.pdf
```
