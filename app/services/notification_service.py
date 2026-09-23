"""
notification_service.py
=======================
Firebase Cloud Messaging (FCM) push notification service for Mitihar.

Initialise once at app startup via init_firebase().
All notify_* helpers are fire-and-forget — they never raise, so a
notification failure never breaks the operation that triggered it.

Notification types:
  plan_ready        — patient's first meal plan has been generated
  doctor_accepted   — doctor accepted the patient's connection request
  sub_expiring      — subscription expires in N days (sent by cron)
  renewal_approved  — doctor approved a renewal request
"""

import logging
import os
from typing import Optional

_log = logging.getLogger(__name__)
_firebase_app = None   # singleton — set by init_firebase()


# ─────────────────────────────────────────────────────────────────────────────
# Initialisation
# ─────────────────────────────────────────────────────────────────────────────

def init_firebase() -> None:
    """
    Load the service-account JSON and initialise the firebase_admin app.
    Called once from main.py lifespan on startup.
    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _firebase_app
    if _firebase_app is not None:
        return  # already initialised

    path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "./firebase_service_account.json")
    if not os.path.exists(path):
        _log.warning(
            "Firebase service account file not found at '%s'. "
            "Push notifications are DISABLED. "
            "Download it from Firebase console → Project Settings → Service Accounts.",
            path,
        )
        return

    try:
        import firebase_admin
        from firebase_admin import credentials
        cred = credentials.Certificate(path)
        _firebase_app = firebase_admin.initialize_app(cred)
        _log.info("Firebase Admin SDK initialised successfully.")
    except Exception as exc:
        _log.error("Failed to initialise Firebase Admin SDK: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Core send helper
# ─────────────────────────────────────────────────────────────────────────────

def send_push(
    fcm_token: Optional[str],
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> bool:
    """
    Send a single FCM push notification to a device token.

    Returns True on success, False on any failure (token invalid, Firebase
    unreachable, SDK not initialised). Never raises — caller should not need
    to handle notification failures.
    """
    if not fcm_token:
        return False
    if _firebase_app is None:
        _log.debug("send_push called but Firebase is not initialised — skipping.")
        return False

    try:
        from firebase_admin import messaging
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=fcm_token,
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                headers={"apns-priority": "10"},
            ),
        )
        response = messaging.send(message)
        _log.debug("FCM message sent: %s", response)
        return True
    except Exception as exc:
        _log.warning("FCM send failed (token=%s...): %s", fcm_token[:20], exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Notification helpers — one per trigger event
# ─────────────────────────────────────────────────────────────────────────────

def notify_plan_ready(patient) -> None:
    """
    Called after onboarding auto-generation succeeds.
    Tells the patient their first meal plan is ready to view.
    """
    send_push(
        fcm_token=getattr(patient, "fcm_token", None),
        title="Your meal plan is ready! 🥗",
        body="7 days of personalised meals are waiting for you.",
        data={"type": "plan_ready"},
    )


def notify_doctor_accepted(patient, doctor_name: str) -> None:
    """
    Called when a doctor accepts a patient's connection request.
    """
    send_push(
        fcm_token=getattr(patient, "fcm_token", None),
        title=f"Dr. {doctor_name} accepted your request 🎉",
        body="You're now connected. Your personalised plan will be generated shortly.",
        data={"type": "doctor_accepted"},
    )


def notify_sub_expiring(patient, days_left: int) -> None:
    """
    Called by the daily expiry cron when token_1_expiry ≤ 4 days away.
    """
    send_push(
        fcm_token=getattr(patient, "fcm_token", None),
        title=f"Your subscription expires in {days_left} day{'s' if days_left != 1 else ''} ⏳",
        body="Ask your doctor for a renewal to keep your meal plan active.",
        data={"type": "sub_expiring", "days_left": str(days_left)},
    )


def notify_renewal_approved(patient, doctor_name: str) -> None:
    """
    Called when a doctor approves a patient's renewal request.
    """
    send_push(
        fcm_token=getattr(patient, "fcm_token", None),
        title="Subscription renewed! ✅",
        body=f"Dr. {doctor_name} approved your renewal. 30 more days active.",
        data={"type": "renewal_approved"},
    )


def notify_weekly_plan_approved(patient, doctor_name: str) -> None:
    """
    Called when a doctor approves a patient's weekly meal plan recommendation.
    """
    send_push(
        fcm_token=getattr(patient, "fcm_token", None),
        title="Your meal plan is ready 🥗",
        body=f"Dr. {doctor_name} has approved your weekly plan.",
        data={"type": "weekly_plan_approved"},
    )


def notify_visit_flagged(patient, doctor_name: str) -> None:
    """
    Called when a doctor flags a visit (patient forgot phone / no Token 2).
    Patient must confirm the pending visit approval in the app.
    """
    send_push(
        fcm_token=getattr(patient, "fcm_token", None),
        title="Visit confirmation needed 📋",
        body=f"Dr. {doctor_name} flagged a visit. Please confirm in the app.",
        data={"type": "visit_flagged"},
    )
