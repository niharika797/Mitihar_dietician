import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { Leaf, Eye, EyeOff, ArrowRight } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import {
  loginDoctor,
  loginDoctorMfa,
  loginAdmin,
  loginAdminMfa,
  commitLogin,
} from '../../lib/authService';
import { isMFARequired } from '../../lib/types';
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from '../components/ui/input-otp';

type Role = 'doctor' | 'admin';

// ─── Step-1 login mutation ────────────────────────────────────────────────────

function useLoginMutation(role: Role) {
  return useMutation({
    mutationFn: ({
      email,
      password,
    }: {
      email: string;
      password: string;
    }) =>
      role === 'doctor'
        ? loginDoctor(email, password)
        : loginAdmin(email, password),
  });
}

// ─── Step-2 MFA mutation ──────────────────────────────────────────────────────

function useMfaMutation(role: Role) {
  return useMutation({
    mutationFn: ({
      partial_token,
      totp_code,
    }: {
      partial_token: string;
      totp_code: string;
    }) =>
      role === 'doctor'
        ? loginDoctorMfa(partial_token, totp_code)
        : loginAdminMfa(partial_token, totp_code),
  });
}

// ─── Error extractor ──────────────────────────────────────────────────────────

function extractError(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (error.response?.status === 401)
      return 'Incorrect email or password';
    if (error.response?.status === 429)
      return 'Too many attempts. Please wait a moment.';
  }
  return 'Something went wrong. Please try again.';
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Login() {
  const [role, setRole] = useState<Role>('doctor');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // MFA step-2 state
  const [mfaMode, setMfaMode] = useState(false);
  const [partialToken, setPartialToken] = useState('');
  const [otpValue, setOtpValue] = useState('');

  const navigate = useNavigate();

  const loginMutation = useLoginMutation(role);
  const mfaMutation = useMfaMutation(role);

  // ── Step-1 submit ────────────────────────────────────────────────────────
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    loginMutation.mutate(
      { email, password },
      {
        onSuccess: (result) => {
          if (isMFARequired(result)) {
            // Account has MFA enabled — show the OTP input
            setPartialToken(result.partial_token);
            setMfaMode(true);
          } else {
            // No MFA — commit tokens and navigate
            commitLogin(result, role);
            navigate(role === 'doctor' ? '/doctor/overview' : '/admin/overview');
          }
        },
      },
    );
  };

  // ── Step-2 OTP submit ────────────────────────────────────────────────────
  const handleMfaSubmit = () => {
    if (otpValue.length !== 6) return;

    mfaMutation.mutate(
      { partial_token: partialToken, totp_code: otpValue },
      {
        onSuccess: (result) => {
          commitLogin(result, role);
          navigate(role === 'doctor' ? '/doctor/overview' : '/admin/overview');
        },
      },
    );
  };

  // Auto-submit when all 6 digits are entered
  const handleOtpChange = (val: string) => {
    setOtpValue(val);
    if (val.length === 6) {
      // Small delay so the user sees the last digit before submit
      setTimeout(() => {
        mfaMutation.mutate(
          { partial_token: partialToken, totp_code: val },
          {
            onSuccess: (result) => {
              commitLogin(result, role);
              navigate(
                role === 'doctor' ? '/doctor/overview' : '/admin/overview',
              );
            },
          },
        );
      }, 120);
    }
  };

  const isLoading = loginMutation.isPending || mfaMutation.isPending;
  const loginError = loginMutation.error
    ? extractError(loginMutation.error)
    : null;
  const mfaError = mfaMutation.error ? extractError(mfaMutation.error) : null;

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#F9FAFB] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-[#1E7C45] flex items-center justify-center mb-3">
            <Leaf size={22} className="text-white" />
          </div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">
            Mityahar
          </h1>
          <p className="text-sm text-[#6B7280] mt-1">
            Clinical Nutrition Dashboard
          </p>
        </div>

        {/* ── MFA screen ── */}
        {mfaMode ? (
          <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-[0_1px_3px_0_rgb(0_0_0/0.1)]">
            <h2 className="text-base font-semibold text-[#111827] mb-1">
              Two-factor authentication
            </h2>
            <p className="text-sm text-[#6B7280] mb-5">
              Enter the 6-digit code from your authenticator app.
            </p>

            <div className="flex justify-center mb-5">
              <InputOTP
                maxLength={6}
                value={otpValue}
                onChange={handleOtpChange}
                disabled={isLoading}
              >
                <InputOTPGroup>
                  {[0, 1, 2, 3, 4, 5].map((i) => (
                    <InputOTPSlot key={i} index={i} />
                  ))}
                </InputOTPGroup>
              </InputOTP>
            </div>

            {/* Inline MFA error */}
            {mfaError && (
              <p className="text-sm text-[#DC2626] mb-4 text-center">
                {mfaError}
              </p>
            )}

            <button
              onClick={handleMfaSubmit}
              disabled={otpValue.length !== 6 || isLoading}
              className="w-full h-10 rounded-md bg-[#1E7C45] text-white text-sm font-medium hover:bg-[#166534] transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Verify code
                  <ArrowRight size={15} />
                </>
              )}
            </button>

            <button
              onClick={() => {
                setMfaMode(false);
                setOtpValue('');
                setPartialToken('');
                loginMutation.reset();
                mfaMutation.reset();
              }}
              className="w-full mt-3 text-sm text-[#6B7280] hover:text-[#374151] transition-colors"
            >
              ← Back to login
            </button>
          </div>
        ) : (
          /* ── Login screen ── */
          <>
            {/* Role toggle */}
            <div className="flex items-center gap-1 p-1 rounded-lg bg-[#F3F4F6] mb-6">
              {(['doctor', 'admin'] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => {
                    setRole(r);
                    loginMutation.reset();
                  }}
                  className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors capitalize ${
                    role === r
                      ? 'bg-white text-[#111827] shadow-sm'
                      : 'text-[#6B7280] hover:text-[#374151]'
                  }`}
                >
                  {r === 'doctor' ? 'Doctor' : 'Admin'}
                </button>
              ))}
            </div>

            {/* Form */}
            <form
              onSubmit={handleSubmit}
              className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-[0_1px_3px_0_rgb(0_0_0/0.1)]"
            >
              <div className="mb-4">
                <label className="block text-sm font-medium text-[#374151] mb-1.5">
                  Email address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={
                    role === 'doctor'
                      ? 'doctor@mityahar.in'
                      : 'admin@mityahar.in'
                  }
                  required
                  className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent transition"
                />
              </div>

              <div className="mb-5">
                <label className="block text-sm font-medium text-[#374151] mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full h-10 px-3 pr-10 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9CA3AF] hover:text-[#6B7280]"
                  >
                    {showPassword ? (
                      <EyeOff size={15} />
                    ) : (
                      <Eye size={15} />
                    )}
                  </button>
                </div>
              </div>

              {/* Inline error */}
              {loginError && (
                <div className="mb-4 px-3 py-2.5 rounded-md bg-[#FEF2F2] border border-[#FECACA]">
                  <p className="text-sm text-[#DC2626]">{loginError}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading || !email || !password}
                className="w-full h-10 rounded-md bg-[#1E7C45] text-white text-sm font-medium hover:bg-[#166534] transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    Sign in as {role === 'doctor' ? 'Doctor' : 'Admin'}
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </form>

            {/* Quick demo access — pre-fills credentials for local testing */}
            <div className="mt-4 p-4 rounded-lg bg-[#F0FDF4] border border-[#DCFCE7]">
              <p className="text-xs font-medium text-[#15803d] mb-2">
                Quick dev access
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setRole('doctor');
                    setEmail('testdoctor@mityahar.com');
                    setPassword('doctor1234');
                    loginMutation.reset();
                  }}
                  className="flex-1 h-7 rounded text-xs bg-white border border-[#DCFCE7] text-[#15803d] hover:bg-[#DCFCE7] transition-colors"
                >
                  Doctor
                </button>
                <button
                  onClick={() => {
                    setRole('admin');
                    setEmail('admin@mityahar.com');
                    setPassword('admin1234');
                    loginMutation.reset();
                  }}
                  className="flex-1 h-7 rounded text-xs bg-white border border-[#DCFCE7] text-[#15803d] hover:bg-[#DCFCE7] transition-colors"
                >
                  Admin
                </button>
              </div>
            </div>
          </>
        )}

        <p className="text-center text-xs text-[#9CA3AF] mt-6">
          © 2026 Mityahar Health Technologies
        </p>
      </div>
    </div>
  );
}
