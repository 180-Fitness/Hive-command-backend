"""Deployment settings for a single enterprise with many subsidiary companies."""

# Parent enterprise (one deployment = one enterprise)
enterprise_name = "The Hive Group"
enterprise_email = "admin@hivecommand.local"
enterprise_phone = ""

# Default subsidiary created on first boot (corporate / HQ)
default_company_name = "Corporate HQ"
default_company_city = ""
default_company_state = ""
default_company_postal = ""

# Subsidiary companies under The Hive Group
hive_group_companies = [
    {"name": "WhiteRaven Apparel", "code": "WRA", "color": "#1a1a1a"},
    {"name": "White Raven", "code": "WR", "color": "#2d2d2d"},
    {"name": "180 Fieldhouse", "code": "180FH", "color": "#0a0a0a"},
    {"name": "180 Fitness", "code": "180FIT", "color": "#111111"},
    {"name": "180 Fit Kitchen", "code": "180FK", "color": "#141414"},
    {"name": "Reciprocity", "code": "RECIP", "color": "#2563EB"},
    {"name": "Dr. Inks", "code": "DRINKS", "color": "#7C3AED"},
    {"name": "Kids Rule Daycare", "code": "KRD", "color": "#DB2777"},
    {"name": "Heart of Utah Foundation", "code": "HOUF", "color": "#DC2626"},
    {"name": "Anderson Family Properties", "code": "AFP", "color": "#CA8A04"},
    {"name": "Monroe Mountain Marketing", "code": "MMM", "color": "#16A34A"},
]

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

# Company-specific workflow statuses (name must match companies.name in hive_group_companies)
company_task_statuses = {
    "White Raven": [
        {"name": "Shoot, Edit - Katie", "color": "#2563EB"},
        {"name": "Online, Data - Ashli", "color": "#7C3AED"},
        {"name": "Printing - Martha", "color": "#CA8A04"},
        {"name": "QC - Ashli", "color": "#16A34A"},
    ],
}

company_project_board_views = {
    "White Raven": {
        "backlog": ["Shoot, Edit - Katie"],
        "working": ["Online, Data - Ashli", "Printing - Martha"],
        "done": ["QC - Ashli"],
        "sprint_promote_to": "Online, Data - Ashli",
    },
}

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

