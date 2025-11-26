import os
import tempfile

try:
    import pytest  # type: ignore
except ImportError:
    pytest = None  # Allow the file to be imported even if pytest is missing


from safecopy.db.controller import add_mapping, init_database


def get_schedule_rows(db_path):
    """
    Retrieve all rows from the backup_schedules table, ordered by id ascending.

    Args:
        db_path (str): Path to the SQLite database file.

    Returns:
        list[dict]: List of schedule records as dictionaries.
    """
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Enable foreign key constraints for SELECT session as well (defensive)
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("SELECT * FROM backup_schedules ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]


if pytest is not None:

    @pytest.fixture
    def temp_db_file():
        """
        Pytest fixture for creating and cleaning up a temporary database file.

        Yields:
            str: Path to the temporary SQLite database file.
        """
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test_sched.db")
        yield db_path
        try:
            for name in os.listdir(tmpdir):
                os.remove(os.path.join(tmpdir, name))
            os.rmdir(tmpdir)
        except Exception:
            pass

    def test_backup_schedules_crud(temp_db_file):
        """
        Test create, read, update, and delete operations for backup_schedules table.
        """
        init_database(temp_db_file)

        # Add a mapping to associate schedule with
        mapping_id = add_mapping(
            "foo", "bar", max_versions=3, compression="none", db_path=temp_db_file
        )
        assert isinstance(mapping_id, int)

        # Insert a schedule directly (simulate what a schedule function would do)
        import sqlite3

        schedule_type = "cron"
        schedule_value = "0 0 * * *"
        with sqlite3.connect(temp_db_file) as conn:
            cursor = conn.cursor()
            # Ensure foreign key constraint is enforced on this connection
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(
                """
                INSERT INTO backup_schedules (mapping_id, schedule_type, schedule_value, enabled)
                VALUES (?, ?, ?, ?)
                """,
                (mapping_id, schedule_type, schedule_value, 1),
            )
            schedule_id = cursor.lastrowid

        # Query schedule directly
        schedules = get_schedule_rows(temp_db_file)
        assert len(schedules) == 1
        sched = schedules[0]
        assert sched["mapping_id"] == mapping_id
        assert sched["schedule_type"] == schedule_type
        assert sched["schedule_value"] == schedule_value
        assert sched["enabled"] == 1

        # Test updating a schedule
        new_value = "0 12 * * *"
        with sqlite3.connect(temp_db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(
                """
                UPDATE backup_schedules SET schedule_value = ?, enabled = ?
                WHERE id = ?
                """,
                (new_value, 0, schedule_id),
            )
        updated = get_schedule_rows(temp_db_file)[0]
        assert updated["schedule_value"] == new_value
        assert updated["enabled"] == 0

        # Delete the schedule
        with sqlite3.connect(temp_db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("DELETE FROM backup_schedules WHERE id = ?", (schedule_id,))
        assert get_schedule_rows(temp_db_file) == []

    def test_backup_schedules_foreign_key_deletes(temp_db_file):
        """
        Test that deleting a mapping cascades to delete backup_schedules.

        This ensures foreign key cascade is enabled on every connection.
        """
        init_database(temp_db_file)
        mapping_id = add_mapping("a", "b", db_path=temp_db_file)
        import sqlite3

        # Add a schedule linked to mapping, enabling foreign key constraints explicitly
        with sqlite3.connect(temp_db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(
                """
                INSERT INTO backup_schedules (mapping_id, schedule_type, schedule_value, enabled)
                VALUES (?, ?, ?, ?)
                """,
                (mapping_id, "interval", "1:00:00", 1),
            )
        schedules = get_schedule_rows(temp_db_file)
        assert schedules and schedules[0]["mapping_id"] == mapping_id

        # Delete mapping using controller (which uses its own connection)
        from safecopy.db.controller import delete_mapping

        delete_mapping(mapping_id, db_path=temp_db_file)

        # Ensure foreign key cascades are effective (enforce on this SELECT, too)
        assert get_schedule_rows(temp_db_file) == []
