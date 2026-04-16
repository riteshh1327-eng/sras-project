"""SRAS URL Configuration"""

from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('', views.home, name='home'),
    path('notices/', views.public_notices, name='public_notices'),

    # Auth
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── Teacher Dashboard ──────────────────────────────────────────────────
    path('dashboard/', views.dashboard, name='dashboard'),

    # Classes
    path('classes/',                    views.class_list,   name='class_list'),
    path('classes/create/',             views.class_create, name='class_create'),
    path('classes/<int:pk>/edit/',      views.class_edit,   name='class_edit'),
    path('classes/<int:pk>/delete/',    views.class_delete, name='class_delete'),

    # Subjects
    path('subjects/',                   views.subject_list,   name='subject_list'),
    path('subjects/create/',            views.subject_create, name='subject_create'),
    path('subjects/<int:pk>/edit/',     views.subject_edit,   name='subject_edit'),
    path('subjects/<int:pk>/delete/',   views.subject_delete, name='subject_delete'),

    # Subject Combinations
    path('combinations/',               views.combination_list,   name='combination_list'),
    path('combinations/create/',        views.combination_create, name='combination_create'),
    path('combinations/<int:pk>/edit/', views.combination_edit,   name='combination_edit'),
    path('combinations/<int:pk>/delete/', views.combination_delete, name='combination_delete'),

    # Students (permanent profiles — no class/roll here)
    path('students/',                   views.student_list,         name='student_list'),
    path('students/add/',               views.student_create,       name='student_create'),
    path('students/upload/',            views.student_upload_excel, name='student_upload'),
    path('students/download-sample/',   views.download_sample_excel,name='download_sample_excel'),
    path('students/<int:pk>/',          views.student_detail,       name='student_detail'),
    path('students/<int:pk>/edit/',     views.student_edit,         name='student_edit'),
    path('students/<int:pk>/delete/',   views.student_delete,       name='student_delete'),

    # Legacy Results (kept for pattern analysis)
    path('results/',                                    views.result_list,  name='result_list'),
    path('results/add/',                                views.result_add,   name='result_add'),
    path('results/enter/<int:class_id>/<int:subject_id>/', views.result_enter, name='result_enter'),

    # Pattern Analysis
    path('analysis/pattern/',    views.pattern_analysis,   name='pattern_analysis'),
    path('analysis/export-csv/', views.export_failure_csv, name='export_failure_csv'),

    # Notices
    path('notices/manage/',           views.notice_list,   name='notice_list'),
    path('notices/add/',              views.notice_create, name='notice_create'),
    path('notices/<int:pk>/edit/',    views.notice_edit,   name='notice_edit'),
    path('notices/<int:pk>/delete/',  views.notice_delete, name='notice_delete'),

    # ── Student Portal ─────────────────────────────────────────────────────
    path('student/dashboard/',          views.student_dashboard,        name='student_dashboard'),
    path('student/results/',            views.student_results,          name='student_results'),
    path('student/results/<int:subject_id>/', views.student_subject_detail, name='student_subject_detail'),
    path('student/performance/',        views.student_performance,      name='student_performance'),
    path('student/notices/',            views.student_notices,          name='student_notices'),
    path('student/export-csv/',         views.student_export_results_csv, name='student_export_csv'),

    # AJAX
    path('api/subjects-for-class/', views.get_subjects_for_class, name='subjects_for_class'),
]


# ── Result Engine URLs ─────────────────────────────────────────────────────────
from . import result_views as rv

urlpatterns += [

    # Enrollment management (Teacher)
    path('engine/enrollments/',                     rv.enrollment_list,   name='re_enrollment_list'),
    path('engine/enrollments/add/',                 rv.enrollment_create, name='re_enrollment_create'),
    path('engine/enrollments/<int:pk>/delete/',     rv.enrollment_delete, name='re_enrollment_delete'),

    # Semester Subjects (Teacher)
    path('engine/subjects/',                        rv.semester_subject_list,   name='re_semester_subject_list'),
    path('engine/subjects/create/',                 rv.semester_subject_create, name='re_semester_subject_create'),
    path('engine/subjects/<int:pk>/edit/',          rv.semester_subject_edit,   name='re_semester_subject_edit'),
    path('engine/subjects/<int:pk>/delete/',        rv.semester_subject_delete, name='re_semester_subject_delete'),

    # Bulk Result Entry (Teacher)
    path('results/engine/bulk/',                    rv.bulk_result_entry, name='re_bulk_entry'),
    path('results/engine/bulk/save/',               rv.bulk_result_save,  name='re_bulk_save'),

    # Class Results / Analytics (Teacher) — no topper/rank
    path('results/engine/class/',                   rv.enhanced_result_list, name='re_result_list'),
    path('analytics/teacher/',                      rv.teacher_analytics,    name='re_teacher_analytics'),

    # Student Portal (Enrollment-centric)
    path('student/results/explore/',                rv.student_result_explorer,       name='student_result_explorer'),
    path('student/results/subject/<int:ss_id>/',    rv.student_subject_detail_enhanced, name='re_subject_detail'),
    path('student/marksheet/<str:semester>/<str:academic_year>/',
                                                    rv.student_marksheet,            name='re_marksheet'),
    path('student/marksheet/<str:semester>/<str:academic_year>/<int:student_pk>/pdf/',
                                                    rv.student_marksheet_pdf,        name='re_marksheet_pdf'),
    path('student/performance/enhanced/',           rv.student_performance_enhanced, name='re_student_performance'),

    # AJAX
    path('api/engine/semester-subjects/',           rv.ajax_semester_subjects,          name='re_ajax_semester_subjects'),
    path('api/engine/years-for-class/',             rv.ajax_academic_years_for_class,   name='re_ajax_years_for_class'),
]
