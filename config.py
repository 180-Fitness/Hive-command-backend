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
        {"name": "Shoot, Edit", "color": "#2563EB"},
        {"name": "Online, Data", "color": "#7C3AED"},
        {"name": "Printing", "color": "#CA8A04"},
        {"name": "QC", "color": "#16A34A"},
        {"name": "Done", "color": "#0891B2"},
    ],
}

company_task_status_renames = {
    "White Raven": {
        "Shoot, Edit - Katie": "Shoot, Edit",
        "Online, Data - Ashli": "Online, Data",
        "Printing - Martha": "Printing",
        "QC - Ashli": "QC",
    },
}

company_project_board_views = {
    "White Raven": {
        "backlog": ["Shoot, Edit"],
        "working": ["Online, Data", "Printing", "QC"],
        "done": ["Done"],
        "sprint_promote_to": "Online, Data",
        "mark_done_requires_status": "QC",
    },
}

# White Raven: calendar shoots auto-create a school project + assigned task
company_calendar_task_sync = {
    "White Raven": {
        "shoot_event_types": ["Fall Picture Day", "Retake Fall Picture Day"],
        "shoot_keyword": "shoot",
        "assignee": {"first_name": "Katie", "last_name": "Gleave"},
        "task_status": "Shoot, Edit",
        "my_tasks_require_sprint": True,
        "backlog_until_picture_day": True,
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

# TV dashboard kiosk logins (one account per company)
dashboard_accounts = [
    {
        "username": "whiteraven-dashboard",
        "company_name": "White Raven",
        "password_env": "DASHBOARD_WHITERAVEN_PASSWORD",
        "default_password": "Test123!",
    },
]

# Project UI uses three columns: backlog (no sprint), in sprint, done (status name).
project_board_views = {
    "backlog": ["Backlog", "Ready"],
    "working": ["In Progress", "In Review", "Blocked"],
    "done": ["Done"],
}

