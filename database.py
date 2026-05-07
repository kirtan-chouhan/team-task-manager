import os
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "mysql+mysqlconnector://root:root@localhost:3306/team_task_manager")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+mysqlconnector://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("ADMIN", "MEMBER", name="user_roles"), default="MEMBER")
    created_at = Column(DateTime, default=datetime.utcnow)

    assigned_tasks = relationship("Task", back_populates="assignee")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")
    tasks = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(220), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum("TO_DO", "DOING", "DONE", name="task_statuses"),
        default="TO_DO",
        nullable=False,
    )
    priority = Column(
        Enum("HIGH", "MEDIUM", "LOW", name="task_priorities"),
        default="MEDIUM",
        nullable=False,
    )
    due_date = Column(DateTime, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(120), nullable=False)
    detail = Column(Text, nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    actor = relationship("User")
    task = relationship("Task")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema()


def ensure_schema() -> None:
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    task_columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "priority" not in task_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE tasks ADD COLUMN priority VARCHAR(6) DEFAULT 'MEDIUM' NOT NULL")
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
