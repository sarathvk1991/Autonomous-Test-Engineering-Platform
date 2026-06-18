# requirement_intelligence/reports

Report **templates** (e.g. Jinja2 `.html`/`.md`) and rendering assets for the
Requirement Intelligence Layer. The `ReportGenerator` service renders the
consolidated/classified/analyzed requirements and the CP1 verdict into these
templates.

- Templates are versioned here; rendered output is written to `reports/output/`
  (git-ignored) or returned inline.
- Keep presentation here; keep data shaping in the service.
