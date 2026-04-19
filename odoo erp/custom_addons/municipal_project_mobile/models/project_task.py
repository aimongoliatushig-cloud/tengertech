from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command


EXECUTION_STATE_SELECTION = [
    ("planned", "Төлөвлөсөн"),
    ("in_progress", "Ажиллаж байна"),
    ("done", "Дууссан"),
    ("blocked", "Саатсан"),
]

REPORT_STATUS_SELECTION = [
    ("draft", "Ноорог"),
    ("submitted", "Илгээсэн"),
    ("approved", "Баталсан"),
    ("rejected", "Буцаасан"),
]


class ProjectTask(models.Model):
    _inherit = "project.task"

    mpm_general_manager_id = fields.Many2one(
        "res.users",
        string="Ерөнхий менежер",
        related="project_id.mpm_general_manager_id",
        store=True,
        readonly=True,
    )
    mpm_project_manager_id = fields.Many2one(
        "res.users",
        string="Төслийн менежер",
        related="project_id.mpm_project_manager_id",
        store=True,
        readonly=True,
    )
    mpm_team_leader_id = fields.Many2one(
        "res.users",
        string="Багийн ахлагч",
        tracking=True,
        index=True,
    )
    mpm_worker_ids = fields.Many2many(
        "res.users",
        "mpm_task_worker_rel",
        "task_id",
        "user_id",
        string="Ажилтнууд",
        tracking=True,
    )
    mpm_execution_state = fields.Selection(
        selection=EXECUTION_STATE_SELECTION,
        string="Ажлын төлөв",
        default="planned",
        required=True,
        tracking=True,
        index=True,
    )
    report_status = fields.Selection(
        selection=REPORT_STATUS_SELECTION,
        string="Тайлангийн төлөв",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    progress_percent = fields.Integer(
        string="Гүйцэтгэл",
        default=0,
        tracking=True,
    )
    issue_note = fields.Text(string="Асуудлын тэмдэглэл")
    report_note = fields.Text(string="Тайлан")
    report_photo_ids = fields.One2many(
        "municipal.project.report.photo",
        "task_id",
        string="Тайлангийн зураг",
    )
    approved_by_pm = fields.Many2one(
        "res.users",
        string="Төслийн менежер баталсан",
        readonly=True,
        tracking=True,
    )
    approved_by_gm = fields.Many2one(
        "res.users",
        string="Ерөнхий менежер баталсан",
        readonly=True,
        tracking=True,
    )
    mpm_report_submitted_at = fields.Datetime(
        string="Тайлан илгээсэн цаг",
        readonly=True,
    )
    mpm_report_reviewed_at = fields.Datetime(
        string="Тайлан шийдсэн цаг",
        readonly=True,
    )
    mpm_worker_names = fields.Char(
        string="Ажилтны нэрс",
        compute="_compute_mpm_display_fields",
    )
    mpm_photo_count = fields.Integer(
        string="Зураг",
        compute="_compute_mpm_display_fields",
    )
    mpm_is_delayed = fields.Boolean(
        string="Хоцролт",
        compute="_compute_mpm_is_delayed",
    )
    mpm_can_start = fields.Boolean(compute="_compute_mpm_action_flags")
    mpm_can_mark_done = fields.Boolean(compute="_compute_mpm_action_flags")
    mpm_can_block = fields.Boolean(compute="_compute_mpm_action_flags")
    mpm_can_submit_report = fields.Boolean(compute="_compute_mpm_action_flags")
    mpm_can_pm_approve = fields.Boolean(compute="_compute_mpm_action_flags")
    mpm_can_pm_reject = fields.Boolean(compute="_compute_mpm_action_flags")
    mpm_can_gm_override = fields.Boolean(compute="_compute_mpm_action_flags")

    @api.depends("mpm_worker_ids.name", "report_photo_ids")
    def _compute_mpm_display_fields(self):
        for task in self:
            task.mpm_worker_names = ", ".join(task.mpm_worker_ids.mapped("name"))
            task.mpm_photo_count = len(task.report_photo_ids)

    @api.depends("date_deadline", "mpm_execution_state")
    def _compute_mpm_is_delayed(self):
        today = fields.Date.context_today(self)
        for task in self:
            task.mpm_is_delayed = bool(
                task.date_deadline
                and task.date_deadline < today
                and task.mpm_execution_state != "done"
            )

    @api.depends(
        "mpm_execution_state",
        "report_status",
        "mpm_team_leader_id",
        "mpm_worker_ids",
        "mpm_project_manager_id",
    )
    @api.depends_context("uid")
    def _compute_mpm_action_flags(self):
        user = self.env.user
        is_general_manager = user.has_group("municipal_project_mobile.group_general_manager")
        is_project_manager_group = user.has_group("municipal_project_mobile.group_project_manager")
        for task in self:
            is_project_manager = is_project_manager_group and task.mpm_project_manager_id == user
            is_team_leader = task.mpm_team_leader_id == user
            can_execute = is_general_manager or is_project_manager or is_team_leader
            task.mpm_can_start = can_execute and task.mpm_execution_state in {"planned", "blocked"}
            task.mpm_can_mark_done = can_execute and task.mpm_execution_state in {
                "planned",
                "in_progress",
                "blocked",
            }
            task.mpm_can_block = can_execute and task.mpm_execution_state in {"planned", "in_progress"}
            task.mpm_can_submit_report = can_execute and task.report_status in {"draft", "rejected"}
            task.mpm_can_pm_approve = is_project_manager and task.report_status == "submitted"
            task.mpm_can_pm_reject = is_project_manager and task.report_status == "submitted"
            task.mpm_can_gm_override = is_general_manager and task.report_status in {
                "submitted",
                "approved",
                "rejected",
            }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("project_id") and not vals.get("mpm_team_leader_id"):
                project = self.env["project.project"].browse(vals["project_id"])
                if project.mpm_team_leader_id:
                    vals["mpm_team_leader_id"] = project.mpm_team_leader_id.id
        tasks = super().create(vals_list)
        tasks._mpm_sync_user_ids()
        return tasks

    def write(self, vals):
        result = super().write(vals)
        if {"mpm_team_leader_id", "mpm_worker_ids", "project_id"}.intersection(vals):
            self._mpm_sync_user_ids()
        return result

    @api.constrains("progress_percent")
    def _check_mpm_progress_percent(self):
        for task in self:
            if task.progress_percent < 0 or task.progress_percent > 100:
                raise ValidationError(_("Гүйцэтгэл 0-100 хооронд байх ёстой."))

    def _mpm_sync_user_ids(self):
        for task in self:
            assigned_ids = []
            if task.mpm_project_manager_id:
                assigned_ids.append(task.mpm_project_manager_id.id)
            if task.mpm_team_leader_id:
                assigned_ids.append(task.mpm_team_leader_id.id)
            assigned_ids.extend(task.mpm_worker_ids.ids)
            task.user_ids = [Command.set(list(dict.fromkeys(assigned_ids)))]

    def _mpm_check_can_execute(self):
        user = self.env.user
        for task in self:
            if user.has_group("municipal_project_mobile.group_general_manager"):
                continue
            if task.mpm_project_manager_id == user:
                continue
            if task.mpm_team_leader_id == user:
                continue
            raise UserError(_("Энэ ажил дээр үйлдэл хийх эрх алга."))

    def _mpm_check_can_pm_review(self):
        user = self.env.user
        for task in self:
            if task.mpm_project_manager_id != user and not user.has_group(
                "municipal_project_mobile.group_general_manager"
            ):
                raise UserError(_("Зөвхөн төслийн менежер эсвэл ерөнхий менежер шийдвэрлэнэ."))

    def action_mpm_start_work(self):
        self._mpm_check_can_execute()
        for task in self:
            values = {"mpm_execution_state": "in_progress"}
            if task.progress_percent == 0:
                values["progress_percent"] = 10
            task.write(values)
        return True

    def action_mpm_mark_done(self):
        self._mpm_check_can_execute()
        self.write({"mpm_execution_state": "done", "progress_percent": 100})
        return True

    def action_mpm_mark_blocked(self):
        self._mpm_check_can_execute()
        self.write({"mpm_execution_state": "blocked"})
        return True

    def action_mpm_submit_report(self):
        self._mpm_check_can_execute()
        for task in self:
            if not task.report_note and not task.issue_note and not task.report_photo_ids:
                raise UserError(_("Тайлан илгээхийн өмнө тайлбар эсвэл зураг оруулна уу."))
            task.write(
                {
                    "report_status": "submitted",
                    "mpm_report_submitted_at": fields.Datetime.now(),
                    "approved_by_pm": False,
                    "approved_by_gm": False,
                }
            )
        return True

    def action_mpm_pm_approve_report(self):
        self._mpm_check_can_pm_review()
        self.write(
            {
                "report_status": "approved",
                "approved_by_pm": self.env.user.id,
                "approved_by_gm": False,
                "mpm_report_reviewed_at": fields.Datetime.now(),
            }
        )
        return True

    def action_mpm_pm_reject_report(self):
        self._mpm_check_can_pm_review()
        self.write(
            {
                "report_status": "rejected",
                "approved_by_pm": False,
                "approved_by_gm": False,
                "mpm_report_reviewed_at": fields.Datetime.now(),
            }
        )
        return True

    def action_mpm_gm_override_approve(self):
        if not self.env.user.has_group("municipal_project_mobile.group_general_manager"):
            raise UserError(_("Зөвхөн ерөнхий менежер эцсийн шийдвэр хийнэ."))
        self.write(
            {
                "report_status": "approved",
                "approved_by_gm": self.env.user.id,
                "mpm_report_reviewed_at": fields.Datetime.now(),
            }
        )
        return True

    def action_mpm_gm_override_reject(self):
        if not self.env.user.has_group("municipal_project_mobile.group_general_manager"):
            raise UserError(_("Зөвхөн ерөнхий менежер эцсийн шийдвэр хийнэ."))
        self.write(
            {
                "report_status": "rejected",
                "approved_by_gm": False,
                "mpm_report_reviewed_at": fields.Datetime.now(),
            }
        )
        return True
