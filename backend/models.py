from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import datetime

class RecordData(BaseModel):
    """Model for patient health record data"""
    patientID: str
    date: str
    diagnosis: str
    doctorID: str
    notes: str

class RecordMetadata(BaseModel):
    """Model for record metadata stored on-chain"""
    cid: str
    merkle_root: str
    signature: str
    owner: str
    timestamp: Optional[datetime.datetime] = None

class CertStructure(BaseModel):
    """CERT structure as defined in the blueprint"""
    sig: str  # 362-byte group signature (hex)
    eId: str  # PCS(hospitalInfo || K_patient)

class ShareRequest(BaseModel):
    """Model for record sharing request"""
    record_cid: str
    doctor_address: str
    wallet_address: str

class ShareResponse(BaseModel):
    """Model for record sharing response"""
    shared_cid: str
    encrypted_key: str

class PurchaseRequest(BaseModel):
    """Model for data purchase request"""
    template_hash: str
    amount: float
    wallet_address: str

class PurchaseRequestResponse(BaseModel):
    """Model for data purchase request response"""
    request_id: str
    transaction_hash: str

class PurchaseReply(BaseModel):
    """Model for reply to purchase request"""
    request_id: str
    template_cid: str
    wallet_address: str

class PurchaseFinalize(BaseModel):
    """Model for finalizing a purchase"""
    request_id: str
    approved: bool
    recipients: List[str]
    wallet_address: str
