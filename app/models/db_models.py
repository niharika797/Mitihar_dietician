from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date,
    Text, Index, UniqueConstraint, ForeignKey,
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
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


Index("idx_fi_slot",       FoodItem.slot_type)
Index("idx_fi_diet",       FoodItem.diet_type)
Index("idx_fi_verified",   FoodItem.is_verified)
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
    mfa_secret        = Column(String, nullable=True)
    mfa_enabled       = Column(Boolean, default=False)
    is_active         = Column(Boolean, default=True)
    role              = Column(String(10), default="doctor")
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    patients          = relationship("Patient", back_populates="doctor", foreign_keys="Patient.doctor_id")
    patient_requests  = relationship("PatientRequest", back_populates="doctor")
    subscription_codes = relationship("SubscriptionCode", back_populates="doctor")


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class Admin(Base):
    __tablename__ = "admins"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    email           = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name            = Column(String, nullable=False)
    mfa_secret      = Column(String, nullable=True)
    mfa_enabled     = Column(Boolean, default=False)
    allowed_ips     = Column(JSONB, default=[])
    is_active       = Column(Boolean, default=True)
    role            = Column(String(10), default="admin")
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    doctor                = relationship("Doctor", back_populates="patients", foreign_keys=[doctor_id])
    recommendations       = relationship("Recommendation", back_populates="patient")
    meal_logs             = relationship("MealLog", back_populates="patient")
    progress_logs         = relationship("ProgressLog", back_populates="patient")
    patient_requests      = relationship("PatientRequest", back_populates="patient")


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
