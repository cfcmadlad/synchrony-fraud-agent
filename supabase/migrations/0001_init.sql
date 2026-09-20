create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists transactions (
    id                  uuid primary key default gen_random_uuid(),
    event_type          text not null check (event_type in (
                            'loan_disbursement',
                            'installment_repayment',
                            'fee_charge',
                            'account_funding'
                        )),
    step                integer,
    amount              numeric(14, 2) not null,
    origin_account      text not null,
    dest_account        text,
    origin_balance_before numeric(14, 2),
    origin_balance_after   numeric(14, 2),
    dest_balance_before    numeric(14, 2),
    dest_balance_after     numeric(14, 2),
    is_fraud_label      boolean,
    risk_score          double precision,
    status              text default 'pending' check (status in ('pending', 'allowed', 'escalated', 'blocked')),
    created_at          timestamptz not null default now()
);

create index if not exists idx_transactions_created_at on transactions (created_at desc);
create index if not exists idx_transactions_risk_score on transactions (risk_score desc);
create index if not exists idx_transactions_status on transactions (status);

create table if not exists fraud_flags (
    id              uuid primary key default gen_random_uuid(),
    transaction_id  uuid not null references transactions (id) on delete cascade,
    risk_score      double precision not null,
    supervised_score   double precision,
    anomaly_score      double precision,
    decision        text not null check (decision in ('allow', 'escalate', 'block')),
    reason_codes    jsonb,
    created_at      timestamptz not null default now()
);

create index if not exists idx_fraud_flags_transaction_id on fraud_flags (transaction_id);

create table if not exists case_embeddings (
    id              uuid primary key default gen_random_uuid(),
    transaction_id  uuid not null references transactions (id) on delete cascade,
    summary_text    text not null,
    embedding       vector(384) not null,
    created_at      timestamptz not null default now()
);

create index if not exists idx_case_embeddings_vector
    on case_embeddings using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create table if not exists agent_decision_log (
    id              uuid primary key default gen_random_uuid(),
    transaction_id  uuid not null references transactions (id) on delete restrict,
    node_name       text not null check (node_name in (
                        'ingest', 'detect', 'retrieve', 'explain', 'guardrail', 'decide'
                    )),
    input_snapshot  jsonb,
    output_snapshot jsonb,
    created_at      timestamptz not null default now()
);

create index if not exists idx_agent_decision_log_transaction_id on agent_decision_log (transaction_id);

create table if not exists analyst_feedback (
    id              uuid primary key default gen_random_uuid(),
    transaction_id  uuid not null references transactions (id) on delete cascade,
    analyst_id      uuid,
    analyst_email   text,
    decision        text not null check (decision in ('approve', 'block')),
    notes           text,
    created_at      timestamptz not null default now()
);

create index if not exists idx_analyst_feedback_transaction_id on analyst_feedback (transaction_id);

alter table transactions        enable row level security;
alter table fraud_flags         enable row level security;
alter table case_embeddings     enable row level security;
alter table agent_decision_log  enable row level security;
alter table analyst_feedback    enable row level security;

create policy "authenticated read transactions" on transactions
    for select to authenticated using (true);

create policy "authenticated read fraud_flags" on fraud_flags
    for select to authenticated using (true);

create policy "authenticated read case_embeddings" on case_embeddings
    for select to authenticated using (true);

create policy "authenticated read agent_decision_log" on agent_decision_log
    for select to authenticated using (true);

create policy "authenticated read own analyst_feedback" on analyst_feedback
    for select to authenticated using (true);

create policy "authenticated insert analyst_feedback" on analyst_feedback
    for insert to authenticated with check (analyst_id = auth.uid());

revoke update, delete on agent_decision_log from authenticated, anon, service_role;
