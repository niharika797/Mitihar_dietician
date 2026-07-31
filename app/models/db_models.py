from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, SmallInteger, String, Numeric, Float, Boolean, DateTime, Date,
    Text, Index, UniqueConstraint, CheckConstraint, ForeignKey, text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
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
    # IFCT2017-derived per-serving nutrients (added 2026-07-29). Nullable — computed
    # from the ingredient chain only where coverage is sufficient (NULL = unknown, not 0).
    # Minerals + fatty acids in mg; free sugars in g. Numeric(8,2) headroom for oils/fats.
    iron_per_serving          = Column(Numeric(8, 2), nullable=True)
    calcium_per_serving       = Column(Numeric(8, 2), nullable=True)
    potassium_per_serving     = Column(Numeric(8, 2), nullable=True)
    phosphorus_per_serving    = Column(Numeric(8, 2), nullable=True)
    zinc_per_serving          = Column(Numeric(8, 2), nullable=True)
    free_sugars_per_serving   = Column(Numeric(8, 2), nullable=True)
    saturated_fat_per_serving = Column(Numeric(8, 2), nullable=True)
    # Doctor-override guard: set true when a doctor edits this dish's tags, so the
    # nutrition-derived tag script (derive_medical_tags.py) skips it.
    tags_locked         = Column(Boolean, nullable=False, server_default='false')
    serving_weight_g    = Column(Numeric(6, 1))
    diet_type           = Column(String(30), nullable=False)   # see diet values below
    region_tags         = Column(ARRAY(Text), nullable=False, default=[])
    meal_time_tags      = Column(ARRAY(Text), nullable=False, default=[])
    ingredients         = Column(JSONB, nullable=False, default=[])  # [{"name": str, "amount_g": float}]
    # ^ DEPRECATED (Stage 2, 2026-07-15): recipe_ingredients is the authoritative
    #   ingredient source — all app readers repointed (meal_generator, meal_plan combo
    #   detail); doctor add-recipe dual-writes. Do not add new readers. Column drop is
    #   Stage 3 scope (after the 61 flagged artifact rows are resolved).
    source              = Column(String(20), nullable=False, default="manual")
    nutrition_source    = Column(Text, nullable=False, server_default="manual")
    is_verified         = Column(Boolean, nullable=False, default=False)
    submitted_for_review = Column(Boolean, nullable=False, default=False)
    avoid_tags          = Column(JSONB, nullable=False, server_default='[]')
    prefer_tags         = Column(JSONB, nullable=False, server_default='[]')
    image_url           = Column(String(500), nullable=True)
    # URL to food image — populated by ETL script in Phase 6
    doctor_id           = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    # Tracks which doctor submitted this item. NULL for system/ETL food items.
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at          = Column(DateTime(timezone=True), nullable=True)
    # Soft-delete (Stage 6). NULL = active. Set by Tier 1 auto-merge instead of
    # a hard DELETE. Distinct from is_verified=False, which means "unreviewed",
    # not "deleted" — the Data Review tab must filter on this, not is_verified.
    name_normalized     = Column(String(255), nullable=True)
    # Canonical form of recipe_name (lower/strip/collapse-whitespace) for dedup +
    # the uq_fi_canonical partial-unique index. Maintained on every insert/rename.
    original_name       = Column(Text, nullable=True)
    # Rollback-safety snapshot of recipe_name before clean_dish_names.py runs (migration
    # b5c6d7e8f9a0). Modelled here so `alembic check` matches the live column.

    # relationships
    doctor              = relationship("Doctor")
    recipe_ingredients  = relationship("RecipeIngredient", back_populates="food_item", cascade="all, delete-orphan")


