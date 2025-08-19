# generate_keys.py
import getpass
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import hashlib

# 1. Generate a new private key
# Using a public exponent of 65537 is standard practice.
# Key size of 2048 bits is a good minimum for security.
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

# 2. Get the public key from the private key
public_key = private_key.public_key()

# 3. Prompt for a password to protect the private key
password = getpass.getpass("Enter a strong password to protect the private key: ").encode('utf-8')
password_confirm = getpass.getpass("Confirm password: ").encode('utf-8')

if password != password_confirm:
    print("Passwords do not match. Aborting.")
    exit()

# 4. Serialize and save the private key, encrypted with the password
# PEM is a standard format.
# BestAvailableEncryption uses a secure algorithm like AES-256-CBC.
# The library automatically handles salt and key derivation (PBKDF2).
pem_private_key = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.BestAvailableEncryption(password)
)

pkeysha256 = hashlib.sha256(pem_private_key).hexdigest()

with open('private_key_sha256_'+pkeysha256+'.pem', 'wb') as f:
    f.write(pem_private_key)

print("Encrypted private key saved to 'private_key_sha256_"+pkeysha256+".pem'")

# 5. Serialize and save the public key (no encryption needed)
pem_public_key = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

publicKeySha256 = hashlib.sha256(pem_public_key).hexdigest()
with open('public_key_sha256_'+publicKeySha256+'.pem', 'wb') as f:
    f.write(pem_public_key)

print("Public key saved to 'public_key_sha256_"+publicKeySha256+".pem'")
