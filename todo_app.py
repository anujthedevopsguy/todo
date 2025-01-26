
import mysql.connector
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from mysql.connector import Error
from typing import List

# FastAPI instance
app = FastAPI()

# Define the MySQL connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOSTNAME"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database="todo_db",  # Ensure the database exists
            port=int(os.getenv("MYSQL_PORT", 3306))
        )
        return connection
    except Error as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")

# Define Todo model
class Todo(BaseModel):
    task: str

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"message": "Instance is healthy"}

# Add a Todo item to the database
@app.post("/todos")
async def add_todo(todo: Todo):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Insert the todo item into the database
        cursor.execute("INSERT INTO todos (task) VALUES (%s)", (todo.task,))
        connection.commit()
        return {"message": "Task added successfully"}
    except Error as e:
        connection.rollback()
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
        return [{"task": task[0]} for task in tasks]
    except Error as e:
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")
    finally:
        cursor.close()
        connection.close()

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")