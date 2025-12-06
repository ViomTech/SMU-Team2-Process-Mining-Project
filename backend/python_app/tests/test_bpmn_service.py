import pytest
import math
from unittest.mock import Mock, PropertyMock, patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
import hashlib

# Import the module to test (assuming it's named bpmn_service.py)
from services import bpmn_service
from services.models import BpmnFile, User, BpmnFileAudit, Project
from services.db import db


# Add mock functions to the bpmn_service module for testing
bpmn_service.log_audit_event = Mock()
bpmn_service.create_notification = Mock()


class TestSaveBpmn:
    """Test cases for save_bpmn function"""

    def test_save_bpmn_success_new_file(self, app):
        """Test saving a new BPMN file successfully"""
        with app.app_context():
            # Mock dependencies
            mock_user_id = 1
            mock_project_id = 1
            mock_name = "test.bpmn"
            mock_description = "Test description"
            mock_xml = "<bpmn>test</bpmn>"
            
            with patch('services.bpmn_service.db') as mock_db, \
                 patch('services.bpmn_service.BpmnFile') as mock_bpmn_file, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_query:
                
                # Setup mocks
                mock_last_bpmn = None
                mock_filter_by = Mock()
                mock_order_by = Mock()
                mock_order_by.first.return_value = mock_last_bpmn
                mock_filter_by.order_by.return_value = mock_order_by
                mock_query.filter_by.return_value = mock_filter_by
                
                mock_new_bpmn = Mock()
                mock_bpmn_file.return_value = mock_new_bpmn
                
                # Call function
                result = bpmn_service.save_bpmn(mock_user_id, mock_project_id, mock_name, mock_description, mock_xml)
                
                # Assertions
                assert result == mock_new_bpmn
                mock_bpmn_file.assert_called_once()
                mock_db.session.add.assert_called_once_with(mock_new_bpmn)
                mock_db.session.commit.assert_called_once()

    def test_save_bpmn_missing_required_fields(self, app):
        """Test saving BPMN with missing required fields"""
        with app.app_context():
            with pytest.raises(ValueError, match="Missing filename or BPMN XML"):
                bpmn_service.save_bpmn(1, 1, "", "description", "<bpmn>test</bpmn>")
            
            with pytest.raises(ValueError, match="Missing filename or BPMN XML"):
                bpmn_service.save_bpmn(1, 1, "test.bpmn", "description", "")

    def test_save_bpmn_database_error(self, app):
        """Test database error during save"""
        with app.app_context():
            with patch('services.bpmn_service.db') as mock_db, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_query:
                
                # Setup mocks to raise database error
                mock_filter_by = Mock()
                mock_order_by = Mock()
                mock_order_by.first.return_value = None
                mock_filter_by.order_by.return_value = mock_order_by
                mock_query.filter_by.return_value = mock_filter_by
                
                mock_db.session.commit.side_effect = SQLAlchemyError("DB error")
                
                # Call function and assert
                with pytest.raises(RuntimeError, match="Database error while saving BPMN"):
                    bpmn_service.save_bpmn(1, 1, "test.bpmn", "desc", "<bpmn>test</bpmn>")
                
                mock_db.session.rollback.assert_called_once()


