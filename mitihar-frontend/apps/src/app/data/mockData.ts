export type PatientStatus = 'active' | 'inactive' | 'pending' | 'expired';
export type RequestStatus = 'pending' | 'accepted' | 'rejected';
export type DoctorBillingStatus = 'paid' | 'pending' | 'overdue';

export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: 'M' | 'F';
  email: string;
  phone: string;
  doctorId: string;
  status: PatientStatus;
  planExpiry: string;
  bmi: number;
  tdee: number;
  conditions: string[];
  allergies: string[];
  joinedAt: string;
  lastLogin: string;
  adherenceThisWeek: number;
  weight: number;
  targetWeight: number;
  weightHistory: { date: string; value: number }[];
  waterHistory: { date: string; value: number; target: number }[];
  notes: { id: string; text: string; createdAt: string; author: string }[];
}

export interface Doctor {
  id: string;
  name: string;
  email: string;
  phone: string;
  specialty: string;
  activePatients: number;
  codesRemaining: number;
  revenue: number;
  billingStatus: DoctorBillingStatus;
  joinedAt: string;
  status: 'active' | 'inactive';
}

export interface Request {
  id: string;
  name: string;
  age: number;
  email: string;
  phone: string;
  requestedAt: string;
  healthGoals: string;
  status: RequestStatus;
  doctorId: string;
}

export interface Recipe {
  id: string;
  name: string;
  category: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  submittedBy: string;
  submittedAt: string;
  approvalStatus: 'approved' | 'pending' | 'rejected';
  cuisine: string;
  servings: number;
}

export interface FoodItem {
  id: string;
  name: string;
  category: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  submittedBy: string;
  submittedAt: string;
  status: 'approved' | 'pending' | 'rejected';
  rejectionReason?: string;
}

export interface AuditLog {
  id: string;
  actor: string;
  actorRole: 'admin' | 'doctor' | 'system';
  action: string;
  target: string;
  timestamp: string;
  ipAddress: string;
}

export interface Notification {
  id: string;
  text: string;
  time: string;
  read: boolean;
  type: 'request' | 'alert' | 'warning';
}

// === Mock Data ===

export const currentDoctor: Doctor = {
  id: 'doc1',
  name: 'Dr. Ashok Sharma',
  email: 'ashok@mityahar.in',
  phone: '9876543210',
  specialty: 'Dietician',
  activePatients: 24,
  codesRemaining: 8,
  revenue: 6000,
  billingStatus: 'paid',
  joinedAt: '2025-01-15',
  status: 'active',
};

export const currentAdmin = {
  id: 'admin1',
  name: 'Vikram Nair',
  email: 'vikram@mityahar.in',
  role: 'Super Admin',
};

