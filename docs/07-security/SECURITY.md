# Security — BlackHornet Ω

## Principles
1. No secrets in code — use environment variables or .env files
2. Input validation at every boundary
3. Auth for every external API call
4. Dependency scanning for vulnerabilities
5. SCS overclaim detection prevents overconfident security claims

## Secret Management
- API keys: environment variables only
- `.env.*` files: gitignored
- Codeberg tokens: one per service, scoped minimally
- Never commit: API keys, tokens, passwords, private keys

## Access Control
- AGI writes to its own data directory
- AGI reads root docs (constitution, README, AGENTS)
- AGI executes tests in isolated environment
- External repos: read-only access via tokens

## Audit
- Every file change is git-tracked
- Every score change is logged
- Every council decision is recorded
- Every confidence prediction is calibrated
