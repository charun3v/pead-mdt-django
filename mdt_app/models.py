from django.db import models
from django.utils import timezone
from datetime import date
from dateutil.relativedelta import relativedelta


# ==============================================================================
# REFERENCE & LOOKUP MODELS
# ==============================================================================

class Sex(models.Model):
    s = models.CharField(max_length=10, blank=True, null=True)
    sex = models.CharField(max_length=50, primary_key=True)

    class Meta:
        db_table = 'tblSex'
        verbose_name = 'Sex'
        verbose_name_plural = 'Sexes'

    def __str__(self):
        return self.sex


class PrimaryTreatmentSite(models.Model):
    site = models.CharField(max_length=255, primary_key=True)

    class Meta:
        db_table = 'tblPrimarysite'
        verbose_name = 'Primary Treatment Site'
        verbose_name_plural = 'Primary Treatment Sites'

    def __str__(self):
        return self.site


class Laterality(models.Model):
    laterality = models.CharField(max_length=255, primary_key=True)

    class Meta:
        db_table = 'tblLaterality'
        verbose_name = 'Laterality'
        verbose_name_plural = 'Lateralities'

    def __str__(self):
        return self.laterality


class State(models.Model):
    state_id = models.FloatField(primary_key=True, db_column='StateID')
    state_name = models.TextField(db_column='StateName')

    class Meta:
        db_table = 'tblStates'
        ordering = ['state_name']

    def __str__(self):
        return self.state_name


class District(models.Model):
    district_id = models.FloatField(primary_key=True, db_column='DistrictID')
    district_name = models.TextField(db_column='DistrictName')
    state = models.ForeignKey(State, on_delete=models.CASCADE, db_column='StateID', related_name='districts')

    class Meta:
        db_table = 'tblDistricts'
        ordering = ['district_name']

    def __str__(self):
        return self.district_name


