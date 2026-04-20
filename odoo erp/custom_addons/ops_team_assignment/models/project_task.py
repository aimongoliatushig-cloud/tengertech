from odoo import api, fields, models


OPS_TEAM_SYNC_LOCKED_STATES = {"02_changes_requested", "1_done"}
OPS_MASTER_USER_TYPES = {"team_leader", "senior_master"}


class ProjectTask(models.Model):
    _inherit = "project.task"

    ops_team_leader_id = fields.Many2one(
        "res.users",
        string="Мастер",
        domain="[('share', '=', False), ('ops_user_type', 'in', ['team_leader', 'senior_master'])]",
    )

    @api.model
    def _get_ops_team_member_user_ids(self, team_leader):
        if not team_leader:
            return []
        if isinstance(team_leader, int):
            team_leader = self.env["res.users"].browse(team_leader)
        team_leader = team_leader.exists()
        if not team_leader:
            return []

        Employee = self.env["hr.employee"].sudo()
        leader_employee = Employee.search([("user_id", "=", team_leader.id)], limit=1)

        users = team_leader
        if leader_employee:
            member_employees = Employee.search(
                [("id", "child_of", leader_employee.id), ("id", "!=", leader_employee.id)]
            )
            users |= member_employees.mapped("user_id")

        return users.filtered(lambda user: user and not user.share).ids

    @api.model
    def _resolve_ops_user_ids_from_commands(self, commands, current_ids=None):
        user_ids = set(current_ids or [])
        for command in commands or []:
            if not isinstance(command, (list, tuple)) or not command:
                continue
            operation = command[0]
            if operation == 6:
                user_ids = set(command[2] or [])
            elif operation == 4:
                user_ids.add(command[1])
            elif operation == 3:
                user_ids.discard(command[1])
            elif operation == 5:
                user_ids.clear()
        return list(user_ids)

    @api.model
    def _get_ops_auto_team_leader_id(self, user_ids):
        users = self.env["res.users"].browse(user_ids).exists().filtered(lambda user: not user.share)
        if len(users) != 1:
            return False
        user = users[0]
        return user.id if user.ops_user_type in OPS_MASTER_USER_TYPES else False

    @api.model
    def _prepare_ops_team_assignment_values(self, vals, current_user_ids=None):
        new_vals = dict(vals)
        if self.env.context.get("ops_skip_team_autofill"):
            return new_vals

        if new_vals.get("ops_team_leader_id"):
            new_vals["user_ids"] = [
                (6, 0, self._get_ops_team_member_user_ids(new_vals["ops_team_leader_id"]))
            ]
            return new_vals

        if "user_ids" not in new_vals:
            return new_vals

        resolved_user_ids = self._resolve_ops_user_ids_from_commands(
            new_vals.get("user_ids"),
            current_ids=current_user_ids,
        )
        auto_team_leader_id = self._get_ops_auto_team_leader_id(resolved_user_ids)
        if auto_team_leader_id:
            new_vals["ops_team_leader_id"] = auto_team_leader_id
            new_vals["user_ids"] = [
                (6, 0, self._get_ops_team_member_user_ids(auto_team_leader_id))
            ]
        return new_vals

    def _ops_sync_current_team_members(self):
        for task in self.filtered(
            lambda item: item.ops_team_leader_id and item.state not in OPS_TEAM_SYNC_LOCKED_STATES
        ):
            target_user_ids = task._get_ops_team_member_user_ids(task.ops_team_leader_id)
            if set(task.user_ids.ids) == set(target_user_ids):
                continue
            task.sudo().with_context(ops_skip_team_autofill=True).write(
                {
                    "user_ids": [(6, 0, target_user_ids)],
                }
            )
        return True

    @api.model
    def _ops_sync_open_tasks_for_team_leaders(self, leader_user_ids):
        leader_users = self.env["res.users"].browse(leader_user_ids).exists().filtered(
            lambda user: user and not user.share
        )
        if not leader_users:
            return self.browse()

        tasks = self.sudo().search(
            [
                ("ops_team_leader_id", "in", leader_users.ids),
                ("state", "not in", list(OPS_TEAM_SYNC_LOCKED_STATES)),
            ]
        )
        tasks._ops_sync_current_team_members()
        return tasks

    @api.onchange("ops_team_leader_id")
    def _onchange_ops_team_leader_id(self):
        if self.ops_team_leader_id:
            self.user_ids = [(6, 0, self._get_ops_team_member_user_ids(self.ops_team_leader_id))]

    @api.onchange("user_ids")
    def _onchange_user_ids_ops_team_leader(self):
        if self.ops_team_leader_id or len(self.user_ids) != 1:
            return
        user = self.user_ids[0]
        if user.ops_user_type in OPS_MASTER_USER_TYPES:
            self.ops_team_leader_id = user
            self.user_ids = [(6, 0, self._get_ops_team_member_user_ids(user))]

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals = []
        for vals in vals_list:
            prepared_vals.append(self._prepare_ops_team_assignment_values(vals))
        return super().create(prepared_vals)

    def write(self, vals):
        if len(self) == 1:
            return super().write(
                self._prepare_ops_team_assignment_values(vals, current_user_ids=self.user_ids.ids)
            )

        for task in self:
            super(ProjectTask, task).write(
                task._prepare_ops_team_assignment_values(vals, current_user_ids=task.user_ids.ids)
            )
        return True
