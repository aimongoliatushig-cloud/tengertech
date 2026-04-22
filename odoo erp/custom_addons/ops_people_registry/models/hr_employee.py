from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ops_employee_code = fields.Char(
        string="Ажилтны код",
        copy=False,
        index=True,
    )
    ops_access_profile_id = fields.Many2one(
        "ops.access.profile",
        string="Системийн эрх",
        domain="[('active', '=', True)]",
    )

    def _ops_archive_user_with_employee(self):
        return (
            self.env["ir.config_parameter"].sudo().get_param(
                "ops_people_registry.archive_user_with_employee"
            )
            == "True"
        )

    def _ops_sync_user_from_employee(self):
        archive_user = self._ops_archive_user_with_employee()
        registry_service = self.env["ops.people.registry.service"]
        for employee in self.sudo():
            if not employee.user_id:
                continue
            user_vals = {
                "name": employee.name,
                "ops_department_id": employee.department_id.id or False,
                "ops_job_id": employee.job_id.id or False,
                "ops_manager_employee_id": employee.parent_id.id or False,
                "ops_employee_code": employee.ops_employee_code or False,
                "ops_access_profile_id": employee.ops_access_profile_id.id or False,
            }
            if employee.work_email and "@" in employee.work_email:
                user_vals["email"] = employee.work_email
            if employee.work_phone:
                user_vals["phone"] = employee.work_phone
            if employee.active:
                user_vals["active"] = True
            elif archive_user:
                user_vals["active"] = False

            if registry_service._needs_write(employee.user_id, user_vals):
                employee.user_id.with_context(ops_skip_user_employee_sync=True).write(user_vals)

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        if not self.env.context.get("ops_skip_employee_user_sync"):
            employees._ops_sync_user_from_employee()
        return employees

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get("ops_skip_employee_user_sync") and {
            "name",
            "active",
            "user_id",
            "department_id",
            "job_id",
            "parent_id",
            "work_email",
            "work_phone",
            "mobile_phone",
            "ops_employee_code",
            "ops_access_profile_id",
        } & set(vals):
            self._ops_sync_user_from_employee()
        return result
