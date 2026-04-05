from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date,
    Text, Index, UniqueConstraint, ForeignKey, text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# ---------------------------------------------------------------------------
# FoodItem  (DO NOT MODIFY)
# ---------------------------------------------------------------------------

class FoodItem(Base):
    __tablename__ = "food_items"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    recipe_name         = Column(String(255), nullable=False)
    slot_type           = Column(String(50), nullable=False)   # see slot values below
    cal_per_serving     = Column(Numeric(7, 2), nullable=False)
    protein_per_serving = Column(Numeric(6, 2), nullable=False, default=0)
    carbs_per_serving   = Column(Numeric(6, 2), nullable=False, default=0)
    fat_per_serving     = Column(Numeric(6, 2), nullable=False, default=0)
    fiber_per_serving   = Column(Numeric(6, 2), nullable=False, default=0)
    sodium_per_serving  = Column(Numeric(6, 2), default=0)
    serving_weight_g    = Column(Numeric(6, 1))
    diet_type           = Column(String(30), nullable=False)   # see diet values below
    region_tags         = Column(ARRAY(Text), nullable=False, default=[])
    meal_time_tags      = Column(ARRAY(Text), nullable=False, default=[])
    plan_type_tags      = Column(ARRAY(Text), nullable=False, default=["Healthy", "Diabetic-Friendly", "Gym-Friendly"])
    ingredients         = Column(JSONB, nullable=False, default=[])  # [{"name": str, "amount_g": float}]
    source              = Column(String(20), nullable=False, default="manual")
    is_verified         = Column(Boolean, nullable=False, default=False)
    image_url           = Column(String(500), nullable=True)
    # URL to food image — populated by ETL script in Phase 6
    doctor_id           = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    # Tracks which doctor submitted this item. NULL for system/ETL food items.
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    doctor              = relationship("Doctor")


Index("idx_fi_slot",       FoodItem.slot_type)
Index("idx_fi_diet",       FoodItem.diet_type)
Index("idx_fi_verified",   FoodItem.is_verified)
Index("idx_fi_doctor",     FoodItem.doctor_id)
# GIN indexes for ARRAY columns — declared here so Alembic stops flagging them as drift
Index("idx_fi_regions",    FoodItem.region_tags,   postgresql_using="gin")
Index("idx_fi_meal_times", FoodItem.meal_time_tags, postgresql_using="gin")
Index("idx_fi_plan_types", FoodItem.plan_type_tags, postgresql_using="gin")

# ---------------------------------------------------------------------------
# MealTemplate  (DO NOT MODIFY)
# ---------------------------------------------------------------------------

class MealTemplate(Base):
    __tablename__ = "meal_templates"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    meal_time   = Column(String(20), nullable=False)   # 'Breakfast','Lunch','Dinner','Morning_Snack','Evening_Snack'
    region      = Column(String(10), nullable=False)   # 'North','South','East','West'
    diet_type   = Column(String(30), nullable=False)
    plan_type   = Column(String(30), nullable=False)
    slots       = Column(JSONB, nullable=False)
    # slots format: [{"slot_type": "grain", "calorie_pct": 0.35, "required": true}, ...]
    
    __table_args__ = (
        UniqueConstraint("meal_time", "region", "diet_type", "plan_type", name="uq_template"),
    )


# ===================================================================
#  NEW MODELS — Doctors, Admins, Patients, Recommendations, Logs …
# ===================================================================

# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------

