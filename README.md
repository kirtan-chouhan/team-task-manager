# Team Task Manager

## Overview

Team Task Manager is a modern internal productivity app built with FastAPI, SQLAlchemy, and MySQL. It provides role-based access control for `ADMIN` and `MEMBER` users, task and project management, activity logging, and a visual workload dashboard powered by Chart.js.

---

## Tech Stack

- Python 3.14
- FastAPI
- SQLAlchemy
- MySQL
- Tailwind CSS
- Chart.js

---

## Installation

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Virtual Environment

- Windows PowerShell:
  ```bash
  .\venv\Scripts\Activate.ps1
  ```

- Windows CMD:
  ```bash
  .\venv\Scripts\activate
  ```

### 3. Install Requirements

```bash
pip install -r requirements.txt
```

### 4. Configure MySQL

Create the MySQL database:

```sql
CREATE DATABASE team_task_manager;
```

Update environment variables as needed:

- `DATABASE_URL`
- `SECRET_KEY`
- `SESSION_MAX_AGE`
- `ENVIRONMENT`

Default DB URL in database.py:
```text
mysql+mysqlconnector://root:root@localhost:3306/team_task_manager
```

---

## Running the App

Start the FastAPI server with Uvicorn:

```bash
uvicorn main:app --reload
```

Then visit the app in your browser at:

```text
http://127.0.0.1:8000
```

---

## Database Schema

Main models defined in database.py:

- `User`
  - name, email, password_hash, role, created_at
  - role values: `ADMIN`, `MEMBER`
- `Task`
  - title, description, status, priority, due_date, project_id, assignee_id
- `Project`
  - name, description, owner_id
- `ActivityLog`
  - action, detail, actor_id, task_id, created_at

---

## Deployment to Railway

1. Connect the GitHub repository to Railway.
2. Add the MySQL plugin in Railway.
3. Set the `DATABASE_URL` environment variable in Railway to your MySQL connection string.
4. Deploy the app with the `main:app` Uvicorn entrypoint.

---

## Usage

- The first registered user becomes `ADMIN`.
- Additional accounts are created as `MEMBER`.
- `ADMIN` users can manage all projects, tasks, and team workload.
- `MEMBER` users only see tasks assigned to them.

---

## Notes

- database.py initializes the schema using SQLAlchemy models.
- main.py includes session management, RBAC, and dashboard data routing.
- dashboard.html renders the workload chart and handles the loading state with Chart.js and Tailwind CSS.