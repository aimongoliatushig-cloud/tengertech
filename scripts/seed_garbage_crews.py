import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ODOO_SERVER = Path(r"C:\Program Files\Odoo 19.0.20260415\server")
ODOO_CONF = ODOO_SERVER / "odoo.conf"
ADDONS_PATH = ",".join(
    [
        str(ODOO_SERVER / "odoo" / "addons"),
        str(ROOT / "odoo erp" / "custom_addons"),
    ]
)
DB_NAME = "odoo19_admin"

DEPARTMENT_NAME = "Авто бааз, хог тээвэрлэлтийн хэлтэс"
VEHICLE_LICENSES = [
    "УБА 2101",
    "УБА 2102",
    "УБА 2103",
    "УБА 2104",
    "УБА 2105",
    "УБА 2106",
    "УБА 2107",
    "УБА 2108",
    "УБА 2109",
    "УБА 2110",
    "УБА 2111",
    "УБА 2112",
]
INSPECTOR_LOGINS = ["91100190", "88210622", "90530609"]


def init_odoo():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(ODOO_SERVER))

    import odoo  # pylint: disable=import-outside-toplevel
    import odoo.service.server  # pylint: disable=import-outside-toplevel
    from odoo import api, SUPERUSER_ID  # pylint: disable=import-outside-toplevel
    from odoo.tools import config  # pylint: disable=import-outside-toplevel

    config.parse_config(["-c", str(ODOO_CONF), "--addons-path", ADDONS_PATH])
    odoo.service.server.load_server_wide_modules()
    registry = odoo.modules.registry.Registry(DB_NAME)
    return api, SUPERUSER_ID, registry


def upsert(recordset, domain, values):
    record = recordset.search(domain, limit=1)
    if record:
        record.write(values)
    else:
        record = recordset.create(values)
    return record


def role_title(role_code):
    mapping = {
        "driver": "Жолооч",
        "collector": "Ачигч",
        "inspector": "Ахлах мастер",
    }
    return mapping.get(role_code, "Ажилтан")


def upsert_employee(env, user, department, role_code):
    employee_vals = {
        "name": user.name,
        "user_id": user.id,
        "department_id": department.id,
        "work_phone": user.login,
        "mobile_phone": user.login,
        "job_title": role_title(role_code),
        "mfo_is_field_active": True,
        "mfo_field_role": role_code,
        "company_id": user.company_id.id if user.company_id else False,
    }
    return upsert(env["hr.employee"], [("user_id", "=", user.id)], employee_vals)


def main():
    api, superuser_id, registry = init_odoo()
    from odoo import Command  # pylint: disable=import-outside-toplevel

    with registry.cursor() as cr:
        env = api.Environment(cr, superuser_id, {})

        department = env["hr.department"].search([("name", "=", DEPARTMENT_NAME)], limit=1)
        if not department:
            raise RuntimeError(f"{DEPARTMENT_NAME} хэлтэс олдсонгүй.")

        vehicles = env["fleet.vehicle"].search([("license_plate", "in", VEHICLE_LICENSES)], order="license_plate")
        if len(vehicles) != len(VEHICLE_LICENSES):
            raise RuntimeError("12 машины суурь өгөгдөл бүрэн алга байна.")

        inspector_users = env["res.users"].search([("login", "in", INSPECTOR_LOGINS)], order="id")
        if len(inspector_users) != len(INSPECTOR_LOGINS):
            raise RuntimeError("Ахлах мастер / мастер хэрэглэгчид бүрэн олдсонгүй.")
        inspectors = [upsert_employee(env, user, department, "inspector") for user in inspector_users]

        worker_users = env["res.users"].search(
            [
                ("ops_user_type", "=", "worker"),
                ("share", "=", False),
                ("id", "!=", 2),
            ],
            order="id",
            limit=36,
        )
        if len(worker_users) < 36:
            raise RuntimeError("12 жолооч, 24 ачигч үүсгэхэд хүрэлцэхүйц ажилтан алга.")

        driver_users = worker_users[:12]
        collector_users = worker_users[12:36]
        drivers = [upsert_employee(env, user, department, "driver") for user in driver_users]
        collectors = [upsert_employee(env, user, department, "collector") for user in collector_users]

        created_team_ids = []
        for index, vehicle in enumerate(vehicles, start=1):
            driver = drivers[index - 1]
            collector_pair = collectors[(index - 1) * 2 : index * 2]
            inspector = inspectors[(index - 1) % len(inspectors)]
            team = upsert(
                env["mfo.crew.team"],
                [("vehicle_id", "=", vehicle.id), ("operation_type", "=", "garbage")],
                {
                    "name": f"Хог тээврийн экипаж {index:02d}",
                    "code": f"GT-CREW-{index:02d}",
                    "operation_type": "garbage",
                    "vehicle_id": vehicle.id,
                    "driver_employee_id": driver.id,
                    "collector_employee_ids": [Command.set([collector.id for collector in collector_pair])],
                    "inspector_employee_id": inspector.id,
                    "note": f"{vehicle.license_plate} машины жолооч, 2 ачигчтай байнгын баг.",
                },
            )
            created_team_ids.append(team.id)

        print("Хог тээврийн экипажийн өгөгдөл амжилттай үүслээ.")
        print(f"Жолооч: {len(drivers)}")
        print(f"Ачигч: {len(collectors)}")
        print(f"Ахлах мастер / мастер: {len(inspectors)}")
        print(
            "Экипаж:",
            env["mfo.crew.team"].search_count([("id", "in", created_team_ids)]),
        )
        cr.commit()


if __name__ == "__main__":
    main()