class Doctor(Base):
    __tablename__ = "doctors"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    email             = Column(String, unique=True, nullable=False)
    hashed_password   = Column(String, nullable=False)
    name              = Column(String, nullable=False)
    phone             = Column(String, nullable=True)
    specialization    = Column(String, nullable=True)
    clinic_name       = Column(String, nullable=True)
    clinic_address    = Column(Text, nullable=True)
    city              = Column(String, nullable=True)
    state             = Column(String, nullable=True)
    experience_years  = Column(Integer, nullable=True, default=0)
    fee_per_month     = Column(Integer, nullable=True, default=0)   # in ₹
    rating            = Column(Numeric(3, 2), nullable=True, default=0)
    review_count      = Column(Integer, nullable=True, default=0)
    is_accepting      = Column(Boolean, default=True)               # false = not taking new patients
    mfa_secret              = Column(String, nullable=True)
    mfa_enabled             = Column(Boolean, default=False)
    # ── Login lockout (T1-6) ──────────────────────────────────────────────
    failed_login_attempts   = Column(Integer, default=0, nullable=False)
    locked_until            = Column(DateTime(timezone=True), nullable=True)
    is_active               = Column(Boolean, default=True)
    role                    = Column(String(10), default="doctor")
    created_at              = Column(DateTime(timezone=True), server_default=func.now())
    updated_at              = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    patients          = relationship("Patient", back_populates="doctor", foreign_keys="Patient.doctor_id")
    patient_requests  = relationship("PatientRequest", back_populates="doctor")
    subscription_codes = relationship("SubscriptionCode", back_populates="doctor")
    clinical_notes    = relationship("ClinicalNote", foreign_keys="ClinicalNote.doctor_id", overlaps="doctor")


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class Admin(Base):
    __tablename__ = "admins"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    email           = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name            = Column(String, nullable=False)
    mfa_secret              = Column(String, nullable=True)
    mfa_enabled             = Column(Boolean, default=False)
    allowed_ips             = Column(JSONB, default=[])
    # ── Login lockout (T1-6) ──────────────────────────────────────────────
    failed_login_attempts   = Column(Integer, default=0, nullable=False)
    locked_until            = Column(DateTime(timezone=True), nullable=True)
    is_active               = Column(Boolean, default=True)
    role                    = Column(String(10), default="admin")
    created_at              = Column(DateTime(timezone=True), server_default=func.now())
    updated_at              = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Patient
# ---------------------------------------------------------------------------

