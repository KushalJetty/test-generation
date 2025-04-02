from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FileField, BooleanField, DateField, IntegerField
from wtforms.validators import DataRequired, Optional, Length

class ProjectForm(FlaskForm):
    """Form for creating and editing projects."""
    name = StringField('Project Name', validators=[DataRequired(), Length(max=100)])
    path = StringField('Project Path', validators=[DataRequired(), Length(max=500)])
    description = TextAreaField('Description', validators=[Optional()])

class TestSuiteForm(FlaskForm):
    """Form for creating and editing test suites."""
    name = StringField('Test Suite Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    project_id = SelectField('Project', coerce=int, validators=[DataRequired()])
    ignore_patterns = TextAreaField('Ignore Patterns (one per line)', validators=[Optional()], description='Files or directories to ignore when generating test cases')

class TestRunForm(FlaskForm):
    """Form for creating and running test runs."""
    name = StringField('Test Run Name', validators=[DataRequired(), Length(max=100)])
    test_suite_id = SelectField('Test Suite', coerce=int, validators=[DataRequired()])

class FilterForm(FlaskForm):
    """Form for filtering test results."""
    status = SelectField('Status', choices=[
        ('', 'All'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
        ('error', 'Error')
    ], validators=[Optional()])
    date_from = DateField('From Date', validators=[Optional()], format='%Y-%m-%d')
    date_to = DateField('To Date', validators=[Optional()], format='%Y-%m-%d')
    project = SelectField('Project', coerce=int, validators=[Optional()])
    test_suite_id = SelectField('Test Suite', coerce=int, validators=[Optional()])

class ExportForm(FlaskForm):
    """Form for exporting test results."""
    format = SelectField('Export Format', choices=[
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('excel', 'Excel')
    ], validators=[DataRequired()])
    include_details = BooleanField('Include Details', default=True)
    test_run_id = SelectField('Test Run', coerce=int, validators=[Optional()])
    test_suite_id = SelectField('Test Suite', coerce=int, validators=[Optional()])