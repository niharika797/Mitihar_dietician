/**
 * notifications.ts
 * ================
 * FCM push-notification helpers for the Mitihar patient app.
 *
 * Usage (called from _layout.tsx after successful auth):
 *   await requestPermissions();
 *   const token = await getFCMToken();
 *   if (token) await sendTokenToBackend(token);
 *   setupNotificationListeners(router);
 *
 * Expo Go compatibility: expo-notifications removed push support from Expo Go
 * in SDK 53. We lazy-require the module only in real builds so that the app
 * still loads (and silently skips notification setup) when run via Expo Go.
 */

import Constants from "expo-constants";
import { Platform } from "react-native";
import api from "./axios";

// expo-notifications is unavailable in Expo Go from SDK 53 onwards.
// Lazy-require it only when running in a development/production build.
const isExpoGo = Constants.appOwnership === "expo";

type Notif = typeof import("expo-notifications");
let N: Notif | null = null;

if (!isExpoGo) {
  try {
    N = require("expo-notifications") as Notif;
    // Foreground display policy — show banner + sound even when app is open
    N.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: false,
        shouldShowBanner: true,
        shouldShowList: true,
      }),
    });
  } catch {
    N = null;
  }
}

// ─── Permission ────────────────────────────────────────────────────────────

/**
 * Request OS-level notification permission.
 * Returns true if permission was granted (or was already granted).
 * Never throws — returns false on any error or in Expo Go.
 */
export async function requestPermissions(): Promise<boolean> {
  if (!N) return false;
  try {
    const { status: existing } = await N.getPermissionsAsync();
    if (existing === "granted") return true;

    const { status } = await N.requestPermissionsAsync();
    return status === "granted";
  } catch {
    return false;
  }
}

// ─── Token ─────────────────────────────────────────────────────────────────

/**
 * Get the device's Expo/FCM push token.
 * Returns null if permission is denied, on emulator (Android), in Expo Go, or on any error.
 */
export async function getFCMToken(): Promise<string | null> {
  if (!N) return null;
  try {
    const { status } = await N.getPermissionsAsync();
    if (status !== "granted") return null;

    // Android requires a notification channel
    if (Platform.OS === "android") {
      await N.setNotificationChannelAsync("default", {
        name: "default",
        importance: N.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: "#1E7C45",
      });
    }

    const tokenData = await N.getExpoPushTokenAsync();
    return tokenData.data ?? null;
  } catch {
    return null;
  }
}

// ─── Backend sync ───────────────────────────────────────────────────────────

/**
 * Register or clear the FCM token on the backend.
 * Pass null to deregister (called on logout).
 * Fire-and-forget — never throws.
 */
export async function sendTokenToBackend(token: string | null): Promise<void> {
  try {
    await api.post("/auth/register-fcm-token", { fcm_token: token });
  } catch {
    // Non-fatal — notification registration failure must never break auth flow
  }
}

// ─── Navigation map ─────────────────────────────────────────────────────────

type NotifType = "plan_ready" | "doctor_accepted" | "sub_expiring" | "renewal_approved";

const ROUTE_MAP: Record<NotifType, string> = {
  plan_ready:        "/(tabs)/meals",
  doctor_accepted:   "/doctor/connection-status",
  sub_expiring:      "/(tabs)/profile",
  renewal_approved:  "/(tabs)/profile",
};

// ─── Listeners ──────────────────────────────────────────────────────────────

/**
 * Wire foreground display + tap-navigation listeners.
 * Call once after successful login. Returns a cleanup function.
 * No-op in Expo Go.
 */
export function setupNotificationListeners(
  router: { push: (route: string) => void },
): () => void {
  if (!N) return () => {};

  // Tap on a notification (foreground or background)
  const tapSub = N.addNotificationResponseReceivedListener(
    (response) => {
      const type = response.notification.request.content.data?.type as
        | NotifType
        | undefined;
      const route = type ? ROUTE_MAP[type] : null;
      if (route) {
        router.push(route);
      }
    },
  );

  return () => {
    tapSub.remove();
  };
}
