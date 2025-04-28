from app import app, db
from models import Project, TestSuite, TestCase, TestRun, TestResult

def create_sample_data():
    with app.app_context():
        # Create a sample project
        project = Project(
            name="Demo Project",
            path="/demo/path",
            description="This is a demo project"
        )
        db.session.add(project)
        db.session.commit()
        print(f"Created project: {project.name} (ID: {project.id})")
        return project

def toggle_project_status(project_id):
    with app.app_context():
        project = Project.query.get(project_id)
        if project:
            project.active = not project.active
            db.session.commit()
            print(f"Project '{project.name}' is now {'active' if project.active else 'inactive'}")
        else:
            print(f"Project with ID {project_id} not found")

def show_active_projects():
    with app.app_context():
        active_projects = Project.query.filter_by(active=True).all()
        print("\nActive Projects:")
        for project in active_projects:
            print(f"- {project.name} (ID: {project.id})")

def show_inactive_projects():
    with app.app_context():
        inactive_projects = Project.query.filter_by(active=False).all()
        print("\nInactive Projects:")
        for project in inactive_projects:
            print(f"- {project.name} (ID: {project.id})")

if __name__ == "__main__":
    # Create a sample project
    project = create_sample_data()
    
    # Show active projects
    show_active_projects()
    
    # Make the project inactive
    toggle_project_status(project.id)
    
    # Show both active and inactive projects
    show_active_projects()
    show_inactive_projects()
    
    # Make the project active again
    toggle_project_status(project.id)
    
    # Show final state
    show_active_projects()
    show_inactive_projects() 