from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    clearance_ids = fields.One2many(
        "hr.employee.clearance",
        "employee_id",
        string="Тойрох хуудасны түүх",
    )
    clearance_count = fields.Integer(
        string="Тойрох хуудасны тоо",
        compute="_compute_clearance_count",
    )

    def _compute_clearance_count(self):
        grouped_data = self.env["hr.employee.clearance"].read_group(
            [("employee_id", "in", self.ids)],
            ["employee_id"],
            ["employee_id"],
        )
        counts = {
            item["employee_id"][0]: item["employee_id_count"]
            for item in grouped_data
            if item["employee_id"]
        }
        for employee in self:
            employee.clearance_count = counts.get(employee.id, 0)

    def action_open_clearance_records(self):
        self.ensure_one()
        action = self.env.ref("hr_clearance_mn.action_hr_employee_clearance").read()[0]
        action["domain"] = [("employee_id", "=", self.id)]
        action["context"] = {"default_employee_id": self.id}
        return action

    def action_create_clearance(self):
        self.ensure_one()
        action = self.env.ref("hr_clearance_mn.action_hr_employee_clearance").read()[0]
        action["views"] = [(False, "form")]
        action["target"] = "current"
        action["context"] = {
            "default_employee_id": self.id,
            "default_employee_department_id": self.department_id.id,
            "default_employee_job_id": self.job_id.id,
            "default_hr_responsible_id": self.env.user.id,
        }
        return action
