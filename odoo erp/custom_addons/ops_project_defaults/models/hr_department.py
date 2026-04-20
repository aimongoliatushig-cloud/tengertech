from odoo import api, fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    ops_project_manager_user_id = fields.Many2one(
        "res.users",
        string="Хэлтсийн дарга",
        domain="[('share', '=', False), ('ops_user_type', '=', 'project_manager')]",
        help="Энэ алба нэгж дээр шинэ төсөл үүсгэх үед project manager-ийг автоматаар сонгоно.",
    )

    def _ops_can_sync_department_links(self):
        self.env.cr.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = 'ops_project_manager_department_rel'
            )
            """
        )
        return bool(self.env.cr.fetchone()[0])

    def _ops_run_initial_sync(self):
        if not self._ops_can_sync_department_links():
            return

        departments = self.sudo().search([("ops_project_manager_user_id", "!=", False)])
        if departments:
            departments._sync_ops_project_manager_user_links()

    def init(self):
        self._ops_run_initial_sync()

    def _register_hook(self):
        result = super()._register_hook()
        self._ops_run_initial_sync()
        return result

    def _sync_ops_project_manager_user_links(self):
        if self.env.context.get("skip_ops_project_department_sync"):
            return

        for department in self.sudo():
            linked_users = department.ops_project_manager_user_id.sudo()

            users_with_department = self.env["res.users"].sudo().search(
                [("ops_project_department_ids", "in", department.id)]
            )

            if not linked_users:
                if users_with_department:
                    users_with_department.with_context(
                        skip_ops_project_department_sync=True
                    ).write(
                        {
                            "ops_project_department_ids": [
                                fields.Command.unlink(department.id)
                            ]
                        }
                    )
                continue

            users_to_cleanup = users_with_department.filtered(
                lambda user: user.id != linked_users.id
            )
            if users_to_cleanup:
                users_to_cleanup.with_context(
                    skip_ops_project_department_sync=True
                ).write(
                    {
                        "ops_project_department_ids": [
                            fields.Command.unlink(department.id)
                        ]
                    }
                )

            if department not in linked_users.ops_project_department_ids:
                linked_users.with_context(skip_ops_project_department_sync=True).write(
                    {
                        "ops_project_department_ids": [
                            fields.Command.link(department.id)
                        ]
                    }
                )

    @api.model_create_multi
    def create(self, vals_list):
        departments = super().create(vals_list)
        departments._sync_ops_project_manager_user_links()
        return departments

    def write(self, vals):
        result = super().write(vals)
        if "ops_project_manager_user_id" in vals:
            self._sync_ops_project_manager_user_links()
        return result
