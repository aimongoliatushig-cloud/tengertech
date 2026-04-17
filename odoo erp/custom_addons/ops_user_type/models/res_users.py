from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    ops_user_type = fields.Selection(
        selection=[
            ("system_admin", "Системийн админ"),
            ("general_manager", "Ерөнхий менежер"),
            ("project_manager", "Төслийн удирдагч"),
            ("team_leader", "Багийн ахлагч"),
            ("worker", "Ажилтан"),
        ],
        string="Хэрэглэгчийн төрөл",
        default="worker",
        help="Municipal operations role used when creating and managing users.",
    )
