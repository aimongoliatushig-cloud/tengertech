import html
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare


OPS_STAGE_NAME_ALIASES = {
    "todo": ["Хийгдэх ажил", "hiigdeh ajil", "daalgavar", "task"],
    "progress": [
        "Явагдаж буй ажил",
        "yovagdaj bui ajil",
        "yavagdaj bui ajil",
        "yavagdajh bui",
        "hiihdej baina",
    ],
    "review": [
        "Шалгагдаж буй ажил",
        "shalgagdaj bui ajil",
        "shlagah",
        "shalgah",
        "shalgalt",
    ],
    "done": ["Дууссан ажил", "duussan ajil", "duussan"],
}
OPS_LOCKED_STAGE_BUCKETS = {"review", "done"}
OPS_LOCKED_STATES = {"02_changes_requested", "1_done"}


class ProjectTask(models.Model):
    _inherit = "project.task"

    ops_measurement_unit = fields.Char(
        string="Measurement Unit",
        help="For example: мод, км2, м3, ширхэг.",
    )
    ops_planned_quantity = fields.Float(
        string="Planned Quantity",
        digits=(16, 2),
    )
    ops_completed_quantity = fields.Float(
        string="Completed Quantity",
        compute="_compute_ops_quantity_progress",
        store=True,
        digits=(16, 2),
    )
    ops_remaining_quantity = fields.Float(
        string="Remaining Quantity",
        compute="_compute_ops_quantity_progress",
        store=True,
        digits=(16, 2),
    )
    ops_progress_percent = fields.Float(
        string="Progress",
        compute="_compute_ops_quantity_progress",
        store=True,
        digits=(16, 2),
    )
    ops_report_ids = fields.One2many(
        "ops.task.report",
        "task_id",
        string="Field Reports",
    )
    ops_can_submit_for_review = fields.Boolean(
        compute="_compute_ops_workflow_actions",
    )
    ops_can_mark_done = fields.Boolean(
        compute="_compute_ops_workflow_actions",
    )
    ops_can_return_for_changes = fields.Boolean(
        compute="_compute_ops_workflow_actions",
    )
    ops_reports_locked = fields.Boolean(
        compute="_compute_ops_workflow_actions",
    )

    @api.depends("ops_planned_quantity", "ops_report_ids.reported_quantity")
    def _compute_ops_quantity_progress(self):
        for task in self:
            completed = sum(task.ops_report_ids.mapped("reported_quantity"))
            planned = task.ops_planned_quantity or 0.0
            task.ops_completed_quantity = completed
            task.ops_remaining_quantity = planned - completed
            task.ops_progress_percent = (completed / planned * 100.0) if planned else 0.0

    @staticmethod
    def _ops_normalize_stage_name(name):
        return (name or "").strip().lower()

    def _ops_get_stage_bucket(self):
        self.ensure_one()
        current_name = self._ops_normalize_stage_name(self.stage_id.name)
        for bucket, aliases in OPS_STAGE_NAME_ALIASES.items():
            if current_name in {self._ops_normalize_stage_name(alias) for alias in aliases}:
                return bucket
        return False

    def _ops_get_stage_bucket_from_name(self, stage_name):
        normalized_name = self._ops_normalize_stage_name(stage_name)
        for bucket, aliases in OPS_STAGE_NAME_ALIASES.items():
            if normalized_name in {self._ops_normalize_stage_name(alias) for alias in aliases}:
                return bucket
        return False

    def _ops_get_target_stage(self, bucket):
        self.ensure_one()
        aliases = {
            self._ops_normalize_stage_name(alias) for alias in OPS_STAGE_NAME_ALIASES.get(bucket, [])
        }
        stages = self.project_id.type_ids or self.stage_id.project_ids.type_ids or self.env["project.task.type"]
        return stages.filtered(
            lambda stage: self._ops_normalize_stage_name(stage.name) in aliases
        )[:1]

    def _ops_is_current_user_team_leader(self):
        self.ensure_one()
        user = self.env.user
        if not user.has_group("ops_role_security.group_ops_team_leader"):
            return False
        return self.ops_team_leader_id == user or user in self.user_ids

    def _ops_is_current_user_general_manager(self):
        self.ensure_one()
        return self.env.user.has_group("ops_role_security.group_ops_general_manager")

    def _ops_is_current_user_system_admin(self):
        self.ensure_one()
        return self.env.su or self.env.user.has_group("ops_role_security.group_ops_system_admin")

    def _ops_is_allowed_workflow_transition(
        self, current_bucket, current_state, target_bucket, target_state
    ):
        self.ensure_one()
        transition = self.env.context.get("ops_workflow_transition")
        if transition == "submit_for_review":
            return (
                current_bucket not in OPS_LOCKED_STAGE_BUCKETS
                and current_state not in OPS_LOCKED_STATES
                and target_bucket == "review"
                and target_state == "02_changes_requested"
            )
        if transition == "mark_done":
            return (
                current_bucket == "review"
                and current_state == "02_changes_requested"
                and target_bucket == "done"
                and target_state == "1_done"
            )
        if transition == "return_to_progress":
            return (
                current_bucket == "review"
                and current_state == "02_changes_requested"
                and target_bucket == "progress"
                and target_state == "01_in_progress"
            )
        return False

    def _ops_check_workflow_write_lock(self, vals):
        if not {"stage_id", "state"} & set(vals):
            return

        stage_model = self.env["project.task.type"]
        for task in self:
            if task._ops_is_current_user_system_admin():
                continue

            current_bucket = task._ops_get_stage_bucket()
            current_state = task.state
            target_stage = (
                stage_model.browse(vals["stage_id"]).exists()
                if "stage_id" in vals
                else task.stage_id
            )
            target_bucket = task._ops_get_stage_bucket_from_name(target_stage.name if target_stage else "")
            target_state = vals.get("state", current_state)
            touches_locked_workflow = bool(
                current_bucket in OPS_LOCKED_STAGE_BUCKETS
                or current_state in OPS_LOCKED_STATES
                or target_bucket in OPS_LOCKED_STAGE_BUCKETS
                or target_state in OPS_LOCKED_STATES
            )

            if not touches_locked_workflow:
                continue

            if task._ops_is_allowed_workflow_transition(
                current_bucket, current_state, target_bucket, target_state
            ):
                continue

            raise AccessError(
                _(
                    "Энэ төлөвийн өөрчлөлтийг гараар хийхгүй. "
                    "`Шалгалтад илгээх` ба `Дуусгах` товчийг ашиглана уу."
                )
            )

    def _ops_validate_quantity_totals(self):
        for task in self:
            total_reported = sum(task.ops_report_ids.mapped("reported_quantity"))
            planned = task.ops_planned_quantity or 0.0

            if (
                float_compare(total_reported, 0.0, precision_digits=2) > 0
                and float_compare(planned, 0.0, precision_digits=2) <= 0
            ):
                raise ValidationError(
                    _(
                        "Гүйцэтгэсэн тоо хэмжээ оруулахын өмнө `Төлөвлөсөн хэмжээ`-г бөглөнө үү."
                    )
                )

            if (
                float_compare(planned, 0.0, precision_digits=2) > 0
                and float_compare(total_reported, planned, precision_digits=2) > 0
            ):
                raise ValidationError(
                    _(
                        "Нийт гүйцэтгэсэн хэмжээ нь төлөвлөсөн хэмжээнээс их байж болохгүй."
                    )
                )

    @api.depends(
        "ops_report_ids",
        "ops_team_leader_id",
        "user_ids",
        "stage_id",
        "state",
    )
    @api.depends_context("uid")
    def _compute_ops_workflow_actions(self):
        for task in self:
            stage_bucket = task._ops_get_stage_bucket()
            has_reports = bool(task.ops_report_ids)
            is_locked = bool(stage_bucket in OPS_LOCKED_STAGE_BUCKETS or task.state in OPS_LOCKED_STATES)
            task.ops_can_submit_for_review = bool(
                has_reports
                and task._ops_is_current_user_team_leader()
                and stage_bucket not in {"review", "done"}
            )
            is_review_for_general_manager = bool(
                task._ops_is_current_user_general_manager() and stage_bucket == "review"
            )
            task.ops_can_mark_done = is_review_for_general_manager
            task.ops_can_return_for_changes = is_review_for_general_manager
            task.ops_reports_locked = bool(
                is_locked and not task._ops_is_current_user_system_admin()
            )

    def action_ops_submit_for_review(self):
        for task in self:
            if not task._ops_is_current_user_team_leader():
                raise AccessError(_("Зөвхөн энэ ажилд оноогдсон багийн ахлагч шалгалтад илгээх боломжтой."))
            if not task.ops_report_ids:
                raise UserError(_("Эхлээд энэ ажил дээр гүйцэтгэлийн тайлан оруулна уу."))

            review_stage = task._ops_get_target_stage("review")
            if not review_stage:
                raise UserError(_("`Шалгагдаж буй ажил` үе шат энэ төсөл дээр алга байна."))

            task.with_context(ops_workflow_transition="submit_for_review").write(
                {
                    "stage_id": review_stage.id,
                    "state": "02_changes_requested",
                }
            )
            task.message_post(body=_("Ажлыг багийн ахлагч шалгалтад илгээлээ."))
        return True

    def action_ops_mark_done(self):
        for task in self:
            if not task._ops_is_current_user_general_manager():
                raise AccessError(_("Зөвхөн ерөнхий менежер шалгасны дараа энэ ажлыг дуусгах боломжтой."))

            done_stage = task._ops_get_target_stage("done")
            if not done_stage:
                raise UserError(_("`Дууссан ажил` үе шат энэ төсөл дээр алга байна."))

            task.with_context(ops_workflow_transition="mark_done").write(
                {
                    "stage_id": done_stage.id,
                    "state": "1_done",
                }
            )
            task.message_post(body=_("Ажлыг ерөнхий менежер шалгаад дуусгалаа."))
        return True

    def action_ops_open_return_wizard(self):
        self.ensure_one()
        if not self._ops_is_current_user_general_manager():
            raise AccessError(_("Зөвхөн ерөнхий менежер шалгагдаж буй ажлыг буцаах боломжтой."))
        if self._ops_get_stage_bucket() != "review":
            raise UserError(_("Зөвхөн `Шалгагдаж буй ажил` үе шатанд байгаа ажлыг буцаана уу."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Засвар буцаах"),
            "res_model": "ops.task.return.wizard",
            "view_mode": "form",
            "view_id": self.env.ref("ops_field_reporting.view_ops_task_return_wizard_form").id,
            "target": "new",
            "context": {
                "default_task_id": self.id,
            },
        }

    @staticmethod
    def _extract_ops_quantity_defaults(description):
        if not description:
            return {}

        plain = re.sub(r"<[^>]+>", "\n", html.unescape(description))
        plain = re.sub(r"[ \t]+", " ", plain)
        lines = [line.strip() for line in plain.splitlines() if line.strip()]

        values_by_label = {}
        pending_label = None
        for line in lines:
            if ":" in line:
                label, remainder = line.split(":", 1)
                label = label.strip()
                remainder = remainder.strip()
                if remainder:
                    values_by_label[label] = remainder
                    pending_label = None
                else:
                    pending_label = label
                continue
            if pending_label and pending_label not in values_by_label:
                values_by_label[pending_label] = line
                pending_label = None

        values = {}
        total_trees = values_by_label.get("Нийт мод")
        total_quantity = values_by_label.get("Нийт хэмжээ")
        unit = values_by_label.get("Хэмжих нэгж")

        if total_trees:
            values["ops_planned_quantity"] = float(total_trees.replace(",", "."))
            values["ops_measurement_unit"] = "mod"
            return values

        if total_quantity:
            values["ops_planned_quantity"] = float(total_quantity.replace(",", "."))
        if unit:
            values["ops_measurement_unit"] = unit.strip()
        return values

    @classmethod
    def _apply_ops_quantity_defaults(cls, vals):
        if "description" not in vals:
            return vals
        if vals.get("ops_measurement_unit") not in (None, False, "") or vals.get("ops_planned_quantity") not in (None, False):
            return vals
        parsed = cls._extract_ops_quantity_defaults(vals.get("description"))
        if not parsed:
            return vals
        merged = dict(vals)
        merged.update(parsed)
        return merged

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._apply_ops_quantity_defaults(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        vals = self._apply_ops_quantity_defaults(vals)
        self._ops_check_workflow_write_lock(vals)
        result = super().write(vals)
        self._ops_validate_quantity_totals()
        return result

    @api.constrains("ops_planned_quantity")
    def _check_ops_planned_quantity(self):
        for task in self:
            if task.ops_planned_quantity < 0:
                raise ValidationError(_("Planned quantity cannot be negative."))
        self._ops_validate_quantity_totals()


class OpsTaskReport(models.Model):
    _name = "ops.task.report"
    _description = "Task Field Report"
    _order = "report_datetime desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Report",
        compute="_compute_name",
        store=True,
    )
    task_id = fields.Many2one(
        "project.task",
        string="Task",
        required=True,
        ondelete="cascade",
        index=True,
    )
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        related="task_id.project_id",
        store=True,
        readonly=True,
    )
    reporter_id = fields.Many2one(
        "res.users",
        string="Submitted By",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        index=True,
    )
    report_datetime = fields.Datetime(
        string="Submitted On",
        required=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    report_text = fields.Text(
        string="Report Text",
        required=True,
    )
    task_measurement_unit = fields.Char(
        string="Measurement Unit",
        related="task_id.ops_measurement_unit",
        readonly=True,
    )
    task_planned_quantity = fields.Float(
        string="Planned Quantity",
        related="task_id.ops_planned_quantity",
        readonly=True,
        digits=(16, 2),
    )
    reported_quantity = fields.Float(
        string="Completed This Report",
        digits=(16, 2),
    )
    image_attachment_ids = fields.Many2many(
        "ir.attachment",
        "ops_task_report_image_rel",
        "report_id",
        "attachment_id",
        string="Images",
        bypass_search_access=True,
    )
    audio_attachment_ids = fields.Many2many(
        "ir.attachment",
        "ops_task_report_audio_rel",
        "report_id",
        "attachment_id",
        string="Audio Files",
        bypass_search_access=True,
    )
    image_count = fields.Integer(
        string="Image Count",
        compute="_compute_media_counts",
    )
    audio_count = fields.Integer(
        string="Audio Count",
        compute="_compute_media_counts",
    )
    report_summary = fields.Char(
        string="Summary",
        compute="_compute_report_summary",
    )

    @api.model
    def _ops_check_report_lock(self, tasks, operation):
        if self.env.su or self.env.user.has_group("ops_role_security.group_ops_system_admin"):
            return

        locked_tasks = tasks.filtered(
            lambda task: task._ops_get_stage_bucket() in OPS_LOCKED_STAGE_BUCKETS
            or task.state in OPS_LOCKED_STATES
        )
        if locked_tasks:
            raise AccessError(
                _(
                    "Энэ ажил шалгагдаж буй эсвэл дууссан төлөвт орсон тул тайланг өөрчлөх боломжгүй."
                )
            )

    @api.depends("task_id", "report_datetime")
    def _compute_name(self):
        for report in self:
            if not report.task_id:
                report.name = _("New Report")
                continue
            if report.report_datetime:
                timestamp = fields.Datetime.to_string(report.report_datetime)
                report.name = f"{report.task_id.display_name} - {timestamp}"
            else:
                report.name = report.task_id.display_name

    @api.depends("image_attachment_ids", "audio_attachment_ids")
    def _compute_media_counts(self):
        for report in self:
            report.image_count = len(report.image_attachment_ids)
            report.audio_count = len(report.audio_attachment_ids)

    @api.depends("report_text")
    def _compute_report_summary(self):
        for report in self:
            text = (report.report_text or "").strip()
            report.report_summary = text[:80] + ("..." if len(text) > 80 else "")

    @api.constrains("reported_quantity")
    def _check_reported_quantity(self):
        for report in self:
            if report.reported_quantity < 0:
                raise ValidationError(_("Completed quantity cannot be negative."))

    def _link_media_attachments(self):
        for report in self:
            attachments = report.image_attachment_ids | report.audio_attachment_ids
            if attachments:
                attachments.sudo().write(
                    {
                        "res_model": report._name,
                        "res_id": report.id,
                    }
                )

    @api.model_create_multi
    def create(self, vals_list):
        task_ids = [vals.get("task_id") for vals in vals_list if vals.get("task_id")]
        self._ops_check_report_lock(self.env["project.task"].browse(task_ids).exists(), "create")
        reports = super().create(vals_list)
        reports._ops_check_report_lock(reports.mapped("task_id"), "create")
        reports.mapped("task_id")._ops_validate_quantity_totals()
        reports._link_media_attachments()
        return reports

    def write(self, vals):
        tasks_to_check = self.mapped("task_id")
        if vals.get("task_id"):
            tasks_to_check |= self.env["project.task"].browse(vals["task_id"]).exists()
        self._ops_check_report_lock(tasks_to_check, "write")
        result = super().write(vals)
        if {"reported_quantity", "task_id"} & set(vals):
            self.mapped("task_id")._ops_validate_quantity_totals()
        if {"image_attachment_ids", "audio_attachment_ids", "task_id"} & set(vals):
            self._link_media_attachments()
        return result

    def unlink(self):
        self._ops_check_report_lock(self.mapped("task_id"), "unlink")
        return super().unlink()
