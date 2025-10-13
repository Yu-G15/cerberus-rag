"""
URL configuration for cerberus_ms_rest project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('dfd.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

from django.http import JsonResponse
def healthz(request):
    return JsonResponse({"status": "ok"})

urlpatterns += [
    path("healthz/", healthz),
]

from django.urls import path
from django.http import JsonResponse
import os, httpx, asyncio

AGENTS_URL = os.getenv("AGENTS_URL", "http://cerberus-gai-agents:8001")

async def ask_agent_async(q: str):
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{AGENTS_URL}/analyze", json={"question": q})
        r.raise_for_status()
        return r.json()

def ask(request):
    q = request.GET.get("q", "ping")
    data = asyncio.run(ask_agent_async(q))
    return JsonResponse(data)

urlpatterns += [
    path("healthz/", lambda r: JsonResponse({"status":"ok"})),
    path("ask/", ask),
]
