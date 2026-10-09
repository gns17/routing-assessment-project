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

# Approved architecture

- Use Django ORM + the default SQLite database for normalized stations, prices,
  coordinates, enrichment metadata, and status. The supplied CSV is immutable seed
  data, not runtime storage. This is a deliberate conventional-persistence trade-off,
  not an assertion that Django requires a database or ORM queries are faster.
- Use management commands for validated, reproducible CSV import and resumable
  offline enrichment. Keep price selection separate from location enrichment;
  location fingerprints exclude prices, timestamps, row positions, and source checksum.
- Keep external API requests outside database transactions. Use short transactional
  writes, OPIS-ID uniqueness, appropriate checks and coordinate indexes.
- The station repository performs coarse ORM geographic filtering and returns
  plain objects. Avoid N+1 queries and unnecessary model creation. Precise route
  matching and fuel optimization remain pure Python, independent of Django models.
- Do not add PostgreSQL, PostGIS, Redis, Celery, station CRUD endpoints, or admin
  interfaces. Benchmark actual performance before adding complexity.
- Preserve Geoapify, start/finish strings, the three-call baseline target, the
  approved fuel model, and the minimal Leaflet map. See docs/architecture.md.

# Quality

- Add tests for business logic and important failure cases.
- Run tests after meaningful changes.
- Run Ruff before considering a task complete.
- Treat the supplied CSV as external input and validate assumptions about its contents.
- Document ambiguous requirements explicitly in the README rather than hiding assumptions in code.

## Linear

Linear is available through MCP for project tracking.

- Use Linear to track approved implementation work.
- Before creating or substantially modifying issues, show the proposed changes for approval.
- Keep issues scoped, actionable, and tied to the agreed implementation plan.
- Update issue status as implementation progresses.
- Do not create speculative work that has not been approved.

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

GNS-5 is complete with a negative conclusion for unattended nationwide station
enrichment; its unexecuted sample/audit criteria are explicitly superseded.
Prioritize GNS-7 routing integration and GNS-9 pure optimization with mocked tests,
then GNS-6 minimal ORM schema/CSV import and a tested end-to-end vertical slice.
Import unresolved stations with prices/provenance/status, but only sufficiently
reconciled coordinates participate in matching. Synthetic fixtures are for tests,
never real CSV matches in a demonstration. Disclose real-world coverage limits.
GNS-12 is a nonblocking New Mexico-only offline feasibility experiment, initially
60–90 minutes after core work starts; abort early if setup/processing is costly.
No OSM downloads, Michigan expansion, or additional live Geoapify requests without
explicit approval. Keep implementation scoped to active approved Linear issues.
