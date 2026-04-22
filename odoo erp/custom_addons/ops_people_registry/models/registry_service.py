import base64
import csv
import io
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from odoo import fields, models


def _normalize_lookup_key(value):
    value = (value or "").strip().lower()
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^0-9a-zа-яөүё]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


STANDARD_DEPARTMENTS = [
    {
        "code": "management",
        "name": "Удирдлага",
        "parent_code": False,
        "aliases": ("удирдлага", "удирдлагын алба", "administration"),
    },
    {
        "code": "internal_control",
        "name": "Дотоод хяналт",
        "parent_code": "management",
        "aliases": ("дотоод хяналт", "дотоод хяналтын алба"),
    },
    {
        "code": "finance",
        "name": "Санхүүгийн алба",
        "parent_code": "management",
        "aliases": ("санхүүгийн алба", "санхүү алба"),
    },
    {
        "code": "administration",
        "name": "Захиргааны алба",
        "parent_code": "management",
        "aliases": ("захиргааны алба",),
    },
    {
        "code": "waste_transport",
        "name": "Хог тээвэрлэлтийн хэлтэс",
        "parent_code": False,
        "aliases": (
            "хог тээвэрлэлтийн хэлтэс",
            "авто бааз хог тээвэрлэлтийн хэлтэс",
            "авто бааз, хог тээвэрлэлтийн хэлтэс",
        ),
    },
    {
        "code": "green_service",
        "name": "Ногоон байгууламж, цэвэрлэгээ үйлчилгээний хэлтэс",
        "parent_code": False,
        "aliases": (
            "ногоон байгууламж цэвэрлэгээ үйлчилгээний хэлтэс",
            "ногоон байгууламж, цэвэрлэгээ үйлчилгээний хэлтэс",
        ),
    },
    {
        "code": "beautification",
        "name": "Тохижилтын хэлтэс",
        "parent_code": False,
        "aliases": ("тохижилтын хэлтэс",),
    },
]

STANDARD_JOBS = [
    ("director", "Захирал", ("захирал",)),
    ("manager", "Менежер", ("менежер",)),
    ("internal_control_officer", "Дотоод хяналтын ажилтан", ("дотоод хяналтын ажилтан",)),
    ("chief_accountant", "Ерөнхий ня-бо", ("ерөнхий ня бо", "ерөнхий нягтлан")),
    ("accountant", "Тооцооны ня-бо", ("тооцооны ня бо", "тооцооны нягтлан")),
    ("storekeeper", "Нярав", ("нярав",)),
    ("hr_specialist", "Хүний нөөцийн мэргэжилтэн", ("хүний нөөцийн мэргэжилтэн",)),
    ("legal_specialist", "Хуулийн мэргэжилтэн", ("хуулийн мэргэжилтэн",)),
    (
        "planning_specialist",
        "Тайлан, төлөвлөгөө хариуцсан мэргэжилтэн",
        ("тайлан төлөвлөгөө хариуцсан мэргэжилтэн",),
    ),
    ("archive_clerk", "Архив, бичиг хэргийн ажилтан", ("архив бичиг хэргийн ажилтан",)),
    (
        "safety_officer",
        "Хөдөлмөрийн аюулгүй байдал, эрүүл ахуйн хяналтын ажилтан",
        ("хөдөлмөрийн аюулгүй байдал эрүүл ахуйн хяналтын ажилтан",),
    ),
    ("it_officer", "Мэдээлэл, технологийн ажилтан", ("мэдээлэл технологийн ажилтан",)),
    ("pr_officer", "Олон нийттэй харилцах ажилтан", ("олон нийттэй харилцах ажилтан",)),
    ("department_head", "Хэлтсийн дарга", ("хэлтсийн дарга",)),
    ("chief_mechanic", "Ерөнхий механик", ("ерөнхий механик",)),
    (
        "payment_specialist",
        "Төлбөр, хураамж хариуцсан мэргэжилтэн",
        ("төлбөр хураамж хариуцсан мэргэжилтэн",),
    ),
    ("transport_controller", "Тээвэрлэлтийн хяналтын ажилтан", ("тээвэрлэлтийн хяналтын ажилтан",)),
    ("green_engineer", "Ногоон байгууламжийн инженер", ("ногоон байгууламжийн инженер",)),
    ("senior_master", "Зам талбайн ахлах мастер", ("зам талбайн ахлах мастер", "ахлах мастер")),
    ("master", "Мастер", ("мастер",)),
    ("field_engineer", "Даамал, талбайн инженер", ("даамал талбайн инженер",)),
    ("waste_driver", "Хог тээврийн жолооч", ("хог тээврийн жолооч",)),
    ("waste_loader", "Хог тээврийн ачигч", ("хог тээврийн ачигч",)),
    (
        "road_cleaner",
        "Зам талбайн үйлчлэгч",
        ("зам талбайн үйлчлэгч", "зам талбайн үйлчилгээч", "зам талбайн үйлчилгээч дотоод ажил хариуцна"),
    ),
    ("repairman", "Засварчин", ("засварчин",)),
    ("welder", "Гагнуурчин", ("гагнуурчин",)),
    ("guard", "Харуул", ("харуул",)),
    ("spot_cleaner", "Түүвэр хог цэвэрлэгээний ажилтан", ("түүвэр хог цэвэрлэгээний ажилтан",)),
    ("electrician", "Цахилгаанчин", ("цахилгаанчин",)),
    ("assistant", "Туслах ажилтан", ("туслах ажилтан",)),
    ("driver", "Жолооч", ("жолооч",)),
    ("loader_operator", "Ковшийн оператор", ("ковшийн оператор",)),
    ("cleaner", "Үйлчлэгч", ("үйлчлэгч",)),
]

