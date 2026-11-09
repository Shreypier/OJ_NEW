# Image used to run ONE submission in a throwaway container.
# Build with:  python manage.py build_sandbox
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ libc6-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY runner.py /runner.py
RUN chmod 644 /runner.py

# The runner starts as root (with almost all capabilities dropped by `docker run`)
# only so that it can run submitted code as the unprivileged user "nobody" and keep
# its own process, files and result channel out of that code's reach.
ENTRYPOINT ["python", "/runner.py"]
