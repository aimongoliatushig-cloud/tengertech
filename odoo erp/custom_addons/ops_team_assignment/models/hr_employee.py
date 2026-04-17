from odoo import api, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _ops_sync_related_team_tasks(self, leader_user_ids):
        if leader_user_ids:
            self.env["project.task"]._ops_sync_open_tasks_for_team_leaders(list(leader_user_ids))

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees._ops_sync_related_team_tasks(set(employees.sudo().mapped("parent_id.user_id").ids))
        return employees

    def write(self, vals):
        old_leader_user_ids = set(self.sudo().mapped("parent_id.user_id").ids)
        result = super().write(vals)
        new_leader_user_ids = set(self.sudo().mapped("parent_id.user_id").ids)
        self._ops_sync_related_team_tasks(old_leader_user_ids | new_leader_user_ids)
        return result

    def unlink(self):
        leader_user_ids = set(self.sudo().mapped("parent_id.user_id").ids)
        result = super().unlink()
        self._ops_sync_related_team_tasks(leader_user_ids)
        return result
