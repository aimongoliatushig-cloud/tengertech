from odoo import _, models
from odoo.exceptions import AccessError


class ProjectTask(models.Model):
    _inherit = "project.task"

    def write(self, vals):
        user = self.env.user
        if user.has_group("ops_role_security.group_ops_worker") and not self.env.context.get(
            "skip_repair_request_sync"
        ):
            disallowed_fields = set(vals) - {"stage_id"}
            if disallowed_fields:
                raise AccessError(
                    _("Ажилтан зөвхөн даалгаврын төлөв шинэчилж болно. Бусад өөрчлөлтийг мастерээс хүснэ үү.")
                )
        return super().write(vals)
