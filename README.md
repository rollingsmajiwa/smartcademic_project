
# SmartAcademic — Backend API

## Project Brief
SmartAcademic Backend Project is a RESTful API built with Django and Django REST Framework. It powers user authentication, role-based access control, geofenced teacher attendance verification, live examination delivery, and AI-assisted study workflows.

## Business Rationale
Schools and academic institutions need tamper-proof operational records and secure data isolation between roles. This backend service addresses two primary business needs:
* **Accountability & Verification:** GPS coordinate validation and automated punctuality rules eliminate manual register manipulation.
* **Data Security & Scalability:** Encrypted JWT authentication, tokenized email invitations, and modular REST endpoints ensure secure, reliable communication with client applications.

## Technologies Used
* **Python & Django:** Core web framework for rapid, secure backend development.
* **Django REST Framework (DRF):** Structured API endpoints, serialization, and permission handling.
* **SimpleJWT & Google Auth:** Token-based authentication supporting standard password login and Google Sign-In.
* **Django CORS Headers:** Secure cross-origin resource sharing with the React frontend.
* **PostgreSQL:** Relational database storage for users, classrooms, attendance logs, exams, and submissions.
* **Git/GitHub:** Version control and feature-based branching.

## Accessibility & API Standards
* **Standardized JSON Responses:** Consistent HTTP status codes and descriptive error messages for clear client-side feedback.
* **Role-Based Permissions:** Strict endpoint guards ensuring Admins, Teachers, and Students can only access authorized data.
* **Clean Data Schemas:** Predictable field naming and validation rules across all serializers.

## Product Features
* **Geofenced Attendance Engine:** Validates teacher clock-in coordinates against school boundary limits and executes automated exit logs when stepping outside compound bounds.
* **Punctuality Classification Logic:** Automatically classifies clock-ins at or before `7:00 AM` as *Present*, after `7:00 AM` as *Late*, and unclocked records as *Absent* at `4:30 PM`.
* **Tokenized Invitation System:** Generates encrypted registration links dispatched via email for verified student and teacher onboarding.
* **Academic Management APIs:** Full CRUD support for classrooms, assignments, timed live exams, automated grading, and student submissions.
* **Mwalimu AI Backend:** Processes uploaded study materials to power Socratic student revision prompts.

## Git Workflow
* **Fork the Repository:** Create your own copy of the project to work on.
* **Create a Feature Branch:**
  ```bash
  git checkout -b feature/YourFeatureName
Commit Your Changes

Push to Branch:

```Bash
git push origin feature/YourFeatureName
Open a Pull Request (PR): Describe your changes clearly and link any related issues.
```

## Setup Instructions
a. Clone this repository on your local machine:

```Bash
git clone https://github.com/rollingsmajiwa/smartacademic_project.git
```
```bash
cd smartacademic-backend
```
b. Create and activate a virtual environment:

```Bash
python -m venv .venv
```
### On Windows:
```bash
.venv\Scripts\activate
```

c. Install dependencies:

```Bash
pip install -r requirements.txt
```
d. Configure environment variables:
Create a .env file in the root directory:

```bash
SECRET_KEY=your_django_secret_key
DEBUG=True
CORS_ALLOWED_ORIGINS=http://localhost:5173
GOOGLE_CLIENT_ID=your_google_oauth_client_id
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```
e. Apply database migrations and run the server:

```bash
python manage.py makemigrations
```

```Bash
python manage.py migrate
```
```bash
python manage.py runserver
```
# Screenshots
# Author
Rollings Majiwa

GitHub: [https://github.com/rollingsmajiwa](https://github.com/rollingsmajiwa)

Email: [rollingsmajiwa@gmail.com](rollingsmajiwa@gmail.com)

# Get Started
Interested in the code behind SmartAcademic Backend? You can reach me directly via my profile or open an issue for collaboration. [Visit my GitHub profile](https://github.com/rollingsmajiwa)