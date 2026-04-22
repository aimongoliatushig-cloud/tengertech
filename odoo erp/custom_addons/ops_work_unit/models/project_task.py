from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = "project.task"

    ops_allowed_unit_ids = fields.Many2many(
        "ops.work.unit",
        string="Зөвшөөрөгдсөн нэгжүүд",
        related="project_id.ops_allowed_unit_ids",
        readonly=True,
    )
    ops_default_unit_id = fields.Many2one(
        "ops.work.unit",
        string="Үндсэн нэгж",
        related="project_id.ops_default_unit_id",
        readonly=True,
    )
    ops_measurement_unit_id = fields.Many2one("ops.work.unit", string="Хэмжих нэгж")
    ops_measurement_unit_code = fields.Char(
        string="Нэгжийн код",
        related="ops_measurement_unit_id.code",
        store=True,
        readonly=True,
    )
    ops_allowed_unit_summary = fields.Char(
        string="Энэ ажилд ашиглах боломжтой нэгжүүд",
        compute="_compute_ops_allowed_unit_summary",
    )

    @api.depends("project_id.ops_allowed_unit_ids.name")
    def _compute_ops_allowed_unit_summary(self):
        for task in self:
            task.ops_allowed_unit_summary = ", ".join(task.ops_allowed_unit_ids.mapped("name"))

    @api.onchange("project_id")
    def _onchange_project_id_apply_unit_defaults(self):
        for task in self:
            self.env["ops.work.unit"]._ops_sync_task_units_from_project(task)

    @api.onchange("ops_measurement_unit_id")
    def _onchange_ops_measurement_unit_id(self):
        for task in self:
            if (
                task.ops_measurement_unit_id
                and task.ops_allowed_unit_ids
                and task.ops_measurement_unit_id not in task.ops_allowed_unit_ids
            ):
                task.ops_measurement_unit_id = task.ops_default_unit_id or task.ops_allowed_unit_ids[:1]

    @api.model
    def _ops_prepare_unit_vals(self, vals):
        prepared = dict(vals)
        if not prepared.get("ops_measurement_unit_id") and (prepared.get("ops_measurement_unit") or "").strip():
            unit = self.env["ops.work.unit"]._ops_find_unit_from_text(prepared["ops_measurement_unit"])
            if not unit:
                raise ValidationError(_("Хэмжих нэгжийг лавлахаас сонгоно уу."))
            prepared["ops_measurement_unit_id"] = unit.id
            prepared["ops_measurement_unit"] = unit.name
        if "ops_measurement_unit_id" in prepared:
            unit = self.env["ops.work.unit"].browse(prepared["ops_measurement_unit_id"]).exists()
            prepared["ops_measurement_unit"] = unit.name if unit else False
        return prepared

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._ops_prepare_unit_vals(vals) for vals in vals_list]
        tasks = super().create(vals_list)
        if not self.env.context.get("skip_ops_unit_sync"):
            for task in tasks:
                self.env["ops.work.unit"]._ops_sync_task_units_from_project(task)
        return tasks

    def write(self, vals):
        vals = self._ops_prepare_unit_vals(vals)
        result = super().write(vals)
        if not self.env.context.get("skip_ops_unit_sync"):
            for task in self:
                self.env["ops.work.unit"]._ops_sync_task_units_from_project(task)
        return result

    @api.constrains("project_id", "ops_measurement_unit_id", "ops_planned_quantity")
    def _check_ops_task_unit_selection(self):
        for task in self:
            if (
                task.ops_measurement_unit_id
                and task.ops_allowed_unit_ids
                and task.ops_measurement_unit_id not in task.ops_allowed_unit_ids
            ):
                raise ValidationError(_("Сонгосон хэмжих нэгж тухайн ажлын төрөлд зөвшөөрөгдсөн байх ёстой."))

            needs_unit = bool(
                task.ops_planned_quantity > 0
                or task.ops_report_ids
                or (task.ops_measurement_unit or "").strip()
                or task.ops_measurement_unit_id
            )
            if needs_unit and not task.ops_measurement_unit_id:
                raise ValidationError(_("Хэмжих нэгж сонгоно уу."))
