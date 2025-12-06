import pytest
from sqlalchemy.exc import SQLAlchemyError
from services import project_service
from services.models import Project
from services.db import db

# --- Tests for create_project() ---

def test_create_project_success(app, make_user):
    """
    GIVEN a valid user ID, project name, and description
    WHEN the create_project function is called
    THEN a new Project object should be created and returned
    """
    with app.app_context():
        user = make_user()
        
        project = project_service.create_project(
            user_id=user.user_id,
            name="My First Project",
            description="A test description.",
            assigned_bpo_id=user.user_id
        )

        assert project is not None
        assert project.project_name == "My First Project"
        assert project.user_id == user.user_id
        assert project.assigned_bpo_id == user.user_id

        db_project = db.session.get(Project, project.project_id)
        assert db_project is not None


def test_create_project_duplicate_name_fails(app, make_user):
    """
    GIVEN a user who already has a project with a certain name
    WHEN create_project is called with the same name for the same user
    THEN a ValueError should be raised
    """
    with app.app_context():
        user = make_user()
        project_service.create_project(user.user_id, "Duplicate Project", "", assigned_bpo_id=user.user_id)

        with pytest.raises(ValueError, match="A project named 'Duplicate Project' already exists."):
            project_service.create_project(user.user_id, "Duplicate Project", "", assigned_bpo_id=user.user_id)


def test_create_project_empty_name_fails(app, make_user):
    """
    GIVEN a user ID
    WHEN create_project is called with an empty name
    THEN a ValueError should be raised
    """
    with app.app_context():
        user = make_user()
        with pytest.raises(ValueError, match="Project name cannot be empty."):
            project_service.create_project(user.user_id, "", "Should fail.", assigned_bpo_id=user.user_id)


# --- Tests for get_projects_by_user() ---

def test_get_projects_by_user_success(app, make_user):
    """
    GIVEN a user who has created multiple projects
    WHEN get_projects_by_user is called
    THEN a list of their projects should be returned, ordered by most recent first
    """
    with app.app_context():
        # create main user and a separate BPO user
        user = make_user(email="owner@test.com")
        bpo = make_user(email="bpo@test.com")

        # create projects assigned to bpo
        project1 = project_service.create_project(
            user.user_id, "Old Project", "", assigned_bpo_id=bpo.user_id
        )
        project2 = project_service.create_project(
            user.user_id, "New Project", "", assigned_bpo_id=bpo.user_id
        )

        # get projects
        projects = project_service.get_projects_by_user(user.user_id)

        assert len(projects) == 2
        assert projects[0]["project_name"] == "Old Project"
        assert projects[1]["project_name"] == "New Project"


def test_get_projects_by_user_is_isolated(app, make_user):
    """
    GIVEN two users with their own projects
    WHEN get_projects_by_user is called for one user
    THEN it should only return projects for that specific user
    """
    with app.app_context():
        user1 = make_user(email="user1@test.com")
        user2 = make_user(email="user2@test.com")
        
        project_service.create_project(user1.user_id, "User1 Project", "", assigned_bpo_id=user1.user_id)
        project_service.create_project(user2.user_id, "User2 Project", "", assigned_bpo_id=user2.user_id)

        user1_projects = project_service.get_projects_by_user(user1.user_id)

        assert len(user1_projects) == 1
        assert user1_projects[0]["project_name"] == "User1 Project"


def test_get_projects_by_user_empty(app, make_user):
    """
    GIVEN a user with no projects
    WHEN get_projects_by_user is called
    THEN an empty list should be returned
    """
    with app.app_context():
        user = make_user()
        projects = project_service.get_projects_by_user(user.user_id)
        assert projects == []


# --- Tests for get_project_by_id() ---

def test_get_project_by_id_success(app, make_user):
    """
    GIVEN a project that exists and belongs to a user
    WHEN get_project_by_id is called with the correct IDs
    THEN the Project object should be returned
    """
    with app.app_context():
        user = make_user()
        project = project_service.create_project(user.user_id, "My Project", "", assigned_bpo_id=user.user_id)

        found_project = project_service.get_project_by_id(project.project_id, user.user_id)

        assert found_project is not None
        assert found_project.project_id == project.project_id


