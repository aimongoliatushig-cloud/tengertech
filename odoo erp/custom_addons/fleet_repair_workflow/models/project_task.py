from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


MAINTENANCE_CATEGORY_SELECTION = [
    ("repair", "Засвар"),
    ("service", "Үйлчилгээ"),
    ("inspection", "Шалгалт"),
    ("emergency", "Яаралтай"),
]

REPAIR_RESULT_SELECTION = [
    ("fixed", "Зассан"),
    ("temporary", "Түр арга хэмжээ"),
    ("waiting_parts", "Сэлбэг хүлээж байгаа"),
    ("not_fixed", "Засагдаагүй"),
]


class ProjectTask(models.Model):
    _inherit = "project.task"

    is_vehicle_repair_task = fields.Boolean(default=False, index=True)
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Машин",
        tracking=True,
        index=True,
    )
    repair_request_id = fields.Many2one(
        "fleet.repair.request",
        string="Засварын хүсэлт",
        tracking=True,
        index=True,
    )
    maintenance_category = fields.Selection(
        MAINTENANCE_CATEGORY_SELECTION,
        string="Ажлын төрөл",
        tracking=True,
    )
    issue_summary = fields.Char(string="Асуудлын товч", tracking=True)
    diagnosis_note = fields.Text(string="Онош")
    action_taken = fields.Text(string="Авсан арга хэмжээ")
    repair_start_datetime = fields.Datetime(string="Засвар эхэлсэн")
    repair_end_datetime = fields.Datetime(string="Засвар дууссан")
    estimated_repair_hours = fields.Float(string="Тооцоот засварын цаг")
    actual_repair_hours = fields.Float(string="Бодит засварын цаг")
    expected_ready_datetime = fields.Datetime(string="Бэлэн болох хүлээгдэж буй хугацаа")
    downtime_hours = fields.Float(
        string="Нийт зогсолтын цаг",
        compute="_compute_downtime_hours",
        store=True,
    )
    reviewed_by_id = fields.Many2one("res.users", string="Шалгасан")
    approved_by_id = fields.Many2one("res.users", string="Баталсан")
    repair_result = fields.Selection(
        REPAIR_RESULT_SELECTION,
        string="Үр дүн",
        tracking=True,
    )

    @api.depends(
        "repair_start_datetime",
        "repair_end_datetime",
        "repair_request_id.downtime_start",
        "repair_request_id.downtime_end",
    )
    def _compute_downtime_hours(self):
        now_dt = fields.Datetime.now()
        for task in self:
            start_dt = task.repair_request_id.downtime_start or task.repair_start_datetime
            end_dt = task.repair_request_id.downtime_end or task.repair_end_datetime or (
                now_dt if start_dt else False
            )
            if start_dt and end_dt:
                start_dt = fields.Datetime.to_datetime(start_dt)
                end_dt = fields.Datetime.to_datetime(end_dt)
                task.downtime_hours = max((end_dt - start_dt).total_seconds(), 0.0) / 3600.0
            else:
                task.downtime_hours = 0.0

    @api.constrains("repair_start_datetime", "repair_end_datetime")
    def _check_repair_datetime(self):
        for task in self:
            if (
                task.repair_start_datetime
                and task.repair_end_datetime
                and task.repair_end_datetime < task.repair_start_datetime
            ):
                raise ValidationError("Засварын дуусах хугацаа эхлэх хугацаанаас өмнө байж болохгүй.")

    def action_open_repair_request(self):
        self.ensure_one()
        if not self.repair_request_id:
            raise UserError("Энэ task-д холбогдсон засварын хүсэлт алга байна.")
        return self.repair_request_id.action_open_form()

    def write(self, vals):
        result = super().write(vals)
        if "stage_id" in vals and not self.env.context.get("skip_repair_request_sync"):
            requests = self.filtered(
                lambda task: task.repair_request_id
                and task.stage_id.fold
                and task.repair_request_id.state in {"parts_received", "in_repair"}
            ).mapped("repair_request_id")
            if requests:
                requests.with_context(skip_task_sync=True)._mark_waiting_repair_approval_from_task()
        return result
