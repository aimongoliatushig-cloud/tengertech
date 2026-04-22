import re

from odoo import _, api, fields, models
from odoo.addons.municipal_field_ops.models.common import OPERATION_TYPE_SELECTION
from odoo.exceptions import ValidationError


UNIT_CATEGORY_SELECTION = [
    ("count", "Тоо ширхэг"),
    ("weight", "Жин"),
    ("distance", "Зай"),
    ("area", "Талбай"),
    ("volume", "Эзлэхүүн"),
    ("trip", "Давтамж"),
    ("point", "Цэг"),
    ("vehicle", "Тээврийн хэрэгсэл"),
    ("tree", "Мод"),
    ("other", "Бусад"),
]

LEGACY_UNIT_ALIASES = {
    "pcs": ["ширхэг", "ш", "шир", "pcs", "pc", "piece", "pieces"],
    "kg": ["кг", "kg", "kilogram", "kilograms"],
    "tn": ["тн", "tn", "ton", "tons", "tonne", "tonnes"],
    "m": ["м", "m", "metr", "meter", "meters", "metre", "metres"],
    "km": ["км", "km", "kilometer", "kilometers", "kilometre", "kilometres"],
    "m2": ["м2", "m2", "м²", "m²", "мкв", "квм", "sqm", "sqmeter", "squaremeter"],
    "m3": [
        "м3",
        "m3",
        "м³",
        "m³",
        "мкуб",
        "мкубметр",
        "кубм",
        "кубметр",
        "mcube",
        "cubicmeter",
        "м куб",
    ],
    "liter": ["литр", "л", "liter", "liters", "litre", "litres", "ltr"],
    "times": ["удаа", "рейс", "times", "trip", "trips"],
    "point": ["цэг", "point", "points", "stop", "stops"],
    "vehicle": ["машин", "vehicle", "vehicles", "truck", "trucks"],
    "tree": ["мод", "mod", "tree", "trees"],
}


def normalize_unit_text(value):
    if not value:
        return ""
    normalized = (value or "").strip().lower()
    normalized = normalized.replace("²", "2").replace("³", "3").replace("ё", "е")
    normalized = re.sub(r"[\s._-]+", "", normalized)
    return normalized


ALIAS_CODE_MAP = {
    normalize_unit_text(alias): code
    for code, aliases in LEGACY_UNIT_ALIASES.items()
    for alias in aliases
}


