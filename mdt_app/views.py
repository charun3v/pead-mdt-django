from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.utils import timezone
from datetime import date, timedelta, datetime
from django.db.models import Q
from django.db import transaction
import os
import json

from .models import (
    Patient, ClinicalDetails, MDTConsensus,
    BloodInvestigation, ImagingInvestigation, PathologyInvestigation, MolecularInvestigation,
    ClinicalAttachment, State, District, PrimaryTreatmentSite, Laterality, Sex,
    BCMInvestigationType, ImagingTestType, ImagingSite, PathologySpecimenType, MolecularTestType
)
from .utils import format_age, generate_mdt_id, write_audit_log, update_patient_diagnosis


# ==============================================================================
# AUTHENTICATION (frmLogin)
# ==============================================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    error_msg = ""
    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            if user.is_active:
                login(request, user)
                write_audit_log(user, "LOGIN", "auth_user", user.username, "User logged in successfully")
                return redirect('dashboard')
            else:
                error_msg = "Account is disabled."
        else:
            error_msg = "Invalid Username or Password."
            
    return render(request, 'login.html', {'error_msg': error_msg})


def logout_view(request):
    if request.user.is_authenticated:
        write_audit_log(request.user, "LOGOUT", "auth_user", request.user.username, "User logged out")
    logout(request)
    return redirect('login')


# ==============================================================================
# DASHBOARD (frmDashboard)
# ==============================================================================

@login_required
def dashboard_view(request):
    today = date.today()
    in_10_days = today + timedelta(days=10)
    
    # Upcoming MDTs: planned within next 10 days, Approved status (qryUpcomingMDTs)
    upcoming_mdts = ClinicalDetails.objects.filter(
        status='Approved',
        date_mdt_planned__gte=today,
        date_mdt_planned__lte=in_10_days
    ).select_related('patient').order_by('date_mdt_planned')
    
    # Recent MDTs: Top 10 approved conducted MDTs (qryRecentMDTs)
    recent_mdts = MDTConsensus.objects.filter(
        status='Approved'
    ).select_related('patient', 'clinical').order_by('-date_mdt_conducted')[:10]
    
    context = {
        'upcoming_mdts': upcoming_mdts,
        'recent_mdts': recent_mdts,
        'user_full_name': request.user.get_full_name() or request.user.username,
        'is_admin': request.user.is_staff or request.user.is_superuser,
    }
    return render(request, 'dashboard.html', context)


# ==============================================================================
# PATIENT REGISTRATION & EDIT (frmPatientReg)
# ==============================================================================

@login_required
def patient_reg_view(request, mr_no=None):
    patient = None
    is_edit = False
    
    if mr_no:
        patient = get_object_or_404(Patient, mr_no=mr_no)
        is_edit = True
        
    if request.method == 'POST':
        p_mr_no = request.POST.get('mr_no', '').strip()
        pt_name = request.POST.get('pt_name', '').strip()
        sex = request.POST.get('sex', 'Male')
        dob_str = request.POST.get('date_of_birth')
        diagnosis = request.POST.get('diagnosis', '').strip()
        site = request.POST.get('primary_treatment_site', '')
        laterality = request.POST.get('laterality', '')
        phone = request.POST.get('phone', '').strip()
        phone_alt = request.POST.get('phone_alternate', '').strip()
        notes = request.POST.get('notes', '').strip()
        address = request.POST.get('address', '').strip()
        country = request.POST.get('country', 'India')
        state = request.POST.get('state', 'Karnataka')
        district = request.POST.get('district', '')
        pincode = request.POST.get('pincode', '').strip()
        digipin = request.POST.get('digipin', '').strip()
        
        dob = None
        if dob_str:
            try:
                dob = date.fromisoformat(dob_str)
            except ValueError:
                dob = None

        if not pincode:
            messages.error(request, "Pincode is mandatory.")
            context = {
                'patient': patient,
                'is_edit': is_edit,
                'sexes': Sex.objects.all(),
                'sites': PrimaryTreatmentSite.objects.all(),
                'lateralities': Laterality.objects.all(),
                'states': State.objects.all(),
            }
            return render(request, 'patient_reg.html', context)

        if is_edit:
            patient.pt_name = pt_name
            patient.sex = sex
            patient.date_of_birth = dob
            patient.diagnosis = diagnosis
            patient.primary_treatment_site = site
            patient.laterality = laterality
            patient.phone = phone
            patient.phone_alternate = phone_alt
            patient.notes = notes
            patient.address = address
            patient.country = country
            patient.state = state
            patient.district = district
            patient.pincode = pincode
            patient.digipin = digipin
            patient.last_modified_by = request.user.username
            patient.last_modified_on = timezone.now()
            patient.save()
            
            write_audit_log(request, "UPDATE_PATIENT", "tblPtDetails", patient.mr_no, "Patient updated")
            messages.success(request, f"Patient {patient.mr_no} details updated successfully.")
            return redirect('patient_search_with_mr', mr_no=patient.mr_no)
        else:
            if Patient.objects.filter(mr_no=p_mr_no).exists():
                messages.error(request, f"Patient with MR No '{p_mr_no}' already exists.")
            else:
                new_pt = Patient.objects.create(
                    mr_no=p_mr_no,
                    pt_name=pt_name,
                    sex=sex,
                    date_of_birth=dob,
                    diagnosis=diagnosis,
                    primary_treatment_site=site,
                    laterality=laterality,
                    phone=phone,
                    phone_alternate=phone_alt,
                    notes=notes,
                    address=address,
                    country=country,
                    state=state,
                    district=district,
                    pincode=pincode,
                    digipin=digipin,
                    entered_by=request.user.username,
                    entered_on=timezone.now()
                )
                write_audit_log(request, "REGISTER_PATIENT", "tblPtDetails", new_pt.mr_no, "New patient registered")
                messages.success(request, f"Patient {new_pt.mr_no} registered successfully.")
                return redirect('patient_search_with_mr', mr_no=new_pt.mr_no)

    context = {
        'patient': patient,
        'is_edit': is_edit,
        'sexes': Sex.objects.all(),
        'sites': PrimaryTreatmentSite.objects.all(),
        'lateralities': Laterality.objects.all(),
        'states': State.objects.all(),
    }
    return render(request, 'patient_reg.html', context)


# ==============================================================================
# PATIENT SEARCH & COCKPIT (frmPatientSearch)
# ==============================================================================

@login_required
def patient_search_view(request, mr_no=None):
    query = request.GET.get('q', '').strip()
    if mr_no:
        query = mr_no
        
    patient = None
    episodes = []
    
    if query:
        patient = Patient.objects.filter(Q(mr_no__iexact=query) | Q(pt_name__icontains=query)).first()
        if patient:
            # Episodes with MDT Consensus status (qryPtMDTHistory)
            episodes = ClinicalDetails.objects.filter(patient=patient).select_related('consensus').order_by('-clinical_id')
        else:
            messages.info(request, f"No patient found matching '{query}'.")

    context = {
        'query': query,
        'patient': patient,
        'episodes': episodes,
        'formatted_age': patient.format_age() if patient else "",
        'is_admin': request.user.is_staff or request.user.is_superuser,
    }
    return render(request, 'patient_search.html', context)


