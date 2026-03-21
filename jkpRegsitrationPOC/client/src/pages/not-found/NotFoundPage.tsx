import { Link } from "@tanstack/react-router";

export function NotFoundPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4">
      <h1 className="text-6xl font-bold">404</h1>
      <p className="text-lg text-muted">Page not found</p>
      <Link
        to="/"
        className="mt-2 rounded-full bg-primary px-6 py-2 text-sm font-medium text-on-primary transition-opacity hover:opacity-80"
      >
        Go Home
      </Link>
    </div>
  );
}