Index("idx_fi_slot",       FoodItem.slot_type)
Index("idx_fi_diet",       FoodItem.diet_type)
Index("idx_fi_verified",   FoodItem.is_verified)
Index("idx_fi_doctor",     FoodItem.doctor_id)
# GIN indexes for ARRAY columns — declared here so Alembic stops flagging them as drift
Index("idx_fi_regions",    FoodItem.region_tags,   postgresql_using="gin")
Index("idx_fi_meal_times", FoodItem.meal_time_tags, postgresql_using="gin")
Index("idx_fi_avoid_tags",  FoodItem.avoid_tags,     postgresql_using="gin")
Index("idx_fi_prefer_tags", FoodItem.prefer_tags,    postgresql_using="gin")
Index("idx_fi_deleted_at", FoodItem.deleted_at, postgresql_where=text("deleted_at IS NULL"))
Index("idx_fi_name_norm", FoodItem.name_normalized)
# At most one CANONICAL dish per (normalized name, slot, diet) in the served pool.
# Private/unverified doctor dishes and soft-deleted history are exempt (predicate),
# and diet-variants differ on diet_type so both diet pools keep their copy.
Index(
    "uq_fi_canonical", FoodItem.name_normalized, FoodItem.slot_type, FoodItem.diet_type,
    unique=True,
    postgresql_where=text("deleted_at IS NULL AND is_verified = true AND name_normalized IS NOT NULL"),
)

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    specialization: Mapped[str | None] = mapped_column(String, nullable=True)
    clinic_name: Mapped[str | None] = mapped_column(String, nullable=True)
    clinic_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    fee_per_month: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)   # in ₹
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True, default=0)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    is_accepting: Mapped[bool | None] = mapped_column(Boolean, default=True)               # false = not taking new patients
    mfa_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    mfa_enabled: Mapped[bool | None] = mapped_column(Boolean, default=False)
    # ── Login lockout (T1-6) ──────────────────────────────────────────────
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True)
    role: Mapped[str | None] = mapped_column(String(10), default="doctor")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    patients: Mapped[list["Patient"]] = relationship("Patient", back_populates="doctor", foreign_keys="Patient.doctor_id")
    patient_requests: Mapped[list["PatientRequest"]] = relationship("PatientRequest", back_populates="doctor")
    subscription_codes: Mapped[list["SubscriptionCode"]] = relationship("SubscriptionCode", back_populates="doctor")
    clinical_notes: Mapped[list["ClinicalNote"]] = relationship("ClinicalNote", foreign_keys="ClinicalNote.doctor_id", overlaps="doctor")


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    mfa_enabled: Mapped[bool | None] = mapped_column(Boolean, default=False)
    allowed_ips: Mapped[list | None] = mapped_column(JSONB, default=[])
    # ── Login lockout (T1-6) ──────────────────────────────────────────────
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True)
    role: Mapped[str | None] = mapped_column(String(10), default="admin")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Patient
# ---------------------------------------------------------------------------

class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(String, nullable=False)
    height_cm: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    activity_level: Mapped[str] = mapped_column(String(5), nullable=False)      # S / LA / MA / VA / SA
    diet_type: Mapped[str] = mapped_column(String(30), nullable=False)
    region: Mapped[str] = mapped_column(String(10), nullable=False)
    health_condition: Mapped[str | None] = mapped_column(String(30), default="Healthy")
    bmi: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    bmr: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    tdee: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    target_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    health_goals: Mapped[list | None] = mapped_column(JSONB, default=[])
    medical_conditions: Mapped[list | None] = mapped_column(JSONB, default=[])
    food_allergies: Mapped[list | None] = mapped_column(JSONB, default=[])
    dietary_preferences: Mapped[list | None] = mapped_column(JSONB, default=[])
    meals_per_day: Mapped[int | None] = mapped_column(Integer, default=3)
    fasting_days: Mapped[list | None] = mapped_column(JSONB, default=[])
    sleep_hours: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    water_glasses: Mapped[int | None] = mapped_column(Integer, default=8)
    occupation: Mapped[str | None] = mapped_column(String, nullable=True)
    smoking: Mapped[bool | None] = mapped_column(Boolean, default=False)
    alcohol: Mapped[bool | None] = mapped_column(Boolean, default=False)
    user_type: Mapped[str | None] = mapped_column(String(20), default="standalone")   # standalone | doctor_connected
    doctor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("doctors.id"), nullable=True)
    subscription_status: Mapped[str | None] = mapped_column(String(20), default="inactive")
    subscription_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disclaimer_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nonveg_meals_per_week: Mapped[int | None] = mapped_column(Integer, default=3)
    role: Mapped[str | None] = mapped_column(String(10), default="patient")
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True)
    google_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    # Stable Google 'sub' claim — set on first Google Sign-In, never changes
    is_email_verified: Mapped[bool | None] = mapped_column(Boolean, default=False)
    # True once the patient clicks the verification link in their welcome email.
    # Google-authenticated patients are auto-verified (Google already confirmed the email).
    pace_preference: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # valid values: "slow" | "moderate" | "fast" — patient's preferred weight-loss pace
    eating_habits: Mapped[list | None] = mapped_column(JSONB, default=[])
    # e.g. ["skips_breakfast", "late_night_eating", "irregular_meals"]

    # ── Token 1 — permanent meal plan identity ────────────────────────────
    token_1: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    # e.g. TKN1-PAT-00142 — generated once at onboarding, never changes
    token_1_active: Mapped[bool | None] = mapped_column(Boolean, default=False)
    # True = meal plan active, False = inactive (expired or not yet onboarded)
    token_1_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 30-day rolling window — reset on each renewal

    # ── Renewal flags ─────────────────────────────────────────────────────
    renewal_requested: Mapped[bool | None] = mapped_column(Boolean, default=False)
    renewal_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiring_soon: Mapped[bool | None] = mapped_column(Boolean, default=False)
    # set True by daily cron when ≤4 days left on token_1_expiry

    # ── FCM push notifications ──────────────────────────────────────────────
    fcm_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notification_preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default={})
    # Device FCM token — updated on every login, cleared on logout.
    # NULL means patient has not granted notification permission or is logged out.

    # ── Login lockout (T1-6) ─────────────────────────────────────────────────
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Session invalidation on password change (T1-7) ─────────────────────
    # Set to now() on every password reset. Tokens issued before this timestamp
    # are rejected, providing stateless session invalidation without a blacklist.
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    doctor: Mapped["Doctor | None"] = relationship("Doctor", back_populates="patients", foreign_keys=[doctor_id])
    recommendations: Mapped[list["Recommendation"]] = relationship("Recommendation", back_populates="patient")
    meal_logs: Mapped[list["MealLog"]] = relationship("MealLog", back_populates="patient")
    progress_logs: Mapped[list["ProgressLog"]] = relationship("ProgressLog", back_populates="patient")
    patient_requests: Mapped[list["PatientRequest"]] = relationship("PatientRequest", back_populates="patient")
    patient_visits: Mapped[list["PatientVisit"]] = relationship("PatientVisit", back_populates="patient", order_by="PatientVisit.created_at.desc()")


