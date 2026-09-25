"""Generate a VAPID keypair for Web Push and print the two env vars to set.

    python -m app.vapid_gen

Never commit the private key. Paste both lines into .env (local) and into Vercel's environment
variables (production) for the vantage-api project.
"""

import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def main() -> None:
    vapid = Vapid()
    vapid.generate_keys()

    public_raw = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    private_der = vapid.private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    b64 = lambda raw: base64.urlsafe_b64encode(raw).rstrip(b"=").decode()  # noqa: E731

    print(f"VAPID_PUBLIC_KEY={b64(public_raw)}")
    print(f"VAPID_PRIVATE_KEY={b64(private_der)}")
    print("VAPID_SUBJECT=mailto:hello@example.com  # change to a real contact address")


if __name__ == "__main__":
    main()
