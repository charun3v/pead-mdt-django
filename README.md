# Paediatric Oncology MDT Web Application

Native Django web application for Multidisciplinary Tumor Board (MDT) meetings in Paediatric Oncology, migrated from a legacy Microsoft Access database with full clinical workflow fidelity.

## Features
- **Paediatric Patient Registration & Cockpit**: Demographic tracking, automated age calculation (years/months/days), state & district cascading lookups, mandatory pincode validation.
- **Clinical Presentation & Vitals**: Height, weight, presenting complaints, clinical exam, previous treatment history, and diagnostic staging.
- **Investigation Subforms**: 4 dedicated investigation modalities (Hematology/Biochemistry, Imaging/Radiology, Pathology/Histopathology, Molecular/Cytogenetics) with entry audit timestamps.
- **MDT Consensus & Tumor Board Workflow**: Sequential institutional MDT ID generation (`PEDYY00XXXXX`), chronological timeline, unified discussion memo, consensus recommendations, and follow-up actions.
- **Medicolegal Record Locking**: Once an MDT consensus is finalized and approved, both the clinical presentation and MDT records become permanently locked and uneditable.
- **Institutional PDF Reports**: Formatted print previews matching Kidwai Memorial Institute of Oncology standards (`rptClinicalSummary` and `rptMDTFull`).
- **User Management & RBAC**: Administrator, Consultant, Resident / Fellow, and Standard User roles with password management and access control.
- **Data Safety**: Full audit logging (`tblAuditLog`), single-click external database backup (JSON export), and atomic database restore/import.

## Tech Stack
- **Framework**: Django 4.2 LTS (Python 3.8+)
- **Database**: SQLite (default fallback) / PostgreSQL (production ready)
- **UI Theme**: Responsive classic clinical desktop theme replicating MS Access styling

## Quick Start

### 1. Clone repository
```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

### 2. Set up virtual environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run migrations & load initial lookups
```bash
python manage.py migrate
python manage.py load_access_data
```

### 5. Launch development server
```bash
python manage.py runserver 127.0.0.1:8000
```
*(On Windows, you can also double-click `run_server.bat`)*

Access the application in your browser at `http://127.0.0.1:8000/`.

**Default Accounts**:
- Administrator: `admin` / `admin123`
- Clinician: `dr_oncologist` / `doctor123`
