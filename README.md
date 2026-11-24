# CareConnect – Elderly Care & Assistance Portal
### Final MVP (Minimum Viable Product)

CareConnect is an elderly care and assistance portal designed to simplify daily care coordination and help elderly individuals independently manage their everyday needs. The platform provides a centralized interface for managing medicine schedules, appointments, daily well-being check-ins, emergency contacts, and assistance requests.

The Final MVP focuses on delivering a functional and accessible experience for the **Elderly Person role**, with an emphasis on simplicity, usability, security, and reliable information management.

## Features

- **Secure Authentication:** Elderly user login with password hashing and secure session management.
- **Personal Dashboard:** Centralized overview of important information and daily activities.
- **Daily Well-being Check-in:** Record daily health-related status as WELL or NOT WELL.
- **Medicine Management:** Add, view, and manage medicines and their schedules.
- **Appointment Management:** Organize and maintain personal appointment details.
- **Emergency Contacts:** Store important contacts with a direct call action.
- **Help Requests:** Request assistance with groceries, transportation, companionship, home help, and technology support.
- **Notifications:** Access relevant reminders and application updates.
- **Profile Management:** View and update personal profile information.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Data Validation | Pydantic |
| Frontend | Jinja2, HTML, CSS, JavaScript |
| Authentication | JWT-based authentication |
| Password Security | bcrypt hashing |
| Session Management | HttpOnly Cookie |

## Demo Credentials

The following synthetic credentials can be used to explore the application:

- **Email:** `elder@example.com`
- **Password:** `Demo12345!`

*Note: Change demonstration credentials before any production deployment.*

## Installation and Setup

### Prerequisites

- Python 3.10+
- PostgreSQL
- pip

### Steps

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd <project-folder>
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   **Windows:**
   ```bash
   .venv\Scripts\activate
   ```

   **Linux/macOS:**
   ```bash
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables by copying `.env.example` to `.env` and setting the required database connection and secret key.

5. Initialize the demo account and required data:

   ```bash
   python -m scripts.seed
   ```

6. Start the application:

   ```bash
   uvicorn index:app --reload
   ```

7. Open the application:

   ```text
   http://127.0.0.1:8000/login
   ```

## Accessibility and User Experience

CareConnect is designed with elderly users as its primary audience. Its interface emphasizes:

- Large, readable text and clearly identifiable buttons.
- High-contrast visual elements.
- Simple navigation and accessible form labels.
- Visible keyboard focus indicators.
- Text and icons alongside status indicators.
- Responsive layouts for different screen sizes.

## Current MVP Scope

- The current release delivers the core elderly-user as the intended user for this application.
- The other users such as family and volunteer users for assistance to the elderly user. 
- The current release has user logins and registrations for family and volunteer users.
- The family members can request the connection the elderly-user and a notification will be sent to the elderly-user.
- The elderly user can accept or decline the family connection.
- The elderly-user can request for help through the Help Request option, a notification will be sent to the volunteer with the details for the help request.
- There is only one admin user which tracks all the user activities and can deactivate any user account in case of any mischief.

## Disclaimer

CareConnect is a care coordination and reminder application. It is **not a medical device or an emergency-response service**. Daily well-being check-ins do not constitute medical assessments, and the application does not provide emergency dispatch or medical intervention.

---

**Project:** CareConnect – Elderly Care & Assistance Portal  
**Release:** Final MVP  
**Project Type:** Academic Community Project  
**Primary User:** Elderly Person
