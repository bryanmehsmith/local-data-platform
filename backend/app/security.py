import hashlib
import hmac
import secrets

from fastapi import Header, HTTPException

from app.config import settings

# Static pepper used to hash the incoming X-API-Key header before comparing
# it against the configured hash(es) in BACKEND_API_KEY_HASHES, so the
# plaintext key is never stored or compared directly. Because the pepper
# itself lives in source control, this does not resist offline brute-force
# of a leaked hash — treat BACKEND_API_KEY_HASHES entries as secrets in
# their own right, the same as the plaintext key would be.
_PEPPER = b"ldp-backend-api-key-pepper-v1"


def hash_api_key(raw_key: str) -> str:
    """Hash a plaintext API key the same way an incoming request header is
    hashed, for generating/rotating BACKEND_API_KEY_HASHES entries, e.g.:

        python -c "import hashlib,hmac; p=b'ldp-backend-api-key-pepper-v1'; \\
        print(hmac.new(p, b'<your-key>', hashlib.sha256).hexdigest())"
    """
    return hmac.new(_PEPPER, msg=raw_key.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()


def _valid_hashes() -> list[str]:
    hashes = settings.backend_api_key_hashes
    if hashes:
        return hashes
    # Backward compatibility: if no hashes are configured but the legacy
    # plaintext BACKEND_API_KEY is set, hash it on the fly as the sole
    # valid hash.
    if settings.api_key:
        return [hash_api_key(settings.api_key)]
    return []


def require_api_key(x_api_key: str = Header(default="")) -> None:
    valid_hashes = _valid_hashes()
    candidate = hash_api_key(x_api_key)
    if not valid_hashes or not any(secrets.compare_digest(candidate, h) for h in valid_hashes):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")
