from odoo import api, models


ROLE_GROUP_XMLIDS = {
    "system_admin": "ops_role_security.group_ops_system_admin",
    "director": "ops_role_security.group_ops_general_manager",
    "general_manager": "ops_role_security.group_ops_general_manager",
    "project_manager": "ops_role_security.group_ops_project_leader",
    "senior_master": "ops_role_security.group_ops_team_leader",
    "team_leader": "ops_role_security.group_ops_team_leader",
    "worker": "ops_role_security.group_ops_worker",
}

MFO_GROUP_XMLIDS = {
    "director": ["municipal_field_ops.group_mfo_manager"],
    "general_manager": ["municipal_field_ops.group_mfo_manager"],
    "project_manager": ["municipal_field_ops.group_mfo_manager"],
    "senior_master": ["municipal_field_ops.group_mfo_mobile_user"],
    "team_leader": ["municipal_field_ops.group_mfo_mobile_user"],
    "worker": ["municipal_field_ops.group_mfo_mobile_user"],
}


class ResUsers(models.Model):
    _inherit = "res.users"

    def _get_ops_managed_role_groups(self):
        return {role: self.env.ref(xmlid) for role, xmlid in ROLE_GROUP_XMLIDS.items()}

    def _get_mfo_managed_role_groups(self):
        role_groups = {}
        for role, xmlids in MFO_GROUP_XMLIDS.items():
            role_groups[role] = [
                group
                for xmlid in xmlids
                for group in [self.env.ref(xmlid, raise_if_not_found=False)]
                if group
            ]
        return role_groups

    @api.model
    def action_ops_sync_role_groups(self):
        self.sudo().search([])._sync_ops_role_group()
        return True

    def _sync_ops_role_group(self):
        role_groups = self._get_ops_managed_role_groups()
        mfo_role_groups = self._get_mfo_managed_role_groups()
        managed_group_ids = list({group.id for group in role_groups.values()})
        managed_group_ids.extend(
            {
                group.id
                for groups in mfo_role_groups.values()
                for group in groups
            }
        )
        managed_group_ids = list(set(managed_group_ids))
        for user in self.sudo():
            target_group = None if user.share else role_groups.get(user.ops_user_type)
            target_mfo_groups = [] if user.share else mfo_role_groups.get(user.ops_user_type, [])
            if managed_group_ids:
                self.env.cr.execute(
                    """
                    DELETE FROM res_groups_users_rel
                    WHERE uid = %s
                      AND gid = ANY(%s)
                    """,
                    [user.id, managed_group_ids],
                )
            if target_group:
                self.env.cr.execute(
                    """
                    INSERT INTO res_groups_users_rel (gid, uid)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    [target_group.id, user.id],
                )
            for group in target_mfo_groups:
                self.env.cr.execute(
                    """
                    INSERT INTO res_groups_users_rel (gid, uid)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    [group.id, user.id],
                )
        self.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._sync_ops_role_group()
        return users

    def write(self, vals):
        needs_role_resync = any(key in vals for key in ("ops_user_type", "group_ids", "groups_id"))
        if "groups_id" in vals and "group_ids" not in vals:
            vals = dict(vals)
            vals["group_ids"] = vals.pop("groups_id")
        result = super().write(vals)
        if needs_role_resync:
            self._sync_ops_role_group()
        return result
