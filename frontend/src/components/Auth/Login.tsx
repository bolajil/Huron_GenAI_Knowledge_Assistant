"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Brain,
  Building2,
  Shield,
  Fingerprint,
  Eye,
  EyeOff,
  ArrowRight,
} from "lucide-react";
import { api } from "../../services/api";
import { useAuth } from "../../contexts/auth-context";
import { SmokeyBackground } from "../ui/login-form";

type AuthMethod = "local" | "azure" | "okta";

const AUTH_TABS: { value: AuthMethod; label: string }[] = [
  { value: "local", label: "Local" },
  { value: "azure", label: "Azure AD" },
  { value: "okta", label: "Okta SSO" },
];

export function Login() {
  const router = useRouter();
  useAuth();
  const [authMethod, setAuthMethod] = useState<AuthMethod>("local");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    username: "",
    password: "",
    rememberMe: false,
    trustDevice: false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const response = await api.login(formData.username, formData.password, authMethod);
      localStorage.setItem("pending_auth_token", response.access_token);
      localStorage.setItem("pending_user", JSON.stringify(response.user));
      router.push("/mfa");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSSOLogin = (provider: "azure" | "okta") => {
    const hostname = typeof window !== "undefined" ? window.location.hostname : "";
    // In Azure Container Apps, frontend and backend share the same FQDN suffix.
    // Derive the backend URL at runtime to avoid build-time env var baking.
    const backendBase = hostname.includes("azurecontainerapps.io")
      ? `https://${hostname.replace("huron-dev-frontend", "huron-dev-backend")}`
      : (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8004");
    window.location.href = `${backendBase}/api/v1/auth/oidc/login?provider=${provider}`;
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
          <p className="text-gray-300 text-sm">
            Knowledge Assistant — Enterprise Secure Login
          </p>
        </div>

        {/* Card */}
        <div className="w-full max-w-sm bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 shadow-2xl p-8 space-y-6">
          {/* Auth method tabs */}
          <div className="grid grid-cols-3 gap-1 bg-white/5 rounded-xl p-1">
            {AUTH_TABS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => { setAuthMethod(value); setError(""); }}
                className={`py-2 px-1 rounded-lg text-xs font-medium transition-all ${
                  authMethod === value
                    ? "bg-blue-600 text-white shadow"
                    : "text-gray-300 hover:text-white"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-500/20 border border-red-500/30 rounded-lg px-4 py-3 text-red-300 text-sm">
              {error}
            </div>
          )}

          {authMethod === "local" ? (
            <form onSubmit={handleSubmit} className="glass-form space-y-8">
              {/* Username floating label */}
              <div className="relative z-0">
                <input
                  type="text"
                  id="username"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="block py-2.5 px-0 w-full text-sm text-white bg-transparent border-0 border-b-2 border-gray-500 appearance-none focus:outline-none focus:ring-0 focus:border-blue-400 peer"
                  placeholder=" "
                  required
                />
                <label
                  htmlFor="username"
                  className="absolute text-sm text-gray-400 duration-300 transform -translate-y-6 scale-75 top-3 -z-10 origin-[0] peer-focus:text-blue-400 peer-placeholder-shown:scale-100 peer-placeholder-shown:translate-y-0 peer-focus:scale-75 peer-focus:-translate-y-6"
                >
                  👤 Username or Email
                </label>
              </div>

              {/* Password floating label */}
              <div className="relative z-0">
                <input
                  type={showPassword ? "text" : "password"}
                  id="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="block py-2.5 px-0 w-full text-sm text-white bg-transparent border-0 border-b-2 border-gray-500 appearance-none focus:outline-none focus:ring-0 focus:border-blue-400 peer pr-8"
                  placeholder=" "
                  required
                />
                <label
                  htmlFor="password"
                  className="absolute text-sm text-gray-400 duration-300 transform -translate-y-6 scale-75 top-3 -z-10 origin-[0] peer-focus:text-blue-400 peer-placeholder-shown:scale-100 peer-placeholder-shown:translate-y-0 peer-focus:scale-75 peer-focus:-translate-y-6"
                >
                  🔒 Password
                </label>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-0 top-2.5 text-gray-400 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>

              {/* Checkboxes */}
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-gray-300 text-sm cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={formData.rememberMe}
                    onChange={(e) => setFormData({ ...formData, rememberMe: e.target.checked })}
                    className="glass-checkbox"
                  />
                  Remember me
                </label>
                <label className="flex items-center gap-2 text-gray-300 text-sm cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={formData.trustDevice}
                    onChange={(e) => setFormData({ ...formData, trustDevice: e.target.checked })}
                    className="glass-checkbox"
                  />
                  Trust device
                </label>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={isLoading}
                className="group w-full flex items-center justify-center py-3 px-4 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold transition-all duration-300 disabled:opacity-50 shadow-md"
              >
                {isLoading ? "Authenticating..." : "Sign In"}
                {!isLoading && (
                  <ArrowRight className="ml-2 h-5 w-5 transform group-hover:translate-x-1 transition-transform" />
                )}
              </button>
            </form>
          ) : (
            <div className="space-y-4 pt-2">
              <p className="text-gray-300 text-sm text-center">
                {authMethod === "azure"
                  ? "Authenticate via Azure Active Directory"
                  : "Authenticate via Okta SSO"}
              </p>
              <button
                onClick={() => handleSSOLogin(authMethod)}
                className="w-full flex items-center justify-center py-3 gap-2 bg-white/20 hover:bg-white/30 border border-white/20 rounded-lg text-white font-semibold transition-all"
              >
                {authMethod === "azure" ? (
                  <>
                    <Building2 className="h-5 w-5" />
                    Sign in with Azure AD
                  </>
                ) : (
                  <>
                    <Shield className="h-5 w-5" />
                    Sign in with Okta
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* Security badges */}
        <div className="flex gap-5 mt-6 flex-wrap justify-center">
          <span className="text-xs text-emerald-400/70 flex items-center gap-1.5">
            <Building2 size={11} /> Active Directory Ready
          </span>
          <span className="text-xs text-emerald-400/70 flex items-center gap-1.5">
            <Shield size={11} /> Okta SSO Ready
          </span>
          <span className="text-xs text-emerald-400/70 flex items-center gap-1.5">
            <Fingerprint size={11} /> MFA Enabled
          </span>
        </div>

        <p className="text-gray-400 text-xs mt-4">
          © 2026 Huron Enterprise. All rights reserved.
        </p>
      </div>
    </main>
  );
}

export default Login;