class TestSaveBpmnEdits:
    """Test cases for save_bpmn_edits function"""

    def test_save_bpmn_edits_success_with_changes(self, app):
        """Test saving edits when XML has changed"""
        with app.app_context():
            with patch('services.bpmn_service.db') as mock_db, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_query, \
                 patch('services.bpmn_service.BpmnFileAudit') as mock_audit:
                
                # Setup mocks with proper attributes
                mock_bpmn_file = Mock()
                mock_bpmn_file.file_hash = "old_hash"
                mock_bpmn_file.bpmnfile_id = 1
                mock_bpmn_file.user_id = 1
                mock_bpmn_file.file_data = b"old_data"
                mock_bpmn_file.version = 1.0  # Make sure this is a float
                mock_bpmn_file.approval_status = "approved"
                
                mock_query.get.return_value = mock_bpmn_file
                
                mock_audit_entry = Mock()
                mock_audit.return_value = mock_audit_entry
                
                # Call function with different XML
                new_xml = "<bpmn>new_content</bpmn>"
                result = bpmn_service.save_bpmn_edits(1, new_xml, 1)
                
                # Assertions
                assert result == mock_bpmn_file
                mock_audit.assert_called_once()
                mock_db.session.add.assert_called_once_with(mock_audit_entry)
                mock_db.session.commit.assert_called_once()
                # Version should be incremented by 0.1
                assert mock_bpmn_file.version == 1.1
                assert mock_bpmn_file.approval_status is None

    def test_save_bpmn_edits_no_changes(self, app):
        """Test saving edits when XML hasn't changed"""
        with app.app_context():
            with patch('services.bpmn_service.db') as mock_db, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_query:
                
                # Setup mocks
                mock_bpmn_file = Mock()
                xml_content = "<bpmn>test</bpmn>"
                xml_bytes = xml_content.encode('utf-8')
                file_hash = hashlib.sha256(xml_bytes).hexdigest()
                
                mock_bpmn_file.file_hash = file_hash
                mock_bpmn_file.version = 1.0  # Make sure this is a float
                mock_query.get.return_value = mock_bpmn_file
                
                # Call function with same XML
                result = bpmn_service.save_bpmn_edits(1, xml_content, 1)
                
                # Assertions - no audit entry should be created
                assert result == mock_bpmn_file
                mock_db.session.add.assert_not_called()
                mock_db.session.commit.assert_called_once()

    def test_save_bpmn_edits_bpmn_not_found(self, app):
        """Test saving edits for non-existent BPMN"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                mock_query.get.return_value = None
                
                with pytest.raises(ValueError, match="BPMN with id 999 not found"):
                    bpmn_service.save_bpmn_edits(999, "<bpmn>test</bpmn>", 1)

    def test_save_bpmn_edits_database_error(self, app):
        """Test database error during edit save"""
        with app.app_context():
            with patch('services.bpmn_service.db') as mock_db, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_query:
                
                # Setup mock with proper float version
                mock_bpmn_file = Mock()
                mock_bpmn_file.file_hash = "old_hash"
                mock_bpmn_file.version = 1.0  # This must be a float for the += operation
                mock_bpmn_file.bpmnfile_id = 1
                mock_bpmn_file.user_id = 1
                mock_bpmn_file.file_data = b"old_data"
                mock_bpmn_file.approval_status = "approved"
                mock_query.get.return_value = mock_bpmn_file
                
                mock_db.session.commit.side_effect = SQLAlchemyError("DB error")
                
                with pytest.raises(RuntimeError, match="Database error while saving BPMN edits"):
                    bpmn_service.save_bpmn_edits(1, "<bpmn>new</bpmn>", 1)
                
                mock_db.session.rollback.assert_called_once()


class TestGetBpmn:
    """Test cases for get_bpmn function"""

    def test_get_bpmn_success(self, app):
        """Test successfully retrieving a BPMN file"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                # Setup mocks
                mock_bpmn = Mock()
                mock_join = Mock()
                mock_filter = Mock()
                mock_filter.first.return_value = mock_bpmn
                mock_join.filter.return_value = mock_filter
                mock_query.join.return_value = mock_join
                
                # Call function
                result = bpmn_service.get_bpmn(1, 1)
                
                # Assertions
                assert result == mock_bpmn
                mock_query.join.assert_called_once_with(Project)

    def test_get_bpmn_database_error(self, app):
        """Test database error during BPMN retrieval"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                mock_join = Mock()
                mock_filter = Mock()
                mock_filter.first.side_effect = SQLAlchemyError("DB error")
                mock_join.filter.return_value = mock_filter
                mock_query.join.return_value = mock_join
                
                with pytest.raises(RuntimeError, match="Database error while fetching BPMN"):
                    bpmn_service.get_bpmn(1, 1)


class TestGetRecentBpmn:
    """Test cases for get_recent_bpmn function"""

    def test_get_recent_bpmn_success(self, app):
        """Test successfully retrieving recent BPMN files"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                # Setup mocks
                mock_bpmn_list = [Mock(), Mock()]
                mock_join = Mock()
                mock_filter = Mock()
                mock_order_by = Mock()
                mock_limit = Mock()
                
                mock_limit.all.return_value = mock_bpmn_list
                mock_order_by.limit.return_value = mock_limit
                mock_filter.order_by.return_value = mock_order_by
                mock_join.filter.return_value = mock_filter
                mock_query.join.return_value = mock_join
                
                # Call function
                result = bpmn_service.get_recent_bpmn(1)
                
                # Assertions
                assert result == mock_bpmn_list
                mock_query.join.assert_called_once_with(Project)

    def test_get_recent_bpmn_database_error(self, app):
        """Test database error during recent BPMN retrieval"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                mock_join = Mock()
                mock_filter = Mock()
                mock_filter.order_by.side_effect = SQLAlchemyError("DB error")
                mock_join.filter.return_value = mock_filter
                mock_query.join.return_value = mock_join
                
                with pytest.raises(RuntimeError, match="Database error while fetching recent BPMNs"):
                    bpmn_service.get_recent_bpmn(1)


class TestGetAllBpmn:
    """Test cases for get_all_bpmn function"""

    def test_get_all_bpmn_success(self, app):
        """Test successfully retrieving all BPMN files"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                # Setup mocks
                mock_bpmn_list = [Mock(), Mock(), Mock()]
                mock_join = Mock()
                mock_filter = Mock()
                mock_order_by = Mock()
                
                mock_order_by.all.return_value = mock_bpmn_list
                mock_filter.order_by.return_value = mock_order_by
                mock_join.filter.return_value = mock_filter
                mock_query.join.return_value = mock_join
                
                # Call function
                result = bpmn_service.get_all_bpmn(1)
                
                # Assertions
                assert result == mock_bpmn_list

    def test_get_all_bpmn_database_error(self, app):
        """Test database error during all BPMN retrieval"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                mock_join = Mock()
                mock_filter = Mock()
                mock_filter.order_by.side_effect = SQLAlchemyError("DB error")
                mock_join.filter.return_value = mock_filter
                mock_query.join.return_value = mock_join
                
                with pytest.raises(RuntimeError, match="Database error while fetching all BPMNs"):
                    bpmn_service.get_all_bpmn(1)


class TestGetBpmnByProject:
    """Test cases for get_bpmn_by_project function"""

    def test_get_bpmn_by_project_success(self, app):
        """Test successfully retrieving BPMN files by project"""
        with app.app_context():
            with patch('services.bpmn_service.Project.query') as mock_project_query, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query:
                
                # Setup mocks
                mock_project = Mock()
                mock_project_query.filter.return_value.first.return_value = mock_project
                
                mock_bpmn_list = [Mock(), Mock()]
                mock_bpmn_filter = Mock()
                mock_order_by = Mock()
                mock_order_by.all.return_value = mock_bpmn_list
                mock_bpmn_filter.order_by.return_value = mock_order_by
                mock_bpmn_query.filter_by.return_value = mock_bpmn_filter
                
                # Call function
                result = bpmn_service.get_bpmn_by_project(1, 1)
                
                # Assertions
                assert result == mock_bpmn_list

    def test_get_bpmn_by_project_no_access(self, app):
        """Test retrieving BPMN files for project with no access"""
        with app.app_context():
            with patch('services.bpmn_service.Project.query') as mock_project_query:
                mock_project_query.filter.return_value.first.return_value = None
                
                result = bpmn_service.get_bpmn_by_project(1, 1)
                
                assert result == []

    def test_get_bpmn_by_project_database_error(self, app):
        """Test database error during project BPMN retrieval"""
        with app.app_context():
            with patch('services.bpmn_service.Project.query') as mock_project_query:
                mock_project_query.filter.return_value.first.side_effect = SQLAlchemyError("DB error")
                
                with pytest.raises(RuntimeError, match="Database error while fetching project BPMNs"):
                    bpmn_service.get_bpmn_by_project(1, 1)


class TestUpdateBpmn:
    """Test cases for update_bpmn function"""

    def test_update_bpmn_success(self, app):
        """Test successfully updating BPMN XML content"""
        with app.app_context():
            with patch('services.bpmn_service.db') as mock_db, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_query:
                
                # Setup mocks
                mock_bpmn_file = Mock()
                mock_filter_by = Mock()
                mock_filter_by.first.return_value = mock_bpmn_file
                mock_query.filter_by.return_value = mock_filter_by
                
                new_xml = "<bpmn>updated</bpmn>"
                
                # Call function
                result = bpmn_service.update_bpmn(1, new_xml)
                
                # Assertions
                assert result == mock_bpmn_file
                assert mock_bpmn_file.file_data == new_xml.encode('utf-8')
                mock_db.session.commit.assert_called_once()

    def test_update_bpmn_not_found(self, app):
        """Test updating non-existent BPMN"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                mock_filter_by = Mock()
                mock_filter_by.first.return_value = None
                mock_query.filter_by.return_value = mock_filter_by
                
                with pytest.raises(ValueError, match="BPMN with id 999 not found"):
                    bpmn_service.update_bpmn(999, "<bpmn>test</bpmn>")

    def test_update_bpmn_database_error(self, app):
        """Test database error during BPMN update"""
        with app.app_context():
            with patch('services.bpmn_service.db') as mock_db, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_query:
                
                mock_bpmn_file = Mock()
                mock_filter_by = Mock()
                mock_filter_by.first.return_value = mock_bpmn_file
                mock_query.filter_by.return_value = mock_filter_by
                
                mock_db.session.commit.side_effect = SQLAlchemyError("DB error")
                
                with pytest.raises(RuntimeError, match="Database error while updating BPMN 1"):
                    bpmn_service.update_bpmn(1, "<bpmn>test</bpmn>")
                
                mock_db.session.rollback.assert_called_once()


