# Bruce => Authentication & Onboarding

**Role:** You own the user's first experience — signing up, logging in, and setting up their business profile. You also define the User and Company data models.

---

## Your Files

| File                     | What it does                        |
| ------------------------ | ----------------------------------- |
| `screens/auth_screen.py` | Login/Signup tabbed screen          |
| `screens/onboarding.py`  | Business profile form for new users |
| `models/user.py`         | User and Company dataclasses        |

---

## What To Build

### 1. `models/user.py` (do this first)

**Urgency:** HIGH — Priscilla needs the User model for DB queries

---

### 2. `screens/auth_screen.py` — AuthScreen

**Urgency:** HIGH — first screen users see, gates the whole app

**What it does:**

- Tabbed screen with "Login" and "Signup" tabs
- **Login tab:** username input + password input + "Sign In" button
  - On click: query DB for user → `bcrypt.checkpw(password, stored_hash)` → if match, push dashboard
  - On fail: show error notification
- **Signup tab:** username input + password input + company name input + "Create Account" button
  - On click: insert into users table with hashed password → push onboarding screen

### 3. `screens/onboarding.py` — OnboardingScreen

**Urgency:** MEDIUM — only shown to new users after signup

**What it does:**

- Form with: Company Name (pre-filled from signup), Contact Email, Address, Business Hours (default: "Mon-Fri 8:00-17:00")
- On submit: update the company record with full details → push dashboard

---

## How To Test Your Work

1. **Auth flow:** Run `python main.py` → verify login/signup tabs render
2. **Login:** Try wrong password → see error. Try correct → pushed to dashboard
3. **Signup:** Create new account → verify user appears in MySQL (`SELECT * FROM users`)
4. **Onboarding:** Fill form → verify company updated in MySQL (`SELECT * FROM companies`)

---

## Dependencies

- You need **Priscilla's** `DatabaseManager` with these methods: `fetch_user_by_username()`, `insert_company()`, `insert_user()`, `update_company()`
- You need **David's** `app.py` to register your screens
