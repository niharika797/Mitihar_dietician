## The Doctor — Who They Are and What They Control

---

### Who is the Doctor?

The doctor is your **primary client** — the person paying you ₹250/patient/month. They are a certified dietician or nutritionist who uses Mityahar as their professional clinical tool. They don't build the system. They don't manage the platform. They use it daily to manage their patients' diet journeys.

Think of it like this:

```
Doctor = Professional using your platform as their work tool
       = Your direct paying customer
       = The bridge between Mityahar and patients
```

The doctor's relationship is with their patients. Your relationship is with the doctor. The doctor never talks to admin unless something goes wrong.

---

### The Doctor's Powers — Every Single One

---

#### 1. Patient Request Management
This is the doctor's first and most important daily task — the approval gate.

**What doctor can do:**
- View all incoming patient registration requests in real time
- See each request's details — name, phone, email, age submitted by patient
- Accept a request → patient gets activated, subscription starts, one code consumed
- Reject a request → patient gets a notification, account stays locked
- Add a note when rejecting (e.g. "Please visit clinic first before joining")
- View history of all accepted and rejected requests

**Why this matters:** This is the security gate you designed. No random person can enter the system. Doctor personally knows every patient they approve. This is also what justifies the doctor's authority on the platform — they are clinically responsible for who they take on.

---

#### 2. Patient Profile — Full View
Once a patient is activated, doctor has complete visibility into that patient's health profile.

**What doctor can see per patient:**
- Full personal details (name, age, gender, phone, email)
- Physical stats (height, weight, current BMI, BMR, TDEE)
- Health goals (lose weight, manage diabetes etc.)
- Medical conditions declared during onboarding
- Food allergies and intolerances
- Dietary preferences (vegetarian, jain, regional etc.)
- Lifestyle information (activity level, sleep, occupation)
- Current eating habits declared at onboarding
- Profile completion status
- Date they joined and activation history

**Why this matters:** Doctor needs the full clinical picture before they can meaningfully refine any recommendation. This replaces the paper file a doctor normally maintains for each patient.

---

#### 3. Patient Monitoring — What They're Actually Eating
Doctor can track every patient's real daily behavior — not just what was recommended.

**What doctor can see:**
- Daily meal logs — what the patient actually ate vs what was recommended
- Time of eating for each meal
- Any substitutions the patient made (recommended sprouts, patient ate cucumber instead)
- Water intake logs per day
- Steps count per day
- Weight log history — track whether patient is progressing toward goal
- Weekly adherence rate — what percentage of recommendations the patient followed
- Days where patient logged nothing (flagged as inactive days)
- Progress graphs — weight over time, water intake trends, meal adherence trends

**Why this matters:** A dietician's job is not just to prescribe — it's to monitor and adjust. Without this data, the doctor is flying blind between clinic visits. Mityahar gives the doctor a live window into every patient's daily behavior.

---

#### 4. Recommendation Management — Refine and Approve
Doctor can directly intervene in what the AI recommends to each patient.

**What doctor can do:**
- View the AI-generated 7-day meal plan for any patient
- Approve the plan as-is
- Edit specific meals — swap one item for another
- Remove a meal item entirely and replace it manually
- Add portion size guidance per meal per patient
- Add a personal note to a meal (e.g. "Have this after morning walk only")
- Regenerate the plan if they're not satisfied with AI output
- View recommendation history — what was recommended in previous weeks
- Compare recommended vs actual eaten side by side

**Why this matters:** The AI gives a starting point. The doctor gives it clinical authority. No two patients are the same — a diabetic patient and a weight loss patient might get similar AI recommendations but the doctor knows the difference and adjusts accordingly.

---

#### 5. Recipe and Food Management
Doctor can expand the food database beyond what exists.

**What doctor can do:**
- Browse the entire food database (all 6,000+ items)
- Search food items by name, cuisine, diet type, course
- Add a completely new recipe:
  - Fill name (mandatory)
  - Optionally fill ingredients, instructions, nutrition, portion size
  - If left blank → system auto-fetches from internet
  - Preview the recipe before saving
- After adding recipe → choose to assign it to:
  - One specific patient
  - All patients under this doctor
  - Just add to database without assigning yet
- Edit a recipe they added (cannot edit original dataset items)
- View all custom recipes they have added

**Why this matters:** Indian dieticians work with highly regional, seasonal, and traditional foods. A doctor in Gujarat will prescribe Khichdi variations that no generic dataset would have. This feature makes Mityahar clinically relevant rather than generic.

---

#### 6. Patient List Management
Doctor manages their full patient roster.

**What doctor can do:**
- View complete list of all their patients — active, expired, pending
- Search and filter patients by name, status, condition, diet type
- View a patient's summary card without opening full profile
- Remove a patient from their list:
  - Patient loses doctor-connected status
  - Patient drops to Tier 1 standalone automatically
  - Patient's historical data is preserved
