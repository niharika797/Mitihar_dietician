## The Admin — Who They Are and What They Control

---

### Who is the Admin?

The admin is **you and your core team** — the people who built Mityahar and own the platform. Not the doctors. Not the patients. The admin is the invisible engine room that keeps the entire system running.

Think of it like this:

```
Admin = Platform Owner
Doctor = Client using the platform  
Patient = End user of the platform
```

The admin never interacts with patients directly. The admin never prescribes diet plans. The admin's job is to **control, monitor, and maintain the entire business and system.**

---

### The Admin's Powers — Every Single One

---

#### 1. Doctor Management
This is the most important admin power. Nobody becomes a doctor on Mityahar without the admin's action.

**What admin can do:**
- Add a new doctor to the system (name, email, phone, address, specialization, clinic name)
- System auto-generates a unique Doctor ID
- Send doctor their login credentials
- Deactivate a doctor temporarily (without deleting their data)
- Permanently remove a doctor (with data handling rules — patients go inactive or get transferred)
- Edit doctor's details if something changes
- Reset a doctor's password if they're locked out
- View doctor's full profile and account history

**Why this matters:** No doctor can self-register. You control exactly who represents your platform. If a doctor behaves badly or stops paying — you switch them off in one click.

---

#### 2. Activation Code Management
Admin is the only one who generates and issues codes. This is your financial control lever.

**What admin can do:**
- Generate a batch of codes for a specific doctor (e.g. 20 codes for Doctor Ashok)
- Set expiry on code batches (e.g. codes must be used within 6 months of purchase)
- View all codes — issued, used, unused, expired — per doctor
- Revoke a code batch if a doctor's payment bounces
- Manually issue emergency codes in exceptional cases
- View full code consumption history per doctor

**Why this matters:** This is where your revenue control lives. No payment = no new codes issued. Doctor can't onboard new patients. System enforces itself.

---

#### 3. Subscription and Billing Management
Admin sees the full financial picture of the entire platform.

**What admin can do:**
- View monthly billing for every doctor (how many active patients × ₹250)
- Generate invoices per doctor per month automatically
- Mark a payment as received
- Flag a doctor as payment overdue
- Set subscription to expired if payment not received by due date — which auto-locks all their patients
- View total platform revenue — monthly, quarterly, yearly
- Apply discounts or custom pricing to specific doctors (annual plan, early adopter discount etc.)
- View complete billing history of every doctor since they joined

**Why this matters:** This replaces every manual spreadsheet. Admin always knows exactly how much money is coming in and from whom.

---

#### 4. Platform-Wide Monitoring Dashboard
The admin sees the entire system at a glance — something neither doctors nor patients can see.

**What admin sees:**
- Total registered doctors (active / inactive)
- Total patients across all doctors (active / expired / standalone)
- Total Tier 1 standalone users
- Total Tier 2 doctor-connected users
- Monthly active users (MAU)
- New patients joined this month
- Patients churned this month
- Revenue this month vs last month
- Which doctors have the most patients
- Which doctors have high patient dropout rates (warning sign)
- Platform growth trend over time (graph)

**Why this matters:** This is how you make business decisions. Which city has the most standalone users? Time to recruit a doctor there. Which doctor has 80% patient dropout? Maybe their patients are unhappy — reach out.

---

#### 5. Food Dataset Management
Admin controls the master food database that every doctor and every AI recommendation runs on.

**What admin can do:**
- View all food items in the database
- Add new food items directly (without going through a doctor)
- Approve or reject food items added by doctors before they go live
- Edit existing food items (fix wrong nutrition values, update images)
- Remove food items that are incorrect or inappropriate
- Trigger bulk nutrition enrichment (call Edamam API for items missing nutrition data)
- View which food items are used most in recommendations
- Manage custom recipes added by doctors — approve, reject, edit

**Why this matters:** Every meal recommendation across every patient comes from this database. If bad data enters, bad recommendations go out. Admin is the quality gatekeeper.

---

#### 6. System Configuration and Settings
Admin controls global platform settings that apply to everyone.