class TestUpdateBpmnInfo:
    """Test cases for update_bpmn_info function"""

    def test_update_bpmn_info_success(self, app):
        """Test successfully updating BPMN metadata"""
        with app.app_context():
            with patch('services.bpmn_service.db') as mock_db, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_query:
                
                # Setup mocks
                mock_bpmn_file = Mock()
                mock_filter_by = Mock()
                mock_filter_by.first.return_value = mock_bpmn_file
                mock_query.filter_by.return_value = mock_filter_by
                
                new_filename = "updated.bpmn"
                new_description = "Updated description"
                
                # Call function
                result = bpmn_service.update_bpmn_info(1, new_filename, new_description)
                
                # Assertions
                assert result == mock_bpmn_file
                assert mock_bpmn_file.filename == new_filename
                assert mock_bpmn_file.description == new_description
                mock_db.session.commit.assert_called_once()

    def test_update_bpmn_info_not_found(self, app):
        """Test updating non-existent BPMN metadata"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                mock_filter_by = Mock()
                mock_filter_by.first.return_value = None
                mock_query.filter_by.return_value = mock_filter_by
                
                with pytest.raises(ValueError, match="BPMN with id 999 not found"):
                    bpmn_service.update_bpmn_info(999, "test.bpmn", "desc")

    def test_update_bpmn_info_database_error(self, app):
        """Test database error during BPMN info update"""
        with app.app_context():
            with patch('services.bpmn_service.db') as mock_db, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_query:
                
                mock_bpmn_file = Mock()
                mock_filter_by = Mock()
                mock_filter_by.first.return_value = mock_bpmn_file
                mock_query.filter_by.return_value = mock_filter_by
                
                mock_db.session.commit.side_effect = SQLAlchemyError("DB error")
                
                with pytest.raises(RuntimeError, match="Database error while updating BPMN 1 information"):
                    bpmn_service.update_bpmn_info(1, "test.bpmn", "desc")
                
                mock_db.session.rollback.assert_called_once()


class TestDeleteBpmn:
    """Test cases for delete_bpmn function"""

    def test_delete_bpmn_success(self, app):
        """Test successfully deleting a BPMN file"""
        with app.app_context():
            with patch('services.bpmn_service.db') as mock_db, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_query:
                
                # Setup mocks
                mock_bpmn_file = Mock()
                mock_query.get.return_value = mock_bpmn_file
                
                # Call function
                result = bpmn_service.delete_bpmn(1)
                
                # Assertions
                assert result == {"message": "BPMN 1 deleted successfully"}
                mock_db.session.delete.assert_called_once_with(mock_bpmn_file)
                mock_db.session.commit.assert_called_once()

    def test_delete_bpmn_not_found(self, app):
        """Test deleting non-existent BPMN"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                mock_query.get.return_value = None
                
                with pytest.raises(ValueError, match="BPMN with id 999 not found"):
                    bpmn_service.delete_bpmn(999)

    def test_delete_bpmn_database_error(self, app):
        """Test database error during BPMN deletion"""
        with app.app_context():
            with patch('services.bpmn_service.db') as mock_db, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_query:
                
                mock_bpmn_file = Mock()
                mock_query.get.return_value = mock_bpmn_file
                
                mock_db.session.commit.side_effect = SQLAlchemyError("DB error")
                
                with pytest.raises(RuntimeError, match="Database error while deleting BPMN 1"):
                    bpmn_service.delete_bpmn(1)
                
                mock_db.session.rollback.assert_called_once()


