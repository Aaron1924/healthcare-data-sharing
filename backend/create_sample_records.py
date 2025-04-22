"""
Create sample records for Patient 1 to test the auto-fill template function.
"""

import os
import json
import time
import hashlib

# Constants
PATIENT_1_ADDRESS = "0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A"
DOCTOR_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

# Sample records
sample_records = [
    {
        "patientID": PATIENT_1_ADDRESS,
        "doctorID": DOCTOR_ADDRESS,
        "date": "2023-01-15",
        "category": "Cardiology",
        "hospitalInfo": "General Hospital",
        "demographics": {
            "age": 45,
            "gender": "Male",
            "location": "New York",
            "ethnicity": "Caucasian"
        },
        "medical_data": {
            "diagnosis": "Hypertension",
            "treatment": "Prescribed ACE inhibitors",
            "medications": "Lisinopril 10mg daily",
            "lab_results": "Blood pressure: 140/90 mmHg"
        },
        "notes": "Patient advised to reduce sodium intake and increase physical activity."
    },
    {
        "patientID": PATIENT_1_ADDRESS,
        "doctorID": DOCTOR_ADDRESS,
        "date": "2023-02-20",
        "category": "Cardiology",
        "hospitalInfo": "General Hospital",
        "demographics": {
            "age": 45,
            "gender": "Male",
            "location": "New York",
            "ethnicity": "Caucasian"
        },
        "medical_data": {
            "diagnosis": "Hypertension - Follow-up",
            "treatment": "Continue ACE inhibitors, add diuretic",
            "medications": "Lisinopril 10mg daily, Hydrochlorothiazide 12.5mg daily",
            "lab_results": "Blood pressure: 135/85 mmHg"
        },
        "notes": "Patient reports improved adherence to medication regimen."
    },
    {
        "patientID": PATIENT_1_ADDRESS,
        "doctorID": DOCTOR_ADDRESS,
        "date": "2023-03-25",
        "category": "General",
        "hospitalInfo": "General Hospital",
        "demographics": {
            "age": 45,
            "gender": "Male",
            "location": "New York",
            "ethnicity": "Caucasian"
        },
        "medical_data": {
            "diagnosis": "Annual physical examination",
            "treatment": "No treatment required",
            "medications": "Lisinopril 10mg daily, Hydrochlorothiazide 12.5mg daily",
            "lab_results": "Blood pressure: 130/80 mmHg, Cholesterol: 190 mg/dL"
        },
        "notes": "Patient in good health. Continue current medications."
    },
    {
        "patientID": PATIENT_1_ADDRESS,
        "doctorID": DOCTOR_ADDRESS,
        "date": "2023-04-10",
        "category": "Neurology",
        "hospitalInfo": "General Hospital",
        "demographics": {
            "age": 45,
            "gender": "Male",
            "location": "New York",
            "ethnicity": "Caucasian"
        },
        "medical_data": {
            "diagnosis": "Migraine",
            "treatment": "Prescribed sumatriptan for acute attacks",
            "medications": "Sumatriptan 50mg as needed",
            "lab_results": "MRI: Normal"
        },
        "notes": "Patient reports occasional migraines, typically triggered by stress."
    },
    {
        "patientID": PATIENT_1_ADDRESS,
        "doctorID": DOCTOR_ADDRESS,
        "date": "2023-05-05",
        "category": "Cardiology",
        "hospitalInfo": "General Hospital",
        "demographics": {
            "age": 45,
            "gender": "Male",
            "location": "New York",
            "ethnicity": "Caucasian"
        },
        "medical_data": {
            "diagnosis": "Hypertension - Follow-up",
            "treatment": "Continue current medications",
            "medications": "Lisinopril 10mg daily, Hydrochlorothiazide 12.5mg daily",
            "lab_results": "Blood pressure: 125/80 mmHg, ECG: Normal"
        },
        "notes": "Blood pressure well-controlled. Continue current regimen."
    },
    {
        "patientID": PATIENT_1_ADDRESS,
        "doctorID": DOCTOR_ADDRESS,
        "date": "2023-06-15",
        "category": "Oncology",
        "hospitalInfo": "General Hospital",
        "demographics": {
            "age": 45,
            "gender": "Male",
            "location": "New York",
            "ethnicity": "Caucasian"
        },
        "medical_data": {
            "diagnosis": "Routine cancer screening",
            "treatment": "No treatment required",
            "medications": "No new medications",
            "lab_results": "All screening tests negative"
        },
        "notes": "Routine cancer screening. No abnormalities detected."
    },
    {
        "patientID": PATIENT_1_ADDRESS,
        "doctorID": DOCTOR_ADDRESS,
        "date": "2023-07-20",
        "category": "Cardiology",
        "hospitalInfo": "General Hospital",
        "demographics": {
            "age": 45,
            "gender": "Male",
            "location": "New York",
            "ethnicity": "Caucasian"
        },
        "medical_data": {
            "diagnosis": "Hypertension - Follow-up",
            "treatment": "Continue current medications",
            "medications": "Lisinopril 10mg daily, Hydrochlorothiazide 12.5mg daily",
            "lab_results": "Blood pressure: 120/75 mmHg"
        },
        "notes": "Blood pressure well-controlled. Patient reports regular exercise."
    },
    {
        "patientID": PATIENT_1_ADDRESS,
        "doctorID": DOCTOR_ADDRESS,
        "date": "2023-08-10",
        "category": "Neurology",
        "hospitalInfo": "General Hospital",
        "demographics": {
            "age": 45,
            "gender": "Male",
            "location": "New York",
            "ethnicity": "Caucasian"
        },
        "medical_data": {
            "diagnosis": "Migraine - Follow-up",
            "treatment": "Continue sumatriptan as needed",
            "medications": "Sumatriptan 50mg as needed",
            "lab_results": "No new tests"
        },
        "notes": "Patient reports reduced frequency of migraines."
    },
    {
        "patientID": PATIENT_1_ADDRESS,
        "doctorID": DOCTOR_ADDRESS,
        "date": "2023-09-05",
        "category": "General",
        "hospitalInfo": "General Hospital",
        "demographics": {
            "age": 45,
            "gender": "Male",
            "location": "New York",
            "ethnicity": "Caucasian"
        },
        "medical_data": {
            "diagnosis": "Seasonal allergies",
            "treatment": "Prescribed antihistamine",
            "medications": "Cetirizine 10mg daily as needed",
            "lab_results": "No tests required"
        },
        "notes": "Patient experiencing seasonal allergies. Prescribed antihistamine."
    },
    {
        "patientID": PATIENT_1_ADDRESS,
        "doctorID": DOCTOR_ADDRESS,
        "date": "2023-10-15",
        "category": "Cardiology",
        "hospitalInfo": "General Hospital",
        "demographics": {
            "age": 45,
            "gender": "Male",
            "location": "New York",
            "ethnicity": "Caucasian"
        },
        "medical_data": {
            "diagnosis": "Hypertension - Follow-up",
            "treatment": "Continue current medications",
            "medications": "Lisinopril 10mg daily, Hydrochlorothiazide 12.5mg daily",
            "lab_results": "Blood pressure: 122/78 mmHg"
        },
        "notes": "Blood pressure remains well-controlled."
    }
]

def create_sample_records():
    """Create sample records for Patient 1."""
    # Create the records directory if it doesn't exist
    os.makedirs("local_storage/records", exist_ok=True)
    
    # Save each record to a file
    for i, record in enumerate(sample_records):
        # Generate a unique ID for the record
        record_id = hashlib.sha256(f"{PATIENT_1_ADDRESS}_{i}_{int(time.time())}".encode()).hexdigest()
        
        # Add the record ID to the record
        record["cid"] = record_id
        
        # Save the record to a file
        file_path = f"local_storage/records/{record_id}.json"
        with open(file_path, "w") as f:
            json.dump(record, f, indent=2)
        
        print(f"Created sample record {i+1}/{len(sample_records)}: {file_path}")

if __name__ == "__main__":
    create_sample_records()
    print(f"Created {len(sample_records)} sample records for Patient 1")
