"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "../../../contexts/auth-context";
import type { User } from "../../../contexts/auth-context";
import { Loader2, AlertCircle } from "lucide-react";

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(base64));
  } catch {
    return null;
  }
}

function SsoCompleteInner() {
  const router                  = useRouter();
  const params                  = useSearchParams();
  const { login }               = useAuth();
  const [errorMsg, setErrorMsg] = useState("");
  const processed               = useRef(false);

  useEffect(() => {
    // Guard against re-runs caused by login() → setUser() → new login reference
    if (processed.current) return;
    processed.current = true;

    const token = params.get("token");
    const error = params.get("error");

    if (error) {
      setErrorMsg(decodeURIComponent(error));
      setTimeout(() => router.replace("/"), 3000);
      return;
    }

    if (!token) {
      setErrorMsg("No token received from SSO provider.");
      setTimeout(() => router.replace("/"), 3000);
      return;
    }

    const payload = decodeJwtPayload(token);
    if (!payload) {
      setErrorMsg("Invalid token received from SSO provider.");
      setTimeout(() => router.replace("/"), 3000);
      return;
    }

    const userData: User = {
      id:              String(payload.user_id),
      username:        payload.sub as string,
      email:           payload.email as string,
      full_name:       (payload.full_name as string) || (payload.sub as string),
      department:      (payload.dept_id as string) || "company",
      role:            payload.role as User["role"],
      permissions:     (payload.permissions as string[]) || [],
      namespace_scope: (payload.namespace_scope as string[]) || [],
    };

    login(token, userData);
    router.replace("/dashboard");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (errorMsg) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <AlertCircle className="h-10 w-10 text-red-400 mx-auto mb-3" />
          <p className="text-white font-medium mb-1">Sign-in failed</p>
          <p className="text-gray-400 text-sm">{errorMsg}</p>
          <p className="text-gray-500 text-xs mt-2">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-400 mx-auto mb-3" />
        <p className="text-white font-medium">Completing sign-in...</p>
        <p className="text-gray-400 text-sm mt-1">Please wait</p>
      </div>
    </div>
  );
}

export default function SsoCompletePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-900">
          <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
        </div>
      }
    >
      <SsoCompleteInner />
    </Suspense>
  );
}
