import { Suspense } from "react";
import { AuthForm } from "@/components/site/auth-form";

export const metadata = { title: "Sign in", robots: { index: false } };

export default function Page() {
  return <Suspense><AuthForm mode="login" /></Suspense>;
}
