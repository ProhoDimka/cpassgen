import base64
import hashlib


def generate_password(username: str, resource: str, secret: str) -> str:
    data = f"{username}:{resource}:{secret}".encode("utf-8")
    b64_data = base64.urlsafe_b64encode(data)
    digest = hashlib.sha256(b64_data).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8")
