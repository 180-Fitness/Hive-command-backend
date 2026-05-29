"""Deployment settings for a single enterprise with many subsidiary companies."""

# Parent enterprise (one deployment = one enterprise)
enterprise_name = "Hive Command"
enterprise_email = "admin@hivecommand.local"
enterprise_phone = ""

# Default subsidiary created on first boot (corporate / HQ)
default_company_name = "Corporate HQ"
default_company_city = ""
default_company_state = ""
default_company_postal = ""

# Bootstrap enterprise administrator
admin_first_name = "Enterprise"
admin_last_name = "Admin"
admin_email = "hive-admin@hivecommand.local"
admin_phone = ""

database_name = "hive_command"

max_per_page_default = 20
default_start_page = 1
purge_expired_auth_tokens = True

default_task_statuses = [
    "Backlog",
    "Ready",
    "In Progress",
    "In Review",
    "Blocked",
    "Done",
]

palette = [
    "#2563EB",
    "#7C3AED",
    "#DB2777",
    "#EA580C",
    "#CA8A04",
    "#16A34A",
    "#0891B2",
    "#4F46E5",
]

# Project UI uses three columns: backlog (no sprint), in sprint, done (status name).
project_board_views = {
    "backlog": ["Backlog", "Ready"],
    "working": ["In Progress", "In Review", "Blocked"],
    "done": ["Done"],
}
