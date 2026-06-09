from datetime import date, timedelta

from config import project_board_views


def is_done_status_name(name):
    if not name:
        return False
    normalized = name.strip().lower()
    return normalized in ("done", "complete", "completed")


def done_status_names():
    return project_board_views.get("done", ["Done"])


def week_bounds(today=None):
    today = today or date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


def bucket_for_task(task, today=None):
    """Return overdue, this_week, upcoming, or unfinished for an open task."""
    today = today or date.today()
    if task.status and is_done_status_name(task.status.name):
        return None

    due_date = task.due_date
    if not due_date:
        return "unfinished"

    if due_date < today:
        return "overdue"

    week_start, week_end = week_bounds(today)
    if week_start <= due_date <= week_end:
        return "this_week"

    return "upcoming"


def serialize_workload_task(task):
    data = {
        "task_id": str(task.task_id),
        "name": task.name,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "task_status_id": str(task.task_status_id),
        "project_id": str(task.project_id) if task.project_id else None,
        "in_sprint": len(task.sprints) > 0,
    }
    if task.status:
        data["status"] = {
            "task_status_id": str(task.status.task_status_id),
            "name": task.status.name,
            "color": task.status.color,
        }
    return data


def empty_workload_buckets():
    return {
        "overdue": [],
        "this_week": [],
        "upcoming": [],
        "unfinished": [],
    }


def build_user_workloads(users, tasks):
    workloads = {
        str(user.user_id): {
            "user": {
                "user_id": str(user.user_id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "color": user.color,
            },
            **empty_workload_buckets(),
        }
        for user in users
    }

    for task in tasks:
        bucketed = bucket_for_task(task)
        if not bucketed:
            continue

        for assignee in task.assignees:
            user_id = str(assignee.user_id)
            if user_id not in workloads:
                continue
            workloads[user_id][bucketed].append(serialize_workload_task(task))

    for entry in workloads.values():
        for bucket in ("overdue", "this_week", "upcoming", "unfinished"):
            entry[bucket].sort(
                key=lambda row: (row.get("due_date") or "9999-99-99", row["name"].lower())
            )

    return list(workloads.values())
