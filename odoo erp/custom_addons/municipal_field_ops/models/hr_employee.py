from odoo import fields, models

from .common import EMPLOYEE_ROLE_SELECTION


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    mfo_is_field_active = fields.Boolean(
        string="Талбайн ажиллагаанд ашиглах",
        default=True,
        tracking=True,
    )
    mfo_field_role = fields.Selection(
        selection=EMPLOYEE_ROLE_SELECTION,
        string="Талбайн үүрэг",
        tracking=True,
    )