# Partial unique index on google_id — declared here so Alembic autogenerate doesn't flag it as drift
Index(
    "idx_patients_google_id",
    Patient.google_id,
    unique=True,
    postgresql_where=text("google_id IS NOT NULL"),
)
Index("idx_patients_doctor_id", Patient.doctor_id)


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------

class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    week_start_date: Mapped[date | None] = mapped_column(Date)
    week_number: Mapped[int | None] = mapped_column(Integer)
    meals: Mapped[list] = mapped_column(JSONB, nullable=False, default=[])
    ingredient_checklist: Mapped[list | None] = mapped_column(JSONB, default=[])
    used_food_ids: Mapped[list | None] = mapped_column(JSONB, default=[])
    # List of food_item IDs used in this plan — enables cross-week variety
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True)
    generated_by: Mapped[str | None] = mapped_column(String(20), default="system")   # system | doctor
    doctor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int | None] = mapped_column(Integer, default=1)
    generation_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # 1 = old single-combo JSONB model, 2 = new multi-combo weekly_combos model
    approval_status: Mapped[str] = mapped_column(String(20), nullable=False, default="approved")
    # 'draft' | 'approved' — v1 plans default 'approved' (always patient-visible)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="recommendations")
    meal_logs: Mapped[list["MealLog"]] = relationship("MealLog", back_populates="recommendation")

    __table_args__ = (
        Index("idx_rec_patient", "patient_id"),
        CheckConstraint("approval_status IN ('draft', 'approved')", name="ck_rec_approval_status"),
    )


# ---------------------------------------------------------------------------
# WeeklyCombo  (v2 multi-combo model — 4 pre-generated combos per slot)
# ---------------------------------------------------------------------------

class WeeklyCombo(Base):
    __tablename__ = "weekly_combos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recommendation_id: Mapped[int] = mapped_column(Integer, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)   # 'Breakfast' / 'Lunch' / 'Dinner'
    combo_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)   # 0-3, hard cap 4 per slot
    slot_composition: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)   # e.g. ['grain','dal_protein','sabzi']
    total_calories: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)   # unscaled SUM(cal_per_serving)
    dishes: Mapped[list] = mapped_column(JSONB, nullable=False, default=[])   # same shape as meals[].dishes[]
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    recommendation: Mapped["Recommendation"] = relationship("Recommendation")

    __table_args__ = (
        UniqueConstraint("recommendation_id", "slot_date", "meal_type", "combo_index", name="uq_weekly_combo"),
        CheckConstraint("combo_index BETWEEN 0 AND 3", name="ck_combo_index"),
        CheckConstraint("meal_type IN ('Breakfast', 'Lunch', 'Dinner')", name="ck_meal_type"),
        Index("idx_wc_rec_date_meal", "recommendation_id", "slot_date", "meal_type"),
        Index("idx_wc_rec_id", "recommendation_id"),
    )


