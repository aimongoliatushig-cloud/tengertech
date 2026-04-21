from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    disciplinary_action_ids = fields.One2many(
        "hr.disciplinary.action",
        "employee_id",
        string="Сахилгын түүх",
    )
    disciplinary_action_count = fields.Integer(
        string="Сахилгын тоо",
        compute="_compute_hr_history_counts",
    )
    transfer_ids = fields.One2many(
        "hr.employee.transfer",
        "employee_id",
        string="Шилжилт хөдөлгөөний түүх",
    )
    transfer_count = fields.Integer(
        string="Шилжилтийн тоо",
        compute="_compute_hr_history_counts",
    )
    employment_status = fields.Selection(
        [
            ("active", "Идэвхтэй"),
            ("suspended", "Түдгэлзсэн"),
            ("terminated", "Халагдсан"),
        ],
        string="Ажил эрхлэлтийн төлөв",
        default="active",
        tracking=True,
    )
    termination_date = fields.Date(string="Халагдсан огноо", tracking=True)
    termination_reason = fields.Text(string="Халагдсан шалтгаан", tracking=True)

    def _compute_hr_history_counts(self):
        disciplinary_data = self.env["hr.disciplinary.action"].read_group(
            [("employee_id", "in", self.ids)],
            ["employee_id"],
            ["employee_id"],
        )
        transfer_data = self.env["hr.employee.transfer"].read_group(
            [("employee_id", "in", self.ids)],
            ["employee_id"],
            ["employee_id"],
        )
        disciplinary_map = {
            item["employee_id"][0]: item["employee_id_count"] for item in disciplinary_data if item["employee_id"]
        }
        transfer_map = {
            item["employee_id"][0]: item["employee_id_count"] for item in transfer_data if item["employee_id"]
        }
        for employee in self:
            employee.disciplinary_action_count = disciplinary_map.get(employee.id, 0)
            employee.transfer_count = transfer_map.get(employee.id, 0)

    def action_open_disciplinary_actions(self):
        self.ensure_one()
        action = self.env.ref("hr_discipline_transfer_mn.action_hr_disciplinary_action").read()[0]
        action["domain"] = [("employee_id", "=", self.id)]
        action["context"] = {"default_employee_id": self.id}
        return action

    def action_open_transfer_history(self):
        self.ensure_one()
        action = self.env.ref("hr_discipline_transfer_mn.action_hr_employee_transfer").read()[0]
        action["domain"] = [("employee_id", "=", self.id)]
        action["context"] = {"default_employee_id": self.id}
        return action
