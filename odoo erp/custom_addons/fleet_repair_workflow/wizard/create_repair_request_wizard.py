from odoo import fields, models


class CreateRepairRequestWizard(models.TransientModel):
    _name = "create.repair.request.wizard"
    _description = "Create Repair Request Wizard"

    vehicle_id = fields.Many2one("fleet.vehicle", string="Машин", required=True)
    project_id = fields.Many2one("project.project", string="Төсөл")
    maintenance_category = fields.Selection(
        [
            ("repair", "Засвар"),
            ("service", "Үйлчилгээ"),
            ("inspection", "Шалгалт"),
            ("emergency", "Яаралтай"),
        ],
        string="Төрөл",
        default="repair",
        required=True,
    )
    issue_summary = fields.Char(string="Асуудлын товч", required=True)
    problem_description = fields.Text(string="Асуудлын дэлгэрэнгүй")
    team_leader_id = fields.Many2one("res.users", string="Багийн ахлагч")
    estimated_repair_hours = fields.Float(string="Тооцоот засварын цаг")
    create_task = fields.Boolean(string="Task үүсгэх", default=True)

    def action_create_request(self):
        self.ensure_one()
        request = self.env["fleet.repair.request"].create(
            {
                "vehicle_id": self.vehicle_id.id,
                "project_id": self.project_id.id,
                "maintenance_category": self.maintenance_category,
                "issue_summary": self.issue_summary,
                "problem_description": self.problem_description,
                "team_leader_id": self.team_leader_id.id,
                "estimated_repair_hours": self.estimated_repair_hours,
                "downtime_start": fields.Datetime.now(),
            }
        )
        if self.create_task:
            request._ensure_repair_task()
        return request.action_open_form()
