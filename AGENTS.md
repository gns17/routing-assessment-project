# Project

This repository contains a take-home assessment for a Backend Django Engineer role.

The goal is to build a Django API that:
- accepts a start and finish location within the USA;
- returns a route and recommended fuel stops;
- optimizes stops primarily for fuel cost;
- assumes a maximum vehicle range of 500 miles and fuel economy of 10 MPG;
- uses the provided fuel-price dataset;
- minimizes calls to the external routing provider;
- returns results quickly.

The full assignment is in `docs/assignment.md`.

# Workflow

- Use `uv` for Python versions, dependencies, and commands.
- Use Python 3.13.
- Use the latest stable Django version installed in the project.
- Before implementing significant functionality, analyze the requirement and propose a plan.
- Do not make major architectural decisions silently. Surface assumptions and trade-offs first.
- Prefer simple, explainable solutions suitable for a 3-day take-home.
- Avoid unnecessary infrastructure or abstractions.
- Keep external service integrations isolated from business logic.
- Keep route and fuel-optimization logic independently testable.
- Do not hardcode secrets or API keys.
- Never commit `.env`.

# Quality

- Add tests for business logic and important failure cases.
- Run tests after meaningful changes.
- Run Ruff before considering a task complete.
- Treat the supplied CSV as external input and validate assumptions about its contents.
- Document ambiguous requirements explicitly in the README rather than hiding assumptions in code.

# Commands

Run tests:

`uv run pytest`

Lint:

`uv run ruff check .`

Format:

`uv run ruff format .`

Run Django:

`uv run python manage.py runserver`

# Current phase

The project is currently in analysis and design.

Do not implement the assignment until the proposed architecture, external API strategy, dataset handling, and fuel-optimization approach have been reviewed and approved.