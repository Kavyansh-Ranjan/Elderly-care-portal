# CareConnect – Elderly Care & Assistance Portal (Review 2 Prototype)

This Review 2 build is intentionally focused on **one user role: Elderly Person**. Family, volunteer and administrator login/demo flows have been removed from the authentication and UI so the initial implementation can be demonstrated clearly.

## Elderly demo features
- Secure elderly-only login
- Personal dashboard
- Daily WELL / NOT WELL check-in
- Medicine management and schedules
- Appointment management
- Emergency contacts with call action
- Help requests for groceries, transport, companionship, home help and technology support
- Notifications
- Elderly profile management

## Demo credentials
- Email: `elder@example.com`
- Password: `Demo12345!`

## Stack
- Python + FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- Jinja2 + HTML/CSS/JavaScript
- bcrypt password hashing
- HttpOnly session cookie

## Run
1. Create a PostgreSQL database.
2. Copy `.env.example` to `.env` and set `DATABASE_URL` and `SECRET_KEY`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Seed the demo elderly account: `python -m scripts.seed`.
5. Start the server: `uvicorn index:app --reload`.
6. Open `/login`.

The prototype is designed for Community Project Review 2 and deliberately keeps the demonstration scope small and functional.
