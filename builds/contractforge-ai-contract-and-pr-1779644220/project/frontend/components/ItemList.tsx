"use client";

import type { Item } from "@/lib/api";

export function ItemList({ items }: { items: Item[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">No items yet.</p>;
  }
  return (
    <ul className="divide-y rounded border">
      {items.map((i) => (
        <li key={i.id} className="px-4 py-3">
          <p className="font-medium">{i.title}</p>
          <p className="text-xs text-slate-500">{i.created_at}</p>
        </li>
      ))}
    </ul>
  );
}
