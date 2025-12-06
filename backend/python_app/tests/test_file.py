# tests/test_file.py
import pytest
from services.models import User, File, Project
from services.db import db
import routes.file as file_module # Import your file module

# --- Tests for store_file() and is_file_duplicate() ---
def test_store_file_success(app, make_user, make_project):
    """
    GIVEN a user and new file data
    WHEN the store_file function is called
    THEN check that a new file is created in the database with correct attributes
    """
    # Arrange: Create a user and some sample file data
    with app.app_context():
        user = make_user(email="fileuser@example.com")
        project = make_project(user)
        test_filename = "test.txt"
        test_file_data = b"hello world" # 'b' prefix creates a bytes object

        # Act: Call the function to store the file
        result = file_module.store_file(user.user_id, project.project_id, test_file_data, test_filename)

        # Assert: Check the results
        assert "stored successfully" in result
        
        # Verify the file was actually saved to the DB
        stored_file = File.query.filter_by(user_id=user.user_id).first()
        assert stored_file is not None
        assert stored_file.filename == test_filename
        assert stored_file.status == 0 # Should be "uploaded"

def test_store_duplicate_file_in_same_project(app, make_user, make_project):
    """Checks that a duplicate file is NOT stored in the SAME project."""
    with app.app_context():
        user = make_user(email="dupe@example.com")
        project = make_project(user)
        file_data = b"some unique content"
        
        # Arrange: Store the file once
        file_module.store_file(user.user_id, project.project_id, file_data, "original.csv")

        # Act: Try to store the exact same file in the same project
        result = file_module.store_file(user.user_id, project.project_id, file_data, "duplicate.csv")

        # Assert
        assert "already exists" in result
        
        # Verify there is still only one file in this project
        file_count = File.query.filter_by(project_id=project.project_id).count()
        assert file_count == 1
        assert file_count == 1

def test_duplicate_file_in_different_project_is_not_a_duplicate(app, make_user, make_project):
    """Checks that a duplicate file IS stored if it's in a DIFFERENT project."""
    with app.app_context():
        user = make_user(email="multi-project@example.com")
        project1 = make_project(user, project_name="Project Alpha")
        project2 = make_project(user, project_name="Project Beta")
        file_data = b"cross-project content"
        
        # Arrange: Store the file in the first project
        file_module.store_file(user.user_id, project1.project_id, file_data, "report.csv")

        # Act: Store the exact same file in the second project
        result = file_module.store_file(user.user_id, project2.project_id, file_data, "report.csv")

        # Assert
        assert "stored successfully" in result
        
        # Verify there are now two file records for this user, one for each project
        user_file_count = File.query.filter_by(user_id=user.user_id).count()
        assert user_file_count == 2

def test_duplicate_hash_for_different_user_is_not_a_duplicate(app, make_user, make_project):
    """Checks that different users can store files with the same content."""
    with app.app_context():
        user1 = make_user(email="user1@example.com")
        project1 = make_project(user1)
        
        user2 = make_user(email="user2@example.com")
        project2 = make_project(user2) # Each user has their own project
        
        file_data = b"shared content"
        
        # Arrange: User 1 stores the file
        file_module.store_file(user1.user_id, project1.project_id, file_data, "file.txt")

        # Act: User 2 stores the same file in their own project
        result = file_module.store_file(user2.user_id, project2.project_id, file_data, "file.txt")

        # Assert
        assert "stored successfully" in result
        
        # Verify there are now two separate file records in the database
        total_files = File.query.count()
        assert total_files == 2

# --- Tests for get_file_info_by_user() ---

def test_get_file_info_for_user_with_files(app, make_user, make_project):
    """
    GIVEN a user who has stored multiple files
    WHEN get_file_info_by_user is called
    THEN check that a list of dictionaries with correct file metadata is returned
    """
    # Arrange: Create a user and add two files
    with app.app_context():
        user = make_user()
        project = make_project(user) 
        file_module.store_file(user.user_id, project.project_id, b"data1", "report.csv")
        file_module.store_file(user.user_id, project.project_id, b"data2", "image.jpg")

        # Act: Get the file info
        file_list = file_module.get_file_info_by_user(user.user_id)

        # Assert: Check the structure and content of the returned list
        assert isinstance(file_list, list)
        assert len(file_list) == 2
        
        # Check the first file's details
        csv_file = next(f for f in file_list if f["filename"] == "report.csv")
        assert csv_file["file_type"] == "csv"
        assert csv_file["size_bytes"] == 5
        assert csv_file["status"] == 0

def test_get_file_info_for_user_with_no_files(app, make_user):
    """
    GIVEN a user who has not stored any files
    WHEN get_file_info_by_user is called
    THEN check that an empty list is returned
    """
    # Arrange: Create a user but do not add any files for them
    with app.app_context():
        user_with_no_files = make_user(email="nofiles@example.com")

        # Act: Get the file info
        file_list = file_module.get_file_info_by_user(user_with_no_files.user_id)

        # Assert: Check that the list is empty
        assert file_list == []

# --- Tests for store_file() and is_file_duplicate() ---
def test_get_file_by_project(app, make_user, make_project):
    """
    GIVEN multiple projects with different files
    WHEN get_file_by_project is called for a specific project
    THEN check that it returns only the files for that project
    """
    with app.app_context():
        # Arrange
        user = make_user()
        project1 = make_project(user, project_name="Project Alpha")
        project2 = make_project(user, project_name="Project Beta")

        # Add one file to Project 1
        file_module.store_file(user.user_id, project1.project_id, b"alpha_data", "alpha.csv")

        # Add two files to Project 2
        file_module.store_file(user.user_id, project2.project_id, b"beta_data_1", "beta1.csv")
        file_module.store_file(user.user_id, project2.project_id, b"beta_data_2", "beta2.csv")

        # Act: Call the function for Project 2
        project2_files = file_module.get_file_by_project(project2.project_id)

        # Assert
        assert isinstance(project2_files, list)
        # Check that it returned exactly the 2 files from Project 2
        assert len(project2_files) == 2 

        # Verify the filenames to be certain
        filenames = {f.filename for f in project2_files}
        assert "beta1.csv" in filenames
        assert "beta2.csv" in filenames
        assert "alpha.csv" not in filenames