#!/usr/bin/env python3
"""
Generate test medical records for a patient.

This script creates a large number of medical records with varied data
for testing the purchasing workflow.
"""

import os
import sys
import json
import time
import random
import argparse
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path to import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Constants
API_URL = os.getenv("API_URL", "http://localhost:8000")
DOCTOR_ADDRESS = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # Default doctor address

# Medical categories
CATEGORIES = [
    "Cardiology",
    "Oncology",
    "Neurology",
    "Pediatrics",
    "General",
    "Orthopedics",
    "Dermatology",
    "Gastroenterology",
    "Endocrinology",
    "Pulmonology"
]

# Demographics data
GENDERS = ["Male", "Female", "Other"]
LOCATIONS = [
    "New York, USA",
    "London, UK",
    "Tokyo, Japan",
    "Berlin, Germany",
    "Sydney, Australia",
    "Toronto, Canada",
    "Paris, France",
    "Mumbai, India",
    "São Paulo, Brazil",
    "Cape Town, South Africa"
]
ETHNICITIES = [
    "Caucasian",
    "African American",
    "Hispanic",
    "Asian",
    "Middle Eastern",
    "Pacific Islander",
    "Native American",
    "Mixed"
]

# Medical data
DIAGNOSES = {
    "Cardiology": [
        "Hypertension",
        "Coronary Artery Disease",
        "Atrial Fibrillation",
        "Heart Failure",
        "Valve Disease"
    ],
    "Oncology": [
        "Breast Cancer",
        "Lung Cancer",
        "Prostate Cancer",
        "Leukemia",
        "Lymphoma"
    ],
    "Neurology": [
        "Migraine",
        "Epilepsy",
        "Multiple Sclerosis",
        "Parkinson's Disease",
        "Alzheimer's Disease"
    ],
    "Pediatrics": [
        "Asthma",
        "ADHD",
        "Ear Infection",
        "Chickenpox",
        "Growth Disorder"
    ],
    "General": [
        "Common Cold",
        "Influenza",
        "Diabetes Type 2",
        "Hypertension",
        "Obesity"
    ],
    "Orthopedics": [
        "Fracture",
        "Osteoarthritis",
        "Scoliosis",
        "Tendonitis",
        "Carpal Tunnel Syndrome"
    ],
    "Dermatology": [
        "Eczema",
        "Psoriasis",
        "Acne",
        "Melanoma",
        "Dermatitis"
    ],
    "Gastroenterology": [
        "GERD",
        "Irritable Bowel Syndrome",
        "Crohn's Disease",
        "Ulcerative Colitis",
        "Gallstones"
    ],
    "Endocrinology": [
        "Diabetes Type 1",
        "Hypothyroidism",
        "Hyperthyroidism",
        "Cushing's Syndrome",
        "Addison's Disease"
    ],
    "Pulmonology": [
        "Asthma",
        "COPD",
        "Pneumonia",
        "Pulmonary Fibrosis",
        "Sleep Apnea"
    ]
}

TREATMENTS = {
    "Cardiology": [
        "Beta Blockers",
        "ACE Inhibitors",
        "Anticoagulants",
        "Stent Placement",
        "Bypass Surgery"
    ],
    "Oncology": [
        "Chemotherapy",
        "Radiation Therapy",
        "Immunotherapy",
        "Targeted Therapy",
        "Surgery"
    ],
    "Neurology": [
        "Anti-seizure Medication",
        "Pain Management",
        "Disease-modifying Therapy",
        "Deep Brain Stimulation",
        "Cognitive Therapy"
    ],
    "Pediatrics": [
        "Antibiotics",
        "Inhalers",
        "Behavioral Therapy",
        "Growth Hormone",
        "Vaccination"
    ],
    "General": [
        "Rest and Fluids",
        "Antiviral Medication",
        "Insulin Therapy",
        "Lifestyle Modification",
        "Diet and Exercise"
    ],
    "Orthopedics": [
        "Cast Application",
        "Physical Therapy",
        "Joint Replacement",
        "Corticosteroid Injection",
        "Splinting"
    ],
    "Dermatology": [
        "Topical Steroids",
        "Antibiotics",
        "Retinoids",
        "Excision",
        "Phototherapy"
    ],
    "Gastroenterology": [
        "Proton Pump Inhibitors",
        "Dietary Changes",
        "Immunosuppressants",
        "Antibiotics",
        "Cholecystectomy"
    ],
    "Endocrinology": [
        "Insulin Therapy",
        "Hormone Replacement",
        "Antithyroid Medication",
        "Corticosteroids",
        "Surgery"
    ],
    "Pulmonology": [
        "Bronchodilators",
        "Inhaled Corticosteroids",
        "Antibiotics",
        "Oxygen Therapy",
        "CPAP"
    ]
}

