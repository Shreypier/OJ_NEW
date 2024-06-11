from django.urls import path
from django.contrib import admin
from home.views import starts,problem_details,add_problem,logout_user,problems  # Import views from the authentication app
from django.conf import settings   # Application settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from Online_Compiler.views import submit_page
from django.conf.urls.static import static

urlpatterns = [
    path('',starts,name="home-start"),
    path('problem/id=<int:id>/',problem_details,name="problem-details"),
    path('problems/',problems,name="problems"),
    path('id=<int:id>/submit/',submit_page,name="submit-page"),
    path('employee/add_problem/',add_problem,name="add-problem"),
     path('logout/',logout_user,name="logout-user"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
 
# Serve static files using staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()

