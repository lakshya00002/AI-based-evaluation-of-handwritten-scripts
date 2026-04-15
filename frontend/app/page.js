"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getMe } from "../lib/api";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const { data } = await getMe();
        router.replace(data.role === "teacher" ? "/teacher" : "/student");
      } catch {
        router.replace("/login");
      }
    };
    bootstrap();
  }, [router]);

  return <div className="p-8">Loading...</div>;
}
