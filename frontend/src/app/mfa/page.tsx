/**
 * MFA Verification Page
 * Per app/auth/mfa_setup.py, mfa_providers.py, and enterprise_auth.py
 */
"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield, Smartphone, Key, CheckCircle, AlertCircle, Mail, MessageSquare } from "lucide-react";
import { useAuth } from "../../contexts/auth-context";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type MFAMethod = "totp" | "email" | "sms";

interface AuthenticatorOption {
  id: string;
  name: string;
  icon: string;
  description: string;
}

const AUTHENTICATOR_APPS: AuthenticatorOption[] = [
  { id: "google", name: "Google Authenticator", icon: "🔐", description: "Free, simple TOTP app" },
  { id: "microsoft", name: "Microsoft Authenticator", icon: "🔵", description: "Enterprise-ready with push" },
  { id: "duo", name: "Duo Mobile", icon: "🟢", description: "Cisco Duo with push notifications" },
  { id: "authy", name: "Authy", icon: "🔴", description: "Multi-device sync, cloud backup" },
  { id: "1password", name: "1Password", icon: "🔒", description: "Password manager with TOTP" },
];

export default function MFAPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [secret, setSecret] = useState<string | null>(null);
  const [isSetup, setIsSetup] = useState(false);
  const [mfaMethod, setMfaMethod] = useState<MFAMethod>("totp");
  const [selectedApp, setSelectedApp] = useState<string>("google");
  const [step, setStep] = useState<"choose" | "setup" | "verify">("choose");
  const [copied, setCopied] = useState(false);

  // Get user info from localStorage
  const [userEmail, setUserEmail] = useState("admin@vaultmind.ai");
  const [userName, setUserName] = useState("admin");

  useEffect(() => {
    // Get pending user info from login
    const pendingUser = localStorage.getItem("pending_user");
    if (pendingUser) {
      try {
        const user = JSON.parse(pendingUser);
        setUserEmail(user.email || "admin@huron.com");
        setUserName(user.username || "admin");
      } catch (e) {
        console.error("Failed to parse user data");
      }
    } else {
      // No pending auth, redirect to login
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

      // Verify MFA code with backend
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/mfa/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, token: pendingToken }),
      });

      const data = await response.json();

      if (response.ok && data.verified) {
        // MFA verified - complete login
        const user = JSON.parse(pendingUser || "{}");
        login(pendingToken || "", user);

        // Clean up pending auth
        localStorage.removeItem("pending_auth_token");
        localStorage.removeItem("pending_user");
        localStorage.setItem("mfa_verified", "true");
        localStorage.setItem("mfa_method", mfaMethod);

        // Redirect to dashboard
        router.push("/dashboard");
      } else {
        setError(data.detail || "Invalid MFA code");
      }
    } catch (err) {
      setError("Failed to verify MFA code");
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Shield className="h-10 w-10 text-green-500" />
            <h1 className="text-2xl font-bold text-white">
              Multi-Factor Authentication
            </h1>
          </div>
          <p className="text-gray-400">
            {step === "choose" && "Choose your preferred authentication method"}
            {step === "setup" && "Set up your authenticator app"}
            {step === "verify" && "Enter the verification code"}
          </p>
        </div>

        {/* Step 1: Choose Method */}
        {step === "choose" && (
          <div className="bg-[#12121a] border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Key className="h-5 w-5 text-yellow-400" />
              Select Authentication Method
            </h2>

            {/* MFA Method Tabs */}
            <div className="grid grid-cols-3 gap-2 mb-6">
              <button
                onClick={() => setMfaMethod("totp")}
                className={`p-3 rounded-lg border text-sm flex flex-col items-center gap-2 transition-all ${
                  mfaMethod === "totp"
                    ? "border-green-500 bg-green-500/10 text-green-400"
                    : "border-gray-700 text-gray-400 hover:border-gray-600"
                }`}
              >
                <Smartphone className="h-5 w-5" />
                Authenticator App
              </button>
              <button
                onClick={() => setMfaMethod("email")}
                className={`p-3 rounded-lg border text-sm flex flex-col items-center gap-2 transition-all ${
                  mfaMethod === "email"
                    ? "border-blue-500 bg-blue-500/10 text-blue-400"
                    : "border-gray-700 text-gray-400 hover:border-gray-600"
                }`}
              >
                <Mail className="h-5 w-5" />
                Email Code
              </button>
              <button
                onClick={() => setMfaMethod("sms")}
                className={`p-3 rounded-lg border text-sm flex flex-col items-center gap-2 transition-all ${
                  mfaMethod === "sms"
                    ? "border-purple-500 bg-purple-500/10 text-purple-400"
                    : "border-gray-700 text-gray-400 hover:border-gray-600"
                }`}
              >
                <MessageSquare className="h-5 w-5" />
                SMS Code
              </button>
            </div>

            {/* Authenticator App Selection */}
            {mfaMethod === "totp" && (
              <div className="space-y-3 mb-6">
                <p className="text-gray-400 text-sm mb-3">Choose your authenticator app:</p>
                {AUTHENTICATOR_APPS.map((app) => (
                  <button
                    key={app.id}
                    onClick={() => setSelectedApp(app.id)}
                    className={`w-full p-4 rounded-lg border text-left flex items-center gap-4 transition-all ${
                      selectedApp === app.id
                        ? "border-green-500 bg-green-500/10"
                        : "border-gray-700 hover:border-gray-600"
                    }`}
                  >
                    <span className="text-2xl">{app.icon}</span>
                    <div>
                      <p className="text-white font-medium">{app.name}</p>
                      <p className="text-gray-500 text-sm">{app.description}</p>
                    </div>
                    {selectedApp === app.id && (
                      <CheckCircle className="h-5 w-5 text-green-500 ml-auto" />
                    )}
                  </button>
                ))}
              </div>
            )}

            {mfaMethod === "email" && (
              <div className="p-4 bg-blue-900/20 rounded-lg border border-blue-800 mb-6">
                <p className="text-blue-400 text-sm">
                  A verification code will be sent to your registered email address.
                </p>
              </div>
            )}

            {mfaMethod === "sms" && (
              <div className="p-4 bg-purple-900/20 rounded-lg border border-purple-800 mb-6">
                <p className="text-purple-400 text-sm">
                  A verification code will be sent via SMS to your phone.
                </p>
              </div>
            )}

            <button
              onClick={() => setStep(mfaMethod === "totp" ? "setup" : "verify")}
              className="w-full bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2"
            >
              Continue
              <CheckCircle className="h-5 w-5" />
            </button>
          </div>
        )}

        {/* Step 2: QR Code Setup (for TOTP only) */}
        {step === "setup" && mfaMethod === "totp" && (
          <div className="bg-[#12121a] border border-gray-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <Smartphone className="h-5 w-5 text-green-400" />
              <h2 className="text-white font-semibold">
                Set Up {AUTHENTICATOR_APPS.find(a => a.id === selectedApp)?.name}
              </h2>
            </div>

            <div className="space-y-6">
              {/* Step indicator */}
              <div className="flex items-center gap-2 text-sm">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-green-500 text-white text-xs font-bold">1</span>
                <span className="text-gray-400">Open {AUTHENTICATOR_APPS.find(a => a.id === selectedApp)?.name} on your phone</span>
              </div>

              {/* QR Code */}
              <div className="flex items-center gap-2 text-sm">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-green-500 text-white text-xs font-bold">2</span>
                <span className="text-gray-400">Scan this QR code</span>
              </div>

              <div className="flex justify-center">
                <div className="bg-white p-4 rounded-xl shadow-lg">
                  {/* QR Code - using actual user info */}
                  <img 
                    src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(`otpauth://totp/VaultMind:${userName}?secret=JBSWY3DPEHPK3PXP&issuer=VaultMind`)}`}
                    alt="Scan QR Code"
                    className="w-48 h-48"
                  />
                </div>
              </div>
              
              <p className="text-center text-gray-500 text-xs">
                Setting up MFA for: <span className="text-green-400">{userName}</span>
              </p>

              {/* Manual entry option */}
              <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-800">
                <p className="text-gray-400 text-sm mb-2">Can't scan? Enter this key manually:</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-gray-800 text-green-400 p-3 rounded font-mono text-center tracking-wider">
                    JBSWY 3DPE HPK3 PXP
                  </code>
                  <button 
                    onClick={() => {
                      navigator.clipboard.writeText("JBSWY3DPEHPK3PXP");
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="p-3 bg-gray-800 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
                    title="Copy to clipboard"
                  >
                    {copied ? "✅" : "📋"}
                  </button>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex items-center gap-2 text-sm">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-gray-700 text-white text-xs font-bold">3</span>
                <span className="text-gray-400">Enter the 6-digit code from your app to verify</span>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setStep("choose")}
                className="flex-1 border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 font-semibold py-3 rounded-lg"
              >
                Back
              </button>
              <button
                onClick={() => setStep("verify")}
                className="flex-1 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2"
              >
                I've Scanned It
                <CheckCircle className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Verify Code */}
        {step === "verify" && (
          <div className="bg-[#12121a] border border-gray-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              {mfaMethod === "totp" && <Smartphone className="h-5 w-5 text-green-400" />}
              {mfaMethod === "email" && <Mail className="h-5 w-5 text-blue-400" />}
              {mfaMethod === "sms" && <MessageSquare className="h-5 w-5 text-purple-400" />}
              <h2 className="text-white font-semibold">
                {mfaMethod === "totp" && `Enter code from ${AUTHENTICATOR_APPS.find(a => a.id === selectedApp)?.name}`}
                {mfaMethod === "email" && "Enter code sent to your email"}
                {mfaMethod === "sms" && "Enter code sent via SMS"}
              </h2>
            </div>

            {error && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg px-4 py-3 mb-4 flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-red-400" />
                <span className="text-red-400 text-sm">{error}</span>
              </div>
            )}

            {/* Code Input */}
            <div className="mb-6">
              <label className="block text-gray-400 text-sm mb-2">
                6-Digit Authentication Code
              </label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="000000"
                maxLength={6}
                className="w-full bg-[#1a1a2e] border border-gray-700 rounded-lg px-4 py-4 text-white text-center text-2xl tracking-[0.5em] font-mono placeholder-gray-600 focus:outline-none focus:border-green-500"
                autoFocus
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => { setStep("choose"); setCode(""); setError(""); }}
                className="flex-1 border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 font-semibold py-3 rounded-lg"
              >
                Back
              </button>
              <button
                onClick={handleVerify}
                disabled={isVerifying || code.length !== 6}
                className="flex-1 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <CheckCircle className="h-5 w-5" />
                {isVerifying ? "Verifying..." : "Verify"}
              </button>
            </div>

            {/* Selected App Info */}
            {mfaMethod === "totp" && (
              <div className="mt-6 p-4 bg-gray-900/50 rounded-lg border border-gray-800">
                <p className="text-gray-400 text-sm flex items-center gap-2">
                  <span className="text-xl">{AUTHENTICATOR_APPS.find(a => a.id === selectedApp)?.icon}</span>
                  Using {AUTHENTICATOR_APPS.find(a => a.id === selectedApp)?.name}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
