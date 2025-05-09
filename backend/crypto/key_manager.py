"""
Key management module for the healthcare data sharing application.
Handles secure storage, retrieval, and generation of cryptographic keys.
"""

import os
import base64
import hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

class KeyManager:
    """Secure key management system for handling cryptographic keys"""
    
    def __init__(self):
        self.key_store = {}
        self.public_key_store = {}
        self.symmetric_key_store = {}
        
    def initialize_keys(self, addresses):
        """Initialize keys for all provided addresses
        
        Args:
            addresses: Dictionary mapping role names to wallet addresses
        """
        # Create secure keys directory if it doesn't exist
        os.makedirs("secure_keys", exist_ok=True)
        
        # Initialize keys for each role
        for role, address in addresses.items():
            self._initialize_role_keys(role, address)
            
        print("Key initialization complete")
    
    def _initialize_role_keys(self, role, address):
        """Initialize keys for a specific role
        
        Args:
            role: Role name (e.g., "patient", "doctor")
            address: Wallet address for the role
        """
        key_file = f"secure_keys/{role}_{address}.pem"
        pub_key_file = f"secure_keys/{role}_{address}_pub.pem"
        
        if os.path.exists(key_file) and os.path.exists(pub_key_file):
            # Load existing keys
            try:
                with open(key_file, "rb") as f:
                    private_key_data = f.read()
                    private_key = serialization.load_pem_private_key(
                        private_key_data,
                        password=None,
                        backend=default_backend()
                    )
                
                with open(pub_key_file, "rb") as f:
                    public_key_data = f.read()
                    public_key = serialization.load_pem_public_key(
                        public_key_data,
                        backend=default_backend()
                    )
                
                # Store in memory
                self.key_store[address] = private_key
                self.public_key_store[address] = public_key
                
                # Generate and store symmetric key
                self._generate_symmetric_key(address)
                
                print(f"Loaded keys for {role} ({address})")
            except Exception as e:
                print(f"Error loading keys for {role}: {str(e)}")
                # Generate new keys if loading fails
                self._generate_and_save_keys(role, address)
        else:
            # Generate new keys
            self._generate_and_save_keys(role, address)
    
    def _generate_and_save_keys(self, role, address):
        """Generate and save new keys for a role
        
        Args:
            role: Role name (e.g., "patient", "doctor")
            address: Wallet address for the role
        """
        private_key, public_key = self._generate_rsa_key_pair()
        
        # Save private key
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(f"secure_keys/{role}_{address}.pem", "wb") as f:
            f.write(private_key_pem)
        
        # Save public key
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        with open(f"secure_keys/{role}_{address}_pub.pem", "wb") as f:
            f.write(public_key_pem)
        
        # Store in memory
        self.key_store[address] = private_key
        self.public_key_store[address] = public_key
        
        # Generate and store symmetric key
        self._generate_symmetric_key(address)
        
        print(f"Generated and saved new keys for {role} ({address})")
    
    def _generate_rsa_key_pair(self):
        """Generate an RSA key pair
        
        Returns:
            tuple: (private_key, public_key)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        return private_key, public_key
    
    def _generate_symmetric_key(self, address):
        """Generate a symmetric key for an address
        
        Args:
            address: Wallet address
            
        Returns:
            bytes: 32-byte symmetric key
        """
        # In a real implementation, this would use a secure key derivation function
        # For now, we'll derive it from the private key
        private_key = self.key_store[address]
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        # Use SHA-256 to derive a symmetric key
        symmetric_key = hashlib.sha256(private_key_bytes).digest()
        self.symmetric_key_store[address] = symmetric_key
        return symmetric_key
    
    def get_private_key(self, address):
        """Get the private key for an address
        
        Args:
            address: Wallet address
            
        Returns:
            RSAPrivateKey: Private key for the address
        """
        if address in self.key_store:
            return self.key_store[address]
        else:
            print(f"Warning: No private key found for {address}. Generating temporary key.")
            private_key, public_key = self._generate_rsa_key_pair()
            self.key_store[address] = private_key
            self.public_key_store[address] = public_key
            self._generate_symmetric_key(address)
            return private_key
    
    def get_public_key(self, address):
        """Get the public key for an address
        
        Args:
            address: Wallet address
            
        Returns:
            RSAPublicKey: Public key for the address
        """
        if address in self.public_key_store:
            return self.public_key_store[address]
        else:
            print(f"Warning: No public key found for {address}. Generating temporary key.")
            private_key, public_key = self._generate_rsa_key_pair()
            self.key_store[address] = private_key
            self.public_key_store[address] = public_key
            self._generate_symmetric_key(address)
            return public_key
    
    def get_symmetric_key(self, address):
        """Get the symmetric key for an address
        
        Args:
            address: Wallet address
            
        Returns:
            bytes: 32-byte symmetric key for the address
        """
        if address in self.symmetric_key_store:
            return self.symmetric_key_store[address]
        elif address in self.key_store:
            return self._generate_symmetric_key(address)
        else:
            print(f"Warning: No keys found for {address}. Generating temporary keys.")
            private_key, public_key = self._generate_rsa_key_pair()
            self.key_store[address] = private_key
            self.public_key_store[address] = public_key
            return self._generate_symmetric_key(address)
    
    def encrypt_with_public_key(self, data, address=None, public_key=None):
        """Encrypt data with a public key using RSA-OAEP
        
        Args:
            data: Data to encrypt (bytes or string)
            address: Address to use for encryption (optional)
            public_key: Public key to use for encryption (optional)
            
        Returns:
            bytes: Encrypted data
            
        Note:
            Either address or public_key must be provided
        """
        if not public_key and not address:
            raise ValueError("Either address or public_key must be provided")
        
        if not public_key:
            public_key = self.get_public_key(address)
        
        if isinstance(data, str):
            data = data.encode()
        elif not isinstance(data, bytes):
            raise ValueError(f"Data must be bytes or string, got {type(data)}")
        
        ciphertext = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext
    
    def decrypt_with_private_key(self, data, address=None, private_key=None):
        """Decrypt data with a private key using RSA-OAEP
        
        Args:
            data: Encrypted data (bytes)
            address: Address to use for decryption (optional)
            private_key: Private key to use for decryption (optional)
            
        Returns:
            bytes: Decrypted data
            
        Note:
            Either address or private_key must be provided
        """
        if not private_key and not address:
            raise ValueError("Either address or private_key must be provided")
        
        if not private_key:
            private_key = self.get_private_key(address)
        
        if not isinstance(data, bytes):
            raise ValueError(f"Data must be bytes, got {type(data)}")
        
        plaintext = private_key.decrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext
    
    def encrypt_eid(self, hospital_info, patient_key, group_manager_address):
        """Encrypt hospital info and patient key with the Group Manager's public key
        
        Args:
            hospital_info: Hospital information (string)
            patient_key: Patient's symmetric key (bytes)
            group_manager_address: Group Manager's wallet address
            
        Returns:
            bytes: Encrypted eId
        """
        # Combine hospital info and patient key
        combined = f"{hospital_info}||{base64.b64encode(patient_key).decode()}"
        
        # Encrypt with Group Manager's public key
        group_manager_public_key = self.get_public_key(group_manager_address)
        return self.encrypt_with_public_key(combined, public_key=group_manager_public_key)
    
    def decrypt_eid(self, encrypted_eid, group_manager_address):
        """Decrypt eId with the Group Manager's private key
        
        Args:
            encrypted_eid: Encrypted eId (bytes)
            group_manager_address: Group Manager's wallet address
            
        Returns:
            tuple: (hospital_info, patient_key)
        """
        # Decrypt with Group Manager's private key
        group_manager_private_key = self.get_private_key(group_manager_address)
        decrypted = self.decrypt_with_private_key(encrypted_eid, private_key=group_manager_private_key)
        
        # Split into hospital info and patient key
        hospital_info, patient_key_b64 = decrypted.decode().split('||')
        patient_key = base64.b64decode(patient_key_b64)
        
        return hospital_info, patient_key

# Create a singleton instance
_instance = None

def get_instance():
    """Get the singleton instance of KeyManager
    
    Returns:
        KeyManager: Singleton instance
    """
    global _instance
    if _instance is None:
        _instance = KeyManager()
    return _instance
