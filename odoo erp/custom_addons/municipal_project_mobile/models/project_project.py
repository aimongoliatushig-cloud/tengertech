from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


PROJECT_APPROVAL_SELECTION = [
    ("draft", "Батлаагүй"),
    ("approved", "Баталсан"),
]


class ProjectProject(models.Model):
    _inherit = "project.project"

    mpm_general_manager_id = fields.Many2one(
        "res.users",
        string="Ерөнхий менежер",
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
    )
    mpm_project_manager_id = fields.Many2one(
        "res.users",
        string="Төслийн менежер",
        tracking=True,
        index=True,
    )
    mpm_team_leader_id = fields.Many2one(
        "res.users",
        string="Багийн ахлагч",
        tracking=True,
        index=True,
    )
    mpm_approval_state = fields.Selection(
        selection=PROJECT_APPROVAL_SELECTION,
        string="Баталгаажуулалт",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    mpm_task_count = fields.Integer(
        string="Нийт ажил",
        compute="_compute_mpm_metrics",
    )
    mpm_delayed_task_count = fields.Integer(
        string="Хоцролттой ажил",
        compute="_compute_mpm_metrics",
    )
    mpm_pending_report_count = fields.Integer(
        string="Шалгах тайлан",
        compute="_compute_mpm_metrics",
    )
    mpm_progress_percent = fields.Float(
        string="Ерөнхий явц",
        compute="_compute_mpm_metrics",
    )
    mpm_summary_note = fields.Char(
        string="Товч тайлбар",
        compute="_compute_mpm_summary_note",
    )
    mpm_can_approve = fields.Boolean(compute="_compute_mpm_action_flags")
    mpm_can_return_to_draft = fields.Boolean(compute="_compute_mpm_action_flags")

    @api.depends("task_ids.date_deadline", "task_ids.progress_percent", "task_ids.report_status", "task_ids.mpm_execution_state")
    def _compute_mpm_metrics(self):
        today = fields.Date.context_today(self)
        for project in self:
            tasks = project.task_ids
            project.mpm_task_count = len(tasks)
            project.mpm_delayed_task_count = len(
                tasks.filtered(
                    lambda task: task.date_deadline
                    and task.date_deadline < today
                    and task.mpm_execution_state != "done"
                )
            )
            project.mpm_pending_report_count = len(
                tasks.filtered(lambda task: task.report_status == "submitted")
            )
            project.mpm_progress_percent = (
                sum(tasks.mapped("progress_percent")) / len(tasks)
                if tasks
                else 0.0
            )

    @api.depends("mpm_task_count", "mpm_delayed_task_count", "mpm_pending_report_count", "mpm_approval_state")
    def _compute_mpm_summary_note(self):
        for project in self:
            if project.mpm_approval_state == "draft":
                project.mpm_summary_note = _("Энэ төсөл одоогоор батлагдаагүй байна.")
            elif project.mpm_delayed_task_count:
                project.mpm_summary_note = _(
                    "%(count)s хоцролттой ажилтай, яаралтай хяналт шаардлагатай."
                ) % {"count": project.mpm_delayed_task_count}
            elif project.mpm_pending_report_count:
                project.mpm_summary_note = _(
                    "%(count)s тайлан шалгалт хүлээж байна."
                ) % {"count": project.mpm_pending_report_count}
            elif project.mpm_task_count:
                project.mpm_summary_note = _("Нийт %(count)s ажил явагдаж байна.") % {
                    "count": project.mpm_task_count
                }
            else:
                project.mpm_summary_note = _("Одоогоор ажил үүсээгүй байна.")

    @api.depends("mpm_approval_state")
    def _compute_mpm_action_flags(self):
        is_general_manager = self.env.user.has_group(
            "municipal_project_mobile.group_general_manager"
        )
        for project in self:
            project.mpm_can_approve = bool(
                is_general_manager and project.mpm_approval_state != "approved"
            )
            project.mpm_can_return_to_draft = bool(
                is_general_manager and project.mpm_approval_state == "approved"
            )

    @api.constrains("mpm_general_manager_id", "mpm_project_manager_id", "mpm_team_leader_id")
    def _check_mpm_assignment_duplicates(self):
        for project in self:
            users = [
                user.id
                for user in [
                    project.mpm_general_manager_id,
                    project.mpm_project_manager_id,
                    project.mpm_team_leader_id,
                ]
                if user
            ]
            if len(users) != len(set(users)):
                raise ValidationError(
                    _("Ерөнхий менежер, төслийн менежер, багийн ахлагч давхардахгүй байна.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("mpm_project_manager_id") and not vals.get("user_id"):
                vals["user_id"] = vals["mpm_project_manager_id"]
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("mpm_project_manager_id"):
            vals["user_id"] = vals["mpm_project_manager_id"]
        return super().write(vals)

    def action_mpm_approve_project(self):
        self.ensure_one()
        if not self.env.user.has_group("municipal_project_mobile.group_general_manager"):
            raise UserError(_("Зөвхөн ерөнхий менежер төслийг батална."))
        if not self.mpm_project_manager_id:
            raise UserError(_("Төсөл батлахаас өмнө төслийн менежер онооно уу."))
        self.mpm_approval_state = "approved"
        self.message_post(body=_("Төслийг ерөнхий менежер баталлаа."))
        return True

    def action_mpm_return_to_draft(self):
        self.ensure_one()
        if not self.env.user.has_group("municipal_project_mobile.group_general_manager"):
            raise UserError(_("Зөвхөн ерөнхий менежер төслийг дахин батлаагүй болгоно."))
        self.mpm_approval_state = "draft"
        self.message_post(body=_("Төслийг дахин батлаагүй төлөвт орууллаа."))
        return True

    def action_mpm_open_project_tasks(self):
        self.ensure_one()
        action = self.env.ref("municipal_project_mobile.action_mpm_task_mobile").read()[0]
        action["domain"] = [("project_id", "=", self.id)]
        action["context"] = {
            "default_project_id": self.id,
            "search_default_project_id": self.id,
        }
        return action
