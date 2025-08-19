import getpass
import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidKey
import sys

class EncryptionManager:
    def __init__(self):
        
        # The size of the RSA key in bytes. For a 2048-bit key, this is 256.
        self.RSA_ENCRYPTED_KEY_SIZE = 256 
        # The size of the AES-GCM nonce (IV). 12 bytes is recommended.
        self.AES_NONCE_SIZE = 12

        with open("D:/bkp/backup-keys/public_key_sha256_c4a1c951f7eb5585da940891ac3ed8128df8914cd4bd84e2c671d8bed2d9b5ea.pem", "rb") as key_file:
            self.encryptionKey = serialization.load_pem_public_key(key_file.read())
        
        self.decryptionKeyPath = "D:/bkp/backup-keys/private_key_sha256_307b636be4c84c184e81257eaebfae90693a8314f7f883a6575c715e519b78cf.pem"


    def encrypt(self, data) -> bytes:
        # 1. Generate a one-time-use AES-256 key for symmetric encryption.
        symmetric_key = AESGCM.generate_key(bit_length=256)
        
        # 2. Encrypt the *symmetric key* with the RSA public key.
        encrypted_symmetric_key = self.encryptionKey.encrypt( # type: ignore
            symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # 3. Encrypt the actual data using AES-GCM with the symmetric key.
        aesgcm = AESGCM(symmetric_key)
        # A nonce (number used once) is required for AES-GCM.
        nonce = os.urandom(self.AES_NONCE_SIZE)
        # The encrypt() method returns the ciphertext and authentication tag combined.
        ciphertext_with_tag = aesgcm.encrypt(nonce, data, None)

        # 4. Construct the final payload:
        # [Encrypted AES Key (256 bytes)] + [Nonce (12 bytes)] + [AES Ciphertext]
        payload = encrypted_symmetric_key + nonce + ciphertext_with_tag

        return payload

    def initDecryption(self):
        password = getpass.getpass("Enter the password to decrypt the private key: ")
        with open(self.decryptionKeyPath, "rb") as key_file:
            self.decryptionKey = serialization.load_pem_private_key(key_file.read(), password=password.encode('utf-8'))



    def decrypt(self, data) -> bytes:
        
        # 1. Deconstruct the payload
        encrypted_symmetric_key = data[:self.RSA_ENCRYPTED_KEY_SIZE]
        nonce = data[self.RSA_ENCRYPTED_KEY_SIZE:self.RSA_ENCRYPTED_KEY_SIZE + self.AES_NONCE_SIZE]
        ciphertext_with_tag = data[self.RSA_ENCRYPTED_KEY_SIZE + self.AES_NONCE_SIZE:]

        # 2. Decrypt the symmetric key with the RSA private key
        symmetric_key = self.decryptionKey.decrypt(
            encrypted_symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # 3. Decrypt the actual data using the now-decrypted symmetric key.
        # If it fails here, it means the ciphertext was tampered with or the key/nonce is incorrect.
        aesgcm = AESGCM(symmetric_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)

        return plaintext
    

    def encryptFile(self, filePath):
        with open(filePath, "rb") as file:
            data = file.read()
        
        encrypted_data = self.encrypt(data)
        
        with open(filePath + ".enc", "wb+") as enc_file:
            enc_file.write(encrypted_data)

        os.remove(filePath)  # Remove the original file after encryption
        
        print(f"Encrypted file '{filePath}'")


    def encryptDir(self, dirPath):
        for root, dirs, files in os.walk(dirPath):
            for file in files:
                if file.endswith(".enc"):
                    continue
                filePath = os.path.join(root, file)
                self.encryptFile(filePath)

        print(f"All files in directory '{dirPath}' encrypted successfully.")


    def decryptFile(self, filePath):
        if not filePath.endswith(".enc"):
            raise ValueError("File '" + filePath + "' is not an encrypted file (does not end with .enc)")
        
        with open(filePath, "rb") as enc_file:
            encrypted_data = enc_file.read()
        
        decrypted_data = self.decrypt(encrypted_data)
        
        with open(filePath[:-len(".enc")], "wb+") as dec_file:
            dec_file.write(decrypted_data)

        os.remove(filePath)  # Remove the encrypted file after decryption
        
        print(f"Decrypted file '{filePath}'")


    def decryptDir(self, dirPath):
        for root, dirs, files in os.walk(dirPath):
            for file in files:
                if file.endswith(".enc"):
                    filePath = os.path.join(root, file)
                    self.decryptFile(filePath)

        print(f"All encrypted files in directory '{dirPath}' decrypted successfully.")


if __name__ == "__main__":
    encryptionManager = EncryptionManager()

    
    """original_data = b"This is a secret message that nobody should read. sfsdfdsfqdsfqdfqfdsqsdfqfsddsfmqljjkfsdqlkmjfdsqjmklsdfqmlkjfsdqmjlkds azproiejazporijrpoiaproaizjreaiopreoiapjrepaoijreapioarepiozeropizera"
    print(f"Original Data: {original_data.decode()}")

    encrypted_data = encryptionManager.encrypt(original_data)

    print(f"Encrypted (Ciphertext): {encrypted_data.hex()}")
    user_password_correct = input("\nEnter the CORRECT password to decrypt: ")
    decrypted_data = encryptionManager.decrypt(encrypted_data, user_password_correct)
    print(f"Decrypted Data: {decrypted_data.decode()}")
    assert original_data == decrypted_data"""

    #encryptionManager.initDecryption()

    #encryptionManager.encryptDir("D:/bkp/notion/")