class BCMInvestigationType(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    test_type_bcm = models.CharField(max_length=255, db_column='Test_Type_Bcm')

    class Meta:
        db_table = 'sbtblBCMinv'
        ordering = ['test_type_bcm']

    def __str__(self):
        return self.test_type_bcm


class ImagingTestType(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    test_type_imaging = models.CharField(max_length=255, db_column='Test_Type_Imaging')

    class Meta:
        db_table = 'sbtblImaging'
        ordering = ['test_type_imaging']

    def __str__(self):
        return self.test_type_imaging


class ImagingSite(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    test_type_imaging = models.CharField(max_length=255, db_column='Test_Type_Imaging')

    class Meta:
        db_table = 'sbtblImagingSite'
        ordering = ['test_type_imaging']

    def __str__(self):
        return self.test_type_imaging


class PathologySpecimenType(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    test_type_path = models.CharField(max_length=255, db_column='Test_Type_Path')

    class Meta:
        db_table = 'sbtblPath'
        ordering = ['test_type_path']

    def __str__(self):
        return self.test_type_path


class MolecularTestType(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    test_type_mol = models.CharField(max_length=255, db_column='Test_Type_Mol')

    class Meta:
        db_table = 'sbtblMolecular'
        ordering = ['test_type_mol']

    def __str__(self):
        return self.test_type_mol


# ==============================================================================
# CORE PATIENT MODEL
# ==============================================================================

class Patient(models.Model):
    mr_no = models.CharField(max_length=255, primary_key=True, db_column='MR_No', verbose_name='MR No')
    pt_name = models.CharField(max_length=255, db_column='Pt_name', verbose_name='Patient Name')
    sex = models.CharField(max_length=255, db_column='Sex', verbose_name='Sex')
    date_of_birth = models.DateField(db_column='Date_Of_birth', verbose_name='Date of Birth')
    diagnosis = models.CharField(max_length=255, db_column='Diagnosis', verbose_name='Diagnosis')
    primary_treatment_site = models.CharField(max_length=255, db_column='Primary_treatment_site', verbose_name='Primary Disease Site')
    laterality = models.CharField(max_length=255, db_column='Laterality', verbose_name='Laterality')
    phone = models.CharField(max_length=50, db_column='Phone', verbose_name='Phone')
    phone_alternate = models.CharField(max_length=50, blank=True, null=True, db_column='Phone_Alternate', verbose_name='Phone [Alternate]')
    notes = models.TextField(blank=True, null=True, db_column='Notes', verbose_name='Notes')
    address = models.CharField(max_length=255, blank=True, null=True, db_column='Address', verbose_name='Address')
    country = models.CharField(max_length=50, default='India', db_column='Country', verbose_name='Country')
    state = models.CharField(max_length=255, default='Karnataka', db_column='State', verbose_name='State')
    district = models.CharField(max_length=255, blank=True, null=True, db_column='District', verbose_name='District')
    pincode = models.CharField(max_length=20, blank=True, null=True, db_column='Pincode', verbose_name='Pincode')
    digipin = models.CharField(max_length=255, blank=True, null=True, db_column='Digipin', verbose_name='Digipin')
    
    # Audit tracking
    entered_by = models.CharField(max_length=255, blank=True, null=True, db_column='EnteredBy')
    entered_on = models.DateTimeField(blank=True, null=True, db_column='EnteredOn')
    last_modified_by = models.CharField(max_length=255, blank=True, null=True, db_column='LastModifiedBy')
    last_modified_on = models.DateTimeField(blank=True, null=True, db_column='LastModifiedOn')

    class Meta:
        db_table = 'tblPtDetails'
        ordering = ['mr_no']

    def __str__(self):
        return f"{self.pt_name} ({self.mr_no})"

    def format_age(self, as_of_date=None):
        """Faithful reproduction of Access mdlAge.FormatAge"""
        if not self.date_of_birth:
            return ""
        ref_date = as_of_date if as_of_date else date.today()
        dob = self.date_of_birth
        
        total_days = (ref_date - dob).days
        if total_days < 0:
            return "(future date)"
        
        if total_days < 30:
            return f"{total_days} day{'s' if total_days != 1 else ''}"
        
        rd = relativedelta(ref_date, dob)
        yrs = rd.years
        mths = rd.months
        
        if yrs == 0:
            return f"{mths} month{'s' if mths != 1 else ''}"
        elif yrs < 5:
            res = f"{yrs} yr{'s' if yrs != 1 else ''}"
            if mths > 0:
                res += f" {mths} mo"
            return res
        else:
            return f"{yrs} years"


# ==============================================================================
# CLINICAL DETAILS & MDT EPISODE
# ==============================================================================

class ClinicalDetails(models.Model):
    clinical_id = models.AutoField(primary_key=True, db_column='ClinicalID')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, db_column='MR_No', related_name='clinical_episodes')
    mdt_id = models.CharField(max_length=255, blank=True, null=True, unique=True, db_column='MDTID')
    height = models.FloatField(default=0, blank=True, null=True, db_column='Height', verbose_name='Height (cm)')
    weight = models.FloatField(default=0, blank=True, null=True, db_column='Weight', verbose_name='Weight (kg)')
    presenting_complaints = models.TextField(blank=True, null=True, db_column='Presenting_Complaints', verbose_name='Presenting Complaints')
    examination_findings = models.TextField(blank=True, null=True, db_column='Examination_Findings', verbose_name='Examination Findings')
    prev_tx_history = models.TextField(blank=True, null=True, db_column='Prev_Tx_History', verbose_name='Previous Treatment History')
    diagnosis = models.CharField(max_length=255, blank=True, null=True, db_column='Diagnosis', verbose_name='Diagnosis')
    stage = models.CharField(max_length=255, blank=True, null=True, db_column='Stage', verbose_name='Stage')
    status = models.CharField(max_length=20, default='Draft', db_column='Status', choices=[('Draft', 'Draft'), ('Approved', 'Approved')])
    mdt_discussion_for = models.TextField(blank=True, null=True, db_column='MDT_Discussion_For', verbose_name='MDT Discussion For')
    date_mdt_planned = models.DateField(blank=True, null=True, db_column='Date_MDT_Planned', verbose_name='Date MDT Planned')
    
    # Audit tracking
    entered_by = models.CharField(max_length=50, blank=True, null=True, db_column='EnteredBy')
    entered_on = models.DateTimeField(blank=True, null=True, db_column='EnteredOn')
    approved_by = models.CharField(max_length=50, blank=True, null=True, db_column='ApprovedBy')
    approved_on = models.DateTimeField(blank=True, null=True, db_column='ApprovedOn')

    class Meta:
        db_table = 'tblClinicalDetails'
        ordering = ['-clinical_id']

    def __str__(self):
        return f"Clinical #{self.clinical_id} - {self.patient.mr_no} ({self.status})"

    @property
    def is_approved(self):
        return self.status == 'Approved'


# ==============================================================================
# MDT CONSENSUS & MEETING OUTCOME
# ==============================================================================

class MDTConsensus(models.Model):
    consensus_id = models.AutoField(primary_key=True, db_column='MDTConsensusID')
    clinical = models.OneToOneField(ClinicalDetails, on_delete=models.CASCADE, db_column='ClinicalID', related_name='consensus')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, db_column='MR_No', related_name='mdt_consensuses')
    mdt_id = models.CharField(max_length=255, unique=True, db_column='MDTID')
    date_mdt_conducted = models.DateField(blank=True, null=True, db_column='Date_MDT_conducted', verbose_name='Date of MDT Conducted')
    mdt_discussion = models.TextField(blank=True, null=True, db_column='MDT_Discussion', verbose_name='MDT Discussion')
    mdt_consensus = models.TextField(blank=True, null=True, db_column='MDTConsensus', verbose_name='MDT Consensus')
    follow_up_actions = models.TextField(blank=True, null=True, db_column='FollowUp_Actions', verbose_name='Follow-Up Actions')
    status = models.CharField(max_length=20, default='Draft', db_column='Status', choices=[('Draft', 'Draft'), ('Approved', 'Approved')])
    
    # Audit tracking
    entered_by = models.CharField(max_length=255, blank=True, null=True, db_column='EnteredBy')
    entered_on = models.DateTimeField(blank=True, null=True, db_column='EnteredOn')
    approved_by = models.CharField(max_length=255, blank=True, null=True, db_column='ApprovedBy')
    approved_on = models.DateTimeField(blank=True, null=True, db_column='ApprovedOn')

    class Meta:
        db_table = 'tblMDTConsensus'
        ordering = ['-consensus_id']

    def __str__(self):
        return f"MDT Consensus {self.mdt_id} ({self.status})"

    @property
    def is_approved(self):
        return self.status == 'Approved'


# ==============================================================================
# INVESTIGATION MODELS (Blood, Imaging, Pathology, Molecular)
# ==============================================================================

class BloodInvestigation(models.Model):
    blood_id = models.AutoField(primary_key=True, db_column='BloodID')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, db_column='MR_No', related_name='blood_tests')
    clinical = models.ForeignKey(ClinicalDetails, on_delete=models.CASCADE, db_column='ClinicalID', related_name='blood_tests')
    test_date = models.DateField(db_column='Test_date', verbose_name='Date of Test')
    specimen_type = models.CharField(max_length=255, db_column='Specimen_Type', verbose_name='Specimen Type')
    details = models.TextField(blank=True, null=True, db_column='Details', verbose_name='Details')
    impression = models.TextField(blank=True, null=True, db_column='Impression', verbose_name='Impression')
    linked_to_mdt = models.BooleanField(default=False, db_column='LinkedToMDT', verbose_name='Linked to MDT')
    entered_by = models.CharField(max_length=255, blank=True, null=True, db_column='EnteredBy')
    entered_on = models.DateTimeField(blank=True, null=True, db_column='EnteredOn')

    class Meta:
        db_table = 'tblBlood'
        ordering = ['test_date', 'blood_id']

    def __str__(self):
        return f"Blood Test #{self.blood_id} ({self.specimen_type}) - {self.test_date}"


class ImagingInvestigation(models.Model):
    imaging_id = models.AutoField(primary_key=True, db_column='ImagingID')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, db_column='MR_No', related_name='imaging_tests')
    clinical = models.ForeignKey(ClinicalDetails, on_delete=models.CASCADE, db_column='ClinicalID', related_name='imaging_tests')
    imaging_date = models.DateField(db_column='Imaging_Date', verbose_name='Date of Imaging')
    imaging_type = models.CharField(max_length=255, db_column='Imaging_type', verbose_name='Imaging Type')
    site = models.CharField(max_length=255, blank=True, null=True, db_column='Site', verbose_name='Site')
    details = models.TextField(blank=True, null=True, db_column='Details', verbose_name='Details')
    impression = models.TextField(blank=True, null=True, db_column='Impression', verbose_name='Impression')
    linked_to_mdt = models.BooleanField(default=False, db_column='LinkedToMDT', verbose_name='Linked to MDT')
    entered_by = models.CharField(max_length=255, blank=True, null=True, db_column='EnteredBy')
    entered_on = models.DateTimeField(blank=True, null=True, db_column='EnteredOn')

    class Meta:
        db_table = 'tblImaging'
        ordering = ['imaging_date', 'imaging_id']

    def __str__(self):
        return f"Imaging #{self.imaging_id} ({self.imaging_type}) - {self.imaging_date}"


class PathologyInvestigation(models.Model):
    path_id = models.AutoField(primary_key=True, db_column='PathID')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, db_column='MR_No', related_name='pathology_tests')
    clinical = models.ForeignKey(ClinicalDetails, on_delete=models.CASCADE, db_column='ClinicalID', related_name='pathology_tests')
    path_date = models.DateField(db_column='Path_Date', verbose_name='Date of Report')
    lab_reference_no = models.CharField(max_length=255, blank=True, null=True, default='', db_column='Lab_Reference_No', verbose_name='Lab Reference No')
    specimen_type = models.CharField(max_length=255, blank=True, null=True, db_column='Specimen_type', verbose_name='Specimen Type')
    site_of_biopsy = models.CharField(max_length=255, blank=True, null=True, db_column='Site_Of_Biopsy', verbose_name='Site of Biopsy')
    details = models.TextField(blank=True, null=True, db_column='Details', verbose_name='Details')
    impression = models.TextField(blank=True, null=True, db_column='Impression', verbose_name='Impression')
    linked_to_mdt = models.BooleanField(default=False, db_column='LinkedToMDT', verbose_name='Linked to MDT')
    entered_by = models.CharField(max_length=255, blank=True, null=True, db_column='EnteredBy')
    entered_on = models.DateTimeField(blank=True, null=True, db_column='EnteredOn')

    class Meta:
        db_table = 'tblPath'
        ordering = ['path_date', 'path_id']

    def __str__(self):
        return f"Pathology #{self.path_id} ({self.lab_reference_no}) - {self.path_date}"


