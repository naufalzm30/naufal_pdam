from django.urls import path, include
from .views import (PDAMDashboardView, StationView, MaintenanceRecordTableView,
                     MaintenanceRecordDView, SensorDataTableView, DataStationView,
                     LoggerView,SensorTypeView, ChannelView,
                     UploadCSVAPIView, PublishResendView)
urlpatterns = [
  path("dashboard/", PDAMDashboardView.as_view()),
  path("station/", StationView.as_view()),
  path("station/<str:station_serial_id>/", StationView.as_view()),
  
  path("maintenance_table/<str:station_serial_id>/", MaintenanceRecordTableView.as_view()),
  path("maintenance/<str:station_serial_id>/", MaintenanceRecordDView.as_view()),
 
  path("sensor_data/<str:station_serial_id>/", SensorDataTableView.as_view()),
  path("station_data/<str:station_serial_id>/",DataStationView.as_view()),

  path("logger_type/",LoggerView.as_view()),
  path("logger_type/<int:pk>/",LoggerView.as_view()),
 
  path("sensor_type/",SensorTypeView.as_view()),
  path("sensor_type/<int:pk>/",SensorTypeView.as_view()),
  
  path("channel/",ChannelView.as_view()),
  path("upload_threshold/<str:station_serial_id>",UploadCSVAPIView.as_view()),
  path("resend/",PublishResendView.as_view()),
]