# ==============================================================================
# CLINICAL DETAILS EPISODE (frmClinicalDetails)
# ==============================================================================

@login_required
def clinical_details_view(request, clinical_id=None, mr_no=None):
    clinical = None
    is_new = False
    
    if clinical_id:
        clinical = get_object_or_404(ClinicalDetails, clinical_id=clinical_id)
        patient = clinical.patient
    elif mr_no:
        patient = get_object_or_404(Patient, mr_no=mr_no)
        is_new = True
        # Check if an empty draft already exists
        clinical = ClinicalDetails.objects.filter(patient=patient, status='Draft', mdt_id__isnull=True).first()
        if not clinical:
            clinical = ClinicalDetails.objects.create(
                patient=patient,
                diagnosis=patient.diagnosis,
                status='Draft',
                entered_by=request.user.username,
                entered_on=timezone.now()
            )
    else:
        return redirect('dashboard')

    # Handle Save / Approve
    consensus_obj = getattr(clinical, 'consensus', None)
    is_locked = bool(consensus_obj and consensus_obj.is_approved)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if is_locked and action in ['save', 'generate_mdt', 'approve']:
            messages.error(request, "This clinical record has already been finalized and approved in MDT. It cannot be edited.")
            return redirect('clinical_details', clinical_id=clinical.clinical_id)
            
        if action == 'go_to_mdt':
            if not is_locked:
                clinical.height = float(request.POST.get('height') or 0)
                clinical.weight = float(request.POST.get('weight') or 0)
                clinical.presenting_complaints = request.POST.get('presenting_complaints', '').strip()
                clinical.examination_findings = request.POST.get('examination_findings', '').strip()
                clinical.prev_tx_history = request.POST.get('prev_tx_history', '').strip()
                clinical.diagnosis = request.POST.get('diagnosis', '').strip() or patient.diagnosis
                clinical.stage = request.POST.get('stage', '').strip()
                clinical.mdt_discussion_for = request.POST.get('mdt_discussion_for', '').strip()
                
                planned_str = request.POST.get('date_mdt_planned')
                if planned_str:
                    try:
                        clinical.date_mdt_planned = date.fromisoformat(planned_str)
                    except ValueError:
                        pass
                elif not clinical.date_mdt_planned:
                    clinical.date_mdt_planned = date.today()
                    
                clinical.save()
                update_patient_diagnosis(patient.mr_no, clinical.diagnosis, request)
                if not clinical.mdt_id:
                    new_mdt_id = generate_mdt_id()
                    clinical.mdt_id = new_mdt_id
                    clinical.save()

            consensus, _ = MDTConsensus.objects.get_or_create(
                clinical=clinical,
                defaults={
                    'patient': patient,
                    'mdt_id': clinical.mdt_id or generate_mdt_id(),
                    'date_mdt_conducted': clinical.date_mdt_planned or date.today(),
                    'status': 'Draft',
                    'entered_by': request.user.username,
                    'entered_on': timezone.now()
                }
            )
            write_audit_log(request, "GO_TO_MDT", "tblClinicalDetails", patient.mr_no, f"Proceeded to MDT ({clinical.mdt_id})")
            return redirect('mdt_consensus', consensus_id=consensus.consensus_id)

        # Save Draft or Generate MDT
        clinical.height = float(request.POST.get('height') or 0)
        clinical.weight = float(request.POST.get('weight') or 0)
        clinical.presenting_complaints = request.POST.get('presenting_complaints', '').strip()
        clinical.examination_findings = request.POST.get('examination_findings', '').strip()
        clinical.prev_tx_history = request.POST.get('prev_tx_history', '').strip()
        clinical.diagnosis = request.POST.get('diagnosis', '').strip() or patient.diagnosis
        clinical.stage = request.POST.get('stage', '').strip()
        clinical.mdt_discussion_for = request.POST.get('mdt_discussion_for', '').strip()
        
        planned_str = request.POST.get('date_mdt_planned')
        if planned_str:
            try:
                clinical.date_mdt_planned = date.fromisoformat(planned_str)
            except ValueError:
                pass
        elif not clinical.date_mdt_planned:
            clinical.date_mdt_planned = date.today()

        if action in ['generate_mdt', 'approve']:
            already_had_mdt = bool(clinical.mdt_id)
            if not clinical.mdt_id:
                new_mdt_id = generate_mdt_id()
                clinical.mdt_id = new_mdt_id
            clinical.save()
            
            # Create Consensus Stub (tblMDTConsensus)
            MDTConsensus.objects.get_or_create(
                clinical=clinical,
                defaults={
                    'patient': patient,
                    'mdt_id': clinical.mdt_id,
                    'date_mdt_conducted': clinical.date_mdt_planned or date.today(),
                    'status': 'Draft',
                    'entered_by': request.user.username,
                    'entered_on': timezone.now()
                }
            )
            
            update_patient_diagnosis(patient.mr_no, clinical.diagnosis, request)
            if already_had_mdt:
                write_audit_log(request, "EDIT_CLINICAL_POST_MDT", "tblClinicalDetails", patient.mr_no, f"Clinical details updated post-MDT ID ({clinical.mdt_id})")
                messages.success(request, f"Clinical details updated and logged under MDT ID: {clinical.mdt_id}")
            else:
                write_audit_log(request, "GENERATE_MDT_ID", "tblClinicalDetails", patient.mr_no, f"MDT ID generated: {clinical.mdt_id}")
                messages.success(request, f"Clinical details saved. MDT ID: {clinical.mdt_id}")
            return redirect('clinical_details', clinical_id=clinical.clinical_id)
            
        else: # Regular save (Save as Draft)
            clinical.save()
            update_patient_diagnosis(patient.mr_no, clinical.diagnosis, request)
            if clinical.mdt_id:
                write_audit_log(request, "EDIT_CLINICAL_POST_MDT", "tblClinicalDetails", patient.mr_no, f"Clinical details saved as Draft post-MDT ID ({clinical.mdt_id})")
            else:
                write_audit_log(request, "SAVE_CLINICAL", "tblClinicalDetails", patient.mr_no, f"Clinical #{clinical.clinical_id} saved as Draft")
            messages.success(request, "Clinical details saved as Draft.")
            return redirect('clinical_details', clinical_id=clinical.clinical_id)

    # Context Data
    blood_tests = clinical.blood_tests.all()
    imaging_tests = clinical.imaging_tests.all()
    pathology_tests = clinical.pathology_tests.all()
    molecular_tests = clinical.molecular_tests.all()
    attachments = clinical.attachments.all()
    
    # Lookups for modals
    bcm_types = BCMInvestigationType.objects.all()
    imaging_types = ImagingTestType.objects.all()
    imaging_sites = ImagingSite.objects.all()
    path_types = PathologySpecimenType.objects.all()
    molecular_types = MolecularTestType.objects.all()
    
    context = {
        'patient': patient,
        'clinical': clinical,
        'formatted_age': patient.format_age(clinical.date_mdt_planned),
        'blood_tests': blood_tests,
        'imaging_tests': imaging_tests,
        'pathology_tests': pathology_tests,
        'molecular_tests': molecular_tests,
        'attachments': attachments,
        'bcm_types': bcm_types,
        'imaging_types': imaging_types,
        'imaging_sites': imaging_sites,
        'path_types': path_types,
        'molecular_types': molecular_types,
        'consensus_obj': consensus_obj,
        'is_locked': is_locked,
        'is_admin': request.user.is_staff or request.user.is_superuser,
    }
    return render(request, 'clinical_details.html', context)


