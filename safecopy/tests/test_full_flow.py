import os
import shutil
import tempfile
import zipfile

from safecopy.backup import run_backup
from safecopy.cryptor import Cryptor
from safecopy.db.controller import add_mapping, get_mapping, init_database


def test_full_flow():
    # Setup temporary directories
    src_dir = tempfile.mkdtemp()
    dst_dir = tempfile.mkdtemp()
    db_dir = tempfile.mkdtemp()
    db_path = os.path.join(db_dir, "test_flow.db")

    dec_file = None
    try:
        # Initialize temp database
        init_database(db_path)

        # Create a real mapping in the temp database
        mapping_id = add_mapping(
            source=src_dir,
            destination=dst_dir,
            max_versions=3,
            compression="zip",  # Encrypted directory needs compression to be a file
            enabled=True,
            encrypted=True,
            db_path=db_path,
        )

        # Create a test file in source
        test_file_path = os.path.join(src_dir, "test.txt")
        test_content = "This is a test file for encryption and backup."
        with open(test_file_path, "w") as f:
            f.write(test_content)

        # Get full mapping info from DB
        mapping = get_mapping(mapping_id, db_path=db_path)
        mapping["id"] = mapping_id  # Ensure ID is present for run_backup

        print(f"Running backup with encryption for mapping {mapping_id}...")

        # Override run_backup's internal DB path for testing if possible
        # Since run_backup imports it, we might need a better way or just ignore DB logging for this test
        # Actually, let's just use the mapping dict directly

        success, message = run_backup(mapping, db_path=db_path)

        print(f"Success: {success}")
        print(f"Message: {message}")

        assert success is True, f"Backup failed: {message}"

        # Verify that an encrypted file exists in the destination
        files = os.listdir(dst_dir)
        enc_files = [f for f in files if f.endswith(".enc")]
        print(f"Destination files: {files}")

        assert len(enc_files) > 0, "No encrypted file found in destination!"

        enc_file_path = os.path.join(dst_dir, enc_files[0])
        print(f"Encrypted file path: {enc_file_path}")

        # Verify it has the magic header
        with open(enc_file_path, "rb") as f:
            header = f.read(8)
            print(f"Header: {header}")
            assert header == b"SFENC1.0", f"Magic header mismatch: {header}"

        # Decrypt to verify content
        print("Attempting decryption...")
        cryptor = Cryptor(
            mapping_uuid=mapping["uuid"], mapping_name=mapping.get("name", "test")
        )

        # Copy to a temporary location for decryption because decrypt deletes the source .enc
        tmp_enc = enc_file_path + ".copy"
        shutil.copy2(enc_file_path, tmp_enc)

        dec_file = cryptor.decrypt(tmp_enc)
        assert dec_file is not False, "Decryption failed!"

        print(f"Decrypted file (or dir): {dec_file}")

        # Check content
        # Since we used compression="zip", the decrypted file is a zip
        assert os.path.isfile(dec_file), "Decrypted item should be a file"

        if dec_file.endswith(".zip") or zipfile.is_zipfile(dec_file):
            print("Decrypted file is a zip, verifying contents...")
            with zipfile.ZipFile(dec_file, "r") as zf:
                # Zip should contain "test.txt"
                file_names = zf.namelist()
                print(f"Zip contents: {file_names}")
                assert "test.txt" in file_names or any(
                    "test.txt" in name for name in file_names
                )

                # Extract and verify
                with zf.open("test.txt") as f:
                    content = f.read().decode("utf-8")
                    print(f"Zip member content: {content}")
                    assert content == test_content
        else:
            with open(dec_file, "r") as f:
                content = f.read()
                print(f"Decrypted content: {content}")
                assert content == test_content

    finally:
        # Cleanup
        if dec_file and os.path.exists(dec_file):
            if os.path.isdir(dec_file):
                shutil.rmtree(dec_file)
            else:
                os.remove(dec_file)
        if os.path.exists(src_dir):
            shutil.rmtree(src_dir)
        if os.path.exists(dst_dir):
            shutil.rmtree(dst_dir)
        if os.path.exists(db_dir):
            shutil.rmtree(db_dir)

        print("\nFlow verification complete!")


if __name__ == "__main__":
    test_full_flow()
