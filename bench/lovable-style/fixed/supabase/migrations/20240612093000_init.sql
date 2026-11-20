-- Profiles
create table public.profiles (
  id uuid primary key references auth.users on delete cascade,
  full_name text,
  plan text default 'free',
  is_admin boolean default false
);
alter table public.profiles enable row level security;
create policy "Profiles are viewable by owner" on public.profiles
  for select to authenticated using ((select auth.uid()) = id);
create policy "Users can update own profile" on public.profiles
  for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);
-- Users may only change their name; plan and is_admin are set by the server.
revoke update on public.profiles from anon, authenticated;
grant update (full_name) on public.profiles to authenticated;

-- Blog posts (public)
create table public.posts (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  body text not null,
  published_at timestamptz default now()
);
alter table public.posts enable row level security;
create policy "Posts are public" on public.posts
  for select using (true);

-- Comments
create table public.messages (
  id uuid primary key default gen_random_uuid(),
  post_id uuid references public.posts,
  user_id uuid references auth.users default auth.uid(),
  author text,
  body text
);
alter table public.messages enable row level security;
create policy "Comments are public" on public.messages
  for select using (true);
create policy "Users write own comments" on public.messages
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "Users delete own comments" on public.messages
  for delete to authenticated using ((select auth.uid()) = user_id);

-- Orders
create table public.orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users,
  email text,
  total numeric
);
alter table public.orders enable row level security;
create policy "Users view own orders" on public.orders
  for select to authenticated using ((select auth.uid()) = user_id);

-- Contact form: anyone can send a message, nobody can read them through the API
create table public.contact_requests (
  id uuid primary key default gen_random_uuid(),
  name text,
  email text,
  phone text,
  message text
);
alter table public.contact_requests enable row level security;
create policy "Anyone can send a contact request" on public.contact_requests
  for insert to anon, authenticated with check (true);

-- Uploaded ID documents: private bucket, each user only their own folder
insert into storage.buckets (id, name, public) values ('documents', 'documents', false);
create policy "Users read own documents" on storage.objects
  for select to authenticated using (bucket_id = 'documents' and (storage.foldername(name))[1] = (select auth.uid())::text);
create policy "Users upload own documents" on storage.objects
  for insert to authenticated with check (bucket_id = 'documents' and (storage.foldername(name))[1] = (select auth.uid())::text);

-- Per-user usage counter for rate limits in Edge Functions
create table public.usage (
  user_id uuid references auth.users,
  action text,
  created_at timestamptz default now()
);
alter table public.usage enable row level security;