MEDICATIONS_TEMPLATES = {
    "Cardiology": "- {0} {1}mg daily\n- {2} {3}mg twice daily\n- Low-dose aspirin",
    "Oncology": "- {0} {1}mg/m²\n- Anti-nausea medication\n- {2} for pain management",
    "Neurology": "- {0} {1}mg daily\n- {2} {3}mg as needed for pain\n- Vitamin D supplement",
    "Pediatrics": "- {0} {1}mg/kg every 8 hours\n- {2} as needed\n- Multivitamin daily",
    "General": "- {0} {1}mg daily\n- {2} {3}mg as needed\n- Vitamin supplements",
    "Orthopedics": "- {0} {1}mg for pain\n- Calcium {2}mg daily\n- Vitamin D {3}IU daily",
    "Dermatology": "- {0} cream applied twice daily\n- {1} {2}mg daily\n- Moisturizer as needed",
    "Gastroenterology": "- {0} {1}mg before meals\n- {2} fiber supplement\n- Probiotic daily",
    "Endocrinology": "- {0} {1}mg daily\n- {2} {3}mcg daily\n- Calcium supplement",
    "Pulmonology": "- {0} inhaler {1} puffs twice daily\n- {2} {3}mg daily\n- Nasal spray as needed"
}

LAB_RESULTS_TEMPLATES = {
    "Cardiology": "Blood Pressure: {0}/{1} mmHg\nHeart Rate: {2} bpm\nCholesterol: {3} mg/dL\nTriglycerides: {4} mg/dL",
    "Oncology": "White Blood Cell Count: {0} x10^9/L\nRed Blood Cell Count: {1} x10^12/L\nPlatelet Count: {2} x10^9/L\nTumor Markers: {3}",
    "Neurology": "EEG: {0}\nMRI: {1}\nCSF Analysis: {2}\nNerve Conduction: {3}",
    "Pediatrics": "Height: {0} cm ({1} percentile)\nWeight: {2} kg ({3} percentile)\nHead Circumference: {4} cm",
    "General": "Blood Pressure: {0}/{1} mmHg\nHeart Rate: {2} bpm\nTemperature: {3}°C\nO2 Saturation: {4}%",
    "Orthopedics": "X-Ray: {0}\nBone Density: {1} g/cm²\nRange of Motion: {2}°\nStrength Test: {3}/5",
    "Dermatology": "Skin Biopsy: {0}\nAllergy Test: {1}\nPatch Test: {2}\nDermatoscopy: {3}",
    "Gastroenterology": "Liver Function: ALT {0} U/L, AST {1} U/L\nEndoscopy: {2}\nH. pylori Test: {3}\nStool Analysis: {4}",
    "Endocrinology": "TSH: {0} mIU/L\nT4: {1} ng/dL\nGlucose: {2} mg/dL\nHbA1c: {3}%\nCortisol: {4} μg/dL",
    "Pulmonology": "Spirometry: FEV1 {0}%, FVC {1}%\nO2 Saturation: {2}%\nArterial Blood Gas: pH {3}, pO2 {4} mmHg"
}

NOTES_TEMPLATES = [
    "Patient is responding well to treatment. Follow-up in {0} weeks.",
    "Patient reports {0} improvement in symptoms. Continuing current treatment plan.",
    "Discussed lifestyle modifications. Patient is {0} compliant with recommendations.",
    "Patient experienced side effects including {0}. Adjusting medication dosage.",
    "Referred to specialist for {0}. Patient to follow up after consultation.",
    "Patient reports no significant changes since last visit. Monitoring condition.",
    "Treatment shows {0} effectiveness. Considering alternative approaches.",
    "Patient missed {0} doses of medication. Emphasized importance of adherence.",
    "Symptoms have {0} since last visit. Adjusting treatment accordingly.",
    "Patient reports new symptoms including {0}. Additional testing ordered."
]

# Hospital information
HOSPITALS = [
    "General Hospital",
    "University Medical Center",
    "Memorial Hospital",
    "Community Health Center",
    "Regional Medical Center"
]

