FROM python:3.12-slim

# Compilers for C / C++ submissions
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ libc6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app

# Run as an unprivileged user so submitted code cannot modify the app or system.
# App code stays root-owned; only /app (for the SQLite journal) and db.sqlite3 are writable.
RUN useradd --create-home judge     && chown judge:judge /app /app/db.sqlite3
USER judge

EXPOSE 8000
ENV DJANGO_SETTINGS_MODULE=Online_Judge.settings PYTHONUNBUFFERED=1
# Inside this image there is no Docker daemon, so submissions run directly in THIS
# container (timeouts + rlimits only). For per-submission containers, run the app on the
# host with JUDGE_BACKEND=docker (the default) instead of inside this image.
ENV JUDGE_BACKEND=local

# For stronger isolation run with:
#   docker run --read-only --tmpfs /tmp --memory=512m --cpus=1 --pids-limit=128 \
#     -v judge-db:/app -p 8000:8000 <image>
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
