## 🔴 ADMIN DASHBOARD (Web — React, Desktop)

---

### Admin Screens

```
SIDEBAR NAVIGATION:
[ Overview ]
[ Doctors ]
[ Patients ]
[ Food Database ]
[ Codes & Billing ]
[ Audit Logs ]
[ Settings ]
[ Logout ]
```

---

#### OVERVIEW

```
Screen: Admin Overview Dashboard
┌─────────────────────────────────────────────────────┐
│ Mityahar Admin Dashboard          Feb 25, 2026      │
├────────┬────────┬────────┬────────┬─────────────────┤
│ Total  │ Active │ Total  │ Active │ Revenue         │
│ Doctors│ Doctors│Patients│Patients│ This Month      │
│   8    │   6    │  312   │  247   │ ₹61,750         │
└────────┴────────┴────────┴────────┴─────────────────┘
│                                                      │
│ DOCTORS BREAKDOWN                                   │
│ Dr. Ashok Mehta      24 active patients    ₹6,000  │
│ Dr. Priya Shah       18 active patients    ₹4,500  │
│ Dr. Ravi Kumar       31 active patients    ₹7,750  │
│ ...                                                  │
│                                                      │
│ PLATFORM GROWTH                                     │
│ [Line chart — patients over last 6 months]          │
│                                                      │
│ ⚠️  ALERTS                                          │
│ • Dr. Mehta billing overdue — March payment        │
│ • 3 doctors have < 5 codes remaining               │
└─────────────────────────────────────────────────────┘
```

---

#### DOCTORS SECTION

```
Screen 1: All Doctors List
┌─────────────────────────────────────────────────────┐
│ Doctors                              [ + Add Doctor ]│
├──────────────────┬────────┬──────────┬──────────────┤
│ Name             │ Status │ Patients │ Revenue MTD  │
├──────────────────┼────────┼──────────┼──────────────┤
│ Dr. Ashok Mehta  │ Active │   24     │ ₹6,000       │
│ Dr. Priya Shah   │ Active │   18     │ ₹4,500       │
│ Dr. Ravi Kumar   │ Active │   31     │ ₹7,750       │
│ Dr. Sonal Desai  │ Inactive│  0      │ ₹0           │
└──────────────────┴────────┴──────────┴──────────────┘

Screen 2: Add New Doctor
┌─────────────────────────────────────────────────────┐
│ ← Add New Doctor                                    │
│                                                      │
│ Full Name *          [________________________]     │
│ Email *              [________________________]     │
│ Phone *              [________________________]     │
│ Specialisation *     [________________________]     │
│ Clinic Name          [________________________]     │
│ Clinic Address       [________________________]     │
│ City                 [________________________]     │
│ Languages Spoken     [________________________]     │
│                                                      │
│ System will auto-generate Doctor ID                 │
│ and send login credentials to their email.          │
│                                                      │
│ Initial code pack:                                  │
│ [ 10 codes ] [ 20 codes ] [ 50 codes ] [ Custom ]   │
│                                                      │
│ [ Create Doctor Account ]                           │
└─────────────────────────────────────────────────────┘

Screen 3: Individual Doctor View
Full profile, patient list, code history,
billing history, activity log, 
[ Deactivate ] [ Delete ] buttons
```

---

#### FOOD DATABASE SECTION

```
Screen 1: Food Database
┌─────────────────────────────────────────────────────┐
│ Food Database          🔍 Search...    Filter ▼     │
│ 6,871 items   [ + Add Item ]   [ Bulk Import ]      │
│                                                      │
│ [ All ] [ Verified ✅ ] [ Pending Nutrition ⚠️ ] [ Custom 👨‍⚕️ ]
│                                                      │
│ Palak Paneer   Veg|Dinner   410 cal  ✅  [Edit][Del]│
│ Poha           Veg|Breakfast 320 cal ✅  [Edit][Del]│
│ New Recipe*    Veg|Lunch     —  ⚠️  [Approve][Del] │
│ (* added by Dr. Ashok — pending approval)           │
└─────────────────────────────────────────────────────┘

Screen 2: Approve/Reject Doctor Recipe
Shows full recipe details, nutrition data fetched,
admin reviews and approves or rejects with note
```

---

#### CODES & BILLING SECTION

```
Screen 1: Platform Billing Overview
┌─────────────────────────────────────────────────────┐
│ Billing — March 2026                                │
│                                                      │
│ TOTAL PLATFORM REVENUE THIS MONTH                   │
│ ₹61,750 (247 active patients × ₹250)               │
│                                                      │
│ STATUS BREAKDOWN                                    │
│ Paid:    ₹54,250  (5 doctors)  ✅                  │
│ Pending: ₹7,500   (1 doctor)   ⚠️                  │
│ Overdue: ₹0                                         │
│                                                      │
│ GENERATE CODES FOR DOCTOR                           │
│ Select doctor: [Dr. Ashok ▼]                       │
│ Quantity: [ 10 ] [ 20 ] [ 50 ] [ Custom ]          │
│ Amount: ₹2,500  (10 × ₹250)                        │
│ [ Generate & Send to Doctor ]                       │
│                                                      │
│ BILLING HISTORY (all doctors)                       │
│ [Table of all monthly payments]                     │
└─────────────────────────────────────────────────────┘
```

---

#### AUDIT LOGS SECTION

```
Screen: Audit Logs
┌─────────────────────────────────────────────────────┐
│ Audit Logs                    🔍 Filter by action ▼ │
│                                                      │
│ Feb 25, 09:14  Dr. Ashok accepted Anjali Verma     │
│ Feb 25, 09:10  Admin created Dr. Sharma account    │
│ Feb 25, 08:55  Dr. Priya added recipe "Methi Thepla"│
│ Feb 24, 22:30  Radha Sharma subscription expired   │
│ Feb 24, 18:00  20 codes generated for Dr. Ravi     │
│ Feb 24, 14:22  Dr. Ashok removed patient Mohan     │
│ ...                                                  │
│                                                      │
│ [ Export as CSV ]                                   │
└─────────────────────────────────────────────────────┘
```

---

## Complete User Flow — All Three Roles in One Picture

```
PATIENT (TIER 2) COMPLETE FLOW:

Download App
    ↓
Welcome Screen → Google Login
    ↓
"Do you have a doctor?" → Yes
    ↓
Enter doctor code / select doctor
    ↓
Submit registration request
    ↓
Waiting screen ←————————————————————————┐
    ↓                                    │
                              DOCTOR receives notification
                              Views request on dashboard
                              Accepts → 1 code consumed
                                         ↑
                              ADMIN generated codes
                              and issued to doctor
    ↓
Patient notified → "You're approved!"
    ↓
Fill 7-section health questionnaire
    ↓
BMI/BMR/TDEE calculated and shown
    ↓
First meal plan auto-generated
    ↓
HOME DASHBOARD — daily usage begins:
    ↓
Morning: Open app → See breakfast → Cook → Log meal
    ↓
Midday: See lunch → Log meal → Log water
    ↓
Evening: See dinner → Log meal → Log steps
    ↓
Night: See daily nutrition summary → Check progress
    ↓
Every Sunday: New week plan appears
    ↓                    ↑
              DOCTOR reviews logs weekly
              Refines next week's plan
              Adds notes to specific meals
    ↓
Month end → Subscription expires
    ↓
App locked → "Contact your doctor"
    ↓
DOCTOR renews → buys more codes → patient reactivated
    ↓
Cycle continues
```
