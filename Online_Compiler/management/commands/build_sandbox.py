import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Build the Docker image used to run submissions in isolation."

    def handle(self, *args, **options):
        context = settings.BASE_DIR / "sandbox"
        cmd = ["docker", "build", "-t", settings.JUDGE_DOCKER_IMAGE, str(context)]
        self.stdout.write("Running: " + " ".join(cmd))
        try:
            result = subprocess.run(cmd)
        except FileNotFoundError:
            raise CommandError("Docker is not installed or not on PATH.")
        if result.returncode != 0:
            raise CommandError("docker build failed (is Docker running?).")
        self.stdout.write(self.style.SUCCESS(f"Built image '{settings.JUDGE_DOCKER_IMAGE}'."))
