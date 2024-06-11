
from django.urls import path
from accounts.views import register_user,login_user,login_employee  # Import views from the authentication app
from django.conf import settings   # Application settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static

urlpatterns = [
    path("register/",register_user,name="register-user"),
    path("login/",login_user,name="login-user"),
    path("employee_login/",login_employee,name="login-employee"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
 
# Serve static files using staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()