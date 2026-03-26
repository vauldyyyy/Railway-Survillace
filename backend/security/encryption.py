from cryptography.fernet import Fernet
import io
import os
from pathlib import Path

class SecureModelLoader:
    def __init__(self, key_path: str = "models/secret.key"):
        self.key_path = Path(key_path)
        if not self.key_path.exists():
            self.key = Fernet.generate_key()
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            self.key_path.write_bytes(self.key)
        else:
            self.key = self.key_path.read_bytes()
        self.cipher = Fernet(self.key)

    def encrypt_model(self, model_path: str):
        path = Path(model_path)
        if not path.exists(): return False
        data = path.read_bytes()
        encrypted = self.cipher.encrypt(data)
        Path(f"{model_path}.enc").write_bytes(encrypted)
        return True

    def load_encrypted_model(self, encrypted_path: str) -> io.BytesIO:
        """
        Decrypts an encrypted .pt.enc model into memory.
        The decrypted bytes are wrapped in a BytesIO buffer and NEVER saved to disk,
        meaning the model weights remain secure at rest on the edge node.
        """
        path = Path(encrypted_path)
        if not path.exists(): return None
        encrypted = path.read_bytes()
        decrypted = self.cipher.decrypt(encrypted)
        buffer = io.BytesIO(decrypted)
        return buffer
