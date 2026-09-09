APP_TITLE = "langgraph-poc backend"

# "*" is a deliberate, scoped choice, not an oversight: this backend has
# no auth (BRD constraint-03), no cookies/credentials in play, and only
# ever runs on localhost for POC development (architecture decision-11)
# — so there is no real origin to restrict against. Widened from a
# fixed localhost-port allowlist to also let the Approval Gate Console
# testing artifact (served from a claude.site-style origin) call this
# backend directly from the developer's own browser.
CORS_ALLOWED_ORIGINS = ["*"]
CORS_ALLOWED_METHODS = ["*"]
CORS_ALLOWED_HEADERS = ["*"]
