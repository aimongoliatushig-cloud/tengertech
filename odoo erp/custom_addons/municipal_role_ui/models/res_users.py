from odoo import api, fields, models

from .common import (
    LEGACY_USER_TYPE_BY_ROLE,
    MUNICIPAL_ROLE_SELECTION,
    ROLE_NAME_BY_CODE,
    ROLE_PROFILE_CODE_BY_ROLE,
)


class ResUsers(models.Model):
    _inherit = "res.users"

    municipal_role_code = fields.Selection(
        selection=MUNICIPAL_ROLE_SELECTION,
        string="Эрхийн ангилал",
        default="employee",
        copy=False,
    )
    municipal_role_name = fields.Char(
        string="Эрхийн ангиллын нэр",
        compute="_compute_municipal_role_name",
    )

    @api.depends("municipal_role_code")
    def _compute_municipal_role_name(self):
        for user in self:
            user.municipal_role_name = ROLE_NAME_BY_CODE.get(user.municipal_role_code, "")

    def _get_municipal_profile_by_role(self, role_code):
        profile_code = ROLE_PROFILE_CODE_BY_ROLE.get(role_code)
        if not profile_code or "ops.access.profile" not in self.env:
            return self.env["ops.access.profile"]
        return self.env["ops.access.profile"].sudo().search([("code", "=", profile_code)], limit=1)

    def _sync_municipal_role_profile(self):
        for user in self.sudo():
            if user.share:
                continue
            role_code = user.municipal_role_code or "employee"
            updates = {}
            profile = user._get_municipal_profile_by_role(role_code)
            if profile and user.ops_access_profile_id != profile:
                updates["ops_access_profile_id"] = profile.id
            legacy_role = LEGACY_USER_TYPE_BY_ROLE.get(role_code)
            if legacy_role and user.ops_user_type != legacy_role:
                updates["ops_user_type"] = legacy_role
            if updates:
                super(
                    ResUsers,
                    user.with_context(municipal_role_ui_skip_profile_sync=True),
                ).write(updates)

    def _sync_municipal_role_from_profile(self):
        for user in self.sudo():
            profile = user.ops_access_profile_id
            if not profile or not (profile.code or "").startswith("municipal_role_ui."):
                continue
            role_code = (profile.code or "").replace("municipal_role_ui.", "", 1)
            if role_code in ROLE_NAME_BY_CODE and user.municipal_role_code != role_code:
                super(
                    ResUsers,
                    user.with_context(municipal_role_ui_skip_profile_sync=True),
                ).write({"municipal_role_code": role_code})

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        if not self.env.context.get("municipal_role_ui_skip_profile_sync"):
            if any("municipal_role_code" in values for values in vals_list):
                users._sync_municipal_role_profile()
            elif any("ops_access_profile_id" in values for values in vals_list):
                users._sync_municipal_role_from_profile()
        return users

    def write(self, vals):
        result = super().write(vals)
        if self.env.context.get("municipal_role_ui_skip_profile_sync"):
            return result
        if "municipal_role_code" in vals:
            self._sync_municipal_role_profile()
        elif "ops_access_profile_id" in vals:
            self._sync_municipal_role_from_profile()
        return result

    def action_open_municipal_dashboard(self):
        self.ensure_one()
        return self.env["municipal.role.dashboard"].action_open_role_workspace(
            self.municipal_role_code or "employee",
            user=self,
        )
