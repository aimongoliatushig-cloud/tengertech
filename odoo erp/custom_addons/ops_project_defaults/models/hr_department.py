from odoo import api, fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    ops_project_manager_user_id = fields.Many2one(
        "res.users",
        string="Төслийн удирдагч",
        domain="[('share', '=', False), ('ops_user_type', '=', 'project_manager')]",
        help="Энэ алба нэгж дээр шинэ төсөл үүсгэх үед project manager-ийг автоматаар сонгоно.",
    )

    def _sync_ops_project_manager_user_links(self):
        if self.env.context.get("skip_ops_project_department_sync"):
            return

        User = self.env["res.users"].sudo()
        Department = self.sudo()

        for department in Department:
            linked_users = User.search(
                [("ops_project_department_id", "=", department.id)]
            )

            if not department.ops_project_manager_user_id:
                if linked_users:
                    linked_users.with_context(
                        skip_ops_project_department_sync=True
                    ).write({"ops_project_department_id": False})
                continue

            conflicting_departments = Department.search(
                [
                    ("id", "!=", department.id),
                    ("ops_project_manager_user_id", "=", department.ops_project_manager_user_id.id),
                ]
            )
            if conflicting_departments:
                conflicting_departments.with_context(
                    skip_ops_project_department_sync=True
                ).write({"ops_project_manager_user_id": False})

            conflicting_users = linked_users.filtered(
                lambda user: user.id != department.ops_project_manager_user_id.id
            )
            if conflicting_users:
                conflicting_users.with_context(
                    skip_ops_project_department_sync=True
                ).write({"ops_project_department_id": False})

            if department.ops_project_manager_user_id.ops_project_department_id.id != department.id:
                department.ops_project_manager_user_id.with_context(
                    skip_ops_project_department_sync=True
                ).write({"ops_project_department_id": department.id})

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
