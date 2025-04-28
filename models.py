from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Project(db.Model):
    """Model for storing project information."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=True, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    test_suites = db.relationship('TestSuite', backref='project', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Project {self.name}>' 

class TestSuite(db.Model):
    """Model for storing test suite information."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    is_active = db.Column(db.Boolean, nullable=True, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    test_cases = db.relationship('TestCase', backref='test_suite', lazy=True, cascade='all, delete-orphan')
    test_runs = db.relationship('TestRun', backref='test_suite', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TestSuite {self.name}>'

class TestCase(db.Model):
    """Model for storing test case information."""
    id = db.Column(db.Integer, primary_key=True)
    original_file_path = db.Column(db.String(500), nullable=False)
    test_file_path = db.Column(db.String(500), nullable=False)
    language = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='generated')  # generated, passed, failed
    test_suite_id = db.Column(db.Integer, db.ForeignKey('test_suite.id'), nullable=False)
    is_active = db.Column(db.Boolean, nullable=True, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    test_results = db.relationship('TestResult', backref='test_case', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TestCase {self.test_file_path}>'

class TestRun(db.Model):
    """Model for storing test run information."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, running, completed, failed
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    test_suite_id = db.Column(db.Integer, db.ForeignKey('test_suite.id'), nullable=False)
    is_active = db.Column(db.Boolean, nullable=True, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    test_results = db.relationship('TestResult', backref='test_run', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TestRun {self.name}>'

class TestResult(db.Model):
    """Model for storing test result information."""
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False)  # passed, failed, skipped, error
    execution_time = db.Column(db.Float, nullable=True)  # in seconds
    error_message = db.Column(db.Text, nullable=True)
    test_case_id = db.Column(db.Integer, db.ForeignKey('test_case.id'), nullable=False)
    test_run_id = db.Column(db.Integer, db.ForeignKey('test_run.id'), nullable=False)
    is_active = db.Column(db.Boolean, nullable=True, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<TestResult {self.status} for TestCase {self.test_case_id}>'