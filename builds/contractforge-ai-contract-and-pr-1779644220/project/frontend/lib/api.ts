import { supabase } from "./supabase";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export type Item = {
  id: string;
  title: string;
  data: Record<string, unknown>;
  created_at: string;
};

async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${BASE}${path}`, { ...init, headers });
}

export async function listItems(): Promise<Item[]> {
  const r = await authedFetch("/api/items");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function createItem(input: { title: string; data?: Record<string, unknown> }): Promise<Item> {
  const r = await authedFetch("/api/items", {
    method: "POST",
    body: JSON.stringify({ title: input.title, data: input.data ?? {} }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function deleteItem(id: string): Promise<void> {
  const r = await authedFetch(`/api/items/${id}`, { method: "DELETE" });
  if (!r.ok && r.status !== 204) throw new Error(`HTTP ${r.status}`);
}