# ---------------------------------------------------------------------------
# WeeklyPatientSummary  (doctor-visible week-end summary, computed on-demand)
# ---------------------------------------------------------------------------

class WeeklyPatientSummary(Base):
    __tablename__ = "weekly_patient_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    recommendation_id: Mapped[int] = mapped_column(Integer, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False)
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    summary_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})

    # relationships
    patient: Mapped["Patient"] = relationship("Patient")
    recommendation: Mapped["Recommendation"] = relationship("Recommendation")

    __table_args__ = (
        UniqueConstraint("patient_id", "week_start_date", name="uq_wps_patient_week"),
        Index("idx_wps_patient_id", "patient_id"),
    )


# ---------------------------------------------------------------------------
# MealLog
# ---------------------------------------------------------------------------

class MealLog(Base):
    __tablename__ = "meal_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    recommendation_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recommendations.id"), nullable=True)
    logged_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str | None] = mapped_column(String(20))   # Breakfast / MorningSnacks / Lunch / EveningSnacks / Dinner
    food_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("food_items.id"), nullable=True)
    custom_food_name: Mapped[str | None] = mapped_column(String, nullable=True)
    calories_consumed: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    protein_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), default=0)
    carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), default=0)
    fat_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), default=0)
    fiber_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), default=0)
    portion_servings: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), default=1.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="meal_logs")
    recommendation: Mapped["Recommendation | None"] = relationship("Recommendation", back_populates="meal_logs")
    food_item: Mapped["FoodItem | None"] = relationship("FoodItem")

    __table_args__ = (
        Index("idx_ml_patient_date", "patient_id", "logged_date"),
    )


# ---------------------------------------------------------------------------
# ProgressLog
# ---------------------------------------------------------------------------

class ProgressLog(Base):
    __tablename__ = "progress_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    water_glasses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calories_burned: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    total_calories_consumed: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    protein_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    carbs_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    fat_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calorie_adjustment: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="progress_logs")

    __table_args__ = (
        UniqueConstraint("patient_id", "log_date", name="uq_progress_patient_date"),
    )


# ---------------------------------------------------------------------------
# PatientRequest
# ---------------------------------------------------------------------------

class PatientRequest(Base):
    __tablename__ = "patient_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"), nullable=False)
    status: Mapped[str | None] = mapped_column(String(20), default="pending")   # pending / accepted / rejected
    rejection_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="patient_requests")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="patient_requests")

    __table_args__ = (
        Index("idx_patient_requests_doctor_id", "doctor_id"),
    )


# ---------------------------------------------------------------------------
# SubscriptionCode
# ---------------------------------------------------------------------------

class SubscriptionCode(Base):
    __tablename__ = "subscription_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    is_used: Mapped[bool | None] = mapped_column(Boolean, default=False)
    used_by_patient_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("patients.id"), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Three-state lifecycle: AVAILABLE → RESERVED → CONSUMED
    # reserved_by set at registration; used_by_patient_id set at activation
    reserved_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("patients.id"), nullable=True)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="subscription_codes")
    used_by_patient: Mapped["Patient | None"] = relationship("Patient", foreign_keys=[used_by_patient_id])

    __table_args__ = (
        Index("idx_sc_reserved_by", "reserved_by"),
    )


# ---------------------------------------------------------------------------
# ClinicalNote
# ---------------------------------------------------------------------------

class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    note_type: Mapped[str] = mapped_column(String(20), nullable=False, default="general")
    # "general" | "dietary" | "medical" | "progress"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_private: Mapped[bool | None] = mapped_column(Boolean, default=True)   # True = doctor-only, False = visible to patient
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", overlaps="clinical_notes")
    patient: Mapped["Patient"] = relationship("Patient")

    __table_args__ = (
        Index("idx_cn_doctor_patient", "doctor_id", "patient_id"),
    )


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[int] = mapped_column(Integer, nullable=False)   # doctor.id or admin.id
    actor_role: Mapped[str] = mapped_column(String(10), nullable=False)  # "doctor" | "admin"
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "accept_request", "deactivate_doctor"
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)   # e.g. "patient", "doctor", "recipe"
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)      # ID of the affected record
    detail: Mapped[dict | None] = mapped_column(JSONB, default={})           # any extra context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)   # IPv4 or IPv6
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_al_actor", "actor_id", "actor_role"),
        Index("idx_al_created", "created_at"),
    )


