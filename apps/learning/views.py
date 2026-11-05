from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.permissions import AgriculturalistRequiredMixin

from .forms import LearningArticleForm
from .models import LearningArticle, LearningCategory


class LearningArticleListView(ListView):
    template_name = "learning/list.html"
    context_object_name = "articles"
    paginate_by = 12

    def get_queryset(self):
        queryset = LearningArticle.objects.filter(status=LearningArticle.Status.PUBLISHED).select_related("category", "author")
        query = self.request.GET.get("q", "").strip()
        category = self.request.GET.get("category", "").strip()
        language = self.request.GET.get("language", "").strip()
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(summary__icontains=query) | Q(body__icontains=query))
        if category:
            queryset = queryset.filter(category__slug=category)
        if language in LearningArticle.Language.values:
            queryset = queryset.filter(language=language)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = LearningCategory.objects.all()
        if self.request.user.is_authenticated and self.request.user.role == "AGRICULTURALIST":
            context["my_drafts"] = LearningArticle.objects.filter(author=self.request.user).exclude(status=LearningArticle.Status.PUBLISHED)[:5]
        return context


class LearningArticleDetailView(DetailView):
    template_name = "learning/detail.html"
    context_object_name = "article"

    def get_queryset(self):
        queryset = LearningArticle.objects.select_related("category", "author")
        if self.request.user.is_authenticated and self.request.user.role == "ADMIN":
            return queryset
        if self.request.user.is_authenticated and self.request.user.role == "AGRICULTURALIST":
            return queryset.filter(Q(status=LearningArticle.Status.PUBLISHED) | Q(author=self.request.user))
        return queryset.filter(status=LearningArticle.Status.PUBLISHED)


class LearningArticleCreateView(AgriculturalistRequiredMixin, CreateView):
    form_class = LearningArticleForm
    template_name = "learning/form.html"
    success_url = reverse_lazy("learning:list")

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.status = LearningArticle.Status.DRAFT
        messages.success(self.request, "Draft article saved.")
        return super().form_valid(form)


class LearningArticleUpdateView(AgriculturalistRequiredMixin, UpdateView):
    form_class = LearningArticleForm
    template_name = "learning/form.html"
    success_url = reverse_lazy("learning:list")

    def get_queryset(self):
        return LearningArticle.objects.filter(
            author=self.request.user,
            status__in=[LearningArticle.Status.DRAFT, LearningArticle.Status.REJECTED],
        )

    def form_valid(self, form):
        messages.success(self.request, "Draft article updated.")
        return super().form_valid(form)


class SubmitArticleView(AgriculturalistRequiredMixin, View):
    def post(self, request, pk):
        article = get_object_or_404(
            LearningArticle,
            pk=pk,
            author=request.user,
            status__in=[LearningArticle.Status.DRAFT, LearningArticle.Status.REJECTED],
        )
        article.status = LearningArticle.Status.SUBMITTED
        article.review_notes = ""
        article.save(update_fields=["status", "review_notes", "updated_at"])
        messages.success(request, "Article submitted for admin review.")
        return redirect("learning:list")
