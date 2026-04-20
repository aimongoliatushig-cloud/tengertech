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


DEPARTMENT_SPECS = [
    {
        "name": "Авто бааз, хог тээвэрлэлтийн хэлтэс",
        "manager_login": "88880943",
    },
    {
        "name": "Ногоон байгууламж, цэвэрлэгээ үйлчилгээний хэлтэс",
        "manager_login": False,
    },
    {
        "name": "Тохижилтын хэлтэс",
        "manager_login": "99160453",
    },
]


PROJECT_SPECS = [
    {
        "name": "Авто бааз - 12 машины бэлэн байдал",
        "department_name": "Авто бааз, хог тээвэрлэлтийн хэлтэс",
        "manager_login": "88880943",
        "planned_quantity": 12,
        "measurement_unit": "машин",
        "note": "Хог тээвэрлэлтийн 12 машины бэлэн байдлыг төвлөрүүлэн хянах ажлын суурь бүртгэл.",
    },
    {
        "name": "Хог тээвэрлэлт - 8 хороо",
        "department_name": "Авто бааз, хог тээвэрлэлтийн хэлтэс",
        "manager_login": "88880943",
        "planned_quantity": 156,
        "measurement_unit": "цэг",
        "note": "Хан-Уул дүүргийн 1-8-р хорооны 156 хогийн цэг, 12 маршрутын суурь бүртгэл.",
    },
]


DISTRICT_NAME = "Хан-Уул дүүрэг"
SUBDISTRICT_COUNTS = {
    1: 20,
    2: 19,
    3: 20,
    4: 19,
    5: 20,
    6: 19,
    7: 20,
    8: 19,
}

STREET_THEME = {
    1: "Чингисийн өргөн чөлөө",
    2: "Зайсангийн гудамж",
    3: "Буянт-Ухаа 1-р гудамж",
    4: "Яармагийн зам",
    5: "Нисэхийн тойрог",
    6: "Сонсголонгийн зам",
    7: "Арцатын ам",
    8: "Шувуун фабрикийн зам",
}

POINT_REFERENCES = [
    "орон сууцны хашааны ард",
    "сургуулийн баруун талд",
    "цэцэрлэгийн зүүн талын талбайд",
    "үйлчилгээний төвийн урд",
    "автобусны буудлын хажууд",
]

ROUTE_LAYOUT = [
    {"khoroo": 1, "suffix": "А", "count": 10, "shift_type": "morning", "vehicle_idx": 1},
    {"khoroo": 1, "suffix": "Б", "count": 10, "shift_type": "day", "vehicle_idx": 2},
    {"khoroo": 2, "suffix": "", "count": 19, "shift_type": "morning", "vehicle_idx": 3},
    {"khoroo": 3, "suffix": "А", "count": 10, "shift_type": "morning", "vehicle_idx": 4},
    {"khoroo": 3, "suffix": "Б", "count": 10, "shift_type": "evening", "vehicle_idx": 5},
    {"khoroo": 4, "suffix": "", "count": 19, "shift_type": "morning", "vehicle_idx": 6},
    {"khoroo": 5, "suffix": "А", "count": 10, "shift_type": "morning", "vehicle_idx": 7},
    {"khoroo": 5, "suffix": "Б", "count": 10, "shift_type": "night", "vehicle_idx": 8},
    {"khoroo": 6, "suffix": "", "count": 19, "shift_type": "day", "vehicle_idx": 9},
    {"khoroo": 7, "suffix": "А", "count": 10, "shift_type": "morning", "vehicle_idx": 10},
    {"khoroo": 7, "suffix": "Б", "count": 10, "shift_type": "night", "vehicle_idx": 11},
    {"khoroo": 8, "suffix": "", "count": 19, "shift_type": "morning", "vehicle_idx": 12},
]

