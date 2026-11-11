# CodeLANG: an online judge

[![Tests](https://github.com/Shreypier/OJ_NEW/actions/workflows/tests.yml/badge.svg)](https://github.com/Shreypier/OJ_NEW/actions/workflows/tests.yml)

A web platform where users solve programming problems in **Python, C and C++** and get instant
verdicts from a judge that runs every submission in an isolated Docker container.

> Live demo: **https://codelang.duckdns.org**

## Features

- Problem list with search, difficulty filter, and solved / attempted status
- In-browser **Monaco editor** (the VS Code editor), with Run (custom input) and Submit
- Multi-test-case judging with hidden cases and verdicts: Accepted, Wrong Answer, Time Limit,
  Runtime Error, Compile Error, Output Limit, System Error
- Submission history per user, with the code and per-case results
- Employee portal to create, edit and delete problems and test cases
- Light and dark themes

## Tech stack

Django 4.2, SQLite, Docker, Gunicorn, Nginx, WhiteNoise, Monaco editor, plain HTML/CSS/JS.

## How the judge keeps code execution safe

Each submission runs in its own throwaway container started with:

| Protection | Setting |
|---|---|
| No network | `--network none` |
| Memory cap, no swap | `--memory`, `--memory-swap` |
| CPU and process caps | `--cpus 1`, `--pids-limit 128` |
| Read-only root filesystem | `--read-only` with a small tmpfs |
| No extra privileges | `--cap-drop ALL`, `no-new-privileges` |
| Unprivileged user | code runs as uid 65534 with resource limits |

A runner inside the container compiles and executes the code and returns one JSON result to the
web app. Time limit: 10 s per test case. A concurrency cap makes extra submissions wait for a free
slot instead of overloading the server. If Docker is unavailable the judge reports a System Error and
**never** falls back to running code on the host.

## Run it locally

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py build_sandbox        # builds the Docker image (needs Docker running)
python manage.py createsuperuser
python manage.py runserver
```

Open http://localhost:8000. Without Docker, `JUDGE_BACKEND=local` runs code on your machine for
development only (it is not safe for public use).

## Tests

```bash
python manage.py test
```

The suite covers the judge engine, submissions, employee authentication, and (when Docker and the
sandbox image are available) real sandbox escape attempts: network access, fork bombs, memory hogs,
output floods and attempts to forge the result.

## Roles

Users and employees share Django's user table. An **employee** is a user with `is_staff=True`
(created in `/admin/`) who signs in at `/accounts/employee_login/`. Passwords are hashed.

## Deployment

See [DEPLOY_AWS.md](DEPLOY_AWS.md) for a step-by-step guide to hosting on a small AWS EC2 server.

## Project layout

```
accounts/        login, registration, employee login
home/            problems, test cases, problem workspace, employee panel
Online_Compiler/ judge engine, submissions
sandbox/         Dockerfile and runner for the per-submission container
deploy/          production config: systemd service, Nginx, setup scripts
```