export const patients: Patient[] = [
  {
    id: 'pat1',
    name: 'Radha Sharma',
    age: 34,
    gender: 'F',
    email: 'radha.sharma@gmail.com',
    phone: '9876543211',
    doctorId: 'doc1',
    status: 'active',
    planExpiry: '2026-03-31',
    bmi: 28.4,
    tdee: 2090,
    conditions: ['PCOS', 'Thyroid'],
    allergies: ['Dairy'],
    joinedAt: '2026-01-15',
    lastLogin: '2026-03-04',
    adherenceThisWeek: 43,
    weight: 72,
    targetWeight: 62,
    weightHistory: [
      { date: 'Jan 15', value: 75 },
      { date: 'Jan 22', value: 74.2 },
      { date: 'Jan 29', value: 73.8 },
      { date: 'Feb 05', value: 73.1 },
      { date: 'Feb 12', value: 72.9 },
      { date: 'Feb 19', value: 72.4 },
      { date: 'Feb 26', value: 72.0 },
      { date: 'Mar 05', value: 71.6 },
    ],
    waterHistory: [
      { date: 'Mon', value: 1.8, target: 2.5 },
      { date: 'Tue', value: 2.2, target: 2.5 },
      { date: 'Wed', value: 1.5, target: 2.5 },
      { date: 'Thu', value: 2.0, target: 2.5 },
      { date: 'Fri', value: 2.4, target: 2.5 },
      { date: 'Sat', value: 1.9, target: 2.5 },
      { date: 'Sun', value: 2.1, target: 2.5 },
    ],
    notes: [
      { id: 'n1', text: 'Patient reports feeling tired in the mornings. Adjusted iron intake recommendation.', createdAt: '2026-03-01', author: 'Dr. Ashok Sharma' },
      { id: 'n2', text: 'PCOS management going well. Keep current macros, review in 2 weeks.', createdAt: '2026-02-15', author: 'Dr. Ashok Sharma' },
    ],
  },
  {
    id: 'pat2',
    name: 'Meena Joshi',
    age: 29,
    gender: 'F',
    email: 'meena.joshi@gmail.com',
    phone: '9876541122',
    doctorId: 'doc1',
    status: 'active',
    planExpiry: '2026-04-15',
    bmi: 31.2,
    tdee: 1950,
    conditions: ['Type 2 Diabetes'],
    allergies: ['Gluten'],
    joinedAt: '2026-01-20',
    lastLogin: '2026-03-02',
    adherenceThisWeek: 61,
    weight: 78,
    targetWeight: 68,
    weightHistory: [
      { date: 'Jan 20', value: 80.5 },
      { date: 'Jan 27', value: 80.1 },
      { date: 'Feb 03', value: 79.5 },
      { date: 'Feb 10', value: 79.0 },
      { date: 'Feb 17', value: 78.8 },
      { date: 'Feb 24', value: 78.3 },
      { date: 'Mar 03', value: 78.0 },
    ],
    waterHistory: [
      { date: 'Mon', value: 2.1, target: 2.5 },
      { date: 'Tue', value: 2.5, target: 2.5 },
      { date: 'Wed', value: 2.3, target: 2.5 },
      { date: 'Thu', value: 1.8, target: 2.5 },
      { date: 'Fri', value: 2.2, target: 2.5 },
      { date: 'Sat', value: 2.4, target: 2.5 },
      { date: 'Sun', value: 2.0, target: 2.5 },
    ],
    notes: [],
  },
  {
    id: 'pat3',
    name: 'Suresh Kumar',
    age: 45,
    gender: 'M',
    email: 'suresh.kumar@yahoo.com',
    phone: '9871234567',
    doctorId: 'doc1',
    status: 'active',
    planExpiry: '2026-03-18',
    bmi: 26.1,
    tdee: 2400,
    conditions: ['Hypertension'],
    allergies: [],
    joinedAt: '2025-12-01',
    lastLogin: '2026-03-07',
    adherenceThisWeek: 82,
    weight: 84,
    targetWeight: 78,
    weightHistory: [
      { date: 'Dec 01', value: 88 },
      { date: 'Dec 15', value: 87 },
      { date: 'Jan 01', value: 86.2 },
      { date: 'Jan 15', value: 85.5 },
      { date: 'Feb 01', value: 85 },
      { date: 'Feb 15', value: 84.5 },
      { date: 'Mar 01', value: 84 },
    ],
    waterHistory: [
      { date: 'Mon', value: 2.8, target: 3.0 },
      { date: 'Tue', value: 3.0, target: 3.0 },
      { date: 'Wed', value: 2.9, target: 3.0 },
      { date: 'Thu', value: 3.0, target: 3.0 },
      { date: 'Fri', value: 2.7, target: 3.0 },
      { date: 'Sat', value: 2.5, target: 3.0 },
      { date: 'Sun', value: 2.8, target: 3.0 },
    ],
    notes: [
      { id: 'n3', text: 'Sodium intake reduced successfully. Blood pressure readings improving.', createdAt: '2026-02-20', author: 'Dr. Ashok Sharma' },
    ],
  },
  {
    id: 'pat4',
    name: 'Priya Menon',
    age: 38,
    gender: 'F',
    email: 'priya.menon@outlook.com',
    phone: '9845123456',
    doctorId: 'doc1',
    status: 'inactive',
    planExpiry: '2026-02-01',
    bmi: 22.8,
    tdee: 1820,
    conditions: [],
    allergies: ['Nuts'],
    joinedAt: '2025-11-10',
    lastLogin: '2026-02-01',
    adherenceThisWeek: 0,
    weight: 58,
    targetWeight: 55,
    weightHistory: [
      { date: 'Nov 10', value: 62 },
      { date: 'Nov 24', value: 61 },
      { date: 'Dec 08', value: 60 },
      { date: 'Dec 22', value: 59.5 },
      { date: 'Jan 05', value: 59 },
      { date: 'Jan 19', value: 58.5 },
      { date: 'Feb 01', value: 58 },
    ],
    waterHistory: [],
    notes: [],
  },
  {
    id: 'pat5',
    name: 'Arjun Patel',
    age: 52,
    gender: 'M',
    email: 'arjun.patel@gmail.com',
    phone: '9912345678',
    doctorId: 'doc1',
    status: 'active',
    planExpiry: '2026-05-01',
    bmi: 29.7,
    tdee: 2200,
    conditions: ['Obesity', 'Pre-diabetes'],
    allergies: [],
    joinedAt: '2026-02-01',
    lastLogin: '2026-03-08',
    adherenceThisWeek: 74,
    weight: 91,
    targetWeight: 80,
    weightHistory: [
      { date: 'Feb 01', value: 93 },
      { date: 'Feb 08', value: 92.5 },
      { date: 'Feb 15', value: 92 },
      { date: 'Feb 22', value: 91.5 },
      { date: 'Mar 01', value: 91.2 },
      { date: 'Mar 08', value: 91 },
    ],
    waterHistory: [
      { date: 'Mon', value: 2.0, target: 3.0 },
      { date: 'Tue', value: 2.3, target: 3.0 },
      { date: 'Wed', value: 2.1, target: 3.0 },
      { date: 'Thu', value: 2.5, target: 3.0 },
      { date: 'Fri', value: 2.4, target: 3.0 },
      { date: 'Sat', value: 2.0, target: 3.0 },
      { date: 'Sun', value: 2.2, target: 3.0 },
    ],
    notes: [],
  },
  {
    id: 'pat6',
    name: 'Kavita Singh',
    age: 41,
    gender: 'F',
    email: 'kavita.singh@gmail.com',
    phone: '9867891234',
    doctorId: 'doc1',
    status: 'active',
    planExpiry: '2026-06-15',
    bmi: 24.3,
    tdee: 1980,
    conditions: ['Hypothyroidism'],
    allergies: ['Soy'],
    joinedAt: '2026-02-15',
    lastLogin: '2026-03-07',
    adherenceThisWeek: 88,
    weight: 65,
    targetWeight: 60,
    weightHistory: [
      { date: 'Feb 15', value: 67 },
      { date: 'Feb 22', value: 66.5 },
      { date: 'Mar 01', value: 66 },
      { date: 'Mar 08', value: 65.5 },
    ],
    waterHistory: [
      { date: 'Mon', value: 2.3, target: 2.5 },
      { date: 'Tue', value: 2.5, target: 2.5 },
      { date: 'Wed', value: 2.4, target: 2.5 },
      { date: 'Thu', value: 2.5, target: 2.5 },
      { date: 'Fri', value: 2.2, target: 2.5 },
      { date: 'Sat', value: 2.1, target: 2.5 },
      { date: 'Sun', value: 2.3, target: 2.5 },
    ],
    notes: [],
  },
];

