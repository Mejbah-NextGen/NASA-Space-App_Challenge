import csv
from datetime import date

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.accounts.models import AgriculturalistProfile, AgriculturalistVerification, User
from apps.accounts.permissions import PlatformAdminRequiredMixin
from apps.agricultural_data.models import AgriculturalDataset, DataSource
from apps.farms.models import Crop

from .forms import (
    DataUploadForm,
    AgriculturalDatasetForm,
    CropCatalogForm,
    CropCatalogToggleForm,
    DataSourceForm,
    ExpertAssignmentForm,
    LearningReviewForm,
    PublicPlatformSettingForm,
    SupportTicketUpdateForm,
    UserStatusForm,
    VerificationReviewForm,
    WeatherAlertForm,
    WeatherAlertToggleForm,
)
from .models import AuditLog
from .services import record_audit


def safe_csv(value):
    text = str(value or "")
    return f"'{text}" if text[:1] in {"=", "+", "-", "@"} else text


class AdminDashboardView(PlatformAdminRequiredMixin, TemplateView):
    template_name = "admin_dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.consultations.models import Consultation
        from apps.farms.models import Farm
        from apps.weather.models import WeatherAlert

        context.update(
            {
                "total_users": User.objects.count(),
                "total_farmers": User.objects.filter(role=User.Role.FARMER).count(),
                "total_agriculturalists": User.objects.filter(role=User.Role.AGRICULTURALIST).count(),
                "pending_approvals": AgriculturalistVerification.objects.filter(
                    status=AgriculturalistVerification.Status.PENDING
                ).count(),
                "total_farms": Farm.objects.filter(is_archived=False).count(),
                "active_consultations": Consultation.objects.exclude(
                    status__in=[Consultation.Status.COMPLETED, Consultation.Status.CANCELLED, Consultation.Status.DECLINED]
                ).count(),
                "weather_alerts": WeatherAlert.objects.filter(is_active=True).count(),
                "recent_audits": AuditLog.objects.select_related("actor")[:8],
                "role_distribution": list(
                    User.objects.values("role").annotate(total=Count("id")).order_by("role")
                ),
            }
        )
        return context


class UserManagementView(PlatformAdminRequiredMixin, ListView):
    template_name = "admin_dashboard/users.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.order_by("full_name")
        query = self.request.GET.get("q", "").strip()
        role = self.request.GET.get("role", "").strip()
        status = self.request.GET.get("status", "").strip()
        if query:
            queryset = queryset.filter(Q(full_name__icontains=query) | Q(email__icontains=query) | Q(district__icontains=query))
        if role in User.Role.values:
            queryset = queryset.filter(role=role)
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "suspended":
            queryset = queryset.filter(is_active=False)
        return queryset


class UserDetailView(PlatformAdminRequiredMixin, DetailView):
    model = User
    template_name = "admin_dashboard/user_detail.html"
    context_object_name = "account"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.consultations.models import Consultation, ExpertAssignment
        from apps.farms.models import Farm

        context.update(
            {
                "farm_count": Farm.objects.filter(owner=self.object).count(),
                "farmer_consultation_count": Consultation.objects.filter(farmer=self.object).count(),
                "expert_consultation_count": Consultation.objects.filter(agriculturalist=self.object).count(),
                "active_assignment_count": ExpertAssignment.objects.filter(
                    Q(farmer=self.object) | Q(agriculturalist=self.object),
                    is_active=True,
                ).count(),
            }
        )
        return context


class UserStatusView(PlatformAdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = UserStatusForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Select a valid account action.")
            return redirect("administration:users")
        if user == request.user and form.cleaned_data["action"] == "suspend":
            messages.error(request, "You cannot suspend your own active session.")
            return redirect("administration:users")
        user.is_active = form.cleaned_data["action"] == "activate"
        user.save(update_fields=["is_active"])
        record_audit(request, f"user.{form.cleaned_data['action']}", user)
        messages.success(request, f"{user.email} was {'activated' if user.is_active else 'suspended'}.")
        return redirect("administration:users")


class AgriculturalistListView(PlatformAdminRequiredMixin, ListView):
    model = AgriculturalistProfile
    template_name = "admin_dashboard/agriculturalists.html"
    context_object_name = "agriculturalists"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("user")
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(user__full_name__icontains=query)
                | Q(user__email__icontains=query)
                | Q(specialization__icontains=query)
            )
        return queryset.order_by("user__full_name")