class OpsWorkUnit(models.Model):
    _name = "ops.work.unit"
    _description = "Ажлын хэмжих нэгж"
    _order = "sequence, name, id"

    name = fields.Char(string="Нэр", required=True)
    code = fields.Char(string="Код", required=True)
    category = fields.Selection(
        selection=UNIT_CATEGORY_SELECTION,
        string="Ангилал",
        required=True,
        default="count",
    )
    sequence = fields.Integer(string="Дараалал", default=10)
    active = fields.Boolean(string="Идэвхтэй", default=True)

    _name_unique = models.Constraint(
        "unique(name)",
        "Хэмжих нэгжийн нэр давхцахгүй байна.",
    )
    _code_unique = models.Constraint(
        "unique(code)",
        "Хэмжих нэгжийн код давхцахгүй байна.",
    )

    @api.constrains("code")
    def _check_code(self):
        for unit in self:
            if normalize_unit_text(unit.code) != unit.code.strip().lower():
                raise ValidationError(_("Кодыг жижиг латин тэмдэгтээр, зайгүй хадгална уу."))

    @api.model
    def _ops_find_unit_from_text(self, value):
        normalized = normalize_unit_text(value)
        if not normalized:
            return self.browse()

        alias_code = ALIAS_CODE_MAP.get(normalized)
        if alias_code:
            unit = self.search([("code", "=", alias_code)], limit=1)
            if unit:
                return unit

        units = self.search([])
        return units.filtered(
            lambda unit: normalize_unit_text(unit.name) == normalized
            or normalize_unit_text(unit.code) == normalized
        )[:1]

    @api.model
    def _ops_get_work_type_profile_map(self):
        profiles = self.env["ops.work.type"].sudo().search([], order="sequence asc, id asc")
        return {profile.operation_type: profile for profile in profiles}

    @api.model
    def _ops_build_review_vals(self, model_name, record_id, field_name, raw_value):
        return {
            "model_name": model_name,
            "res_id": record_id,
            "field_name": field_name,
            "raw_value": raw_value,
            "normalized_key": normalize_unit_text(raw_value),
        }

    @api.model
    def _ops_sync_project_units_from_profile(self, project):
        profile = self._ops_get_work_type_profile_map().get(project.mfo_operation_type)
        updates = {}
        allowed = project.ops_allowed_unit_ids

        if not allowed and profile and profile.allowed_unit_ids:
            allowed = profile.allowed_unit_ids
            updates["ops_allowed_unit_ids"] = [fields.Command.set(allowed.ids)]

        if project.ops_default_unit_id and allowed and project.ops_default_unit_id not in allowed:
            allowed |= project.ops_default_unit_id
            updates["ops_allowed_unit_ids"] = [fields.Command.set(allowed.ids)]

        if project.ops_measurement_unit_id and allowed and project.ops_measurement_unit_id not in allowed:
            allowed |= project.ops_measurement_unit_id
            updates["ops_allowed_unit_ids"] = [fields.Command.set(allowed.ids)]

        default_unit = project.ops_default_unit_id
        if not default_unit:
            if profile and profile.default_unit_id and (
                not allowed or profile.default_unit_id in allowed
            ):
                default_unit = profile.default_unit_id
            elif allowed:
                default_unit = allowed[:1]
            if default_unit:
                updates["ops_default_unit_id"] = default_unit.id

        if project.ops_track_quantity:
            measurement_unit = project.ops_measurement_unit_id or default_unit
            if measurement_unit:
                updates["ops_measurement_unit_id"] = measurement_unit.id
                updates["ops_measurement_unit"] = measurement_unit.name
        elif project.ops_measurement_unit_id or project.ops_measurement_unit:
            updates["ops_measurement_unit_id"] = False
            updates["ops_measurement_unit"] = False

        if updates:
            if project.id:
                project.with_context(skip_ops_unit_sync=True).write(updates)
            else:
                if "ops_allowed_unit_ids" in updates:
                    project.ops_allowed_unit_ids = self.env["ops.work.unit"].browse(
                        updates["ops_allowed_unit_ids"][0][2]
                    )
                if "ops_default_unit_id" in updates:
                    project.ops_default_unit_id = updates["ops_default_unit_id"]
                if "ops_measurement_unit_id" in updates:
                    project.ops_measurement_unit_id = updates["ops_measurement_unit_id"]
                if "ops_measurement_unit" in updates:
                    project.ops_measurement_unit = updates["ops_measurement_unit"]

    @api.model
    def _ops_sync_task_units_from_project(self, task):
        updates = {}
        allowed = task.project_id.ops_allowed_unit_ids
        default_unit = task.project_id.ops_default_unit_id or allowed[:1]

        if task.ops_measurement_unit_id and allowed and task.ops_measurement_unit_id not in allowed:
            if default_unit:
                updates["ops_measurement_unit_id"] = default_unit.id
                updates["ops_measurement_unit"] = default_unit.name

        if not task.ops_measurement_unit_id and default_unit:
            requires_default = bool(
                task.ops_planned_quantity > 0
                or task.project_id.ops_track_quantity
                or task.mfo_is_operation_project
                or (task.ops_measurement_unit or "").strip()
            )
            if requires_default:
                updates["ops_measurement_unit_id"] = default_unit.id
                updates["ops_measurement_unit"] = default_unit.name

        if updates:
            if task.id:
                task.with_context(skip_ops_unit_sync=True).write(updates)
            else:
                if "ops_measurement_unit_id" in updates:
                    task.ops_measurement_unit_id = updates["ops_measurement_unit_id"]
                if "ops_measurement_unit" in updates:
                    task.ops_measurement_unit = updates["ops_measurement_unit"]

    @api.model
    def _ops_run_legacy_unit_migration(self):
        project_model = self.env["project.project"].sudo().with_context(active_test=False)
        task_model = self.env["project.task"].sudo().with_context(active_test=False)
        review_model = self.env["ops.work.unit.review"].sudo()
        review_index = {
            (item.model_name, item.res_id, item.field_name, item.raw_value): item
            for item in review_model.search([])
        }
        profile_map = self._ops_get_work_type_profile_map()

        for project in project_model.search([]):
            updates = {}
            raw_value = (project.ops_measurement_unit or "").strip()
            mapped_unit = project.ops_measurement_unit_id

            if raw_value and not mapped_unit:
                mapped_unit = self._ops_find_unit_from_text(raw_value)
                if mapped_unit:
                    updates["ops_measurement_unit_id"] = mapped_unit.id
                    updates["ops_measurement_unit"] = mapped_unit.name
                else:
                    key = ("project.project", project.id, "ops_measurement_unit", raw_value)
                    if key not in review_index:
                        review_index[key] = review_model.create(self._ops_build_review_vals(*key))

            if not project.ops_allowed_unit_ids:
                profile = profile_map.get(project.mfo_operation_type)
                if profile and profile.allowed_unit_ids:
                    updates["ops_allowed_unit_ids"] = [fields.Command.set(profile.allowed_unit_ids.ids)]

            allowed_ids = set(project.ops_allowed_unit_ids.ids)
            if not allowed_ids:
                profile = profile_map.get(project.mfo_operation_type)
                if profile:
                    allowed_ids = set(profile.allowed_unit_ids.ids)
            if mapped_unit and mapped_unit.id not in allowed_ids:
                allowed_ids.add(mapped_unit.id)
                updates["ops_allowed_unit_ids"] = [fields.Command.set(sorted(allowed_ids))]

            if not project.ops_default_unit_id:
                profile = profile_map.get(project.mfo_operation_type)
                candidate = mapped_unit or (profile.default_unit_id if profile else False)
                if candidate:
                    updates["ops_default_unit_id"] = candidate.id

            if updates:
                project.with_context(skip_ops_unit_sync=True).write(updates)

        for task in task_model.search([]):
            updates = {}
            raw_value = (task.ops_measurement_unit or "").strip()
            mapped_unit = task.ops_measurement_unit_id

            if raw_value and not mapped_unit:
                mapped_unit = self._ops_find_unit_from_text(raw_value)
                if mapped_unit:
                    updates["ops_measurement_unit_id"] = mapped_unit.id
                    updates["ops_measurement_unit"] = mapped_unit.name
                else:
                    key = ("project.task", task.id, "ops_measurement_unit", raw_value)
                    if key not in review_index:
                        review_index[key] = review_model.create(self._ops_build_review_vals(*key))

            if mapped_unit and task.project_id:
                allowed_ids = set(task.project_id.ops_allowed_unit_ids.ids)
                if mapped_unit.id not in allowed_ids:
                    allowed_ids.add(mapped_unit.id)
                    task.project_id.with_context(skip_ops_unit_sync=True).write(
                        {"ops_allowed_unit_ids": [fields.Command.set(sorted(allowed_ids))]}
                    )
                if not task.project_id.ops_default_unit_id:
                    task.project_id.with_context(skip_ops_unit_sync=True).write(
                        {"ops_default_unit_id": mapped_unit.id}
                    )

            if not mapped_unit and task.project_id.ops_default_unit_id:
                updates["ops_measurement_unit_id"] = task.project_id.ops_default_unit_id.id
                updates["ops_measurement_unit"] = task.project_id.ops_default_unit_id.name

            if updates:
                task.with_context(skip_ops_unit_sync=True).write(updates)

        for project in project_model.search([]):
            self._ops_sync_project_units_from_profile(project)
        for task in task_model.search([]):
            self._ops_sync_task_units_from_project(task)


