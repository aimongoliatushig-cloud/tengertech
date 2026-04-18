from odoo import api, fields, models
from odoo.fields import Command
from odoo.exceptions import ValidationError


DEFAULT_TASK_STAGES = (
    {"name": "Хийгдэх ажил", "sequence": 0, "fold": False},
    {"name": "Явагдаж буй ажил", "sequence": 1, "fold": False},
    {"name": "Шалгагдаж буй ажил", "sequence": 2, "fold": False},
    {"name": "Дууссан ажил", "sequence": 3, "fold": False},
)


class ProjectProject(models.Model):
    _inherit = "project.project"

    ops_department_id = fields.Many2one(
        "hr.department",
        string="Алба нэгж",
        index=True,
        group_expand="_read_group_ops_department_id",
    )
    ops_attachment_ids = fields.Many2many(
        "ir.attachment",
        "ops_project_attachment_rel",
        "project_id",
        "attachment_id",
        string="Төслийн хавсралтууд",
        bypass_search_access=True,
    )
    ops_track_quantity = fields.Boolean(string="Төлөвлөсөн хэмжээ ашиглах")
    ops_planned_quantity = fields.Float(string="Төлөвлөсөн хэмжээ")
    ops_measurement_unit = fields.Char(string="Хэмжих нэгж")

    def _link_ops_attachments(self):
        for project in self:
            if project.ops_attachment_ids:
                project.ops_attachment_ids.sudo().write(
                    {
                        "res_model": project._name,
                        "res_id": project.id,
                    }
                )

    def _ensure_ops_default_task_stages(self):
        Stage = self.env["project.task.type"].sudo()
        for project in self:
            if project.is_template or project.type_ids:
                continue
            stage_ids = []
            for stage_vals in DEFAULT_TASK_STAGES:
                stage = Stage.create(
                    {
                        **stage_vals,
                        "project_ids": [Command.link(project.id)],
                    }
                )
                stage_ids.append(stage.id)
            project.type_ids = [Command.set(stage_ids)]

    @api.model
    def _read_group_ops_department_id(self, departments, domain):
        department_ids = self.env["hr.department"].search(
            [("active", "=", True)],
            order="name asc",
        )
        return department_ids

    @api.onchange("ops_department_id")
    def _onchange_ops_department_id(self):
        for project in self:
            department_user = project._get_ops_department_project_manager(
                project.ops_department_id.id
            )
            if department_user:
                project.user_id = department_user

    @api.onchange("ops_track_quantity")
    def _onchange_ops_track_quantity(self):
        for project in self:
            if not project.ops_track_quantity:
                project.ops_planned_quantity = 0
                project.ops_measurement_unit = False

    @api.constrains(
        "ops_track_quantity",
        "ops_planned_quantity",
        "ops_measurement_unit",
    )
    def _check_ops_quantity_configuration(self):
        for project in self:
            if not project.ops_track_quantity:
                continue
            if project.ops_planned_quantity <= 0:
                raise ValidationError("Төлөвлөсөн хэмжээ 0-ээс их байх ёстой.")
            if not (project.ops_measurement_unit or "").strip():
                raise ValidationError("Хэмжих нэгжээ заавал оруулна уу.")

    @api.model
    def _get_ops_department_project_manager(self, department_id):
        if not department_id:
            return self.env["res.users"]

        department = self.env["hr.department"].browse(department_id)
        if department.ops_project_manager_user_id:
            return department.ops_project_manager_user_id

        return self.env["res.users"].search(
            [
                ("share", "=", False),
                ("ops_user_type", "=", "project_manager"),
                ("ops_project_department_ids", "in", department_id),
            ],
            limit=1,
        )

    @api.model
    def _ops_apply_department_manager_defaults(self, vals):
        department_id = vals.get("ops_department_id")
        if not department_id or vals.get("user_id"):
            return vals

        department_user = self._get_ops_department_project_manager(department_id)
        if department_user:
            vals["user_id"] = department_user.id
        return vals

    @api.model
    def _ops_normalize_quantity_defaults(self, vals):
        vals = dict(vals)
        if vals.get("ops_track_quantity") is False:
            vals["ops_planned_quantity"] = 0
            vals["ops_measurement_unit"] = False
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [
            self._ops_normalize_quantity_defaults(
                self._ops_apply_department_manager_defaults(dict(vals))
            )
            for vals in vals_list
        ]
        projects = super().create(vals_list)
        projects._ensure_ops_default_task_stages()
        projects._link_ops_attachments()
        return projects

    def write(self, vals):
        vals = self._ops_normalize_quantity_defaults(vals)
        if "ops_department_id" in vals and "user_id" not in vals:
            vals = self._ops_apply_department_manager_defaults(dict(vals))
        result = super().write(vals)
        if "ops_attachment_ids" in vals:
            self._link_ops_attachments()
        return result
