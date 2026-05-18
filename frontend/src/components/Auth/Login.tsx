/**
 * Login Component
 * Per FRONTEND_MIGRATION_GUIDE.md - components/Auth/Login.jsx
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Shield,
  Key,
  Eye,
  EyeOff,
  LogIn,
  Building2,
  Fingerprint,
  ChevronDown,
  Brain,
} from "lucide-react";
import { api } from "../../services/api";

type AuthMethod = "local" | "azure" | "okta";

export function Login() {
  const router = useRouter();
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
      const response = await api.login(
        formData.username,
        formData.password,
        authMethod
      );

      // Store auth data
      localStorage.setItem("auth_token", response.access_token);
      localStorage.setItem("user", JSON.stringify(response.user));

      // Redirect to MFA verification (per enterprise_auth.py require_mfa: bool = True)
      router.push("/mfa");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSSOLogin = (provider: "azure" | "okta") => {
    window.location.href = `/api/v1/auth/sso/${provider}`;
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex flex-col items-center justify-center p-4">
      {/* Logo and Title */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-3 mb-2">
          <Brain className="h-10 w-10 text-pink-500" />
          <h1 className="text-3xl font-bold text-white">
            VaultMind GenAI Knowledge Assistant
          </h1>
        </div>
        <div className="flex items-center justify-center gap-2 text-gray-400">
          <Shield className="h-5 w-5 text-yellow-500" />
          <span className="text-lg">Enterprise Secure Login</span>
        </div>
        <p className="text-gray-500 text-sm mt-1">
          Production-grade authentication with enterprise security
        </p>
      </div>

      {/* Security Status Badges */}
      <div className="flex gap-4 mb-8 flex-wrap justify-center">
        <div className="bg-green-900/30 border border-green-700 rounded-lg px-4 py-2 flex items-center gap-2">
          <Building2 className="h-4 w-4 text-green-400" />
          <span className="text-green-400 text-sm">Active Directory Ready</span>
        </div>
        <div className="bg-green-900/30 border border-green-700 rounded-lg px-4 py-2 flex items-center gap-2">
          <Shield className="h-4 w-4 text-green-400" />
          <span className="text-green-400 text-sm">Okta SSO: Ready</span>
        </div>
        <div className="bg-green-900/30 border border-green-700 rounded-lg px-4 py-2 flex items-center gap-2">
          <Fingerprint className="h-4 w-4 text-green-400" />
          <span className="text-green-400 text-sm">MFA: Enabled</span>
        </div>
      </div>

      {/* Auth Method Selector */}
      <div className="w-full max-w-md mb-4">
        <label className="text-gray-400 text-sm mb-2 block">
          Choose Authentication Method:
        </label>
        <div className="relative">
          <select
            value={authMethod}
            onChange={(e) => setAuthMethod(e.target.value as AuthMethod)}
            className="w-full bg-[#1a1a2e] border border-gray-700 rounded-lg px-4 py-3 text-white appearance-none cursor-pointer focus:outline-none focus:border-primary"
          >
            <option value="local">🔑 Local Login</option>
            <option value="azure">🏢 Azure Active Directory</option>
            <option value="okta">🔐 Okta SSO</option>
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
        </div>
      </div>

      {/* Login Form */}
      <div className="w-full max-w-md bg-[#12121a] border border-gray-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-6">
          <Key className="h-5 w-5 text-yellow-500" />
          <h2 className="text-white font-semibold">
            {authMethod === "local" && "Local Authentication"}
            {authMethod === "azure" && "Azure AD Authentication"}
            {authMethod === "okta" && "Okta SSO Authentication"}
          </h2>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg px-4 py-3 mb-4 text-red-400 text-sm">
            {error}
          </div>
        )}

        {authMethod === "local" ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="flex items-center gap-1 text-red-400 text-sm mb-2">
                <span>👤</span> Username or Email
              </label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) =>
                  setFormData({ ...formData, username: e.target.value })
                }
                placeholder="Enter your username or email address"
                className="w-full bg-[#1a1a2e] border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-primary"
                required
              />
            </div>

            <div>
              <label className="flex items-center gap-1 text-gray-400 text-sm mb-2">
                <span>🔒</span> Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={formData.password}
                  onChange={(e) =>
                    setFormData({ ...formData, password: e.target.value })
                  }
                  placeholder="Enter your password"
                  className="w-full bg-[#1a1a2e] border border-gray-700 rounded-lg px-4 py-3 pr-12 text-white placeholder-gray-500 focus:outline-none focus:border-primary"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-gray-400 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.rememberMe}
                  onChange={(e) =>
                    setFormData({ ...formData, rememberMe: e.target.checked })
                  }
                  className="rounded border-gray-600 bg-gray-800"
                />
                Remember me
              </label>
              <label className="flex items-center gap-2 text-gray-400 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.trustDevice}
                  onChange={(e) =>
                    setFormData({ ...formData, trustDevice: e.target.checked })
                  }
                  className="rounded border-gray-600 bg-gray-800"
                />
                Trust device
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-red-500 to-orange-500 hover:from-red-600 hover:to-orange-600 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              <LogIn className="h-5 w-5" />
              {isLoading ? "Authenticating..." : "Login"}
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            <p className="text-gray-400 text-sm">
              {authMethod === "azure"
                ? "Click below to authenticate with your organization's Azure Active Directory account."
                : "Click below to authenticate with your Okta SSO credentials."}
            </p>
            <button
              onClick={() => handleSSOLogin(authMethod)}
              className="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2"
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

      <p className="text-gray-600 text-xs mt-8">
        © 2024 VaultMind Enterprise. All rights reserved.
      </p>
    </div>
  );
}

export default Login;