class Patient(Base):
    __tablename__ = "patients"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    email                 = Column(String, unique=True, nullable=False)
    hashed_password       = Column(String, nullable=False)
    name                  = Column(String, nullable=False)
    phone                 = Column(String, nullable=True)
    date_of_birth         = Column(Date, nullable=True)
    gender                = Column(String, nullable=False)
    height_cm             = Column(Numeric, nullable=False)
    weight_kg             = Column(Numeric, nullable=False)
    activity_level        = Column(String(5), nullable=False)      # S / LA / MA / VA / SA
    diet_type             = Column(String(30), nullable=False)
    region                = Column(String(10), nullable=False)
    health_condition      = Column(String(30), default="Healthy")
    bmi                   = Column(Numeric(5, 2), nullable=True)
    bmr                   = Column(Numeric(7, 2), nullable=True)
    tdee                  = Column(Numeric(7, 2), nullable=True)
    target_weight_kg      = Column(Numeric, nullable=True)
    health_goals          = Column(JSONB, default=[])
    medical_conditions    = Column(JSONB, default=[])
    food_allergies        = Column(JSONB, default=[])
    dietary_preferences   = Column(JSONB, default=[])
    meals_per_day         = Column(Integer, default=5)
    fasting_days          = Column(JSONB, default=[])
    sleep_hours           = Column(Numeric, nullable=True)
    water_glasses         = Column(Integer, default=8)
    occupation            = Column(String, nullable=True)
    smoking               = Column(Boolean, default=False)
    alcohol               = Column(Boolean, default=False)
    user_type             = Column(String(20), default="standalone")   # standalone | doctor_connected
    doctor_id             = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    subscription_status   = Column(String(20), default="inactive")
    subscription_end_date = Column(DateTime(timezone=True), nullable=True)
    disclaimer_accepted_at = Column(DateTime(timezone=True), nullable=True)
    nonveg_meals_per_week = Column(Integer, default=3)
    role                  = Column(String(10), default="patient")
    is_active             = Column(Boolean, default=True)
    google_id             = Column(String(128), unique=True, nullable=True)
    # Stable Google 'sub' claim — set on first Google Sign-In, never changes
    is_email_verified     = Column(Boolean, default=False)
    # True once the patient clicks the verification link in their welcome email.
    # Google-authenticated patients are auto-verified (Google already confirmed the email).
    pace_preference       = Column(String(20), nullable=True)
    # valid values: "slow" | "moderate" | "fast" — patient's preferred weight-loss pace
    eating_habits         = Column(JSONB, default=[])
    # e.g. ["skips_breakfast", "late_night_eating", "irregular_meals"]

    # ── Token 1 — permanent meal plan identity ────────────────────────────
    token_1               = Column(String(20), unique=True, nullable=True)
    # e.g. TKN1-PAT-00142 — generated once at onboarding, never changes
    token_1_active        = Column(Boolean, default=False)
    # True = meal plan active, False = inactive (expired or not yet onboarded)
    token_1_expiry        = Column(DateTime(timezone=True), nullable=True)
    # 30-day rolling window — reset on each renewal

    # ── Renewal flags ─────────────────────────────────────────────────────
    renewal_requested     = Column(Boolean, default=False)
    renewal_requested_at  = Column(DateTime(timezone=True), nullable=True)
    expiring_soon         = Column(Boolean, default=False)
    # set True by daily cron when ≤4 days left on token_1_expiry

    # ── FCM push notifications ──────────────────────────────────────────────
    fcm_token             = Column(String(512), nullable=True)
    notification_preferences = Column(JSONB, nullable=True, default={})
    # Device FCM token — updated on every login, cleared on logout.
    # NULL means patient has not granted notification permission or is logged out.

    # ── Login lockout (T1-6) ─────────────────────────────────────────────────
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until          = Column(DateTime(timezone=True), nullable=True)

    # ── Session invalidation on password change (T1-7) ─────────────────────
    # Set to now() on every password reset. Tokens issued before this timestamp
    # are rejected, providing stateless session invalidation without a blacklist.
    password_changed_at   = Column(DateTime(timezone=True), nullable=True)

    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    doctor                = relationship("Doctor", back_populates="patients", foreign_keys=[doctor_id])
    recommendations       = relationship("Recommendation", back_populates="patient")
    meal_logs             = relationship("MealLog", back_populates="patient")
    progress_logs         = relationship("ProgressLog", back_populates="patient")
    patient_requests      = relationship("PatientRequest", back_populates="patient")
    patient_visits        = relationship("PatientVisit", back_populates="patient", order_by="PatientVisit.created_at.desc()")


# Partial unique index on google_id — declared here so Alembic autogenerate doesn't flag it as drift
Index(
    "idx_patients_google_id",
    Patient.google_id,
    unique=True,
    postgresql_where=text("google_id IS NOT NULL"),
)


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------

class Recommendation(Base):
    __tablename__ = "recommendations"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    patient_id           = Column(Integer, ForeignKey("patients.id"), nullable=False)
    week_start_date      = Column(Date)
    week_number          = Column(Integer)
    meals                = Column(JSONB, nullable=False, default=[])
    ingredient_checklist = Column(JSONB, default=[])
    used_food_ids        = Column(JSONB, default=[])
    # List of food_item IDs used in this plan — enables cross-week variety
    is_active            = Column(Boolean, default=True)
    generated_by         = Column(String(20), default="system")   # system | doctor
    doctor_notes         = Column(Text, nullable=True)
    version              = Column(Integer, default=1)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    patient              = relationship("Patient", back_populates="recommendations")
    meal_logs            = relationship("MealLog", back_populates="recommendation")

    __table_args__ = (
        Index("idx_rec_patient", "patient_id"),
    )


# ---------------------------------------------------------------------------
# MealLog
# ---------------------------------------------------------------------------

