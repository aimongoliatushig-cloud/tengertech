from odoo import fields, models


class MfoDailyOperationReportExtension(models.Model):
    _inherit = "mfo.daily.operation.report"

    vehicle_license_plate = fields.Char(
        string="Улсын дугаар",
        related="vehicle_id.license_plate",
        readonly=True,
    )
