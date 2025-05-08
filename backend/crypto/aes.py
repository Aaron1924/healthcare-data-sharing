from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import os
import base64
import json

def generate_key():
    """Generate a random AES key"""
    return os.urandom(32)  # 256-bit key

def encrypt(data, key):
    """Encrypt data using AES-GCM"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    if isinstance(key, str):
        key = key.encode('utf-8')
    
    # Generate a random IV
    iv = os.urandom(12)  # 96 bits for GCM
    
    # Create an encryptor
    encryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(iv),
        backend=default_backend()
    ).encryptor()
    
    # Encrypt the data
    ciphertext = encryptor.update(data) + encryptor.finalize()
    
    # Return IV, ciphertext, and tag
    result = {
        'iv': base64.b64encode(iv).decode('utf-8'),
        'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
        'tag': base64.b64encode(encryptor.tag).decode('utf-8')
    }
    
    return json.dumps(result).encode('utf-8')

def decrypt(encrypted_data, key):
    """Decrypt data using AES-GCM"""
    if isinstance(encrypted_data, bytes):
        encrypted_data = encrypted_data.decode('utf-8')
    if isinstance(key, str):
        key = key.encode('utf-8')
    
    # Parse the encrypted data
    data = json.loads(encrypted_data)
    iv = base64.b64decode(data['iv'])
    ciphertext = base64.b64decode(data['ciphertext'])
    tag = base64.b64decode(data['tag'])
    
    # Create a decryptor
    decryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(iv, tag),
        backend=default_backend()
    ).decryptor()
    
    # Decrypt the data
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    
    return plaintext.decode('utf-8')

def encrypt_key(key, public_key):
    """Encrypt a symmetric key with a public key (ECIES)"""
    # In a real implementation, this would use ECIES
    # For this MVP, we'll just use a simple XOR with the public key
    if isinstance(key, str):
        key = key.encode('utf-8')
    if isinstance(public_key, str):
        public_key = public_key.encode('utf-8')
    
    # Ensure public_key is at least as long as key
    while len(public_key) < len(key):
        public_key = public_key + public_key
    
    # XOR the key with the public key
    encrypted_key = bytes(a ^ b for a, b in zip(key, public_key[:len(key)]))
    
    return base64.b64encode(encrypted_key).decode('utf-8')

def decrypt_key(encrypted_key, private_key):
    """Decrypt a symmetric key with a private key (ECIES)"""
    # In a real implementation, this would use ECIES
    # For this MVP, we'll just use a simple XOR with the private key
    if isinstance(encrypted_key, str):
        encrypted_key = base64.b64decode(encrypted_key)
    if isinstance(private_key, str):
        private_key = private_key.encode('utf-8')
    
    # Ensure private_key is at least as long as encrypted_key
    while len(private_key) < len(encrypted_key):
        private_key = private_key + private_key
    
    # XOR the encrypted key with the private key
    decrypted_key = bytes(a ^ b for a, b in zip(encrypted_key, private_key[:len(encrypted_key)]))
    
    return decrypted_key
