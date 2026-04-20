from datetime import datetime, time, timedelta


MFO_SHARED_FIELD_GROUPS = ",".join(
    [
        "municipal_field_ops.group_mfo_manager",
        "municipal_field_ops.group_mfo_dispatcher",
        "municipal_field_ops.group_mfo_inspector",
        "municipal_field_ops.group_mfo_mobile_user",
        "ops_role_security.group_ops_system_admin",
        "ops_role_security.group_ops_general_manager",
        "ops_role_security.group_ops_project_leader",
        "ops_role_security.group_ops_team_leader",
        "ops_role_security.group_ops_worker",
        "base.group_system",
    ]
)


OPERATION_TYPE_SELECTION = [
    ("garbage", "Хог цуглуулалт"),
    ("street_cleaning", "Гудамж цэвэрлэгээ"),
    ("green_maintenance", "Ногоон байгууламж"),
]

SHIFT_TYPE_SELECTION = [
    ("morning", "Өглөө"),
    ("day", "Өдөр"),
    ("evening", "Орой"),
    ("night", "Шөнө"),
]

WEEKDAY_SELECTION = [
    ("0", "Даваа"),
    ("1", "Мягмар"),
    ("2", "Лхагва"),
    ("3", "Пүрэв"),
    ("4", "Баасан"),
    ("5", "Бямба"),
    ("6", "Ням"),
]

TASK_STATE_SELECTION = [
    ("draft", "Төлөвлөгдсөн"),
    ("dispatched", "Хуваарилсан"),
    ("in_progress", "Гүйцэтгэж байна"),
    ("submitted", "Шалгахаар илгээсэн"),
    ("verified", "Баталгаажсан"),
    ("cancelled", "Цуцалсан"),
]

STAGE_CODE_SELECTION = [
    ("planned", "Төлөвлөгдсөн"),
    ("dispatched", "Хуваарилсан"),
    ("in_progress", "Гүйцэтгэж байна"),
    ("review", "Шалгаж байна"),
    ("done", "Дууссан"),
]

STOP_STATE_SELECTION = [
    ("draft", "Хүлээгдэж байна"),
    ("arrived", "Очсон"),
    ("done", "Гүйцэтгэсэн"),
    ("skipped", "Алгассан"),
    ("issue", "Асуудалтай"),
]

PROOF_TYPE_SELECTION = [
    ("before", "Цуглуулахаас өмнө"),
    ("after", "Цуглуулсны дараа"),
    ("start", "Ээлж эхлэх"),
    ("stop", "Зогсоол"),
    ("completion", "Ээлж дуусах"),
    ("verification", "Баталгаажуулалт"),
]

PLANNING_OVERRIDE_SELECTION = [
    ("off_day", "Амралтын өдөр"),
    ("cancel_generation", "Үүсгэхгүй"),
    ("route_swap", "Маршрут солих"),
    ("vehicle_swap", "Техник солих"),
    ("crew_swap", "Экипаж солих"),
]

ISSUE_TYPE_SELECTION = [
    ("route", "Маршрут"),
    ("vehicle", "Техник"),
    ("crew", "Экипаж"),
    ("safety", "Аюулгүй байдал"),
    ("citizen", "Иргэний гомдол"),
    ("other", "Бусад"),
]

ISSUE_STATE_SELECTION = [
    ("new", "Шинэ"),
    ("in_progress", "Шийдвэрлэж байна"),
    ("resolved", "Шийдсэн"),
    ("cancelled", "Хаасан"),
]

ISSUE_SEVERITY_SELECTION = [
    ("low", "Бага"),
    ("medium", "Дунд"),
    ("high", "Өндөр"),
    ("critical", "Яаралтай"),
]

SYNC_TYPE_SELECTION = [
    ("weighbridge", "Пүүгийн синк"),
    ("manual", "Гараар"),
    ("healthcheck", "Холболтын шалгалт"),
]

SYNC_STATE_SELECTION = [
    ("draft", "Ноорог"),
    ("running", "Ажиллаж байна"),
    ("success", "Амжилттай"),
    ("warning", "Анхааруулга"),
    ("failed", "Алдаа"),
]

WEIGHT_TOTAL_SOURCE_SELECTION = [
    ("manual", "Гараар"),
    ("wrs_normalized", "WRS өдөр тутмын нийт"),
]

EMPLOYEE_ROLE_SELECTION = [
    ("driver", "Жолооч"),
    ("collector", "Ачигч"),
    ("inspector", "Хянагч"),
    ("dispatcher", "Диспетчер"),
    ("manager", "Менежер"),
    ("other", "Бусад"),
]


def monday_for(date_value):
    return date_value - timedelta(days=date_value.weekday())


def combine_date_float_hours(date_value, float_hours):
    if not date_value:
        return False
    hours = int(float_hours or 0.0)
    minutes = int(round(((float_hours or 0.0) - hours) * 60))
    if minutes == 60:
        hours += 1
        minutes = 0
    return datetime.combine(date_value, time(hour=hours % 24, minute=minutes))
