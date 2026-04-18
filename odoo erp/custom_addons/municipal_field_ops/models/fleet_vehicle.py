from odoo import api, fields, models

from .common import OPERATION_TYPE_SELECTION


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    mfo_active_for_ops = fields.Boolean(
        string="Талбайн ажиллагаанд ашиглах",
        default=True,
        tracking=True,
    )
    mfo_operation_type = fields.Selection(
        selection=OPERATION_TYPE_SELECTION,
        string="Үндсэн ажиллагаа",
        default="garbage",
        tracking=True,
    )
    mfo_capacity_ton = fields.Float(string="Ачааны даац (тн)")
    mfo_wrs_vehicle_code = fields.Char(
        string="WRS техникийн код",
        tracking=True,
        help="WRS-ийн өдөр тутмын жингийн тайланд энэ техник ямар кодоор гардагийг хадгална.",
    )
    mfo_weight_measurement_ids = fields.One2many(
        "mfo.weight.measurement",
        "vehicle_id",
        string="Жингийн бүртгэлүүд",
    )
    mfo_daily_weight_total_ids = fields.One2many(
        "mfo.daily.weight.total",
        "vehicle_id",
        string="Өдөр тутмын жингийн нийтүүд",
    )

    @api.model
    def _mfo_apply_model_capacity(self, vals):
        values = dict(vals)
        if "mfo_capacity_ton" in values:
            return values

        model_id = values.get("model_id")
        if not model_id:
            return values

        model = self.env["fleet.vehicle.model"].browse(model_id).exists()
        if model and model.mfo_capacity_ton:
            values["mfo_capacity_ton"] = model.mfo_capacity_ton
        return values

    @api.onchange("model_id")
    def _onchange_model_id_mfo_capacity(self):
        for vehicle in self:
            if vehicle.model_id and not vehicle.mfo_capacity_ton:
                vehicle.mfo_capacity_ton = vehicle.model_id.mfo_capacity_ton

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._mfo_apply_model_capacity(vals) for vals in vals_list]
        return super().create(vals_list)