def generate_random_record(patient_address, doctor_address):
    """Generate a random medical record with detailed structure."""
    # Select a random category
    category = random.choice(CATEGORIES)

    # Generate a random date within the last 3 years
    days_ago = random.randint(1, 1095)  # Up to 3 years
    record_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    # Generate demographics data
    age = random.randint(18, 85)
    gender = random.choice(GENDERS)
    location = random.choice(LOCATIONS)
    ethnicity = random.choice(ETHNICITIES)

    # Generate medical data
    diagnosis = random.choice(DIAGNOSES[category])
    treatment = random.choice(TREATMENTS[category])

    # Generate medications
    med_values = [
        random.choice(["Medication A", "Medication B", "Medication C", "Medication D"]),
        random.randint(5, 100),
        random.choice(["Medication X", "Medication Y", "Medication Z"]),
        random.randint(10, 200)
    ]
    medications = MEDICATIONS_TEMPLATES[category].format(*med_values)

    # Generate lab results
    lab_values = []
    if category == "Cardiology":
        lab_values = [
            random.randint(110, 180),  # Systolic BP
            random.randint(60, 110),   # Diastolic BP
            random.randint(60, 100),   # Heart rate
            random.randint(150, 300),  # Cholesterol
            random.randint(100, 300)   # Triglycerides
        ]
    elif category == "Oncology":
        lab_values = [
            round(random.uniform(3.5, 11.0), 1),  # WBC
            round(random.uniform(3.5, 5.5), 1),   # RBC
            random.randint(150, 450),             # Platelets
            random.choice(["Elevated", "Normal", "Borderline"])  # Tumor markers
        ]
    elif category == "Neurology":
        lab_values = [
            random.choice(["Normal", "Abnormal - showing seizure activity", "Mildly abnormal"]),
            random.choice(["No abnormalities", "Small lesion detected", "Evidence of inflammation"]),
            random.choice(["Normal", "Elevated protein", "Elevated white cells"]),
            random.choice(["Normal", "Delayed conduction", "Reduced amplitude"])
        ]
    elif category == "Pediatrics":
        lab_values = [
            random.randint(80, 150),   # Height
            random.randint(10, 90),    # Height percentile
            random.randint(10, 50),    # Weight
            random.randint(10, 90),    # Weight percentile
            random.randint(40, 55)     # Head circumference
        ]
    elif category == "General":
        lab_values = [
            random.randint(110, 180),  # Systolic BP
            random.randint(60, 110),   # Diastolic BP
            random.randint(60, 100),   # Heart rate
            round(random.uniform(36.0, 38.5), 1),  # Temperature
            random.randint(94, 100)    # O2 Saturation
        ]
    elif category == "Orthopedics":
        lab_values = [
            random.choice(["Normal alignment", "Fracture visible", "Degenerative changes", "Joint effusion"]),
            round(random.uniform(0.8, 1.5), 2),  # Bone density
            random.randint(30, 180),  # Range of motion
            random.choice(["3", "4", "5"])  # Strength test
        ]
    elif category == "Dermatology":
        lab_values = [
            random.choice(["Benign", "Inflammatory", "Pre-malignant", "Malignant"]),
            random.choice(["Positive for allergens", "Negative", "Mild reaction"]),
            random.choice(["Positive", "Negative", "Inconclusive"]),
            random.choice(["Normal pattern", "Atypical pattern", "Suspicious features"])
        ]
    elif category == "Gastroenterology":
        lab_values = [
            random.randint(10, 100),  # ALT
            random.randint(10, 100),  # AST
            random.choice(["Normal", "Inflammation", "Ulceration", "Polyps"]),
            random.choice(["Positive", "Negative"]),
            random.choice(["Normal", "Abnormal", "Presence of blood", "Parasites detected"])
        ]
    elif category == "Endocrinology":
        lab_values = [
            round(random.uniform(0.4, 5.0), 2),  # TSH
            round(random.uniform(0.8, 2.0), 2),  # T4
            random.randint(70, 200),  # Glucose
            round(random.uniform(4.0, 10.0), 1),  # HbA1c
            round(random.uniform(5.0, 25.0), 1)  # Cortisol
        ]
    elif category == "Pulmonology":
        lab_values = [
            random.randint(60, 120),  # FEV1
            random.randint(60, 120),  # FVC
            random.randint(90, 100),  # O2 Saturation
            round(random.uniform(7.35, 7.45), 2),  # pH
            random.randint(80, 100)  # pO2
        ]

    lab_results = LAB_RESULTS_TEMPLATES[category].format(*lab_values)

    # Generate notes
    notes_values = [
        random.choice(["4", "6", "8", "12"]),  # Weeks for follow-up
        random.choice(["significant", "moderate", "slight", "no"]),  # Improvement
        random.choice(["highly", "moderately", "partially", "not"]),  # Compliance
        random.choice(["nausea", "dizziness", "fatigue", "headache"]),  # Side effects
        random.choice(["further evaluation", "second opinion", "advanced testing"])  # Referral reason
    ]
    notes = random.choice(NOTES_TEMPLATES).format(random.choice(notes_values))

    # Generate hospital info
    hospital_info = random.choice(HOSPITALS)

    # Create the record
    record = {
        "patientID": patient_address,  # Main patient identifier
        "patientId": patient_address,  # Alternative spelling for compatibility
        "doctorID": doctor_address,
        "date": record_date,
        "category": category,
        "hospitalInfo": hospital_info,
        "demographics": {
            "age": age,
            "gender": gender,
            "location": location,
            "ethnicity": ethnicity
        },
        "medical_data": {
            "diagnosis": diagnosis,
            "treatment": treatment,
            "medications": medications,
            "lab_results": lab_results
        },
        "notes": notes
    }

    return record

