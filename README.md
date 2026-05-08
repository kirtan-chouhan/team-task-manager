# Team Task Manager

A modern, full-stack team collaboration application for managing tasks and projects with role-based access control. Built with FastAPI, MySQL, and SQLAlchemy, featuring real-time workload analytics and a responsive Jinja2 frontend.

---

## Features

✅ **Role-Based Access Control (RBAC)**
- Admin users: Full system access, manage all projects and tasks
- Member users: View and update only assigned tasks

✅ **Task Management**
- Create, update, delete tasks with priority levels (HIGH, MEDIUM, LOW)
- Set due dates and track task status (TO_DO, DOING, DONE)
- Task assignment to team members
- Real-time activity logging

✅ **Project Management**
- Organize tasks by projects
- Admin-only project creation and updates
- Project descriptions and task tracking

✅ **Analytics & Dashboard**
- Live workload distribution chart (Chart.js)
- Task completion trend (7-day view)
- Project load visualization
- Delivery health metrics
- Personal task statistics for Members

✅ **Cloud-Ready Architecture**
- REST API endpoints for all operations
- Railway.app deployment support
- Environment-based database configuration
- Session management with JWT tokens

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend Framework | FastAPI |
| Database | MySQL |
| ORM | SQLAlchemy |
| Authentication | JWT + Session Middleware |
| Frontend | Jinja2 Templates |
| UI Framework | Tailwind CSS |
| Charts | Chart.js |
| Password Security | bcrypt + SHA256 |
| Language | Python 3.14 |

---

## Installation

### Prerequisites

- Python 3.14+
- MySQL 8.0+
- pip (Python package manager)

### Step 1: Clone and Setup Virtual Environment

```bash
git clone <your-repo-url>
cd Team\ task\ manager
python -m venv venv
```

**Activate Virtual Environment:**

- Windows (PowerShell):
  ```bash
  .\venv\Scripts\Activate.ps1
  ```

- Windows (CMD):
  ```bash
  .\venv\Scripts\activate
  ```

- macOS/Linux:
  ```bash
  source venv/bin/activate
  ```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure MySQL Database

Create the database:

```sql
CREATE DATABASE team_task_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Step 4: Set Environment Variables (Optional for Local Development)

Create a `.env` file in the project root:

```env
DATABASE_URL=mysql+mysqlconnector://root:root@localhost:3306/team_task_manager
SECRET_KEY=your-secret-key-here
SESSION_MAX_AGE=86400
ENVIRONMENT=development
```

**Default values** (if `.env` not provided):
- `DATABASE_URL`: `mysql+mysqlconnector://root:root@localhost:3306/team_task_manager`
- `SECRET_KEY`: `change-this-before-production`
- `ENVIRONMENT`: `development`

### Step 5: Run the Application

```bash
uvicorn main:app --reload
```

The application will start on `http://127.0.0.1:8000`

---

## Database Schema

### Users Table
```
- id (Primary Key)
- name (String, 120 chars)
- email (String, 255 chars, Unique)
- password_hash (String, 255 chars)
- role (Enum: ADMIN | MEMBER)
- created_at (DateTime)
```

### Projects Table
```
- id (Primary Key)
- name (String, 180 chars)
- description (Text, optional)
- owner_id (Foreign Key → Users)
- created_at (DateTime)
```

### Tasks Table
```
- id (Primary Key)
- title (String, 220 chars)
- description (Text, optional)
- status (Enum: TO_DO | DOING | DONE)
- priority (Enum: HIGH | MEDIUM | LOW)
- due_date (DateTime, optional)
- project_id (Foreign Key → Projects)
- assignee_id (Foreign Key → Users)
- created_at (DateTime)
- updated_at (DateTime)
```

### Activity Logs Table
```
- id (Primary Key)
- action (String, 120 chars)
- detail (Text)
- actor_id (Foreign Key → Users)
- task_id (Foreign Key → Tasks, nullable)
- created_at (DateTime)
```

---

## API Documentation

All endpoints require authentication via session tokens. Base URL: `/api`

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/signup` | POST | Register a new user (first user becomes ADMIN) |
| `/login` | POST | Sign in with email and password |
| `/logout` | POST | Clear session and sign out |

### Tasks

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/tasks` | GET | Required | List all visible tasks (filtered by role) |
| `/api/tasks` | POST | ADMIN | Create a new task |
| `/api/tasks/{task_id}/status` | POST | Required | Update task status |
| `/api/tasks/{task_id}/delete` | POST | ADMIN | Delete a task |

### Projects

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/projects` | GET | Required | List all visible projects |
| `/api/projects` | POST | ADMIN | Create a new project |
| `/api/projects/{project_id}` | POST | ADMIN | Update project details |
| `/api/projects/{project_id}/delete` | POST | ADMIN | Delete a project |

### Analytics

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/dashboard-data` | GET | Required | Get chart data for dashboard |
| `/api/stats` | GET | Required | Get task statistics (total, completed, overdue) |