class MealLog(Base):
    __tablename__ = "meal_logs"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    patient_id          = Column(Integer, ForeignKey("patients.id"), nullable=False)
    recommendation_id   = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    logged_date         = Column(Date, nullable=False)
    meal_type           = Column(String(20))   # Breakfast / MorningSnacks / Lunch / EveningSnacks / Dinner
    food_id             = Column(Integer, ForeignKey("food_items.id"), nullable=True)
    custom_food_name    = Column(String, nullable=True)
    calories_consumed   = Column(Numeric(7, 2))
    protein_g           = Column(Numeric(6, 2), default=0)
    carbs_g             = Column(Numeric(6, 2), default=0)
    fat_g               = Column(Numeric(6, 2), default=0)
    fiber_g             = Column(Numeric(6, 2), default=0)
    portion_servings    = Column(Numeric(4, 2), default=1.0)
    notes               = Column(Text, nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    patient             = relationship("Patient", back_populates="meal_logs")
    recommendation      = relationship("Recommendation", back_populates="meal_logs")
    food_item           = relationship("FoodItem")

    __table_args__ = (
        Index("idx_ml_patient_date", "patient_id", "logged_date"),
    )


# ---------------------------------------------------------------------------
# ProgressLog
# ---------------------------------------------------------------------------

class ProgressLog(Base):
    __tablename__ = "progress_logs"

    id                       = Column(Integer, primary_key=True, autoincrement=True)
    patient_id               = Column(Integer, ForeignKey("patients.id"), nullable=False)
    log_date                 = Column(Date, nullable=False)
    weight_kg                = Column(Numeric, nullable=True)
    water_glasses            = Column(Integer, nullable=True)
    steps                    = Column(Integer, nullable=True)
    calories_burned          = Column(Numeric, nullable=True)
    total_calories_consumed  = Column(Numeric, nullable=True)
    protein_pct              = Column(Numeric, nullable=True)
    carbs_pct                = Column(Numeric, nullable=True)
    fat_pct                  = Column(Numeric, nullable=True)
    streak_days              = Column(Integer, nullable=False, default=0)
    calorie_adjustment       = Column(Numeric, nullable=True)
    created_at               = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    patient                  = relationship("Patient", back_populates="progress_logs")

    __table_args__ = (
        UniqueConstraint("patient_id", "log_date", name="uq_progress_patient_date"),
    )


# ---------------------------------------------------------------------------
# PatientRequest
# ---------------------------------------------------------------------------

class PatientRequest(Base):
    __tablename__ = "patient_requests"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    patient_id      = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id       = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    status          = Column(String(20), default="pending")   # pending / accepted / rejected
    rejection_note  = Column(Text, nullable=True)
    requested_at    = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    responded_at    = Column(DateTime(timezone=True), nullable=True)

    # relationships
    patient         = relationship("Patient", back_populates="patient_requests")
    doctor          = relationship("Doctor", back_populates="patient_requests")


# ---------------------------------------------------------------------------
# SubscriptionCode
# ---------------------------------------------------------------------------

class SubscriptionCode(Base):
    __tablename__ = "subscription_codes"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id          = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    code               = Column(String(20), unique=True, nullable=False)
    is_used            = Column(Boolean, default=False)
    used_by_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    used_at            = Column(DateTime(timezone=True), nullable=True)
    expires_at         = Column(DateTime(timezone=True), nullable=True)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    doctor             = relationship("Doctor", back_populates="subscription_codes")
    used_by_patient    = relationship("Patient")


# ---------------------------------------------------------------------------
# ClinicalNote
# ---------------------------------------------------------------------------

class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id   = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    patient_id  = Column(Integer, ForeignKey("patients.id"), nullable=False)
    note_type   = Column(String(20), nullable=False, default="general")
    # "general" | "dietary" | "medical" | "progress"
    content     = Column(Text, nullable=False)
    is_private  = Column(Boolean, default=True)   # True = doctor-only, False = visible to patient
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    doctor      = relationship("Doctor", overlaps="clinical_notes")
    patient     = relationship("Patient")

    __table_args__ = (
        Index("idx_cn_doctor_patient", "doctor_id", "patient_id"),
    )


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    actor_id    = Column(Integer, nullable=False)   # doctor.id or admin.id
    actor_role  = Column(String(10), nullable=False)  # "doctor" | "admin"
    action      = Column(String(100), nullable=False)  # e.g. "accept_request", "deactivate_doctor"
    entity_type = Column(String(50), nullable=True)   # e.g. "patient", "doctor", "recipe"
    entity_id   = Column(Integer, nullable=True)      # ID of the affected record
    detail      = Column(JSONB, default={})           # any extra context
    ip_address  = Column(String(45), nullable=True)   # IPv4 or IPv6
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_al_actor", "actor_id", "actor_role"),
        Index("idx_al_created", "created_at"),
    )


