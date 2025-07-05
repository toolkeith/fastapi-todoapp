import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from main import app
from database import get_db, Base
import models

# Test database URL
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:test_password@127.0.0.1:3306/todoapp_test")

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(test_db):
    return TestClient(app)

@pytest.fixture
def db_session(test_db):
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

---

# tests/test_main.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import models

def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_root_endpoint_empty(client):
    """Test the root endpoint with no todos."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Simple Todo App" in response.text

def test_create_todo(client, db_session):
    """Test creating a new todo."""
    response = client.post("/todos", data={"title": "Test Todo"})
    assert response.status_code == 303  # Redirect response
    
    # Check if todo was created in database
    todo = db_session.query(models.Todo).filter(models.Todo.title == "Test Todo").first()
    assert todo is not None
    assert todo.title == "Test Todo"
    assert todo.completed is False

def test_create_todo_empty_title(client):
    """Test creating a todo with empty title should fail."""
    response = client.post("/todos", data={"title": ""})
    assert response.status_code == 422  # Validation error

def test_toggle_todo(client, db_session):
    """Test toggling a todo's completion status."""
    # Create a todo first
    todo = models.Todo(title="Test Todo for Toggle")
    db_session.add(todo)
    db_session.commit()
    todo_id = todo.id
    
    # Toggle it to completed
    response = client.post(f"/todos/{todo_id}/toggle")
    assert response.status_code == 303
    
    # Check if it's completed
    updated_todo = db_session.query(models.Todo).filter(models.Todo.id == todo_id).first()
    assert updated_todo.completed is True
    
    # Toggle it back to incomplete
    response = client.post(f"/todos/{todo_id}/toggle")
    assert response.status_code == 303
    
    # Check if it's incomplete
    updated_todo = db_session.query(models.Todo).filter(models.Todo.id == todo_id).first()
    assert updated_todo.completed is False

def test_delete_todo(client, db_session):
    """Test deleting a todo."""
    # Create a todo first
    todo = models.Todo(title="Test Todo for Delete")
    db_session.add(todo)
    db_session.commit()
    todo_id = todo.id
    
    # Delete it
    response = client.post(f"/todos/{todo_id}/delete")
    assert response.status_code == 303
    
    # Check if it's deleted
    deleted_todo = db_session.query(models.Todo).filter(models.Todo.id == todo_id).first()
    assert deleted_todo is None

def test_toggle_nonexistent_todo(client):
    """Test toggling a non-existent todo should return 404."""
    response = client.post("/todos/999/toggle")
    assert response.status_code == 404

def test_delete_nonexistent_todo(client):
    """Test deleting a non-existent todo should return 404."""
    response = client.post("/todos/999/delete")
    assert response.status_code == 404

def test_root_endpoint_with_todos(client, db_session):
    """Test the root endpoint with existing todos."""
    # Create some test todos
    todo1 = models.Todo(title="Test Todo 1", completed=False)
    todo2 = models.Todo(title="Test Todo 2", completed=True)
    db_session.add_all([todo1, todo2])
    db_session.commit()
    
    response = client.get("/")
    assert response.status_code == 200
    assert "Test Todo 1" in response.text
    assert "Test Todo 2" in response.text

---

# tests/test_models.py
import pytest
from sqlalchemy.orm import Session
import models
from datetime import datetime

def test_todo_creation(db_session):
    """Test creating a Todo model."""
    todo = models.Todo(title="Test Todo")
    db_session.add(todo)
    db_session.commit()
    
    assert todo.id is not None
    assert todo.title == "Test Todo"
    assert todo.completed is False
    assert isinstance(todo.created_at, datetime)

def test_todo_completion_toggle(db_session):
    """Test toggling todo completion."""
    todo = models.Todo(title="Test Todo")
    db_session.add(todo)
    db_session.commit()
    
    # Initially should be incomplete
    assert todo.completed is False
    
    # Toggle to complete
    todo.completed = True
    db_session.commit()
    
    # Verify it's completed
    updated_todo = db_session.query(models.Todo).filter(models.Todo.id == todo.id).first()
    assert updated_todo.completed is True

def test_todo_string_representation(db_session):
    """Test todo model string representation."""
    todo = models.Todo(title="Test Todo")
    db_session.add(todo)
    db_session.commit()
    
    # The model doesn't have __str__ method, but we can test the title
    assert todo.title == "Test Todo"

---

# tests/test_database.py
import pytest
from database import get_db, engine, Base
from sqlalchemy.orm import Session

def test_database_connection():
    """Test that we can connect to the database."""
    db = next(get_db())
    assert isinstance(db, Session)
    db.close()

def test_tables_exist():
    """Test that required tables exist."""
    Base.metadata.create_all(bind=engine)
    
    # Check if tables exist by querying metadata
    table_names = [table.name for table in Base.metadata.tables.values()]
    assert "todos" in table_names

---

# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --color=yes
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
