# Test Data Generation Scripts

This directory contains scripts for generating test data for the healthcare data sharing application.

## Scripts Overview

- `generate_test_records.py`: Creates medical records for testing
- `generate_template.py`: Creates templates for purchase requests



### Command-line Arguments

- `--count`: Number of records to generate (default: 10)
- `--patient`: Patient wallet address (default: 0xEDB64f85F1fC9357EcA100C2970f7F84a5faAD4A)
- `--doctor`: Doctor wallet address (default: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8)
- `--output`: Output file for records (optional)
- `--api`: API URL (overrides the API_URL from .env file)
- `--retries`: Number of retries for API calls (default: 3)

### Generated Data

The script generates records with varied data across different medical categories:

- Cardiology
- Oncology
- Neurology
- Pediatrics
- General
- Orthopedics
- Dermatology
- Gastroenterology
- Endocrinology
- Pulmonology

Each record includes:

- Demographics (age, gender, location, ethnicity)
- Medical data (diagnosis, treatment, medications, lab results)
- Notes
- Hospital information

### Example

To generate 20 records for a test patient and save them to a file:

```bash
python scripts/generate_test_records.py --count 20 --output data/patient_records.json
```

This will:

1. Generate 20 random medical records
2. Sign each record with the doctor's group signature
3. Encrypt and store each record on IPFS
4. Save a copy of the records to `data/patient_records.json`

## Generate Template

The `generate_template.py` script creates a template for purchasing medical records. This template can be used to request records matching specific criteria.

### Template Usage

```bash
# Generate a basic template
python scripts/generate_template.py

# Generate a template for a specific category
python scripts/generate_template.py --category Cardiology

# Generate a template with multiple filters
python scripts/generate_template.py --category Oncology --diagnosis "Breast Cancer" --age 30-60 --gender Female

# Save the template to a file
python scripts/generate_template.py --category Neurology --output data/neurology_template.json
```

### Template Command-line Arguments

- `--category`: Medical category (e.g., Cardiology, Oncology)
- `--diagnosis`: Specific diagnosis to filter for
- `--age`: Age range (e.g., 18-65)
- `--gender`: Gender filter (Male, Female, Other)
- `--location`: Location filter (e.g., 'New York, USA')
- `--output`: Output file for template (optional)

### Example Workflow

1. Generate test records:

   ```bash
   python scripts/generate_test_records.py --count 100
   ```

2. Create a template to match some of those records:

   ```bash
   python scripts/generate_template.py --category Cardiology --age 40-70
   ```

3. Use the generated template hash in the Buyer interface to create a purchase request

4. Process the request through the Hospital and Buyer interfaces
