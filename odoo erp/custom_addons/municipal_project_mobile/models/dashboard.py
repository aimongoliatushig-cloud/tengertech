from odoo import _, api, fields, models
from odoo.fields import Domain


ROLE_SELECTION = [
    ("general_manager", "Ерөнхий менежер"),
    ("project_manager", "Төслийн менежер"),
    ("team_leader", "Багийн ахлагч"),
    ("worker", "Ажилтан"),
]


class MunicipalProjectDashboard(models.TransientModel):
    _name = "municipal.project.dashboard"
    _description = "Мобайл хяналтын самбар"

    dashboard_date = fields.Date(
        string="Огноо",
        default=fields.Date.context_today,
        required=True,
    )
    role_code = fields.Selection(selection=ROLE_SELECTION, string="Үүрэг", compute="_compute_dashboard")
    role_label = fields.Char(string="Үүргийн нэр", compute="_compute_dashboard")
    summary_text = fields.Text(string="Товч тайлбар", compute="_compute_dashboard")
    total_projects = fields.Integer(string="Нийт төсөл", compute="_compute_dashboard")
    delayed_projects = fields.Integer(string="Хоцролттой төсөл", compute="_compute_dashboard")
    pending_approvals = fields.Integer(string="Шалгах тайлан", compute="_compute_dashboard")
    my_projects = fields.Integer(string="Миний төсөл", compute="_compute_dashboard")
    attention_tasks = fields.Integer(string="Анхаарах ажил", compute="_compute_dashboard")
    missing_reports = fields.Integer(string="Дутуу тайлан", compute="_compute_dashboard")
    today_tasks = fields.Integer(string="Өнөөдрийн ажил", compute="_compute_dashboard")
    monthly_tasks = fields.Integer(string="Сарын хуваарь", compute="_compute_dashboard")
    pending_reports = fields.Integer(string="Илгээх тайлан", compute="_compute_dashboard")
    today_task_ids = fields.Many2many(
        "project.task",
        string="Өнөөдрийн ажлын мөрүүд",
        compute="_compute_dashboard",
    )
    attention_task_ids = fields.Many2many(
        "project.task",
        string="Анхаарах ажлын мөрүүд",
        compute="_compute_dashboard",
    )
    review_task_ids = fields.Many2many(
        "project.task",
        string="Шийдвэр хүлээж буй тайлан",
        compute="_compute_dashboard",
    )

    def _get_role_code(self):
        user = self.env.user
        if user.has_group("municipal_project_mobile.group_general_manager"):
            return "general_manager"
        if user.has_group("municipal_project_mobile.group_project_manager"):
            return "project_manager"
        if user.has_group("municipal_project_mobile.group_team_leader"):
            return "team_leader"
        return "worker"

    def _get_project_domain(self, role_code):
        user = self.env.user
        if role_code == "general_manager":
            return []
        if role_code == "project_manager":
            return [("mpm_project_manager_id", "=", user.id)]
        if role_code == "team_leader":
            return [("mpm_team_leader_id", "=", user.id)]
        return [("task_ids.mpm_worker_ids", "in", [user.id])]

    def _get_task_domain(self, role_code):
        user = self.env.user
        if role_code == "general_manager":
            return []
        if role_code == "project_manager":
            return [("project_id.mpm_project_manager_id", "=", user.id)]
        if role_code == "team_leader":
            return [("mpm_team_leader_id", "=", user.id)]
        return [("mpm_worker_ids", "in", [user.id])]

    @api.depends("dashboard_date")
    def _compute_dashboard(self):
        Project = self.env["project.project"]
        Task = self.env["project.task"]
        role_label_map = dict(ROLE_SELECTION)
        current_user = self.env.user

        for dashboard in self:
            role_code = dashboard._get_role_code()
            project_domain = dashboard._get_project_domain(role_code)
            task_domain = dashboard._get_task_domain(role_code)
            date_value = dashboard.dashboard_date or fields.Date.context_today(self)
            month_start = date_value.replace(day=1)

            delayed_task_domain = [
                ("date_deadline", "<", date_value),
                ("mpm_execution_state", "!=", "done"),
            ]
            today_task_domain = [("date_deadline", "=", date_value)]
            monthly_task_domain = [
                ("date_deadline", ">=", month_start),
                ("date_deadline", "<=", date_value),
            ]
            review_task_domain = [("report_status", "=", "submitted")]
            attention_task_domain = [
                "|",
                ("mpm_execution_state", "=", "blocked"),
                ("date_deadline", "<", date_value),
            ]
            missing_report_domain = [
                ("mpm_execution_state", "=", "done"),
                ("report_status", "in", ["draft", "rejected"]),
            ]
            pending_report_domain = [
                ("report_status", "in", ["draft", "rejected"]),
                ("mpm_team_leader_id", "=", current_user.id),
            ]

            projects = Project.search(project_domain)
            delayed_tasks = Task.search(Domain.AND([task_domain, delayed_task_domain]))
            review_tasks = Task.search(
                Domain.AND([task_domain, review_task_domain]),
                limit=5,
                order="write_date desc",
            )
            today_tasks = Task.search(
                Domain.AND([task_domain, today_task_domain]),
                limit=5,
                order="priority desc, date_deadline asc, id desc",
            )
            attention_tasks = Task.search(
                Domain.AND([task_domain, attention_task_domain]),
                limit=5,
                order="priority desc, date_deadline asc, id desc",
            )

            dashboard.role_code = role_code
            dashboard.role_label = role_label_map[role_code]
            dashboard.total_projects = len(projects)
            dashboard.delayed_projects = len(delayed_tasks.mapped("project_id"))
            dashboard.pending_approvals = Task.search_count(
                Domain.AND([task_domain, review_task_domain])
            )
            dashboard.my_projects = Project.search_count(project_domain)
            dashboard.attention_tasks = Task.search_count(
                Domain.AND([task_domain, attention_task_domain])
            )
            dashboard.missing_reports = Task.search_count(
                Domain.AND([task_domain, missing_report_domain])
            )
            dashboard.today_tasks = Task.search_count(
                Domain.AND([task_domain, today_task_domain])
            )
            dashboard.monthly_tasks = Task.search_count(
                Domain.AND([task_domain, monthly_task_domain])
            )
            dashboard.pending_reports = Task.search_count(
                Domain.AND([task_domain, pending_report_domain])
            )
            dashboard.today_task_ids = today_tasks
            dashboard.attention_task_ids = attention_tasks
            dashboard.review_task_ids = review_tasks

            if role_code == "general_manager":
                dashboard.summary_text = _(
                    "Нийт төсөл, хоцролт, батлал хүлээж буй тайланг эндээс хурдан харна."
                )
            elif role_code == "project_manager":
                dashboard.summary_text = _(
                    "Өөрийн төсөл, хоцролттой ажил, дутуу тайланг төвлөрүүлж харна."
                )
            elif role_code == "team_leader":
                dashboard.summary_text = _(
                    "Өнөөдрийн ажил, зурагтай тайлан, саад тэмдэглэлийг нэг урсгалаар оруулна."
                )
            else:
                dashboard.summary_text = _(
                    "Өнөөдөр болон сарын хуваариа зөвхөн унших горимоор харуулна."
                )

    @api.model
    def action_open_dashboard(self):
        dashboard = self.create({})
        view = self.env.ref("municipal_project_mobile.view_mpm_dashboard_form")
        return {
            "name": _("Хяналтын самбар"),
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": dashboard.id,
            "view_mode": "form",
            "views": [(view.id, "form")],
            "target": "current",
        }

    def action_refresh_dashboard(self):
        return self.action_open_dashboard()

    def _action_open_tasks(self, domain=None, name=None, context=None, view_mode="kanban,list,form,calendar"):
        self.ensure_one()
        action = self.env.ref("municipal_project_mobile.action_mpm_task_mobile").read()[0]
        action["name"] = name or action["name"]
        action["domain"] = Domain.AND([self._get_task_domain(self.role_code), domain or []])
        action["view_mode"] = view_mode
        if context:
            action["context"] = context
        return action

    def _action_open_projects(self, domain=None, name=None, context=None):
        self.ensure_one()
        action = self.env.ref("municipal_project_mobile.action_mpm_project_mobile").read()[0]
        action["name"] = name or action["name"]
        action["domain"] = Domain.AND([self._get_project_domain(self.role_code), domain or []])
        if context:
            action["context"] = context
        return action

    def action_open_new_project(self):
        self.ensure_one()
        return {
            "name": _("Шинэ төсөл"),
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "view_mode": "form",
            "target": "current",
            "context": {"default_mpm_general_manager_id": self.env.user.id},
        }

    def action_open_new_task(self):
        self.ensure_one()
        return {
            "name": _("Шинэ ажил"),
            "type": "ir.actions.act_window",
            "res_model": "project.task",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_mpm_team_leader_id": self.env.user.id
                if self.role_code == "team_leader"
                else False,
            },
        }

    def action_open_all_projects(self):
        self.ensure_one()
        return self._action_open_projects(name=_("Бүх төсөл"))

    def action_open_my_projects(self):
        self.ensure_one()
        return self._action_open_projects(name=_("Миний төсөл"))

    def action_open_delayed_projects(self):
        self.ensure_one()
        date_value = self.dashboard_date or fields.Date.context_today(self)
        tasks = self.env["project.task"].search(
            Domain.AND(
                [
                    self._get_task_domain(self.role_code),
                    [("date_deadline", "<", date_value), ("mpm_execution_state", "!=", "done")],
                ]
            )
        )
        return self._action_open_projects(
            domain=[("id", "in", tasks.mapped("project_id").ids)],
            name=_("Хоцролттой төсөл"),
        )

    def action_open_pending_approvals(self):
        self.ensure_one()
        return self._action_open_tasks(
            domain=[("report_status", "=", "submitted")],
            name=_("Шийдвэр хүлээж буй тайлан"),
        )

    def action_open_attention_tasks(self):
        self.ensure_one()
        date_value = self.dashboard_date or fields.Date.context_today(self)
        return self._action_open_tasks(
            domain=["|", ("mpm_execution_state", "=", "blocked"), ("date_deadline", "<", date_value)],
            name=_("Анхаарах ажил"),
        )

    def action_open_missing_reports(self):
        self.ensure_one()
        return self._action_open_tasks(
            domain=[("mpm_execution_state", "=", "done"), ("report_status", "in", ["draft", "rejected"])],
            name=_("Дутуу тайлан"),
        )

    def action_open_today_tasks(self):
        self.ensure_one()
        date_value = self.dashboard_date or fields.Date.context_today(self)
        return self._action_open_tasks(
            domain=[("date_deadline", "=", date_value)],
            name=_("Өнөөдрийн ажил"),
        )

    def action_open_monthly_tasks(self):
        self.ensure_one()
        date_value = self.dashboard_date or fields.Date.context_today(self)
        month_start = date_value.replace(day=1)
        return self._action_open_tasks(
            domain=[("date_deadline", ">=", month_start), ("date_deadline", "<=", date_value)],
            name=_("Сарын хуваарь"),
            view_mode="calendar,list,kanban,form",
        )

    def action_open_report_tasks(self):
        self.ensure_one()
        return self._action_open_tasks(
            domain=[("report_status", "in", ["draft", "rejected"])],
            name=_("Тайлан оруулах ажил"),
        )
