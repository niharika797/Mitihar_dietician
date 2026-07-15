# Mitihar — FCM Push Notifications
> Written: 2026-03-20
> Status: NOT STARTED — hard blocked on Firebase manual setup
> Phase: 5 | Task count: 19 | Related: Task_List.md (Phase 5 section)

---

## What is FCM?

FCM (Firebase Cloud Messaging) is Google's free push notification service.
It is the standard delivery pipeline for mobile notifications on both Android and iOS.

```
Mitihar backend  →  Firebase servers  →  Patient's phone
```

The backend sends a message to Firebase identifying the target device (via its FCM token)
and what to show. Firebase handles waking the phone and displaying the notification,
even when the app is fully closed.

---

## Why Mitihar Needs It

Four events currently happen silently — the patient only finds out when they manually
open the app:

| Event | Current state | With FCM |
|---|---|---|
| Doctor accepts request | Patient has no idea | Phone notification instantly |
| Meal plan is ready after onboarding | Patient sees spinner, has to wait | "Your plan is ready!" notification |
| Subscription expiring (≤4 days left) | Patient misses it until too late | Reminder notification sent by cron |
| Doctor approved renewal | Patient doesn't know | "Renewed! You have 30 more days" |

---

## The Hard Blocker — Manual Firebase Setup (Do This First)

**No code can be written until these 3 things are done manually.**
They require your Google account and the Firebase console. They cannot be automated.

### Step 1 — Create Firebase Project

1. Go to https://console.firebase.google.com
2. Click "Add project" → name it `mitihar` (or `mitihar-prod`)
3. Disable Google Analytics (not needed)
4. Project is created — takes ~30 seconds

### Step 2 — Add Android App

1. In the project, click "Add app" → Android icon
2. Android package name: `com.mitihar.patient`
   (this is already set in `mitihar-patient-app/app.config.ts`)
3. App nickname: Mitihar Patient
4. Download the file: `google-services.json`
5. Place it at: `mitihar-patient-app/google-services.json`
   (already gitignored via `.gitignore`)

### Step 3 — Add iOS App

1. Click "Add app" → iOS icon
2. iOS bundle ID: `com.mitihar.patient`
   (this is already set in `mitihar-patient-app/app.config.ts`)
3. App nickname: Mitihar Patient iOS
4. Download the file: `GoogleService-Info.plist`
5. Place it at: `mitihar-patient-app/GoogleService-Info.plist`
   (already gitignored)

### Step 4 — Generate Backend Service Account

1. In Firebase console → Project Settings (gear icon top left)
2. Click "Service accounts" tab
3. Click "Generate new private key"
4. Download the file — rename it to `firebase_service_account.json`
5. Place it at the backend root:
   `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\firebase_service_account.json`
6. Add to `.env`:
   `FIREBASE_SERVICE_ACCOUNT_PATH=./firebase_service_account.json`
7. Add to `.env.example`:
   `FIREBASE_SERVICE_ACCOUNT_PATH=./firebase_service_account.json`

**Once all 4 steps are done, the 19 coding tasks below can begin.**

---

## Full Task List (19 tasks)

### Backend — 9 tasks

- [ ] Add `firebase-admin` to `requirements.txt`
- [ ] Add `fcm_token` column (String, nullable) to `patients` table in `db_models.py`
- [ ] Write Alembic migration for `fcm_token` column
      Run: `alembic revision --autogenerate -m "add_fcm_token_to_patients"`
      Then: `alembic upgrade head`
- [ ] Create `app/services/notification_service.py` with:
      - `init_firebase()` — loads service account JSON, initialises firebase_admin app
      - `send_push(fcm_token, title, body, data={})` — sends via `messaging.send()`
      - `notify_plan_ready(patient)` — "Your meal plan is ready 🥗"
      - `notify_doctor_accepted(patient)` — "Dr. [Name] accepted your request 🎉"
      - `notify_sub_expiring(patient, days_left)` — "Your plan expires in N days"
      - `notify_renewal_approved(patient)` — "Your subscription has been renewed ✅"
- [ ] Call `init_firebase()` in `main.py` lifespan startup (after APScheduler starts)
- [ ] Add `POST /auth/register-fcm-token` endpoint — stores FCM token on Patient row
      Body: `{ "fcm_token": "..." }`
      Authenticated route — patient must be logged in
- [ ] Wire `notify_plan_ready()` into `patients.py` onboarding auto-generation
      Call it after `store_diet_plan()` succeeds (fire-and-forget, never block onboarding)
- [ ] Wire `notify_doctor_accepted()` into `auth.py` `accept_request` endpoint
      Call after `doctor_id` is set on patient row
- [ ] Wire `notify_sub_expiring()` into daily expiry cron in `main.py`
      Call for each patient where `expiring_soon` just flipped to True
- [ ] Wire `notify_renewal_approved()` into `doctor.py` `approve_renewal` endpoint
      Call after token_1_active is reset to True

### Patient App — 10 tasks

- [ ] Install `expo-notifications`:
      `pnpm add expo-notifications`
- [ ] Update `mitihar-patient-app/app.config.ts`:
      - Add `"expo-notifications"` to the `plugins` array
      - Add `"googleServicesFile": "./google-services.json"` under `android`
      - Add `"googleServicesFile": "./GoogleService-Info.plist"` under `ios`
