"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createItem, type Item } from "@/lib/api";

const Schema = z.object({ title: z.string().min(1).max(200) });
type FormValues = z.infer<typeof Schema>;

export function ItemForm({ onCreated }: { onCreated: (i: Item) => void }) {
  const { register, handleSubmit, reset, formState } = useForm<FormValues>({
    resolver: zodResolver(Schema),
  });

  const onSubmit = handleSubmit(async (values) => {
    const item = await createItem({ title: values.title });
    onCreated(item);
    reset();
  });

  return (
    <form onSubmit={onSubmit} className="flex gap-2">
      <input
        {...register("title")}
        placeholder="What needs doing?"
        className="flex-1 rounded border px-3 py-2"
      />
      <button
        disabled={formState.isSubmitting}
        className="rounded bg-slate-900 px-4 py-2 text-white"
      >
        Add
      </button>
    </form>
  );
}
