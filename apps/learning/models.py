from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class LearningCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)
    description = models.TextField(blank=True, max_length=500)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Learning categories"

    def __str__(self):
        return self.name


class LearningArticle(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted for review"
        PUBLISHED = "PUBLISHED", "Published"
        REJECTED = "REJECTED", "Changes requested"

    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        BENGALI = "bn", "Bangla"

    category = models.ForeignKey(LearningCategory, on_delete=models.PROTECT, related_name="articles")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="learning_articles")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_learning_articles",
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    summary = models.TextField(max_length=500)
    body = models.TextField(max_length=15000)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.ENGLISH, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    review_notes = models.TextField(blank=True, max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-published_at", "-updated_at"]
        indexes = [models.Index(fields=["status", "language", "-published_at"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:175] or "learning-article"
            candidate = base
            suffix = 2
            while LearningArticle.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f"{base}-{suffix}"
                suffix += 1
            self.slug = candidate
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("learning:detail", args=[self.slug])

    def __str__(self):
        return self.title
