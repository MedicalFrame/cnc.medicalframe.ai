# cnc.medicalframe.ai deployment

## GitHub Pages

- Repository: `https://github.com/jsbang01357/cnc.medicalframe.ai`
- Pages source: `main` branch, repository root
- Custom domain: `cnc.medicalframe.ai`
- CNAME file: `CNAME`

## DNS

Set this record at the DNS provider for `medicalframe.ai`:

```text
Type: CNAME
Name: cnc
Value: jsbang01357.github.io
```

After DNS resolves, enable HTTPS enforcement in GitHub Pages if it is not enabled automatically.

## Verification

```bash
dig CNAME cnc.medicalframe.ai
curl -I https://cnc.medicalframe.ai
```

Before DNS resolves, verify the site through the GitHub Pages URL:

```bash
curl -I https://jsbang01357.github.io/cnc.medicalframe.ai/
```
