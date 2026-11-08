from types import SimpleNamespace
from pathlib import PurePosixPath

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, RedirectView, TemplateView

from apps.accounts.models import User
from apps.accounts.permissions import AgriculturalistRequiredMixin, FarmerRequiredMixin
from apps.accounts.verification import restrict_to_email_verified
from apps.agricultural_data.views import history_context
from apps.notifications.services import create_notification
from apps.simulations.services import run_baseline
from apps.weather.views import weather_context

from .forms import AgriculturalistSimulationForm, ConsultationCreateForm, ConsultationMessageForm, RecommendationForm
from .models import Consultation, ConsultationMessage, ExpertAssignment, ExpertRecommendation, FarmDataConsent
from .services import assign_consultation, close_consultation, grant_farm_data_consent, notify_message


def _report_form_errors(request, form):
    for field_name, errors in form.errors.items():
        label = "Form" if field_name == "__all__" else form.fields[field_name].label
        for error in errors:
            messages.error(request, f"{label}: {error}")


def _can_access_consultation_media(user, consultation):
    return user.role == User.Role.ADMIN or user.pk in {
        consultation.farmer_id,
        consultation.agriculturalist_id,
    }


def _private_file_response(field_file):
    if not field_file or not field_file.name:
        raise Http404
    try:
        stream = field_file.storage.open(field_file.name, "rb")
    except (FileNotFoundError, OSError):
        raise Http404 from None
    filename = PurePosixPath(field_file.name.replace("\\", "/")).name
    response = FileResponse(stream, as_attachment=True, filename=filename)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


class ConsultationQuestionImageView(LoginRequiredMixin, View):
    def get(self, request, pk):
        consultation = get_object_or_404(Consultation, pk=pk)
        if not _can_access_consultation_media(request.user, consultation):
            raise Http404
        return _private_file_response(consultation.image)


class ConsultationMessageAttachmentView(LoginRequiredMixin, View):
    def get(self, request, pk, message_pk):
        message = get_object_or_404(
            ConsultationMessage.objects.select_related("consultation"),
            pk=message_pk,
            consultation_id=pk,
        )
        if not _can_access_consultation_media(request.user, message.consultation):
            raise Http404
        return _private_file_response(message.attachment)


class ExpertDirectoryView(FarmerRequiredMixin, ListView):
    template_name = "consultations/expert_directory.html"
    context_object_name = "experts"
    paginate_by = 12

    def get_queryset(self):
        queryset = User.objects.filter(
            role=User.Role.AGRICULTURALIST,
            is_active=True,
        )
        queryset = restrict_to_email_verified(queryset).select_related("agriculturalist_profile")
        query = self.request.GET.get("q", "").strip()
        specialization = self.request.GET.get("specialization", "").strip()
        if query:
            queryset = queryset.filter(
                Q(full_name__icontains=query)
                | Q(agriculturalist_profile__specialization__icontains=query)
                | Q(agriculturalist_profile__organization__icontains=query)
            )
        if specialization:
            queryset = queryset.filter(agriculturalist_profile__specialization__icontains=specialization)
        return queryset


class FarmerConsultationListView(FarmerRequiredMixin, ListView):
    template_name = "consultations/farmer_list.html"
    context_object_name = "consultations"
    paginate_by = 12

    def get_queryset(self):
        queryset = Consultation.objects.filter(farmer=self.request.user).select_related("agriculturalist", "farm")
        status = self.request.GET.get("status", "").strip()
        query = self.request.GET.get("q", "").strip()
        if status in Consultation.Status.values:
            queryset = queryset.filter(status=status)
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))
        return queryset


class ConsultationCreateView(FarmerRequiredMixin, CreateView):
    template_name = "consultations/create.html"
    form_class = ConsultationCreateForm
    success_url = reverse_lazy("farmer_consultations:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["farmer"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        expert_id = self.request.GET.get("expert")
        if expert_id:
            initial["agriculturalist"] = expert_id
        return initial

    @transaction.atomic
    def form_valid(self, form):
        consultation = form.save(commit=False)
        consultation.farmer = self.request.user
        consultation.status = (
            Consultation.Status.ASSIGNED if consultation.agriculturalist_id else Consultation.Status.PENDING
        )
        consultation.full_clean()
        consultation.save()
        assign_consultation(
            consultation,
            share_farm=form.cleaned_data["share_farm_data"],
            consent_scope=form.cleaned_data["consent_scope"],
        )
        self.object = consultation
        messages.success(self.request, "Your consultation request has been submitted.")
        return redirect("farmer_consultations:detail", pk=consultation.pk)


class FarmerConsultationDetailView(FarmerRequiredMixin, DetailView):
    template_name = "consultations/farmer_detail.html"
    context_object_name = "consultation"

    def get_queryset(self):
        return (
            Consultation.objects.filter(farmer=self.request.user)
            .select_related("agriculturalist", "farm")
            .prefetch_related("messages__sender", "recommendations")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["message_form"] = ConsultationMessageForm()
        return context


class FarmerSendMessageView(FarmerRequiredMixin, View):
    @transaction.atomic
    def post(self, request, pk):
        consultation = get_object_or_404(
            Consultation.objects.select_for_update(),
            pk=pk,
            farmer=request.user,
        )
        if consultation.status in {Consultation.Status.COMPLETED, Consultation.Status.CANCELLED, Consultation.Status.DECLINED}:
            return HttpResponseBadRequest("This consultation is closed.")
        form = ConsultationMessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.consultation = consultation
            message.sender = request.user
            message.full_clean()
            message.save()
            notify_message(message)
            messages.success(request, "Message sent.")
        else:
            _report_form_errors(request, form)
        return redirect("farmer_consultations:detail", pk=consultation.pk)


class FarmerCloseConsultationView(FarmerRequiredMixin, View):
    def post(self, request, pk):
        consultation = get_object_or_404(Consultation, pk=pk, farmer=request.user)
        try:
            close_consultation(
                consultation,
                status=Consultation.Status.CANCELLED,
                closed_by=request.user,
            )
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))
        messages.success(request, "The consultation has been closed.")
        return redirect("farmer_consultations:detail", pk=pk)