def create_and_store_record(record, index, total, max_retries=3):
    """Sign, encrypt, and store a record using the API."""
    for attempt in range(max_retries):
        try:
            # Step 1: Sign the record
            print(f"[{index}/{total}] Signing record... (attempt {attempt+1}/{max_retries})")

            # Try both API endpoints
            sign_endpoints = [
                f"{API_URL}/api/records/sign",
                f"{API_URL}/records/sign"
            ]

            sign_response = None
            for endpoint in sign_endpoints:
                try:
                    sign_response = requests.post(endpoint, json=record, timeout=10)
                    if sign_response.status_code == 200:
                        break
                    print(f"Endpoint {endpoint} returned {sign_response.status_code}")
                except Exception as e:
                    print(f"Error with endpoint {endpoint}: {str(e)}")

            if sign_response is None or sign_response.status_code != 200:
                error_text = sign_response.text if sign_response else "No response"
                print(f"Error signing record: {error_text}")
                if attempt < max_retries - 1:
                    print(f"Retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                return False

            signed_data = sign_response.json()

            # Step 2: Store the record
            print(f"[{index}/{total}] Storing record... (attempt {attempt+1}/{max_retries})")

            # Try both API endpoints
            store_endpoints = [
                f"{API_URL}/api/records/store",
                f"{API_URL}/records/store"
            ]

            store_data = {
                "record": signed_data['record'],
                "signature": signed_data['signature'],
                "merkleRoot": signed_data['merkleRoot'],
                "patientAddress": record["patientID"],
                "patientId": record["patientID"],  # Alternative spelling for compatibility
                "hospitalInfo": record["hospitalInfo"]
            }

            store_response = None
            for endpoint in store_endpoints:
                try:
                    store_response = requests.post(endpoint, json=store_data, timeout=10)
                    if store_response.status_code == 200:
                        break
                    print(f"Endpoint {endpoint} returned {store_response.status_code}")
                except Exception as e:
                    print(f"Error with endpoint {endpoint}: {str(e)}")

            if store_response is None or store_response.status_code != 200:
                error_text = store_response.text if store_response else "No response"
                print(f"Error storing record: {error_text}")
                if attempt < max_retries - 1:
                    print(f"Retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                return False

            store_result = store_response.json()
            print(f"[{index}/{total}] Record created successfully! CID: {store_result['cid']}")
            return True

        except Exception as e:
            print(f"Error creating record: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in 2 seconds...")
                time.sleep(2)
            else:
                return False

    return False

def main():
    """Main function to generate and store records."""
    parser = argparse.ArgumentParser(description="Generate test medical records for a patient")
    parser.add_argument("--count", type=int, default=10, help="Number of records to generate")
    parser.add_argument("--patient", type=str, default="0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A",
                        help="Patient wallet address")
    parser.add_argument("--doctor", type=str, default=DOCTOR_ADDRESS,
                        help="Doctor wallet address")
    parser.add_argument("--output", type=str, help="Output file for records (optional)")
    parser.add_argument("--api", type=str, help="API URL (overrides .env)")
    parser.add_argument("--retries", type=int, default=3, help="Number of retries for API calls")

    args = parser.parse_args()

    # Override API_URL if specified in command line
    global API_URL
    if args.api:
        API_URL = args.api

    print(f"Using API URL: {API_URL}")

    print(f"Generating {args.count} medical records for patient {args.patient}")

    # Create output directory if needed
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    # Generate and store records
    records = []
    success_count = 0

    for i in range(1, args.count + 1):
        record = generate_random_record(args.patient, args.doctor)
        records.append(record)

        # Store the record via API
        if create_and_store_record(record, i, args.count, max_retries=args.retries):
            success_count += 1

        # Add a small delay to avoid overwhelming the API
        time.sleep(1.0)

    # Save records to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(records, f, indent=2)
        print(f"Saved {len(records)} records to {args.output}")

    print(f"Successfully created {success_count} out of {args.count} records")

if __name__ == "__main__":
    main()
