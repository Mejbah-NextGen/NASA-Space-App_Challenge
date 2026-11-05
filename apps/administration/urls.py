from django.urls import path

from . import views


app_name = "administration"
urlpatterns = [
    path("dashboard/", views.AdminDashboardView.as_view(), name="dashboard"),
    path("users/", views.UserManagementView.as_view(), name="users"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user_detail"),
    path("users/<int:pk>/status/", views.UserStatusView.as_view(), name="user_status"),
    path("agriculturalists/", views.AgriculturalistListView.as_view(), name="agriculturalists"),
    path("agriculturalists/<int:pk>/review/", views.AgriculturalistReviewView.as_view(), name="agriculturalist_review"),
    path("farmers/", views.FarmerListView.as_view(), name="farmers"),
    path("data/", views.DataManagementView.as_view(), name="data"),
    path("data/sources/add/", views.DataSourceCreateView.as_view(), name="data_source_create"),
    path("data/sources/<int:pk>/edit/", views.DataSourceUpdateView.as_view(), name="data_source_update"),
    path("data/datasets/add/", views.AgriculturalDatasetCreateView.as_view(), name="dataset_create"),
    path("data/datasets/<int:pk>/edit/", views.AgriculturalDatasetUpdateView.as_view(), name="dataset_update"),
    path("data/crops/add/", views.CropCatalogCreateView.as_view(), name="crop_create"),
    path("data/crops/<int:pk>/edit/", views.CropCatalogUpdateView.as_view(), name="crop_update"),
    path("data/crops/<int:pk>/toggle/", views.CropCatalogToggleView.as_view(), name="crop_toggle"),
    path("farms/", views.FarmOverviewView.as_view(), name="farms"),
    path("assignments/", views.AssignmentListView.as_view(), name="assignments"),
    path("assignments/assign/", views.AssignmentActionView.as_view(), name="assignment_action"),
    path("reports/", views.ReportsView.as_view(), name="reports"),
    path("reports/export/", views.ReportExportView.as_view(), name="report_export"),
    path("weather/", views.WeatherManagementView.as_view(), name="weather"),
    path("weather/alerts/create/", views.WeatherAlertCreateView.as_view(), name="weather_alert_create"),
    path("weather/alerts/<int:pk>/toggle/", views.WeatherAlertToggleView.as_view(), name="weather_alert_toggle"),
    path("content/", views.ContentReviewView.as_view(), name="content"),
    path("content/<int:pk>/review/", views.ContentReviewActionView.as_view(), name="content_review"),
    path("settings/", views.SystemSettingsView.as_view(), name="settings"),
    path("settings/public/<int:pk>/", views.PublicPlatformSettingUpdateView.as_view(), name="public_setting_update"),
    path("logs/", views.AuditLogView.as_view(), name="logs"),
    path("support/", views.SupportManagementView.as_view(), name="support"),
    path("support/<int:pk>/", views.SupportTicketUpdateView.as_view(), name="support_ticket"),
]