- [ ] Create `mitihar-patient-app/lib/notifications.ts` with:
      - `requestPermissions()` — asks user for notification permission
      - `getFCMToken()` — gets the device's FCM token from expo-notifications
      - `sendTokenToBackend(token)` — calls `POST /auth/register-fcm-token`
      - `setupNotificationListeners(router)` — handles foreground notification display +
        tap-to-navigate (e.g. tap on "plan ready" → opens Meals tab)
- [ ] Wire into `mitihar-patient-app/app/_layout.tsx`:
      After `loginSuccess()` or `setTokens()` fires (i.e. after any successful auth):
      1. Call `requestPermissions()`
      2. Call `getFCMToken()`
      3. Call `sendTokenToBackend(token)`
      4. Call `setupNotificationListeners(router)`
- [ ] Handle notification tap navigation:
      - "plan_ready" → `router.replace("/(tabs)/meals")`
      - "doctor_accepted" → `router.replace("/doctor/connection-status")`
      - "sub_expiring" → `router.replace("/(tabs)/profile")`
      - "renewal_approved" → `router.replace("/(tabs)/profile")`
- [ ] Handle foreground notifications (app is open):
      Show a toast via `useToast()` instead of a system notification
      Use `Notifications.addNotificationReceivedListener()`
- [ ] Update `mitihar-patient-app/store/useAuthStore.ts`:
      On `logout()`, also clear the FCM token from the backend:
      Call `POST /auth/register-fcm-token` with `{ "fcm_token": null }` before clearing local state
      (Prevents the old device receiving notifications after the user logs out)
- [ ] Wire `profile/notifications.tsx` toggle states:
      Currently all toggles are placeholders (no API calls)
      Add `POST /users/me/notification-preferences` endpoint (new backend endpoint)
      Store preferences as JSONB on Patient row: `notification_preferences: { plan_ready: true, ... }`
      Respect preferences in `notification_service.py` before sending each type
- [ ] Handle edge case — FCM token refresh:
      Expo FCM tokens can change (device reinstall, app update). Use
      `Notifications.addPushTokenListener()` to detect changes and re-send to backend
- [ ] Test on physical device (emulators don't receive FCM on all platforms):
      Android: works on emulator with Google Play Services
      iOS: requires real device for push notifications (Simulator cannot receive them)

---

## Notification Payload Formats

```python
# plan_ready
{
  "title": "Your meal plan is ready! 🥗",
  "body": "7 days of personalised meals are waiting for you.",
  "data": { "type": "plan_ready" }
}

# doctor_accepted
{
  "title": "Dr. [Name] accepted your request 🎉",
  "body": "You're now connected. Your plan will be generated shortly.",
  "data": { "type": "doctor_accepted" }
}

# sub_expiring
{
  "title": "Your subscription expires in [N] days ⏳",
  "body": "Ask your doctor for a renewal to keep your meal plan active.",
  "data": { "type": "sub_expiring", "days_left": "3" }
}

# renewal_approved
{
  "title": "Subscription renewed! ✅",
  "body": "Dr. [Name] approved your renewal. 30 more days active.",
  "data": { "type": "renewal_approved" }
}
```

---

## Environment Variables to Add

In `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\.env`:
```
FIREBASE_SERVICE_ACCOUNT_PATH=./firebase_service_account.json
```

In `.env.example`:
```
# Firebase Admin SDK — download from Firebase console → Project Settings → Service Accounts
FIREBASE_SERVICE_ACCOUNT_PATH=./firebase_service_account.json
```

---

## Files to Be Modified / Created

| File | Action |
|---|---|
| `requirements.txt` | Add `firebase-admin` |
| `app/models/db_models.py` | Add `fcm_token` column to Patient |
| `app/services/notification_service.py` | Create new file |
| `app/main.py` | Call `init_firebase()` in lifespan |
| `app/routers/auth.py` | Add `POST /auth/register-fcm-token` |
| `app/routers/patients.py` | Wire `notify_plan_ready()` |
| `app/routers/doctor.py` | Wire `notify_doctor_accepted()`, `notify_renewal_approved()` |
| `mitihar-patient-app/app.config.ts` | Add expo-notifications plugin + JSON file paths |
| `mitihar-patient-app/lib/notifications.ts` | Create new file |
| `mitihar-patient-app/app/_layout.tsx` | Wire permission + token sending after auth |
| `mitihar-patient-app/app/profile/notifications.tsx` | Wire toggle states to backend |
| `mitihar-patient-app/store/useAuthStore.ts` | Clear FCM token on logout |
| `.env` | Add `FIREBASE_SERVICE_ACCOUNT_PATH` |
| `.env.example` | Add `FIREBASE_SERVICE_ACCOUNT_PATH` placeholder |

---

## Implementation Order (Once Firebase Setup is Done)

```
1. Backend migration (fcm_token column) + alembic upgrade head
2. notification_service.py + init_firebase in main.py
3. POST /auth/register-fcm-token endpoint
4. Wire the 4 notification triggers in backend routers
5. Patient app: install expo-notifications + update app.config.ts
6. Patient app: lib/notifications.ts + wire into _layout.tsx
7. Patient app: test on physical Android device
8. Patient app: test on physical iOS device
9. Wire notifications.tsx preference toggles (lower priority — UI polish)
```

---

## Estimated Work

Once Firebase files are in place: **2–3 days** for a developer familiar with the codebase.
Backend work (~1 day) is straightforward — it's mostly wiring existing logic.
Patient app work (~1–2 days) requires Expo-specific knowledge and device testing.

---

## Score

**Current: 0 / 19**
Hard blocked on Firebase manual setup (Steps 1–4 above).