class AgriculturalistReviewView(PlatformAdminRequiredMixin, DetailView):
    model = AgriculturalistVerification
    template_name = "admin_dashboard/agriculturalist_review.html"
    context_object_name = "verification"

    def get_queryset(self):
        return super().get_queryset().select_related("agriculturalist__user", "reviewer")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = VerificationReviewForm(instance=self.object)
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = VerificationReviewForm(request.POST, instance=self.object)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))
        verification = form.save(commit=False)
        verification.reviewer = request.user
        verification.reviewed_at = timezone.now()
        verification.save()
        profile = verification.agriculturalist
        approved = verification.status == AgriculturalistVerification.Status.APPROVED
        profile.is_approved = approved
        profile.approved_at = timezone.now() if approved else None
        profile.save(update_fields=["is_approved", "approved_at"])
        record_audit(request, f"expert.{verification.status.lower()}", profile.user)
        messages.success(request, "The professional verification decision was recorded.")
        return redirect("administration:agriculturalists")


class FarmerListView(PlatformAdminRequiredMixin, ListView):
    template_name = "admin_dashboard/farmers.html"
    context_object_name = "farmers"
    paginate_by = 20

    def get_queryset(self):
        return User.objects.filter(role=User.Role.FARMER).annotate(farm_total=Count("farms")).order_by("full_name")