### Profile

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/profile` | POST | Required | Update user profile (name, email) |

### Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health check |

---

## Deployment to Railway

### Prerequisites

- GitHub account with repository
- Railway account (https://railway.app)

### Step 1: Connect GitHub Repository

1. Log in to Railway dashboard
2. Click "New Project" → "Deploy from GitHub"
3. Select your repository
4. Authorize Railway to access your GitHub account

### Step 2: Add MySQL Database Service

1. In Railway project dashboard, click "Add Service"
2. Select "MySQL"
3. Railway will provision a MySQL instance and auto-generate `DATABASE_URL`

### Step 3: Configure Environment Variables

In Railway project settings, add or verify:

```
DATABASE_URL=mysql://user:password@your-railway-host:port/team_task_manager
SECRET_KEY=your-production-secret-key
ENVIRONMENT=production
PORT=3000
```

**Note:** Railway automatically sets `DATABASE_URL` when MySQL service is added.

### Step 4: Deploy Application

1. Create a `Procfile` in the project root:
   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

2. Ensure `requirements.txt` includes all dependencies

3. Railway will auto-detect and deploy on every GitHub push

### Step 5: Verify Deployment

- Visit your Railway app URL
- Check logs in Railway dashboard for errors
- Use the `/health` endpoint to verify the server is running

---

## Usage Guide

### First Login

1. Visit the application
2. Click "Register"
3. Enter name, email, and password
4. The first registered user automatically becomes `ADMIN`
5. Subsequent users are registered as `MEMBER`

### Admin Capabilities

- View all tasks and projects
- Create projects
- Assign tasks to team members
- Update and delete projects
- View team workload distribution
- Change task priorities and statuses

### Member Capabilities

- View only assigned tasks
- Update status of assigned tasks
- Edit profile information
- View personal task statistics
- Cannot create projects or assign tasks to others

### Dashboard Sections

- **Work Intelligence**: Overview of total, completed, and overdue tasks
- **Completion Trend**: 7-day trend of completed tasks
- **Workload Chart** (Admin only): Distribution of tasks across team members
- **Task Status**: Pie chart of TO_DO, DOING, DONE tasks
- **Project Load**: Bar chart of tasks per project
- **Delivery Health**: Polar chart of completion, overdue, and remaining work
- **Activity Feed**: Recent task changes logged by system

---

## File Structure

```
Team task manager/
├── main.py                      # FastAPI application and routes
├── database.py                  # SQLAlchemy models and configuration
├── requirements.txt             # Python dependencies
├── Procfile                     # Railway deployment configuration
├── README.md                    # This file
├── static/                      # Static assets (CSS, images)
└── templates/
    ├── dashboard.html           # Main dashboard template
    ├── login.html               # Login page
    └── register.html            # Registration page
```

---

## Environment Variables

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `DATABASE_URL` | `mysql+mysqlconnector://root:root@localhost:3306/team_task_manager` | No | MySQL connection string |
| `SECRET_KEY` | `change-this-before-production` | No | JWT and session signing key |
| `SESSION_MAX_AGE` | `86400` | No | Session timeout in seconds (24h) |
| `ENVIRONMENT` | `development` | No | Set to `production` for HTTPS-only cookies |
| `PORT` | `8000` | No | Application port (auto-set by Railway) |

---

## Troubleshooting

### Issue: Database Connection Error

**Solution**: Verify MySQL is running and connection string is correct:
```bash
# Test MySQL connection
mysql -h localhost -u root -p team_task_manager
```

### Issue: "ModuleNotFoundError: No module named 'mysql'"

**Solution**: Install mysql-connector-python:
```bash
pip install mysql-connector-python
```

### Issue: Port Already in Use

**Solution**: Change the port or kill the existing process:
```bash
# Run on different port
uvicorn main:app --port 8001
```

### Issue: Railway Deployment Fails

**Solution**: Check logs and verify:
1. `Procfile` is present and correct
2. `requirements.txt` has all dependencies
3. `DATABASE_URL` is set in Railway variables
4. MySQL service is linked to the project

---

## Development Notes

- The application uses JWT tokens stored in sessions for authentication
- Passwords are hashed using bcrypt with SHA256 digests
- MySQL uses connection pooling with 3600-second recycle for cloud stability
- All date/times are in UTC (datetime.utcnow())
- The workload chart only displays for `ADMIN` users

---

## License

This project is provided as-is for educational and assessment purposes.

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Railway deployment logs
3. Verify all environment variables are correctly set
4. Ensure MySQL service is running and accessible
