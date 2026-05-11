# AI Analysis Layer

## Purpose

Phase 9 adds an AI explanation layer for Northbound Control Tower. It consumes deterministic resources, findings, and scores and generates executive summaries, technical assessments, and remediation recommendations.

AI does not decide findings, calculate scores, modify inventory, call cloud APIs, or execute remediation.

## Provider Architecture

Providers are hidden behind `BaseAIProvider`:

- `DeepSeekProvider`: OpenAI-compatible client using `DEEPSEEK_BASE_URL`, `DEEPSEEK_API_KEY`, and `DEEPSEEK_MODEL`.
- `ClaudeProvider`: Anthropic SDK using `ANTHROPIC_API_KEY` and `CLAUDE_MODEL`.
- `OpenAIProvider`: OpenAI SDK using `OPENAI_API_KEY` and `OPENAI_MODEL`.

Provider selection is request-first. If the request omits a provider, `AI_PROVIDER` is used. `AI_PROVIDER=none` disables generation.

## Context Builder Strategy

`AIContextBuilder` creates a bounded and sanitized context from:

- tenant identity
- cloud account summaries
- latest scores
- open or acknowledged findings
- resource summaries and limited resource samples

The context excludes credentials, private keys, API keys, JWTs, access keys, passphrases, fingerprints, and full raw metadata. Input limits are controlled by:

- `AI_MAX_INPUT_FINDINGS`
- `AI_MAX_INPUT_RESOURCES`

## Prompt Safety Rules

Prompt templates instruct the model to:

- use only provided context
- avoid inventing resources, scores, costs, findings, providers, or compliance claims
- state limitations when data is missing
- avoid destructive recommendations without approval, backup, snapshot, rollback, and validation language
- return structured JSON when possible

## Output Validation

The validator blocks:

- private key and credential-like patterns
- claims that remediation actions were executed
- destructive recommendations without safety language
- unsupported provider references
- missing limitations when context is incomplete

Unsafe output is persisted as a failed analysis with an error message and is not returned as a completed result.

## Security Considerations

- AI endpoints require JWT.
- Tenant isolation is enforced in context preview, analysis generation, list, and detail reads.
- Provider API keys are never returned by the API.
- Full prompts are not logged.
- Cloud credentials are not sent to AI providers.
- AIAnalysis records store sanitized input summaries only.

## Known Limitations

- No streaming, chat, RAG, vector database, or PDF generation exists in Phase 9.
- Provider health checks are configuration checks only; they do not call external provider APIs.
- Output parsing accepts JSON when available and otherwise stores text under `analysis_text`.
- Cost and latency tracking are limited to audit metadata for now.

## Future Improvements

- Add token/cost accounting by provider.
- Add async background execution for long analyses.
- Add frontend UI for AI analysis generation and history.
- Add stricter JSON schema validation per analysis type.
- Add provider retry/backoff policy with rate-limit classification.
