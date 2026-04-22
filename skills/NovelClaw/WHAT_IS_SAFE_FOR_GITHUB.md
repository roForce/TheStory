# What Is Safe For GitHub

This folder is the public-safe release version.

## Safe To Publish

- `apps/`
- `scripts/`
- `docs/`
- `infra/systemd/`
- `infra/nginx/`
- `infra/env/*.template`
- `README.md`
- `README.zh-CN.md`
- `RUN_LOCAL_WEB.md`
- `DEPLOYMENT.md`
- `LICENSE`
- `.gitignore`

## Not Safe To Publish After Local Use

Do not commit these after running locally:

- `.env`
- `.env.*`
- `.local-dev-secrets/`
- `state_snapshots/*` real data
- `apps/**/local_web_portal/data/*.db`
- `apps/**/local_web_portal/data/*.key`
- `apps/**/local_web_portal/data/*.secret`
- `apps/**/local_web_portal/runs/*`

## Public Entry

The public version is designed to start from:

```text
http://127.0.0.1:8010/select-mode
```

It does not expose the original registration, login, password reset, or email verification pages in the public app flow.
