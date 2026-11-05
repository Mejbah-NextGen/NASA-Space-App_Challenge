from django.db.models import Count, Q
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.models import AgriculturalistVerification, User
from apps.accounts.permissions import AgriculturalistRequiredMixin, FarmerRequiredMixin


class FarmerDashboardView(FarmerRequiredMixin, TemplateView):
    template_name = "dashboard/farmer_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        from apps.consultations.models import Consultation
        from apps.decisions.models import FarmingDecision
        from apps.farms.models import CropPlanting, Farm, FarmActivity, FarmTask
        from apps.weather.models import WeatherAlert

        farms = Farm.objects.filter(owner=user, is_archived=False)
        context.update(
            {
                "farms": farms[:4],
                "farm_count": farms.count(),
                "active_crop_count": CropPlanting.objects.filter(
                    field__farm__owner=user,
                    status__in=[CropPlanting.Status.PLANNED, CropPlanting.Status.PLANTED, CropPlanting.Status.GROWING],
                ).count(),
                "upcoming_tasks": FarmTask.objects.filter(
                    farm__owner=user,
                ).exclude(
                    status__in=[FarmTask.Status.COMPLETED, FarmTask.Status.CANCELLED]
                ).select_related("farm")[:5],
                "recent_activities": FarmActivity.objects.filter(
                    farm__owner=user
                ).select_related("farm")[:5],
                "recent_decisions": FarmingDecision.objects.filter(owner=user).select_related("farm")[:4],
                "consultations": Consultation.objects.filter(farmer=user)[:4],
                "active_consultation_count": Consultation.objects.filter(
                    farmer=user,
                    status__in=[Consultation.Status.PENDING, Consultation.Status.ASSIGNED, Consultation.Status.ACTIVE],
                ).count(),
                "weather_alerts": WeatherAlert.objects.filter(
                    Q(region__district__iexact=user.district), is_active=True
                ).select_related("region", "source")[:3],
                "today": timezone.localdate(),
            }
        )
        return context


class AgriculturalistDashboardView(AgriculturalistRequiredMixin, TemplateView):
    template_name = "dashboard/agriculturalist_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.consultations.models import Consultation, ExpertAssignment, ExpertRecommendation
        from apps.weather.models import WeatherAlert

        user = self.request.user
        assignments = ExpertAssignment.objects.filter(agriculturalist=user, is_active=True)
        consultations = Consultation.objects.filter(assignment__in=assignments)
        context.update(
            {
                "assigned_farmer_count": assignments.values("farmer").distinct().count(),
                "pending_consultation_count": consultations.filter(
                    status__in=[Consultation.Status.ASSIGNED, Consultation.Status.ACTIVE]
                ).count(),
                "completed_consultation_count": consultations.filter(status=Consultation.Status.COMPLETED).count(),
                "active_recommendation_count": ExpertRecommendation.objects.filter(
                    agriculturalist=user,
                    status__in=[ExpertRecommendation.Status.DRAFT, ExpertRecommendation.Status.PUBLISHED],
                ).count(),
                "recent_consultations": consultations.select_related("farmer", "farm")[:6],
                "weather_alerts": WeatherAlert.objects.filter(is_active=True)[:4],
            }
        )
        return context