# ==============================================================================
# MODAL INVESTIGATION ADD & DELETE
# ==============================================================================

@login_required
def add_investigation_view(request, inv_type, clinical_id):
    clinical = get_object_or_404(ClinicalDetails, clinical_id=clinical_id)
    patient = clinical.patient
    
    if getattr(clinical, 'consensus', None) and clinical.consensus.is_approved:
        messages.error(request, "Cannot add investigation: This MDT episode is already finalized and approved.")
        return redirect('clinical_details', clinical_id=clinical.clinical_id)

    if request.method == 'POST':
        test_date_str = request.POST.get('test_date')
        test_date = date.fromisoformat(test_date_str) if test_date_str else date.today()
        
        # Validation 1: No future date allowed
        if test_date > date.today():
            messages.error(request, "Investigation date cannot be in the future.")
            return redirect('clinical_details', clinical_id=clinical.clinical_id)

        details = request.POST.get('details', '').strip()
        impression = request.POST.get('impression', '').strip()
        linked_to_mdt = request.POST.get('linked_to_mdt') == 'on'

        # Validation 2: Impression is mandatory for Imaging, Pathology, Molecular
        if inv_type in ['imaging', 'pathology', 'molecular'] and not impression:
            messages.error(request, f"Impression is mandatory for {inv_type.capitalize()} investigation.")
            return redirect('clinical_details', clinical_id=clinical.clinical_id)
        
        if inv_type == 'blood':
            BloodInvestigation.objects.create(
                patient=patient, clinical=clinical,
                test_date=test_date,
                specimen_type=request.POST.get('specimen_type', 'CBC'),
                details=details, impression=impression,
                linked_to_mdt=linked_to_mdt,
                entered_by=request.user.username, entered_on=timezone.now()
            )
        elif inv_type == 'imaging':
            ImagingInvestigation.objects.create(
                patient=patient, clinical=clinical,
                imaging_date=test_date,
                imaging_type=request.POST.get('imaging_type', 'CT'),
                site=request.POST.get('site', ''),
                details=details, impression=impression,
                linked_to_mdt=linked_to_mdt,
                entered_by=request.user.username, entered_on=timezone.now()
            )
        elif inv_type == 'pathology':
            PathologyInvestigation.objects.create(
                patient=patient, clinical=clinical,
                path_date=test_date,
                lab_reference_no=request.POST.get('lab_reference_no', ''),
                specimen_type=request.POST.get('specimen_type', ''),
                site_of_biopsy=request.POST.get('site_of_biopsy', ''),
                details=details, impression=impression,
                linked_to_mdt=linked_to_mdt,
                entered_by=request.user.username, entered_on=timezone.now()
            )
        elif inv_type == 'molecular':
            MolecularInvestigation.objects.create(
                patient=patient, clinical=clinical,
                test_date=test_date,
                lab_reference_no=request.POST.get('lab_reference_no', ''),
                test_type=request.POST.get('test_type', ''),
                details=details, impression=impression,
                linked_to_mdt=linked_to_mdt,
                entered_by=request.user.username, entered_on=timezone.now()
            )
            
        messages.success(request, f"{inv_type.capitalize()} investigation added successfully.")
        return redirect('clinical_details', clinical_id=clinical.clinical_id)
        
    return redirect('clinical_details', clinical_id=clinical.clinical_id)


@login_required
def delete_investigation_view(request, inv_type, inv_id):
    if inv_type == 'blood':
        inv = get_object_or_404(BloodInvestigation, blood_id=inv_id)
    elif inv_type == 'imaging':
        inv = get_object_or_404(ImagingInvestigation, imaging_id=inv_id)
    elif inv_type == 'pathology':
        inv = get_object_or_404(PathologyInvestigation, path_id=inv_id)
    elif inv_type == 'molecular':
        inv = get_object_or_404(MolecularInvestigation, molecular_id=inv_id)
    else:
        raise Http404()
        
    clinical_id = inv.clinical.clinical_id
    if getattr(inv.clinical, 'consensus', None) and inv.clinical.consensus.is_approved:
        messages.error(request, "Cannot delete investigation: This MDT episode is already finalized and approved.")
        return redirect('clinical_details', clinical_id=clinical_id)

    inv.delete()
    messages.success(request, f"{inv_type.capitalize()} investigation removed.")
    return redirect('clinical_details', clinical_id=clinical_id)


# ==============================================================================
# MDT DISCUSSION & CONSENSUS FORM (frmMDTConsensus)
# ==============================================================================

