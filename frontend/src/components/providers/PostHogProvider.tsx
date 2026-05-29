"use client";

import posthog from "posthog-js";
import { PostHogProvider as PHProvider } from "posthog-js/react";
import { useEffect } from "react";
import { useAuth } from "../../contexts/auth-context";

const POSTHOG_KEY  = process.env.NEXT_PUBLIC_POSTHOG_KEY  ?? "";
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://app.posthog.com";

// Initialise once at module level so hot-reloads don't duplicate the init.
if (typeof window !== "undefined" && POSTHOG_KEY && !posthog.__loaded) {
  posthog.init(POSTHOG_KEY, {
    api_host:                  POSTHOG_HOST,
    capture_pageview:          false, // we fire manual page events below
    capture_pageleave:         true,
    persistence:               "localStorage",
    // Autocapture off — we use explicit trackXxx() calls for full control.
    autocapture:               false,
    session_recording: {
      // Mask text inside <textarea> and query inputs to avoid capturing PII.
      maskAllInputs: true,
      maskTextSelector: "textarea, [data-ph-mask]",
    },
  });
}

// Inner component wires the logged-in user identity to PostHog.
function PostHogIdentifier() {
  const { user } = useAuth();
  useEffect(() => {
    if (!POSTHOG_KEY || !user) return;
    // Identify by numeric user id only — never by username or email.
    posthog.identify(user.id, {
      department: user.department,
      role:       user.role,
    });
    return () => {
      // Reset on unmount so a subsequent login gets a fresh identity.
    };
  }, [user]);
  return null;
}

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  // If no key is configured, render children without any PostHog wrapping.
  if (!POSTHOG_KEY) return <>{children}</>;

  return (
    <PHProvider client={posthog}>
      <PostHogIdentifier />
      {children}
    </PHProvider>
  );
}
