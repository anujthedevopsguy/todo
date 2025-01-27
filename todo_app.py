import pymysql
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from prometheus_client import Counter, generate_latest, CollectorRegistry
import os
from typing import List

# FastAPI instance
app = FastAPI()

# Prometheus metrics registry and counters
registry = CollectorRegistry()
todo_requests_total = Counter(
    "todo_requests_total",
    "Total number of requests to the Todo app",
    ["method", "endpoint", "status"],
    registry=registry,
)
tasks_created = Counter(
    "tasks_created_total",
    "Total number of tasks created",
    registry=registry,
)

# Serve static files (CSS, JS, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Define Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# Define the MySQL connection
def get_db_connection():
    try:
        connection = pymysql.connect(
            host=os.getenv("MYSQL_HOSTNAME").strip(),
            user=os.getenv("MYSQL_USER").strip(),
            password=os.getenv("MYSQL_PASSWORD").strip(),
            database=os.getenv("MYSQL_DATABASE").strip(),
            port=int(os.getenv("MYSQL_PORT", 3306))
        )
        return connection
    except pymysql.MySQLError as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")

# Define Todo model
class Todo(BaseModel):
    task: str

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "The application is running"}

# Add a Todo item to the database
@app.post("/todos")
async def add_todo(todo: Todo):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("INSERT INTO todos (task) VALUES (%s)", (todo.task,))
        connection.commit()
        tasks_created.inc()  # Increment the tasks_created counter
        todo_requests_total.labels(method="POST", endpoint="/todos", status="200").inc()
        return {"message": "Task added successfully"}
    except pymysql.MySQLError as e:
        connection.rollback()
        todo_requests_total.labels(method="POST", endpoint="/todos", status="500").inc()
        raise HTTPException(status_code=500, detail="Failed to add task")
    finally:
        cursor.close()
        connection.close()

# Retrieve all Todo items from the database
@app.get("/todos", response_model=List[Todo])
async def get_todos():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT task FROM todos")
        tasks = cursor.fetchall()
        todo_requests_total.labels(method="GET", endpoint="/todos", status="200").inc()
        return [{"task": task[0]} for task in tasks]
    except pymysql.MySQLError as e:
        todo_requests_total.labels(method="GET", endpoint="/todos", status="500").inc()
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")
    finally:
        cursor.close()
        connection.close()

# Metrics endpoint for Prometheus
@app.get("/metrics")
def metrics():
    return Response(generate_latest(registry), media_type="text/plain")

# Web page to show and add tasks
@app.get("/", response_class=HTMLResponse)
async def show_tasks(request: Request):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT task FROM todos")
        tasks = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception:
        tasks = []

    return templates.TemplateResponse("index.html", {"request": request, "tasks": [{"task": t[0]} for t in tasks]})

@app.post("/add-task", response_class=HTMLResponse)
async def add_task(request: Request, task: str = Form(...)):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO todos (task) VALUES (%s)", (task,))
        connection.commit()
        tasks_created.inc()
        cursor.close()
        connection.close()
    except Exception as e:
        return templates.TemplateResponse("error.html", {"request": request, "message": str(e)})

    return await show_tasks(request)