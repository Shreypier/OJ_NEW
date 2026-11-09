from django.contrib import admin
from home.models import problem, TestCase


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1


@admin.register(problem)
class ProblemAdmin(admin.ModelAdmin):
    inlines = [TestCaseInline]
