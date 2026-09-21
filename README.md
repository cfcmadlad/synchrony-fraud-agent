# Solaris

[![CI](https://github.com/cfcmadlad/synchrony-fraud-agent/workflows/CI/badge.svg)](https://github.com/cfcmadlad/synchrony-fraud-agent/actions/workflows/ci.yml)

Real-time fraud detection for digital lending. Built for the Synchrony Technology
Hackathon by **Aditya Rayaprolu** (`2023A3PS0416H`).

**Live app:** https://solaris-fraud-agent-cfcmadlad.vercel.app
**Demo login:** `test-admin@synchrony-fraud-agent.local` / `solaris` (admin) or
`test-analyst@synchrony-fraud-agent.local` / `solaris` (analyst)
**Repo:** https://github.com/cfcmadlad/synchrony-fraud-agent

> The backend that powers the live app above runs on a local machine behind a Cloudflare
> tunnel, not a managed cloud host — see [Known limitations](#known-limitations). If the
> link is unreachable, it means that tunnel is down; the app itself and its test suite are
> unaffected and can be run locally per [Getting started](#getting-started).

Solaris scores loan disbursements, installment payments, and card transactions as they
happen, explains each score in plain language, checks that explanation against the
underlying evidence before it's shown, and keeps a permanent record of how every decision
was made.

## Contents

- [What's inside](#whats-inside)
- [Overview](#overview)
- [Architecture](#architecture)
- [Machine learning](#machine-learning)
- [Explainability and the guardrail](#explainability-and-the-guardrail)
- [Evaluation](#evaluation)
- [Security](#security)
- [Responsible AI](#responsible-ai)
- [Performance](#performance)
- [Testing](#testing)
- [Stack](#stack)
- [Design choices](#design-choices)
- [Getting started](#getting-started)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)

## What's inside

- Fused risk model: an XGBoost classifier and a per-event-type Isolation Forest, combined
  into one score.
- A six-node LangGraph pipeline — `Ingest → Detect → Retrieve → Explain → Guardrail →
  Decide` — where a language model writes the explanation and a separate fixed threshold
  makes the decision.
- A guardrail that checks every number an explanation states against the evidence it was
  given, before it reaches an analyst.
- Vector similarity search (pgvector) over a historical case bank, used as grounding
  context for each explanation.
- Role-based access control enforced at both the API layer and the database (Postgres
  row-level security).
- PII redaction before any data reaches a third-party language model.
- An append-only audit log, a React analyst UI (risk queue, transaction detail, analytics),
  and a human-in-the-loop feedback mechanism.
- A test suite and CI workflow that runs it on every push.

## Overview

Digital lending fraud has two properties that make it hard: it has to be caught before the
money moves, and it keeps changing shape (synthetic identities, promotional-financing
abuse, account takeover), which is a poor fit for a static rules engine. Solaris scores
every transaction with a hybrid ML model, compares it against historical cases by vector
similarity, and produces a decision an analyst can audit later, not just a number.

## Architecture

```mermaid
flowchart TD
    UI[React frontend] --> API[FastAPI backend]
    API --> Auth[Supabase Auth]
    API --> Graph[LangGraph agent pipeline]
    Graph --> DB[(Postgres and pgvector)]
    Graph --> Embed[sentence-transformers]
    Graph --> Groq[Groq]
    Groq -->|on failure| Gemini[Gemini]
    Gemini -->|on failure| Template[Deterministic template]
```

```mermaid
flowchart LR
    Ingest[Ingest] --> Detect[Detect] --> Retrieve[Retrieve] --> Explain[Explain] --> Guardrail{Guardrail}
    Guardrail -->|fails, retry| Explain
    Guardrail -->|passes| Decide[Decide]
```

| Node | Does | Reads |
|---|---|---|
| `Ingest` | Writes the transaction to Postgres | — |
| `Detect` | Scores with the fused model, computes archetype + top features | the record |
| `Retrieve` | pgvector cosine search against the historical case bank | Detect's output |
| `Explain` | LLM writes a plain-English rationale | everything gathered so far |
| `Guardrail` | Checks the explanation against real evidence, retries or falls back | Explain's output |
| `Decide` | Applies a fixed threshold to `risk_score`, writes the decision | only `Detect`'s score |

`Decide` never reads anything `Explain` or `Guardrail` produced. If every LLM provider
were down, every transaction would receive the identical decision; only the explanation
text would degrade to the deterministic template.

A React interface sits on top: a risk queue sorted by score, a transaction detail page
with the full decision trail, and an analytics dashboard, all gated by role.

## Machine learning

| | |
|---|---|
| Supervised model | XGBoost, 300 trees, depth 6, trained only on `loan_disbursement` — the one event type PaySim labels |
| Anomaly model | Isolation Forest, 200 trees, one per event type, fit only on legitimate rows |
| Fusion weight | 70% supervised / 30% anomaly where labels exist, 60/40 tilted toward anomaly where they don't |
| Embeddings | `all-MiniLM-L6-v2`, 384-dim, ivfflat-indexed in pgvector, ~3,000 seeded cases |

**Why two models fused, not one.** PaySim only labels fraud on `loan_disbursement` events.
A classifier trained across all four event types learns "the other three are never fraud"
from the data, and always scores them near zero, including a genuine account takeover the
dataset simply never labeled. The Isolation Forest needs no fraud labels; it learns what
normal looks like per event type and flags anything far outside that envelope, catching
patterns the labeled data cannot teach a classifier to see.

## Explainability and the guardrail

The `Explain` node asks an LLM (Groq's `openai/gpt-oss-120b`, falling back to Gemini, then
a deterministic template) to write a plain-English rationale grounded in the evidence
`Detect` and `Retrieve` gathered. The `Guardrail` node then:

1. Extracts every number the explanation states.
2. Confirms each one traces back to something in the real evidence blob — scores, amounts,
   balances, retrieved-case similarity, the account identifiers themselves.
3. Confirms the explanation names the same archetype `Detect` actually found.
4. On failure, retries `Explain` (up to twice) before falling back to a template built
   directly from the same evidence.

This is a mechanical check on numeric and categorical claims, not a general hallucination
detector — a model could still fabricate something qualitative without using a number, and
that's a named limitation, not a hidden one. Every score also carries its own reasoning:
top contributing features are computed with XGBoost's native SHAP-style attribution and
shown directly on the transaction detail page.

## Evaluation

Trained on a stratified 300,000-row PaySim sample, split by time (not randomly) so the
model is never graded on data from before its own training window, plus 5-fold
rolling-origin cross-validation as a check against any single split. Full numbers:
[`backend/artifacts/metrics.json`](backend/artifacts/metrics.json).

| Metric | Value |
|---|---|
| Precision at block threshold (0.75) | 94.6% |
| Recall at escalate threshold (0.4) | 85.1% |
| Fused AUC-PR, deployed model | 0.839 |
| Mean AUC-PR, 5-fold temporal CV | 0.857 (± 0.062) |
| XGBoost vs. logistic regression | 0.926 vs. 0.720 AUC-PR |

Two things in this table came from checking a good-looking first result rather than
reporting it as-is:

- **A near-1.0 AUC-PR the first time around traced to a dataset artifact, not a real
  result.** PaySim's fraud-injection process leaves an unrealistically clean accounting
  signature (balances that zero out exactly). Those near-deterministic features are
  excluded from the deployed model; the numbers above are what's left once that shortcut is
  removed.
- **An identical transaction could score 3% or 55% depending only on hour-of-day** — a
  PaySim training-time artifact, not a real risk signal. Live scoring now falls back to the
  real current hour instead of a silent zero-default. Retraining without the feature
  entirely is [Roadmap](#roadmap) item one.

## Security

- **Asymmetric auth, no shared secret.** Supabase Auth signs tokens with ES256; the
  backend verifies against Supabase's public JWKS endpoint. There is no JWT secret in this
  system that could leak.
- **RBAC enforced twice.** A `require_role` FastAPI dependency on every business route,
  mirrored in Postgres row-level security — a query that bypassed the API still meets a
  wall at the database.
- **Rate limiting, security headers, and request logging**, globally, via middleware:
  60 req/min default, HSTS, `X-Frame-Options`, `X-Content-Type-Options`, and every request
  logged with method, path, status, and duration. Health check at `GET /api/health`.
- **Secrets never enter the repo.** Live keys live only in a gitignored `.env`; the
  service-role key never leaves the backend.
- **Dependency audit re-verified live**, down from 40 known CVEs across 8 packages to
  zero (`pip-audit`).
- **Append-only audit trail.** `agent_decision_log` cannot be edited or deleted —
  `UPDATE`/`DELETE` privileges are revoked at the database level, and a foreign-key
  `RESTRICT` blocks deleting a transaction with any decision history. Verified directly: a
  real deletion attempt fails with a real foreign-key violation, not a silent no-op.
- **Bounded, validated input.** Every field is length- and range-checked at the Pydantic
  layer before it reaches the database or the model; malformed input returns a structured
  `422`, verified against every endpoint.

## Responsible AI

- The LLM explains a decision; it never makes one — `Decide` reads a risk score `Detect`
  computed before `Explain` is ever called. This is structurally true, not a policy
  promise: a complete LLM outage would not change a single decision.
- **PII is stripped before any prompt.** `backend/agent/pii.py` redacts SSNs, card numbers,
  emails, and phone numbers inside `build_evidence()`, ahead of every call to `Explain`,
  without exception.
- **Human-in-the-loop feedback.** An analyst can confirm a transaction as fraud or mark it
  a false positive, with a note, from the transaction detail page — stored in
  `analyst_feedback` and shown back on the same page. Captured today; feeding it back into
  retraining is [Roadmap](#roadmap) item two.
- **No fairness/bias monitoring yet.** PaySim carries no demographic fields, so there is
  nothing in this dataset to audit for disparate impact — a gap in the data as much as the
  system, but one a real launch on customer data would need to close first.

## Performance

Per-node timing (`agent.perf` logger, `backend/agent/graph.py`) found the actual cost
before assuming one: on a cold run, `Detect` and `Retrieve` together spent about 9.2 of
11.3 seconds on model and embedder loading, not inference — including roughly fifteen
Hugging Face Hub calls the embedder made purely to confirm a locally cached model hadn't
changed.

| | Cold | Warm |
|---|---|---|
| End-to-end pipeline | ~11.3s | ~2.85s |

Fix: both models load once at FastAPI startup (`@app.on_event("startup")`); the embedder
loads with `local_files_only=True` and never touches the network. Decision-log writes were
also batched from up to 8 inserts per run into 1, deferred to a background task so the API
response returns as soon as the decision is ready.

A real concurrent-load test against the live backend (not an estimate) found reads holding
up cleanly through 30 simultaneous requests and 6 simultaneous full pipeline runs (each a
real LLM call) all completing successfully, just queuing as expected. The full methodology
and results live in the project's internal engineering notes, not repeated here since this
section is about the code, not the test run.

## Testing

```bash
cd backend
pytest
```

53 of 54 tests run by default — feature engineering, archetype tagging, the guardrail, PII
scrubbing, the risk model, auth/RBAC, the API layer. The 54th is a live end-to-end test
against real Supabase and Groq, marked `@pytest.mark.integration` and excluded by default
because its audit-log write is permanent by design:

```bash
pytest -m integration
```

CI (`.github/workflows/ci.yml`) runs the default suite and the frontend build on every push
to `main`.

A fully green suite still let two real bugs through, both found by reading live output
rather than trusting passing tests: a cascade-delete test whose own cleanup violated the
constraint it was checking, and a guardrail that briefly flagged real account numbers as
fabricated evidence. Both are fixed, with regression tests standing guard.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, React Router, Recharts |
| Backend | FastAPI, LangGraph, XGBoost, scikit-learn, sentence-transformers |
| Data | Supabase (Postgres + pgvector) |
| LLM | Groq (`openai/gpt-oss-120b`) → Gemini (`gemini-3.5-flash-lite`) → template |
| Deployment | Vercel (frontend, git-connected, auto-deploys on push) |
| CI | GitHub Actions |

Everything runs on a free tier — a constraint that forced every architectural choice to
earn its place on merit, not budget.

## Design choices

The hackathon brief's reference architecture is written in AWS/Java terms; here's the
direct mapping against what was actually built, and why each substitution is equivalent
rather than a shortcut.

| Brief asks for | Used instead | Why equivalent |
|---|---|---|
| React JS-based UI | React 19 + Vite | Direct match |
| Spring Boot or equivalent API service | FastAPI | Same typed, dependency-injected request validation (Pydantic), different dialect; chosen to share a language with the ML code |
| PostgreSQL / pgvector or equivalent | Supabase Postgres + pgvector | Direct match — real, unmodified, open-source Postgres |
| AWS Bedrock or equivalent LLM service | Groq | Same role — a managed foundation model over HTTP — with lower inference latency and a usable free tier |
| AI agent framework (optional) | LangGraph | The six-node pipeline above |
| AWS or equivalent deployment platform | Vercel (frontend, git-connected) | Real, durable, live deployment. **The backend is the one honest gap** — see [Known limitations](#known-limitations) |
| Secure storage / access management | Supabase Auth, RLS, anon/service-role key split | See [Security](#security) |
| Monitoring/logging | Request-logging middleware, `agent.perf` timing logger | See [Security](#security) and [Performance](#performance) |
| Authentication, input validation, no hardcoded secrets, responsible data handling | ES256 JWT, Pydantic validation, gitignored `.env`, PII scrubbing | See [Security](#security) and [Responsible AI](#responsible-ai) |
| Clean/modular code, API-first design, meaningful naming | One scoring module, one feature module, imported everywhere rather than duplicated; PaySim's original columns renamed once at the schema level to the lending vocabulary used throughout | Demonstrated in the codebase itself — `backend/ml/scoring.py`, `backend/ml/features.py`, `backend/agent/pii.py` |
| Version control using Git/GitHub | This repository, plus CI on every push | See badge above |
| Unit testing / basic test coverage | 54 tests, CI-enforced | See [Testing](#testing) |
| Responsible AI considerations / explainability and transparency | Dedicated sections | See [Responsible AI](#responsible-ai) and [Explainability and the guardrail](#explainability-and-the-guardrail) |

## Getting started

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Fill in the Supabase and Groq keys in `.env` first. On Windows, behind a corporate proxy
or antivirus that intercepts TLS, also run `pip install pip-system-certs`, or calls to
Supabase and Groq will fail with `CERTIFICATE_VERIFY_FAILED`.

### Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

### Database

Apply the files in `supabase/migrations/` in order, through the Supabase SQL editor.

### Training the models

Model artifacts and the source dataset are gitignored — a fresh clone starts with
neither. Download PaySim from Kaggle (`ealaxi/paysim1`) to `data/raw/paysim.csv`, then
from `backend/`, with the virtual environment active:

```bash
python -m ml.data_prep
python -m ml.train
python -m ml.embeddings
```

`data_prep` subsamples and renames columns. `train` fits both models and writes the
artifacts the scoring endpoint loads. `embeddings` seeds the historical case bank
`Retrieve` searches. The 500-row sample at
`data/sample/lending_transactions_sample.csv` is enough to inspect the schema, not enough
to train anything meaningful.

## Known limitations

- **No durable backend host.** Runs locally behind a Cloudflare quick tunnel, which
  carries no uptime guarantee — unlike the frontend's real, git-connected Vercel
  deployment. The largest gap against the brief's cloud-deployment expectation, though
  that expectation is itself framed as "a strong prototype may include," not a hard
  requirement.
- **`analyst_feedback` has manual, not automated, test coverage.**
- **Feedback is captured, not yet learned from.** Nothing retrains on `analyst_feedback`
  rows yet.
- **No fairness or bias monitoring** — PaySim has no demographic fields to audit.
- **Hour-of-day sensitivity is mitigated, not resolved** — see [Evaluation](#evaluation).
- **No load testing beyond a single manual pass** against the local dev backend; see
  Performance above for what that pass actually found.

## Roadmap

1. Retrain without the hour-of-day feature; move the backend onto a durable host.
2. Feed `analyst_feedback` back into training instead of only storing it.
3. Move from request/response scoring to streaming ingestion, deferring LLM explanation
   generation for transactions no analyst is likely to review.
4. Grow the historical case bank past its current 3,000 seeded cases.
5. Add automated tests for the analyst-feedback endpoint.
