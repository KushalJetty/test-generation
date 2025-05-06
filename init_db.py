from app import app, db
from models import TestCase, TestSuite, Project, TestRun, TestResult

with app.app_context():
    # Create all tables
    db.create_all()
    print("Database tables created successfully!") 