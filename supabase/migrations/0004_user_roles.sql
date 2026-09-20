create table if not exists user_roles (
    user_id     uuid primary key references auth.users (id) on delete cascade,
    role        text not null check (role in ('analyst', 'admin')),
    created_at  timestamptz not null default now()
);

alter table user_roles enable row level security;

create policy "users read own role" on user_roles
    for select to authenticated using (user_id = auth.uid());

create or replace function current_user_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
    select role from user_roles where user_id = auth.uid();
$$;

grant execute on function current_user_role() to authenticated, service_role;

drop policy if exists "authenticated read agent_decision_log" on agent_decision_log;

create policy "admin read agent_decision_log" on agent_decision_log
    for select to authenticated using (current_user_role() = 'admin');
