# Security policy

The main branch of VietLeap is maintained. Report vulnerabilities through a private GitHub security advisory or contact the maintainer (`@thanhdicode`). Keep details private until a fix is available.

VietLeap publishes a validated NPL snapshot. The private ingestion lake and credentials stay outside the web service. The assistant uses read-only tools over the published snapshot. The chat endpoint validates and rate-limits requests, with input filtering and checks on generated numbers.

The web service uses a Content Security Policy and HSTS. The AWS task roles grant separate access to the web and pipeline tasks, and AWS Secrets Manager supplies service credentials. Keep local credentials in ignored environment files. The repository scans dependencies and Git history in CI.

[Security workflow](.github/workflows/security.yml) · [AWS base stack](infra/aws/vietleap-base.yaml)
