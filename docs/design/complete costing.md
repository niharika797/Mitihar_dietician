Now I have every number needed. Let me compile the complete picture.

---

## Complete Mityahar Cost Breakdown — Everything in ₹ (February 2026)

**Exchange rate used: 1 USD = ₹83.5**

---

## SECTION 1 — ONE-TIME SETUP COSTS

These you pay once. Never again.

| Item | Cost (USD) | Cost (₹) | Notes |
|---|---|---|---|
| Google Play Developer Account | $25 | **₹2,088** | One-time, lifetime, unlimited apps |
| Domain `mityahar.com` first year | $6.79 | **₹567** | New customer rate at Namecheap |
| GCP Account Setup | $0 | **₹0** | Free to create |
| Firebase Account Setup | $0 | **₹0** | Free to create |
| **Total One-Time** | | **₹2,655** | |

---

## SECTION 2 — ANNUAL RECURRING COSTS

These you pay every year.

| Item | Cost (USD/year) | Cost (₹/year) | Cost (₹/month) | Notes |
|---|---|---|---|---|
| Apple Developer Program | $99/year | **₹8,267/year** | ₹689/month | Required for App Store. Must renew every year or your app disappears |
| Domain `mityahar.com` renewal | $13.98/year | **₹1,167/year** | ₹97/month | After first year |
| **Total Annual** | | **₹9,434/year** | **₹786/month** | |

---

## SECTION 3 — MONTHLY INFRASTRUCTURE COSTS (GCP)

### Phase 1 — Launch (6 doctors, ~100 patients)

| Service | What It Does | Monthly Cost (₹) | Notes |
|---|---|---|---|
| Cloud Run — API | Runs your FastAPI backend | ₹0 | Free tier covers 2M requests/month — you won't hit this at launch |
| Cloud Run — ML | Runs meal generator separately | ₹0 | Same free tier applies |
| Cloud SQL PostgreSQL | Your main database (1 vCPU, 3.75GB, 10GB SSD, Mumbai) | ₹3,006 | No free tier for Cloud SQL — this is your biggest cost |
| Cloud Storage | Food images, APK hosting | ₹125 | ~5GB stored + downloads |
| Firebase Auth + FCM | Google OAuth + push notifications | ₹0 | Free up to 50,000 MAU. Push notifications free unlimited |
| Cloudflare CDN + SSL | DDoS protection, SSL, CDN across India | ₹0 | Free plan sufficient at this stage |
| Secret Manager | Stores DB passwords, API keys securely | ₹42 | Negligible |
| GCP Free Credits | New account credit | -₹25,050 | $300 free credits for new GCP customers in first 90 days — covers ~8 months of Cloud SQL |
| **Phase 1 Total** | | **₹3,173/month** | After free credits run out |

---

### Phase 2 — Growth (20 doctors, ~500 patients)

| Service | Monthly Cost (₹) | Change from Phase 1 |
|---|---|---|
| Cloud Run — API + ML | ₹900 | Now beyond free tier — ~5M requests/month |
| Cloud SQL (upgraded: 2 vCPU, 7.5GB RAM) | ₹6,500 | Database needs more compute for 500 patients |
| Cloud Storage | ₹500 | More images, more downloads |
| Firebase Auth + FCM | ₹0 | Still within free tier |
| Cloudflare | ₹0 | Still free tier |
| Cloud Memorystore Redis | ₹2,000 | Added for meal plan caching — reduces DB load |
| Secret Manager | ₹50 | Slightly more secrets |
| **Phase 2 Total** | **₹9,950/month** | |

---

### Phase 3 — Scale (100 doctors, ~5,000 patients)

| Service | Monthly Cost (₹) | Notes |
|---|---|---|
| Cloud Run — API + ML | ₹8,000 | High traffic, multiple instances |
| Cloud SQL (4 vCPU, 15GB RAM, High Availability) | ₹18,000 | HA means automatic failover — no downtime |
| Cloud Storage + CDN | ₹2,000 | Heavy image traffic |
| Firebase Auth + FCM | ₹0 | Still within free 50k MAU tier |
| Cloudflare Pro | ₹1,670 | Upgrade needed for advanced WAF at this scale |
| Cloud Memorystore Redis | ₹4,000 | Larger cache for 5,000 patients |
| Secret Manager | ₹100 | |
| **Phase 3 Total** | **₹33,770/month** | |

---

## SECTION 4 — PAYMENT GATEWAY (Razorpay)

This is the cost of collecting ₹250/patient/month from doctors.

Razorpay charges 2% per successful transaction + 18% GST on that fee. No setup fee. No annual fee. Only charged on successful transactions.

**What this means per doctor payment:**

| Scenario | Transaction Amount | Razorpay Fee (2%) | GST (18% on fee) | Total Deducted | You Receive |
|---|---|---|---|---|---|
| Doctor pays for 1 patient | ₹250 | ₹5 | ₹0.90 | ₹5.90 | **₹244.10** |
| Doctor pays for 10 patients | ₹2,500 | ₹50 | ₹9 | ₹59 | **₹2,441** |
| Doctor pays for 20 patients | ₹5,000 | ₹100 | ₹18 | ₹118 | **₹4,882** |

**Effective rate after Razorpay fees:**

You charge ₹250. You receive ₹244.10. That's 97.6 paise on every rupee. Very acceptable.

