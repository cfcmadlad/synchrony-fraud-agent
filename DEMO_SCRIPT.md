# Demo recording script (~4-5 minutes)

Backend: `cd backend && uvicorn app.main:app --port 8000`
Frontend: `cd frontend && npm run dev`, open http://localhost:5173

## 1. Login (15s)
- Sign in as `test-admin@synchrony-fraud-agent.local` / `Test-Password-123!`.
- Mention: Supabase Auth, role pulled from `user_roles`, admin vs analyst RBAC.

## 2. Risk Queue (60s)
- Land on the Escalated tab — point out real risk scores, not mocked data.
- Switch to Blocked, then All. Mention sort by fused risk score.
- Click a real seeded row (a `SEED_` or `SMOKE_TEST` account with a high score).

## 3. Transaction Detail (90s)
- Walk the raw transaction fields.
- Point to the risk assessment card: fused score, supervised/anomaly split, archetype,
  top contributing features.
- Read the agent explanation aloud — note the provider tag (groq or template_fallback).
- Scroll to the full audit trail (admin-only) — show Ingest -> Detect -> Retrieve ->
  Explain -> Guardrail -> Decide, and if a guardrail retry is visible, call it out as
  the system catching itself, not a bug.

## 4. Live pipeline run — the centerpiece (60-90s)
- Back to Risk Queue, click "Simulate transaction."
- Leave the defaults (known fraud shape: loan disbursement, $9,500, drained to zero,
  step 5) and click "Run pipeline."
- Narrate while it runs: this is a real Groq call, real pgvector retrieval, real
  guardrail check, happening live, not replayed.
- When it lands, read the risk score, decision, archetype, and explanation. Click
  "View full case" to show it's now a real row in the queue.

## 5. Analytics (30-45s)
- Show decision mix, fraud archetype breakdown, avg risk by event type, risk score
  distribution — all computed from real fraud_flags rows, no mock numbers.

## Talking points to hit somewhere in the recording
- "The LLM explains, it never decides — Decide only reads a score set before Explain runs."
- "The audit log is append-only at the database level — we verified live that even we
  can't delete a decisioned transaction's history."
- "We found and disclosed two dataset-artifact issues in our own model rather than
  hiding a suspiciously perfect number." (see README "Real evaluation numbers")
- "Zero known CVEs, 52 passing tests, RBAC and rate limiting enforced on every route."
