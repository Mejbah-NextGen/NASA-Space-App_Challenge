from django.contrib import admin

from .models import LearningArticle, LearningCategory


@admin.register(LearningArticle)
class LearningArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "language", "status", "published_at")
    list_filter = ("status", "language", "category")
    search_fields = ("title", "summary", "body", "author__email")
    prepopulated_fields = {"slug": ("title",)}


admin.site.register(LearningCategory)
