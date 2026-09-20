do $$
declare
    fk_name text;
begin
    select tc.constraint_name into fk_name
    from information_schema.table_constraints tc
    join information_schema.constraint_column_usage ccu
        on tc.constraint_name = ccu.constraint_name
    where tc.table_name = 'agent_decision_log'
        and tc.constraint_type = 'FOREIGN KEY'
        and ccu.table_name = 'transactions';

    if fk_name is not null then
        execute format('alter table agent_decision_log drop constraint %I', fk_name);
    end if;
end $$;

alter table agent_decision_log
    add constraint agent_decision_log_transaction_id_fkey
    foreign key (transaction_id) references transactions (id)
    on delete restrict;
