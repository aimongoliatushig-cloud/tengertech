from odoo import api, fields, models


LEGACY_USER_TYPE_SELECTION = [
    ("system_admin", "Администратор"),
    ("director", "Захирал"),
    ("general_manager", "Ерөнхий менежер"),
    ("project_manager", "Хэлтсийн дарга"),
    ("senior_master", "Ахлах мастер"),
    ("team_leader", "Мастер"),
    ("worker", "Ажилтан"),
]


class OpsAccessProfile(models.Model):
    _name = "ops.access.profile"
    _description = "Системийн эрхийн профайл"
    _order = "sequence, id"

    name = fields.Char(string="Нэр", required=True, translate=True)
    code = fields.Char(string="Код", required=True, index=True)
    active = fields.Boolean(string="Идэвхтэй", default=True)
    sequence = fields.Integer(string="Дараалал", default=10)
    description = fields.Text(string="Тайлбар", translate=True)
    legacy_user_type = fields.Selection(
        selection=LEGACY_USER_TYPE_SELECTION,
        string="Хуучин системийн ангилал",
        required=True,
        default="worker",
    )
    group_ids = fields.Many2many(
        "res.groups",
        "ops_access_profile_group_rel",
        "profile_id",
        "group_id",
        string="Хамаарах бүлгүүд",
    )
    user_ids = fields.One2many(
        "res.users",
        "ops_access_profile_id",
        string="Хэрэглэгчид",
    )
    user_count = fields.Integer(
        string="Хэрэглэгчийн тоо",
        compute="_compute_related_counts",
    )
    employee_ids = fields.One2many(
        "hr.employee",
        "ops_access_profile_id",
        string="Ажилтнууд",
    )
    employee_count = fields.Integer(
        string="Ажилтны тоо",
        compute="_compute_related_counts",
    )

    @api.depends("user_ids", "employee_ids")
    def _compute_related_counts(self):
        for profile in self:
            profile.user_count = len(profile.user_ids)
            profile.employee_count = len(profile.employee_ids)

    def action_open_users(self):
        self.ensure_one()
        return {
            "name": "Профайлтай хэрэглэгчид",
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "view_mode": "list,form",
            "domain": [("ops_access_profile_id", "=", self.id)],
        }

    def action_open_employees(self):
        self.ensure_one()
        return {
            "name": "Профайлтай ажилтнууд",
            "type": "ir.actions.act_window",
            "res_model": "hr.employee",
            "view_mode": "list,form",
            "domain": [("ops_access_profile_id", "=", self.id)],
        }
