#!/usr/bin/env python3
"""Generate an Ed25519 keypair for signing skill packages."""

import base64

from nacl.signing import SigningKey

sk = SigningKey.generate()

print(f"NEXUS_SIGNING_KEY={base64.b64encode(bytes(sk)).decode()}")
print()
print(f"Public key: {base64.b64encode(bytes(sk.verify_key)).decode()}")
print()
print("Add NEXUS_SIGNING_KEY to your environment or .env file.")
print("The public key will be served at GET /skill/pubkey.")
