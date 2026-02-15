"use client";

import { useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";

function SearchRedirect() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const q = searchParams.get("q") || "";

  useEffect(() => {
    if (q) {
      router.replace(`/papers?q=${encodeURIComponent(q)}`);
    } else {
      router.replace("/papers");
    }
  }, [q, router]);

  return (
    <div className="flex items-center justify-center py-20 text-dim text-xs">
      Redirecting to Papers...
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={<div className="text-dim text-xs p-6">Redirecting...</div>}
    >
      <SearchRedirect />
    </Suspense>
  );
}
