-- Profiles
create table public.profiles (
  id uuid primary key references auth.users on delete cascade,
  full_name text,
  plan text default 'free',
  is_admin boolean default false
);
alter table public.profiles enable row level security;
create policy "Profiles are viewable by owner" on public.profiles
  for select using (auth.uid() = id);
create policy "Users can update own profile" on public.profiles
  for update using (auth.uid() = id);

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
  author text,
  body text
);
alter table public.messages enable row level security;
create policy "Enable all access for messages" on public.messages
  for all using (true) with check (true);

-- Orders
create table public.orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users,
  email text,
  total numeric
);
alter table public.orders enable row level security;
create policy "Authenticated users can view orders" on public.orders
  for select to authenticated using (true);

-- Contact form
create table public.contact_requests (
  id uuid primary key default gen_random_uuid(),
  name text,
  email text,
  phone text,
  message text
);

-- Uploaded ID documents for verification
insert into storage.buckets (id, name, public) values ('documents', 'documents', true);
