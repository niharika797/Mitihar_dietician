"""
MFA (TOTP) service — pyotp-backed Google Authenticator support.

Usage pattern:
  1. setup:   secret = generate_mfa_secret()
              uri    = get_totp_uri(secret, user_email)
              → store secret on user row (not yet enabled)
              → return uri to client (client renders QR code)

  2. confirm: verify_totp(secret, code)  →  True  →  set mfa_enabled=True

  3. login:   if mfa_enabled → issue partial token (role=mfa_pending_*)
              client POSTs partial_token + totp_code to /mfa-login
              verify_totp → True → issue real JWT
"""

import pyotp


def generate_mfa_secret() -> str:
    """Generate a cryptographically-random base32 TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "Mitihar") -> str:
    """
    Return an otpauth:// URI for QR-code generation.
    The client (web/mobile) renders this as a QR code — the backend never
    generates an image, keeping the dependency surface minimal.
    """
    return pyotp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=issuer,
    )


def verify_totp(secret: str, code: str) -> bool:
    """
    Verify a 6-digit TOTP code against the stored secret.
    valid_window=1 allows ±30 seconds of clock drift (one step either side).
    Returns False if secret or code is falsy (never raises).
    """
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)
