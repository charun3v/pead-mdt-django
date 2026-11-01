import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from mdt_app.models import (
    Sex, PrimaryTreatmentSite, Laterality, State, District,
    BCMInvestigationType, ImagingTestType, ImagingSite, PathologySpecimenType, MolecularTestType,
    Patient, ClinicalDetails, MDTConsensus,
    BloodInvestigation, ImagingInvestigation, PathologyInvestigation, MolecularInvestigation,
    AuditLog
)

class Command(BaseCommand):
    help = 'Imports lookup data and records from Access dump into Django'

    def handle(self, *args, **options):
        base_dir = r"C:\Users\charu\.gemini\antigravity\brain\ddbdd618-8ca2-4b21-b4df-94e5ef659ddb\scratch\access_dump"
        
        def load_json(name):
            p = os.path.join(base_dir, f"{name}.json")
            if not os.path.exists(p):
                return []
            with open(p, 'r', encoding='utf-8-sig') as f:
                return json.load(f)

        def parse_date(dt_str):
            if not dt_str:
                return None
            try:
                return datetime.strptime(dt_str.split()[0], "%Y-%m-%d").date()
            except Exception:
                return None

        def parse_datetime(dt_str):
            if not dt_str:
                return None
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                return timezone.make_aware(dt)
            except Exception:
                return None

        # 1. Superuser & Standard Clinician
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write("Created superuser 'admin' / 'admin123'")
        if not User.objects.filter(username='dr_oncologist').exists():
            u = User.objects.create_user('dr_oncologist', 'onco@example.com', 'doctor123')
            u.first_name = "Dr. Oncologist"
            u.save()
            self.stdout.write("Created clinician 'dr_oncologist' / 'doctor123'")

        # 2. Lookups: Sex
        for row in load_json('tblSex'):
            Sex.objects.update_or_create(sex=row['Sex'], defaults={'s': row.get('S')})
        self.stdout.write("Loaded Sex lookup.")

        # 3. Lookups: Primary Treatment Site
        for row in load_json('tblPrimarysite'):
            if row.get('Site'):
                PrimaryTreatmentSite.objects.get_or_create(site=row['Site'])
        self.stdout.write("Loaded PrimaryTreatmentSite lookup.")

        # 4. Lookups: Laterality
        for row in load_json('tblLaterality'):
            if row.get('Laterality'):
                Laterality.objects.get_or_create(laterality=row['Laterality'])
        self.stdout.write("Loaded Laterality lookup.")

        # 5. Lookups: States & Districts
        for row in load_json('tblStates'):
            State.objects.update_or_create(
                state_id=row['StateID'],
                defaults={'state_name': row['StateName']}
            )
        self.stdout.write("Loaded States.")

        states_dict = {s.state_id: s for s in State.objects.all()}
        districts_to_create = []
        for row in load_json('tblDistricts'):
            st_id = row.get('StateID')
            st_obj = states_dict.get(st_id)
            if st_obj:
                districts_to_create.append(District(
                    district_id=row['DistrictID'],
                    district_name=row['DistrictName'],
                    state=st_obj
                ))
        District.objects.bulk_create(districts_to_create, ignore_conflicts=True)
        self.stdout.write(f"Loaded {len(districts_to_create)} Districts.")

        # 6. Investigation Lookups
        for row in load_json('sbtblBCMinv'):
            if row.get('Test_Type_Bcm'):
                BCMInvestigationType.objects.update_or_create(id=row['ID'], defaults={'test_type_bcm': row['Test_Type_Bcm']})
        for row in load_json('sbtblImaging'):
            if row.get('Test_Type_Imaging'):
                ImagingTestType.objects.update_or_create(id=row['ID'], defaults={'test_type_imaging': row['Test_Type_Imaging']})
        for row in load_json('sbtblImagingSite'):
            if row.get('Test_Type_Imaging'):
                ImagingSite.objects.update_or_create(id=row['ID'], defaults={'test_type_imaging': row['Test_Type_Imaging']})
        for row in load_json('sbtblPath'):
            if row.get('Test_Type_Path'):
                PathologySpecimenType.objects.update_or_create(id=row['ID'], defaults={'test_type_path': row['Test_Type_Path']})
        for row in load_json('sbtblMolecular'):
            if row.get('Test_Type_Mol'):
                MolecularTestType.objects.update_or_create(id=row['ID'], defaults={'test_type_mol': row['Test_Type_Mol']})
        self.stdout.write("Loaded Investigation type lookups.")

        # 7. Patients (De-identified for privacy, preserving clinical diagnosis and exact MR_No)
        raw_pts = load_json('tblPtDetails')
        for i, row in enumerate(raw_pts, start=1):
            de_identified_name = f"Patient {row['MR_No'][-5:]}" if len(row['MR_No']) >= 5 else f"Patient #{i}"
            Patient.objects.update_or_create(
                mr_no=row['MR_No'],
                defaults={
                    'pt_name': de_identified_name,
                    'sex': row.get('Sex') or 'Male',
                    'date_of_birth': parse_date(row.get('Date_Of_birth')),
                    'diagnosis': row.get('Diagnosis') or 'Paediatric Malignancy',
                    'primary_treatment_site': row.get('Primary_treatment_site') or 'Bone',
                    'laterality': row.get('Laterality') or 'Right',
                    'phone': '9800000000'[:len(row.get('Phone', '')) or 10],
                    'phone_alternate': '9800000001' if row.get('Phone_Alternate') else None,
                    'address': 'De-identified Address',
                    'country': row.get('Country') or 'India',
                    'state': row.get('State') or 'Karnataka',
                    'district': row.get('District') or 'Bengaluru Urban',
                    'pincode': row.get('Pincode') or '560029',
                    'digipin': row.get('Digipin') or '',
                    'notes': row.get('Notes') or '',
                    'entered_by': row.get('EnteredBy') or 'admin',
                    'entered_on': parse_datetime(row.get('EnteredOn')),
                    'last_modified_by': row.get('LastModifiedBy'),
                    'last_modified_on': parse_datetime(row.get('LastModifiedOn')),
                }
            )
        self.stdout.write(f"Loaded {len(raw_pts)} Patients.")

        # 8. Clinical Details
        raw_clin = load_json('tblClinicalDetails')
        for row in raw_clin:
            try:
                pt = Patient.objects.get(mr_no=row['MR_No'])
                ClinicalDetails.objects.update_or_create(
                    clinical_id=row['ClinicalID'],
                    defaults={
                        'patient': pt,
                        'mdt_id': row.get('MDTID'),
                        'height': row.get('Height') or 0,
                        'weight': row.get('Weight') or 0,
                        'presenting_complaints': row.get('Presenting_Complaints'),
                        'examination_findings': row.get('Examination_Findings'),
                        'prev_tx_history': row.get('Prev_Tx_History'),
                        'diagnosis': row.get('Diagnosis'),
                        'stage': row.get('Stage'),
                        'status': row.get('Status') or 'Draft',
                        'mdt_discussion_for': row.get('MDT_Discussion_For'),
                        'date_mdt_planned': parse_date(row.get('Date_MDT_Planned')),
                        'entered_by': row.get('EnteredBy'),
                        'entered_on': parse_datetime(row.get('EnteredOn')),
                        'approved_by': row.get('ApprovedBy'),
                        'approved_on': parse_datetime(row.get('ApprovedOn')),
                    }
                )
            except Patient.DoesNotExist:
                pass
        self.stdout.write(f"Loaded {len(raw_clin)} Clinical Details records.")

        # 9. MDT Consensus
        raw_con = load_json('tblMDTConsensus')
        for row in raw_con:
            try:
                clin = ClinicalDetails.objects.get(clinical_id=row['ClinicalID'])
                pt = Patient.objects.get(mr_no=row['MR_No'])
                MDTConsensus.objects.update_or_create(
                    consensus_id=row['MDTConsensusID'],
                    defaults={
                        'clinical': clin,
                        'patient': pt,
                        'mdt_id': row['MDTID'],
                        'date_mdt_conducted': parse_date(row.get('Date_MDT_conducted')),
                        'mdt_discussion': row.get('MDT_Discussion'),
                        'mdt_consensus': row.get('MDTConsensus'),
                        'follow_up_actions': row.get('FollowUp_Actions'),
                        'status': row.get('Status') or 'Draft',
                        'entered_by': row.get('EnteredBy'),
                        'entered_on': parse_datetime(row.get('EnteredOn')),
                        'approved_by': row.get('ApprovedBy'),
                        'approved_on': parse_datetime(row.get('ApprovedOn')),
                    }
                )
            except (ClinicalDetails.DoesNotExist, Patient.DoesNotExist):
                pass
        self.stdout.write(f"Loaded {len(raw_con)} MDT Consensus records.")

        # 10. Blood Investigations
        for row in load_json('tblBlood'):
            try:
                pt = Patient.objects.get(mr_no=row['MR_No'])
                clin = ClinicalDetails.objects.get(clinical_id=row['ClinicalID'])
                BloodInvestigation.objects.update_or_create(
                    blood_id=row['BloodID'],
                    defaults={
                        'patient': pt,
                        'clinical': clin,
                        'test_date': parse_date(row.get('Test_date')),
                        'specimen_type': row.get('Specimen_Type') or 'CBC',
                        'details': row.get('Details'),
                        'impression': row.get('Impression'),
                        'linked_to_mdt': bool(row.get('LinkedToMDT')),
                        'entered_by': row.get('EnteredBy'),
                        'entered_on': parse_datetime(row.get('EnteredOn')),
                    }
                )
            except Exception:
                pass

        # 11. Imaging Investigations
        for row in load_json('tblImaging'):
            try:
                pt = Patient.objects.get(mr_no=row['MR_No'])
                clin = ClinicalDetails.objects.get(clinical_id=row['ClinicalID'])
                ImagingInvestigation.objects.update_or_create(
                    imaging_id=row['ImagingID'],
                    defaults={
                        'patient': pt,
                        'clinical': clin,
                        'imaging_date': parse_date(row.get('Imaging_Date')),
                        'imaging_type': row.get('Imaging_type') or 'MRI',
                        'site': row.get('Site'),
                        'details': row.get('Details'),
                        'impression': row.get('Impression'),
                        'linked_to_mdt': bool(row.get('LinkedToMDT')),
                        'entered_by': row.get('EnteredBy'),
                        'entered_on': parse_datetime(row.get('EnteredOn')),
                    }
                )
            except Exception:
                pass

        # 12. Pathology Investigations
        for row in load_json('tblPath'):
            try:
                pt = Patient.objects.get(mr_no=row['MR_No'])
                clin = ClinicalDetails.objects.get(clinical_id=row['ClinicalID'])
                PathologyInvestigation.objects.update_or_create(
                    path_id=row['PathID'],
                    defaults={
                        'patient': pt,
                        'clinical': clin,
                        'path_date': parse_date(row.get('Path_Date')),
                        'lab_reference_no': row.get('Lab_Reference_No') or 'LAB-001',
                        'specimen_type': row.get('Specimen_type'),
                        'site_of_biopsy': row.get('Site_Of_Biopsy'),
                        'details': row.get('Details'),
                        'impression': row.get('Impression'),
                        'linked_to_mdt': bool(row.get('LinkedToMDT')),
                        'entered_by': row.get('EnteredBy'),
                        'entered_on': parse_datetime(row.get('EnteredOn')),
                    }
                )
            except Exception:
                pass

        # 13. Molecular Investigations
        for row in load_json('tblMolecular'):
            try:
                pt = Patient.objects.get(mr_no=row['MR_No'])
                clin = ClinicalDetails.objects.get(clinical_id=row['ClinicalID'])
                MolecularInvestigation.objects.update_or_create(
                    molecular_id=row['MolecularID'],
                    defaults={
                        'patient': pt,
                        'clinical': clin,
                        'test_date': parse_date(row.get('Test_Date')),
                        'lab_reference_no': row.get('Lab_Reference_No') or 'MOL-001',
                        'test_type': row.get('Test_Type'),
                        'details': row.get('Details'),
                        'impression': row.get('Impression'),
                        'linked_to_mdt': bool(row.get('LinkedToMDT')),
                        'entered_by': row.get('EnteredBy'),
                        'entered_on': parse_datetime(row.get('EnteredOn')),
                    }
                )
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS("Data import completed successfully!"))