# ---------------------------------------------------------------------------
# PatientVisit  (Token 2 — visit billing tracker)
# ---------------------------------------------------------------------------

class PatientVisit(Base):
    __tablename__ = "patient_visits"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    patient_id       = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id        = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    token_2          = Column(String(24), nullable=False)
    # e.g. TKN2-XK9-20260301 — freshly generated every 30-day cycle
    cycle_start      = Column(DateTime(timezone=True), nullable=False)
    cycle_expiry     = Column(DateTime(timezone=True), nullable=False)
    # cycle_expiry = cycle_start + 30 days
    last_charged_at  = Column(DateTime(timezone=True), nullable=True)
    # timestamp of most recent chargeable visit (>15 days since previous)
    visit_counter    = Column(Integer, default=0, nullable=False)
    # increments only on chargeable visits (>15-day gap)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    patient          = relationship("Patient", back_populates="patient_visits")
    doctor           = relationship("Doctor")

    __table_args__ = (
        Index("idx_pv_patient", "patient_id"),
        Index("idx_pv_doctor", "doctor_id"),
    )


# ---------------------------------------------------------------------------
# DoctorMealOverride  (Phase 8 Tier 0 — RL signal collection)
# ---------------------------------------------------------------------------

class DoctorMealOverride(Base):
    """
    Records every time a doctor replaces an AI-suggested meal in a patient's plan.
    This is the highest-quality training signal for the future recommendation engine.
    One row per swapped meal slot.  Never purge — permanent training corpus.
    """
    __tablename__ = "doctor_meal_overrides"

    id                       = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id                = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    patient_id               = Column(Integer, ForeignKey("patients.id"), nullable=False)
    override_date            = Column(Date, nullable=False)
    slot_type                = Column(String(50), nullable=True)   # grain / main_dish / snack_item etc.
    meal_type                = Column(String(30), nullable=False)   # Breakfast / Lunch etc.
    rejected_food_id         = Column(Integer, ForeignKey("food_items.id"), nullable=True)
    # NULL if original meal was a custom (non-DB) meal
    chosen_food_id           = Column(Integer, ForeignKey("food_items.id"), nullable=True)
    # NULL if doctor replaced with a free-text custom meal
    # ── Patient context snapshot at time of override ──────────────────────
    patient_health_condition = Column(String(30), nullable=True)   # "Healthy" / "Diabetic-Friendly" etc.
    patient_medical_conditions = Column(JSONB, default=[])         # ["PCOS/PCOD"] etc.
    patient_region           = Column(String(10), nullable=True)   # "North" / "South" etc.
    patient_diet_type        = Column(String(30), nullable=True)   # "Vegetarian" etc.
    patient_age_bucket       = Column(String(10), nullable=True)   # "18-25" / "26-35" etc.
    patient_bmi_bucket       = Column(String(15), nullable=True)   # "normal" / "overweight" etc.
    created_at               = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    doctor                   = relationship("Doctor")
    patient                  = relationship("Patient")
    rejected_food            = relationship("FoodItem", foreign_keys=[rejected_food_id])
    chosen_food              = relationship("FoodItem", foreign_keys=[chosen_food_id])

    __table_args__ = (
        Index("idx_dmo_doctor",  "doctor_id"),
        Index("idx_dmo_patient", "patient_id"),
        Index("idx_dmo_date",    "override_date"),
    )