For subscriptions specifically, Razorpay charges an additional 0.99% subscription management fee on top of the base 2% — so if you use Razorpay's built-in subscription billing (recommended for monthly auto-charge):

| Per patient per month | ₹250 charged |
|---|---|
| Gateway fee (2%) | -₹5.00 |
| Subscription fee (0.99%) | -₹2.48 |
| GST on fees (18%) | -₹1.35 |
| **You receive** | **₹241.17** |

Still 96.5% of every rupee. The convenience of automated billing is worth the 3.5%.

---

## SECTION 5 — APP STORE COMMISSIONS

**Critical point — this only applies if you charge users INSIDE the app using Apple/Google's own payment system.**

For Mityahar, doctors pay you directly via Razorpay (outside the app store ecosystem). So:

| Scenario | Google Commission | Apple Commission |
|---|---|---|
| Doctor pays via Razorpay (outside app) | ₹0 | ₹0 |
| Tier 1 Premium ₹149 charged via Play Store billing | 15% = ₹22.35 per transaction | 15% = ₹22.35 per transaction |
| Tier 1 Premium ₹149 charged via Razorpay (website/link) | ₹0 | ₹0 |

**The smart move:** For Tier 1 Premium subscriptions, bill doctors and patients through your own website/Razorpay link — not through in-app purchase. 97% of developers distribute apps on Google Play at no charge — commissions only apply when selling digital goods through their billing system.

This is legal and widely practiced. You direct users to pay on your website. Apple is stricter about this (they want iPhone users to pay through Apple IAP) — but for B2B doctor billing, it's not an issue. The grey area is only for direct consumer subscriptions on iOS.

---

## SECTION 6 — TESTFLIGHT (iOS TESTING)

TestFlight is included in your $99/year Apple Developer account. No extra cost. Use it for iOS distribution before App Store launch.

---

## COMPLETE COST SUMMARY — ALL THREE PHASES

### Phase 1 Launch — First Year Total Cost

| Category | Cost |
|---|---|
| Google Play one-time | ₹2,088 |
| Domain first year | ₹567 |
| Apple Developer (annual) | ₹8,267 |
| GCP infrastructure (12 months × ₹3,173) | ₹38,076 |
| Razorpay fees (6 doctors × avg 15 patients × ₹8.83 fee × 12 months) | ₹9,540 |
| **Year 1 Total** | **₹58,538** |
| **Monthly average** | **₹4,878/month** |
| **Minus GCP free $300 credits** | **-₹25,050** |
| **Effective Year 1 Total** | **₹33,488** |
| **Effective monthly average** | **₹2,791/month** |

---

### Revenue vs Cost — The Reality Check

| Phase | Active Patients | Monthly Revenue | Monthly Cost | Monthly Profit | Margin |
|---|---|---|---|---|---|
| Launch | 100 | ₹25,000 | ₹4,878 | **₹20,122** | **80%** |
| Growth | 500 | ₹1,25,000 | ₹11,286 | **₹1,13,714** | **91%** |
| Scale | 5,000 | ₹12,50,000 | ₹35,056 | **₹12,14,944** | **97%** |

---

### Cost Per Patient — Across All Phases

| Phase | Patients | Total Monthly Cost | Cost Per Patient |
|---|---|---|---|
| Launch | 100 | ₹4,878 | **₹48.78** |
| Growth | 500 | ₹11,286 | **₹22.57** |
| Scale | 5,000 | ₹35,056 | **₹7.01** |

You charge ₹250. Your cost at launch is ₹48.78. Your margin per patient is **₹201.22 at launch and only improves from there.**

---

## EVERYTHING IN ONE PLACE — MASTER TABLE

| # | Item | Type | Amount (₹) | Frequency |
|---|---|---|---|---|
| 1 | Google Play Account | One-time | ₹2,088 | Once ever |
| 2 | Apple Developer Account | Annual | ₹8,267 | Every year |
| 3 | Domain `mityahar.com` — Year 1 | One-time | ₹567 | First year only |
| 4 | Domain `mityahar.com` — Renewal | Annual | ₹1,167 | Every year after |
| 5 | Cloud SQL PostgreSQL (launch) | Monthly | ₹3,006 | Every month |
| 6 | Cloud Run API + ML (launch) | Monthly | ₹0 | Free tier |
| 7 | Cloud Storage (launch) | Monthly | ₹125 | Every month |
| 8 | Firebase Auth + FCM | Monthly | ₹0 | Free |
| 9 | Cloudflare CDN + SSL | Monthly | ₹0 | Free |
| 10 | Secret Manager | Monthly | ₹42 | Every month |
| 11 | Razorpay per transaction | Per payment | 2.99% + GST | Per doctor payment |
| 12 | GCP Free Credits (new account) | One-time credit | -₹25,050 | First 90 days |
| 13 | Apple App Store commission | Per iOS sub | 15% of transaction | Only if billing via Apple IAP |
| 14 | Google Play commission | Per Android sub | 15% of transaction | Only if billing via Play billing |
| 15 | Redis Cache (growth phase) | Monthly | ₹2,000 | Added at ~500 patients |
| 16 | Cloudflare Pro (scale phase) | Monthly | ₹1,670 | Added at ~5,000 patients |

---

## The One Number to Remember

> At launch with 100 patients your total monthly spend is **₹4,878.** Your monthly revenue is **₹25,000.** You are profitable from your very first patient.