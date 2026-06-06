from django.urls import path
from monitors.views import MonitorListView, MonitorDetailView

urlpatterns = [
    path('monitors/', MonitorListView.as_view(), name='monitor-list'),
    path('monitors/<str:device_id>/', MonitorDetailView.as_view(), name='monitor-detail'),
]