export const pendingRequests: Request[] = [
  {
    id: 'req1',
    name: 'Anjali Verma',
    age: 28,
    email: 'anjali.verma@gmail.com',
    phone: '9876541234',
    requestedAt: '2026-03-07',
    healthGoals: 'Weight loss, manages PCOD. Looking for sustainable meal planning.',
    status: 'pending',
    doctorId: 'doc1',
  },
  {
    id: 'req2',
    name: 'Rohit Patel',
    age: 35,
    email: 'rohit.patel@gmail.com',
    phone: '9834567890',
    requestedAt: '2026-03-06',
    healthGoals: 'Muscle gain and sports performance. Currently training for marathon.',
    status: 'pending',
    doctorId: 'doc1',
  },
  {
    id: 'req3',
    name: 'Sunita Rao',
    age: 48,
    email: 'sunita.rao@hotmail.com',
    phone: '9812345670',
    requestedAt: '2026-03-05',
    healthGoals: 'Diabetes management, need low-GI Indian meal plan.',
    status: 'pending',
    doctorId: 'doc1',
  },
];

export const recipes: Recipe[] = [
  { id: 'rec1', name: 'Moong Dal Cheela', category: 'Breakfast', calories: 185, protein: 12, carbs: 24, fat: 5, submittedBy: 'Dr. Ashok Sharma', submittedAt: '2026-02-20', approvalStatus: 'approved', cuisine: 'North Indian', servings: 2 },
  { id: 'rec2', name: 'Ragi Dosa with Sambar', category: 'Breakfast', calories: 210, protein: 9, carbs: 38, fat: 4, submittedBy: 'Dr. Ashok Sharma', submittedAt: '2026-02-22', approvalStatus: 'approved', cuisine: 'South Indian', servings: 2 },
  { id: 'rec3', name: 'Methi Thepla', category: 'Snack', calories: 145, protein: 5, carbs: 22, fat: 4, submittedBy: 'Dr. Priya Mehta', submittedAt: '2026-03-01', approvalStatus: 'pending', cuisine: 'Gujarati', servings: 3 },
  { id: 'rec4', name: 'Palak Paneer (Low Fat)', category: 'Dinner', calories: 220, protein: 16, carbs: 12, fat: 11, submittedBy: 'Dr. Ashok Sharma', submittedAt: '2026-02-18', approvalStatus: 'approved', cuisine: 'North Indian', servings: 2 },
  { id: 'rec5', name: 'Oats Upma', category: 'Breakfast', calories: 195, protein: 7, carbs: 33, fat: 5, submittedBy: 'Dr. Ashok Sharma', submittedAt: '2026-03-02', approvalStatus: 'approved', cuisine: 'South Indian', servings: 1 },
  { id: 'rec6', name: 'Sprouts Salad Bowl', category: 'Lunch', calories: 175, protein: 14, carbs: 22, fat: 3, submittedBy: 'Dr. Ravi Nair', submittedAt: '2026-03-05', approvalStatus: 'pending', cuisine: 'Generic', servings: 1 },
];