# ---------------------------------------------------------------------------
# MealRating  (Phase 8 Tier 0 — RL signal collection)
# ---------------------------------------------------------------------------

class MealRating(Base):
    """
    Patient thumbs-up / thumbs-down on a specific meal serving.
    One row per (patient × food_item × recommendation).
    Captures personal food preferences for the bandit personalisation layer.
    """
    __tablename__ = "meal_ratings"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    patient_id        = Column(Integer, ForeignKey("patients.id"), nullable=False)
    food_item_id      = Column(Integer, ForeignKey("food_items.id"), nullable=False)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    rating            = Column(Integer, nullable=False)   # +1 (liked) or -1 (disliked)
    rated_at          = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    patient           = relationship("Patient")
    food_item         = relationship("FoodItem")
    recommendation    = relationship("Recommendation")

    __table_args__ = (
        UniqueConstraint("patient_id", "food_item_id", "recommendation_id",
                         name="uq_meal_rating"),
        Index("idx_mr_patient", "patient_id"),
        Index("idx_mr_food",    "food_item_id"),
    )


# ---------------------------------------------------------------------------
# EmailVerificationToken  (security — one-time tokens for email confirmation)
# ---------------------------------------------------------------------------

class EmailVerificationToken(Base):
    """
    Single-use token emailed to a patient on registration.
    Expires after 24 hours. Consumed on first use (deleted after verification).
    """
    __tablename__ = "email_verification_tokens"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, unique=True)
    token      = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient    = relationship("Patient")

    __table_args__ = (
        Index("idx_evt_token",   "token"),
        Index("idx_evt_patient", "patient_id"),
    )


# ---------------------------------------------------------------------------
# PasswordResetToken  (security — expiring tokens for password recovery)
# ---------------------------------------------------------------------------

class PasswordResetToken(Base):
    """
    Single-use token emailed on forgot-password request.
    Expires after RESET_TOKEN_EXPIRE_MINUTES (default 30 min).
    Consumed on first use (deleted after successful reset).
    Only one active reset token per patient at a time (previous ones replaced).
    """
    __tablename__ = "password_reset_tokens"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, unique=True)
    token      = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient    = relationship("Patient")

    __table_args__ = (
        Index("idx_prt_token",   "token"),
        Index("idx_prt_patient", "patient_id"),
    )


# ---------------------------------------------------------------------------
# PendingVisitApproval  (visit fraud prevention — patient must confirm)
# ---------------------------------------------------------------------------

class PendingVisitApproval(Base):
    """
    Created when a doctor flags a visit for a patient who forgot their phone.
    The patient must approve it from their app before the visit is recorded
    and charges applied. This prevents doctors from fraudulently recording
    visits that never happened.

    Status transitions:
      pending → approved  (patient confirms they visited)
      pending → rejected  (patient denies the visit)
    """
    __tablename__ = "pending_visit_approvals"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    patient_id      = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id       = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    patient_visit_id= Column(Integer, ForeignKey("patient_visits.id"), nullable=True)
    # Linked to the PatientVisit cycle (set on creation, may be None if no cycle yet)
    status          = Column(String(10), nullable=False, default="pending")
    # "pending" | "approved" | "rejected"
    visit_date      = Column(DateTime(timezone=True), nullable=False)
    doctor_note     = Column(Text, nullable=True)
    responded_at    = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    patient         = relationship("Patient")
    doctor          = relationship("Doctor")

    __table_args__ = (
        Index("idx_pva_patient", "patient_id"),
        Index("idx_pva_status",  "status"),
    )