@login_required
def mdt_consensus_view(request, consensus_id):
    consensus = get_object_or_404(MDTConsensus, consensus_id=consensus_id)
    clinical = consensus.clinical
    patient = consensus.patient
    
    if request.method == 'POST':
        if consensus.is_approved:
            messages.error(request, "This MDT Discussion has already been finalized and approved. No further edits are permitted.")
            return redirect('mdt_consensus', consensus_id=consensus.consensus_id)

        action = request.POST.get('action')
        consensus.mdt_discussion = request.POST.get('mdt_discussion', '').strip()
        consensus.mdt_consensus = request.POST.get('mdt_consensus', '').strip()
        consensus.follow_up_actions = request.POST.get('follow_up_actions', '').strip()
        
        # Diagnosis modification cascade
        new_diag = request.POST.get('diagnosis', '').strip()
        if new_diag and new_diag != clinical.diagnosis:
            clinical.diagnosis = new_diag
            clinical.save(update_fields=['diagnosis'])
            update_patient_diagnosis(patient.mr_no, new_diag, request)
            
        # Parse and update Date Conducted
        date_conducted_str = request.POST.get('date_mdt_conducted', '').strip()
        if date_conducted_str:
            try:
                c_date = datetime.strptime(date_conducted_str, "%Y-%m-%d").date()
                if c_date > date.today():
                    messages.error(request, "Date MDT Conducted cannot be in the future.")
                    return redirect('mdt_consensus', consensus_id=consensus.consensus_id)
                consensus.date_mdt_conducted = c_date
            except ValueError:
                pass
        if not consensus.date_mdt_conducted:
            consensus.date_mdt_conducted = date.today()

        if action == 'save':
            if not consensus.status:
                consensus.status = 'Draft'
            consensus.save()
            write_audit_log(request, "SAVE_MDT", "tblMDTConsensus", consensus.mdt_id, f"MDT discussion saved ({consensus.status}, Conducted: {consensus.date_mdt_conducted})")
            messages.success(request, "MDT Discussion saved successfully.")
            return redirect('mdt_consensus', consensus_id=consensus.consensus_id)
            
        elif action == 'approve':
            if not consensus.mdt_discussion or not consensus.mdt_consensus:
                messages.error(request, "Cannot approve: 'MDT Discussion' and 'MDT Consensus Decision' are required.")
                return redirect('mdt_consensus', consensus_id=consensus.consensus_id)
                
            consensus.status = 'Approved'
            consensus.approved_by = request.user.username
            consensus.approved_on = timezone.now()
            consensus.save()
            
            # Lock the respective clinical form as well!
            clinical.status = 'Approved'
            clinical.approved_by = request.user.username
            clinical.approved_on = timezone.now()
            clinical.save(update_fields=['status', 'approved_by', 'approved_on'])
            
            write_audit_log(request, "APPROVE_MDT", "tblMDTConsensus", consensus.mdt_id, f"MDT finalized and approved (Conducted: {consensus.date_mdt_conducted}). Clinical and MDT records locked.")
            messages.success(request, "MDT Discussion FINALIZED & APPROVED. Both the Clinical Form and MDT Form are now locked.")
            return redirect('mdt_consensus', consensus_id=consensus.consensus_id)

    # Gather chronological investigations timeline (qrySubInvestigationsForMDT)
    all_invs = []
    for b in clinical.blood_tests.all():
        all_invs.append({'date': b.test_date, 'category': 'Hematology / Biochemistry', 'type': b.specimen_type, 'details': b.details, 'impression': b.impression})
    for im in clinical.imaging_tests.all():
        type_str = f"{im.imaging_type} - {im.site}" if im.site else im.imaging_type
        all_invs.append({'date': im.imaging_date, 'category': 'Imaging', 'type': type_str, 'details': im.details, 'impression': im.impression})
    for p in clinical.pathology_tests.all():
        type_str = f"{p.specimen_type} ({p.site_of_biopsy})" if p.site_of_biopsy else (p.specimen_type or "Biopsy")
        all_invs.append({'date': p.path_date, 'category': 'Pathology', 'type': type_str, 'details': p.details, 'impression': p.impression})
    for m in clinical.molecular_tests.all():
        all_invs.append({'date': m.test_date, 'category': 'Molecular', 'type': m.test_type, 'details': m.details, 'impression': m.impression})
        
    all_invs.sort(key=lambda x: x['date'] if x['date'] else date.min)

    context = {
        'consensus': consensus,
        'clinical': clinical,
        'patient': patient,
        'formatted_age': patient.format_age(consensus.date_mdt_conducted or date.today()),
        'all_investigations': all_invs,
        'is_locked': consensus.is_approved,
        'is_admin': request.user.is_staff or request.user.is_superuser,
    }
    return render(request, 'mdt_consensus.html', context)


# ==============================================================================
# PRINTABLE INSTITUTIONAL REPORTS (rptClinicalSummary & rptMDTFull)
# ==============================================================================

@login_required
def report_clinical_summary_view(request, clinical_id):
    clinical = get_object_or_404(ClinicalDetails, clinical_id=clinical_id)
    patient = clinical.patient
    write_audit_log(request, "PRINT_CLINICAL", "tblClinicalDetails", patient.mr_no, f"Clinical #{clinical.clinical_id}")
    
    # Chronological investigations
    all_invs = []
    for b in clinical.blood_tests.all():
        all_invs.append({'date': b.test_date, 'category': 'Hematology / Biochemistry', 'type': b.specimen_type, 'details': b.details, 'impression': b.impression})
    for im in clinical.imaging_tests.all():
        type_str = f"{im.imaging_type} - {im.site}" if im.site else im.imaging_type
        all_invs.append({'date': im.imaging_date, 'category': 'Imaging', 'type': type_str, 'details': im.details, 'impression': im.impression})
    for p in clinical.pathology_tests.all():
        type_str = f"{p.specimen_type} ({p.site_of_biopsy})" if p.site_of_biopsy else (p.specimen_type or "Biopsy")
        all_invs.append({'date': p.path_date, 'category': 'Pathology', 'type': type_str, 'details': p.details, 'impression': p.impression})
    for m in clinical.molecular_tests.all():
        all_invs.append({'date': m.test_date, 'category': 'Molecular', 'type': m.test_type, 'details': m.details, 'impression': m.impression})
    all_invs.sort(key=lambda x: x['date'] if x['date'] else date.min)

    context = {
        'clinical': clinical,
        'patient': patient,
        'formatted_age': patient.format_age(clinical.date_mdt_planned),
        'investigations': all_invs,
        'print_date': timezone.now(),
    }
    return render(request, 'report_clinical.html', context)


@login_required
def report_mdt_full_view(request, mdt_id):
    consensus = get_object_or_404(MDTConsensus, mdt_id=mdt_id)
    clinical = consensus.clinical
    patient = consensus.patient
    write_audit_log(request, "PRINT", "tblMDTConsensus", consensus.mdt_id, f"MDT Report printed ({consensus.status})")

    # Chronological investigations
    all_invs = []
    for b in clinical.blood_tests.all():
        all_invs.append({'date': b.test_date, 'category': 'Hematology / Biochemistry', 'type': b.specimen_type, 'details': b.details, 'impression': b.impression})
    for im in clinical.imaging_tests.all():
        type_str = f"{im.imaging_type} - {im.site}" if im.site else im.imaging_type
        all_invs.append({'date': im.imaging_date, 'category': 'Imaging', 'type': type_str, 'details': im.details, 'impression': im.impression})
    for p in clinical.pathology_tests.all():
        type_str = f"{p.specimen_type} ({p.site_of_biopsy})" if p.site_of_biopsy else (p.specimen_type or "Biopsy")
        all_invs.append({'date': p.path_date, 'category': 'Pathology', 'type': type_str, 'details': p.details, 'impression': p.impression})
    for m in clinical.molecular_tests.all():
        all_invs.append({'date': m.test_date, 'category': 'Molecular', 'type': m.test_type, 'details': m.details, 'impression': m.impression})
    all_invs.sort(key=lambda x: x['date'] if x['date'] else date.min)

    context = {
        'consensus': consensus,
        'clinical': clinical,
        'patient': patient,
        'formatted_age': patient.format_age(consensus.date_mdt_conducted or date.today()),
        'investigations': all_invs,
        'print_date': timezone.now(),
    }
    return render(request, 'report_mdt.html', context)


# ==============================================================================
# ATTACHMENT UPLOADS & SECURE STREAMING (Photos / Scans / Videos / PDFs)
# ==============================================================================

