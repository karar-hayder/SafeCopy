import hashlib
import os
import shutil

from safecopy.cryptor import Cryptor


def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def test_cryptor():
    chunk_size = 5 * 1024 * 1024

    test_dir = os.path.dirname(os.path.abspath(__file__))
    tmp_root = os.path.join(test_dir, "tmp_test_dir_cryptor")
    os.makedirs(tmp_root, exist_ok=True)

    tmp_files = []
    test_file = None
    enc_file = None
    dec_file = None

    try:
        # Create test file with random content in our own tmp dir
        test_file_path = os.path.join(tmp_root, "test_random.bin")
        with open(test_file_path, "wb") as test_f:
            test_f.write(os.urandom(chunk_size + 1024))  # 5MB + 1KB
            test_file = test_file_path
            tmp_files.append(test_file)

        print(f"Created test file: {test_file}")

        original_md5 = calculate_md5(test_file)
        print(f"Original MD5: {original_md5}")

        key = Cryptor.derive_key_from_string("secret_password")[0]
        cryptor = Cryptor(
            mapping_uuid="test-uuid", mapping_name="test-mapping", key=key
        )

        # Encrypt, write output to temp file (ensure output is in our tmp dir if possible)
        print("Encrypting...")
        enc_file = cryptor.encrypt(test_file)
        if not enc_file:
            print("Encryption failed!")
            enc_file = None  # Defensive, though already None
            return
        # If enc_file is not in tmp_root, move it for proper cleanup
        enc_file_basename = os.path.basename(enc_file)
        enc_file_in_tmp = os.path.join(tmp_root, enc_file_basename)
        if os.path.abspath(os.path.dirname(enc_file)) != os.path.abspath(tmp_root):
            shutil.move(enc_file, enc_file_in_tmp)
            enc_file = enc_file_in_tmp
        tmp_files.append(enc_file)
        print(f"Encrypted file: {enc_file}")

        # Verify magic header
        with open(enc_file, "rb") as f:
            header = f.read(8)
            print(f"Header found: {header}")
            if header != b"SAFECOPY":
                print("Magic header mismatch!")
                return

        # Decrypt, write output to temp file (ensure output is in our tmp dir if possible)
        print("Decrypting...")
        dec_file = cryptor.decrypt(enc_file)
        if not dec_file:
            print("Decryption failed!")
            dec_file = None  # Defensive, though already None
            return
        # If dec_file is not in tmp_root, move it for proper cleanup
        dec_file_basename = os.path.basename(dec_file)
        dec_file_in_tmp = os.path.join(tmp_root, dec_file_basename)
        if os.path.abspath(os.path.dirname(dec_file)) != os.path.abspath(tmp_root):
            shutil.move(dec_file, dec_file_in_tmp)
            dec_file = dec_file_in_tmp
        tmp_files.append(dec_file)
        print(f"Decrypted file: {dec_file}")

        decrypted_md5 = calculate_md5(dec_file)
        print(f"Decrypted MD5: {decrypted_md5}")

        if original_md5 == decrypted_md5:
            print("SUCCESS: MD5 matches!")
        else:
            print("FAILURE: MD5 mismatch!")
    finally:
        # Cleanup all temp files created, skipping Nones and dupes
        seen = set()
        for f in tmp_files:
            if not f or f in seen:
                continue
            seen.add(f)
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                print(f"Failed to remove {f}: {e}")

        # Ensure temp files are cleaned up even if not in tmp_files list
        for f in (test_file, enc_file, dec_file):
            if f and f not in seen:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception as e:
                    print(f"Failed to remove {f}: {e}")

        # Cleanup tmp_dir
        try:
            if os.path.exists(tmp_root) and not os.listdir(tmp_root):
                os.rmdir(tmp_root)
            elif os.path.exists(tmp_root):
                # Remove all content if anything left
                shutil.rmtree(tmp_root)
        except Exception as e:
            print(f"Failed to remove tmp_root {tmp_root}: {e}")


if __name__ == "__main__":
    test_cryptor()
