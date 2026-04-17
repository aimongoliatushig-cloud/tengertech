from odoo import _, models
from odoo.exceptions import AccessError


class ProjectTask(models.Model):
    _inherit = "project.task"

    def write(self, vals):
        user = self.env.user
        if user.has_group("ops_role_security.group_ops_worker"):
            disallowed_fields = set(vals) - {"stage_id"}
            if disallowed_fields:
                raise AccessError(
                    _(
                        "Workers can only update task status. "
                        "Please ask a team leader for other changes."
                    )
                )
        return super().write(vals)
