## MongoDB Audit

**Collections Found:** ['progress', 'users', 'diet_plans']

### Collection: `progress`
**Sample Document Keys:**
- `_id` (Type: ObjectId)
- `user_id` (Type: str)
- `type` (Type: str)
- `data` (Type: dict)
- `timestamp` (Type: datetime)

### Collection: `users`
**Sample Document Keys:**
- `_id` (Type: ObjectId)
- `email` (Type: str)
- `name` (Type: str)
- `age` (Type: int)
- `gender` (Type: str)
- `height` (Type: float)
- `weight` (Type: float)
- `activity_level` (Type: str)
- `diet` (Type: str)
- `meal_plan_purchased` (Type: bool)
- `health_condition` (Type: str)
- `region` (Type: NoneType)
- `hashed_password` (Type: str)
- `created_at` (Type: datetime)
- `updated_at` (Type: datetime)

### Collection: `diet_plans`
**Sample Document Keys:**
- `_id` (Type: ObjectId)
- `user_id` (Type: str)
- `created_at` (Type: datetime)
- `meals` (Type: dict)
- `ingredient_checklist` (Type: list)

