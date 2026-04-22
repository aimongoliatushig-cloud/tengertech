from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    ops_department_id = fields.Many2one(
        "hr.department",
        string="Алба нэгж",
        domain="[('active', '=', True)]",
    )
    ops_job_id = fields.Many2one(
        "hr.job",
        string="Албан тушаал",
        domain="[('active', '=', True)]",
    )
    ops_access_profile_id = fields.Many2one(
        "ops.access.profile",
        string="Системийн эрх",
        domain="[('active', '=', True)]",
    )
    ops_manager_employee_id = fields.Many2one(
        "hr.employee",
        string="Шууд удирдлага",
        domain="[('active', '=', True)]",
    )
    ops_employee_code = fields.Char(
        string="Ажилтны код",
        copy=False,
        index=True,
    )

    def _ops_get_registry_profile_group_ids(self):
        profile_groups = self.env["ops.access.profile"].sudo().search([]).mapped("group_ids")
        return profile_groups.ids

    def _ops_sync_profile_groups(self):
        managed_group_ids = self._ops_get_registry_profile_group_ids()
        if not managed_group_ids:
            return

        for user in self.sudo():
            target_group_ids = []
            if not user.share and user.ops_access_profile_id:
                target_group_ids = user.ops_access_profile_id.group_ids.ids

            self.env.cr.execute(
                """
                DELETE FROM res_groups_users_rel
                 WHERE uid = %s
                   AND gid = ANY(%s)
                """,
                [user.id, managed_group_ids],
            )
            for group_id in target_group_ids:
                self.env.cr.execute(
                    """
                    INSERT INTO res_groups_users_rel (gid, uid)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    [group_id, user.id],
                )
        self.env.registry.clear_cache()

    def _ops_sync_legacy_user_type_from_profile(self):
        for user in self.sudo():
            if user.share or not user.ops_access_profile_id:
                continue
            legacy_user_type = user.ops_access_profile_id.legacy_user_type
            if legacy_user_type and user.ops_user_type != legacy_user_type:
                user.with_context(
                    ops_skip_access_profile_sync=True,
                    ops_skip_user_employee_sync=True,
                ).write({"ops_user_type": legacy_user_type})

    def _ops_get_or_create_registry_employee(self):
        self.ensure_one()
        Employee = self.env["hr.employee"].sudo().with_context(active_test=False)
        employee = self.employee_id or Employee.search(
            [("user_id", "=", self.id)],
            limit=1,
        )
        employee_created = False
        employee_linked = False

        if not employee:
            exact_name_candidates = Employee.search(
                [
                    ("user_id", "=", False),
                    ("name", "=", self.name),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=2,
            )
            if len(exact_name_candidates) == 1:
                employee = exact_name_candidates
                employee.with_context(ops_skip_employee_user_sync=True).write({"user_id": self.id})
                employee_linked = True
            else:
                employee = Employee.with_context(ops_skip_employee_user_sync=True).create(
                    {
                        "name": self.name,
                        "company_id": self.company_id.id,
                        "user_id": self.id,
                        "active": self.active,
                    }
                )
                employee_created = True
        return employee, employee_created, employee_linked

    def _ops_sync_employee_from_user(self):
        for user in self.sudo():
            if user.share or user.login == "__system__":
                continue
            employee, _employee_created, _employee_linked = user._ops_get_or_create_registry_employee()
            employee_vals = {
                "name": user.name,
                "user_id": user.id,
                "active": user.active,
                "department_id": user.ops_department_id.id or False,
                "job_id": user.ops_job_id.id or False,
                "parent_id": user.ops_manager_employee_id.id or False,
                "ops_employee_code": user.ops_employee_code or False,
                "ops_access_profile_id": user.ops_access_profile_id.id or False,
            }
            if user.email and "@" in user.email:
                employee_vals["work_email"] = user.email
            if user.phone:
                employee_vals["work_phone"] = user.phone
            if user.mobile_phone:
                employee_vals["mobile_phone"] = user.mobile_phone

            if self.env["ops.people.registry.service"]._needs_write(employee, employee_vals):
                employee.with_context(ops_skip_employee_user_sync=True).write(employee_vals)

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        if not self.env.context.get("ops_skip_access_profile_sync"):
            users._ops_sync_legacy_user_type_from_profile()
            users._ops_sync_profile_groups()
        if not self.env.context.get("ops_skip_user_employee_sync"):
            users._ops_sync_employee_from_user()
        return users

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get("ops_skip_access_profile_sync") and (
            "ops_access_profile_id" in vals or "groups_id" in vals
        ):
            self._ops_sync_legacy_user_type_from_profile()
            self._ops_sync_profile_groups()
        if not self.env.context.get("ops_skip_user_employee_sync") and {
            "name",
            "active",
            "phone",
            "email",
            "ops_department_id",
            "ops_job_id",
            "ops_access_profile_id",
            "ops_manager_employee_id",
            "ops_employee_code",
        } & set(vals):
            self._ops_sync_employee_from_user()
        return result
