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
SCHOOL_PICTURE_STAGE_UPCOMING = "Upcoming"
SCHOOL_PICTURE_STAGE_PICTURES = "Pictures Taken and Edit"
SCHOOL_PICTURE_STAGE_ONLINE = "Online, Data"
SCHOOL_PICTURE_STAGE_PRINT = "Print"
SCHOOL_PICTURE_STAGE_QC = "QC"
SCHOOL_PICTURE_STAGE_DONE = "Done"

school_picture_pipeline = {
    "White Raven": {
        "finalize_deadline_weeks": 3,
        "stages": [
            {"name": SCHOOL_PICTURE_STAGE_UPCOMING, "color": "#64748B"},
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

# Non-calendar editing pipeline (regular tasks — not school picture shoots)
REGULAR_TASK_STAGE_FILTER = "Filter"
REGULAR_TASK_STAGE_CROP = "Crop"
REGULAR_TASK_STAGE_CUTOUT = "Cutout"
REGULAR_TASK_STAGE_BACKGROUNDS = "Backgrounds"
REGULAR_TASK_STAGE_PRINTING = "Printing"

company_regular_task_statuses = {
    "White Raven": [
        {"name": REGULAR_TASK_STAGE_FILTER, "color": "#64748B"},
        {"name": REGULAR_TASK_STAGE_CROP, "color": "#2563EB"},
        {"name": REGULAR_TASK_STAGE_CUTOUT, "color": "#7C3AED"},
        {"name": REGULAR_TASK_STAGE_BACKGROUNDS, "color": "#DB2777"},
        {"name": SCHOOL_PICTURE_STAGE_QC, "color": "#16A34A"},
        {"name": REGULAR_TASK_STAGE_PRINTING, "color": "#CA8A04"},
        {"name": SCHOOL_PICTURE_STAGE_DONE, "color": "#0891B2"},
    ],
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
        "backlog": [SCHOOL_PICTURE_STAGE_UPCOMING],
        "working": [
            SCHOOL_PICTURE_STAGE_PICTURES,
            SCHOOL_PICTURE_STAGE_ONLINE,
            SCHOOL_PICTURE_STAGE_PRINT,
            SCHOOL_PICTURE_STAGE_QC,
        ],
        "done": [SCHOOL_PICTURE_STAGE_DONE],
        "sprint_promote_to": SCHOOL_PICTURE_STAGE_PICTURES,
        "mark_done_requires_status": SCHOOL_PICTURE_STAGE_QC,
    },
}

company_regular_project_board_views = {
    "White Raven": {
        "backlog": [],
        "working": [
            REGULAR_TASK_STAGE_FILTER,
            REGULAR_TASK_STAGE_CROP,
            REGULAR_TASK_STAGE_CUTOUT,
            REGULAR_TASK_STAGE_BACKGROUNDS,
            SCHOOL_PICTURE_STAGE_QC,
            REGULAR_TASK_STAGE_PRINTING,
        ],
        "done": [SCHOOL_PICTURE_STAGE_DONE],
        "mark_done_requires_status": REGULAR_TASK_STAGE_PRINTING,
    },
}

# White Raven: calendar shoots auto-create tasks in one shared project
company_calendar_task_sync = {
    "White Raven": {
        "project_name": "School Pictures",
        "shoot_event_types": [
            "Spring Picture Day",
            "Fall Picture Day",
            "Retake",
            "Retake Fall Picture Day",
            "Graduation",
            "Rooftop",
            "Sports",
            "Senior Pictures",
        ],
        "shoot_keyword": "shoot",
        "assignee": {"first_name": "Katie", "last_name": "Gleave"},
        "stage_assignees": {
            SCHOOL_PICTURE_STAGE_PICTURES: {"first_name": "Katie", "last_name": "Gleave"},
            SCHOOL_PICTURE_STAGE_ONLINE: {"first_name": "Ashli", "last_name": "Broadhead"},
            SCHOOL_PICTURE_STAGE_PRINT: {"first_name": "Martha", "last_name": "Whitman"},
            SCHOOL_PICTURE_STAGE_QC: {"first_name": "Ashli", "last_name": "Broadhead"},
        },
        "task_status": SCHOOL_PICTURE_STAGE_UPCOMING,
        "finalize_deadline_weeks": 3,
        "my_tasks_current_week_only": True,
        "my_tasks_require_sprint": True,
        "sprint_duration_days": 7,
        "backlog_until_picture_day": True,
        # shoot_day_reminders — enable on sh/shoot-day-sms-reminders
        # "shoot_day_reminders": {
        #     "enabled": True,
        #     "sms_to_contact": True,
        #     "sms_to_assignee": True,
        #     "contact_message": (
        #         "White Raven Photography: Confirming our {event_type} at {school} "
        #         "tomorrow ({date}).{details} Please reply if anything has changed. "
        #         "Thank you!"
        #     ),
        # },
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

# TV dashboard kiosk logins (one account per company).
# Set DASHBOARD_WHITERAVEN_PASSWORD in the environment — no insecure default.
dashboard_accounts = [
    {
        "username": "whiteraven-dashboard",
        "company_name": "White Raven",
        "password_env": "DASHBOARD_WHITERAVEN_PASSWORD",
        "default_password": "",
    },
]

# Project UI uses three columns: backlog (no sprint), in sprint, done (status name).
project_board_views = {
    "backlog": ["Backlog", "Ready"],
    "working": ["In Progress", "In Review", "Blocked"],
    "done": ["Done"],
}
