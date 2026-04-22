from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectProject(models.Model):
    _inherit = "project.project"

    ops_work_type_id = fields.Many2one(
        "ops.work.type",
        string="Ажлын төрөл",
        compute="_compute_ops_work_type_id",
    )
    ops_profile_allowed_unit_ids = fields.Many2many(
        "ops.work.unit",
        string="Профайлын нэгжүүд",
        compute="_compute_ops_work_type_id",
    )
    ops_profile_default_unit_id = fields.Many2one(
        "ops.work.unit",
        string="Профайлын үндсэн нэгж",
        compute="_compute_ops_work_type_id",
    )
    ops_allowed_unit_ids = fields.Many2many(
        "ops.work.unit",
        "project_project_allowed_unit_rel",
        "project_id",
        "unit_id",
        string="Зөвшөөрөгдсөн нэгжүүд",
    )
    ops_default_unit_id = fields.Many2one("ops.work.unit", string="Үндсэн нэгж")
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

    @api.depends("mfo_operation_type")
    def _compute_ops_work_type_id(self):
        profiles = self.env["ops.work.type"].sudo().search([], order="sequence asc, id asc")
        profile_map = {profile.operation_type: profile for profile in profiles}
        for project in self:
            profile = profile_map.get(project.mfo_operation_type)
            project.ops_work_type_id = profile
            project.ops_profile_allowed_unit_ids = profile.allowed_unit_ids
            project.ops_profile_default_unit_id = profile.default_unit_id

    @api.depends("mfo_operation_type", "ops_allowed_unit_ids.name")
    def _compute_ops_allowed_unit_summary(self):
        for project in self:
            units = project.ops_allowed_unit_ids or project.ops_profile_allowed_unit_ids
            project.ops_allowed_unit_summary = ", ".join(units.mapped("name"))

    @api.onchange("mfo_operation_type")
    def _onchange_mfo_operation_type_apply_units(self):
        for project in self:
            self.env["ops.work.unit"]._ops_sync_project_units_from_profile(project)

    @api.onchange("ops_default_unit_id")
    def _onchange_ops_default_unit_id(self):
        for project in self:
            if project.ops_default_unit_id and project.ops_default_unit_id not in project.ops_allowed_unit_ids:
                project.ops_allowed_unit_ids |= project.ops_default_unit_id
            if project.ops_track_quantity and not project.ops_measurement_unit_id:
                project.ops_measurement_unit_id = project.ops_default_unit_id

    @api.onchange("ops_track_quantity")
    def _onchange_ops_track_quantity_apply_unit(self):
        for project in self:
            if project.ops_track_quantity and not project.ops_measurement_unit_id:
                project.ops_measurement_unit_id = project.ops_default_unit_id
            if not project.ops_track_quantity:
                project.ops_measurement_unit_id = False

    @api.model
    def _ops_prepare_unit_vals(self, vals):
        prepared = dict(vals)
        if prepared.get("ops_track_quantity") is False:
            prepared["ops_measurement_unit_id"] = False
            prepared["ops_measurement_unit"] = False
        elif not prepared.get("ops_measurement_unit_id") and (prepared.get("ops_measurement_unit") or "").strip():
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
        projects = super().create(vals_list)
        if not self.env.context.get("skip_ops_unit_sync"):
            for project in projects:
                self.env["ops.work.unit"]._ops_sync_project_units_from_profile(project)
        return projects

    def write(self, vals):
        vals = self._ops_prepare_unit_vals(vals)
        result = super().write(vals)
        if not self.env.context.get("skip_ops_unit_sync"):
            for project in self:
                self.env["ops.work.unit"]._ops_sync_project_units_from_profile(project)
        return result

    @api.constrains(
        "ops_track_quantity",
        "ops_planned_quantity",
        "ops_allowed_unit_ids",
        "ops_default_unit_id",
        "ops_measurement_unit_id",
    )
    def _check_ops_work_unit_configuration(self):
        for project in self:
            allowed_units = project.ops_allowed_unit_ids or project.ops_profile_allowed_unit_ids
            if project.ops_default_unit_id and allowed_units and project.ops_default_unit_id not in allowed_units:
                raise ValidationError(_("Үндсэн нэгж нь зөвшөөрөгдсөн нэгжүүдийн жагсаалтад байх ёстой."))
            if (
                project.ops_measurement_unit_id
                and allowed_units
                and project.ops_measurement_unit_id not in allowed_units
            ):
                raise ValidationError(_("Сонгосон хэмжих нэгж энэ ажилд зөвшөөрөгдсөн нэгжүүдийн дотор байх ёстой."))
            if project.ops_track_quantity and not project.ops_measurement_unit_id:
                raise ValidationError(_("Хэмжих нэгж сонгоно уу."))
