"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from accounts.views import login_view

urlpatterns = [
    path("", include("tickets.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("login/", login_view, name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("kb/", include("knowledgebase.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("core/", include("core.urls")),
    path("ai/", include("aiassist.urls")),
    path("notifications/", include("notifications.urls")),
    path("audit/", include("auditlog.urls")),
    path("ops/", include("ops.urls")),
    path("api/", include("api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = "core.views.error_400"

handler403 = "core.views.error_403"

handler404 = "core.views.error_404"

handler500 = "core.views.error_500"
