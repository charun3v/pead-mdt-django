from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Auth
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Patient Registration, Edit & Delete
    path('patient/register/', views.patient_reg_view, name='patient_reg'),
    path('patient/<str:mr_no>/edit/', views.patient_reg_view, name='patient_edit'),
    path('patient/<str:mr_no>/delete/', views.patient_delete_view, name='patient_delete'),

    # Patient Search & Cockpit
    path('patient/search/', views.patient_search_view, name='patient_search'),
    path('patient/<str:mr_no>/', views.patient_search_view, name='patient_search_with_mr'),

    # Clinical Episode Details & Delete
    path('clinical/<int:clinical_id>/', views.clinical_details_view, name='clinical_details'),
    path('clinical/new/<str:mr_no>/', views.clinical_details_view, name='clinical_new'),
    path('clinical/<int:clinical_id>/delete/', views.clinical_delete_view, name='clinical_delete'),

    # Modal Investigation Actions
    path('clinical/<int:clinical_id>/add/<str:inv_type>/', views.add_investigation_view, name='add_investigation'),
    path('investigation/<str:inv_type>/<int:inv_id>/delete/', views.delete_investigation_view, name='delete_investigation'),

    # Attachments
    path('clinical/<int:clinical_id>/upload/', views.upload_attachment_view, name='upload_attachment'),
    path('attachment/<int:attachment_id>/download/', views.download_attachment_view, name='download_attachment'),

    # MDT Consensus & Delete
    path('mdt/<int:consensus_id>/', views.mdt_consensus_view, name='mdt_consensus'),
    path('mdt/<int:consensus_id>/delete/', views.mdt_delete_view, name='mdt_delete'),

    # Reports
    path('report/clinical/<int:clinical_id>/', views.report_clinical_summary_view, name='report_clinical'),
    path('report/mdt/<str:mdt_id>/', views.report_mdt_full_view, name='report_mdt'),

    # User Management & Database Backup/Restore
    path('admin/users/', views.user_admin_view, name='user_admin'),
    path('admin/users/create/', views.user_create_view, name='user_create'),
    path('admin/users/<int:user_id>/edit/', views.user_edit_view, name='user_edit'),
    path('admin/users/<int:user_id>/reset-password/', views.user_reset_password_view, name='user_reset_password'),
    path('admin/users/<int:user_id>/toggle-status/', views.user_toggle_status_view, name='user_toggle_status'),
    path('admin/users/<int:user_id>/delete/', views.user_delete_view, name='user_delete'),
    path('user/change-password/', views.user_change_password_view, name='user_change_password'),
    path('admin/backup/export/', views.backup_export_view, name='backup_export'),
    path('admin/backup/import/', views.backup_import_view, name='backup_import'),

    # AJAX Helper
    path('api/districts/', views.api_districts, name='api_districts'),
]