# ---------------------------------------------------------------------------
# DataChangeRequest  (Stage 6 — dish-duplicate merge/conflict pipeline)
# ---------------------------------------------------------------------------

class DataChangeRequest(Base):
    __tablename__ = "data_change_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_table: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    field_changed: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # doctor user_id (as string), or "system:ai_observer" / "system:tier1_auto" — polymorphic like AuditLog.actor_id, can't FK
    proposed_by: Mapped[str] = mapped_column(String(50), nullable=False)
    proposal_reason: Mapped[str] = mapped_column(Text, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)  # "tier1_auto" | "tier2_review"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # "pending" | "approved" | "rejected" | "auto_applied"
    reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("admins.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_dcr_status_tier", "status", "tier"),
        Index("idx_dcr_proposed_by", "proposed_by"),
        Index("idx_dcr_target", "target_table", "target_id"),
    )


# ---------------------------------------------------------------------------
# DataChangeAuditLog  (Stage 6 — append-only trail of every data-change action)
# ---------------------------------------------------------------------------
# One row per state transition (merge / proposed / approved / rejected / applied).
# App code only ever INSERTs here — never UPDATE/DELETE — so the trail is immutable.
# (DB-grant enforcement of that is deferred; see docs/STAGE6_SPEC.md §1.2.)

class DataChangeAuditLog(Base):
    __tablename__ = "data_change_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("data_change_requests.id"), nullable=True
    )  # null for direct actions (e.g. tier1_auto merge) that skip the request queue
    target_table: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    # "merge" | "proposed" | "approved" | "rejected" | "applied" | "soft_delete"
    field_changed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    before_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # actor: doctor user_id (as string), admin id, or "system:tier1_auto" / "system:ai_observer"
    actor: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_dcal_target", "target_table", "target_id"),
        Index("idx_dcal_request", "request_id"),
        Index("idx_dcal_action", "action"),
    )


# ---------------------------------------------------------------------------
# PatientVisit  (Token 2 — visit billing tracker)
# ---------------------------------------------------------------------------

