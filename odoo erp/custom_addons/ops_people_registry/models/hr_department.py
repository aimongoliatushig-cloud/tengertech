from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    ops_registry_code = fields.Char(
        string="Бүртгэлийн код",
        copy=False,
        index=True,
    )
    ops_is_registry_standard = fields.Boolean(
        string="Стандарт бүтэц",
        default=False,
        copy=False,
    )
