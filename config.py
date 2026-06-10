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

# White Raven school-picture pipeline (calendar-linked tasks only)
SCHOOL_PICTURE_STAGE_PICTURES = "Pictures Taken and Edit"
SCHOOL_PICTURE_STAGE_ONLINE = "Online, Data"
SCHOOL_PICTURE_STAGE_PRINT = "Print"
SCHOOL_PICTURE_STAGE_QC = "QC"
SCHOOL_PICTURE_STAGE_DONE = "Done"

school_picture_pipeline = {
    "White Raven": {
        "finalize_deadline_weeks": 3,
        "stages": [
            {"name": SCHOOL_PICTURE_STAGE_PICTURES, "color": "#2563EB"},
            {"name": SCHOOL_PICTURE_STAGE_ONLINE, "color": "#7C3AED"},
            {"name": SCHOOL_PICTURE_STAGE_PRINT, "color": "#CA8A04"},
            {"name": SCHOOL_PICTURE_STAGE_QC, "color": "#16A34A"},
            {"name": SCHOOL_PICTURE_STAGE_DONE, "color": "#0891B2"},
        ],
    },
}

# Company-specific workflow statuses (name must match companies.name in hive_group_companies)
company_task_statuses = {
    "White Raven": school_picture_pipeline["White Raven"]["stages"],
}

company_task_status_renames = {
    "White Raven": {
        "Shoot, Edit - Katie": SCHOOL_PICTURE_STAGE_PICTURES,
        "Shoot, Edit": SCHOOL_PICTURE_STAGE_PICTURES,
        "Online, Data - Ashli": SCHOOL_PICTURE_STAGE_ONLINE,
        "Printing - Martha": SCHOOL_PICTURE_STAGE_PRINT,
        "Printing": SCHOOL_PICTURE_STAGE_PRINT,
        "QC - Ashli": SCHOOL_PICTURE_STAGE_QC,
    },
}

company_project_board_views = {
    "White Raven": {
        "backlog": [SCHOOL_PICTURE_STAGE_PICTURES],
        "working": [SCHOOL_PICTURE_STAGE_ONLINE, SCHOOL_PICTURE_STAGE_PRINT, SCHOOL_PICTURE_STAGE_QC],
        "done": [SCHOOL_PICTURE_STAGE_DONE],
        "sprint_promote_to": SCHOOL_PICTURE_STAGE_ONLINE,
        "mark_done_requires_status": SCHOOL_PICTURE_STAGE_QC,
    },
}

# White Raven: calendar shoots auto-create a school project + assigned task
company_calendar_task_sync = {
    "White Raven": {
        "shoot_event_types": ["Fall Picture Day", "Retake Fall Picture Day"],
        "shoot_keyword": "shoot",
        "assignee": {"first_name": "Katie", "last_name": "Gleave"},
        "stage_assignees": {
            SCHOOL_PICTURE_STAGE_PICTURES: {"first_name": "Katie", "last_name": "Gleave"},
            SCHOOL_PICTURE_STAGE_ONLINE: {"first_name": "Ashli", "last_name": "Broadhead"},
            SCHOOL_PICTURE_STAGE_PRINT: {"first_name": "Martha", "last_name": "Whitman"},
            SCHOOL_PICTURE_STAGE_QC: {"first_name": "Ashli", "last_name": "Broadhead"},
        },
        "task_status": SCHOOL_PICTURE_STAGE_PICTURES,
        "finalize_deadline_weeks": 3,
        "my_tasks_current_week_only": True,
        "my_tasks_require_sprint": True,
        "sprint_duration_days": 7,
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

# Proof Pix order CSV import (EventName -> shoot task under school project)
proofpix_order_sync = {
    "White Raven": {
        "strip_trailing_year": True,
        "create_tasks_on_import": True,
        "new_task_status": SCHOOL_PICTURE_STAGE_PRINT,
        # Exact Proof Pix EventName -> Hive Command task.name (when auto-match fails).
        # Examples that usually auto-match without aliases:
        #   "Gunnison Valley High School Cap&Gown 2026" -> task "Cap&Gown 2026"
        #   "Gunnison Valley High Fall Sports" -> task "Fall Sports"
        "event_aliases": {
            "Gunnison Valley High": "Fall Picture Day",
        },
    },
}

# Daily inbox import: drop Proof Pix CSV exports here (see PROOFPIX_INBOX_PATH in .env)
proofpix_inbox = {
    "company_name": "White Raven",
    "path": "~/Desktop/ProofPix-Inbox",
    "schedule_hour": 7,
}
