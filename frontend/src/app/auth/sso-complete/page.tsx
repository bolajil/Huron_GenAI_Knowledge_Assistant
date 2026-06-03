"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "../../../contexts/auth-context";
import { Loader2, AlertCircle } from "lucide-react";

function SsoCompleteInner() {
  const router       = useRouter();
  const params       = useSearchParams();
  const { loginWithToken } = useAuth();
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
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

    loginWithToken(token)
      .then(() => router.replace("/dashboard"))
      .catch(() => {
        setErrorMsg("Failed to complete sign-in. Please try again.");
        setTimeout(() => router.replace("/"), 3000);
      });
  }, [params, router, loginWithToken]);

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
