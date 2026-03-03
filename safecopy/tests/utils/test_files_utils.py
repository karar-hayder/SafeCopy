from unittest.mock import patch

import pytest

from safecopy.utils.filesUtils import atomic_file_rename


def test_atomic_file_rename_success(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("hello")
    dst = tmp_path / "dst.txt"

    atomic_file_rename(src, dst)

    assert dst.exists()
    assert dst.read_text() == "hello"
    assert not src.exists()


@patch("os.replace")
def test_atomic_file_rename_retries_on_permission_error(mock_replace, tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("hello")
    dst = tmp_path / "dst.txt"

    # Fail twice with PermissionError, then succeed
    mock_replace.side_effect = [
        PermissionError("Locked"),
        PermissionError("Locked"),
        None,
    ]

    with patch("time.sleep", return_value=None):  # Skip actual delay
        atomic_file_rename(src, dst, retries=3, delay=0.1)

    assert mock_replace.call_count == 3


@patch("os.replace")
def test_atomic_file_rename_raises_after_max_retries(mock_replace, tmp_path):
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"

    mock_replace.side_effect = PermissionError("Always Locked")

    with patch("time.sleep", return_value=None):
        with pytest.raises(PermissionError):
            atomic_file_rename(src, dst, retries=3, delay=0.1)

    assert mock_replace.call_count == 3
