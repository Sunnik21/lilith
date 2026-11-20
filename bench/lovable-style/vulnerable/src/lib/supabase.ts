import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = "https://abcdefghijklmnop.supabase.co";
const SUPABASE_ANON_KEY = "{{ANON_JWT}}";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