class TestGetBpmnCountByUser:
    """Test cases for get_bpmn_count_by_user function"""

    def test_get_bpmn_count_by_user_success(self, app):
        """Test successfully counting BPMN files by user"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                # Setup mocks
                mock_join = Mock()
                mock_filter = Mock()
                mock_filter.count.return_value = 5
                mock_join.filter.return_value = mock_filter
                mock_query.join.return_value = mock_join
                
                # Call function
                result = bpmn_service.get_bpmn_count_by_user(1)
                
                # Assertions
                assert result == 5

    def test_get_bpmn_count_by_user_database_error(self, app):
        """Test database error during BPMN count"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                mock_join = Mock()
                mock_filter = Mock()
                mock_filter.count.side_effect = SQLAlchemyError("DB error")
                mock_join.filter.return_value = mock_filter
                mock_query.join.return_value = mock_join
                
                with pytest.raises(RuntimeError, match="Database error while counting BPMNs for user 1"):
                    bpmn_service.get_bpmn_count_by_user(1)


class TestGetLatestBpmn:
    """Test cases for get_latest_bpmn function"""

    def test_get_latest_bpmn_success(self, app):
        """Test successfully retrieving latest BPMN file"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                # Setup mocks
                mock_bpmn_file = Mock()
                mock_join = Mock()
                mock_filter = Mock()
                mock_order_by = Mock()
                
                mock_order_by.first.return_value = mock_bpmn_file
                mock_filter.order_by.return_value = mock_order_by
                mock_join.filter.return_value = mock_filter
                mock_query.join.return_value = mock_join
                
                # Call function
                result = bpmn_service.get_latest_bpmn(1)
                
                # Assertions
                assert result == mock_bpmn_file

    def test_get_latest_bpmn_database_error(self, app):
        """Test database error during latest BPMN retrieval"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_query:
                mock_join = Mock()
                mock_filter = Mock()
                mock_filter.order_by.side_effect = SQLAlchemyError("DB error")
                mock_join.filter.return_value = mock_filter
                mock_query.join.return_value = mock_join
                
                with pytest.raises(RuntimeError, match="Database error while fetching latest BPMN"):
                    bpmn_service.get_latest_bpmn(1)