class PatientVisit(Base):
    __tablename__ = "patient_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"), nullable=False)
    token_2: Mapped[str] = mapped_column(String(24), nullable=False)
    # e.g. TKN2-XK9-20260301 — freshly generated every 30-day cycle
    cycle_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cycle_expiry: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # cycle_expiry = cycle_start + 30 days
    last_charged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # timestamp of most recent chargeable visit (>15 days since previous)
    visit_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # increments only on chargeable visits (>15-day gap)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="patient_visits")
    doctor: Mapped["Doctor"] = relationship("Doctor")

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    override_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot_type: Mapped[str | None] = mapped_column(String(50), nullable=True)   # grain / main_dish / snack_item etc.
    meal_type: Mapped[str] = mapped_column(String(30), nullable=False)   # Breakfast / Lunch etc.
    rejected_food_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("food_items.id"), nullable=True)
    # NULL if original meal was a custom (non-DB) meal
    chosen_food_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("food_items.id"), nullable=True)
    # NULL if doctor replaced with a free-text custom meal
    # ── Patient context snapshot at time of override ──────────────────────
    patient_health_condition: Mapped[str | None] = mapped_column(String(30), nullable=True)   # "Healthy" / "Diabetic-Friendly" etc.
    patient_medical_conditions: Mapped[list | None] = mapped_column(JSONB, default=[])         # ["PCOS/PCOD"] etc.
    patient_region: Mapped[str | None] = mapped_column(String(10), nullable=True)   # "North" / "South" etc.
    patient_diet_type: Mapped[str | None] = mapped_column(String(30), nullable=True)   # "Vegetarian" etc.
    patient_age_bucket: Mapped[str | None] = mapped_column(String(10), nullable=True)   # "18-25" / "26-35" etc.
    patient_bmi_bucket: Mapped[str | None] = mapped_column(String(15), nullable=True)   # "normal" / "overweight" etc.
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # ── Clinical edit-trail enrichment (R-1) ───────────────────────────────
    patient_condition_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # {"conditions": ["Type 2 Diabetes"], "avoid_tags": ["avoid_diabetes"]}
    edit_reason: Mapped[str] = mapped_column(String(20), nullable=False, default="swap")
    # 'swap' | 'add' | 'remove' | 'custom_add'
    doctor_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    doctor: Mapped["Doctor"] = relationship("Doctor")
    patient: Mapped["Patient"] = relationship("Patient")
    rejected_food: Mapped["FoodItem | None"] = relationship("FoodItem", foreign_keys=[rejected_food_id])
    chosen_food: Mapped["FoodItem | None"] = relationship("FoodItem", foreign_keys=[chosen_food_id])

    __table_args__ = (
        Index("idx_dmo_doctor",  "doctor_id"),
        Index("idx_dmo_patient", "patient_id"),
        Index("idx_dmo_date",    "override_date"),
        CheckConstraint("edit_reason IN ('swap', 'add', 'remove', 'custom_add')", name="ck_dmo_edit_reason"),
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"), nullable=False)
    food_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("food_items.id"), nullable=False)
    recommendation_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recommendations.id"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)   # +1 (liked) or -1 (disliked)
    rated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    patient: Mapped["Patient"] = relationship("Patient")
    food_item: Mapped["FoodItem"] = relationship("FoodItem")
    recommendation: Mapped["Recommendation | None"] = relationship("Recommendation")

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, unique=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient")

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, unique=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient")

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    patient_visit_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("patient_visits.id"), nullable=True)
    # Linked to the PatientVisit cycle (set on creation, may be None if no cycle yet)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="pending")
    # "pending" | "approved" | "rejected"
    visit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    doctor_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient")
    doctor: Mapped["Doctor"] = relationship("Doctor")

    __table_args__ = (
        Index("idx_pva_patient", "patient_id"),
        Index("idx_pva_status",  "status"),
    )


# ---------------------------------------------------------------------------
# PatientMealConfig  (doctor TDEE split override per patient)
# ---------------------------------------------------------------------------

class PatientMealConfig(Base):
    __tablename__ = "patient_meal_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"),
                                 nullable=False, unique=True)
    meal_split_override: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # {"breakfast_pct": 25, "lunch_pct": 35, "dinner_pct": 25} when set.
    # NULL = use system defaults. Application layer enforces the three values sum to 85.
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    patient: Mapped["Patient"] = relationship("Patient")

    __table_args__ = (
        Index("idx_pmc_patient", "patient_id"),
    )


# ---------------------------------------------------------------------------
# PatientDishPreferences  (doctor pin/block per patient per dish)
# ---------------------------------------------------------------------------

class PatientDishPreferences(Base):
    __tablename__ = "patient_dish_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    food_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False)
    preference_type: Mapped[str] = mapped_column(Text, nullable=False)  # 'pin' or 'block'
    added_by_doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient")
    food_item: Mapped["FoodItem"] = relationship("FoodItem")

    __table_args__ = (
        UniqueConstraint("patient_id", "food_item_id", name="uq_patient_dish_preference"),
        CheckConstraint("preference_type IN ('pin', 'block')", name="ck_pdp_preference_type"),
        Index("idx_pdp_patient",   "patient_id"),
        Index("idx_pdp_food_item", "food_item_id"),
        Index("idx_pdp_doctor",    "added_by_doctor_id"),
    )


# ---------------------------------------------------------------------------
# PatientPantry  (presence set — one row = "this patient has this ingredient")
# ---------------------------------------------------------------------------

class PatientPantry(Base):
    """Pantry-first meal planning: which ingredients a patient has on hand.
    Presence-based (row exists = have it); no quantities. Read by GET /meal-plan/week
    to rank combos by ingredient coverage. Coverage matches by normalized name, not id."""
    __tablename__ = "patient_pantry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient")

    __table_args__ = (
        UniqueConstraint("patient_id", "ingredient_id", name="uq_patient_pantry"),
        Index("idx_pantry_patient", "patient_id"),
    )


# ---------------------------------------------------------------------------
# PatientMealChoice  (plan-time dish selection per slot per day)
# ---------------------------------------------------------------------------

