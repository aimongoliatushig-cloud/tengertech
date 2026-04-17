from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    ops_project_department_id = fields.Many2one(
        "hr.department",
        string="Хариуцах алба нэгж",
        domain="[('active', '=', True)]",
        help="Төслийн удирдагч энэ алба нэгжийн төслүүдийг хариуцна.",
    )

    def _sync_ops_project_department_links(self):
        if self.env.context.get("skip_ops_project_department_sync"):
            return

        Department = self.env["hr.department"].sudo()
        User = self.env["res.users"].sudo()

        for user in self.sudo():
            departments_for_user = Department.search(
                [("ops_project_manager_user_id", "=", user.id)]
            )

            if not user.ops_project_department_id:
                if departments_for_user:
                    departments_for_user.write({"ops_project_manager_user_id": False})
                continue

            conflicting_users = User.search(
                [
                    ("id", "!=", user.id),
                    ("ops_project_department_id", "=", user.ops_project_department_id.id),
                ]
            )
            if conflicting_users:
                conflicting_users.with_context(
                    skip_ops_project_department_sync=True
                ).write({"ops_project_department_id": False})

            extra_departments = departments_for_user.filtered(
                lambda department: department.id != user.ops_project_department_id.id
            )
            if extra_departments:
                extra_departments.write({"ops_project_manager_user_id": False})

            if user.ops_project_department_id.ops_project_manager_user_id.id != user.id:
                user.ops_project_department_id.write(
                    {"ops_project_manager_user_id": user.id}
                )

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._sync_ops_project_department_links()
        return users

    def write(self, vals):
        if (
            vals.get("ops_user_type")
            and vals.get("ops_user_type") != "project_manager"
            and "ops_project_department_id" not in vals
        ):
            vals = dict(vals)
            vals["ops_project_department_id"] = False

        result = super().write(vals)
        if {"ops_project_department_id", "ops_user_type"} & set(vals):
            self._sync_ops_project_department_links()
        return result
