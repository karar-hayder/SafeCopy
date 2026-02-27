import base64
import logging
import os
import struct
from typing import Literal

import keyring
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

MAGIC_HEADER = b"SFENC1.0"
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB
IV_SIZE = 12


class Cryptor:
    def __init__(
        self,
        mapping_name: str = None,
        mapping_uuid: str = None,
        key: str | bytes = None,
    ) -> None:
        if mapping_uuid is None:
            raise ValueError("Mapping UUID cannot be None")
        if mapping_name is None:
            raise ValueError("Mapping Name cannot be None")

        self.mapping_name = mapping_name
        self.mapping_uuid = mapping_uuid
        self._key = None
        self.aesgcm = None
        self.aad = self.mapping_uuid.encode("utf-8")

        if mapping_uuid is not None and not key:
            self._get_key_from_keyring()
        elif key:
            self.key = key

    @property
    def key(self) -> bytes | None:
        return self._key

    @key.setter
    def key(self, value: str | bytes) -> None:
        if value is None:
            self._key = None
            self.aesgcm = None
            return
        self._key = (
            value if isinstance(value, bytes) else base64.urlsafe_b64decode(value)
        )
        self.aesgcm = AESGCM(self._key)

    def _get_key_from_keyring(self) -> bytes | None:
        key = keyring.get_password("safecopy", self.mapping_uuid + "_key")
        if key is None:
            return None
        # keyring stores passwords as strings, so we encode it back to bytes
        self.key = key
        return self.key

    def _set_key_in_keyring(self) -> None:
        if not self.mapping_uuid or not self.key:
            return
        # keyring.set_password expects a string password
        key_str = base64.urlsafe_b64encode(self.key).decode()
        keyring.set_password("safecopy", self.mapping_uuid + "_key", key_str)

    def __encrypt_data(self, data: bytes) -> bytes:
        iv = os.urandom(IV_SIZE)
        # AESGCM.encrypt returns iv + ciphertext + tag?
        # Actually it returns ciphertext + tag. We provide the IV (nonce).
        ciphertext = self.aesgcm.encrypt(iv, data, self.aad)
        return iv + ciphertext

    def __decrypt_data(self, data: bytes) -> bytes:
        iv = data[:IV_SIZE]
        ciphertext = data[IV_SIZE:]
        return self.aesgcm.decrypt(iv, ciphertext, self.aad)

    @staticmethod
    def generate_random_key() -> bytes:
        return AESGCM.generate_key(bit_length=256)

    @staticmethod
    def derive_key_from_string(
        input_string: str, salt: bytes | None = None
    ) -> tuple[bytes, bytes]:
        """
        Derives a 32-byte key for AES-256-GCM from the input string.
        """
        if not input_string:
            raise ValueError("Input string cannot be empty")
        if not salt:
            salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=500000,
        )
        key = kdf.derive(input_string.encode())
        return key, salt

    @property
    def has_key(self) -> bool:
        return self.key is not None

    def encrypt(self, file_name: str) -> str | Literal[False]:
        """
        Encrypts a file using AES-256-GCM encryption.
        Encrypts 5MB chunks with length prefixes.
        """
        file_name_enc_path = file_name + ".enc"
        tmp_file_name_enc_path = file_name_enc_path + ".tmp"
        try:
            with open(file_name, "rb") as rf, open(tmp_file_name_enc_path, "wb") as wf:
                wf.write(MAGIC_HEADER)
                while True:
                    chunk = rf.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    encrypted_chunk = self.__encrypt_data(chunk)
                    # Write 4-byte big-endian length prefix
                    wf.write(struct.pack(">I", len(encrypted_chunk)))
                    wf.write(encrypted_chunk)

            self._set_key_in_keyring()

        except Exception as e:
            logger.error("Encryption failed for %s: %s", file_name, e, exc_info=True)
            if os.path.exists(tmp_file_name_enc_path):
                try:
                    os.remove(tmp_file_name_enc_path)
                except Exception:
                    pass
            return False

        try:
            os.replace(tmp_file_name_enc_path, file_name_enc_path)
        except Exception as e:
            logger.error(
                "Failed to rename temporary file %s to %s: %s",
                tmp_file_name_enc_path,
                file_name_enc_path,
                e,
                exc_info=True,
            )
            return False

        try:
            os.remove(file_name)
        except Exception as e:
            logger.warning(
                "Failed to remove original file %s after encryption: %s", file_name, e
            )

        return file_name_enc_path

    def decrypt(self, enc_file_name: str) -> str | Literal[False]:
        """
        Decrypts a file using AES-256-GCM encryption.
        Expects magic header and chunk-length-prefixed format.
        """
        file_name_dec_path = enc_file_name.replace(".enc", "")
        try:
            with open(enc_file_name, "rb") as rf, open(file_name_dec_path, "wb") as wf:
                header = rf.read(len(MAGIC_HEADER))
                if header != MAGIC_HEADER:
                    raise ValueError("Invalid magic header")

                while True:
                    length_bytes = rf.read(4)
                    if not length_bytes:
                        break

                    length = struct.unpack(">I", length_bytes)[0]
                    encrypted_chunk = rf.read(length)
                    if len(encrypted_chunk) != length:
                        raise ValueError("Truncated chunk")

                    decrypted_chunk = self.__decrypt_data(encrypted_chunk)
                    wf.write(decrypted_chunk)

        except Exception as e:
            logger.error(
                "Decryption failed for %s: %s", enc_file_name, e, exc_info=True
            )
            if os.path.exists(file_name_dec_path):
                try:
                    os.remove(file_name_dec_path)
                except Exception:
                    pass
            return False

        try:
            os.remove(enc_file_name)
        except Exception as e:
            logger.error(
                "Failed to remove encrypted file %s: %s",
                enc_file_name,
                e,
                exc_info=True,
            )

        return file_name_dec_path