class TestGetBpmnBpoInfo:
    """Test cases for get_bpmn_bpo_info function"""

    def test_get_bpmn_bpo_info_success(self, app):
        """Test successfully retrieving BPO information"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query, \
                 patch('services.bpmn_service.User.query') as mock_user_query:
                
                # Setup mocks
                mock_bpmn = Mock()
                mock_project = Mock()
                mock_bpmn.project = mock_project
                mock_project.assigned_bpo_id = 2
                
                mock_bpmn_query.get.return_value = mock_bpmn
                
                mock_bpo_user = Mock()
                mock_bpo_user.user_id = 2
                mock_bpo_user.email = "bpo@example.com"
                mock_user_query.filter_by.return_value.first.return_value = mock_bpo_user
                
                # Call function
                result = bpmn_service.get_bpmn_bpo_info(1)
                
                # Assertions
                assert result == {"id": 2, "email": "bpo@example.com"}

    def test_get_bpmn_bpo_info_no_bpmn(self, app):
        """Test retrieving BPO info for non-existent BPMN"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query:
                mock_bpmn_query.get.return_value = None
                
                with pytest.raises(ValueError, match="BPMN or associated project not found for id 999"):
                    bpmn_service.get_bpmn_bpo_info(999)

    def test_get_bpmn_bpo_info_no_project(self, app):
        """Test retrieving BPO info for BPMN with no project"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query:
                mock_bpmn = Mock()
                mock_bpmn.project = None
                mock_bpmn_query.get.return_value = mock_bpmn
                
                with pytest.raises(ValueError, match="BPMN or associated project not found for id 1"):
                    bpmn_service.get_bpmn_bpo_info(1)

    def test_get_bpmn_bpo_info_no_bpo_assigned(self, app):
        """Test retrieving BPO info when no BPO is assigned"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query, \
                 patch('services.bpmn_service.User.query') as mock_user_query:
                
                mock_bpmn = Mock()
                mock_project = Mock()
                mock_bpmn.project = mock_project
                mock_project.assigned_bpo_id = 2
                
                mock_bpmn_query.get.return_value = mock_bpmn
                mock_user_query.filter_by.return_value.first.return_value = None
                
                result = bpmn_service.get_bpmn_bpo_info(1)
                
                assert result is None

    def test_get_bpmn_bpo_info_database_error(self, app):
        """Test database error during BPO info retrieval"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query:
                mock_bpmn_query.get.side_effect = SQLAlchemyError("DB error")
                
                with pytest.raises(RuntimeError, match="Database error while fetching assigned BPO"):
                    bpmn_service.get_bpmn_bpo_info(1)


class TestGetVersionHistory:
    """Test cases for get_version_history function"""

    def test_get_version_history_success(self, app):
        """Test successfully retrieving version history"""
        with app.app_context():
            with patch('services.bpmn_service.get_bpmn') as mock_get_bpmn, \
                 patch('services.bpmn_service.BpmnFileAudit.query') as mock_audit_query:
                
                # Setup mocks
                mock_bpmn_file = Mock()
                mock_get_bpmn.return_value = mock_bpmn_file
                
                mock_audit_entries = [
                    Mock(audit_id=1, version=1.1, save_date=Mock(isoformat=Mock(return_value="2023-01-01")), 
                         user_id=1, approval_status="approved"),
                    Mock(audit_id=2, version=1.0, save_date=Mock(isoformat=Mock(return_value="2023-01-01")), 
                         user_id=1, approval_status="pending"),
                ]
                
                mock_filter = Mock()
                mock_order_by = Mock()
                mock_order_by.all.return_value = mock_audit_entries
                mock_filter.order_by.return_value = mock_order_by
                mock_audit_query.filter_by.return_value = mock_filter
                
                # Call function
                result = bpmn_service.get_version_history(1, 1)
                
                # Assertions
                assert len(result) == 2
                assert result[0]["version"] == 1.1
                assert result[1]["version"] == 1.0

    def test_get_version_history_no_access(self, app):
        """Test retrieving version history with no access"""
        with app.app_context():
            with patch('services.bpmn_service.get_bpmn') as mock_get_bpmn:
                mock_get_bpmn.return_value = None
                
                with pytest.raises(ValueError, match="BPMN with id 1 not found or access denied"):
                    bpmn_service.get_version_history(1, 1)

    def test_get_version_history_database_error(self, app):
        """Test database error during version history retrieval"""
        with app.app_context():
            with patch('services.bpmn_service.get_bpmn') as mock_get_bpmn, \
                 patch('services.bpmn_service.BpmnFileAudit.query') as mock_audit_query:
                
                mock_bpmn_file = Mock()
                mock_get_bpmn.return_value = mock_bpmn_file
                mock_audit_query.filter_by.side_effect = SQLAlchemyError("DB error")
                
                with pytest.raises(RuntimeError, match="Database error while fetching version history"):
                    bpmn_service.get_version_history(1, 1)


class TestRestoreBpmnVersion:
    """Test cases for restore_bpmn_version function"""

    def test_restore_bpmn_version_not_bpo(self, app):
        """Test restoring version by non-BPO user"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query:
                class MockProject:
                    def __init__(self):
                        self.assigned_bpo_id = 2  # Different BPO
                
                class MockBpmnFile:
                    def __init__(self):
                        self.project = MockProject()
                
                mock_bpmn_file = MockBpmnFile()
                mock_bpmn_query.get.return_value = mock_bpmn_file
                
                with pytest.raises(PermissionError, match="Only the assigned BPO can restore versions"):
                    bpmn_service.restore_bpmn_version(1, 1, 3)  # user_id=3 is not BPO

    def test_restore_bpmn_version_bpmn_not_found(self, app):
        """Test restoring version for non-existent BPMN"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query:
                mock_bpmn_query.get.return_value = None
                
                with pytest.raises(ValueError, match="BPMN with id 999 not found"):
                    bpmn_service.restore_bpmn_version(999, 1, 1)

    def test_restore_bpmn_version_audit_not_found(self, app):
        """Test restoring non-existent audit version"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query, \
                 patch('services.bpmn_service.BpmnFileAudit.query') as mock_audit_query:
                
                class MockProject:
                    def __init__(self):
                        self.assigned_bpo_id = 1
                
                class MockBpmnFile:
                    def __init__(self):
                        self.project = MockProject()
                
                mock_bpmn_file = MockBpmnFile()
                mock_bpmn_query.get.return_value = mock_bpmn_file
                
                mock_audit_query.get.return_value = None
                
                with pytest.raises(ValueError, match="Version history entry with id 999 not found"):
                    bpmn_service.restore_bpmn_version(1, 999, 1)

    def test_restore_bpmn_version_mismatched_bpmn_id(self, app):
        """Test restoring audit entry that doesn't belong to BPMN"""
        with app.app_context():
            with patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query, \
                 patch('services.bpmn_service.BpmnFileAudit.query') as mock_audit_query:
                
                class MockProject:
                    def __init__(self):
                        self.assigned_bpo_id = 1
                
                class MockBpmnFile:
                    def __init__(self):
                        self.project = MockProject()
                
                class MockAuditEntry:
                    def __init__(self):
                        self.bpmnfile_id = 999  # Different BPMN ID
                
                mock_bpmn_file = MockBpmnFile()
                mock_bpmn_query.get.return_value = mock_bpmn_file
                
                mock_audit_entry = MockAuditEntry()
                mock_audit_query.get.return_value = mock_audit_entry
                
                with pytest.raises(ValueError, match="Version history does not belong to this BPMN"):
                    bpmn_service.restore_bpmn_version(1, 1, 1)


