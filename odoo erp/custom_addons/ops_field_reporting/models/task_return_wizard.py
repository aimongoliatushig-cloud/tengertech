import html

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class OpsTaskReturnWizard(models.TransientModel):
    _name = "ops.task.return.wizard"
    _description = "Return Task For Changes"

    task_id = fields.Many2one(
        "project.task",
        string="Task",
        required=True,
        readonly=True,
    )
    return_reason = fields.Text(
        string="Буцаах шалтгаан",
        required=True,
    )

    def action_confirm_return(self):
        self.ensure_one()
        task = self.task_id
        reason = (self.return_reason or "").strip()

        if not reason:
            raise ValidationError(_("Буцаах шалтгаанаа оруулна уу."))
        if not task._ops_is_current_user_general_manager():
            raise AccessError(_("Зөвхөн ерөнхий менежер шалгагдаж буй ажлыг буцаах боломжтой."))

        progress_stage = task._ops_get_target_stage("progress")
        if not progress_stage:
            raise UserError(_("`Явагдаж буй ажил` үе шат энэ төсөл дээр алга байна."))

        task.with_context(ops_workflow_transition="return_to_progress").write(
            {
                "stage_id": progress_stage.id,
                "state": "01_in_progress",
            }
        )
        reason_html = html.escape(reason).replace("\n", "<br/>")
        task.message_post(
            body=_(
                "Ерөнхий менежер ажлыг засвар нэхэж буцаалаа.<br/><br/><strong>Шалтгаан:</strong><br/>%s"
            )
            % reason_html
        )
        return {"type": "ir.actions.act_window_close"}