class DataManagementView(PlatformAdminRequiredMixin, TemplateView):
    template_name = "admin_dashboard/data.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.agricultural_data.models import AgriculturalDataset, DataImportJob, DataSource
        from apps.farms.models import Crop

        context.update(
            {
                "sources": DataSource.objects.all(),
                "datasets": AgriculturalDataset.objects.select_related("source")[:20],
                "import_jobs": DataImportJob.objects.select_related("dataset")[:10],
                "crops": Crop.objects.all()[:50],
                "upload_form": kwargs.get("upload_form") or DataUploadForm(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        from apps.agricultural_data.services import DataImportValidationError, import_historical_csv

        form = DataUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(upload_form=form))
        try:
            job = import_historical_csv(
                dataset=form.cleaned_data["dataset"],
                upload=form.cleaned_data["csv_file"],
                kind=form.cleaned_data["kind"],
                actor=request.user,
            )
        except DataImportValidationError as exc:
            messages.error(request, "Import failed: " + "; ".join(exc.messages[:3]))
        else:
            record_audit(request, "dataset.csv_imported", form.cleaned_data["dataset"], metadata={"rows": job.rows_imported})
            messages.success(request, f"Imported {job.rows_imported} validated rows.")
        return redirect("administration:data")


class AuditedDataModelFormMixin:
    template_name = "admin_dashboard/data_form.html"
    success_url_name = "administration:data"
    entity_label = "Record"
    audit_prefix = "data_record"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entity_label"] = self.entity_label
        return context

    def get_success_url(self):
        return reverse(self.success_url_name)

    def audit_metadata(self):
        return {}

    def form_valid(self, form):
        created = self.object is None
        response = super().form_valid(form)
        event = "created" if created else "updated"
        record_audit(
            self.request,
            f"{self.audit_prefix}.{event}",
            self.object,
            metadata=self.audit_metadata(),
        )
        messages.success(self.request, f"{self.entity_label} was {event}.")
        return response


class DataSourceCreateView(PlatformAdminRequiredMixin, AuditedDataModelFormMixin, CreateView):
    form_class = DataSourceForm
    entity_label = "Data source"
    audit_prefix = "data_source"

    def audit_metadata(self):
        return {"kind": self.object.kind, "is_demo": self.object.is_demo, "is_active": self.object.is_active}


class DataSourceUpdateView(PlatformAdminRequiredMixin, AuditedDataModelFormMixin, UpdateView):
    model = DataSource
    form_class = DataSourceForm
    entity_label = "Data source"
    audit_prefix = "data_source"

    def audit_metadata(self):
        return {"kind": self.object.kind, "is_demo": self.object.is_demo, "is_active": self.object.is_active}


class AgriculturalDatasetCreateView(PlatformAdminRequiredMixin, AuditedDataModelFormMixin, CreateView):
    form_class = AgriculturalDatasetForm
    entity_label = "Agricultural dataset"
    audit_prefix = "agricultural_dataset"

    def audit_metadata(self):
        return {"status": self.object.status, "source_id": self.object.source_id}


class AgriculturalDatasetUpdateView(PlatformAdminRequiredMixin, AuditedDataModelFormMixin, UpdateView):
    model = AgriculturalDataset
    form_class = AgriculturalDatasetForm
    entity_label = "Agricultural dataset"
    audit_prefix = "agricultural_dataset"

    def audit_metadata(self):
        return {"status": self.object.status, "source_id": self.object.source_id}


class CropCatalogCreateView(PlatformAdminRequiredMixin, AuditedDataModelFormMixin, CreateView):
    form_class = CropCatalogForm
    entity_label = "Crop catalog entry"
    audit_prefix = "crop_catalog"

    def audit_metadata(self):
        return {"is_supported": self.object.is_supported}


class CropCatalogUpdateView(PlatformAdminRequiredMixin, AuditedDataModelFormMixin, UpdateView):
    model = Crop
    form_class = CropCatalogForm
    entity_label = "Crop catalog entry"
    audit_prefix = "crop_catalog"

    def audit_metadata(self):
        return {"is_supported": self.object.is_supported}


class CropCatalogToggleView(PlatformAdminRequiredMixin, View):
    def post(self, request, pk):
        from apps.farms.models import Crop

        crop = get_object_or_404(Crop, pk=pk)
        form = CropCatalogToggleForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Select a valid crop catalog action.")
            return redirect("administration:data")
        supported = form.cleaned_data["action"] == "support"
        if crop.is_supported == supported:
            messages.info(request, f"{crop} already has that catalog state.")
            return redirect("administration:data")
        crop.is_supported = supported
        crop.save(update_fields=["is_supported", "updated_at"])
        event = "activated" if supported else "deactivated"
        record_audit(request, f"crop_catalog.{event}", crop)
        messages.success(request, f"{crop} was {event} in the supported crop catalog.")
        return redirect("administration:data")


class FarmOverviewView(PlatformAdminRequiredMixin, TemplateView):
    template_name = "admin_dashboard/farms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.farms.models import CropPlanting, Farm

        context["farm_count"] = Farm.objects.filter(is_archived=False).count()
        context["regional_summary"] = Farm.objects.filter(is_archived=False).values("district").annotate(total=Count("id")).order_by("-total")[:12]
        context["crop_summary"] = CropPlanting.objects.values("crop__name").annotate(total=Count("id")).order_by("-total")[:12]
        context["recent_farms"] = Farm.objects.select_related("owner")[:10]
        return context


class AssignmentListView(PlatformAdminRequiredMixin, ListView):
    template_name = "admin_dashboard/assignments.html"
    context_object_name = "assignments"
    paginate_by = 20

    def get_queryset(self):
        from apps.consultations.models import ExpertAssignment

        return ExpertAssignment.objects.select_related("farmer", "agriculturalist", "consultation").order_by("-assigned_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.consultations.models import Consultation

        context["assignment_form"] = ExpertAssignmentForm()
        context["unassigned_consultations"] = Consultation.objects.filter(
            agriculturalist__isnull=True,
            status=Consultation.Status.PENDING,
        ).select_related("farmer", "farm")[:10]
        return context


class AssignmentActionView(PlatformAdminRequiredMixin, View):
    @transaction.atomic
    def post(self, request):
        from apps.consultations.models import Consultation, ExpertAssignment, FarmDataConsent
        from apps.consultations.services import assign_consultation

        form = ExpertAssignmentForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Select an active consultation and approved Agriculturalist.")
            return redirect("administration:assignments")
        consultation = form.cleaned_data["consultation"]
        expert = form.cleaned_data["agriculturalist"]
        previous_expert_id = consultation.agriculturalist_id
        existing_assignment = ExpertAssignment.objects.filter(consultation=consultation, is_active=True).first()
        if previous_expert_id == expert.pk and existing_assignment:
            messages.info(request, f'{expert.display_name} is already assigned to "{consultation.title}".')
            return redirect("administration:assignments")
        if previous_expert_id and previous_expert_id != expert.pk:
            FarmDataConsent.objects.filter(
                consultation=consultation,
                revoked_at__isnull=True,
            ).update(revoked_at=timezone.now())
        consultation.agriculturalist = expert
        consultation.status = Consultation.Status.ASSIGNED
        consultation.save(update_fields=["agriculturalist", "status", "updated_at"])
        assign_consultation(consultation, assigned_by=request.user, share_farm=False)
        record_audit(
            request,
            "consultation.expert_assigned",
            consultation,
            metadata={
                "agriculturalist_id": expert.pk,
                "previous_agriculturalist_id": previous_expert_id,
            },
        )
        messages.success(request, f'{expert.display_name} is now assigned to "{consultation.title}".')
        return redirect("administration:assignments")


class ReportsView(PlatformAdminRequiredMixin, TemplateView):
    template_name = "admin_dashboard/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.consultations.models import Consultation
        from apps.farms.models import Farm

        context["role_distribution"] = User.objects.values("role").annotate(total=Count("id"))
        context["farm_regions"] = Farm.objects.values("district").annotate(total=Count("id")).order_by("-total")[:10]
        context["consultation_statuses"] = Consultation.objects.values("status").annotate(total=Count("id"))
        return context


class ReportExportView(PlatformAdminRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="farm-time-machine-users-{date.today().isoformat()}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Name", "Email", "Role", "District", "Status", "Joined"])
        for user in User.objects.order_by("date_joined"):
            writer.writerow([safe_csv(user.full_name), safe_csv(user.email), user.get_role_display(), safe_csv(user.district), "Active" if user.is_active else "Suspended", user.date_joined.isoformat()])
        record_audit(request, "report.users_exported")
        return response


class WeatherManagementView(PlatformAdminRequiredMixin, TemplateView):
    template_name = "admin_dashboard/weather.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.weather.models import WeatherAlert, WeatherObservation

        context["alerts"] = WeatherAlert.objects.select_related("region", "source")[:20]
        context["observations"] = WeatherObservation.objects.select_related("region", "source")[:20]
        context["alert_form"] = kwargs.get("alert_form") or WeatherAlertForm()
        return context


class WeatherAlertCreateView(PlatformAdminRequiredMixin, View):
    def post(self, request):
        form = WeatherAlertForm(request.POST)
        if not form.is_valid():
            page = WeatherManagementView()
            page.setup(request)
            return page.render_to_response(page.get_context_data(alert_form=form), status=400)
        alert = form.save()
        record_audit(
            request,
            "weather_alert.created",
            alert,
            metadata={"region_id": alert.region_id, "severity": alert.severity},
        )
        messages.success(request, f'Weather alert "{alert.title}" was created.')
        return redirect("administration:weather")


class WeatherAlertToggleView(PlatformAdminRequiredMixin, View):
    def post(self, request, pk):
        from apps.weather.models import WeatherAlert

        alert = get_object_or_404(WeatherAlert, pk=pk)
        form = WeatherAlertToggleForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Select a valid weather alert action.")
            return redirect("administration:weather")
        activate = form.cleaned_data["action"] == "activate"
        if alert.is_active == activate:
            messages.info(request, f'Weather alert "{alert.title}" is already {"active" if activate else "inactive"}.')
            return redirect("administration:weather")
        alert.is_active = activate
        alert.save(update_fields=["is_active"])
        action = "activated" if activate else "deactivated"
        record_audit(request, f"weather_alert.{action}", alert)
        messages.success(request, f'Weather alert "{alert.title}" was {action}.')
        return redirect("administration:weather")


class ContentReviewView(PlatformAdminRequiredMixin, ListView):
    template_name = "admin_dashboard/content.html"
    context_object_name = "articles"

    def get_queryset(self):
        from apps.learning.models import LearningArticle

        return LearningArticle.objects.select_related("author", "category").order_by("-updated_at")


class ContentReviewActionView(PlatformAdminRequiredMixin, View):
    def post(self, request, pk):
        from apps.learning.models import LearningArticle

        article = get_object_or_404(LearningArticle, pk=pk)
        form = LearningReviewForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Select a valid review action.")
            return redirect("administration:content")
        if form.cleaned_data["action"] == "approve":
            article.status = LearningArticle.Status.PUBLISHED
            article.published_at = timezone.now()
        else:
            article.status = LearningArticle.Status.REJECTED
            article.published_at = None
        article.reviewer = request.user
        if hasattr(article, "review_notes"):
            article.review_notes = form.cleaned_data["review_notes"]
        article.save()
        record_audit(request, f"content.{form.cleaned_data['action']}", article)
        messages.success(request, "The learning content review was saved.")
        return redirect("administration:content")


class SystemSettingsView(PlatformAdminRequiredMixin, TemplateView):
    template_name = "admin_dashboard/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["integration_status"] = {
            "Weather service": settings.WEATHER_LIVE_ENABLED,
            "AI provider": bool(settings.AI_API_KEY and settings.AI_API_BASE_URL),
            "Demo mode": settings.DEMO_MODE,
            "Secure cookies": settings.SESSION_COOKIE_SECURE,
        }
        from apps.core.models import PlatformSetting

        context["public_setting_forms"] = [
            (item, PublicPlatformSettingForm(instance=item))
            for item in PlatformSetting.objects.filter(is_public=True)
        ]
        return context


class PublicPlatformSettingUpdateView(PlatformAdminRequiredMixin, View):
    def post(self, request, pk):
        from apps.core.models import PlatformSetting

        platform_setting = get_object_or_404(PlatformSetting, pk=pk, is_public=True)
        form = PublicPlatformSettingForm(request.POST, instance=platform_setting)
        if not form.is_valid():
            messages.error(request, f"Could not update {platform_setting.key}: check the JSON value.")
            return redirect("administration:settings")
        form.save()
        record_audit(
            request,
            "platform_setting.updated",
            platform_setting,
            metadata={"key": platform_setting.key},
        )
        messages.success(request, f'Public setting "{platform_setting.key}" was updated.')
        return redirect("administration:settings")


class AuditLogView(PlatformAdminRequiredMixin, ListView):
    model = AuditLog
    template_name = "admin_dashboard/logs.html"
    context_object_name = "logs"
    paginate_by = 30

    def get_queryset(self):
        queryset = super().get_queryset().select_related("actor")
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(action__icontains=query) | Q(target_identifier__icontains=query) | Q(actor__email__icontains=query))
        return queryset