class TestGetProjectBpmnFiles:
    """Test cases for get_project_bpmn_files function"""

    def test_get_project_bpmn_files_success(self, app):
        """Test successfully retrieving project BPMN files"""
        with app.app_context():
            with patch('services.bpmn_service.Project.query') as mock_project_query, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query:
                
                # Setup mocks
                mock_project = Mock()
                mock_project_query.filter.return_value.first.return_value = mock_project
                
                mock_bpmn_files = [
                    Mock(
                        bpmnfile_id=1,
                        filename="file1.bpmn",
                        version=1.0,
                        upload_date=Mock(isoformat=Mock(return_value="2023-01-01")),
                        last_modified=Mock(isoformat=Mock(return_value="2023-01-01")),
                        description="Test file 1"
                    ),
                    Mock(
                        bpmnfile_id=2,
                        filename="file2.bpmn",
                        version=1.1,
                        upload_date=Mock(isoformat=Mock(return_value="2023-01-02")),
                        last_modified=Mock(isoformat=Mock(return_value="2023-01-02")),
                        description="Test file 2"
                    )
                ]
                mock_bpmn_query.filter_by.return_value.all.return_value = mock_bpmn_files
                
                # Call function
                result = bpmn_service.get_project_bpmn_files(1, 1)
                
                # Assertions
                assert len(result) == 2
                assert result[0]["bpmn_id"] == 1
                assert result[1]["bpmn_id"] == 2

    def test_get_project_bpmn_files_no_access(self, app):
        """Test retrieving project files with no access"""
        with app.app_context():
            with patch('services.bpmn_service.Project.query') as mock_project_query:
                mock_project_query.filter.return_value.first.return_value = None
                
                with pytest.raises(ValueError, match="Project with id 1 not found or access denied"):
                    bpmn_service.get_project_bpmn_files(1, 1)

    def test_get_project_bpmn_files_database_error(self, app):
        """Test database error during project files retrieval"""
        with app.app_context():
            with patch('services.bpmn_service.Project.query') as mock_project_query:
                mock_project_query.filter.return_value.first.side_effect = SQLAlchemyError("DB error")
                
                with pytest.raises(RuntimeError, match="Database error while fetching project BPMN files"):
                    bpmn_service.get_project_bpmn_files(1, 1)


