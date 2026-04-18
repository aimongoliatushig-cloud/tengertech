from odoo import fields, models


class FleetVehicleModel(models.Model):
    _inherit = "fleet.vehicle.model"

    mfo_capacity_ton = fields.Float(
        string="Ачааны даац (тн)",
        tracking=True,
        help="Энэ загварын техникийн зөвшөөрөгдөх ачааны даац.",
    )
