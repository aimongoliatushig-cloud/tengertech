from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .common import WEIGHT_TOTAL_SOURCE_SELECTION


class MfoDailyWeightTotal(models.Model):
    _name = "mfo.daily.weight.total"
    _description = "Өдөр тутмын жингийн нийт"
    _order = "shift_date desc, vehicle_id, id desc"

    task_id = fields.Many2one(
        "project.task",
        string="Даалгавар",
        required=True,
        ondelete="cascade",
    )
    shift_date = fields.Date(
        string="Огноо",
        required=True,
        index=True,
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Техник",
        required=True,
        ondelete="restrict",
        index=True,
    )
    route_id = fields.Many2one(
        "mfo.route",
        string="Маршрут",
        ondelete="set null",
    )
    net_weight_total = fields.Float(
        string="Нийт цэвэр жин",
        required=True,
    )
    source = fields.Selection(
        selection=WEIGHT_TOTAL_SOURCE_SELECTION,
        string="Эх сурвалж",
        default="manual",
        required=True,
    )
    external_reference = fields.Char(string="Гадаад лавлагаа")
    sync_log_id = fields.Many2one(
        "mfo.sync.log",
        string="Синк лог",
        ondelete="set null",
    )
    note = fields.Char(string="Тэмдэглэл")

    _sql_constraints = [
        (
            "mfo_daily_weight_total_vehicle_date_unique",
            "unique(vehicle_id, shift_date)",
            "Нэг техник нэг өдөрт зөвхөн нэг өдөр тутмын жингийн нийттэй байна.",
        )
    ]

    @api.constrains("task_id", "vehicle_id", "shift_date")
    def _check_task_alignment(self):
        for total in self:
            if total.task_id.mfo_vehicle_id and total.task_id.mfo_vehicle_id != total.vehicle_id:
                raise ValidationError(_("Жингийн нийт дэх техник нь даалгаврын техниктэй таарах ёстой."))
            if total.task_id.mfo_shift_date and total.task_id.mfo_shift_date != total.shift_date:
                raise ValidationError(_("Жингийн нийт дэх огноо нь даалгаврын ээлжийн огноотой таарах ёстой."))
