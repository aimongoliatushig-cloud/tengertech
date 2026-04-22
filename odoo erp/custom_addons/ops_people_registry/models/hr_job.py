from odoo import fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    ops_registry_code = fields.Char(
        string="Бүртгэлийн код",
        copy=False,
        index=True,
    )
    ops_is_registry_standard = fields.Boolean(
        string="Стандарт мастер",
        default=False,
        copy=False,
    )