class OpsWorkType(models.Model):
    _name = "ops.work.type"
    _description = "Ажлын төрлийн нэгжийн профайл"
    _order = "sequence, name, id"

    name = fields.Char(string="Нэр", required=True)
    operation_type = fields.Selection(
        selection=OPERATION_TYPE_SELECTION,
        string="Ажлын төрөл",
        required=True,
    )
    allowed_unit_ids = fields.Many2many(
        "ops.work.unit",
        "ops_work_type_allowed_unit_rel",
        "work_type_id",
        "unit_id",
        string="Зөвшөөрөгдсөн нэгжүүд",
    )
    default_unit_id = fields.Many2one("ops.work.unit", string="Үндсэн нэгж")
    allowed_unit_summary = fields.Char(
        string="Боломжтой нэгжүүд",
        compute="_compute_allowed_unit_summary",
    )
    sequence = fields.Integer(string="Дараалал", default=10)
    active = fields.Boolean(string="Идэвхтэй", default=True)

    _operation_type_unique = models.Constraint(
        "unique(operation_type)",
        "Нэг ажлын төрөлд нэг л unit профайл байна.",
    )

    @api.depends("allowed_unit_ids.name")
    def _compute_allowed_unit_summary(self):
        for profile in self:
            profile.allowed_unit_summary = ", ".join(profile.allowed_unit_ids.mapped("name"))

    @api.constrains("default_unit_id", "allowed_unit_ids")
    def _check_default_unit_allowed(self):
        for profile in self:
            if profile.default_unit_id and profile.default_unit_id not in profile.allowed_unit_ids:
                raise ValidationError(_("Үндсэн нэгж нь зөвшөөрөгдсөн нэгжүүдийн жагсаалтад байх ёстой."))


class OpsWorkUnitReview(models.Model):
    _name = "ops.work.unit.review"
    _description = "Хэмжих нэгжийн migration шалгах мөр"
    _order = "create_date desc, id desc"

    name = fields.Char(string="Нэр", compute="_compute_name", store=True)
    model_name = fields.Char(string="Model", required=True)
    res_id = fields.Integer(string="Бичлэгийн ID", required=True)
    field_name = fields.Char(string="Талбар", required=True)
    raw_value = fields.Char(string="Анхны утга", required=True)
    normalized_key = fields.Char(string="Харьцуулах түлхүүр")
    state = fields.Selection(
        selection=[
            ("pending", "Шалгах"),
            ("resolved", "Шийдсэн"),
            ("ignored", "Алгассан"),
        ],
        string="Төлөв",
        default="pending",
        required=True,
    )
    note = fields.Text(string="Тэмдэглэл")

    _review_row_unique = models.Constraint(
        "unique(model_name, res_id, field_name, raw_value)",
        "Ижил migration шалгах мөр давхардахгүй байна.",
    )

    @api.depends("model_name", "res_id", "raw_value")
    def _compute_name(self):
        for item in self:
            item.name = "%s #%s - %s" % (
                item.model_name or "record",
                item.res_id or 0,
                item.raw_value or _("Нэгжгүй"),
            )