class PatientMealChoice(Base):
    __tablename__ = "patient_meal_choices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    food_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)   # 'Breakfast' / 'Lunch' / 'Dinner'
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    weekly_combo_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("weekly_combos.id", ondelete="SET NULL"), nullable=True)
    # NULL for v1 legacy choices; points to the selected combo for v2
    bowl_size: Mapped[str | None] = mapped_column(String(6), nullable=True)   # 'small' | 'medium' | 'large' (PD-9)
    actual_calories: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)   # bowl_multiplier × cal_per_serving

    patient: Mapped["Patient"] = relationship("Patient")
    food_item: Mapped["FoodItem"] = relationship("FoodItem")
    weekly_combo: Mapped["WeeklyCombo | None"] = relationship("WeeklyCombo")

    __table_args__ = (
        UniqueConstraint("patient_id", "date", "meal_type", name="uq_pmc_patient_date_meal"),
        Index("idx_pmc_patient_date", "patient_id", "date"),
        CheckConstraint("bowl_size IN ('small', 'medium', 'large')", name="ck_pmc_bowl_size"),
    )


class PatientMealChoiceDish(Base):
    """
    Session 22E (Part 3, Option B): per-dish breakdown of a confirmed meal choice.

    Additive child of patient_meal_choices, for future doctor weekly-summary
    analytics. The parent's `calories` column REMAINS the denormalized summed
    total and stays the budget-math source of truth (meal_plan.py budget reads
    only the parent) — these child rows are never read by the budget path.

    `calories` here is UNSCALED per-serving (= food_items.cal_per_serving, same
    value as dishes[].calories). NOTE: this means a confirm-choice record and the
    corresponding meal_logs.calories_consumed (which logs Σ scaled_calories) can
    represent the same meal on two different calorie bases — intentional, not a bug.
    """
    __tablename__ = "patient_meal_choice_dishes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    choice_id: Mapped[int] = mapped_column(Integer, ForeignKey("patient_meal_choices.id", ondelete="CASCADE"), nullable=False)
    food_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("food_items.id"), nullable=False)
    slot_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)   # UNSCALED (= cal_per_serving)

    choice: Mapped["PatientMealChoice"] = relationship("PatientMealChoice")
    food_item: Mapped["FoodItem"] = relationship("FoodItem")

    __table_args__ = (
        Index("idx_pmcd_choice", "choice_id"),
    )


# ---------------------------------------------------------------------------
# Ingredient  (master nutrition source — per 100g, INDB-compatible)
# ---------------------------------------------------------------------------

class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_hindi: Mapped[str | None] = mapped_column(Text, nullable=True)
    name_normalized: Mapped[str | None] = mapped_column(Text, nullable=True)
    calories_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sodium_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    iron_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    calcium_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    # IFCT2017-sourced nutrients (added 2026-07-29). Minerals + fatty acids in mg/100g;
    # sugars/fat in g/100g. All nullable — populated only for name-matched ingredients.
    potassium_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    phosphorus_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    zinc_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_sugars_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    free_sugars_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    saturated_fat_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    mufa_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    pufa_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_weight_g: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    added_by_doctor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    avoid_tags: Mapped[list] = mapped_column(JSONB, nullable=False, server_default='[]')
    prefer_tags: Mapped[list] = mapped_column(JSONB, nullable=False, server_default='[]')

    # relationships
    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship("RecipeIngredient", back_populates="ingredient")

    __table_args__ = (
        UniqueConstraint("name", "source", name="uq_ingredient_name_source"),
        Index("idx_ing_name",       "name"),
        Index("idx_ing_source",     "source"),
        Index("idx_ing_verified",   "is_verified"),
        Index("idx_ing_avoid_tags", "avoid_tags",  postgresql_using="gin"),
        Index("idx_ing_prefer_tags","prefer_tags", postgresql_using="gin"),
    )


# ---------------------------------------------------------------------------
# RecipeIngredient  (links food_items → ingredients with quantity in grams)
# ---------------------------------------------------------------------------

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    food_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("food_items.id",  ondelete="CASCADE"),  nullable=False)
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False)
    quantity_g: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    food_item: Mapped["FoodItem"] = relationship("FoodItem",   back_populates="recipe_ingredients")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="recipe_ingredients")

    __table_args__ = (
        UniqueConstraint("food_item_id", "ingredient_id", name="uq_recipe_ingredient"),
        Index("idx_ri_food_item",  "food_item_id"),
        Index("idx_ri_ingredient", "ingredient_id"),
    )
