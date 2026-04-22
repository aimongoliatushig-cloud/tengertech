from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OpsTaskReport(models.Model):
    _inherit = "ops.task.report"

    task_measurement_unit_id = fields.Many2one(
        "ops.work.unit",
        string="Хэмжих нэгж",
        related="task_id.ops_measurement_unit_id",
        readonly=True,
    )
    task_measurement_unit_code = fields.Char(
        string="Нэгжийн код",
        related="task_id.ops_measurement_unit_code",
        store=True,
        readonly=True,
    )

    @api.constrains("task_id", "reported_quantity")
    def _check_ops_report_work_unit(self):
        for report in self:
            if not report.task_id:
                continue
            if not report.task_id.ops_measurement_unit_id:
                raise ValidationError(_("Тайлан оруулахын өмнө ажлын хэмжих нэгжийг тохируулна уу."))
            if report.reported_quantity <= 0:
                raise ValidationError(_("Гүйцэтгэсэн хэмжээ 0-ээс их байх ёстой."))