export const allDoctors: Doctor[] = [
  { id: 'doc1', name: 'Dr. Ashok Sharma', email: 'ashok@mityahar.in', phone: '9876543210', specialty: 'Dietician', activePatients: 24, codesRemaining: 8, revenue: 6000, billingStatus: 'paid', joinedAt: '2025-01-15', status: 'active' },
  { id: 'doc2', name: 'Dr. Priya Mehta', email: 'priya@mityahar.in', phone: '9812345678', specialty: 'Nutritionist', activePatients: 18, codesRemaining: 4, revenue: 4500, billingStatus: 'paid', joinedAt: '2025-03-01', status: 'active' },
  { id: 'doc3', name: 'Dr. Ravi Nair', email: 'ravi@mityahar.in', phone: '9834567890', specialty: 'Dietician', activePatients: 31, codesRemaining: 12, revenue: 7750, billingStatus: 'pending', joinedAt: '2024-11-10', status: 'active' },
  { id: 'doc4', name: 'Dr. Sonal Desai', email: 'sonal@mityahar.in', phone: '9856789012', specialty: 'Clinical Nutritionist', activePatients: 9, codesRemaining: 2, revenue: 2250, billingStatus: 'overdue', joinedAt: '2025-06-15', status: 'active' },
  { id: 'doc5', name: 'Dr. Vikram Choudhary', email: 'vikram@mityahar.in', phone: '9867890123', specialty: 'Sports Nutritionist', activePatients: 14, codesRemaining: 18, revenue: 3500, billingStatus: 'paid', joinedAt: '2025-08-20', status: 'inactive' },
];