class MolecularInvestigation(models.Model):
    molecular_id = models.AutoField(primary_key=True, db_column='MolecularID')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, db_column='MR_No', related_name='molecular_tests')
    clinical = models.ForeignKey(ClinicalDetails, on_delete=models.CASCADE, db_column='ClinicalID', related_name='molecular_tests')
    test_date = models.DateField(db_column='Test_Date', verbose_name='Date of Test')
    lab_reference_no = models.CharField(max_length=255, blank=True, null=True, default='', db_column='Lab_Reference_No', verbose_name='Lab Reference No')
    test_type = models.CharField(max_length=255, blank=True, null=True, db_column='Test_Type', verbose_name='Test Type')
    details = models.TextField(blank=True, null=True, db_column='Details', verbose_name='Details')
    impression = models.TextField(blank=True, null=True, db_column='Impression', verbose_name='Impression')
    linked_to_mdt = models.BooleanField(default=False, db_column='LinkedToMDT', verbose_name='Linked to MDT')
    entered_by = models.CharField(max_length=255, blank=True, null=True, db_column='EnteredBy')
    entered_on = models.DateTimeField(blank=True, null=True, db_column='EnteredOn')

    class Meta:
        db_table = 'tblMolecular'
        ordering = ['test_date', 'molecular_id']

    def __str__(self):
        return f"Molecular #{self.molecular_id} ({self.test_type}) - {self.test_date}"