PROFILE_XMLIDS = {
    "admin": "ops_people_registry.access_profile_admin",
    "director": "ops_people_registry.access_profile_director",
    "general_manager": "ops_people_registry.access_profile_general_manager",
    "department_head": "ops_people_registry.access_profile_department_head",
    "senior_master": "ops_people_registry.access_profile_senior_master",
    "master": "ops_people_registry.access_profile_master",
    "specialist": "ops_people_registry.access_profile_specialist",
    "worker": "ops_people_registry.access_profile_worker",
    "finance": "ops_people_registry.access_profile_finance",
    "hr": "ops_people_registry.access_profile_hr",
    "storekeeper": "ops_people_registry.access_profile_storekeeper",
    "mechanic": "ops_people_registry.access_profile_mechanic",
    "control": "ops_people_registry.access_profile_control",
}

PROFILE_ALIAS_MAP = {
    _normalize_lookup_key("system_admin"): "admin",
    _normalize_lookup_key("администратор"): "admin",
    _normalize_lookup_key("director"): "director",
    _normalize_lookup_key("захирал"): "director",
    _normalize_lookup_key("general_manager"): "general_manager",
    _normalize_lookup_key("ерөнхий менежер"): "general_manager",
    _normalize_lookup_key("project_manager"): "department_head",
    _normalize_lookup_key("хэлтсийн дарга"): "department_head",
    _normalize_lookup_key("senior_master"): "senior_master",
    _normalize_lookup_key("ахлах мастер"): "senior_master",
    _normalize_lookup_key("team_leader"): "master",
    _normalize_lookup_key("мастер"): "master",
    _normalize_lookup_key("мэргэжилтэн"): "specialist",
    _normalize_lookup_key("ажилтан"): "worker",
    _normalize_lookup_key("санхүү"): "finance",
    _normalize_lookup_key("хүний нөөц"): "hr",
    _normalize_lookup_key("нярав"): "storekeeper",
    _normalize_lookup_key("механик"): "mechanic",
    _normalize_lookup_key("хяналт"): "control",
    _normalize_lookup_key("worker"): "worker",
}

GENERIC_PROFILE_CODES = {"worker", "specialist"}

FINANCE_TITLES = {"Ерөнхий ня-бо", "Тооцооны ня-бо"}
SPECIALIST_TITLES = {
    "Хүний нөөцийн мэргэжилтэн",
    "Хуулийн мэргэжилтэн",
    "Тайлан, төлөвлөгөө хариуцсан мэргэжилтэн",
    "Архив, бичиг хэргийн ажилтан",
    "Мэдээлэл, технологийн ажилтан",
    "Олон нийттэй харилцах ажилтан",
    "Төлбөр, хураамж хариуцсан мэргэжилтэн",
    "Ногоон байгууламжийн инженер",
}
CONTROL_TITLES = {
    "Дотоод хяналтын ажилтан",
    "Хөдөлмөрийн аюулгүй байдал, эрүүл ахуйн хяналтын ажилтан",
    "Тээвэрлэлтийн хяналтын ажилтан",
}
WORKER_TITLES = {
    "Хог тээврийн жолооч",
    "Хог тээврийн ачигч",
    "Зам талбайн үйлчлэгч",
    "Засварчин",
    "Гагнуурчин",
    "Харуул",
    "Түүвэр хог цэвэрлэгээний ажилтан",
    "Цахилгаанчин",
    "Туслах ажилтан",
    "Жолооч",
    "Ковшийн оператор",
    "Үйлчлэгч",
}
PRODUCTION_DEPARTMENTS = {
    "Хог тээвэрлэлтийн хэлтэс",
    "Ногоон байгууламж, цэвэрлэгээ үйлчилгээний хэлтэс",
    "Тохижилтын хэлтэс",
}


