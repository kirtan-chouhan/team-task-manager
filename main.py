import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session, joinedload
from starlette.middleware.sessions import SessionMiddleware

from database import ActivityLog, Project, Task, User, get_db, init_db


SECRET_KEY = os.getenv("SECRET_KEY", "change-this-before-production")
ALGORITHM = "HS256"
SESSION_MAX_AGE = int(os.getenv("SESSION_MAX_AGE", "86400"))

app = FastAPI(title="Team Task Manager")
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=os.getenv("ENVIRONMENT") == "production",
)

templates = Jinja2Templates(directory="templates")


class SignupSchema(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProjectSchema(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    description: Optional[str] = Field(default=None, max_length=2000)


class TaskSchema(BaseModel):
    title: str = Field(min_length=2, max_length=220)
    description: Optional[str] = Field(default=None, max_length=2000)
    project_id: int = Field(gt=0)
    assignee_id: int = Field(gt=0)
    priority: str = Field(default="MEDIUM", pattern="^(HIGH|MEDIUM|LOW)$")
    due_date: Optional[datetime] = None


class TaskUpdateSchema(BaseModel):
    title: str = Field(min_length=2, max_length=220)
    description: Optional[str] = Field(default=None, max_length=2000)
    project_id: int = Field(gt=0)
    assignee_id: int = Field(gt=0)
    priority: str = Field(pattern="^(HIGH|MEDIUM|LOW)$")
    due_date: Optional[datetime] = None


class StatusSchema(BaseModel):
    status: str = Field(pattern="^(TO_DO|DOING|DONE)$")


class ProfileSchema(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def hash_password(password: str) -> str:
    password_digest = hashlib.sha256(password.encode("utf-8")).digest()
    return bcrypt.hashpw(password_digest, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    password_digest = hashlib.sha256(password.encode("utf-8")).digest()
    return bcrypt.checkpw(password_digest, password_hash.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    expires = datetime.utcnow() + timedelta(seconds=SESSION_MAX_AGE)
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def flash(request: Request, message: str, category: str = "success") -> None:
    request.session["flash"] = {"message": message, "category": category}


def pop_flash(request: Request) -> Optional[dict]:
    return request.session.pop("flash", None)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = request.session.get("access_token")
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        request.session.clear()
        return None

    return db.query(User).filter(User.id == user_id).first()


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    # RBAC middleware dependency: routes using this guard are restricted to
    # ADMIN users. MEMBER users can still authenticate, but they receive a
    # 403 response before protected business logic is executed.
    if user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return user


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=status.HTTP_303_SEE_OTHER)


def parse_due_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d")


def log_activity(
    db: Session,
    actor: User,
    action: str,
    detail: str,
    task: Optional[Task] = None,
) -> None:
    db.add(
        ActivityLog(
            action=action,
            detail=detail,
            actor_id=actor.id,
            task_id=task.id if task else None,
        )
    )


def completion_trend(tasks: list[Task]) -> dict:
    today = datetime.utcnow().date()
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    completed_tasks = [task for task in tasks if task.status == "DONE"]

    return {
        "labels": [day.strftime("%b %d") for day in days],
        "values": [
            len([
                task for task in completed_tasks
                if task.updated_at and task.updated_at.date() == day
            ])
            for day in days
        ],
    }


def build_dashboard_context(request: Request, db: Session, user: User) -> dict:
    now = datetime.utcnow()
    due_soon_at = now + timedelta(hours=24)
    task_query = db.query(Task).options(
        joinedload(Task.project),
        joinedload(Task.assignee),
    )
    project_query = db.query(Project).options(joinedload(Project.tasks))

    if user.role == "MEMBER":
        task_query = task_query.filter(Task.assignee_id == user.id)
        project_query = project_query.join(Task).filter(Task.assignee_id == user.id)

    tasks = task_query.order_by(
        Task.due_date.is_(None),
        Task.due_date.asc(),
        Task.id.desc(),
    ).all()
    projects = project_query.distinct().order_by(Project.created_at.desc()).all()
    project_task_counts = {project.id: 0 for project in projects}
    for task in tasks:
        project_task_counts[task.project_id] = (
            project_task_counts.get(task.project_id, 0) + 1
        )
    users = db.query(User).order_by(User.name.asc()).all()
    total_tasks = len(tasks)
    completed_tasks = len([task for task in tasks if task.status == "DONE"])
    doing_tasks = len([task for task in tasks if task.status == "DOING"])
    todo_tasks = len([task for task in tasks if task.status == "TO_DO"])
    overdue_tasks = [
        task for task in tasks if task.due_date and task.due_date < now
        and task.status != "DONE"
    ]
    completed_percent = (
        round((completed_tasks / total_tasks) * 100) if total_tasks else 0
    )
    due_soon_task_ids = {
        task.id for task in tasks
        if task.due_date and now <= task.due_date <= due_soon_at
        and task.status != "DONE"
    }
    overdue_task_ids = {task.id for task in overdue_tasks}
    workload_labels = []
    workload_values = []
    if user.role == "ADMIN":
        for member in users:
            workload_labels.append(member.name)
            workload_values.append(
                len([task for task in tasks if task.assignee_id == member.id])
            )
    personal_stats = {
        "completed": completed_tasks,
        "pending": max(total_tasks - completed_tasks, 0),
    }
    activity_query = db.query(ActivityLog).options(
        joinedload(ActivityLog.actor),
        joinedload(ActivityLog.task),
    )
    if user.role == "MEMBER":
        visible_task_ids = [task.id for task in tasks]
        if visible_task_ids:
            activity_query = activity_query.filter(
                ActivityLog.task_id.in_(visible_task_ids)
            )
        else:
            activity_query = activity_query.filter(ActivityLog.id == -1)
    activities = (
        activity_query.order_by(ActivityLog.created_at.desc())
        .limit(10)
        .all()
    )
    trend = completion_trend(tasks)

    return {
        "request": request,
        "user": user,
        "users": users,
        "projects": projects,
        "project_task_counts": project_task_counts,
        "tasks": tasks,
        "total_tasks": total_tasks,
        "completed_percent": completed_percent,
        "overdue_count": len(overdue_tasks),
        "due_soon_task_ids": due_soon_task_ids,
        "overdue_task_ids": overdue_task_ids,
        "personal_stats": personal_stats,
        "activities": activities,
        "chart_data": {
            "status_labels": ["To Do", "In Progress", "Done"],
            "status_values": [todo_tasks, doing_tasks, completed_tasks],
            "trend_labels": trend["labels"],
            "trend_values": trend["values"],
            "project_labels": [project.name for project in projects[:8]],
            "project_values": [
                project_task_counts.get(project.id, 0)
                for project in projects[:8]
            ],
            "health_labels": ["Completed", "Overdue", "Remaining"],
            "health_values": [
                completed_tasks,
                len(overdue_tasks),
                max(total_tasks - completed_tasks - len(overdue_tasks), 0),
            ],
            "workload_labels": workload_labels,
            "workload_values": workload_values,
        },
        "now": now,
        "flash": pop_flash(request),
    }


def get_dashboard_chart_data(db: Session, user: User) -> dict:
    now = datetime.utcnow()
    due_soon_at = now + timedelta(hours=24)
    task_query = db.query(Task).options(
        joinedload(Task.project),
        joinedload(Task.assignee),
    )
    project_query = db.query(Project).options(joinedload(Project.tasks))

    if user.role == "MEMBER":
        task_query = task_query.filter(Task.assignee_id == user.id)
        project_query = project_query.join(Task).filter(Task.assignee_id == user.id)

    tasks = task_query.order_by(
        Task.due_date.is_(None),
        Task.due_date.asc(),
        Task.id.desc(),
    ).all()
    projects = project_query.distinct().order_by(Project.created_at.desc()).all()
    project_task_counts = {project.id: 0 for project in projects}
    for task in tasks:
        project_task_counts[task.project_id] = (
            project_task_counts.get(task.project_id, 0) + 1
        )
    total_tasks = len(tasks)
    completed_tasks = len([task for task in tasks if task.status == "DONE"])
    doing_tasks = len([task for task in tasks if task.status == "DOING"])
    todo_tasks = len([task for task in tasks if task.status == "TO_DO"])
    overdue_tasks = [
        task for task in tasks if task.due_date and task.due_date < now
        and task.status != "DONE"
    ]
    workload_labels = []
    workload_values = []
    if user.role == "ADMIN":
        users = db.query(User).order_by(User.name.asc()).all()
        for member in users:
            workload_labels.append(member.name)
            workload_values.append(
                len([task for task in tasks if task.assignee_id == member.id])
            )

    return {
        "status_labels": ["To Do", "In Progress", "Done"],
        "status_values": [todo_tasks, doing_tasks, completed_tasks],
        "trend_labels": completion_trend(tasks)["labels"],
        "trend_values": completion_trend(tasks)["values"],
        "project_labels": [project.name for project in projects[:8]],
        "project_values": [
            project_task_counts.get(project.id, 0)
            for project in projects[:8]
        ],
        "health_labels": ["Completed", "Overdue", "Remaining"],
        "health_values": [
            completed_tasks,
            len(overdue_tasks),
            max(total_tasks - completed_tasks - len(overdue_tasks), 0),
        ],
        "workload_labels": workload_labels,
        "workload_values": workload_values,
    }


@app.get("/dashboard-data")
def dashboard_data(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    return {"chart_data": get_dashboard_chart_data(db, user)}


@app.get("/")
def home(
    user: Optional[User] = Depends(get_current_user),
):
    if user:
        return redirect("/dashboard")
    return redirect("/login")


@app.get("/dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    if not user:
        return redirect("/login")

    # ADMIN users receive a global overview. MEMBER users are filtered in
    # build_dashboard_context so they only see tasks assigned to their user id.
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        build_dashboard_context(request, db, user),
    )


@app.get("/login")
def login_page(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user:
        return redirect("/dashboard")
    return templates.TemplateResponse(
        request,
        "login.html",
        {"flash": pop_flash(request)},
    )


@app.get("/register")
def register_page(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user:
        return redirect("/dashboard")
    return templates.TemplateResponse(
        request,
        "register.html",
        {"flash": pop_flash(request)},
    )


@app.get("/signup")
def signup_page():
    return redirect("/register")


@app.post("/signup")
@app.post("/register")
def signup(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    data = SignupSchema(name=name, email=email, password=password)
    if db.query(User).filter(User.email == data.email).first():
        flash(request, "An account already exists for that email.", "error")
        return redirect("/register")

    user_count = db.query(User).count()
    safe_role = "ADMIN" if user_count == 0 else "MEMBER"
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=safe_role,
    )
    db.add(user)
    db.commit()
    flash(request, "Account created. Please sign in.")
    return redirect("/login")


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    data = LoginSchema(email=email, password=password)
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        flash(request, "Invalid email or password.", "error")
        return redirect("/login")

    request.session["access_token"] = create_access_token(user.id)
    flash(request, "Welcome back.")
    return redirect("/dashboard")


# DO NOT REMOVE THIS ROUTE: dashboard logout forms depend on this exact endpoint.
@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/login")


# DO NOT REMOVE THIS ROUTE: Edit Profile modal posts to /update-profile.
@app.post("/update-profile")
@app.post("/profile")
def update_profile(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    data = ProfileSchema(name=name, email=email)
    existing_user = (
        db.query(User)
        .filter(User.email == data.email, User.id != user.id)
        .first()
    )
    if existing_user:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                {"ok": False, "message": "That email is already used by another account."},
                status_code=400,
            )
        flash(request, "That email is already used by another account.", "error")
        return redirect("/")

    user.name = data.name
    user.email = data.email
    db.commit()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse(
            {
                "ok": True,
                "message": "Profile updated.",
                "name": user.name,
                "email": user.email,
            }
        )
    flash(request, "Profile updated.")
    return redirect("/")


@app.post("/projects")
def create_project(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    data = ProjectSchema(name=name, description=description)
    db.add(Project(name=data.name, description=data.description, owner_id=user.id))
    db.commit()
    flash(request, "Project created.")
    return redirect("/")


@app.post("/projects/{project_id}/update")
def update_project(
    project_id: int,
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    data = ProjectSchema(name=name, description=description)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        flash(request, "Project not found.", "error")
        return redirect("/")

    project.name = data.name
    project.description = data.description
    db.commit()
    flash(request, "Project updated.")
    return redirect("/")


@app.post("/projects/{project_id}/delete")
def delete_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        db.delete(project)
        db.commit()
        flash(request, "Project deleted.")
    return redirect("/")


@app.post("/tasks")
def create_task(
    request: Request,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    project_id: int = Form(...),
    assignee_id: int = Form(...),
    priority: str = Form("MEDIUM"),
    due_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    normalized_priority = priority.strip().upper()
    data = TaskSchema(
        title=title,
        description=description,
        project_id=project_id,
        assignee_id=assignee_id,
        priority=normalized_priority,
        due_date=parse_due_date(due_date),
    )
    if not db.query(Project).filter(Project.id == data.project_id).first():
        flash(request, "Project not found.", "error")
        return redirect("/")
    if not db.query(User).filter(User.id == data.assignee_id).first():
        flash(request, "Assignee not found.", "error")
        return redirect("/")

    task = Task(**data.model_dump())
    db.add(task)
    db.flush()
    log_activity(
        db,
        user,
        "Task assigned",
        f"assigned {task.title} as {task.priority.title()} priority",
        task,
    )
    db.commit()
    flash(request, "Task assigned.")
    return redirect("/")


@app.post("/tasks/{task_id}/update")
def update_task(
    task_id: int,
    request: Request,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    project_id: int = Form(...),
    assignee_id: int = Form(...),
    priority: str = Form(...),
    due_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    data = TaskUpdateSchema(
        title=title,
        description=description,
        project_id=project_id,
        assignee_id=assignee_id,
        priority=priority.strip().upper(),
        due_date=parse_due_date(due_date),
    )
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        flash(request, "Task not found.", "error")
        return redirect("/")
    if not db.query(Project).filter(Project.id == data.project_id).first():
        flash(request, "Project not found.", "error")
        return redirect("/")
    if not db.query(User).filter(User.id == data.assignee_id).first():
        flash(request, "Assignee not found.", "error")
        return redirect("/")

    previous_priority = task.priority
    task.title = data.title
    task.description = data.description
    task.project_id = data.project_id
    task.assignee_id = data.assignee_id
    task.priority = data.priority
    task.due_date = data.due_date
    log_activity(
        db,
        user,
        "Task updated",
        f"updated {task.title}; priority {previous_priority.title()} to {task.priority.title()}",
        task,
    )
    db.commit()
    flash(request, "Task updated.")
    return redirect("/")


@app.post("/tasks/{task_id}/status")
def update_task_status(
    task_id: int,
    request: Request,
    task_status: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    data = StatusSchema(status=task_status)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        flash(request, "Task not found.", "error")
        return redirect("/")

    if user.role != "ADMIN" and task.assignee_id != user.id:
        flash(request, "You can only update tasks assigned to you.", "error")
        return redirect("/")

    old_status = task.status
    task.status = data.status
    log_activity(
        db,
        user,
        "Status updated",
        f"changed {task.title} from {old_status.replace('_', ' ').title()} to {task.status.replace('_', ' ').title()}",
        task,
    )
    db.commit()
    flash(request, "Task status updated.")
    return redirect("/")


@app.post("/tasks/{task_id}/delete")
def delete_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        task_title = task.title
        db.query(ActivityLog).filter(ActivityLog.task_id == task.id).update(
            {ActivityLog.task_id: None}
        )
        log_activity(
            db,
            user,
            "Task deleted",
            f"deleted {task_title}",
        )
        db.delete(task)
        db.commit()
        flash(request, "Task deleted.")
    return redirect("/")


@app.get("/health")
def health():
    return {"status": "ok"}
