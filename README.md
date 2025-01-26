Health Check

Request:
curl http://127.0.0.1:8000/health

Response:
    {
  "message": "Instance is healthy"
   }

Add Todo:

Request:
curl -X 'POST' \
  'http://127.0.0.1:8000/todos' \
  -H 'Content-Type: application/json' \
  -d '{"task": "Buy milk"}'

Response:
{
  "message": "Task added successfully"
}

GetTodos:

Request:
curl http://127.0.0.1:8000/todos

Response:
[
  {"task": "Buy milk"}
]