- Archive an inactive patient (keeps data, removes from active view)
- Transfer a patient to another doctor on the platform (admin must confirm)
- See at a glance which patients haven't logged anything in X days (inactivity flag)

**Why this matters:** A doctor with 30 patients needs to quickly identify who needs attention and who is doing fine. This is their patient management command centre.

---

#### 7. Doctor's Personal Dashboard
The first thing a doctor sees when they log in — their daily overview.

**What doctor sees on dashboard:**
- Total active patients count
- Pending patient requests awaiting approval
- Patients whose subscription expires this week (reminder to renew codes)
- Patients who haven't logged a meal in 3+ days (flagged for follow-up)
- Patients who haven't been meeting their water targets
- New custom recipes added recently
- Remaining unused activation codes count
- Quick access to recently viewed patients

**Why this matters:** Doctor's time is limited. They need to open the dashboard and instantly know who needs attention today. No digging through lists.

---

#### 8. Activation Code and Subscription Visibility
Doctor has full visibility into their own code and subscription status.

**What doctor can see:**
- Total codes purchased historically
- Codes used vs codes remaining
- Which code was used by which patient
- When each patient's subscription expires
- Total active patients this month (= their billing amount)
- Payment history to Mityahar
- Upcoming renewal amounts

**What doctor CANNOT do:**
- Generate codes themselves
- Extend a patient's subscription without a code
- Modify billing amounts

**Why this matters:** Doctor needs to plan ahead. If they have 2 codes left and 5 patients want to join — they know to buy more codes before accepting those requests.

---

#### 9. Communication and Notes
Doctor can leave clinical notes linked to each patient.

**What doctor can do:**
- Add private clinical notes per patient (not visible to patient)
- Add notes to specific meal recommendations (visible to patient)
- Flag a patient for urgent review
- Mark a patient as progressing well / not progressing / at risk

**Why this matters:** In a real clinical setting, a doctor keeps notes. Mityahar should replace the paper notebook entirely, not complement it.

---

#### 10. Doctor's Own Profile Management
Doctor manages their professional profile on the platform.

**What doctor can do:**
- Edit their display name, specialisation, clinic address, phone
- Upload a professional photo (shown to patients in Find a Doctor feature)
- Set their working hours / availability (shown to standalone users browsing nearby doctors)
- Change their login password
- Enable / disable two-factor authentication (MFA)
- View their own login history and active sessions

**Why this matters:** When standalone users browse nearby doctors, they see the doctor's profile. A complete, professional-looking profile increases the chance of a standalone user requesting to connect. This directly increases the doctor's patient count and your revenue.

---

### What Doctor CANNOT Do — The Hard Boundaries

These are non-negotiable system rules:

- ❌ Cannot see another doctor's patients — ever. Even if they know the patient personally
- ❌ Cannot generate activation codes — only admin can
- ❌ Cannot modify billing or subscription amounts
- ❌ Cannot access admin dashboard or any admin function
- ❌ Cannot delete a patient's account — only remove them from their own list
- ❌ Cannot edit food items from the original dataset — only items they added themselves
- ❌ Cannot approve their own account changes — admin manages doctor accounts
- ❌ Cannot see platform-wide statistics — only their own data
- ❌ Cannot transfer a patient to another doctor without admin confirmation

**Why these boundaries matter:** Data isolation is both a legal requirement and a trust requirement. Doctor Ashok should never accidentally or intentionally see Doctor Priya's patients. This is enforced at the database query level — every query is automatically scoped to the requesting doctor's ID from their JWT token.

---

### Doctor's Daily Workflow — How It All Connects

```
Morning — Doctor opens dashboard
            ↓
   Sees 2 pending patient requests
            ↓
   Reviews profiles, accepts both
            ↓
   2 codes consumed automatically
            ↓
   Reviews flagged patients 
   (3 haven't logged in 4 days)
            ↓
   Checks their meal logs and progress
            ↓
   Refines next week's meal plan 
   for one patient with kidney issue
            ↓
   Adds a new Gujarati recipe 
   for a patient who requested it
            ↓
   Assigns it to that patient only
            ↓
   Sees 4 subscriptions expiring
   next week — reminder to buy codes
            ↓
   Logs off
```

This entire workflow happens in one dashboard. No paper. No WhatsApp messages to patients. No manual Excel tracking. Everything in one place.

---

### Summary — Doctor in One Simple Picture

```
         DOCTOR
            │
   ┌────────┼────────┐
   │        │        │
Manages  Manages  Manages
Patients  Recipes   Own
   │        │      Account
   │        │        │
Accept/  Add new   Profile
Reject   recipes   Password
requests Assign    MFA
   │     to        Codes
Monitor  patients  remaining
logs &      │
progress    └── Goes to
Refine          food DB
plans           (admin
                approves)
```

Doctor sees only their own world. Powerful within it. Completely blind to everything outside it.

---