VEHICLE_PLATES = [
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

VEHICLE_CAPACITY = [10, 10, 12, 8, 8, 10, 12, 10, 8, 10, 12, 8]


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
    return odoo, api, SUPERUSER_ID, registry


def upsert(recordset, domain, values):
    record = recordset.search(domain, limit=1)
    if record:
        record.write(values)
    else:
        record = recordset.create(values)
    return record


def build_point_name(khoroo_num, index):
    return f"{khoroo_num}-р хороо - {index:02d}-р хогийн цэг"


def build_point_code(khoroo_num, index):
    return f"GT-K{khoroo_num:02d}-{index:03d}"


def build_address(khoroo_num, index):
    street = STREET_THEME[khoroo_num]
    building_no = 10 + index
    reference = POINT_REFERENCES[(index - 1) % len(POINT_REFERENCES)]
    return f"{street} {building_no}, {reference}"


def build_coordinates(khoroo_num, index):
    base_lat = 47.8650 - ((khoroo_num - 1) * 0.0042)
    base_lon = 106.8290 + ((khoroo_num - 1) * 0.0048)
    lat = round(base_lat + ((index - 1) % 5) * 0.00055 + ((index - 1) // 5) * 0.00018, 6)
    lon = round(base_lon + ((index - 1) % 5) * 0.00062 + ((index - 1) // 5) * 0.00016, 6)
    return lat, lon


def route_display_name(khoroo_num, suffix):
    return f"{khoroo_num}-р хороо {suffix} маршрут".replace("  маршрут", " маршрут")


def route_code(khoroo_num, suffix):
    suffix_code = suffix or "A"
    return f"GT-{khoroo_num:02d}{suffix_code}"


def shift_start_hour(shift_type):
    return {
        "morning": 6.0,
        "day": 13.0,
        "evening": 18.0,
        "night": 22.0,
    }[shift_type]


def main():
    odoo, api, SUPERUSER_ID, registry = init_odoo()
    from odoo import Command  # pylint: disable=import-outside-toplevel

    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # Хуучин base-н хоосон хэлтсийг нуух
        admin_department = env["hr.department"].search([("name", "=", "Administration")], limit=1)
        if admin_department:
            has_members = env["hr.employee"].search_count([("department_id", "=", admin_department.id)]) > 0
            has_projects = env["project.project"].search_count([("ops_department_id", "=", admin_department.id)]) > 0
            if not has_members and not has_projects:
                admin_department.active = False

        manager_users = {
            user.login: user
            for user in env["res.users"].search([("login", "in", [spec["manager_login"] for spec in DEPARTMENT_SPECS if spec["manager_login"]])])
        }

        departments = {}
        for spec in DEPARTMENT_SPECS:
            values = {"name": spec["name"], "active": True}
            manager = manager_users.get(spec["manager_login"]) if spec["manager_login"] else False
            if manager:
                values["ops_project_manager_user_id"] = manager.id
            department = upsert(env["hr.department"], [("name", "=", spec["name"])], values)
            departments[spec["name"]] = department

        district = upsert(env["mfo.district"], [("name", "=", DISTRICT_NAME)], {"name": DISTRICT_NAME})

        subdistricts = {}
        for khoroo_num in SUBDISTRICT_COUNTS:
            name = f"{khoroo_num}-р хороо"
            subdistrict = upsert(
                env["mfo.subdistrict"],
                [("name", "=", name), ("district_id", "=", district.id)],
                {"name": name, "district_id": district.id},
            )
            subdistricts[khoroo_num] = subdistrict

        projects = {}
        for spec in PROJECT_SPECS:
            manager = manager_users.get(spec["manager_login"]) if spec["manager_login"] else False
            values = {
                "name": spec["name"],
                "privacy_visibility": "followers",
                "mfo_is_operation_project": True,
                "mfo_operation_type": "garbage",
                "ops_department_id": departments[spec["department_name"]].id,
                "ops_track_quantity": True,
                "ops_planned_quantity": spec["planned_quantity"],
                "ops_measurement_unit": spec["measurement_unit"],
                "mfo_default_shift_type": "morning",
                "mfo_district_ids": [Command.set([district.id])],
                "description": spec["note"],
                "active": True,
            }
            if manager:
                values["user_id"] = manager.id
            project = upsert(env["project.project"], [("name", "=", spec["name"])], values)
            projects[spec["name"]] = project

        brand = upsert(env["fleet.vehicle.model.brand"], [("name", "=", "Hyundai")], {"name": "Hyundai"})
        model = upsert(
            env["fleet.vehicle.model"],
            [("name", "=", "HD120 Хог тээвэрлэгч"), ("brand_id", "=", brand.id)],
            {
                "name": "HD120 Хог тээвэрлэгч",
                "brand_id": brand.id,
                "vehicle_type": "car",
            },
        )

        vehicles = {}
        for index, plate in enumerate(VEHICLE_PLATES, start=1):
            vehicle = upsert(
                env["fleet.vehicle"],
                [("license_plate", "=", plate)],
                {
                    "model_id": model.id,
                    "license_plate": plate,
                    "mfo_active_for_ops": True,
                    "mfo_operation_type": "garbage",
                    "mfo_capacity_ton": VEHICLE_CAPACITY[index - 1],
                    "mfo_wrs_vehicle_code": f"HU-GT-{index:02d}",
                    "name": f"Хог тээврийн машин {index:02d}",
                },
            )
            vehicles[index] = vehicle

        garbage_project = projects["Хог тээвэрлэлт - 8 хороо"]

        points_by_khoroo = {}
        for khoroo_num, count in SUBDISTRICT_COUNTS.items():
            point_records = []
            for point_index in range(1, count + 1):
                lat, lon = build_coordinates(khoroo_num, point_index)
                point = upsert(
                    env["mfo.collection.point"],
                    [("code", "=", build_point_code(khoroo_num, point_index))],
                    {
                        "name": build_point_name(khoroo_num, point_index),
                        "code": build_point_code(khoroo_num, point_index),
                        "subdistrict_id": subdistricts[khoroo_num].id,
                        "operation_type": "garbage",
                        "address": build_address(khoroo_num, point_index),
                        "latitude": lat,
                        "longitude": lon,
                        "note": "Өдөр тутмын ахуйн хог тээвэрлэлтийн суурь цэг.",
                    },
                )
                point_records.append(point)
            points_by_khoroo[khoroo_num] = point_records

        route_point_cursor = {khoroo_num: 0 for khoroo_num in SUBDISTRICT_COUNTS}
        created_routes = []
        for route_index, layout in enumerate(ROUTE_LAYOUT, start=1):
            assigned_vehicle = vehicles[layout["vehicle_idx"]]
            name = route_display_name(layout["khoroo"], layout["suffix"])
            code = route_code(layout["khoroo"], layout["suffix"])
            route = upsert(
                env["mfo.route"],
                [("code", "=", code)],
                {
                    "name": name,
                    "code": code,
                    "project_id": garbage_project.id,
                    "shift_type": layout["shift_type"],
                    "estimated_duration_hours": round(3.0 + (layout["count"] * 0.22), 1),
                    "estimated_distance_km": round(8.0 + (layout["count"] * 1.1), 1),
                    "note": f"Хариуцсан машин: {assigned_vehicle.license_plate} / WRS код: {assigned_vehicle.mfo_wrs_vehicle_code}",
                },
            )

            current_points = points_by_khoroo[layout["khoroo"]]
            start = route_point_cursor[layout["khoroo"]]
            end = start + layout["count"]
            selected_points = current_points[start:end]
            route_point_cursor[layout["khoroo"]] = end

            route.line_ids.unlink()
            interval = max(route.estimated_duration_hours / max(layout["count"], 1), 0.25)
            start_hour = shift_start_hour(layout["shift_type"])
            for sequence, point in enumerate(selected_points, start=1):
                env["mfo.route.line"].create(
                    {
                        "route_id": route.id,
                        "sequence": sequence * 10,
                        "collection_point_id": point.id,
                        "planned_arrival_hour": round(start_hour + ((sequence - 1) * interval), 2),
                        "planned_service_minutes": 10 if layout["count"] <= 10 else 8,
                        "note": f"{point.name} / {point.address}",
                    }
                )

            created_routes.append(route)

        created_route_ids = [route.id for route in created_routes]
        summary = {
            "departments": env["hr.department"].search_count([("name", "in", [spec["name"] for spec in DEPARTMENT_SPECS])]),
            "districts": env["mfo.district"].search_count([("name", "=", DISTRICT_NAME)]),
            "subdistricts": env["mfo.subdistrict"].search_count([("district_id", "=", district.id)]),
            "projects": env["project.project"].search_count([("name", "in", [spec["name"] for spec in PROJECT_SPECS])]),
            "vehicles": env["fleet.vehicle"].search_count([("license_plate", "in", VEHICLE_PLATES)]),
            "routes": env["mfo.route"].search_count([("project_id", "=", garbage_project.id)]),
            "collection_points": env["mfo.collection.point"].search_count([("operation_type", "=", "garbage")]),
            "route_lines": env["mfo.route.line"].search_count([("route_id", "in", created_route_ids)]),
        }

        print("Seed амжилттай дууслаа.")
        for key, value in summary.items():
            print(f"{key}: {value}")

        cr.commit()


if __name__ == "__main__":
    main()