@login_required
def upload_attachment_view(request, clinical_id):
    clinical = get_object_or_404(ClinicalDetails, clinical_id=clinical_id)
    if getattr(clinical, 'consensus', None) and clinical.consensus.is_approved:
        messages.error(request, "Cannot upload attachment: This MDT episode is already finalized and approved.")
        return redirect('clinical_details', clinical_id=clinical.clinical_id)

    if request.method == 'POST' and request.FILES.get('attachment_file'):
        uploaded_file = request.FILES['attachment_file']
        title = request.POST.get('title', '').strip() or uploaded_file.name
        category = request.POST.get('category', 'document')
        notes = request.POST.get('notes', '')
        
        att = ClinicalAttachment.objects.create(
            patient=clinical.patient,
            clinical=clinical,
            title=title,
            category=category,
            file=uploaded_file,
            file_type=uploaded_file.content_type,
            file_size_bytes=uploaded_file.size,
            notes=notes,
            uploaded_by=request.user.username
        )
        write_audit_log(request, "UPLOAD_ATTACHMENT", "tblClinicalAttachments", clinical.patient.mr_no, f"File: {title} ({category})")
        messages.success(request, f"Attachment '{title}' uploaded successfully.")
        
    return redirect('clinical_details', clinical_id=clinical.clinical_id)


@login_required
def download_attachment_view(request, attachment_id):
    att = get_object_or_404(ClinicalAttachment, attachment_id=attachment_id)
    if not os.path.exists(att.file.path):
        raise Http404("Attachment file does not exist.")
    return FileResponse(open(att.file.path, 'rb'), content_type=att.file_type or 'application/octet-stream')


# ==============================================================================
# USER MANAGEMENT (frmUserAdmin, frmSubUsersList, frmUserEdit, frmUserResetPassword, frmUserChangePassword)
# ==============================================================================

def get_user_role(user):
    if user.is_superuser:
        return 'Administrator'
    elif user.groups.filter(name='Consultant').exists() or user.is_staff:
        return 'Consultant'
    elif user.groups.filter(name='Resident').exists():
        return 'Resident'
    else:
        return 'Standard User'


def set_user_role(user, role_name):
    for gname in ['Administrator', 'Consultant', 'Resident', 'User']:
        Group.objects.get_or_create(name=gname)
        
    user.groups.clear()
    if role_name == 'Administrator':
        user.is_superuser = True
        user.is_staff = True
        g, _ = Group.objects.get_or_create(name='Administrator')
        user.groups.add(g)
    elif role_name == 'Consultant':
        user.is_superuser = False
        user.is_staff = True
        g, _ = Group.objects.get_or_create(name='Consultant')
        user.groups.add(g)
    elif role_name == 'Resident':
        user.is_superuser = False
        user.is_staff = False
        g, _ = Group.objects.get_or_create(name='Resident')
        user.groups.add(g)
    else:
        user.is_superuser = False
        user.is_staff = False
        g, _ = Group.objects.get_or_create(name='User')
        user.groups.add(g)
    user.save()


@login_required
def user_admin_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access restricted to Administrators.")
        return redirect('dashboard')
        
    search_q = request.GET.get('q', '').strip()
    users_qs = User.objects.all().order_by('username')
    
    if search_q:
        users_qs = users_qs.filter(
            Q(username__icontains=search_q) |
            Q(first_name__icontains=search_q) |
            Q(last_name__icontains=search_q) |
            Q(email__icontains=search_q)
        )
        
    user_list = []
    for u in users_qs:
        role = get_user_role(u)
        user_list.append({
            'obj': u,
            'id': u.id,
            'username': u.username,
            'full_name': u.get_full_name() or u.username,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'email': u.email,
            'role': role,
            'is_active': u.is_active,
            'is_staff': u.is_staff,
            'is_superuser': u.is_superuser,
            'last_login': u.last_login,
            'date_joined': u.date_joined,
            'is_self': u.id == request.user.id,
            'is_protected': u.username.lower() == 'admin' or u.id == request.user.id,
        })
        
    total_count = User.objects.count()
    active_count = User.objects.filter(is_active=True).count()
    admin_count = User.objects.filter(is_superuser=True).count()
    clinician_count = total_count - admin_count
    
    context = {
        'users': user_list,
        'search_q': search_q,
        'total_count': total_count,
        'active_count': active_count,
        'admin_count': admin_count,
        'clinician_count': clinician_count,
    }
    return render(request, 'user_admin.html', context)


@login_required
def user_create_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access restricted to Administrators.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        role = request.POST.get('role', 'Consultant')
        is_active = request.POST.get('is_active') == 'on'
        
        if not username:
            messages.error(request, "Username is required.")
            return redirect('user_admin')
            
        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f"Username '{username}' already exists. Please choose a different username.")
            return redirect('user_admin')
            
        if not password or len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return redirect('user_admin')
            
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('user_admin')
            
        new_user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        new_user.is_active = is_active
        set_user_role(new_user, role)
        
        write_audit_log(
            request.user, 
            "CREATE_USER", 
            "tblUsers", 
            username, 
            f"Created user '{username}' ({first_name} {last_name}) with role '{role}'."
        )
        messages.success(request, f"User account '{username}' created successfully.")
        
    return redirect('user_admin')


@login_required
def user_edit_view(request, user_id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access restricted to Administrators.")
        return redirect('dashboard')
        
    target_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'Consultant')
        is_active = request.POST.get('is_active') == 'on'
        
        if target_user.id == request.user.id and not is_active:
            messages.error(request, "You cannot deactivate your own logged-in account.")
            is_active = True
            
        if target_user.id == request.user.id and role != 'Administrator':
            messages.error(request, "You cannot remove Administrator privileges from your own account.")
            role = 'Administrator'
            
        target_user.first_name = first_name
        target_user.last_name = last_name
        target_user.email = email
        target_user.is_active = is_active
        set_user_role(target_user, role)
        
        write_audit_log(
            request.user, 
            "EDIT_USER", 
            "tblUsers", 
            target_user.username, 
            f"Updated user details for '{target_user.username}' (Role: {role}, Active: {is_active})."
        )
        messages.success(request, f"User details for '{target_user.username}' updated successfully.")
        
    return redirect('user_admin')