export const foodDatabase: FoodItem[] = [
  { id: 'food1', name: 'Idli (plain)', category: 'South Indian', calories: 39, protein: 2, carbs: 8, fat: 0.1, submittedBy: 'System', submittedAt: '2024-01-01', status: 'approved' },
  { id: 'food2', name: 'Masoor Dal', category: 'Dal & Legumes', calories: 116, protein: 9, carbs: 20, fat: 0.4, submittedBy: 'System', submittedAt: '2024-01-01', status: 'approved' },
  { id: 'food3', name: 'Chicken Tikka', category: 'Non-Veg', calories: 185, protein: 30, carbs: 6, fat: 5, submittedBy: 'System', submittedAt: '2024-01-01', status: 'approved' },
  { id: 'food4', name: 'Quinoa Pulao', category: 'Grains', calories: 220, protein: 8, carbs: 38, fat: 4, submittedBy: 'Dr. Priya Mehta', submittedAt: '2026-03-03', status: 'pending' },
  { id: 'food5', name: 'Jackfruit Curry', category: 'Vegetables', calories: 155, protein: 3, carbs: 28, fat: 5, submittedBy: 'Dr. Ashok Sharma', submittedAt: '2026-03-04', status: 'pending' },
  { id: 'food6', name: 'Millet Khichdi', category: 'Grains', calories: 190, protein: 6, carbs: 35, fat: 4, submittedBy: 'Dr. Ravi Nair', submittedAt: '2026-03-05', status: 'pending' },
  { id: 'food7', name: 'Keto Bread', category: 'Breads', calories: 95, protein: 5, carbs: 3, fat: 8, submittedBy: 'Dr. Sonal Desai', submittedAt: '2026-02-20', status: 'rejected', rejectionReason: 'Insufficient Indian food context. Not within scope of platform.' },
  { id: 'food8', name: 'Daliya (Broken Wheat)', category: 'Grains', calories: 145, protein: 5, carbs: 28, fat: 1.5, submittedBy: 'System', submittedAt: '2024-01-01', status: 'approved' },
  { id: 'food9', name: 'Rajma', category: 'Dal & Legumes', calories: 127, protein: 9, carbs: 22, fat: 0.5, submittedBy: 'System', submittedAt: '2024-01-01', status: 'approved' },
  { id: 'food10', name: 'Amla Juice', category: 'Beverages', calories: 45, protein: 0.4, carbs: 10, fat: 0.1, submittedBy: 'Dr. Priya Mehta', submittedAt: '2026-02-25', status: 'rejected', rejectionReason: 'Nutritional values unverified.' },
];

export const auditLogs: AuditLog[] = [
  { id: 'log1', actor: 'Vikram Nair', actorRole: 'admin', action: 'Generated 10 subscription codes', target: 'Dr. Ashok Sharma', timestamp: '2026-03-08T09:15:00', ipAddress: '192.168.1.1' },
  { id: 'log2', actor: 'Dr. Ashok Sharma', actorRole: 'doctor', action: 'Accepted patient request', target: 'Anjali Verma', timestamp: '2026-03-08T08:42:00', ipAddress: '10.0.0.5' },
  { id: 'log3', actor: 'Dr. Ravi Nair', actorRole: 'doctor', action: 'Submitted recipe for approval', target: 'Sprouts Salad Bowl', timestamp: '2026-03-07T16:30:00', ipAddress: '10.0.0.8' },
  { id: 'log4', actor: 'Vikram Nair', actorRole: 'admin', action: 'Approved food item', target: 'Ragi Dosa with Sambar', timestamp: '2026-03-07T14:20:00', ipAddress: '192.168.1.1' },
  { id: 'log5', actor: 'Dr. Sonal Desai', actorRole: 'doctor', action: 'Updated patient meal plan', target: 'Patient #P-0091', timestamp: '2026-03-07T11:05:00', ipAddress: '10.0.0.9' },
  { id: 'log6', actor: 'System', actorRole: 'system', action: 'Auto-deactivated expired subscription', target: 'Patient Priya Menon', timestamp: '2026-03-07T00:01:00', ipAddress: 'system' },
  { id: 'log7', actor: 'Vikram Nair', actorRole: 'admin', action: 'Marked billing as overdue', target: 'Dr. Sonal Desai', timestamp: '2026-03-06T17:00:00', ipAddress: '192.168.1.1' },
  { id: 'log8', actor: 'Dr. Priya Mehta', actorRole: 'doctor', action: 'Rejected patient request', target: 'Anonymous Request', timestamp: '2026-03-06T15:30:00', ipAddress: '10.0.0.6' },
];

export const doctorNotifications: Notification[] = [
  { id: 'notif1', text: 'New patient request — Anjali Verma', time: '2 hours ago', read: false, type: 'request' },
  { id: 'notif2', text: 'Radha Sharma hasn\'t logged in 4 days', time: '5 hours ago', read: false, type: 'alert' },
  { id: 'notif3', text: 'Meena Joshi hasn\'t logged in 6 days', time: '1 day ago', read: false, type: 'alert' },
  { id: 'notif4', text: 'Your codes are low — 8 remaining', time: '2 days ago', read: true, type: 'warning' },
  { id: 'notif5', text: 'Suresh Kumar\'s plan expires in 10 days', time: '3 days ago', read: true, type: 'warning' },
];

export const adminNotifications: Notification[] = [
  { id: 'anotif1', text: 'Dr. Sonal billing overdue — ₹2,250 pending', time: '1 day ago', read: false, type: 'alert' },
  { id: 'anotif2', text: '3 food items pending approval', time: '2 hours ago', read: false, type: 'warning' },
  { id: 'anotif3', text: 'Dr. Sonal has only 2 codes left', time: '3 hours ago', read: false, type: 'warning' },
  { id: 'anotif4', text: 'New doctor registered — Dr. Vikram Choudhary', time: '1 week ago', read: true, type: 'request' },
];