class OpsPeopleRegistryService(models.AbstractModel):
    _name = "ops.people.registry.service"
    _description = "Ажилтан бүртгэлийн үйлчилгээ"

    def action_initialize_registry(self):
        rows = self._load_seed_rows()
        return self.run_registry_sync(
            rows=rows,
            source_label="Суурь утасны жагсаалт",
            create_missing_users=False,
            create_missing_departments=True,
            create_missing_jobs=True,
            generate_missing_codes=True,
        )

    def run_registry_sync(
        self,
        rows=None,
        source_label="Гар ажиллагаа",
        create_missing_users=False,
        create_missing_departments=True,
        create_missing_jobs=True,
        generate_missing_codes=True,
    ):
        rows = rows or []
        audit_lines = []
        departments, created_departments = self._ensure_standard_departments(
            audit_lines,
            create_missing=create_missing_departments,
        )
        jobs, created_jobs = self._ensure_standard_jobs(
            audit_lines,
            create_missing=create_missing_jobs,
        )
        prepared_rows = self._prepare_rows(rows, audit_lines)
        row_index = {row["login"]: row for row in prepared_rows}
        name_index = defaultdict(list)
        for row in prepared_rows:
            name_index[self._normalize_key(row["name"])].append(row)
        for row in prepared_rows:
            row["manager_login"] = self._resolve_manager_login(
                row,
                row_index,
                name_index,
                audit_lines,
            )

        run = self.env["ops.people.audit.run"].sudo().create(
            {
                "name": fields.Datetime.now().strftime("Ажилтан бүртгэлийн аудит %Y-%m-%d %H:%M:%S"),
                "source_label": source_label,
                "state": "draft",
                "total_rows": len(prepared_rows),
            }
        )

        changed_user_ids = set()
        created_employee_ids = set()
        linked_employee_ids = set()
        users = self.env["res.users"].sudo().with_context(active_test=False).search(
            [("share", "=", False)]
        )
        users_by_login = {user.login: user for user in users}

        for row in prepared_rows:
            user = users_by_login.get(row["login"])
            if not user and create_missing_users:
                user = self.env["res.users"].sudo().create(
                    {
                        "name": row["name"],
                        "login": row["login"],
                        "active": row["active"],
                    }
                )
                users_by_login[user.login] = user
                changed_user_ids.add(user.id)
            if not user:
                audit_lines.append(
                    {
                        "severity": "error",
                        "issue_type": "missing_user",
                        "login": row["login"],
                        "person_name": row["name"],
                        "note": "Тухайн login-тай хэрэглэгч системд олдсонгүй.",
                    }
                )
                continue

            profile = self._get_profile(row["profile_code"])
            employee, employee_created, employee_linked = user._ops_get_or_create_registry_employee()
            if employee_created:
                created_employee_ids.add(employee.id)
            if employee_linked:
                linked_employee_ids.add(employee.id)

            employee_code = row["employee_code"] or employee.ops_employee_code or user.ops_employee_code
            if not employee_code and generate_missing_codes:
                employee_code = self._generate_employee_code(user, employee)

            employee_vals = {
                "name": row["name"],
                "user_id": user.id,
                "active": row["active"],
                "department_id": departments[row["department_code"]].id if row["department_code"] else False,
                "job_id": jobs[row["job_code"]].id if row["job_code"] else False,
                "job_title": row["job_title"] or False,
                "work_phone": row["phone"] or employee.work_phone or False,
                "mobile_phone": row["mobile_phone"] or employee.mobile_phone or False,
                "work_email": row["work_email"] or employee.work_email or False,
                "ops_employee_code": employee_code or False,
                "ops_access_profile_id": profile.id if profile else False,
            }
            if self._needs_write(employee, employee_vals):
                employee.with_context(ops_skip_employee_user_sync=True).write(employee_vals)
            row["employee"] = employee

            user_vals = {
                "name": row["name"],
                "active": row["active"],
                "ops_department_id": departments[row["department_code"]].id if row["department_code"] else False,
                "ops_job_id": jobs[row["job_code"]].id if row["job_code"] else False,
                "ops_access_profile_id": profile.id if profile else False,
                "ops_employee_code": employee_code or False,
            }
            if row["work_email"] and "@" in row["work_email"]:
                user_vals["email"] = row["work_email"]
            if self._needs_write(user, user_vals):
                user.with_context(ops_skip_user_employee_sync=True).write(user_vals)
                changed_user_ids.add(user.id)

        for row in prepared_rows:
            user = users_by_login.get(row["login"])
            employee = row.get("employee")
            if not user or not employee:
                continue
            manager_employee = False
            if row.get("manager_login") and row.get("manager_login") in row_index:
                manager_employee = row_index[row["manager_login"]].get("employee")
            if row.get("manager_name") and not manager_employee:
                manager_employee = self._find_employee_by_name(row["manager_name"])

            manager_employee_id = manager_employee.id if manager_employee else False
            if employee.parent_id.id != manager_employee_id:
                employee.with_context(ops_skip_employee_user_sync=True).write(
                    {"parent_id": manager_employee_id}
                )
            if user.ops_manager_employee_id.id != manager_employee_id:
                user.with_context(ops_skip_user_employee_sync=True).write(
                    {"ops_manager_employee_id": manager_employee_id}
                )
                changed_user_ids.add(user.id)

        self._sync_department_managers(departments, prepared_rows)
        self._append_duplicate_lines(audit_lines)
        self._append_registry_gap_lines(audit_lines)

        if audit_lines:
            self.env["ops.people.audit.line"].sudo().create(
                [dict(line, run_id=run.id) for line in audit_lines]
            )

        summary = {
            "source_label": source_label,
            "total_rows": len(prepared_rows),
            "created_departments": len(created_departments),
            "created_jobs": len(created_jobs),
            "updated_users": len(changed_user_ids),
            "created_employees": len(created_employee_ids),
            "linked_employees": len(linked_employee_ids),
            "unresolved_count": len(
                [line for line in audit_lines if line["severity"] in ("warning", "error")]
            ),
        }
        run.write(
            {
                "state": "done",
                "updated_users": len(changed_user_ids),
                "created_employees": len(created_employee_ids),
                "linked_employees": len(linked_employee_ids),
                "created_departments": len(created_departments),
                "created_jobs": len(created_jobs),
                "unresolved_count": summary["unresolved_count"],
                "summary_json": json.dumps(summary, ensure_ascii=False, indent=2),
            }
        )
        return run

    def parse_import_file(self, file_content):
        raw = base64.b64decode(file_content or b"")
        encodings = ("utf-8-sig", "utf-8", "utf-16", "cp1251")
        text = False
        for encoding in encodings:
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is False:
            raise ValueError("CSV файлыг уншиж чадсангүй.")

        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for row in reader:
            rows.append(
                {
                    "login": (row.get("login") or "").strip(),
                    "name": (row.get("name") or "").strip(),
                    "phone": (row.get("phone") or "").strip(),
                    "department_name": (row.get("department_name") or "").strip(),
                    "job_title": (row.get("job_title") or "").strip(),
                    "system_role": (row.get("system_role") or "").strip(),
                    "manager_name": (row.get("manager_name") or "").strip(),
                    "employee_code": (row.get("employee_code") or "").strip(),
                    "active": self._parse_active_value(row.get("active"), default=True),
                    "mobile_phone": (row.get("mobile_phone") or "").strip(),
                    "work_email": (row.get("work_email") or "").strip(),
                }
            )
        return rows

    def _load_seed_rows(self):
        module_root = Path(__file__).resolve().parents[1]
        source_path = module_root / "data" / "people_directory.json"
        rows = json.loads(source_path.read_text(encoding="utf-8"))
        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        if admin:
            rows.append(
                {
                    "login": admin.login,
                    "name": admin.name,
                    "phone": "",
                    "mobile": "",
                    "title": "Администратор",
                    "ops_user_type": "system_admin",
                    "department_name": "Удирдлага",
                    "job_title": "Захирал",
                    "page": 0,
                    "record_no": 0,
                    "work_email": admin.email or "",
                }
            )
        return rows

    def _prepare_rows(self, rows, audit_lines):
        prepared_rows = []
        for sequence, raw_row in enumerate(rows):
            login = (raw_row.get("login") or "").strip()
            name = (raw_row.get("name") or "").strip()
            if not login or not name:
                continue

            department_name = raw_row.get("department_name") or self._get_seed_department_name(raw_row)
            department_code = self._get_department_code(department_name)
            if not department_code:
                audit_lines.append(
                    {
                        "severity": "warning",
                        "issue_type": "missing_department",
                        "login": login,
                        "person_name": name,
                        "raw_value": department_name or "",
                        "note": "Алба нэгжийн маппинг тодорхойгүй тул review шаардлагатай.",
                    }
                )

            raw_title = raw_row.get("job_title") or raw_row.get("title")
            job_title, job_code = self._get_job_name_and_code(raw_title)
            if raw_title and not job_code:
                audit_lines.append(
                    {
                        "severity": "warning",
                        "issue_type": "missing_job",
                        "login": login,
                        "person_name": name,
                        "raw_value": raw_title,
                        "note": "Албан тушаалын маппинг тодорхойгүй байна.",
                    }
                )

            profile_code = self._get_profile_code(
                explicit_role=raw_row.get("system_role"),
                legacy_role=raw_row.get("ops_user_type"),
                job_title=job_title,
            )
            if not profile_code:
                audit_lines.append(
                    {
                        "severity": "warning",
                        "issue_type": "unresolved_role",
                        "login": login,
                        "person_name": name,
                        "raw_value": (raw_row.get("system_role") or raw_row.get("ops_user_type") or ""),
                        "normalized_value": job_title or "",
                        "note": "Системийн эрхийн профайл автоматаар тодорхойлогдсонгүй.",
                    }
                )
                profile_code = "worker"

            prepared_rows.append(
                {
                    "sequence": sequence,
                    "login": login,
                    "name": name,
                    "phone": (raw_row.get("phone") or raw_row.get("work_phone") or "").strip(),
                    "mobile_phone": (raw_row.get("mobile_phone") or raw_row.get("mobile") or "").strip(),
                    "work_email": (raw_row.get("work_email") or "").strip(),
                    "department_name": department_name,
                    "department_code": department_code,
                    "job_title": job_title,
                    "job_code": job_code,
                    "profile_code": profile_code,
                    "manager_name": (raw_row.get("manager_name") or "").strip(),
                    "employee_code": (raw_row.get("employee_code") or "").strip(),
                    "active": self._parse_active_value(raw_row.get("active"), default=True),
                    "sort_order": self._get_sort_order(raw_row, sequence),
                }
            )
        return sorted(prepared_rows, key=lambda row: (row["sort_order"], row["sequence"]))

    def _ensure_standard_departments(self, audit_lines, create_missing=True):
        Department = self.env["hr.department"].sudo().with_context(active_test=False)
        all_departments = Department.search([])
        by_key = defaultdict(list)
        for department in all_departments:
            by_key[self._normalize_key(department.name)].append(department)

        created_codes = []
        records_by_code = {}
        for spec in STANDARD_DEPARTMENTS:
            candidates = []
            for alias in (spec["name"], *spec["aliases"]):
                candidates.extend(by_key.get(self._normalize_key(alias), []))
            canonical = candidates[0] if candidates else Department.browse()
            if not canonical and create_missing:
                canonical = Department.create({"name": spec["name"]})
                created_codes.append(spec["code"])
            if not canonical:
                continue
            vals = {
                "name": spec["name"],
                "ops_registry_code": spec["code"],
                "ops_is_registry_standard": True,
                "active": True,
            }
            if self._needs_write(canonical, vals):
                canonical.write(vals)
            records_by_code[spec["code"]] = canonical
            duplicate_departments = [
                department for department in candidates if department.id != canonical.id
            ]
            for duplicate in duplicate_departments:
                audit_lines.append(
                    {
                        "severity": "warning",
                        "issue_type": "duplicate_department",
                        "person_name": duplicate.name,
                        "raw_value": duplicate.name,
                        "normalized_value": spec["name"],
                        "note": "Ижил утгатай давхардсан алба нэгж илэрлээ. Гар аргаар review хийнэ үү.",
                    }
                )

        for spec in STANDARD_DEPARTMENTS:
            department = records_by_code.get(spec["code"])
            parent = records_by_code.get(spec["parent_code"]) if spec["parent_code"] else False
            if department and department.parent_id != parent:
                department.write({"parent_id": parent.id if parent else False})
        return records_by_code, created_codes

    def _ensure_standard_jobs(self, audit_lines, create_missing=True):
        Job = self.env["hr.job"].sudo().with_context(active_test=False)
        all_jobs = Job.search([])
        by_key = defaultdict(list)
        for job in all_jobs:
            by_key[self._normalize_key(job.name)].append(job)

        created_codes = []
        records_by_code = {}
        for code, name, aliases in STANDARD_JOBS:
            candidates = []
            for alias in (name, *aliases):
                candidates.extend(by_key.get(self._normalize_key(alias), []))
            canonical = candidates[0] if candidates else Job.browse()
            if not canonical and create_missing:
                canonical = Job.create({"name": name})
                created_codes.append(code)
            if not canonical:
                continue
            vals = {
                "name": name,
                "ops_registry_code": code,
                "ops_is_registry_standard": True,
                "active": True,
            }
            if self._needs_write(canonical, vals):
                canonical.write(vals)
            records_by_code[code] = canonical
            duplicate_jobs = [job for job in candidates if job.id != canonical.id]
            for duplicate in duplicate_jobs:
                audit_lines.append(
                    {
                        "severity": "warning",
                        "issue_type": "duplicate_job",
                        "person_name": duplicate.name,
                        "raw_value": duplicate.name,
                        "normalized_value": name,
                        "note": "Ижил утгатай давхардсан албан тушаал илэрлээ.",
                    }
                )
        return records_by_code, created_codes

    def _sync_department_managers(self, departments, rows):
        department_rows = defaultdict(list)
        for row in rows:
            if row["department_name"]:
                department_rows[row["department_name"]].append(row)

        for department_name, row_group in department_rows.items():
            department_code = self._get_department_code(department_name)
            department = departments.get(department_code)
            if not department:
                continue
            manager_employee = False
            for title in ("Хэлтсийн дарга", "Зам талбайн ахлах мастер", "Ерөнхий ня-бо", "Захирал"):
                match = next(
                    (
                        row.get("employee")
                        for row in row_group
                        if row.get("job_title") == title and row.get("employee")
                    ),
                    False,
                )
                if match:
                    manager_employee = match
                    break
            if department.manager_id != manager_employee:
                department.write({"manager_id": manager_employee.id if manager_employee else False})

    def _append_duplicate_lines(self, audit_lines):
        Employee = self.env["hr.employee"].sudo().with_context(active_test=False)
        Job = self.env["hr.job"].sudo().with_context(active_test=False)
        Department = self.env["hr.department"].sudo().with_context(active_test=False)

        for model, issue_type in (
            (Employee, "duplicate_employee"),
            (Job, "duplicate_job"),
            (Department, "duplicate_department"),
        ):
            counter = Counter(self._normalize_key(record.name) for record in model.search([]))
            for key, count in counter.items():
                if not key or count <= 1:
                    continue
                audit_lines.append(
                    {
                        "severity": "warning",
                        "issue_type": issue_type,
                        "raw_value": key,
                        "note": f"{count} ижил нэршилтэй бичлэг илэрлээ.",
                    }
                )

    def _append_registry_gap_lines(self, audit_lines):
        users = self.env["res.users"].sudo().with_context(active_test=False).search(
            [("share", "=", False), ("login", "!=", "__system__")]
        )
        for user in users:
            if not user.employee_id:
                audit_lines.append(
                    {
                        "severity": "error",
                        "issue_type": "missing_employee_link",
                        "user_id": user.id,
                        "login": user.login,
                        "person_name": user.name,
                        "note": "Хэрэглэгч employee бичлэггүй байна.",
                    }
                )
            if not user.ops_department_id:
                audit_lines.append(
                    {
                        "severity": "warning",
                        "issue_type": "missing_department",
                        "user_id": user.id,
                        "login": user.login,
                        "person_name": user.name,
                        "note": "Алба нэгж оноогдоогүй байна.",
                    }
                )
            if not user.ops_job_id:
                audit_lines.append(
                    {
                        "severity": "warning",
                        "issue_type": "missing_job",
                        "user_id": user.id,
                        "login": user.login,
                        "person_name": user.name,
                        "note": "Албан тушаал оноогдоогүй байна.",
                    }
                )

    def _resolve_manager_login(self, row, row_index, name_index, audit_lines):
        if row["manager_name"]:
            manager_candidates = name_index.get(self._normalize_key(row["manager_name"]), [])
            if len(manager_candidates) == 1:
                return manager_candidates[0]["login"]
            if len(manager_candidates) > 1:
                audit_lines.append(
                    {
                        "severity": "warning",
                        "issue_type": "unresolved_manager",
                        "login": row["login"],
                        "person_name": row["name"],
                        "raw_value": row["manager_name"],
                        "note": "Ижил нэртэй хэд хэдэн удирдлага олдсон тул гараар баталгаажуулна уу.",
                    }
                )
                return False

        if row["profile_code"] in {"admin", "director"}:
            return False
        if row["profile_code"] == "general_manager":
            return self._find_first_login(row_index.values(), profile_codes=("director", "admin"))
        if row["department_name"] == "Дотоод хяналт":
            return self._find_first_login(row_index.values(), profile_codes=("director", "general_manager"))
        if row["department_name"] in {"Удирдлага", "Санхүүгийн алба", "Захиргааны алба"}:
            return self._find_first_login(row_index.values(), profile_codes=("general_manager", "director"))

        same_department = [
            candidate
            for candidate in row_index.values()
            if candidate["department_name"] == row["department_name"]
            and candidate["login"] != row["login"]
        ]
        if row["profile_code"] == "department_head":
            return self._find_first_login(row_index.values(), profile_codes=("general_manager", "director"))
        if row["profile_code"] == "senior_master":
            return self._find_first_login(same_department, job_titles=("Хэлтсийн дарга",)) or self._find_first_login(
                row_index.values(), profile_codes=("general_manager", "director")
            )
        if row["job_title"] == "Даамал, талбайн инженер":
            return self._find_first_login(same_department, job_titles=("Хэлтсийн дарга",)) or self._find_first_login(
                row_index.values(), profile_codes=("general_manager", "director")
            )
        if row["profile_code"] == "master":
            return (
                self._find_first_login(same_department, job_titles=("Зам талбайн ахлах мастер",))
                or self._find_first_login(same_department, job_titles=("Хэлтсийн дарга",))
                or self._find_first_login(row_index.values(), profile_codes=("general_manager", "director"))
            )
        if row["department_name"] in PRODUCTION_DEPARTMENTS and row["job_title"] in WORKER_TITLES:
            return (
                self._find_first_login(same_department, job_titles=("Мастер",))
                or self._find_first_login(same_department, job_titles=("Зам талбайн ахлах мастер",))
                or self._find_first_login(same_department, job_titles=("Даамал, талбайн инженер",))
                or self._find_first_login(same_department, job_titles=("Хэлтсийн дарга",))
                or self._find_first_login(row_index.values(), profile_codes=("general_manager", "director"))
            )
        return self._find_first_login(same_department, job_titles=("Хэлтсийн дарга",)) or self._find_first_login(
            row_index.values(), profile_codes=("general_manager", "director")
        )

    def _find_first_login(self, rows, job_titles=(), profile_codes=()):
        candidates = list(rows)
        candidates.sort(key=lambda row: row.get("sort_order", 0))
        for candidate in candidates:
            if job_titles and candidate.get("job_title") in job_titles:
                return candidate["login"]
            if profile_codes and candidate.get("profile_code") in profile_codes:
                return candidate["login"]
        return False

    def _find_employee_by_name(self, name):
        normalized_name = self._normalize_key(name)
        if not normalized_name:
            return self.env["hr.employee"]
        employees = self.env["hr.employee"].sudo().with_context(active_test=False).search(
            [("name", "=", name)],
            limit=2,
        )
        if len(employees) == 1:
            return employees
        employees = self.env["hr.employee"].sudo().with_context(active_test=False).search([])
        matching = employees.filtered(lambda employee: self._normalize_key(employee.name) == normalized_name)
        return matching[:1]

    def _get_profile(self, profile_code):
        xmlid = PROFILE_XMLIDS.get(profile_code)
        return self.env.ref(xmlid, raise_if_not_found=False) if xmlid else False

    def _get_profile_code(self, explicit_role=False, legacy_role=False, job_title=False):
        explicit_profile = PROFILE_ALIAS_MAP.get(self._normalize_key(explicit_role))
        if explicit_profile:
            return explicit_profile
        job_profile = self._get_job_profile_code(job_title)
        legacy_profile = PROFILE_ALIAS_MAP.get(self._normalize_key(legacy_role))
        if job_profile and legacy_profile in GENERIC_PROFILE_CODES:
            return job_profile
        return legacy_profile or job_profile

    def _get_job_profile_code(self, job_title):
        if job_title == "Захирал":
            return "director"
        if job_title == "Менежер":
            return "general_manager"
        if job_title == "Хэлтсийн дарга":
            return "department_head"
        if job_title == "Зам талбайн ахлах мастер":
            return "senior_master"
        if job_title == "Мастер":
            return "master"
        if job_title in FINANCE_TITLES:
            return "finance"
        if job_title == "Хүний нөөцийн мэргэжилтэн":
            return "hr"
        if job_title == "Нярав":
            return "storekeeper"
        if job_title == "Ерөнхий механик":
            return "mechanic"
        if job_title in CONTROL_TITLES:
            return "control"
        if job_title in SPECIALIST_TITLES:
            return "specialist"
        if job_title in WORKER_TITLES or job_title == "Үйлчлэгч":
            return "worker"
        return False

    def _get_job_name_and_code(self, raw_title):
        normalized_title = self._normalize_key(raw_title)
        if not normalized_title:
            return False, False
        for code, name, aliases in STANDARD_JOBS:
            if normalized_title == self._normalize_key(name):
                return name, code
            if normalized_title in {self._normalize_key(alias) for alias in aliases}:
                return name, code
        return raw_title, False

    def _get_department_code(self, raw_name):
        normalized_name = self._normalize_key(raw_name)
        if not normalized_name:
            return False
        for spec in STANDARD_DEPARTMENTS:
            if normalized_name == self._normalize_key(spec["name"]):
                return spec["code"]
            if normalized_name in {self._normalize_key(alias) for alias in spec["aliases"]}:
                return spec["code"]
        return False

    def _get_seed_department_name(self, raw_row):
        page = int(raw_row.get("page") or 0)
        record_no = int(raw_row.get("record_no") or 0)
        if page == 2 and record_no <= 2:
            return "Удирдлага"
        if page == 2 and record_no == 3:
            return "Дотоод хяналт"
        if page == 2 and 4 <= record_no <= 7:
            return "Санхүүгийн алба"
        if page == 2 and 8 <= record_no <= 16:
            return "Захиргааны алба"
        if (page == 2 and 17 <= record_no <= 22) or page in (3, 4):
            return "Хог тээвэрлэлтийн хэлтэс"
        if (page == 2 and 23 <= record_no <= 28) or page in (5, 6):
            return "Ногоон байгууламж, цэвэрлэгээ үйлчилгээний хэлтэс"
        if (page == 2 and record_no >= 29) or page == 7:
            return "Тохижилтын хэлтэс"
        return raw_row.get("department_name") or ""

    def _get_sort_order(self, raw_row, fallback):
        page = int(raw_row.get("page") or 0)
        record_no = int(raw_row.get("record_no") or 0)
        return (page * 1000) + record_no if page or record_no else fallback

    def _generate_employee_code(self, user, employee):
        prefix = (
            self.env["ir.config_parameter"].sudo().get_param(
                "ops_people_registry.employee_code_prefix"
            )
            or "HT"
        )
        if user.login and user.login.isdigit():
            return f"{prefix}-{user.login}"
        return f"{prefix}-{employee.id or user.id:04d}"

    def _needs_write(self, record, values):
        for field_name, new_value in values.items():
            field = record._fields[field_name]
            current_value = record[field_name]
            if field.type == "many2one":
                current_value = current_value.id or False
            elif field.type == "boolean":
                current_value = bool(current_value)
                new_value = bool(new_value)
            else:
                current_value = current_value or False
                new_value = new_value or False
            if current_value != new_value:
                return True
        return False

    def _parse_active_value(self, value, default=False):
        if value in (None, "", False):
            return default
        if isinstance(value, bool):
            return value
        normalized_value = self._normalize_key(str(value))
        return normalized_value not in {"0", "false", "inactive", "идэвхгүй", "no"}

    def _normalize_key(self, value):
        return _normalize_lookup_key(value)
