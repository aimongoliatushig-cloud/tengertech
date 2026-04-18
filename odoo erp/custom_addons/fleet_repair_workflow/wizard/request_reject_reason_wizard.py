from odoo import fields, models


class FleetRepairRequestRejectWizard(models.TransientModel):
    _name = "fleet.repair.request.reject.wizard"
    _description = "Fleet Repair Request Reject Wizard"

    request_id = fields.Many2one("fleet.repair.request", string="Хүсэлт", required=True)
    rejection_reason = fields.Text(string="Татгалзсан шалтгаан", required=True)

    def action_apply_rejection(self):
        self.ensure_one()
        self.request_id.action_apply_rejection_reason(self.rejection_reason)
        return {"type": "ir.actions.act_window_close"}