class RevokeConsentView(FarmerRequiredMixin, View):
    @transaction.atomic
    def post(self, request, pk):
        consultation = get_object_or_404(
            Consultation.objects.select_for_update(),
            pk=pk,
            farmer=request.user,
        )
        if hasattr(consultation, "data_consent"):
            consultation.data_consent.revoke()
            messages.success(request, "Farm-data access has been revoked.")
        return redirect("farmer_consultations:detail", pk=pk)


class GrantConsentView(FarmerRequiredMixin, View):
    def post(self, request, pk):
        consultation = get_object_or_404(
            Consultation,
            pk=pk,
            farmer=request.user,
            status__in=[Consultation.Status.ASSIGNED, Consultation.Status.ACTIVE],
        )
        scope = request.POST.get("scope", FarmDataConsent.Scope.SUMMARY)
        if scope not in FarmDataConsent.Scope.values:
            return HttpResponseBadRequest("Invalid consent scope.")
        if not consultation.agriculturalist_id or not consultation.farm_id:
            return HttpResponseBadRequest("An assigned expert and selected farm are required.")
        try:
            grant_farm_data_consent(consultation, scope=scope)
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))
        messages.success(request, "Farm-data access has been granted to the currently assigned Agriculturalist.")
        return redirect("farmer_consultations:detail", pk=pk)


class AgriculturalistQuestionListView(AgriculturalistRequiredMixin, ListView):
    template_name = "consultations/expert_inbox.html"
    context_object_name = "consultations"
    paginate_by = 15

    def get_queryset(self):
        queryset = Consultation.objects.filter(agriculturalist=self.request.user).select_related("farmer", "farm")
        status = self.request.GET.get("status", "").strip()
        query = self.request.GET.get("q", "").strip()
        if status in Consultation.Status.values:
            queryset = queryset.filter(status=status)
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(farmer__full_name__icontains=query))
        return queryset


class AgriculturalistQuestionDetailView(AgriculturalistRequiredMixin, DetailView):
    template_name = "consultations/expert_detail.html"
    context_object_name = "consultation"

    def get_queryset(self):
        return (
            Consultation.objects.filter(agriculturalist=self.request.user)
            .select_related("farmer", "farm")
            .prefetch_related("messages__sender", "recommendations")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consultation = self.object
        context["message_form"] = ConsultationMessageForm()
        context["recommendation_form"] = RecommendationForm()
        consent = getattr(consultation, "data_consent", None)
        context["may_view_farm"] = bool(
            consent
            and consent.is_active
            and consultation.status in {Consultation.Status.ASSIGNED, Consultation.Status.ACTIVE}
            and consent.agriculturalist_id == self.request.user.pk
            and consent.farmer_id == consultation.farmer_id
            and consent.farm_id == consultation.farm_id
        )
        return context


class AgriculturalistReplyView(AgriculturalistRequiredMixin, View):
    @transaction.atomic
    def post(self, request, pk):
        consultation = get_object_or_404(
            Consultation.objects.select_for_update(),
            pk=pk,
            agriculturalist=request.user,
        )
        if consultation.status in {Consultation.Status.COMPLETED, Consultation.Status.CANCELLED, Consultation.Status.DECLINED}:
            return HttpResponseBadRequest("This consultation is closed.")
        form = ConsultationMessageForm(request.POST, request.FILES)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.consultation = consultation
            reply.sender = request.user
            reply.full_clean()
            reply.save()
            if consultation.status == Consultation.Status.ASSIGNED:
                consultation.status = Consultation.Status.ACTIVE
                consultation.save(update_fields=["status", "updated_at"])
            notify_message(reply)
            messages.success(request, "Reply sent.")
        else:
            _report_form_errors(request, form)
        return redirect("agriculturalist:question_detail", pk=pk)


class RecommendationCreateView(AgriculturalistRequiredMixin, View):
    @transaction.atomic
    def post(self, request, pk):
        consultation = get_object_or_404(
            Consultation.objects.select_for_update(),
            pk=pk,
            agriculturalist=request.user,
        )
        if consultation.status in {
            Consultation.Status.COMPLETED,
            Consultation.Status.CANCELLED,
            Consultation.Status.DECLINED,
        }:
            return HttpResponseBadRequest("This consultation is closed.")
        form = RecommendationForm(request.POST)
        if form.is_valid():
            recommendation = form.save(commit=False)
            recommendation.consultation = consultation
            recommendation.agriculturalist = request.user
            recommendation.full_clean()
            recommendation.save()
            if recommendation.status == ExpertRecommendation.Status.PUBLISHED:
                create_notification(
                    consultation.farmer,
                    kind="NEW_RECOMMENDATION",
                    title="New expert recommendation",
                    body=recommendation.title,
                    target_url=f"/farmer/consultations/{consultation.pk}/",
                )
            messages.success(request, "Recommendation saved.")
        else:
            _report_form_errors(request, form)
        return redirect("agriculturalist:question_detail", pk=pk)


class CompleteConsultationView(AgriculturalistRequiredMixin, View):
    def post(self, request, pk):
        consultation = get_object_or_404(Consultation, pk=pk, agriculturalist=request.user)
        try:
            close_consultation(
                consultation,
                status=Consultation.Status.COMPLETED,
                closed_by=request.user,
            )
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))
        messages.success(request, "Consultation marked completed.")
        return redirect("agriculturalist:question_detail", pk=pk)