class SupportManagementView(PlatformAdminRequiredMixin, TemplateView):
    template_name = "admin_dashboard/support.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            from apps.core.models import SupportTicket

            context["tickets"] = SupportTicket.objects.select_related("user")[:30]
        except (ImportError, AttributeError):
            context["tickets"] = []
        return context


class SupportTicketUpdateView(PlatformAdminRequiredMixin, DetailView):
    template_name = "admin_dashboard/support_detail.html"
    context_object_name = "ticket"

    def get_queryset(self):
        from apps.core.models import SupportTicket

        return SupportTicket.objects.select_related("user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or SupportTicketUpdateForm(instance=self.object)
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        from apps.notifications.models import Notification
        from apps.notifications.services import create_notification

        self.object = self.get_object()
        before = {"status": self.object.status, "priority": self.object.priority}
        form = SupportTicketUpdateForm(request.POST, instance=self.object)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form), status=400)
        if not form.has_changed():
            messages.info(request, "No support ticket changes were submitted.")
            return redirect("administration:support_ticket", pk=self.object.pk)
        ticket = form.save()
        record_audit(
            request,
            "support_ticket.updated",
            ticket,
            metadata={
                "status_before": before["status"],
                "status_after": ticket.status,
                "priority_before": before["priority"],
                "priority_after": ticket.priority,
                "response_updated": "staff_response" in form.changed_data,
            },
        )
        if ticket.user_id:
            response_note = " A staff response is available." if "staff_response" in form.changed_data else ""
            create_notification(
                ticket.user,
                kind=Notification.Kind.SUPPORT_UPDATED,
                title="Support ticket updated",
                body=f"Ticket #{ticket.pk} is now {ticket.get_status_display()}.{response_note}",
                target_url=reverse("core:help"),
            )
        messages.success(request, f"Support ticket #{ticket.pk} was updated.")
        return redirect("administration:support_ticket", pk=ticket.pk)
