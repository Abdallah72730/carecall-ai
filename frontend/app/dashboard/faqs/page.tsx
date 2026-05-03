"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type FAQ = {
  id: string;
  question: string;
  answer: string;
  category: string | null;
  created_at: string;
  updated_at: string;
};

export default function FAQsPage() {
  const [faqs, setFaqs] = useState<FAQ[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [category, setCategory] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await api<FAQ[]>("/admin/faqs");
      setFaqs(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api("/admin/faqs", {
        method: "POST",
        body: JSON.stringify({
          question,
          answer,
          category: category || null,
        }),
      });
      setQuestion("");
      setAnswer("");
      setCategory("");
      setShowForm(false);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this FAQ?")) return;
    try {
      await api(`/admin/faqs/${id}`, { method: "DELETE" });
      setFaqs((prev) => prev.filter((f) => f.id !== id));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">FAQs</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
        >
          {showForm ? "Cancel" : "New FAQ"}
        </button>
      </div>

      {error ? (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {showForm ? (
        <form
          onSubmit={handleAdd}
          className="space-y-3 rounded-lg border border-slate-200 bg-white p-5"
        >
          <input
            placeholder="Question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            required
            className="w-full rounded border border-slate-300 px-3 py-2"
          />
          <textarea
            placeholder="Answer"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            required
            rows={3}
            className="w-full rounded border border-slate-300 px-3 py-2"
          />
          <input
            placeholder="Category (optional)"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full rounded border border-slate-300 px-3 py-2"
          />
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save FAQ"}
          </button>
        </form>
      ) : null}

      {loading ? (
        <p className="text-slate-500">Loading...</p>
      ) : faqs.length === 0 ? (
        <p className="text-slate-500">No FAQs yet.</p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">Question</th>
                <th className="px-4 py-2 font-medium">Category</th>
                <th className="px-4 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {faqs.map((f) => (
                <tr key={f.id} className="border-t border-slate-100 align-top">
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-900">{f.question}</p>
                    <p className="mt-1 text-slate-600">{f.answer}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {f.category ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(f.id)}
                      className="text-sm text-red-600 hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
