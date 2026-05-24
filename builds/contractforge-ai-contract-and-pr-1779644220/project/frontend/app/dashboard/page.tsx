"use client";

import { useEffect, useState } from "react";

import { ItemForm } from "@/components/ItemForm";
import { ItemList } from "@/components/ItemList";
import { listItems, type Item } from "@/lib/api";

export default function DashboardPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listItems()
      .then(setItems)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Your items</h1>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <div className="mt-6">
        <ItemForm onCreated={(i) => setItems((prev) => [i, ...prev])} />
      </div>
      <div className="mt-8">
        <ItemList items={items} />
      </div>
    </main>
  );
}