@login_required
def user_reset_password_view(request, user_id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access restricted to Administrators.")
        return redirect('dashboard')
        
    target_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if not new_password or len(new_password) < 6:
            messages.error(request, "New password must be at least 6 characters.")
            return redirect('user_admin')
            
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('user_admin')
            
        target_user.set_password(new_password)
        target_user.save()
        
        if target_user.id == request.user.id:
            update_session_auth_hash(request, target_user)
            
        write_audit_log(
            request.user, 
            "RESET_PASSWORD", 
            "tblUsers", 
            target_user.username, 
            f"Password reset for '{target_user.username}' by admin {request.user.username}."
        )
        messages.success(request, f"Password for '{target_user.username}' has been reset successfully.")
        
    return redirect('user_admin')


@login_required
def user_toggle_status_view(request, user_id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access restricted to Administrators.")
        return redirect('dashboard')
        
    target_user = get_object_or_404(User, id=user_id)
    
    if target_user.id == request.user.id:
        messages.error(request, "You cannot deactivate your own logged-in account.")
        return redirect('user_admin')
        
    if target_user.username.lower() == 'admin':
        messages.error(request, "The root administrator account cannot be deactivated.")
        return redirect('user_admin')
        
    target_user.is_active = not target_user.is_active
    target_user.save()
    
    status_str = "activated" if target_user.is_active else "deactivated"
    write_audit_log(
        request.user, 
        "TOGGLE_USER_STATUS", 
        "tblUsers", 
        target_user.username, 
        f"Account {status_str}."
    )
    messages.success(request, f"Account '{target_user.username}' has been {status_str}.")
    return redirect('user_admin')


@login_required
def user_delete_view(request, user_id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Access restricted to Administrators.")
        return redirect('dashboard')
        
    target_user = get_object_or_404(User, id=user_id)
    
    if target_user.id == request.user.id:
        messages.error(request, "You cannot delete your own logged-in account.")
        return redirect('user_admin')
        
    if target_user.username.lower() == 'admin':
        messages.error(request, "The root administrator account cannot be deleted.")
        return redirect('user_admin')
        
    del_username = target_user.username
    target_user.delete()
    
    write_audit_log(
        request.user, 
        "DELETE_USER", 
        "tblUsers", 
        del_username, 
        f"User account deleted by {request.user.username}."
    )
    messages.success(request, f"User account '{del_username}' has been deleted.")
    return redirect('user_admin')


@login_required
def user_change_password_view(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if not request.user.check_password(old_password):
            messages.error(request, "Current password is incorrect.")
            return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
            
        if not new_password or len(new_password) < 6:
            messages.error(request, "New password must be at least 6 characters.")
            return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
            
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
            
        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)
        
        write_audit_log(
            request.user, 
            "CHANGE_OWN_PASSWORD", 
            "tblUsers", 
            request.user.username, 
            "User successfully changed their own password."
        )
        messages.success(request, "Your password has been changed successfully.")
        
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


# ==============================================================================
# ADMINISTRATIVE RECORD DELETION (Patients, Clinical Episodes, MDTs)
# ==============================================================================

@login_required
def patient_delete_view(request, mr_no):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied: Only Administrators can delete patient records.")
        return redirect('patient_search_with_mr', mr_no=mr_no)
        
    patient = get_object_or_404(Patient, mr_no=mr_no)
    pt_name = patient.pt_name
    
    if request.method == 'POST':
        write_audit_log(
            request.user,
            "DELETE_PATIENT",
            "tblPtDetails",
            mr_no,
            f"Permanently deleted patient {pt_name} ({mr_no}) and all cascaded clinical episodes, MDTs, and investigations."
        )
        patient.delete()
        messages.success(request, f"Patient '{pt_name}' ({mr_no}) and all associated records have been permanently deleted.")
        return redirect('patient_search')
        
    return redirect('patient_search_with_mr', mr_no=mr_no)


@login_required
def clinical_delete_view(request, clinical_id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied: Only Administrators can delete clinical episodes.")
        return redirect('clinical_details', clinical_id=clinical_id)
        
    clinical = get_object_or_404(ClinicalDetails, clinical_id=clinical_id)
    mr_no = clinical.patient.mr_no
    mdt_label = clinical.mdt_id or f"Episode #{clinical_id}"
    
    if request.method == 'POST':
        write_audit_log(
            request.user,
            "DELETE_CLINICAL",
            "tblClinicalDetails",
            mr_no,
            f"Deleted Clinical Episode #{clinical_id} ({mdt_label}) and all associated investigations."
        )
        clinical.delete()
        messages.success(request, f"Clinical Episode #{clinical_id} ({mdt_label}) has been deleted.")
        return redirect('patient_search_with_mr', mr_no=mr_no)
        
    return redirect('clinical_details', clinical_id=clinical_id)


@login_required
def mdt_delete_view(request, consensus_id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied: Only Administrators can delete MDT consensus records.")
        return redirect('dashboard')
        
    consensus = get_object_or_404(MDTConsensus, consensus_id=consensus_id)
    clinical = consensus.clinical
    mdt_id = consensus.mdt_id
    mr_no = consensus.patient.mr_no
    
    if request.method == 'POST':
        clinical.status = 'Draft'
        clinical.save(update_fields=['status'])
        
        write_audit_log(
            request.user,
            "DELETE_MDT",
            "tblMDTConsensus",
            mdt_id,
            f"Deleted MDT Consensus ({mdt_id}) for patient {mr_no}. Clinical episode unlocked and returned to Draft."
        )
        consensus.delete()
        messages.success(request, f"MDT Consensus '{mdt_id}' deleted. The clinical episode has been unlocked and returned to Draft.")
        return redirect('clinical_details', clinical_id=clinical.clinical_id)
        
    return redirect('mdt_consensus', consensus_id=consensus_id)


# ==============================================================================
# EXTERNAL DATA BACKUP & RESTORE (JSON Backup Station)
# ==============================================================================

@login_required
def backup_export_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied: Only Administrators can generate external backups.")
        return redirect('dashboard')
        
    def d_to_s(d):
        return d.isoformat() if d else None
        
    def dt_to_s(dt):
        return dt.isoformat() if dt else None

    patients = []
    for p in Patient.objects.all():
        patients.append({
            'mr_no': p.mr_no,
            'pt_name': p.pt_name,
            'sex': p.sex,
            'date_of_birth': d_to_s(p.date_of_birth),
            'diagnosis': p.diagnosis,
            'primary_treatment_site': p.primary_treatment_site,
            'laterality': p.laterality,
            'phone': p.phone,
            'phone_alternate': p.phone_alternate,
            'notes': p.notes,
            'address': p.address,
            'country': p.country,
            'state': p.state,
            'district': p.district,
            'pincode': p.pincode,
            'digipin': p.digipin,
            'entered_by': p.entered_by,
            'entered_on': dt_to_s(p.entered_on),
            'last_modified_by': p.last_modified_by,
            'last_modified_on': dt_to_s(p.last_modified_on),
        })

    clinicals = []
    for c in ClinicalDetails.objects.all():
        clinicals.append({
            'clinical_id': c.clinical_id,
            'mr_no': c.patient.mr_no,
            'mdt_id': c.mdt_id,
            'height': c.height,
            'weight': c.weight,
            'presenting_complaints': c.presenting_complaints,
            'examination_findings': c.examination_findings,
            'prev_tx_history': c.prev_tx_history,
            'diagnosis': c.diagnosis,
            'stage': c.stage,
            'status': c.status,
            'mdt_discussion_for': c.mdt_discussion_for,
            'date_mdt_planned': d_to_s(c.date_mdt_planned),
            'entered_by': c.entered_by,
            'entered_on': dt_to_s(c.entered_on),
            'approved_by': c.approved_by,
            'approved_on': dt_to_s(c.approved_on),
        })

    mdts = []
    for m in MDTConsensus.objects.all():
        mdts.append({
            'consensus_id': m.consensus_id,
            'clinical_id': m.clinical.clinical_id,
            'mr_no': m.patient.mr_no,
            'mdt_id': m.mdt_id,
            'date_mdt_conducted': d_to_s(m.date_mdt_conducted),
            'mdt_discussion': m.mdt_discussion,
            'mdt_consensus': m.mdt_consensus,
            'follow_up_actions': m.follow_up_actions,
            'status': m.status,
            'entered_by': m.entered_by,
            'entered_on': dt_to_s(m.entered_on),
            'approved_by': m.approved_by,
            'approved_on': dt_to_s(m.approved_on),
        })

    bloods = []
    for b in BloodInvestigation.objects.all():
        bloods.append({
            'blood_id': b.blood_id,
            'clinical_id': b.clinical.clinical_id,
            'mr_no': b.patient.mr_no,
            'test_date': d_to_s(b.test_date),
            'specimen_type': b.specimen_type,
            'details': b.details,
            'impression': b.impression,
            'linked_to_mdt': b.linked_to_mdt,
            'entered_by': b.entered_by,
            'entered_on': dt_to_s(b.entered_on),
        })

    imagings = []
    for im in ImagingInvestigation.objects.all():
        imagings.append({
            'imaging_id': im.imaging_id,
            'clinical_id': im.clinical.clinical_id,
            'mr_no': im.patient.mr_no,
            'imaging_date': d_to_s(im.imaging_date),
            'imaging_type': im.imaging_type,
            'site': im.site,
            'details': im.details,
            'impression': im.impression,
            'linked_to_mdt': im.linked_to_mdt,
            'entered_by': im.entered_by,
            'entered_on': dt_to_s(im.entered_on),
        })

    paths = []
    for p in PathologyInvestigation.objects.all():
        paths.append({
            'path_id': p.path_id,
            'clinical_id': p.clinical.clinical_id,
            'mr_no': p.patient.mr_no,
            'path_date': d_to_s(p.path_date),
            'lab_reference_no': p.lab_reference_no,
            'specimen_type': p.specimen_type,
            'site_of_biopsy': p.site_of_biopsy,
            'details': p.details,
            'impression': p.impression,
            'linked_to_mdt': p.linked_to_mdt,
            'entered_by': p.entered_by,
            'entered_on': dt_to_s(p.entered_on),
        })

    mols = []
    for mol in MolecularInvestigation.objects.all():
        mols.append({
            'molecular_id': mol.molecular_id,
            'clinical_id': mol.clinical.clinical_id,
            'mr_no': mol.patient.mr_no,
            'test_date': d_to_s(mol.test_date),
            'lab_reference_no': mol.lab_reference_no,
            'test_type': mol.test_type,
            'details': mol.details,
            'impression': mol.impression,
            'linked_to_mdt': mol.linked_to_mdt,
            'entered_by': mol.entered_by,
            'entered_on': dt_to_s(mol.entered_on),
        })

    audits = []
    for a in AuditLog.objects.all()[:500]:
        audits.append({
            'log_id': a.log_id,
            'log_date_time': dt_to_s(a.log_date_time),
            'username': a.username,
            'full_name': a.full_name,
            'action': a.action,
            'table_affected': a.table_affected,
            'record_ref': a.record_ref,
            'notes': a.notes,
        })

    payload = {
        'format': 'PeadMDT_External_Backup',
        'version': '1.0',
        'export_timestamp': timezone.now().isoformat(),
        'exported_by': request.user.username,
        'summary': {
            'patients': len(patients),
            'clinical_episodes': len(clinicals),
            'mdt_consensuses': len(mdts),
            'investigations': len(bloods) + len(imagings) + len(paths) + len(mols),
            'audit_records': len(audits),
        },
        'data': {
            'patients': patients,
            'clinical_episodes': clinicals,
            'mdt_consensuses': mdts,
            'blood_investigations': bloods,
            'imaging_investigations': imagings,
            'pathology_investigations': paths,
            'molecular_investigations': mols,
            'audit_logs': audits,
        }
    }

    timestamp_str = timezone.now().strftime("%Y%m%d_%H%M%S")
    filename = f"PeadMDT_Backup_{timestamp_str}.json"
    
    write_audit_log(
        request.user, 
        "BACKUP_EXPORT", 
        "Database", 
        filename, 
        f"Exported complete database backup containing {len(patients)} patients, {len(clinicals)} episodes, {len(mdts)} MDTs."
    )

    response = HttpResponse(
        json.dumps(payload, indent=2, ensure_ascii=False), 
        content_type='application/json; charset=utf-8'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def backup_import_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Permission denied: Only Administrators can import data.")
        return redirect('dashboard')
        
    if request.method == 'POST' and request.FILES.get('backup_file'):
        backup_file = request.FILES['backup_file']
        try:
            content = backup_file.read().decode('utf-8-sig')
            payload = json.loads(content)
        except Exception as e:
            messages.error(request, f"Invalid JSON backup file: {str(e)}")
            return redirect('user_admin')
            
        data = payload.get('data', payload)
        
        def s_to_d(s):
            if not s: return None
            try: return datetime.strptime(s.split('T')[0], "%Y-%m-%d").date()
            except: return None
            
        def s_to_dt(s):
            if not s: return None
            try: return timezone.make_aware(datetime.fromisoformat(s.replace('Z', '+00:00')))
            except: 
                try: return timezone.make_aware(datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S"))
                except: return None

        p_cnt = 0
        c_cnt = 0
        m_cnt = 0
        inv_cnt = 0

        try:
            with transaction.atomic():
                # 1. Patients
                for p in data.get('patients', []):
                    Patient.objects.update_or_create(
                        mr_no=p['mr_no'],
                        defaults={
                            'pt_name': p.get('pt_name', ''),
                            'sex': p.get('sex', 'Male'),
                            'date_of_birth': s_to_d(p.get('date_of_birth')),
                            'diagnosis': p.get('diagnosis', ''),
                            'primary_treatment_site': p.get('primary_treatment_site', ''),
                            'laterality': p.get('laterality', ''),
                            'phone': p.get('phone', ''),
                            'phone_alternate': p.get('phone_alternate'),
                            'notes': p.get('notes'),
                            'address': p.get('address'),
                            'country': p.get('country', 'India'),
                            'state': p.get('state', 'Karnataka'),
                            'district': p.get('district'),
                            'pincode': p.get('pincode'),
                            'digipin': p.get('digipin'),
                            'entered_by': p.get('entered_by') or request.user.username,
                            'entered_on': s_to_dt(p.get('entered_on')) or timezone.now(),
                            'last_modified_by': request.user.username,
                            'last_modified_on': timezone.now(),
                        }
                    )
                    p_cnt += 1

                # 2. Clinical Details
                for c in data.get('clinical_episodes', []):
                    patient = Patient.objects.filter(mr_no=c['mr_no']).first()
                    if patient:
                        ClinicalDetails.objects.update_or_create(
                            clinical_id=c['clinical_id'],
                            defaults={
                                'patient': patient,
                                'mdt_id': c.get('mdt_id'),
                                'height': c.get('height') or 0,
                                'weight': c.get('weight') or 0,
                                'presenting_complaints': c.get('presenting_complaints'),
                                'examination_findings': c.get('examination_findings'),
                                'prev_tx_history': c.get('prev_tx_history'),
                                'diagnosis': c.get('diagnosis'),
                                'stage': c.get('stage'),
                                'status': c.get('status', 'Draft'),
                                'mdt_discussion_for': c.get('mdt_discussion_for'),
                                'date_mdt_planned': s_to_d(c.get('date_mdt_planned')),
                                'entered_by': c.get('entered_by') or request.user.username,
                                'entered_on': s_to_dt(c.get('entered_on')) or timezone.now(),
                                'approved_by': c.get('approved_by'),
                                'approved_on': s_to_dt(c.get('approved_on')),
                            }
                        )
                        c_cnt += 1

                # 3. MDT Consensuses
                for m in data.get('mdt_consensuses', []):
                    clinical = ClinicalDetails.objects.filter(clinical_id=m['clinical_id']).first()
                    patient = Patient.objects.filter(mr_no=m['mr_no']).first()
                    if clinical and patient:
                        MDTConsensus.objects.update_or_create(
                            clinical=clinical,
                            defaults={
                                'patient': patient,
                                'mdt_id': m.get('mdt_id'),
                                'date_mdt_conducted': s_to_d(m.get('date_mdt_conducted')),
                                'mdt_discussion': m.get('mdt_discussion'),
                                'mdt_consensus': m.get('mdt_consensus'),
                                'follow_up_actions': m.get('follow_up_actions'),
                                'status': m.get('status', 'Draft'),
                                'entered_by': m.get('entered_by') or request.user.username,
                                'entered_on': s_to_dt(m.get('entered_on')) or timezone.now(),
                                'approved_by': m.get('approved_by'),
                                'approved_on': s_to_dt(m.get('approved_on')),
                            }
                        )
                        m_cnt += 1

                # 4. Blood Investigations
                for b in data.get('blood_investigations', []):
                    clin = ClinicalDetails.objects.filter(clinical_id=b['clinical_id']).first()
                    pt = Patient.objects.filter(mr_no=b['mr_no']).first()
                    if clin and pt:
                        BloodInvestigation.objects.update_or_create(
                            blood_id=b.get('blood_id'),
                            defaults={
                                'clinical': clin,
                                'patient': pt,
                                'test_date': s_to_d(b.get('test_date')) or date.today(),
                                'specimen_type': b.get('specimen_type', 'Blood'),
                                'details': b.get('details'),
                                'impression': b.get('impression'),
                                'linked_to_mdt': bool(b.get('linked_to_mdt', True)),
                                'entered_by': b.get('entered_by') or request.user.username,
                                'entered_on': s_to_dt(b.get('entered_on')) or timezone.now(),
                            }
                        )
                        inv_cnt += 1

                # 5. Imaging
                for im in data.get('imaging_investigations', []):
                    clin = ClinicalDetails.objects.filter(clinical_id=im['clinical_id']).first()
                    pt = Patient.objects.filter(mr_no=im['mr_no']).first()
                    if clin and pt:
                        ImagingInvestigation.objects.update_or_create(
                            imaging_id=im.get('imaging_id'),
                            defaults={
                                'clinical': clin,
                                'patient': pt,
                                'imaging_date': s_to_d(im.get('imaging_date')) or date.today(),
                                'imaging_type': im.get('imaging_type', 'CT'),
                                'site': im.get('site', ''),
                                'details': im.get('details'),
                                'impression': im.get('impression'),
                                'linked_to_mdt': bool(im.get('linked_to_mdt', True)),
                                'entered_by': im.get('entered_by') or request.user.username,
                                'entered_on': s_to_dt(im.get('entered_on')) or timezone.now(),
                            }
                        )
                        inv_cnt += 1

                # 6. Pathology
                for p in data.get('pathology_investigations', []):
                    clin = ClinicalDetails.objects.filter(clinical_id=p['clinical_id']).first()
                    pt = Patient.objects.filter(mr_no=p['mr_no']).first()
                    if clin and pt:
                        PathologyInvestigation.objects.update_or_create(
                            path_id=p.get('path_id'),
                            defaults={
                                'clinical': clin,
                                'patient': pt,
                                'path_date': s_to_d(p.get('path_date')) or date.today(),
                                'lab_reference_no': p.get('lab_reference_no', ''),
                                'specimen_type': p.get('specimen_type', ''),
                                'site_of_biopsy': p.get('site_of_biopsy', ''),
                                'details': p.get('details'),
                                'impression': p.get('impression'),
                                'linked_to_mdt': bool(p.get('linked_to_mdt', True)),
                                'entered_by': p.get('entered_by') or request.user.username,
                                'entered_on': s_to_dt(p.get('entered_on')) or timezone.now(),
                            }
                        )
                        inv_cnt += 1

                # 7. Molecular
                for mol in data.get('molecular_investigations', []):
                    clin = ClinicalDetails.objects.filter(clinical_id=mol['clinical_id']).first()
                    pt = Patient.objects.filter(mr_no=mol['mr_no']).first()
                    if clin and pt:
                        MolecularInvestigation.objects.update_or_create(
                            molecular_id=mol.get('molecular_id'),
                            defaults={
                                'clinical': clin,
                                'patient': pt,
                                'test_date': s_to_d(mol.get('test_date')) or date.today(),
                                'lab_reference_no': mol.get('lab_reference_no', ''),
                                'test_type': mol.get('test_type', ''),
                                'details': mol.get('details'),
                                'impression': mol.get('impression'),
                                'linked_to_mdt': bool(mol.get('linked_to_mdt', True)),
                                'entered_by': mol.get('entered_by') or request.user.username,
                                'entered_on': s_to_dt(mol.get('entered_on')) or timezone.now(),
                            }
                        )
                        inv_cnt += 1

            write_audit_log(
                request.user,
                "BACKUP_IMPORT",
                "Database",
                backup_file.name,
                f"Import completed: {p_cnt} patients, {c_cnt} episodes, {m_cnt} MDTs, {inv_cnt} investigations."
            )
            messages.success(
                request, 
                f"✅ Backup imported successfully! Processed {p_cnt} Patients, {c_cnt} Clinical Episodes, {m_cnt} MDT Consensuses, and {inv_cnt} Investigations."
            )
        except Exception as err:
            messages.error(request, f"Error occurred during backup restoration: {str(err)}")
            
    return redirect('user_admin')


# Dynamic district cascade helper
def api_districts(request):
    state_name = request.GET.get('state', '')
    districts = District.objects.filter(state__state_name=state_name).values_list('district_name', flat=True).order_by('district_name')
    return JsonResponse({'districts': list(districts)})
