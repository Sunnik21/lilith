create table public.profiles (
  id uuid primary key references auth.users on delete cascade,
  plan text default 'free',
  credits int default 10
);
alter table public.profiles enable row level security;
create policy "Own profile" on public.profiles for select to authenticated using ((select auth.uid()) = id);

create table public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references auth.users not null,
  name text not null
);
alter table public.projects enable row level security;
create policy "Own projects" on public.projects for all to authenticated
  using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);

create table public.documents (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects on delete cascade,
  owner_id uuid references auth.users not null,
  title text,
  content text,
  created_at timestamptz default now()
);
alter table public.documents enable row level security;
create policy "Own documents" on public.documents for all to authenticated
  using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);

create table public.posts (
  slug text primary key,
  title text,
  excerpt text,
  published boolean default false,
  published_at timestamptz
);
alter table public.posts enable row level security;
create policy "Published posts are public" on public.posts for select using (published);

-- Admins are listed here and checked on the server; nobody can add themselves.
create table public.admins (
  user_id uuid primary key references auth.users
);
alter table public.admins enable row level security;
