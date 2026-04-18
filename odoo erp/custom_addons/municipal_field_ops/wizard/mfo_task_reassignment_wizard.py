from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class MfoTaskReassignmentWizard(models.TransientModel):
    _name = "mfo.task.reassignment.wizard"
    _description = "Өдрийн даалгаврын дахин хуваарилалт"

    task_id = fields.Many2one(
        "project.task",
        string="Даалгавар",
        required=True,
        ondelete="cascade",
    )
    route_id = fields.Many2one("mfo.route", string="Маршрут")
    crew_team_id = fields.Many2one("mfo.crew.team", string="Экипаж")
    vehicle_id = fields.Many2one("fleet.vehicle", string="Техник")
    driver_employee_id = fields.Many2one("hr.employee", string="Жолооч")
    collector_employee_ids = fields.Many2many(
        "hr.employee",
        "mfo_reassign_collector_rel",
        "wizard_id",
        "employee_id",
        string="Ачигчид",
    )
    inspector_employee_id = fields.Many2one("hr.employee", string="Хянагч")
    planned_start = fields.Datetime(string="Төлөвлөсөн эхлэх цаг")
    planned_end = fields.Datetime(string="Төлөвлөсөн дуусах цаг")
    reset_stop_lines = fields.Boolean(
        string="Маршрут солигдвол зогсоолын мөрийг дахин үүсгэх",
        default=True,
    )
    reason = fields.Text(string="Шалтгаан", required=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        task = self.env["project.task"].browse(self.env.context.get("default_task_id")).exists()
        if task:
            values.update(
                {
                    "route_id": task.mfo_route_id.id,
                    "crew_team_id": task.mfo_crew_team_id.id,
                    "vehicle_id": task.mfo_vehicle_id.id,
                    "driver_employee_id": task.mfo_driver_employee_id.id,
                    "collector_employee_ids": [fields.Command.set(task.mfo_collector_employee_ids.ids)],
                    "inspector_employee_id": task.mfo_inspector_employee_id.id,
                    "planned_start": task.mfo_planned_start,
                    "planned_end": task.mfo_planned_end,
                }
            )
        return values

    @api.onchange("crew_team_id")
    def _onchange_crew_team_id(self):
        for wizard in self:
            if not wizard.crew_team_id:
                continue
            wizard.vehicle_id = wizard.crew_team_id.vehicle_id
            wizard.driver_employee_id = wizard.crew_team_id.driver_employee_id
            wizard.collector_employee_ids = wizard.crew_team_id.collector_employee_ids
            wizard.inspector_employee_id = wizard.crew_team_id.inspector_employee_id

    def action_apply(self):
        self.ensure_one()
        task = self.task_id
        if not task._mfo_is_dispatcher_or_manager():
            raise AccessError(_("Дахин хуваарилалтыг зөвхөн менежер эсвэл диспетчер хийнэ."))

        write_ctx = self.env.context
        if self.reset_stop_lines:
            write_ctx = dict(write_ctx, mfo_force_route_rebuild=True)

        task.with_context(write_ctx).write(
            {
                "mfo_route_id": self.route_id.id,
                "mfo_crew_team_id": self.crew_team_id.id,
                "mfo_vehicle_id": self.vehicle_id.id,
                "mfo_driver_employee_id": self.driver_employee_id.id,
                "mfo_collector_employee_ids": [fields.Command.set(self.collector_employee_ids.ids)],
                "mfo_inspector_employee_id": self.inspector_employee_id.id,
                "mfo_planned_start": self.planned_start,
                "mfo_planned_end": self.planned_end,
                "mfo_is_emergency_reassignment": True,
                "mfo_last_reassignment_reason": self.reason,
            }
        )
        task.message_post(body=_("Яаралтай дахин хуваарилалт хийлээ: %s") % self.reason)
        return {"type": "ir.actions.act_window_close"}
