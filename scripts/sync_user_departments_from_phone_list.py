import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "odoo erp" / "Odoo 19" / "server"
CONFIG_PATH = SERVER_PATH / "odoo.conf"
DB_NAME = "odoo19_admin"
SOURCE_PATH = ROOT / "parsed_employees.json"
REPORT_PATH = ROOT / "user_department_sync_report.json"

sys.path.insert(0, str(SERVER_PATH))

import odoo
from odoo import SUPERUSER_ID, api, fields
from odoo.modules.module import initialize_sys_path
from odoo.orm.registry import Registry
from odoo.service import server as odoo_server


DEPARTMENT_RULES = (
    (
        lambda row: row["page"] == 2 and row["record_no"] <= 3,
        "Удирдлагын алба",
    ),
    (
        lambda row: row["page"] == 2 and 4 <= row["record_no"] <= 7,
        "Санхүү алба",
    ),
    (
        lambda row: row["page"] == 2 and 8 <= row["record_no"] <= 16,
        "Захиргааны алба",
    ),
    (
        lambda row: (row["page"] == 2 and 17 <= row["record_no"] <= 22)
        or row["page"] in (3, 4),
        "Авто бааз, хог тээвэрлэлтийн хэлтэс",
    ),
    (
        lambda row: (row["page"] == 2 and 23 <= row["record_no"] <= 28)
        or row["page"] in (5, 6),
        "Ногоон байгууламж, цэвэрлэгээ үйлчилгээний хэлтэс",
    ),
    (
        lambda row: (row["page"] == 2 and row["record_no"] >= 29)
        or row["page"] == 7,
        "Тохижилтын хэлтэс",
    ),
)


def load_rows():
    rows = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    normalized_rows = []
    for row in rows:
        department_name = None
        for matcher, candidate in DEPARTMENT_RULES:
            if matcher(row):
                department_name = candidate
                break
        if not department_name:
            continue
        normalized_rows.append(
            {
                "login": (row.get("login") or "").strip(),
                "name": (row.get("name") or "").strip(),
                "ops_user_type": (row.get("ops_user_type") or "").strip(),
                "department_name": department_name,
            }
        )
    return normalized_rows


def configure_odoo():
    sys.stdout.reconfigure(encoding="utf-8")
    odoo.tools.config.parse_config(["-c", str(CONFIG_PATH), "-d", DB_NAME])
    initialize_sys_path()
    odoo_server.load_server_wide_modules()


def ensure_department(env, department_name):
    departments = env["hr.department"].sudo().with_context(
        active_test=False,
        lang="mn_MN",
    ).search(
        [("name", "=", department_name)],
        order="id asc",
    )
    if departments:
        return departments[:1], False
    return (
        env["hr.department"].sudo().with_context(lang="mn_MN").create(
            {"name": department_name}
        ),
        True,
    )


def build_department_map(env, rows):
    department_map = {}
    created_departments = []
    for department_name in sorted({row["department_name"] for row in rows}):
        department, created = ensure_department(env, department_name)
        department_map[department_name] = department
        if created:
            created_departments.append({"id": department.id, "name": department.name})
    return department_map, created_departments


def cleanup_unused_duplicate_departments(env, department_names, department_map):
    removed_departments = []
    Department = env["hr.department"].sudo().with_context(
        active_test=False,
        lang="mn_MN",
    )
    User = env["res.users"].sudo().with_context(active_test=False)
    Project = env["project.project"].sudo().with_context(active_test=False)
    Employee = env["hr.employee"].sudo().with_context(active_test=False)

    for department_name in department_names:
        canonical_department = department_map[department_name]
        departments = Department.search([("name", "=", department_name)], order="id asc")
        duplicates = departments.filtered(
            lambda department: department.id != canonical_department.id
        )
        for duplicate in duplicates:
            has_dependencies = any(
                [
                    User.search_count([("ops_department_id", "=", duplicate.id)]),
                    User.search_count([("ops_project_department_ids", "in", duplicate.id)]),
                    Project.search_count([("ops_department_id", "=", duplicate.id)]),
                    Employee.search_count([("department_id", "=", duplicate.id)]),
                ]
            )
            if has_dependencies:
                continue
            removed_departments.append({"id": duplicate.id, "name": duplicate.name})
            duplicate.unlink()

    return removed_departments


def apply_user_updates(env, rows, department_map):
    User = env["res.users"].sudo().with_context(active_test=False)
    updated_users = []
    missing_users = []

    for row in rows:
        user = User.search([("login", "=", row["login"])], limit=1)
        if not user:
            missing_users.append(
                {
                    "login": row["login"],
                    "name": row["name"],
                    "department_name": row["department_name"],
                }
            )
            continue

        department = department_map[row["department_name"]]
        vals = {}

        if not user.ops_user_type and row["ops_user_type"]:
            vals["ops_user_type"] = row["ops_user_type"]

        if user.ops_department_id.id != department.id:
            vals["ops_department_id"] = department.id

        if (
            user.ops_user_type == "project_manager"
            and set(user.ops_project_department_ids.ids) != {department.id}
        ):
            vals["ops_project_department_ids"] = [fields.Command.set([department.id])]

        if vals:
            before = {
                "id": user.id,
                "login": user.login,
                "name": user.name,
                "ops_user_type": user.ops_user_type,
                "ops_department_id": user.ops_department_id.name or "",
                "ops_project_department_ids": user.ops_project_department_ids.mapped(
                    "name"
                ),
            }
            user.write(vals)
            updated_users.append(
                {
                    "before": before,
                    "after": {
                        "id": user.id,
                        "login": user.login,
                        "name": user.name,
                        "ops_user_type": user.ops_user_type,
                        "ops_department_id": user.ops_department_id.name or "",
                        "ops_project_department_ids": user.ops_project_department_ids.mapped(
                            "name"
                        ),
                    },
                }
            )

    return updated_users, missing_users


def apply_admin_defaults(env, department_map):
    admin_user = env.ref("base.user_admin", raise_if_not_found=False)
    if not admin_user:
        return None

    vals = {}
    management_department = department_map.get("Удирдлагын алба")
    if management_department and admin_user.ops_department_id.id != management_department.id:
        vals["ops_department_id"] = management_department.id
    if admin_user.ops_user_type != "system_admin":
        vals["ops_user_type"] = "system_admin"

    if not vals:
        return None

    before = {
        "id": admin_user.id,
        "login": admin_user.login,
        "name": admin_user.name,
        "ops_user_type": admin_user.ops_user_type,
        "ops_department_id": admin_user.ops_department_id.name or "",
    }
    admin_user.sudo().write(vals)
    return {
        "before": before,
        "after": {
            "id": admin_user.id,
            "login": admin_user.login,
            "name": admin_user.name,
            "ops_user_type": admin_user.ops_user_type,
            "ops_department_id": admin_user.ops_department_id.name or "",
        },
    }


def main():
    configure_odoo()
    rows = load_rows()
    registry = Registry(DB_NAME)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        department_map, created_departments = build_department_map(env, rows)
        updated_users, missing_users = apply_user_updates(env, rows, department_map)
        admin_update = apply_admin_defaults(env, department_map)
        removed_departments = cleanup_unused_duplicate_departments(
            env,
            sorted({row["department_name"] for row in rows}),
            department_map,
        )
        cr.commit()

    report = {
        "source_rows": len(rows),
        "updated_users": len(updated_users),
        "missing_users": len(missing_users),
        "created_departments": created_departments,
        "removed_departments": removed_departments,
        "admin_update": admin_update,
        "sample_updates": updated_users[:10],
        "missing_user_samples": missing_users[:10],
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