def test_get_project_by_id_wrong_user_returns_none(app, make_user):
    """
    GIVEN a project that belongs to user1
    WHEN get_project_by_id is called with that project's ID but with user2's ID
    THEN None should be returned
    """
    with app.app_context():
        user1 = make_user(email="owner@test.com")
        user2 = make_user(email="other@test.com")
        project = project_service.create_project(user1.user_id, "Private Project", "", assigned_bpo_id=user1.user_id)
        
        found_project = project_service.get_project_by_id(project.project_id, user2.user_id)
        assert found_project is None


def test_get_project_by_id_not_found_returns_none(app, make_user):
    """
    GIVEN a user
    WHEN get_project_by_id is called with a non-existent project ID
    THEN None should be returned
    """
    with app.app_context():
        user = make_user()
        found_project = project_service.get_project_by_id(9999, user.user_id)
        assert found_project is None


# --- Tests for update_project_info() ---

def test_update_project_info_success(app, make_user):
    """
    GIVEN an existing project
    WHEN update_project_info is called with new name and description
    THEN the project should be updated and returned
    """
    with app.app_context():
        user = make_user()
        project = project_service.create_project(user.user_id, "Old Name", "Old Description", assigned_bpo_id=user.user_id)

        updated = project_service.update_project_info(project.project_id, "New Name", "New Description")

        assert updated.project_name == "New Name"
        assert updated.description == "New Description"

        db_project = db.session.get(Project, project.project_id)
        assert db_project.project_name == "New Name"


def test_update_project_info_not_found_raises(app):
    """
    GIVEN a non-existent project ID
    WHEN update_project_info is called
    THEN a ValueError should be raised
    """
    with app.app_context():
        with pytest.raises(ValueError, match="Project with id 9999 not found"):
            project_service.update_project_info(9999, "Does Not Exist", "No description")


def test_update_project_info_db_error_rolls_back(app, make_user, monkeypatch):
    """
    GIVEN a valid project
    WHEN a SQLAlchemyError occurs during commit
    THEN it should raise RuntimeError and rollback changes
    """
    with app.app_context():
        user = make_user()
        project = project_service.create_project(user.user_id, "Test Project", "Desc", assigned_bpo_id=user.user_id)

        def mock_commit():
            raise SQLAlchemyError("Forced DB failure")

        monkeypatch.setattr(db.session, "commit", mock_commit)

        with pytest.raises(RuntimeError, match="Database error while updating project"):
            project_service.update_project_info(project.project_id, "Fail Name", "Fail Desc")

        db_project = db.session.get(Project, project.project_id)
        assert db_project.project_name == "Test Project"


# --- Tests for delete_project() ---

def test_delete_project_success(app, make_user):
    """
    GIVEN an existing project
    WHEN delete_project is called
    THEN the project should be deleted from the database
    """
    with app.app_context():
        user = make_user()
        project = project_service.create_project(user.user_id, "Delete Me", "", assigned_bpo_id=user.user_id)

        response = project_service.delete_project(project.project_id)
        assert "deleted successfully" in response["message"]

        db_project = db.session.get(Project, project.project_id)
        assert db_project is None


def test_delete_project_not_found_raises(app):
    """
    GIVEN a non-existent project ID
    WHEN delete_project is called
    THEN a ValueError should be raised
    """
    with app.app_context():
        with pytest.raises(ValueError, match="Project with id 9999 not found"):
            project_service.delete_project(9999)


def test_delete_project_db_error_rolls_back(app, make_user, monkeypatch):
    """
    GIVEN a valid project
    WHEN a SQLAlchemyError occurs during delete
    THEN a RuntimeError should be raised and transaction rolled back
    """
    with app.app_context():
        user = make_user()
        project = project_service.create_project(user.user_id, "DB Error Project", "", assigned_bpo_id=user.user_id)

        def mock_commit():
            raise SQLAlchemyError("Forced delete error")

        monkeypatch.setattr(db.session, "commit", mock_commit)

        with pytest.raises(RuntimeError, match="Database error while deleting project"):
            project_service.delete_project(project.project_id)

        db_project = db.session.get(Project, project.project_id)
        assert db_project is not None
