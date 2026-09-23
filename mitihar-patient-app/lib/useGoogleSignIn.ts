import { useCallback } from "react";
import * as WebBrowser from "expo-web-browser";
import * as AuthSession from "expo-auth-session";
import { discovery as googleDiscovery } from "expo-auth-session/providers/google";
import { verifyGoogleToken } from "../services/auth";
import { getMyProfile } from "../services/profile";
import { useAuthStore } from "../store/useAuthStore";
import { storage } from "./storage";
import { SECURE_KEYS } from "./axios";

// Required on web so the redirect back from Google's consent screen resolves
// the pending auth session instead of leaving the popup hanging.
WebBrowser.maybeCompleteAuthSession();

const redirectUri = AuthSession.makeRedirectUri({ scheme: "mitihar" });

function makeNonce(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
}

export type GoogleSignInResult =
  | { ok: true }
  | { ok: false; cancelled: true }
  | { ok: false; cancelled: false; error: string };

export function useGoogleSignIn() {
  const loginSuccess = useAuthStore(s => s.loginSuccess);
  const setTokens = useAuthStore(s => s.setTokens);

  const [request, , promptAsync] = AuthSession.useAuthRequest(
    {
      clientId: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID ?? "",
      redirectUri,
      scopes: ["openid", "profile", "email"],
      responseType: AuthSession.ResponseType.IdToken,
      extraParams: { nonce: makeNonce() },
    },
    googleDiscovery,
  );

  // Optional: only matters for first-time signup (backend ignores it for existing
  // accounts — see GoogleTokenRequest.gdpr_consent in auth.py). Defaults to false so
  // callers with no consent UI (e.g. the login screen) can omit it safely; a screen
  // with a real checkbox (register.tsx) still passes the actual state explicitly.
  const signInWithGoogle = useCallback(async (gdprConsent: boolean = false): Promise<GoogleSignInResult> => {
    if (!process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID) {
      return { ok: false, cancelled: false, error: "Google sign-in is not configured" };
    }

    const result = await promptAsync();

    if (result.type === "cancel" || result.type === "dismiss") {
      return { ok: false, cancelled: true };
    }
    if (result.type !== "success" || !result.params.id_token) {
      return { ok: false, cancelled: false, error: "Google sign-in failed" };
    }

    // Only matters for first-time signup — the backend ignores it for existing accounts.
    const verify = await verifyGoogleToken(result.params.id_token, gdprConsent);

    if (verify.is_new_user) {
      // Mirrors register.tsx: no profile yet, AuthGate routes to onboarding.
      await setTokens(verify.access_token, verify.refresh_token);
    } else {
      // Mirrors login.tsx: store access token first so the axios interceptor
      // can attach it as Bearer, then fetch profile before the atomic commit.
      await storage.setItemAsync(SECURE_KEYS.ACCESS_TOKEN, verify.access_token);
      const profile = await getMyProfile();
      loginSuccess(verify.access_token, verify.refresh_token, profile);
    }

    return { ok: true };
  }, [promptAsync, loginSuccess, setTokens]);

  return { signInWithGoogle, requestReady: !!request };
}