# ==============================================================================
# CLINICAL ATTACHMENTS (DOCUMENTS, PHOTOS, SCANS, VIDEOS)
# ==============================================================================

class ClinicalAttachment(models.Model):
    CATEGORY_CHOICES = [
        ('imaging', 'Imaging / Radiology Scan'),
        ('pathology', 'Pathology Report / Slide'),
        ('clinical_photo', 'Clinical Photo'),
        ('clinical_video', 'Clinical Video / Procedure'),
        ('document', 'Document / Discharge Summary / Lab PDF'),
        ('other', 'Other Attachment'),
    ]

    attachment_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='attachments')
    clinical = models.ForeignKey(ClinicalDetails, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='document')
    title = models.CharField(max_length=255, verbose_name='File Title / Description')
    file = models.FileField(upload_to='clinical_attachments/%Y/%m/')
    file_type = models.CharField(max_length=50, blank=True, null=True)
    file_size_bytes = models.BigIntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    uploaded_by = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tblClinicalAttachments'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"


# ==============================================================================
# AUDIT LOGGING MODEL
# ==============================================================================

class AuditLog(models.Model):
    log_id = models.AutoField(primary_key=True, db_column='LogID')
    log_date_time = models.DateTimeField(default=timezone.now, db_column='LogDateTime')
    username = models.CharField(max_length=100, db_column='Username')
    full_name = models.CharField(max_length=150, blank=True, null=True, db_column='FullName')
    action = models.CharField(max_length=100, db_column='Action')
    table_affected = models.CharField(max_length=100, db_column='TableAffected')
    record_ref = models.CharField(max_length=255, db_column='RecordRef')
    notes = models.TextField(blank=True, null=True, db_column='Notes')

    class Meta:
        db_table = 'tblAuditLog'
        ordering = ['-log_date_time']

    def __str__(self):
        return f"[{self.log_date_time.strftime('%Y-%m-%d %H:%M')}] {self.username} - {self.action} on {self.table_affected} ({self.record_ref})"
