"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Shield,
  Smartphone,
  CheckCircle,
  AlertCircle,
  Mail,
  MessageSquare,
  ArrowRight,
  Brain,
} from "lucide-react";
import { useAuth } from "../../contexts/auth-context";
import { SmokeyBackground } from "../../components/ui/login-form";

type MFAMethod = "totp" | "email" | "sms";
type Step = "choose" | "setup" | "verify";

interface AuthenticatorApp {
  id: string;
  name: string;
  icon: string;
}

const AUTHENTICATOR_APPS: AuthenticatorApp[] = [
  { id: "google", name: "Google Authenticator", icon: "🔐" },
  { id: "microsoft", name: "Microsoft Authenticator", icon: "🔵" },
  { id: "duo", name: "Duo Mobile", icon: "🟢" },
  { id: "authy", name: "Authy", icon: "🔴" },
  { id: "1password", name: "1Password", icon: "🔒" },
];

const MFA_METHODS: { value: MFAMethod; label: string; icon: React.ReactNode }[] = [
  { value: "totp", label: "Authenticator", icon: <Smartphone size={16} /> },
  { value: "email", label: "Email", icon: <Mail size={16} /> },
  { value: "sms", label: "SMS", icon: <MessageSquare size={16} /> },
];

export default function MFAPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [mfaMethod, setMfaMethod] = useState<MFAMethod>("totp");
  const [selectedApp, setSelectedApp] = useState("duo");
  const [step, setStep] = useState<Step>("choose");
  const [copied, setCopied] = useState(false);
  const [userName, setUserName] = useState("admin");

  useEffect(() => {
    const pendingUser = localStorage.getItem("pending_user");
    if (pendingUser) {
      try {
        const user = JSON.parse(pendingUser);
        setUserName(user.username || "admin");
      } catch {
        // ignore parse errors
      }
    } else {
      router.push("/");
    }
  }, [router]);

  const handleVerify = async () => {
    if (code.length !== 6) {
      setError("Please enter a 6-digit code");
      return;
    }
    setIsVerifying(true);
    setError("");
    try {
      const pendingToken = localStorage.getItem("pending_auth_token");
      const pendingUser = localStorage.getItem("pending_user");

      const response = await fetch("http://localhost:8000/api/v1/auth/mfa/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, session_token: pendingToken }),
      });

      const data = await response.json();

      if (response.ok && data.status === "success") {
        const user = JSON.parse(pendingUser || "{}");
        login(data.access_token, user);
        localStorage.removeItem("pending_auth_token");
        localStorage.removeItem("pending_user");
        localStorage.setItem("mfa_verified", "true");
        router.push("/dashboard");
      } else {
        setError(data.detail || "Invalid MFA code");
      }
    } catch {
      setError("Failed to verify MFA code");
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <main className="relative w-screen min-h-screen bg-gray-900 overflow-hidden">
      <SmokeyBackground color="#1E40AF" />

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-2">
            <Brain className="h-10 w-10 text-blue-400" />
            <h1 className="text-3xl font-bold text-white">Huron GenAI</h1>
          </div>
          <div className="flex items-center justify-center gap-2 text-gray-300 text-sm">
            <Shield size={14} className="text-green-400" />
            Multi-Factor Authentication
          </div>
        </div>

        {/* Card */}
        <div className="w-full max-w-sm bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 shadow-2xl p-8">

          {/* ── Step 1: Choose method ── */}
          {step === "choose" && (
            <div className="space-y-6">
              <h2 className="text-white font-semibold text-center">
                Choose Authentication Method
              </h2>

              {/* Method tabs */}
              <div className="grid grid-cols-3 gap-1 bg-white/5 rounded-xl p-1">
                {MFA_METHODS.map(({ value, label, icon }) => (
                  <button
                    key={value}
                    onClick={() => setMfaMethod(value)}
                    className={`py-2 px-1 rounded-lg text-xs font-medium flex flex-col items-center gap-1 transition-all ${
                      mfaMethod === value
                        ? "bg-blue-600 text-white shadow"
                        : "text-gray-300 hover:text-white"
                    }`}
                  >
                    {icon}
                    {label}
                  </button>
                ))}
              </div>

              {/* App selector (TOTP only) */}
              {mfaMethod === "totp" && (
                <div className="space-y-2">
                  {AUTHENTICATOR_APPS.map((app) => (
                    <button
                      key={app.id}
                      onClick={() => setSelectedApp(app.id)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border text-left transition-all ${
                        selectedApp === app.id
                          ? "border-blue-500/60 bg-blue-600/20 text-white"
                          : "border-white/10 bg-white/5 text-gray-300 hover:border-white/20"
                      }`}
                    >
                      <span className="text-xl">{app.icon}</span>
                      <span className="text-sm font-medium">{app.name}</span>
                      {selectedApp === app.id && (
                        <CheckCircle size={16} className="text-blue-400 ml-auto" />
                      )}
                    </button>
                  ))}
                </div>
              )}

              {mfaMethod === "email" && (
                <p className="text-gray-400 text-sm text-center px-2">
                  A verification code will be sent to your registered email.
                </p>
              )}
              {mfaMethod === "sms" && (
                <p className="text-gray-400 text-sm text-center px-2">
                  A verification code will be sent via SMS to your phone.
                </p>
              )}

              <button
                onClick={() => setStep(mfaMethod === "totp" ? "setup" : "verify")}
                className="group w-full flex items-center justify-center py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold transition-all"
              >
                Continue
                <ArrowRight className="ml-2 h-5 w-5 transform group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          )}

          {/* ── Step 2: TOTP setup ── */}
          {step === "setup" && mfaMethod === "totp" && (
            <div className="space-y-6">
              <h2 className="text-white font-semibold text-center">
                Set Up{" "}
                {AUTHENTICATOR_APPS.find((a) => a.id === selectedApp)?.name}
              </h2>

              <div className="flex justify-center">
                <div className="bg-white p-3 rounded-xl shadow-lg">
                  <img
                    src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(
                      `otpauth://totp/VaultMind:${userName}?secret=JBSWY3DPEHPK3PXP&issuer=VaultMind`
                    )}`}
                    alt="Scan QR Code"
                    className="w-44 h-44"
                  />
                </div>
              </div>

              <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                <p className="text-gray-400 text-xs mb-2">Can't scan? Use this key:</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-green-400 font-mono text-center tracking-wider text-sm">
                    JBSWY 3DPE HPK3 PXP
                  </code>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText("JBSWY3DPEHPK3PXP");
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="p-2 bg-white/10 hover:bg-white/20 rounded-lg text-gray-300 transition-all"
                  >
                    {copied ? "✅" : "📋"}
                  </button>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setStep("choose")}
                  className="flex-1 py-3 border border-white/20 text-gray-300 hover:text-white hover:border-white/40 rounded-lg font-medium transition-all"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep("verify")}
                  className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-all"
                >
                  I've Scanned It
                </button>
              </div>
            </div>
          )}

          {/* ── Step 3: Verify code ── */}
          {step === "verify" && (
            <div className="space-y-6">
              <div className="text-center">
                <div className="flex items-center justify-center gap-2 mb-1">
                  {mfaMethod === "totp" && (
                    <span className="text-xl">
                      {AUTHENTICATOR_APPS.find((a) => a.id === selectedApp)?.icon}
                    </span>
                  )}
                  {mfaMethod === "email" && <Mail size={20} className="text-blue-400" />}
                  {mfaMethod === "sms" && <MessageSquare size={20} className="text-blue-400" />}
                </div>
                <h2 className="text-white font-semibold">
                  {mfaMethod === "totp"
                    ? `Enter code from ${AUTHENTICATOR_APPS.find((a) => a.id === selectedApp)?.name}`
                    : mfaMethod === "email"
                    ? "Enter code sent to your email"
                    : "Enter code sent via SMS"}
                </h2>
              </div>

              {error && (
                <div className="bg-red-500/20 border border-red-500/30 rounded-xl px-4 py-3 flex items-center gap-2">
                  <AlertCircle size={16} className="text-red-400 shrink-0" />
                  <span className="text-red-300 text-sm">{error}</span>
                </div>
              )}

              {/* Code input */}
              <div className="glass-form">
                <label className="block text-gray-400 text-xs mb-2 text-center">
                  6-Digit Authentication Code
                </label>
                <input
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="000000"
                  maxLength={6}
                  autoFocus
                  className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-4 text-white text-center text-3xl tracking-[0.6em] font-mono placeholder-gray-600 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400/50 transition-all"
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => { setStep("choose"); setCode(""); setError(""); }}
                  className="flex-1 py-3 border border-white/20 text-gray-300 hover:text-white hover:border-white/40 rounded-lg font-medium transition-all"
                >
                  Back
                </button>
                <button
                  onClick={handleVerify}
                  disabled={isVerifying || code.length !== 6}
                  className="group flex-1 flex items-center justify-center py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <CheckCircle size={16} className="mr-2" />
                  {isVerifying ? "Verifying..." : "Verify"}
                </button>
              </div>
            </div>
          )}
        </div>

        <p className="text-gray-400 text-xs mt-6">
          © 2026 Huron Enterprise. All rights reserved.
        </p>
      </div>
    </main>
  );
}