class TestCloneBpmnFile:
    """Test cases for clone_bpmn_file function"""

    def test_clone_bpmn_file_not_bpo(self, app):
        """Test cloning by non-BPO user"""
        with app.app_context():
            with patch('services.bpmn_service.Project.query') as mock_project_query:
                class MockProject:
                    def __init__(self):
                        self.assigned_bpo_id = 2  # Different BPO
                
                mock_project = MockProject()
                mock_project_query.get.return_value = mock_project
                
                with pytest.raises(PermissionError, match="Only the assigned BPO can clone BPMN files"):
                    bpmn_service.clone_bpmn_file(1, 1, 3)  # user_id=3 is not BPO

    def test_clone_bpmn_file_project_not_found(self, app):
        """Test cloning for non-existent project"""
        with app.app_context():
            with patch('services.bpmn_service.Project.query') as mock_project_query:
                mock_project_query.get.return_value = None
                
                with pytest.raises(ValueError, match="Project with id 999 not found"):
                    bpmn_service.clone_bpmn_file(1, 999, 1)

    def test_clone_bpmn_file_source_not_found(self, app):
        """Test cloning non-existent source BPMN"""
        with app.app_context():
            with patch('services.bpmn_service.Project.query') as mock_project_query, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query:
                
                class MockProject:
                    def __init__(self):
                        self.assigned_bpo_id = 1
                
                mock_project = MockProject()
                mock_project_query.get.return_value = mock_project
                
                mock_bpmn_query.get.return_value = None
                
                with pytest.raises(ValueError, match="Source BPMN file with id 999 not found"):
                    bpmn_service.clone_bpmn_file(999, 1, 1)

    def test_clone_bpmn_file_wrong_project(self, app):
        """Test cloning BPMN from different project"""
        with app.app_context():
            with patch('services.bpmn_service.Project.query') as mock_project_query, \
                 patch('services.bpmn_service.BpmnFile.query') as mock_bpmn_query:
                
                class MockProject:
                    def __init__(self):
                        self.project_id = 1
                        self.assigned_bpo_id = 1
                
                class MockBpmnFile:
                    def __init__(self):
                        self.project_id = 999  # Different project
                
                mock_project = MockProject()
                mock_project_query.get.return_value = mock_project
                
                mock_source_bpmn = MockBpmnFile()
                mock_bpmn_query.get.return_value = mock_source_bpmn
                
                with pytest.raises(ValueError, match="Source BPMN does not belong to this project"):
                    bpmn_service.clone_bpmn_file(1, 1, 1)


# Fixtures for the tests
@pytest.fixture
def app():
    """Create a Flask app context for the tests"""
    from flask import Flask
    app = Flask(__name__)
    with app.app_context():
        yield app