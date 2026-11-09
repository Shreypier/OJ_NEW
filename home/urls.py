from django.urls import path
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static

from home.views import start, problem_details, manage_problem, logout_user, logout_employee
from Online_Compiler.views import submit_page, submission_detail, submission_list

urlpatterns = [
    path('', start, name="home-start"),
    path('problem/id=<int:id>/', problem_details, name="problem-details"),
    path('id=<int:id>/submit/', submit_page, name="submit-page"),
    path('submission/<int:sub_id>/', submission_detail, name="submission-detail"),
    path('submissions/', submission_list, name="submission-list"),
    path('employee/', manage_problem, name="manage_problem"),
    path('logout/', logout_user, name="logout-user"),
    path('employee_logout/', logout_employee, name="logout-employee"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += staticfiles_urlpatterns()
