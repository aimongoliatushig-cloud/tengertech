from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    repair_ceo_threshold_amount = fields.Float(
        string="CEO босго дүн (MNT)",
        default=1000000.0,
        config_parameter="fleet_repair_workflow.repair_ceo_threshold_amount",
    )
