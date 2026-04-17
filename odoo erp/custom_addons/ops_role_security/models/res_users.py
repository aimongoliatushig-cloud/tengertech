from odoo import api, models


ROLE_GROUP_XMLIDS = {
    "system_admin": "ops_role_security.group_ops_system_admin",
    "general_manager": "ops_role_security.group_ops_general_manager",
    "project_manager": "ops_role_security.group_ops_project_leader",
    "team_leader": "ops_role_security.group_ops_team_leader",
    "worker": "ops_role_security.group_ops_worker",
}


class ResUsers(models.Model):
    _inherit = "res.users"

    def _get_ops_managed_role_groups(self):
        return {
            role: self.env.ref(xmlid)
            for role, xmlid in ROLE_GROUP_XMLIDS.items()
        }

    def _sync_ops_role_group(self):
        role_groups = self._get_ops_managed_role_groups()
        managed_group_ids = [group.id for group in role_groups.values()]
        for user in self.sudo():
            target_group = None if user.share else role_groups.get(user.ops_user_type)
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
        self.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._sync_ops_role_group()
        return users

    def write(self, vals):
        if "groups_id" in vals and "group_ids" not in vals:
            vals = dict(vals)
            vals["group_ids"] = vals.pop("groups_id")
        result = super().write(vals)
        if "ops_user_type" in vals:
            self._sync_ops_role_group()
        return result