class DeclineConsultationView(AgriculturalistRequiredMixin, View):
    def post(self, request, pk):
        consultation = get_object_or_404(Consultation, pk=pk, agriculturalist=request.user)
        try:
            close_consultation(
                consultation,
                status=Consultation.Status.DECLINED,
                closed_by=request.user,
            )
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))
        messages.success(request, "The consultation request was declined and is now read-only.")
        return redirect("agriculturalist:question_detail", pk=pk)


class AssignedFarmerListView(AgriculturalistRequiredMixin, ListView):
    template_name = "consultations/assigned_farmers.html"
    context_object_name = "assignments"
    paginate_by = 15

    def get_queryset(self):
        return (
            ExpertAssignment.objects.filter(agriculturalist=self.request.user, is_active=True)
            .select_related("farmer", "consultation")
            .annotate(message_count=Count("consultation__messages"))
            .order_by("-assigned_at")
        )


class RecommendationListView(AgriculturalistRequiredMixin, ListView):
    template_name = "consultations/recommendation_list.html"
    context_object_name = "recommendations"
    paginate_by = 15

    def get_queryset(self):
        return ExpertRecommendation.objects.filter(agriculturalist=self.request.user).select_related(
            "consultation", "consultation__farmer"
        )


class AgriculturalistAnalysisView(AgriculturalistRequiredMixin, TemplateView):
    template_name = "consultations/farm_analysis.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["consents"] = FarmDataConsent.objects.filter(
            agriculturalist=self.request.user,
            revoked_at__isnull=True,
            consultation__agriculturalist=self.request.user,
            consultation__status__in=[Consultation.Status.ASSIGNED, Consultation.Status.ACTIVE],
        ).select_related("farmer", "farm", "consultation").prefetch_related(
            "farm__fields__plantings__crop",
            "farm__activities",
            "farm__simulation_scenarios",
            "farm__decisions",
        )
        return context


class AgriculturalistHistoryView(AgriculturalistRequiredMixin, TemplateView):
    template_name = "consultations/historical_data.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        if not params.get("district"):
            params["district"] = self.request.user.district or "Kurigram"
        context.update(history_context(params))
        return context


class AgriculturalistSimulatorView(AgriculturalistRequiredMixin, FormView):
    template_name = "consultations/simulator.html"
    form_class = AgriculturalistSimulationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["agriculturalist"] = self.request.user
        return kwargs

    def form_valid(self, form):
        cleaned = form.cleaned_data
        pseudo_scenario = SimpleNamespace(
            crop=cleaned["crop"],
            temperature_assumption=cleaned["temperature_assumption"],
            rainfall_assumption=cleaned["rainfall_assumption"],
            irrigation_scenario=cleaned["irrigation_scenario"],
            historical_year=cleaned["historical_year"],
            season=cleaned["season"],
        )
        context = self.get_context_data(form=form)
        context["result"] = run_baseline(pseudo_scenario)
        context["selected_consultation"] = cleaned["consultation"]
        return self.render_to_response(context)


class AgriculturalistWeatherView(AgriculturalistRequiredMixin, TemplateView):
    template_name = "farmer/weather.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(weather_context(self.request))
        context["page_title"] = "Weather & Alerts"
        return context


class AgriculturalistModuleView(AgriculturalistRequiredMixin, TemplateView):
    template_name = "consultations/module_page.html"
    page_title = "Agriculturalist workspace"
    page_description = "Use assigned consultation data and verified sources for this workflow."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.page_title
        context["page_description"] = self.page_description
        context["active_cases"] = Consultation.objects.filter(
            agriculturalist=self.request.user,
            status__in=[Consultation.Status.ASSIGNED, Consultation.Status.ACTIVE],
        ).count()
        return context
