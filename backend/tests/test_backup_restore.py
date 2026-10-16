import os
import shutil
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.user import User, Workspace
from app.models.automation import Automation
from app.security import get_password_hash

def test_database_backup_and_recovery():
    """Validates that database state can be backed up and restored without data loss."""
    with tempfile.TemporaryDirectory() as temp_dir:
        primary_db_path = os.path.join(temp_dir, "primary.db")
        backup_db_path = os.path.join(temp_dir, "backup.db")

        # 1. Initialize primary DB
        engine = create_engine(f"sqlite:///{primary_db_path}")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Seed data
        user = User(
            email="backup_test@woka.io",
            hashed_password=get_password_hash("Password123!"),
            full_name="Backup User",
            role="CREATOR"
        )
        session.add(user)
        session.flush()

        ws = Workspace(name="Backup Workspace", owner_id=user.id)
        session.add(ws)
        session.flush()

        auto = Automation(
            workspace_id=ws.id,
            ig_account_id="dummy_acc",
            name="Backup Automation",
            trigger_type="COMMENT",
            target_post_type="ALL_POSTS",
            match_type="CONTAINS_ANY",
            trigger_keywords='["backup"]',
            dm_message_template="Recovered successfully",
            is_active=True
        )
        session.add(auto)
        session.commit()
        session.close()
        engine.dispose()

        # 2. Perform point-in-time backup
        shutil.copy2(primary_db_path, backup_db_path)
        assert os.path.exists(backup_db_path)

        # 3. Simulate disaster / database corruption on primary
        engine = create_engine(f"sqlite:///{primary_db_path}")
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

        # Verify primary is empty
        engine = create_engine(f"sqlite:///{primary_db_path}")
        Session = sessionmaker(bind=engine)
        s = Session()
        from sqlalchemy import inspect
        inspector = inspect(engine)
        assert len(inspector.get_table_names()) == 0
        s.close()
        engine.dispose()

        # 4. Perform restoration from backup
        shutil.copy2(backup_db_path, primary_db_path)

        # 5. Verify restored state
        engine = create_engine(f"sqlite:///{primary_db_path}")
        Session = sessionmaker(bind=engine)
        restored_session = Session()

        restored_user = restored_session.query(User).filter(User.email == "backup_test@woka.io").first()
        assert restored_user is not None
        assert restored_user.full_name == "Backup User"

        restored_auto = restored_session.query(Automation).filter(Automation.name == "Backup Automation").first()
        assert restored_auto is not None
        assert restored_auto.dm_message_template == "Recovered successfully"

        restored_session.close()
        engine.dispose()
