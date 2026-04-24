import html
from collections import defaultdict
from datetime import timedelta

from odoo import _, api, fields, models

from .common import MUNICIPAL_ROLE_SELECTION, ROLE_NAME_BY_CODE


class MunicipalRoleDashboard(models.Model):
    _name = "municipal.role.dashboard"
    _description = "Албан тушаалын хяналтын самбар"
    _order = "role_code, user_id"
    _rec_name = "dashboard_title"
    _user_role_unique = models.Constraint(
        "unique(user_id, role_code)",
        "Нэг хэрэглэгч нэг албан үүрэг дээр зөвхөн нэг самбартай байна.",
    )

    name = fields.Char(string="Нэр", required=True, default="Албан тушаалын самбар")
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        "res.users",
        string="Хэрэглэгч",
        required=True,
        default=lambda self: self.env.user,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Компани",
        required=True,
        default=lambda self: self.env.company,
    )
    role_code = fields.Selection(
        selection=MUNICIPAL_ROLE_SELECTION,
        string="Албан тушаал",
        required=True,
        index=True,
    )
    role_label = fields.Char(string="Албан тушаалын нэр", readonly=True)
    dashboard_title = fields.Char(string="Гарчиг", readonly=True)
    dashboard_subtitle = fields.Char(string="Дэд гарчиг", readonly=True)
    highlight_html = fields.Html(string="Товч дүгнэлт", sanitize=False, readonly=True)
    performance_html = fields.Html(string="Гүйцэтгэлийн самбар", sanitize=False, readonly=True)
    alert_html = fields.Html(string="Анхаарах зүйл", sanitize=False, readonly=True)
    last_refreshed_at = fields.Datetime(string="Сүүлд шинэчилсэн", readonly=True)

    kpi_1_label = fields.Char(string="KPI 1", readonly=True)
    kpi_1_value = fields.Char(string="KPI 1 утга", readonly=True)
    kpi_2_label = fields.Char(string="KPI 2", readonly=True)
    kpi_2_value = fields.Char(string="KPI 2 утга", readonly=True)
    kpi_3_label = fields.Char(string="KPI 3", readonly=True)
    kpi_3_value = fields.Char(string="KPI 3 утга", readonly=True)
    kpi_4_label = fields.Char(string="KPI 4", readonly=True)
    kpi_4_value = fields.Char(string="KPI 4 утга", readonly=True)
    kpi_5_label = fields.Char(string="KPI 5", readonly=True)
    kpi_5_value = fields.Char(string="KPI 5 утга", readonly=True)
    kpi_6_label = fields.Char(string="KPI 6", readonly=True)
    kpi_6_value = fields.Char(string="KPI 6 утга", readonly=True)
    kpi_7_label = fields.Char(string="KPI 7", readonly=True)
    kpi_7_value = fields.Char(string="KPI 7 утга", readonly=True)
    kpi_8_label = fields.Char(string="KPI 8", readonly=True)
    kpi_8_value = fields.Char(string="KPI 8 утга", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        dashboards = super().create(vals_list)
        dashboards._refresh_dashboard_payload()
        return dashboards

    def write(self, vals):
        result = super().write(vals)
        if {"role_code", "user_id"} & set(vals):
            self._refresh_dashboard_payload()
        return result

    def action_refresh_dashboard(self):
        self._refresh_dashboard_payload()
        return {
            "type": "ir.actions.act_window",
            "name": self.role_label or _("Ажлын орон зай"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def action_open_role_workspace(self, role_code=None, user=None):
        user = user or self.env.user
        role_code = role_code or user.municipal_role_code or "employee"
        dashboard = self.sudo().search(
            [("user_id", "=", user.id), ("role_code", "=", role_code)],
            limit=1,
        )
        if not dashboard:
            dashboard = self.sudo().create(
                {
                    "user_id": user.id,
                    "company_id": user.company_id.id or self.env.company.id,
                    "role_code": role_code,
                    "name": ROLE_NAME_BY_CODE.get(role_code, "Самбар"),
                }
            )
        else:
            dashboard.sudo()._refresh_dashboard_payload()
        return {
            "type": "ir.actions.act_window",
            "name": ROLE_NAME_BY_CODE.get(role_code, _("Ажлын орон зай")),
            "res_model": self._name,
            "res_id": dashboard.id,
            "view_mode": "form",
            "target": "current",
            "context": dict(self.env.context, default_role_code=role_code),
        }

    def _refresh_dashboard_payload(self):
        for dashboard in self.sudo():
            payload = dashboard._build_payload_for_role(dashboard.role_code, dashboard.user_id)
            payload.update(
                {
                    "role_label": ROLE_NAME_BY_CODE.get(dashboard.role_code, ""),
                    "last_refreshed_at": fields.Datetime.now(),
                }
            )
            super(MunicipalRoleDashboard, dashboard).write(payload)

    def _build_payload_for_role(self, role_code, user):
        handlers = {
            "director": self._payload_director,
            "general_manager": self._payload_general_manager,
            "department_head": self._payload_department_head,
            "project_leader": self._payload_project_leader,
            "senior_master": self._payload_senior_master,
            "master": self._payload_master,
            "employee": self._payload_employee,
            "hr": self._payload_hr,
            "accountant": self._payload_accountant,
            "finance_officer": self._payload_finance_officer,
            "storekeeper": self._payload_storekeeper,
            "office_clerk": self._payload_office_clerk,
            "contract_officer": self._payload_contract_officer,
            "garage_mechanic": self._payload_garage_mechanic,
            "driver": self._payload_driver,
            "loader": self._payload_loader,
            "inspector": self._payload_inspector,
            "system_admin": self._payload_system_admin,
        }
        builder = handlers.get(role_code, self._payload_employee)
        return builder(user)

    def _empty_payload(self, title, subtitle):
        payload = {
            "dashboard_title": title,
            "dashboard_subtitle": subtitle,
            "highlight_html": self._render_panel("Товч төлөв", [("Мэдээлэл", "Одоогоор ачаалж байна", "soft")]),
            "performance_html": self._render_panel("Гүйцэтгэл", [("Төлөв", "Тооцоолол бэлэн", "ok")]),
            "alert_html": self._render_panel("Анхаарах зүйл", [("Тайлбар", "Шинэчилж ачааллаарай", "warn")]),
        }
        for index in range(1, 9):
            payload[f"kpi_{index}_label"] = ""
            payload[f"kpi_{index}_value"] = "0"
        return payload

    def _set_kpis(self, payload, pairs):
        for index in range(1, 9):
            label, value = ("", "0")
            if index - 1 < len(pairs):
                label, value = pairs[index - 1]
            payload[f"kpi_{index}_label"] = label
            payload[f"kpi_{index}_value"] = value
        return payload

    def _get_model(self, model_name):
        return self.env[model_name] if model_name in self.env else False

    def _count(self, model_name, domain=None):
        model = self._get_model(model_name)
        return model.search_count(domain or []) if model else 0

    def _sum(self, model_name, field_name, domain=None):
        model = self._get_model(model_name)
        if not model:
            return 0.0
        data = model.read_group(domain or [], [field_name], [])
        return (data[0].get(field_name) or 0.0) if data else 0.0

    def _today(self):
        return fields.Date.context_today(self)

    def _week_start(self):
        today = self._today()
        return today - timedelta(days=today.weekday())

    def _day_start(self):
        today = self._today()
        return fields.Datetime.to_datetime(f"{today} 00:00:00")

    def _format_number(self, value, digits=0):
        if digits:
            return f"{value:,.{digits}f}"
        return f"{int(round(value or 0)):,.0f}"

    def _render_panel(self, title, items):
        if not items:
            items = [("Мэдээлэл", "Одоогоор бүртгэл алга", "soft")]
        rows = []
        for label, value, tone in items:
            rows.append(
                (
                    '<div class="municipal-role-panel__row municipal-role-panel__row--%s">'
                    '<span class="municipal-role-panel__label">%s</span>'
                    '<strong class="municipal-role-panel__value">%s</strong>'
                    "</div>"
                )
                % (
                    html.escape(tone or "soft"),
                    html.escape(str(label or "")),
                    html.escape(str(value or "")),
                )
            )
        return (
            '<section class="municipal-role-panel">'
            '<header class="municipal-role-panel__title">%s</header>'
            '<div class="municipal-role-panel__body">%s</div>'
            "</section>"
        ) % (html.escape(title), "".join(rows))

    def _department_performance_items(self):
        Project = self._get_model("project.project")
        Task = self._get_model("project.task")
        if not Project or not Task:
            return [("Алба нэгж", "Эх өгөгдөл алга", "soft")]
        projects = Project.search([("ops_department_id", "!=", False), ("active", "=", True)])
        grouped = defaultdict(lambda: {"projects": 0, "tasks": 0})
        for project in projects:
            department = project.ops_department_id.display_name or "Тодорхойгүй"
            grouped[department]["projects"] += 1
        tasks = Task.search([("project_id.ops_department_id", "!=", False)])
        for task in tasks:
            department = task.project_id.ops_department_id.display_name or "Тодорхойгүй"
            grouped[department]["tasks"] += 1
        items = []
        for department, counters in list(grouped.items())[:5]:
            items.append(
                (
                    department,
                    f"{counters['projects']} төсөл / {counters['tasks']} ажил",
                    "ok" if counters["tasks"] else "soft",
                )
            )
        return items or [("Алба нэгж", "Идэвхтэй төсөл алга", "soft")]

    def _vehicle_activity_counts(self):
        Vehicle = self._get_model("fleet.vehicle")
        Task = self._get_model("project.task")
        if not Vehicle or not Task:
            return 0, 0
        active_vehicle_ids = Task.search(
            [("mfo_shift_date", "=", self._today()), ("mfo_vehicle_id", "!=", False)]
        ).mapped("mfo_vehicle_id").ids
        total_active = Vehicle.search_count([("mfo_active_for_ops", "=", True)])
        return len(active_vehicle_ids), max(total_active - len(active_vehicle_ids), 0)

    def _task_scope_domain(self, role_code, user):
        if role_code in {
            "director",
            "general_manager",
            "system_admin",
            "hr",
            "accountant",
            "finance_officer",
            "storekeeper",
            "office_clerk",
            "contract_officer",
        }:
            return []
        if role_code == "department_head":
            return [
                "|",
                ("project_id.ops_department_id.manager_id.user_id", "=", user.id),
                ("project_id.user_id", "=", user.id),
            ]
        if role_code == "project_leader":
            return ["|", ("project_id.user_id", "=", user.id), ("create_uid", "=", user.id)]
        if role_code in {"senior_master", "master"}:
            return ["|", ("ops_team_leader_id", "=", user.id), ("user_ids", "in", user.id)]
        if role_code == "driver":
            return ["|", ("mfo_driver_employee_id.user_id", "=", user.id), ("user_ids", "in", user.id)]
        if role_code == "loader":
            return ["|", ("mfo_collector_employee_ids.user_id", "=", user.id), ("user_ids", "in", user.id)]
        if role_code == "inspector":
            return ["|", ("mfo_inspector_employee_id.user_id", "=", user.id), ("user_ids", "in", user.id)]
        if role_code == "garage_mechanic":
            return ["|", ("repair_request_ids.mechanic_id", "=", user.id), ("user_ids", "in", user.id)]
        return [("user_ids", "in", user.id)]

    def _project_scope_domain(self, role_code, user):
        if role_code in {
            "director",
            "general_manager",
            "system_admin",
            "hr",
            "accountant",
            "finance_officer",
            "storekeeper",
            "office_clerk",
            "contract_officer",
        }:
            return []
        if role_code == "department_head":
            return ["|", ("ops_department_id.manager_id.user_id", "=", user.id), ("user_id", "=", user.id)]
        if role_code == "project_leader":
            return [("user_id", "=", user.id)]
        if role_code in {
            "senior_master",
            "master",
            "employee",
            "driver",
            "loader",
            "inspector",
            "garage_mechanic",
        }:
            return [("task_ids.user_ids", "in", user.id)]
        return []

    def _report_scope_domain(self, role_code, user):
        if role_code in {
            "director",
            "general_manager",
            "system_admin",
            "hr",
            "accountant",
            "finance_officer",
        }:
            return []
        if role_code == "department_head":
            return [
                "|",
                ("task_id.project_id.ops_department_id.manager_id.user_id", "=", user.id),
                ("task_id.project_id.user_id", "=", user.id),
            ]
        if role_code == "project_leader":
            return [("task_id.project_id.user_id", "=", user.id)]
        if role_code in {"senior_master", "master"}:
            return ["|", ("task_id.ops_team_leader_id", "=", user.id), ("task_id.user_ids", "in", user.id)]
        if role_code == "driver":
            return ["|", ("task_id.mfo_driver_employee_id.user_id", "=", user.id), ("reporter_id", "=", user.id)]
        if role_code == "loader":
            return ["|", ("task_id.mfo_collector_employee_ids.user_id", "=", user.id), ("reporter_id", "=", user.id)]
        if role_code == "inspector":
            return ["|", ("task_id.mfo_inspector_employee_id.user_id", "=", user.id), ("reporter_id", "=", user.id)]
        return ["|", ("reporter_id", "=", user.id), ("task_id.user_ids", "in", user.id)]

    def _procurement_scope_domain(self, role_code, user):
        if role_code in {
            "director",
            "general_manager",
            "system_admin",
            "accountant",
            "finance_officer",
            "office_clerk",
            "contract_officer",
        }:
            return []
        if role_code == "storekeeper":
            return [("responsible_storekeeper_user_id", "=", user.id)]
        if role_code in {"department_head", "project_leader"}:
            return [
                "|",
                "|",
                ("department_id.manager_id.user_id", "=", user.id),
                ("project_id.user_id", "=", user.id),
                ("requester_user_id", "=", user.id),
            ]
        return [("task_id.user_ids", "in", user.id)]

    def _repair_scope_domain(self, role_code, user):
        if role_code in {
            "director",
            "general_manager",
            "system_admin",
            "accountant",
            "finance_officer",
            "storekeeper",
        }:
            return []
        if role_code == "garage_mechanic":
            return [("mechanic_id", "=", user.id)]
        if role_code in {"senior_master", "master"}:
            return [("team_leader_id", "=", user.id)]
        return [("repair_task_id.user_ids", "in", user.id)]

    def _today_task_domain(self, role_code, user):
        return self._task_scope_domain(role_code, user) + [
            "|",
            ("mfo_shift_date", "=", self._today()),
            ("date_deadline", "=", self._today()),
        ]

    def _overdue_task_domain(self, role_code, user):
        return self._task_scope_domain(role_code, user) + [
            ("date_deadline", "!=", False),
            ("date_deadline", "<", self._today()),
            ("stage_id.fold", "=", False),
        ]

    def _review_task_domain(self, role_code, user):
        return self._task_scope_domain(role_code, user) + [
            "|",
            ("stage_id.name", "ilike", "Шал"),
            ("state", "=", "02_changes_requested"),
        ]

    def _payload_director(self, user):
        active_vehicle, idle_vehicle = self._vehicle_activity_counts()
        pending_procurement = self._count("mpw.procurement.request", [("state", "=", "director_pending")])
        pending_repair = self._count("fleet.repair.request", [("state", "=", "waiting_ceo")])
        payload = self._empty_payload(
            "Захирлын орон зай",
            "Нийт байгууллагын шийдвэр, KPI, өндөр дүнтэй урсгалыг эндээс харна.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Нийт KPI", self._format_number(self._count("project.project", [("active", "=", True)]))),
                (
                    "Өнөөдрийн гүйцэтгэл",
                    self._format_number(
                        self._count("project.task", [("stage_id.fold", "=", True), ("write_date", ">=", self._day_start())])
                    ),
                ),
                (
                    "Хоцорсон ажил",
                    self._format_number(self._count("project.task", [("date_deadline", "<", self._today()), ("stage_id.fold", "=", False)])),
                ),
                ("Батлах авалт", self._format_number(pending_procurement + pending_repair)),
                (
                    "1 сая+ хүсэлт",
                    self._format_number(
                        self._count(
                            "mpw.procurement.request",
                            [("is_over_threshold", "=", True), ("state", "not in", ["done", "cancelled"])],
                        )
                    ),
                ),
                ("Алба нэгж", self._format_number(self._count("hr.department", [("active", "=", True)]))),
                ("Идэвхтэй машин", self._format_number(active_vehicle)),
                (
                    "Санхүүгийн товч төлөв",
                    self._format_number(self._count("mpw.procurement.request", [("payment_status", "=", "unpaid")])),
                ),
            ],
        )
        payload["highlight_html"] = self._render_panel("Алба нэгжийн гүйцэтгэл", self._department_performance_items())
        payload["performance_html"] = self._render_panel(
            "Машин ба санхүү",
            [
                ("Идэвхтэй машин", active_vehicle, "ok"),
                ("Ажиллаагүй машин", idle_vehicle, "warn" if idle_vehicle else "ok"),
                ("Төлбөр хүлээгдэж буй хүсэлт", self._count("mpw.procurement.request", [("payment_status", "=", "unpaid")]), "warn"),
                ("Засварын CEO баталгаа", pending_repair, "warn" if pending_repair else "soft"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах ажил",
            [
                ("Хоцорсон ажил", self._count("project.task", [("date_deadline", "<", self._today()), ("stage_id.fold", "=", False)]), "danger"),
                (
                    "Өндөр дүнтэй авалт",
                    self._count("mpw.procurement.request", [("is_over_threshold", "=", True), ("state", "not in", ["done", "cancelled"])]),
                    "warn",
                ),
                ("Засварт саатсан машин", self._count("fleet.repair.request", [("is_overdue", "=", True)]), "danger"),
            ],
        )
        return payload

    def _payload_general_manager(self, user):
        active_vehicle, idle_vehicle = self._vehicle_activity_counts()
        weekly_weight = self._sum(
            "mfo.daily.weight.total",
            "net_weight_total",
            [("shift_date", ">=", self._week_start()), ("shift_date", "<=", self._today())],
        )
        payload = self._empty_payload(
            "Ерөнхий менежерийн орон зай",
            "Өдөр тутмын ажлын урсгал, машин, маршрут, гүйцэтгэлийг нэг дэлгэцээс хянана.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Өнөөдрийн ажил", self._format_number(self._count("project.task", self._today_task_domain("general_manager", user)))),
                ("7 хоногийн кг", self._format_number(weekly_weight)),
                ("Идэвхтэй машин", self._format_number(active_vehicle)),
                ("Ажиллаагүй машин", self._format_number(idle_vehicle)),
                (
                    "Хоцорсон маршрут",
                    self._format_number(
                        self._count(
                            "project.task",
                            [("mfo_shift_date", "<", self._today()), ("mfo_state", "not in", ["verified", "cancelled"]), ("mfo_route_id", "!=", False)],
                        )
                    ),
                ),
                ("Айл өрх / ААН / талбай", self._format_number(self._count("mfo.collection.point", [("active", "=", True)]))),
                ("Алба нэгжийн гүйцэтгэл", self._format_number(len(self._department_performance_items()))),
                ("Анхаарах ажил", self._format_number(self._count("project.task", self._overdue_task_domain("general_manager", user)))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Ажлын ангиллын товч төлөв",
            [
                (
                    "Айл өрх / ААН / нийтийн талбай",
                    "Одоогийн master data-д тусдаа ангиллын талбаргүй, нийт цэгийн тоо харуулж байна.",
                    "soft",
                ),
                ("Нийт цэг", self._count("mfo.collection.point", [("active", "=", True)]), "ok"),
                ("Нийт маршрут", self._count("mfo.route", [("active", "=", True)]), "ok"),
            ],
        )
        payload["performance_html"] = self._render_panel("Алба нэгжийн гүйцэтгэл", self._department_performance_items())
        payload["alert_html"] = self._render_panel(
            "Анхаарал шаардсан ажил",
            [
                ("Хоцорсон ажил", self._count("project.task", self._overdue_task_domain("general_manager", user)), "danger"),
                ("Шалгах тайлан", self._count("project.task", self._review_task_domain("general_manager", user)), "warn"),
                ("Засварт саатсан машин", self._count("fleet.repair.request", [("is_overdue", "=", True)]), "warn"),
            ],
        )
        return payload

    def _payload_department_head(self, user):
        payload = self._empty_payload(
            "Хэлтсийн даргын орон зай",
            "Өөрийн хэлтэс, төслүүд, баталгаажуулах урсгал, хоцролтыг хянах самбар.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Өөрийн хэлтсийн ажил", self._format_number(self._count("project.task", self._task_scope_domain("department_head", user)))),
                ("Төслүүд", self._format_number(self._count("project.project", self._project_scope_domain("department_head", user)))),
                ("Ирсэн тайлан", self._format_number(self._count("ops.task.report", self._report_scope_domain("department_head", user)))),
                ("Эцсийн баталгаа", self._format_number(self._count("project.task", self._review_task_domain("department_head", user)))),
                ("Чөлөө / өвчтэй", self._format_number(self._count("hr.leave", [("state", "in", ["confirm", "validate1", "validate"])]) if self._get_model("hr.leave") else 0)),
                ("Хэлтсийн хоцролт", self._format_number(self._count("project.task", self._overdue_task_domain("department_head", user)))),
                ("Хэлтсийн авалт", self._format_number(self._count("mpw.procurement.request", self._procurement_scope_domain("department_head", user)))),
                ("Шуурхай ажил", self._format_number(self._count("project.task", self._today_task_domain("department_head", user)))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Хэлтсийн товч төлөв",
            [
                ("Өнөөдрийн ажил", self._count("project.task", self._today_task_domain("department_head", user)), "ok"),
                ("Шалгах ажил", self._count("project.task", self._review_task_domain("department_head", user)), "warn"),
                ("Хоцролт", self._count("project.task", self._overdue_task_domain("department_head", user)), "danger"),
            ],
        )
        payload["performance_html"] = self._render_panel("Алба нэгжийн дэлгэрэнгүй", self._department_performance_items())
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Чөлөөний модель", "Хэрэв HR Holidays суусан бол чөлөө / өвчтэй хүсэлтийн тоо харагдана.", "soft"),
                ("Эцсийн баталгаа", self._count("project.task", self._review_task_domain("department_head", user)), "warn"),
            ],
        )
        return payload

    def _payload_project_leader(self, user):
        payload = self._empty_payload(
            "Төслийн удирдагчийн орон зай",
            "Хариуцсан төсөл, ажил хуваарилалт, өдөр тутмын гүйцэтгэл, тайлангийн хяналт.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Хариуцсан төсөл", self._format_number(self._count("project.project", self._project_scope_domain("project_leader", user)))),
                ("Task үүсгэх", self._format_number(self._count("project.task", self._task_scope_domain("project_leader", user)))),
                ("Ажил хуваарилалт", self._format_number(self._count("project.task", self._today_task_domain("project_leader", user)))),
                ("Өдөр тутмын гүйцэтгэл", self._format_number(self._count("project.task", self._review_task_domain("project_leader", user)))),
                ("Тайлан хянах", self._format_number(self._count("ops.task.report", self._report_scope_domain("project_leader", user)))),
                ("Худалдан авалт", self._format_number(self._count("mpw.procurement.request", self._procurement_scope_domain("project_leader", user)))),
                ("Хоцролт", self._format_number(self._count("project.task", self._overdue_task_domain("project_leader", user)))),
                ("Идэвхтэй маршрут", self._format_number(self._count("mfo.route", [("project_id.user_id", "=", user.id)]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Өдөр тутмын гүйцэтгэл",
            [
                ("Өнөөдрийн ажил", self._count("project.task", self._today_task_domain("project_leader", user)), "ok"),
                ("Шалгах тайлан", self._count("project.task", self._review_task_domain("project_leader", user)), "warn"),
                ("Хоцролт", self._count("project.task", self._overdue_task_domain("project_leader", user)), "danger"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Төслийн урсгал",
            [
                ("Идэвхтэй төсөл", self._count("project.project", self._project_scope_domain("project_leader", user)), "ok"),
                ("Гүйцэтгэж буй ажил", self._count("project.task", self._task_scope_domain("project_leader", user) + [("stage_id.fold", "=", False)]), "ok"),
                ("Хоцорсон ажил", self._count("project.task", self._overdue_task_domain("project_leader", user)), "danger"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Хүлээгдэж буй авалт", self._count("mpw.procurement.request", self._procurement_scope_domain("project_leader", user) + [("state", "not in", ["done", "cancelled"])]), "warn"),
                (
                    "Маршрутын саатал",
                    self._count(
                        "project.task",
                        [("project_id.user_id", "=", user.id), ("mfo_shift_date", "<", self._today()), ("mfo_state", "not in", ["verified", "cancelled"])],
                    ),
                    "danger",
                ),
            ],
        )
        return payload

    def _payload_senior_master(self, user):
        payload = self._empty_payload(
            "Ахлах мастерын орон зай",
            "Өөрийн багийн ажил, ирсэн тайлан, шалгалт, буцаалтын урсгал.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Багийн ажил", self._format_number(self._count("project.task", self._task_scope_domain("senior_master", user)))),
                ("Ирсэн тайлан", self._format_number(self._count("ops.task.report", self._report_scope_domain("senior_master", user)))),
                ("Шалгах ажил", self._format_number(self._count("project.task", self._review_task_domain("senior_master", user)))),
                ("Буцаах боломж", self._format_number(self._count("project.task", self._review_task_domain("senior_master", user)))),
                ("Өнөөдрийн хуваарь", self._format_number(self._count("project.task", self._today_task_domain("senior_master", user)))),
                ("Багийн машин", self._format_number(self._count("project.task", self._task_scope_domain("senior_master", user) + [("mfo_vehicle_id", "!=", False)]))),
                ("Хоцролт", self._format_number(self._count("project.task", self._overdue_task_domain("senior_master", user)))),
                ("Нийт тайлан зураг", self._format_number(self._count("mfo.proof.image", [("task_id.ops_team_leader_id", "=", user.id)]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Багийн шалгалт",
            [
                ("Шалгах тайлан", self._count("project.task", self._review_task_domain("senior_master", user)), "warn"),
                ("Хоцорсон ажил", self._count("project.task", self._overdue_task_domain("senior_master", user)), "danger"),
                ("Зураг дутуу тайлан", self._count("ops.task.report", self._report_scope_domain("senior_master", user) + [("image_count", "=", 0)]) if "image_count" in self.env["ops.task.report"]._fields else 0, "warn"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Гүйцэтгэлийн мөрүүд",
            [
                ("Өнөөдөр эхлэх", self._count("project.task", self._today_task_domain("senior_master", user)), "ok"),
                ("Дууссан", self._count("project.task", self._task_scope_domain("senior_master", user) + [("stage_id.fold", "=", True)]), "ok"),
                ("Шалгаж буй", self._count("project.task", self._review_task_domain("senior_master", user)), "warn"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Баталгаажуулах эрхгүй", "Ахлах мастер зөвхөн шалгаж, буцаах урсгалыг ашиглана.", "soft"),
                ("Хоцорсон ажил", self._count("project.task", self._overdue_task_domain("senior_master", user)), "danger"),
            ],
        )
        return payload

    def _payload_master(self, user):
        payload = self._empty_payload(
            "Мастерын орон зай",
            "Өөрийн task, ажил хуваарилалт, тайлан, хоцролт, зураг ба аудио бүртгэл.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Өөрийн task", self._format_number(self._count("project.task", self._task_scope_domain("master", user)))),
                ("Ажил хуваарилалт", self._format_number(self._count("project.task", self._today_task_domain("master", user)))),
                ("Тайлан оруулах", self._format_number(self._count("ops.task.report", self._report_scope_domain("master", user)))),
                ("Хоцролт", self._format_number(self._count("project.task", self._overdue_task_domain("master", user)))),
                ("Зураг", self._format_number(self._count("mfo.proof.image", [("task_id.ops_team_leader_id", "=", user.id)]))),
                ("Аудио", self._format_number(self._count("ops.task.report", self._report_scope_domain("master", user) + [("audio_count", ">", 0)]) if "audio_count" in self.env["ops.task.report"]._fields else 0)),
                ("Маршрут", self._format_number(self._count("project.task", [("ops_team_leader_id", "=", user.id), ("mfo_route_id", "!=", False)]))),
                ("Илгээхэд бэлэн", self._format_number(self._count("project.task", self._task_scope_domain("master", user) + [("stage_id.fold", "=", False)]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Шуурхай урсгал",
            [
                ("Өнөөдрийн хуваарь", self._count("project.task", self._today_task_domain("master", user)), "ok"),
                ("Хоцорсон ажил", self._count("project.task", self._overdue_task_domain("master", user)), "danger"),
                ("Шалгах шат", self._count("project.task", self._review_task_domain("master", user)), "warn"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Талбайн тайлан",
            [
                ("Зурагтай тайлан", self._count("ops.task.report", self._report_scope_domain("master", user) + [("image_count", ">", 0)]) if "image_count" in self.env["ops.task.report"]._fields else 0, "ok"),
                ("Аудиотой тайлан", self._count("ops.task.report", self._report_scope_domain("master", user) + [("audio_count", ">", 0)]) if "audio_count" in self.env["ops.task.report"]._fields else 0, "ok"),
                ("Жинтэй тайлан", self._count("mfo.daily.weight.total", [("task_id.ops_team_leader_id", "=", user.id)]), "ok"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Зураггүй тайлан", self._count("ops.task.report", self._report_scope_domain("master", user) + [("image_count", "=", 0)]) if "image_count" in self.env["ops.task.report"]._fields else 0, "warn"),
                ("Хоцорсон task", self._count("project.task", self._overdue_task_domain("master", user)), "danger"),
            ],
        )
        return payload

    def _payload_employee(self, user):
        payload = self._empty_payload(
            "Ажилтны орон зай",
            "Өөрт оноогдсон ажил, тайлан, зураг, аудио, дууссан тэмдэглэгээг эндээс удирдана.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Өөрийн ажил", self._format_number(self._count("project.task", self._task_scope_domain("employee", user)))),
                ("Тайлан", self._format_number(self._count("ops.task.report", self._report_scope_domain("employee", user)))),
                ("Зураг", self._format_number(self._count("mfo.proof.image", [("uploader_user_id", "=", user.id)]))),
                ("Аудио", self._format_number(self._count("ops.task.report", [("reporter_id", "=", user.id), ("audio_count", ">", 0)]) if "audio_count" in self.env["ops.task.report"]._fields else 0)),
                ("Дууссан", self._format_number(self._count("project.task", self._task_scope_domain("employee", user) + [("stage_id.fold", "=", True)]))),
                ("Өнөөдрийн ажил", self._format_number(self._count("project.task", self._today_task_domain("employee", user)))),
                ("Хоцорсон", self._format_number(self._count("project.task", self._overdue_task_domain("employee", user)))),
                ("Тайлангүй ажил", self._format_number(self._count("project.task", [("user_ids", "in", user.id), ("ops_report_ids", "=", False)]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Өдөр тутмын ажил",
            [
                ("Өнөөдрийн ажил", self._count("project.task", self._today_task_domain("employee", user)), "ok"),
                ("Дууссан", self._count("project.task", self._task_scope_domain("employee", user) + [("stage_id.fold", "=", True)]), "ok"),
                ("Хоцорсон", self._count("project.task", self._overdue_task_domain("employee", user)), "danger"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Тайлангийн багц",
            [
                ("Зурагтай тайлан", self._count("ops.task.report", [("reporter_id", "=", user.id), ("image_count", ">", 0)]) if "image_count" in self.env["ops.task.report"]._fields else 0, "ok"),
                ("Аудиотой тайлан", self._count("ops.task.report", [("reporter_id", "=", user.id), ("audio_count", ">", 0)]) if "audio_count" in self.env["ops.task.report"]._fields else 0, "ok"),
                ("Тайлангүй ажил", self._count("project.task", [("user_ids", "in", user.id), ("ops_report_ids", "=", False)]), "warn"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Хоцорсон ажил", self._count("project.task", self._overdue_task_domain("employee", user)), "danger"),
                ("Зураг хавсаргаагүй", self._count("ops.task.report", [("reporter_id", "=", user.id), ("image_count", "=", 0)]) if "image_count" in self.env["ops.task.report"]._fields else 0, "warn"),
            ],
        )
        return payload

    def _payload_hr(self, user):
        leave_count = self._count("hr.leave", [("state", "in", ["confirm", "validate1", "validate"])]) if self._get_model("hr.leave") else 0
        payload = self._empty_payload(
            "Хүний нөөцийн орон зай",
            "Ажилтан, чөлөө, сахилга, суутгал, гаралт, шилжилт, тойрох хуудасны урсгал.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Ажилтны бүртгэл", self._format_number(self._count("hr.employee", [("active", "=", True)]))),
                ("Чөлөө / өвчтэй", self._format_number(leave_count)),
                ("Сахилгын бүртгэл", self._format_number(self._count("hr.disciplinary.action", []))),
                ("Сануулга", self._format_number(self._count("hr.disciplinary.action", [("action_type", "=", "warning")]))),
                ("20% суутгал", self._format_number(self._count("hr.disciplinary.action", [("action_type", "=", "salary_deduction_20")]))),
                ("Ажлаас гаралт", self._format_number(self._count("hr.employee.clearance", []))),
                ("Шилжилт хөдөлгөөн", self._format_number(self._count("hr.employee.transfer", []))),
                ("Тойрох хуудас", self._format_number(self._count("hr.employee.clearance", [("state", "!=", "done")]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Хүний нөөцийн товч төлөв",
            [
                ("Идэвхтэй ажилтан", self._count("hr.employee", [("active", "=", True)]), "ok"),
                ("Архивласан ажилтан", self._count("hr.employee", [("active", "=", False)]), "warn"),
                ("Чөлөөний модель", "Хэрэв HR Holidays суусан бол чөлөөний тоо бодитоор харагдана.", "soft"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Зөрчил ба шилжилт",
            [
                ("Сахилгын ноорог", self._count("hr.disciplinary.action", [("state", "=", "draft")]), "warn"),
                ("Батлуулахаар илгээсэн", self._count("hr.disciplinary.action", [("state", "=", "submitted")]), "warn"),
                ("Шилжилтийн ноорог", self._count("hr.employee.transfer", [("state", "=", "draft")]), "ok"),
                ("Тойрох хуудсын явц", self._count("hr.employee.clearance", [("state", "=", "in_progress")]), "warn"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Архивлах шаардлагатай гаралт", self._count("hr.employee.clearance", [("state", "=", "done")]), "warn"),
                ("Захирлын баталгаа хүлээж буй", self._count("hr.disciplinary.action", [("state", "=", "submitted")]) + self._count("hr.employee.transfer", [("state", "=", "submitted")]), "danger"),
            ],
        )
        return payload

    def _payload_accountant(self, user):
        payload = self._empty_payload(
            "Нягтлан бодогчийн орон зай",
            "Төлбөр, нөхцөл, батлагдсан санхүүгийн урсгал, санхүүгийн товч тайлан.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Төлбөрийн мэдээлэл", self._format_number(self._count("mpw.procurement.request", [("state", "not in", ["done", "cancelled"])]))),
                ("Санхүүгийн нөхцөл", self._format_number(self._count("mpw.procurement.request", [("state", "=", "finance_review")]))),
                ("Төлбөр бэлтгэх", self._format_number(self._count("fleet.repair.request", [("state", "=", "waiting_accounting")]))),
                ("Төлсөн төлөв", self._format_number(self._count("mpw.procurement.request", [("payment_status", "=", "paid")]))),
                ("Санхүүгийн тайлан", self._format_number(self._count("fleet.repair.request", [("state", "in", ["waiting_accounting", "admin_order_ready", "fund_prepared"])]))),
                ("1 сая+ хүсэлт", self._format_number(self._count("mpw.procurement.request", [("is_over_threshold", "=", True)]))),
                ("Төлбөр хүлээж буй", self._format_number(self._count("mpw.procurement.request", [("payment_status", "=", "unpaid")]))),
                ("Засварын нэхэмжлэл", self._format_number(self._count("fleet.repair.request", [("state", "in", ["waiting_accounting", "waiting_admin"])]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Санхүүгийн урсгал",
            [
                ("Finance review", self._count("mpw.procurement.request", [("state", "=", "finance_review")]), "warn"),
                ("Төлбөргүй үлдсэн", self._count("mpw.procurement.request", [("payment_status", "=", "unpaid")]), "danger"),
                ("CEO босготой засвар", self._count("fleet.repair.request", [("needs_ceo_approval", "=", True), ("state", "not in", ["done", "cancelled"])]), "warn"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Санхүүгийн төлөв",
            [
                ("Төлсөн хүсэлт", self._count("mpw.procurement.request", [("payment_status", "=", "paid")]), "ok"),
                ("Хүлээн авалтгүй", self._count("mpw.procurement.request", [("payment_status", "=", "paid"), ("receipt_status", "=", "pending")]), "warn"),
                ("Засварын санхүүгийн хяналт", self._count("fleet.repair.request", [("state", "=", "waiting_accounting")]), "warn"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Саатсан төлбөр", self._count("mpw.procurement.request", [("payment_status", "=", "unpaid"), ("is_delayed", "=", True)]), "danger"),
                ("Саатсан засвар", self._count("fleet.repair.request", [("state", "=", "waiting_accounting"), ("is_overdue", "=", True)]), "danger"),
            ],
        )
        return payload

    def _payload_finance_officer(self, user):
        payload = self._empty_payload(
            "Санхүүгийн ажилтны орон зай",
            "Батлагдсан төлбөр, банкны шилжүүлэг, гэрээний нөхцөлтэй төлбөрийн урсгал.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Батлагдсан төлбөр", self._format_number(self._count("mpw.procurement.request", [("state", "in", ["contract_signed", "paid"])]))),
                ("Банкны төлбөр", self._format_number(self._count("mpw.procurement.request", [("payment_status", "=", "unpaid")]))),
                ("Гэрээт төлбөр", self._format_number(self._count("mpw.procurement.request", [("state", "=", "contract_signed")]))),
                ("Төлөв шинэчлэх", self._format_number(self._count("mpw.procurement.request", [("state", "=", "paid")]))),
                ("Засварын хөрөнгө", self._format_number(self._count("fleet.repair.request", [("state", "=", "admin_order_ready")]))),
                ("Төлбөр хүлээж буй", self._format_number(self._count("fleet.repair.request", [("state", "=", "admin_order_ready")]))),
                ("Өнөөдрийн урсгал", self._format_number(self._count("mpw.procurement.request", [("write_date", ">=", self._day_start())]))),
                ("Нийт дүнтэй хүсэлт", self._format_number(self._count("mpw.procurement.request", [("selected_supplier_total", "!=", 0)]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Төлбөрийн ажлууд",
            [
                ("Гэрээ байгуулсан", self._count("mpw.procurement.request", [("state", "=", "contract_signed")]), "ok"),
                ("Төлбөр хүлээж буй", self._count("mpw.procurement.request", [("payment_status", "=", "unpaid")]), "warn"),
                ("Төлсөн", self._count("mpw.procurement.request", [("payment_status", "=", "paid")]), "ok"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Засварын санхүү",
            [
                ("Тушаал бэлэн", self._count("fleet.repair.request", [("state", "=", "admin_order_ready")]), "warn"),
                ("Хөрөнгө бэлэн", self._count("fleet.repair.request", [("state", "=", "fund_prepared")]), "ok"),
                ("Саатсан хөрөнгө", self._count("fleet.repair.request", [("state", "=", "admin_order_ready"), ("is_overdue", "=", True)]), "danger"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Төлбөрийн тайлбар дутуу", self._count("mpw.procurement.request", [("payment_status", "=", "paid"), ("payment_reference", "=", False)]), "warn"),
            ],
        )
        return payload

    def _payload_storekeeper(self, user):
        payload = self._empty_payload(
            "Няравын орон зай",
            "Бараа материал, үнийн санал, хүлээн авалт, агуулахын хөдөлгөөний шуурхай самбар.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Хариуцсан хүсэлт", self._format_number(self._count("mpw.procurement.request", self._procurement_scope_domain("storekeeper", user)))),
                ("Үнийн санал", self._format_number(self._count("mpw.procurement.quotation", [("request_id.responsible_storekeeper_user_id", "=", user.id)]))),
                ("Хүлээн авалт", self._format_number(self._count("mpw.procurement.request", [("responsible_storekeeper_user_id", "=", user.id), ("receipt_status", "=", "received")]))),
                ("Агуулахын хөдөлгөөн", self._format_number(self._count("stock.move", []))),
                ("Сэлбэгийн хүсэлт", self._format_number(self._count("fleet.repair.request", [("state", "in", ["fund_prepared", "purchasing"])]))),
                ("Бараа авсан төлөв", self._format_number(self._count("mpw.procurement.request", [("responsible_storekeeper_user_id", "=", user.id), ("receipt_status", "=", "received")]))),
                ("Хүлээгдэж буй авалт", self._format_number(self._count("mpw.procurement.request", [("responsible_storekeeper_user_id", "=", user.id), ("state", "=", "quotation_waiting")]))),
                ("Засварын худалдан авалт", self._format_number(self._count("fleet.repair.request", [("state", "=", "purchasing")]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Худалдан авалтын урсгал",
            [
                ("Үнийн санал хүлээгдэж буй", self._count("mpw.procurement.request", [("responsible_storekeeper_user_id", "=", user.id), ("state", "=", "quotation_waiting")]), "warn"),
                ("3 санал бүрдсэн", self._count("mpw.procurement.request", [("responsible_storekeeper_user_id", "=", user.id), ("state", "=", "quotations_ready")]), "ok"),
                ("Бараа хүлээн авсан", self._count("mpw.procurement.request", [("responsible_storekeeper_user_id", "=", user.id), ("receipt_status", "=", "received")]), "ok"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Сэлбэг ба агуулах",
            [
                ("Засварын сэлбэг", self._count("fleet.repair.request", [("state", "=", "purchasing")]), "warn"),
                ("Сэлбэг ирсэн", self._count("fleet.repair.request", [("state", "=", "parts_received")]), "ok"),
                ("Агуулахын бичлэг", self._count("stock.move", []), "ok"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Ирц тэмдэглээгүй авалт", self._count("mpw.procurement.request", [("responsible_storekeeper_user_id", "=", user.id), ("payment_status", "=", "paid"), ("receipt_status", "=", "pending")]), "danger"),
            ],
        )
        return payload

    def _payload_office_clerk(self, user):
        payload = self._empty_payload(
            "Бичиг хэргийн орон зай",
            "Захирлын тушаал, 1 саяас дээш авалтын файл, тушаалын төлөвийн самбар.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Тушаал бэлтгэх", self._format_number(self._count("mpw.procurement.request", [("state", "=", "order_preparing")]))),
                ("1 сая+ хүсэлт", self._format_number(self._count("mpw.procurement.request", [("is_over_threshold", "=", True), ("state", "not in", ["done", "cancelled"])]))),
                ("Файл хавсаргах", self._format_number(self._count("mpw.procurement.document", [("document_type", "=", "director_order_final")]))),
                ("Тушаал гарсан", self._format_number(self._count("mpw.procurement.request", [("state", "=", "order_issued")]))),
                ("CEO шийдвэр", self._format_number(self._count("mpw.procurement.request", [("state", "=", "director_pending")]))),
                ("Засварын тушаал", self._format_number(self._count("fleet.repair.request", [("state", "=", "approved_ceo")]))),
                ("Өнөөдрийн урсгал", self._format_number(self._count("mpw.procurement.request", [("write_date", ">=", self._day_start())]))),
                ("Дутуу файл", self._format_number(self._count("mpw.procurement.request", [("state", "in", ["order_preparing", "decision_approved"]), ("director_order_attachment_count", "=", 0)]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Тушаалын урсгал",
            [
                ("Бэлтгэж буй", self._count("mpw.procurement.request", [("state", "=", "order_preparing")]), "warn"),
                ("Шийдвэр хүлээж буй", self._count("mpw.procurement.request", [("state", "=", "director_pending")]), "warn"),
                ("Тушаал гарсан", self._count("mpw.procurement.request", [("state", "=", "order_issued")]), "ok"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Засварын тушаал",
            [
                ("CEO зөвшөөрсөн", self._count("fleet.repair.request", [("state", "=", "approved_ceo")]), "warn"),
                ("Тушаал бэлэн", self._count("fleet.repair.request", [("state", "=", "admin_order_ready")]), "ok"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Файлгүй тушаал", self._count("fleet.repair.request", [("state", "=", "admin_order_ready"), ("director_order_attachment_id", "=", False)]), "danger"),
            ],
        )
        return payload

    def _payload_contract_officer(self, user):
        payload = self._empty_payload(
            "Гэрээний ажилтны орон зай",
            "Гэрээ бэлтгэх, байгуулах, файл хавсаргах, төлөв шинэчлэх урсгал.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Гэрээ бэлтгэх", self._format_number(self._count("mpw.procurement.request", [("state", "=", "contract_preparing")]))),
                ("Гэрээ байгуулсан", self._format_number(self._count("mpw.procurement.request", [("state", "=", "contract_signed")]))),
                ("Гэрээний файл", self._format_number(self._count("mpw.procurement.document", [("document_type", "=", "contract_final")]))),
                ("Төлөв шинэчлэх", self._format_number(self._count("mpw.procurement.request", [("state", "in", ["contract_preparing", "contract_signed"])]))),
                ("Өндөр дүнтэй урсгал", self._format_number(self._count("mpw.procurement.request", [("is_over_threshold", "=", True), ("state", "in", ["order_issued", "contract_preparing", "contract_signed"])]))),
                ("Төлбөр хүлээж буй", self._format_number(self._count("mpw.procurement.request", [("state", "=", "contract_signed"), ("payment_status", "=", "unpaid")]))),
                ("Хүлээн авалт", self._format_number(self._count("mpw.procurement.request", [("state", "=", "paid"), ("receipt_status", "=", "pending")]))),
                ("Гэрээ дутуу", self._format_number(self._count("mpw.procurement.request", [("state", "=", "contract_preparing"), ("contract_attachment_count", "=", 0)]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Гэрээний урсгал",
            [
                ("Бэлтгэж буй", self._count("mpw.procurement.request", [("state", "=", "contract_preparing")]), "warn"),
                ("Байгуулагдсан", self._count("mpw.procurement.request", [("state", "=", "contract_signed")]), "ok"),
                ("Төлбөрт шилжсэн", self._count("mpw.procurement.request", [("state", "=", "paid")]), "ok"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Файлын бүрдэл",
            [
                ("Гэрээний ноорог", self._count("mpw.procurement.document", [("document_type", "=", "contract_draft")]), "warn"),
                ("Эцсийн гэрээ", self._count("mpw.procurement.document", [("document_type", "=", "contract_final")]), "ok"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Файл хавсаргаагүй гэрээ", self._count("mpw.procurement.request", [("state", "=", "contract_preparing"), ("contract_attachment_count", "=", 0)]), "danger"),
            ],
        )
        return payload

    def _payload_garage_mechanic(self, user):
        payload = self._empty_payload(
            "Гаражийн механикийн орон зай",
            "Үзлэг, засварын шаардлага, сэлбэгийн хэрэгцээ, засварын төлөв, бэлэн болсон машин.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Үзлэг", self._format_number(self._count("fleet.repair.request", [("mechanic_id", "=", user.id)]))),
                ("Засварын шаардлага", self._format_number(self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("state", "not in", ["done", "cancelled"])]))),
                ("Сэлбэгийн хэрэгцээ", self._format_number(self._count("fleet.repair.request.line", [("request_id.mechanic_id", "=", user.id)]))),
                ("Засварын төлөв", self._format_number(self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("state", "=", "in_repair")]))),
                ("Бэлэн болсон машин", self._format_number(self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("state", "=", "done")]))),
                ("Саатсан засвар", self._format_number(self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("is_overdue", "=", True)]))),
                ("Өнөөдрийн засвар", self._format_number(self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("inspection_date", ">=", self._day_start())]))),
                ("Зураг", self._format_number(self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("inspection_image_ids", "!=", False)]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Засварын урсгал",
            [
                ("Үзлэг илгээсэн", self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("state", "=", "submitted")]), "warn"),
                ("Сэлбэг ирсэн", self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("state", "=", "parts_received")]), "ok"),
                ("Засварт орсон", self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("state", "=", "in_repair")]), "warn"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Машины бэлэн байдал",
            [
                ("Бэлэн болсон", self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("state", "=", "done")]), "ok"),
                ("Саатсан", self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("is_overdue", "=", True)]), "danger"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Хүлээгдэж буй сэлбэг", self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("state", "=", "purchasing")]), "warn"),
                ("Шалгалтад очсон", self._count("fleet.repair.request", [("mechanic_id", "=", user.id), ("state", "=", "waiting_repair_approval")]), "warn"),
            ],
        )
        return payload

    def _payload_driver(self, user):
        payload = self._empty_payload(
            "Жолоочийн орон зай",
            "Өөрийн машин, өдөр тутмын маршрут, ачсан кг, рейс, эхэлсэн болон дууссан төлөв.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Өөрийн машин", self._format_number(self._count("project.task", [("mfo_driver_employee_id.user_id", "=", user.id), ("mfo_vehicle_id", "!=", False)]))),
                ("Өдрийн маршрут", self._format_number(self._count("project.task", [("mfo_driver_employee_id.user_id", "=", user.id), ("mfo_shift_date", "=", self._today())]))),
                ("Ачсан кг", self._format_number(self._sum("mfo.daily.weight.total", "net_weight_total", [("task_id.mfo_driver_employee_id.user_id", "=", user.id), ("shift_date", ">=", self._week_start())]))),
                ("Рейсийн тоо", self._format_number(self._count("project.task", [("mfo_driver_employee_id.user_id", "=", user.id), ("mfo_route_id", "!=", False)]))),
                ("Маршрут эхэлсэн", self._format_number(self._count("project.task", [("mfo_driver_employee_id.user_id", "=", user.id), ("mfo_state", "=", "in_progress")]))),
                ("Маршрут дууссан", self._format_number(self._count("project.task", [("mfo_driver_employee_id.user_id", "=", user.id), ("mfo_state", "=", "verified")]))),
                ("Саатал", self._format_number(self._count("project.task", [("mfo_driver_employee_id.user_id", "=", user.id), ("mfo_shift_date", "<", self._today()), ("mfo_state", "not in", ["verified", "cancelled"])]))),
                ("Зурагтай баталгаа", self._format_number(self._count("mfo.proof.image", [("task_id.mfo_driver_employee_id.user_id", "=", user.id)]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Жолоочийн урсгал",
            [
                ("Өнөөдрийн маршрут", self._count("project.task", [("mfo_driver_employee_id.user_id", "=", user.id), ("mfo_shift_date", "=", self._today())]), "ok"),
                ("Эхэлсэн", self._count("project.task", [("mfo_driver_employee_id.user_id", "=", user.id), ("mfo_state", "=", "in_progress")]), "warn"),
                ("Дууссан", self._count("project.task", [("mfo_driver_employee_id.user_id", "=", user.id), ("mfo_state", "=", "verified")]), "ok"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Жин ба рейс",
            [
                ("7 хоногийн кг", self._format_number(self._sum("mfo.daily.weight.total", "net_weight_total", [("task_id.mfo_driver_employee_id.user_id", "=", user.id), ("shift_date", ">=", self._week_start())])), "ok"),
                ("Рейс", self._count("project.task", [("mfo_driver_employee_id.user_id", "=", user.id), ("mfo_route_id", "!=", False)]), "ok"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Хоцорсон маршрут", self._count("project.task", [("mfo_driver_employee_id.user_id", "=", user.id), ("mfo_shift_date", "<", self._today()), ("mfo_state", "not in", ["verified", "cancelled"])]), "danger"),
            ],
        )
        return payload

    def _payload_loader(self, user):
        payload = self._empty_payload(
            "Ачигчийн орон зай",
            "Өөрийн хуваарилагдсан ажил, цэг бүрийн гүйцэтгэл, зурагтай тайлан, дууссан тэмдэглэгээ.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Өөрийн ажил", self._format_number(self._count("project.task", [("mfo_collector_employee_ids.user_id", "=", user.id)]))),
                ("Цэгийн гүйцэтгэл", self._format_number(self._count("mfo.stop.execution.line", [("task_id.mfo_collector_employee_ids.user_id", "=", user.id)]))),
                ("Зурагтай тайлан", self._format_number(self._count("mfo.proof.image", [("uploader_user_id", "=", user.id)]))),
                ("Дууссан", self._format_number(self._count("project.task", [("mfo_collector_employee_ids.user_id", "=", user.id), ("mfo_state", "=", "verified")]))),
                ("Өнөөдрийн ажил", self._format_number(self._count("project.task", [("mfo_collector_employee_ids.user_id", "=", user.id), ("mfo_shift_date", "=", self._today())]))),
                ("Алгассан цэг", self._format_number(self._count("mfo.stop.execution.line", [("task_id.mfo_collector_employee_ids.user_id", "=", user.id), ("status", "=", "skipped")]))),
                ("Асуудал", self._format_number(self._count("mfo.issue.report", [("task_id.mfo_collector_employee_ids.user_id", "=", user.id)]))),
                ("Хоцролт", self._format_number(self._count("project.task", [("mfo_collector_employee_ids.user_id", "=", user.id), ("mfo_shift_date", "<", self._today()), ("mfo_state", "not in", ["verified", "cancelled"])]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Цэгийн гүйцэтгэл",
            [
                ("Гүйцэтгэсэн цэг", self._count("mfo.stop.execution.line", [("task_id.mfo_collector_employee_ids.user_id", "=", user.id), ("status", "=", "done")]), "ok"),
                ("Алгассан цэг", self._count("mfo.stop.execution.line", [("task_id.mfo_collector_employee_ids.user_id", "=", user.id), ("status", "=", "skipped")]), "warn"),
                ("Зурагтай баталгаа", self._count("mfo.proof.image", [("uploader_user_id", "=", user.id)]), "ok"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Өдөр тутмын ажил",
            [
                ("Өнөөдрийн ажил", self._count("project.task", [("mfo_collector_employee_ids.user_id", "=", user.id), ("mfo_shift_date", "=", self._today())]), "ok"),
                ("Дууссан", self._count("project.task", [("mfo_collector_employee_ids.user_id", "=", user.id), ("mfo_state", "=", "verified")]), "ok"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Хоцорсон ажил", self._count("project.task", [("mfo_collector_employee_ids.user_id", "=", user.id), ("mfo_shift_date", "<", self._today()), ("mfo_state", "not in", ["verified", "cancelled"])]), "danger"),
            ],
        )
        return payload

    def _payload_inspector(self, user):
        payload = self._empty_payload(
            "Хяналтын ажилтны орон зай",
            "Дууссан ажил, зураг, тайлан, буцаалт, чанарын хяналтын тайланг эндээс хянаж удирдана.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Дууссан ажил", self._format_number(self._count("project.task", [("mfo_inspector_employee_id.user_id", "=", user.id), ("mfo_state", "=", "submitted")]))),
                ("Шалгах зураг", self._format_number(self._count("mfo.proof.image", [("task_id.mfo_inspector_employee_id.user_id", "=", user.id)]))),
                ("Буцаах", self._format_number(self._count("project.task", [("mfo_inspector_employee_id.user_id", "=", user.id), ("mfo_state", "=", "submitted")]))),
                ("Чанарын тайлан", self._format_number(self._count("mfo.issue.report", [("task_id.mfo_inspector_employee_id.user_id", "=", user.id)]))),
                ("Өнөөдрийн шалгалт", self._format_number(self._count("project.task", [("mfo_inspector_employee_id.user_id", "=", user.id), ("mfo_shift_date", "=", self._today())]))),
                ("Асуудалтай ажил", self._format_number(self._count("mfo.issue.report", [("task_id.mfo_inspector_employee_id.user_id", "=", user.id), ("state", "!=", "resolved")]))),
                ("Шалгагдсан", self._format_number(self._count("project.task", [("mfo_inspector_employee_id.user_id", "=", user.id), ("mfo_state", "=", "verified")]))),
                ("Саатал", self._format_number(self._count("project.task", [("mfo_inspector_employee_id.user_id", "=", user.id), ("mfo_shift_date", "<", self._today()), ("mfo_state", "!=", "verified")]))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Чанарын хяналт",
            [
                ("Шалгах ажил", self._count("project.task", [("mfo_inspector_employee_id.user_id", "=", user.id), ("mfo_state", "=", "submitted")]), "warn"),
                ("Баталгаажсан", self._count("project.task", [("mfo_inspector_employee_id.user_id", "=", user.id), ("mfo_state", "=", "verified")]), "ok"),
                ("Асуудал", self._count("mfo.issue.report", [("task_id.mfo_inspector_employee_id.user_id", "=", user.id), ("state", "!=", "resolved")]), "danger"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Тайлан ба зураг",
            [
                ("Зурагтай ажил", self._count("mfo.proof.image", [("task_id.mfo_inspector_employee_id.user_id", "=", user.id)]), "ok"),
                ("Буцаах тэмдэглэл", self._count("mfo.issue.report", [("task_id.mfo_inspector_employee_id.user_id", "=", user.id)]), "warn"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Саатсан шалгалт", self._count("project.task", [("mfo_inspector_employee_id.user_id", "=", user.id), ("mfo_shift_date", "<", self._today()), ("mfo_state", "!=", "verified")]), "danger"),
            ],
        )
        return payload

    def _payload_system_admin(self, user):
        payload = self._empty_payload(
            "Системийн админы орон зай",
            "Бүх тохиргоо, role management, access rights, sync log, integration settings-ийн төв самбар.",
        )
        payload = self._set_kpis(
            payload,
            [
                ("Role profile", self._format_number(self._count("ops.access.profile", [("code", "ilike", "municipal_role_ui.")]))),
                ("Хэрэглэгч", self._format_number(self._count("res.users", [("share", "=", False)]))),
                ("Sync log", self._format_number(self._count("mfo.sync.log", []))),
                ("Integration", self._format_number(self._count("mfo.sync.log", [("state", "=", "failed")]))),
                ("Access rights", self._format_number(self._count("ir.model.access", [("model_id.model", "=", "municipal.role.dashboard")]))),
                ("Dashboard record", self._format_number(self._count("municipal.role.dashboard", []))),
                ("Засварын урсгал", self._format_number(self._count("fleet.repair.request", []))),
                ("Худалдан авалт", self._format_number(self._count("mpw.procurement.request", []))),
            ],
        )
        payload["highlight_html"] = self._render_panel(
            "Системийн төлөв",
            [
                ("Амжилттай sync", self._count("mfo.sync.log", [("state", "=", "success")]), "ok"),
                ("Анхаарах sync", self._count("mfo.sync.log", [("state", "=", "warning")]), "warn"),
                ("Алдаатай sync", self._count("mfo.sync.log", [("state", "=", "failed")]), "danger"),
            ],
        )
        payload["performance_html"] = self._render_panel(
            "Эрхийн удирдлага",
            [
                ("Албан тушаалын profile", self._count("ops.access.profile", [("code", "ilike", "municipal_role_ui.")]), "ok"),
                ("Dashboard record", self._count("municipal.role.dashboard", []), "ok"),
                ("Идэвхгүй хэрэглэгч", self._count("res.users", [("share", "=", False), ("active", "=", False)]), "warn"),
            ],
        )
        payload["alert_html"] = self._render_panel(
            "Анхаарах зүйл",
            [
                ("Алдаатай integration", self._count("mfo.sync.log", [("state", "=", "failed")]), "danger"),
                ("Profile оноогоогүй хэрэглэгч", self._count("res.users", [("share", "=", False), ("ops_access_profile_id", "=", False)]), "warn"),
            ],
        )
        return payload

    def _make_action(self, name, res_model, domain=None, context=None, view_mode="list,form"):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": res_model,
            "view_mode": view_mode,
            "domain": domain or [],
            "context": context or {},
            "target": "current",
        }

    def _display_notification(self, title, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "sticky": False,
                "type": "warning",
            },
        }

    def action_open_projects(self):
        self.ensure_one()
        return self._make_action("Төслүүд", "project.project", self._project_scope_domain(self.role_code, self.user_id), view_mode="kanban,list,form,activity")

    def action_open_today_tasks(self):
        self.ensure_one()
        return self._make_action("Өнөөдрийн ажил", "project.task", self._today_task_domain(self.role_code, self.user_id), view_mode="list,kanban,form,calendar")

    def action_open_overdue_tasks(self):
        self.ensure_one()
        return self._make_action("Хоцорсон ажил", "project.task", self._overdue_task_domain(self.role_code, self.user_id), view_mode="list,kanban,form")

    def action_open_review_tasks(self):
        self.ensure_one()
        return self._make_action("Шалгах ажил", "project.task", self._review_task_domain(self.role_code, self.user_id), view_mode="list,kanban,form")

    def action_open_task_reports(self):
        self.ensure_one()
        return self._make_action("Тайлан", "ops.task.report", self._report_scope_domain(self.role_code, self.user_id), view_mode="list,form")

    def action_open_procurements(self):
        self.ensure_one()
        return self._make_action("Худалдан авалт", "mpw.procurement.request", self._procurement_scope_domain(self.role_code, self.user_id), view_mode="list,kanban,form,graph,pivot")

    def action_open_procurements_pending(self):
        self.ensure_one()
        return self._make_action(
            "Батлах урсгалтай авалт",
            "mpw.procurement.request",
            self._procurement_scope_domain(self.role_code, self.user_id) + [("state", "in", ["director_pending", "finance_review", "order_preparing", "contract_preparing"])],
            view_mode="list,kanban,form",
        )

    def action_open_procurements_over_threshold(self):
        self.ensure_one()
        return self._make_action(
            "1 саяас дээш хүсэлт",
            "mpw.procurement.request",
            self._procurement_scope_domain(self.role_code, self.user_id) + [("is_over_threshold", "=", True)],
            view_mode="list,kanban,form",
        )

    def action_open_employees(self):
        self.ensure_one()
        return self._make_action("Ажилтнууд", "hr.employee", view_mode="list,form,kanban")

    def action_open_leave_requests(self):
        self.ensure_one()
        if not self._get_model("hr.leave"):
            return self._display_notification("Чөлөөний модель олдсонгүй", "HR Holidays модуль суусан үед энэ товч бодитоор ажиллана.")
        return self._make_action("Чөлөө / өвчтэй хүсэлт", "hr.leave", [("state", "in", ["confirm", "validate1", "validate"])], view_mode="list,form,calendar")

    def action_open_disciplinary_actions(self):
        self.ensure_one()
        return self._make_action("Сахилгын бүртгэл", "hr.disciplinary.action", view_mode="list,form,graph,pivot")

    def action_open_transfers(self):
        self.ensure_one()
        return self._make_action("Шилжилт хөдөлгөөн", "hr.employee.transfer", view_mode="list,form,graph,pivot")

    def action_open_clearance_requests(self):
        self.ensure_one()
        return self._make_action("Тойрох хуудас", "hr.employee.clearance", view_mode="list,form")

    def action_open_repair_requests(self):
        self.ensure_one()
        return self._make_action("Засварын хүсэлт", "fleet.repair.request", self._repair_scope_domain(self.role_code, self.user_id), view_mode="list,form")

    def action_open_vehicles(self):
        self.ensure_one()
        return self._make_action("Машинууд", "fleet.vehicle", [("mfo_active_for_ops", "=", True)], view_mode="list,kanban,form")

    def action_open_my_routes(self):
        self.ensure_one()
        return self._make_action("Маршрут", "project.task", self._task_scope_domain(self.role_code, self.user_id) + [("mfo_route_id", "!=", False)], view_mode="list,kanban,form")

    def action_open_quality_reports(self):
        self.ensure_one()
        return self._make_action("Чанарын тайлан", "mfo.issue.report", view_mode="list,form,kanban")

    def action_open_sync_logs(self):
        self.ensure_one()
        return self._make_action("Sync log", "mfo.sync.log", view_mode="list,form")

    def action_open_access_profiles(self):
        self.ensure_one()
        xmlid = "ops_people_registry.action_ops_access_profile"
        if self.env.ref(xmlid, raise_if_not_found=False):
            return self.env.ref(xmlid).read()[0]
        return self._make_action("Эрхийн профайл", "ops.access.profile", [("code", "ilike", "municipal_role_ui.")], view_mode="list,form")

    def action_open_users(self):
        self.ensure_one()
        return self._make_action("Хэрэглэгчид", "res.users", [("share", "=", False)], view_mode="list,form")
