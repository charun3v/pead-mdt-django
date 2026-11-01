import re
from datetime import date
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.db import transaction
from .models import ClinicalDetails, Patient, AuditLog


def format_age(dob, as_of_date=None):
    """
    Paediatric oncology age calculation:
    - Less than 30 days: 'X days'
    - Less than 1 year: 'X months'
    - 1 to 4 years: 'X yrs Y mo'
    - 5 years and over: 'X years'
    """
    if not dob:
        return ""
    ref_date = as_of_date if as_of_date else date.today()
    
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


def generate_mdt_id():
    """
    Generates the next sequential MDT ID in format:
    PED + YY + 00 + 00001 (e.g. PED260000001)
    """
    curr_year = timezone.now().strftime("%y")
    prefix = f"PED{curr_year}00"
    
    with transaction.atomic():
        # Look for existing MDT IDs with current year prefix
        existing_ids = ClinicalDetails.objects.filter(
            mdt_id__startswith=prefix
        ).values_list('mdt_id', flat=True)
        
        max_seq = 0
        for mid in existing_ids:
            if mid and len(mid) >= 8:
                try:
                    seq_num = int(mid[7:])
                    if seq_num > max_seq:
                        max_seq = seq_num
                except ValueError:
                    pass
                    
        new_seq = max_seq + 1
        return f"{prefix}{new_seq:05d}"


def write_audit_log(user_or_request, action, table_affected, record_ref, notes=""):
    """
    Writes an audit entry to tblAuditLog
    """
    try:
        username = "system"
        full_name = "System"
        
        if hasattr(user_or_request, 'user'):
            user = user_or_request.user
            if user.is_authenticated:
                username = user.username
                full_name = user.get_full_name() or user.username
        elif hasattr(user_or_request, 'username'):
            username = user_or_request.username
            full_name = user_or_request.get_full_name() or user_or_request.username
        elif isinstance(user_or_request, str) and user_or_request:
            username = user_or_request
            full_name = user_or_request
            
        AuditLog.objects.create(
            log_date_time=timezone.now(),
            username=username,
            full_name=full_name,
            action=action,
            table_affected=table_affected,
            record_ref=str(record_ref),
            notes=notes
        )
    except Exception as e:
        # Don't let audit log failure break the clinical transaction
        print(f"Audit log error: {e}")


def update_patient_diagnosis(mr_no, new_diagnosis, user_or_request=None):
    """
    Cascades latest clinical diagnosis to tblPtDetails if changed,
    preserving historical clinical record diagnoses and logging the change.
    """
    if not mr_no or not new_diagnosis:
        return
        
    new_diag_clean = str(new_diagnosis).strip()
    if not new_diag_clean:
        return
        
    try:
        patient = Patient.objects.get(mr_no=mr_no)
        old_diag = patient.diagnosis
        if old_diag != new_diag_clean:
            patient.diagnosis = new_diag_clean
            patient.last_modified_on = timezone.now()
            if user_or_request:
                if hasattr(user_or_request, 'user') and user_or_request.user.is_authenticated:
                    patient.last_modified_by = user_or_request.user.username
                elif hasattr(user_or_request, 'username'):
                    patient.last_modified_by = user_or_request.username
            patient.save(update_fields=['diagnosis', 'last_modified_on', 'last_modified_by'])
            
            write_audit_log(
                user_or_request,
                "UPDATE_DIAGNOSIS",
                "tblPtDetails",
                mr_no,
                f"From: '{old_diag}' To: '{new_diag_clean}'"
            )
    except Patient.DoesNotExist:
        pass
