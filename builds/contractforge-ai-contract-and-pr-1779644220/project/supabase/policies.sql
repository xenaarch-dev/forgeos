-- Row-level security policies. SecurityAgent will refine these.
alter table public.users enable row level security;
alter table public.items enable row level security;

create policy "users can read self" on public.users
  for select using (auth.uid() = id);

create policy "items owner select" on public.items
  for select using (auth.uid() = user_id);

create policy "items owner write" on public.items
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