export const mealPlan = {
  breakfast: {
    name: 'Moong Dal Cheela',
    calories: 185,
    protein: 12,
    carbs: 24,
    fat: 5,
    time: '8:00 AM',
    doctorNote: 'Add one cup of low-fat curd on the side.',
  },
  lunch: {
    name: 'Brown Rice + Palak Paneer + Salad',
    calories: 420,
    protein: 18,
    carbs: 58,
    fat: 12,
    time: '1:00 PM',
    doctorNote: '',
  },
  eveningSnack: {
    name: 'Roasted Makhana (1 cup)',
    calories: 120,
    protein: 4,
    carbs: 18,
    fat: 3,
    time: '4:30 PM',
    doctorNote: 'Sprinkle light black salt. Avoid adding butter.',
  },
  dinner: {
    name: 'Roti (2) + Dal Tadka + Sabzi',
    calories: 380,
    protein: 15,
    carbs: 62,
    fat: 8,
    time: '7:30 PM',
    doctorNote: '',
  },
};

export interface DayMeal {
  name: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  time: string;
  doctorNote: string;
}

export interface WeekDay {
  day: 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday' | 'Friday' | 'Saturday' | 'Sunday';
  meals: {
    breakfast: DayMeal;
    lunch: DayMeal;
    eveningSnack: DayMeal;
    dinner: DayMeal;
  };
}

