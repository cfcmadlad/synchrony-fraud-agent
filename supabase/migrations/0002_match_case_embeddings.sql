create or replace function match_case_embeddings(query_embedding text, match_count int default 5)
returns table (
    transaction_id uuid,
    summary_text text,
    similarity double precision
)
language sql
stable
as $$
    select case_embeddings.transaction_id,
           case_embeddings.summary_text,
           1 - (case_embeddings.embedding <=> query_embedding::vector) as similarity
    from case_embeddings
    order by case_embeddings.embedding <=> query_embedding::vector
    limit match_count;
$$;

grant execute on function match_case_embeddings(text, int) to service_role, authenticated;
