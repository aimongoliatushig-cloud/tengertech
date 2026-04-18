from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command

from .common import (
    MFO_SHARED_FIELD_GROUPS,
    OPERATION_TYPE_SELECTION,
    SHIFT_TYPE_SELECTION,
    monday_for,
)


DEFAULT_STAGE_MAP = [
    ("planned", "Төлөвлөгдсөн", 1, False),
    ("dispatched", "Хуваарилсан", 10, False),
    ("in_progress", "Гүйцэтгэж байна", 20, False),
    ("review", "Шалгаж байна", 30, False),
    ("done", "Дууссан", 40, True),
]


class ProjectProject(models.Model):
    _inherit = "project.project"

    mfo_is_operation_project = fields.Boolean(
        string="Хотын талбайн ажиллагааны төсөл",
        default=False,
        tracking=True,
        groups=MFO_SHARED_FIELD_GROUPS,
    )
    mfo_operation_type = fields.Selection(
        selection=OPERATION_TYPE_SELECTION,
        string="Ажиллагааны төрөл",
        default="garbage",
        required=True,
        tracking=True,
        groups=MFO_SHARED_FIELD_GROUPS,
    )
    mfo_district_ids = fields.Many2many(
        "mfo.district",
        "mfo_project_district_rel",
        "project_id",
        "district_id",
        string="Хариуцах дүүргүүд",
        groups=MFO_SHARED_FIELD_GROUPS,
    )
    mfo_district_names = fields.Char(
        string="Дүүрэг",
        compute="_compute_mfo_district_names",
        groups=MFO_SHARED_FIELD_GROUPS,
    )
    mfo_default_shift_type = fields.Selection(
        selection=SHIFT_TYPE_SELECTION,
        string="Анхны ээлж",
        default="morning",
        groups=MFO_SHARED_FIELD_GROUPS,
    )
    mfo_default_shift_start = fields.Float(
        string="Ээлж эхлэх цаг",
        default=6.0,
        groups=MFO_SHARED_FIELD_GROUPS,
    )
    mfo_default_shift_end = fields.Float(
        string="Ээлж дуусах цаг",
        default=14.0,
        groups=MFO_SHARED_FIELD_GROUPS,
    )
    mfo_route_ids = fields.One2many(
        "mfo.route",
        "project_id",
        string="Маршрутууд",
        groups=MFO_SHARED_FIELD_GROUPS,
    )
    mfo_planning_template_ids = fields.One2many(
        "mfo.planning.template",
        "project_id",
        string="7 хоногийн загварууд",
        groups=MFO_SHARED_FIELD_GROUPS,
    )
    mfo_route_count = fields.Integer(
        string="Маршрутын тоо",
        compute="_compute_mfo_counts",
        groups=MFO_SHARED_FIELD_GROUPS,
    )
    mfo_planning_template_count = fields.Integer(
        string="Загварын тоо",
        compute="_compute_mfo_counts",
        groups=MFO_SHARED_FIELD_GROUPS,
    )

    @api.depends("mfo_district_ids.name")
    def _compute_mfo_district_names(self):
        for project in self:
            project.mfo_district_names = ", ".join(project.mfo_district_ids.mapped("name"))

    @api.depends("mfo_route_ids", "mfo_planning_template_ids")
    def _compute_mfo_counts(self):
        for project in self:
            project.mfo_route_count = len(project.mfo_route_ids)
            project.mfo_planning_template_count = len(project.mfo_planning_template_ids)

    def _mfo_ensure_default_stages(self):
        Stage = self.env["project.task.type"].sudo()
        for project in self.filtered("mfo_is_operation_project"):
            if project.type_ids:
                continue
            stage_ids = []
            for code, name, sequence, fold in DEFAULT_STAGE_MAP:
                stage = Stage.create(
                    {
                        "name": name,
                        "sequence": sequence,
                        "fold": fold,
                        "mfo_stage_code": code,
                        "project_ids": [Command.link(project.id)],
                    }
                )
                stage_ids.append(stage.id)
            project.type_ids = [Command.set(stage_ids)]

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        projects._mfo_ensure_default_stages()
        return projects

    def write(self, vals):
        result = super().write(vals)
        if vals.get("mfo_is_operation_project"):
            self._mfo_ensure_default_stages()
        return result

    def action_mfo_generate_current_week_tasks(self):
        week_start = monday_for(fields.Date.to_date(fields.Date.context_today(self)))
        total_count = 0
        for project in self:
            templates = project.mfo_planning_template_ids.filtered("active")
            if not templates:
                raise UserError(_("Энэ төсөл дээр идэвхтэй 7 хоногийн загвар алга байна."))
            for template in templates:
                total_count += template._generate_tasks_for_week(week_start)
            project.message_post(
                body=_("%(date)s эхлэх 7 хоногт %(count)s өдөр тутмын даалгавар үүсгэлээ.")
                % {
                    "date": fields.Date.to_string(week_start),
                    "count": total_count,
                }
            )
        return True

    def action_mfo_open_new_planning_template(self):
        self.ensure_one()
        view = self.env.ref("municipal_field_ops.view_mfo_planning_template_form", raise_if_not_found=False)
        return {
            "name": _("Шинэ 7 хоногийн загвар"),
            "type": "ir.actions.act_window",
            "res_model": "mfo.planning.template",
            "view_mode": "form",
            "views": [(view.id, "form")] if view else [(False, "form")],
            "target": "new",
            "context": {
                "default_project_id": self.id,
                "default_reference_date": fields.Date.context_today(self),
                "default_name": _("%s - 7 хоногийн загвар") % self.name,
            },
        }
