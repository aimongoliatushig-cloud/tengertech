from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    ops_department_id = fields.Many2one(
        "hr.department",
        string="Харьяалагдах алба нэгж",
        domain="[('active', '=', True)]",
        help="Хэрэглэгчийн үндсэн харьяалагдах алба нэгжийг заана.",
    )
    ops_project_department_id = fields.Many2one(
        "hr.department",
        string="Хариуцах үндсэн алба нэгж",
        compute="_compute_ops_project_department_id",
        inverse="_inverse_ops_project_department_id",
        store=True,
    )
    ops_project_department_ids = fields.Many2many(
        "hr.department",
        "ops_project_manager_department_rel",
        "user_id",
        "department_id",
        string="Хариуцах алба нэгж",
        domain="[('active', '=', True)]",
        help="Төслийн менежер хариуцах алба нэгжээ сонгоно.",
    )

    @api.depends("ops_project_department_ids")
    def _compute_ops_project_department_id(self):
        for user in self:
            user.ops_project_department_id = user.ops_project_department_ids[:1]

    def _inverse_ops_project_department_id(self):
        if self.env.context.get("skip_ops_project_department_sync"):
            return

        for user in self:
            if user.ops_project_department_id:
                user.ops_project_department_ids = [
                    fields.Command.set([user.ops_project_department_id.id])
                ]
            else:
                user.ops_project_department_ids = [fields.Command.clear()]

    def _sync_ops_project_department_links(self):
        if self.env.context.get("skip_ops_project_department_sync"):
            return

        Department = self.env["hr.department"].sudo()

        for user in self.sudo():
            if user.ops_user_type != "project_manager":
                if user.ops_project_department_ids:
                    user.with_context(skip_ops_project_department_sync=True).write(
                        {"ops_project_department_ids": [fields.Command.clear()]}
                    )

                departments_for_user = Department.search(
                    [("ops_project_manager_user_id", "=", user.id)]
                )
                if departments_for_user:
                    departments_for_user.write({"ops_project_manager_user_id": False})
                continue

            departments_for_user = Department.search(
                [("ops_project_manager_user_id", "=", user.id)]
            )
            selected_departments = user.ops_project_department_ids

            if not selected_departments:
                if departments_for_user:
                    departments_for_user.write({"ops_project_manager_user_id": False})
                continue

            extra_departments = departments_for_user.filtered(
                lambda department: department not in selected_departments
            )
            if extra_departments:
                extra_departments.write({"ops_project_manager_user_id": False})

            for department in selected_departments:
                previous_manager = department.ops_project_manager_user_id
                if previous_manager and previous_manager.id != user.id:
                    previous_manager.with_context(
                        skip_ops_project_department_sync=True
                    ).write(
                        {
                            "ops_project_department_ids": [
                                fields.Command.unlink(department.id)
                            ]
                        }
                    )

                if department.ops_project_manager_user_id.id != user.id:
                    department.write({"ops_project_manager_user_id": user.id})

    def _sync_ops_department_defaults(self):
        for user in self:
            if (
                user.ops_user_type == "project_manager"
                and not user.ops_department_id
                and user.ops_project_department_ids
            ):
                user.ops_department_id = user.ops_project_department_ids[:1]

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._sync_ops_department_defaults()
        users._sync_ops_project_department_links()
        return users

    def write(self, vals):
        if (
            vals.get("ops_user_type")
            and vals.get("ops_user_type") != "project_manager"
            and "ops_project_department_ids" not in vals
            and "ops_project_department_id" not in vals
        ):
            vals = dict(vals)
            vals["ops_project_department_ids"] = [fields.Command.clear()]

        result = super().write(vals)
        if {
            "ops_department_id",
            "ops_project_department_ids",
            "ops_project_department_id",
            "ops_user_type",
        } & set(vals):
            self._sync_ops_department_defaults()
            self._sync_ops_project_department_links()
        return result
