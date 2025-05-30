from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class BaseModel(db.Model):
    """Base model with soft delete functionality."""
    __abstract__ = True
    active = db.Column(db.Boolean, default=True, nullable=False)

class Project(BaseModel):
    """Model for storing project information."""
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    test_suites = db.relationship('TestSuite', backref='project', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Project {self.name}>'

class TestSuite(BaseModel):
    """Model for storing test suite information."""
    __tablename__ = 'test_suite'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    test_cases = db.relationship('TestCase', backref='test_suite', lazy=True, cascade='all, delete-orphan')
    test_runs = db.relationship('TestRun', backref='test_suite', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TestSuite {self.name}>'

class TestCase(BaseModel):
    """Model for storing test case information."""
    __tablename__ = 'test_case'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='Unnamed Test')
    description = db.Column(db.Text, nullable=True)
    original_file_path = db.Column(db.String(500), nullable=False)
    test_file_path = db.Column(db.String(500), nullable=False)
    test_suite_id = db.Column(db.Integer, db.ForeignKey('test_suite.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    test_results = db.relationship('TestResult', backref='test_case', lazy=True, cascade='all, delete-orphan')
    action_steps = db.relationship('ActionStep', backref='test_case', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TestCase {self.test_file_path}>'

class TestRun(BaseModel):
    """Model for storing test run information."""
    __tablename__ = 'test_run'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    test_suite_id = db.Column(db.Integer, db.ForeignKey('test_suite.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    test_results = db.relationship('TestResult', backref='test_run', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TestRun {self.name}>'

# Update TestResult to inherit from BaseModel
class TestResult(BaseModel):
    """Model for storing test result information."""
    __tablename__ = 'test_result'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False)
    execution_time = db.Column(db.Float, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    test_case_id = db.Column(db.Integer, db.ForeignKey('test_case.id'), nullable=False)
    test_run_id = db.Column(db.Integer, db.ForeignKey('test_run.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TestResult {self.status} for TestCase {self.test_case_id}>'

class ActionStep(BaseModel):
    """Model for storing test case steps."""
    __tablename__ = 'action_step'
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), nullable=False)  # click, fill, navigate, etc.
    selector = db.Column(db.String(500), nullable=True)  # CSS selector for the element
    value = db.Column(db.Text, nullable=True)  # Value for input fields
    order = db.Column(db.Integer, nullable=False)  # Order of execution
    description = db.Column(db.Text, nullable=True)  # Human-readable description
    test_case_id = db.Column(db.Integer, db.ForeignKey('test_case.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ActionStep {self.action} on {self.selector}>'