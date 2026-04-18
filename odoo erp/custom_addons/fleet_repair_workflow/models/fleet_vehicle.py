from odoo import fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    repair_request_ids = fields.One2many(
        "fleet.repair.request",
        "vehicle_id",
        string="Засварын хүсэлтүүд",
    )
    repair_task_ids = fields.One2many(
        "project.task",
        "vehicle_id",
        string="Засварын task-ууд",
    )
    repair_request_count = fields.Integer(compute="_compute_repair_counters")
    repair_task_count = fields.Integer(compute="_compute_repair_counters")
    latest_repair_request_id = fields.Many2one(
        "fleet.repair.request",
        string="Сүүлийн засварын хүсэлт",
        compute="_compute_latest_repair_request",
    )
    latest_repair_state = fields.Char(
        string="Сүүлийн төлөв",
        compute="_compute_latest_repair_request",
    )
    vehicle_downtime_open = fields.Boolean(
        string="Нээлттэй зогсолт",
        compute="_compute_latest_repair_request",
    )

    def _compute_repair_counters(self):
        request_model = self.env["fleet.repair.request"].with_context(active_test=False)
        task_model = self.env["project.task"].with_context(active_test=False)
        for vehicle in self:
            vehicle.repair_request_count = request_model.search_count([("vehicle_id", "=", vehicle.id)])
            vehicle.repair_task_count = task_model.search_count(
                [("vehicle_id", "=", vehicle.id), ("is_vehicle_repair_task", "=", True)]
            )

    def _compute_latest_repair_request(self):
        request_model = self.env["fleet.repair.request"].with_context(active_test=False)
        state_labels = dict(request_model._fields["state"].selection)
        for vehicle in self:
            latest = request_model.search([("vehicle_id", "=", vehicle.id)], order="create_date desc, id desc", limit=1)
            vehicle.latest_repair_request_id = latest
            vehicle.latest_repair_state = state_labels.get(latest.state, "") if latest else ""
            vehicle.vehicle_downtime_open = bool(
                latest and latest.downtime_start and not latest.downtime_end and latest.state not in {"done", "cancelled"}
            )

    def action_open_repair_requests(self):
        self.ensure_one()
        action = self.env.ref("fleet_repair_workflow.action_fleet_repair_request").sudo().read()[0]
        action["domain"] = [("vehicle_id", "=", self.id)]
        action["context"] = {"default_vehicle_id": self.id}
        return action

    def action_open_repair_tasks(self):
        self.ensure_one()
        action = self.env.ref("project.action_view_task").sudo().read()[0]
        action["domain"] = [("vehicle_id", "=", self.id), ("is_vehicle_repair_task", "=", True)]
        action["context"] = {"default_vehicle_id": self.id, "search_default_my_tasks": 0}
        return action

    def action_new_repair_request(self):
        self.ensure_one()
        action = self.env.ref("fleet_repair_workflow.action_create_repair_request_wizard").sudo().read()[0]
        action["context"] = {
            "default_vehicle_id": self.id,
            "default_create_task": True,
        }
        return action

    def action_start_vehicle_inspection(self):
        self.ensure_one()
        action = self.action_new_repair_request()
        action["context"].update({"default_maintenance_category": "inspection"})
        return action
