export default function Home() {
  return (
    <main className="mx-auto max-w-3xl p-12">
      <h1 className="text-3xl font-semibold">Welcome</h1>
      <p className="mt-4 text-slate-600">
        Sign in and head to the dashboard to start.
      </p>
      <a
        className="mt-6 inline-block rounded bg-slate-900 px-4 py-2 text-white"
        href="/dashboard"
      >
        Go to dashboard
      </a>
    </main>
  );
}