**What admin can do:**
- Set global subscription pricing (if you change ₹250 to ₹300 — one setting change affects all)
- Set code batch sizes and pricing
- Configure free trial periods for new doctors
- Set how many days before expiry the doctor gets a reminder notification
- Configure grace period after expiry (e.g. 3-day grace before hard lock)
- Set password policies for doctor accounts
- Configure which diet type tags are available in the system
- Add new cuisine types or meal categories to the food system
- Enable or disable Tier 1 standalone free access globally

**Why this matters:** As the business evolves, admin can change rules without touching the codebase. Configuration lives in the database, not in code.

---

#### 7. User Support and Dispute Resolution
When something goes wrong, admin has override powers.

**What admin can do:**
- View any patient's account (full read access for support purposes)
- Manually extend a patient's subscription if there was a payment dispute
- Transfer a patient from one doctor to another (if doctor leaves platform)
- Reactivate an expired account during dispute resolution
- Reset a doctor's or patient's password
- View full login history of any account (useful for fraud investigation)
- Permanently delete a patient's data on request (DPDP Act compliance — right to erasure)
- Handle doctor offboarding — archive their data, notify their patients

**Why this matters:** Things go wrong. Payments fail. Doctors leave. Patients complain. Admin has the surgical tools to fix any situation without breaking the system.

---

#### 8. Audit Logs and Compliance
Admin can see a full paper trail of everything that happened on the platform.

**What admin sees:**
- Every doctor login — timestamp, IP address, device
- Every patient activation — which code, which doctor, when
- Every subscription expiry and renewal
- Every food item added or modified and by whom
- Every admin action taken and by whom (if multiple admin accounts exist)
- Every failed login attempt (security monitoring)
- Data export requests (DPDP Act compliance)

**Why this matters:** If a dispute happens — "I paid but my patients are still locked" — the audit log shows exactly what happened and when. Also required for legal compliance.

---

#### 9. Doctor Performance Insights
Admin can see how well each doctor is using the platform.

**What admin can see per doctor:**
- How many patients they've activated since joining
- How many patients are currently active vs expired
- How many patients renewed vs dropped
- How many custom recipes that doctor has added
- How frequently the doctor logs into their dashboard
- Average patient retention rate per doctor

**Why this matters:** You can identify your best doctors (great for case studies and marketing) and your struggling ones (reach out, offer support, prevent churn). This data helps you grow the business intelligently.

---

#### 10. Multi-Admin Support
The admin side is not just one person — your whole team can have access with different permission levels.

**Example team structure:**
```
Super Admin (you)          → Full access to everything
Operations Admin           → Billing, doctor management, support
Technical Admin            → System config, food dataset, logs
Finance Admin              → Billing reports only, no patient data
```

**Why this matters:** You don't give your entire team access to patient health data. Each person sees only what their role requires. This is also a DPDP Act compliance requirement.

---

### What Admin CANNOT Do — The Boundaries

Just as important as what admin can do:

- ❌ Admin cannot see a patient's personal health data (height, weight, medical conditions) by default — only in support scenarios with audit log entry
- ❌ Admin cannot modify a doctor's recommendations or meal plans
- ❌ Admin cannot impersonate a doctor or patient without leaving an audit trail
- ❌ Admin cannot delete billing records (can only archive)
- ❌ Admin cannot bypass their own audit log — every admin action is recorded

**Why these boundaries matter:** Patient health data is sensitive. If your team can freely browse patient medical profiles — that is a DPDP Act violation. Admin access to patient data should be exceptional, logged, and justified.

---

### Summary — Admin in One Simple Picture

```
         YOU (Admin)
              │
    ┌─────────┼──────────┐
    │         │          │
 Controls  Controls   Controls
 Doctors   Money      System
    │         │          │
  Add/      Codes     Food DB
  Remove    Billing   Config
  Doctors   Revenue   Settings
    │         │          │
    └────All flow through admin────┘
              │
         Doctors see
         only their
         own patients
              │
         Patients see
         only their
         own data
```

Admin is the only role that sees the **entire platform** end to end. Doctor sees their slice. Patient sees their slice. Admin sees everything — and controls everything.

