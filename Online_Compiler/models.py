from django.conf import settings
from django.db import models


class Submission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions")
    problem = models.ForeignKey("home.problem", on_delete=models.CASCADE, related_name="submissions")
    language = models.CharField(max_length=50)
    code = models.TextField(blank=True)
    verdict = models.CharField(max_length=10)
    message = models.TextField(blank=True)
    time_ms = models.PositiveIntegerField(default=0)
    passed = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created", "-id"]

    @property
    def verdict_label(self):
        from Online_Compiler.judge import VERDICT_LABELS
        return VERDICT_LABELS.get(self.verdict, self.verdict)

    def __str__(self):
        return f"{self.user} - {self.problem} - {self.verdict}"