export const weekPlan: WeekDay[] = [
  {
    day: 'Monday',
    meals: {
      breakfast: { name: 'Moong Dal Cheela', calories: 185, protein: 12, carbs: 24, fat: 5, time: '8:00 AM', doctorNote: 'Add one cup of low-fat curd on the side.' },
      lunch: { name: 'Brown Rice + Palak Paneer + Salad', calories: 420, protein: 18, carbs: 58, fat: 12, time: '1:00 PM', doctorNote: '' },
      eveningSnack: { name: 'Roasted Makhana (1 cup)', calories: 120, protein: 4, carbs: 18, fat: 3, time: '4:30 PM', doctorNote: 'Sprinkle light black salt. Avoid butter.' },
      dinner: { name: 'Roti (2) + Dal Tadka + Sabzi', calories: 380, protein: 15, carbs: 62, fat: 8, time: '7:30 PM', doctorNote: '' },
    },
  },
  {
    day: 'Tuesday',
    meals: {
      breakfast: { name: 'Oats Upma with Vegetables', calories: 210, protein: 8, carbs: 35, fat: 5, time: '8:00 AM', doctorNote: '' },
      lunch: { name: 'Rajma Rice + Raita', calories: 445, protein: 19, carbs: 65, fat: 10, time: '1:00 PM', doctorNote: '' },
      eveningSnack: { name: 'Sprout Chaat', calories: 130, protein: 9, carbs: 20, fat: 2, time: '4:30 PM', doctorNote: 'No fried additions.' },
      dinner: { name: 'Methi Thepla (2) + Low-fat Curd', calories: 340, protein: 12, carbs: 55, fat: 9, time: '7:30 PM', doctorNote: '' },
    },
  },
  {
    day: 'Wednesday',
    meals: {
      breakfast: { name: 'Ragi Dosa with Sambar', calories: 220, protein: 9, carbs: 38, fat: 4, time: '8:00 AM', doctorNote: '' },
      lunch: { name: 'Khichdi + Papad + Small Pickle', calories: 390, protein: 14, carbs: 60, fat: 9, time: '1:00 PM', doctorNote: 'Use minimal oil in khichdi.' },
      eveningSnack: { name: 'Banana + Handful Almonds', calories: 160, protein: 5, carbs: 28, fat: 6, time: '4:30 PM', doctorNote: '' },
      dinner: { name: 'Roti (2) + Chana Masala + Salad', calories: 400, protein: 17, carbs: 63, fat: 9, time: '7:30 PM', doctorNote: '' },
    },
  },
  {
    day: 'Thursday',
    meals: {
      breakfast: { name: 'Poha with Peas', calories: 195, protein: 6, carbs: 36, fat: 4, time: '8:00 AM', doctorNote: '' },
      lunch: { name: 'Jeera Rice + Dal Makhani + Sabzi', calories: 460, protein: 17, carbs: 68, fat: 12, time: '1:00 PM', doctorNote: '' },
      eveningSnack: { name: 'Roasted Chana (30g)', calories: 115, protein: 7, carbs: 18, fat: 2, time: '4:30 PM', doctorNote: '' },
      dinner: { name: 'Multigrain Roti (2) + Egg Bhurji', calories: 370, protein: 20, carbs: 45, fat: 13, time: '7:30 PM', doctorNote: 'Skip if patient is vegetarian.' },
    },
  },
  {
    day: 'Friday',
    meals: {
      breakfast: { name: 'Idli (3) + Sambar + Coconut Chutney', calories: 230, protein: 8, carbs: 42, fat: 5, time: '8:00 AM', doctorNote: '' },
      lunch: { name: 'Chole + Bhature (1) + Onion Salad', calories: 480, protein: 16, carbs: 72, fat: 14, time: '1:00 PM', doctorNote: 'One bhature only. Add extra salad.' },
      eveningSnack: { name: 'Fruit Bowl (Apple + Pomegranate)', calories: 110, protein: 1, carbs: 27, fat: 0, time: '4:30 PM', doctorNote: '' },
      dinner: { name: 'Roti (2) + Lauki Sabzi + Dal', calories: 355, protein: 14, carbs: 58, fat: 7, time: '7:30 PM', doctorNote: '' },
    },
  },
  {
    day: 'Saturday',
    meals: {
      breakfast: { name: 'Vegetable Upma', calories: 200, protein: 6, carbs: 34, fat: 5, time: '8:30 AM', doctorNote: '' },
      lunch: { name: 'Pulao + Raita + Papad', calories: 430, protein: 13, carbs: 67, fat: 11, time: '1:00 PM', doctorNote: '' },
      eveningSnack: { name: 'Makhana Kheer (small bowl)', calories: 145, protein: 5, carbs: 26, fat: 3, time: '5:00 PM', doctorNote: 'Use low-fat milk.' },
      dinner: { name: 'Paneer Bhurji + Roti (2)', calories: 410, protein: 22, carbs: 48, fat: 15, time: '8:00 PM', doctorNote: '' },
    },
  },
  {
    day: 'Sunday',
    meals: {
      breakfast: { name: 'Stuffed Paratha (1) + Curd', calories: 280, protein: 9, carbs: 40, fat: 10, time: '9:00 AM', doctorNote: 'Use minimal ghee. One paratha only.' },
      lunch: { name: 'Dal + Sabzi + Rice + Salad', calories: 440, protein: 16, carbs: 66, fat: 10, time: '1:30 PM', doctorNote: '' },
      eveningSnack: { name: 'Green Tea + Mixed Nuts (20g)', calories: 130, protein: 4, carbs: 6, fat: 11, time: '5:00 PM', doctorNote: '' },
      dinner: { name: 'Soup + Multigrain Roti (2) + Sabzi', calories: 340, protein: 13, carbs: 55, fat: 8, time: '7:30 PM', doctorNote: '' },
    },
  },
];

export const activityLogs = [
  { date: '2026-03-08', meal: 'Breakfast', item: 'Moong Dal Cheela', calories: 185, logged: true },
  { date: '2026-03-08', meal: 'Lunch', item: 'Brown Rice + Dal', calories: 390, logged: true },
  { date: '2026-03-08', meal: 'Snack', item: 'Banana', calories: 95, logged: true },
  { date: '2026-03-07', meal: 'Breakfast', item: 'Ragi Dosa', calories: 210, logged: true },
  { date: '2026-03-07', meal: 'Lunch', item: 'Rajma Rice', calories: 440, logged: true },
  { date: '2026-03-07', meal: 'Dinner', item: 'Roti + Dal', calories: 380, logged: false },
  { date: '2026-03-06', meal: 'Breakfast', item: 'Oats Upma', calories: 195, logged: true },
  { date: '2026-03-06', meal: 'Lunch', item: 'Palak Paneer + Rice', calories: 450, logged: false },
  { date: '2026-03-06', meal: 'Snack', item: 'Makhana', calories: 120, logged: true },
  { date: '2026-03-06', meal: 'Dinner', item: 'Methi Thepla + Curd', calories: 310, logged: false },
];
