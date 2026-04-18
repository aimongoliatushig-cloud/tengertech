import json
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .common import (
    PLANNING_OVERRIDE_SELECTION,
    SHIFT_TYPE_SELECTION,
    SYNC_STATE_SELECTION,
    SYNC_TYPE_SELECTION,
    WEEKDAY_SELECTION,
    combine_date_float_hours,
    monday_for,
)


class MfoPlanningTemplate(models.Model):
    _name = "mfo.planning.template"
    _description = "7 хоногийн төлөвлөлтийн загвар"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "project_id, name"

    name = fields.Char(string="Нэр", required=True, tracking=True)
    active = fields.Boolean(string="Идэвхтэй", default=True, tracking=True)
    project_id = fields.Many2one(
        "project.project",
        string="Төсөл",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    operation_type = fields.Selection(
        related="project_id.mfo_operation_type",
        string="Ажиллагааны төрөл",
        store=True,
        readonly=True,
    )
    reference_date = fields.Date(
        string="Үүсгэх долоо хоногийн огноо",
        default=fields.Date.today,
    )
    last_generated_week_start = fields.Date(
        string="Сүүлд үүсгэсэн 7 хоног",
        readonly=True,
        tracking=True,
    )
    last_generated_count = fields.Integer(
        string="Сүүлд үүсгэсэн тоо",
        readonly=True,
    )
    line_ids = fields.One2many(
        "mfo.planning.template.line",
        "template_id",
        string="Төлөвлөлтийн мөрүүд",
    )
    override_ids = fields.One2many(
        "mfo.planning.override",
        "template_id",
        string="Өдрийн өөрчлөлтүүд",
    )
    note = fields.Text(string="Тайлбар")

    def _get_override_for_line(self, line, shift_date):
        self.ensure_one()
        return self.override_ids.filtered(
            lambda item: item.active
            and item.template_line_id == line
            and item.override_date == shift_date
        )[:1]

    def _generate_tasks_for_week(self, week_start):
        Task = self.env["project.task"]
        total_created = 0
        for template in self:
            template_created = 0
            for line in template.line_ids:
                shift_date = week_start + timedelta(days=int(line.weekday or "0"))
                override = template._get_override_for_line(line, shift_date)
                if Task.search_count(
                    [
                        ("project_id", "=", template.project_id.id),
                        ("mfo_planning_template_line_id", "=", line.id),
                        ("mfo_shift_date", "=", shift_date),
                    ]
                ):
                    continue
                if override and override.override_type in {"off_day", "cancel_generation"}:
                    continue
                Task.create(line._prepare_task_values(shift_date, override=override))
                total_created += 1
                template_created += 1
            template.write(
                {
                    "last_generated_week_start": week_start,
                    "last_generated_count": template_created,
                }
            )
        return total_created

    def action_generate_tasks_for_reference_week(self):
        for template in self:
            week_start = monday_for(
                fields.Date.to_date(template.reference_date or fields.Date.context_today(template))
            )
            created_count = template._generate_tasks_for_week(week_start)
            template.message_post(
                body=_(
                    "%(date)s эхлэх 7 хоногт %(count)s өдөр тутмын даалгавар үүсгэлээ."
                )
                % {"date": fields.Date.to_string(week_start), "count": created_count}
            )
        return True


class MfoPlanningTemplateLine(models.Model):
    _name = "mfo.planning.template.line"
    _description = "7 хоногийн төлөвлөлтийн мөр"
    _order = "template_id, weekday, sequence, id"

    template_id = fields.Many2one(
        "mfo.planning.template",
        string="Загвар",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Дараалал", default=10)
    weekday = fields.Selection(
        selection=WEEKDAY_SELECTION,
        string="Гараг",
        required=True,
        default="0",
    )
    route_id = fields.Many2one(
        "mfo.route",
        string="Маршрут",
        domain="[('project_id', '=', template_id.project_id)]",
        ondelete="restrict",
    )
    district_id = fields.Many2one(
        "mfo.district",
        string="Дүүрэг",
        compute="_compute_district_id",
        store=True,
    )
    shift_type = fields.Selection(
        selection=SHIFT_TYPE_SELECTION,
        string="Ээлж",
        default="morning",
        required=True,
    )
    planned_start_hour = fields.Float(string="Эхлэх цаг")
    planned_end_hour = fields.Float(string="Дуусах цаг")
    crew_team_id = fields.Many2one(
        "mfo.crew.team",
        string="Экипаж",
        ondelete="restrict",
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Техник",
        domain="[('mfo_active_for_ops', '=', True)]",
        ondelete="restrict",
    )
    driver_employee_id = fields.Many2one(
        "hr.employee",
        string="Жолооч",
        domain="[('mfo_is_field_active', '=', True), ('mfo_field_role', '=', 'driver')]",
        ondelete="restrict",
    )
    collector_employee_ids = fields.Many2many(
        "hr.employee",
        "mfo_plan_line_collector_rel",
        "planning_line_id",
        "employee_id",
        string="Ачигчид",
        domain="[('mfo_is_field_active', '=', True), ('mfo_field_role', '=', 'collector')]",
    )
    inspector_employee_id = fields.Many2one(
        "hr.employee",
        string="Хянагч",
        domain="[('mfo_is_field_active', '=', True), ('mfo_field_role', '=', 'inspector')]",
        ondelete="restrict",
    )
    expected_stop_count = fields.Integer(
        string="Төлөвлөсөн цэг",
        compute="_compute_expected_stop_count",
    )
    override_ids = fields.One2many(
        "mfo.planning.override",
        "template_line_id",
        string="Өдрийн өөрчлөлтүүд",
    )
    note = fields.Char(string="Тайлбар")

    @api.depends("route_id.district_id")
    def _compute_district_id(self):
        for line in self:
            line.district_id = line.route_id.district_id

    @api.depends("route_id.line_ids")
    def _compute_expected_stop_count(self):
        for line in self:
            line.expected_stop_count = len(line.route_id.line_ids)

    @api.onchange("crew_team_id")
    def _onchange_crew_team_id(self):
        for line in self:
            if not line.crew_team_id:
                continue
            line.vehicle_id = line.crew_team_id.vehicle_id
            line.driver_employee_id = line.crew_team_id.driver_employee_id
            line.collector_employee_ids = line.crew_team_id.collector_employee_ids
            line.inspector_employee_id = line.crew_team_id.inspector_employee_id

    @api.constrains("template_id", "route_id")
    def _check_route_project_match(self):
        for line in self:
            if line.route_id and line.route_id.project_id != line.template_id.project_id:
                raise ValidationError(_("Маршрут нь загварын төсөлтэй таарах ёстой."))

    def _mfo_build_task_name(self, route, shift_date):
        self.ensure_one()
        route_name = route.name or _("Маршрутгүй")
        return _("%(route)s - %(date)s") % {
            "route": route_name,
            "date": fields.Date.to_string(shift_date),
        }

    def _prepare_task_values(self, shift_date, override=False):
        self.ensure_one()
        project = self.template_id.project_id
        route = self.route_id
        shift_type = self.shift_type or project.mfo_default_shift_type
        planned_start_hour = self.planned_start_hour or project.mfo_default_shift_start
        planned_end_hour = self.planned_end_hour or project.mfo_default_shift_end
        crew_team = self.crew_team_id
        vehicle = self.vehicle_id
        driver = self.driver_employee_id
        collectors = self.collector_employee_ids
        inspector = self.inspector_employee_id
        note = self.note or False

        if override:
            if override.override_type == "route_swap" and override.route_id:
                route = override.route_id
            elif override.override_type == "vehicle_swap" and override.vehicle_id:
                vehicle = override.vehicle_id
            elif override.override_type == "crew_swap" and override.crew_team_id:
                crew_team = override.crew_team_id
                vehicle = override.crew_team_id.vehicle_id or vehicle
                driver = override.crew_team_id.driver_employee_id or driver
                collectors = override.crew_team_id.collector_employee_ids or collectors
                inspector = override.crew_team_id.inspector_employee_id or inspector
            if override.note:
                note = override.note

        start_dt = combine_date_float_hours(shift_date, planned_start_hour)
        end_dt = combine_date_float_hours(shift_date, planned_end_hour)
        return {
            "name": self._mfo_build_task_name(route, shift_date),
            "project_id": project.id,
            "mfo_shift_date": shift_date,
            "mfo_shift_type": shift_type,
            "mfo_route_id": route.id,
            "mfo_district_id": route.district_id.id,
            "mfo_planned_start": fields.Datetime.to_string(start_dt) if start_dt else False,
            "mfo_planned_end": fields.Datetime.to_string(end_dt) if end_dt else False,
            "mfo_crew_team_id": crew_team.id,
            "mfo_vehicle_id": vehicle.id,
            "mfo_driver_employee_id": driver.id,
            "mfo_collector_employee_ids": [fields.Command.set(collectors.ids)],
            "mfo_inspector_employee_id": inspector.id,
            "mfo_planning_template_line_id": self.id,
            "mfo_end_shift_summary": note,
        }


class MfoPlanningOverride(models.Model):
    _name = "mfo.planning.override"
    _description = "Өдрийн төлөвлөлтийн өөрчлөлт"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "override_date desc, template_line_id, id desc"

    name = fields.Char(
        string="Нэр",
        compute="_compute_name",
        store=True,
    )
    active = fields.Boolean(string="Идэвхтэй", default=True, tracking=True)
    template_line_id = fields.Many2one(
        "mfo.planning.template.line",
        string="Загварын мөр",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    template_id = fields.Many2one(
        "mfo.planning.template",
        string="Загвар",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    project_id = fields.Many2one(
        "project.project",
        string="Төсөл",
        related="template_id.project_id",
        store=True,
        readonly=True,
    )
    override_date = fields.Date(
        string="Өөрчлөх огноо",
        required=True,
        tracking=True,
        index=True,
    )
    override_type = fields.Selection(
        selection=PLANNING_OVERRIDE_SELECTION,
        string="Өөрчлөлтийн төрөл",
        required=True,
        default="route_swap",
        tracking=True,
    )
    route_id = fields.Many2one(
        "mfo.route",
        string="Шинэ маршрут",
        domain="[('project_id', '=', project_id)]",
        ondelete="restrict",
    )
    crew_team_id = fields.Many2one(
        "mfo.crew.team",
        string="Шинэ экипаж",
        ondelete="restrict",
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Шинэ техник",
        domain="[('mfo_active_for_ops', '=', True)]",
        ondelete="restrict",
    )
    note = fields.Char(string="Тэмдэглэл")

    _sql_constraints = [
        (
            "mfo_planning_override_unique_line_date",
            "unique(template_line_id, override_date)",
            "Нэг загварын мөрт нэг өдөрт зөвхөн нэг өөрчлөлт бүртгэнэ.",
        )
    ]

    @api.depends("template_line_id.route_id.name", "override_date", "override_type")
    def _compute_name(self):
        selection_map = dict(PLANNING_OVERRIDE_SELECTION)
        for override in self:
            route_name = override.template_line_id.route_id.name or _("Маршрутгүй")
            type_name = selection_map.get(override.override_type, override.override_type)
            date_name = fields.Date.to_string(override.override_date) if override.override_date else _("Огноогүй")
            override.name = f"{route_name} / {date_name} / {type_name}"

    @api.onchange("template_line_id")
    def _onchange_template_line_id(self):
        for override in self:
            if override.template_line_id:
                override.template_id = override.template_line_id.template_id

    @api.constrains("template_id", "template_line_id")
    def _check_template_line_belongs_to_template(self):
        for override in self:
            if override.template_line_id and override.template_line_id.template_id != override.template_id:
                raise ValidationError(_("Өөрчлөлтийн мөр нь сонгосон загварт хамаарах ёстой."))

    @api.constrains("override_type", "route_id", "vehicle_id", "crew_team_id")
    def _check_required_swap_values(self):
        for override in self:
            if override.override_type == "route_swap" and not override.route_id:
                raise ValidationError(_("Маршрут солих өөрчлөлтөнд шинэ маршрут заавал сонгоно."))
            if override.override_type == "vehicle_swap" and not override.vehicle_id:
                raise ValidationError(_("Техник солих өөрчлөлтөнд шинэ техник заавал сонгоно."))
            if override.override_type == "crew_swap" and not override.crew_team_id:
                raise ValidationError(_("Экипаж солих өөрчлөлтөнд шинэ экипаж заавал сонгоно."))


class MfoSyncLog(models.Model):
    _name = "mfo.sync.log"
    _description = "Гадаад синк лог"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Нэр", required=True, default=lambda self: _("Пүүгийн синк"))
    sync_type = fields.Selection(
        selection=SYNC_TYPE_SELECTION,
        string="Синк төрөл",
        default="weighbridge",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=SYNC_STATE_SELECTION,
        string="Төлөв",
        default="draft",
        required=True,
        tracking=True,
    )
    task_id = fields.Many2one(
        "project.task",
        string="Холбогдох даалгавар",
        ondelete="set null",
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Техник",
        ondelete="set null",
    )
    requested_at = fields.Datetime(string="Эхэлсэн огноо", tracking=True)
    finished_at = fields.Datetime(string="Дууссан огноо", tracking=True)
    external_reference = fields.Char(string="Гадаад лавлагаа")
    result_count = fields.Integer(string="Оруулсан мөр")
    payload_excerpt = fields.Text(string="Хүсэлтийн хэсэг")
    response_excerpt = fields.Text(string="Хариуны хэсэг")
    error_message = fields.Text(string="Алдааны мэдээлэл")

    @api.model
    def cron_sync_weight_measurements(self):
        target_date = fields.Date.context_today(self)
        log = self.create(
            {
                "name": _("Автомат пүүгийн синк"),
                "sync_type": "weighbridge",
                "state": "running",
                "requested_at": fields.Datetime.now(),
                "payload_excerpt": json.dumps(
                    {"shift_date": fields.Date.to_string(target_date)},
                    ensure_ascii=False,
                ),
            }
        )
        result_count = 0
        try:
            tasks = self.env["project.task"].search(
                [
                    ("mfo_operation_type", "=", "garbage"),
                    ("mfo_shift_date", "=", target_date),
                    ("mfo_vehicle_id", "!=", False),
                    ("mfo_state", "in", ["dispatched", "in_progress", "submitted", "verified"]),
                ],
                order="mfo_planned_start asc, id asc",
                limit=200,
            )
            for task in tasks:
                result_count += task.action_mfo_request_weight_sync(sync_log=log)
            log.write(
                {
                    "state": "warning" if not result_count else "success",
                    "finished_at": fields.Datetime.now(),
                    "result_count": result_count,
                    "response_excerpt": _(
                        "%(count)s мөрийн өдөр тутмын жингийн нийт синк хийгдлээ."
                    )
                    % {"count": result_count},
                }
            )
        except Exception as exc:
            log.write(
                {
                    "state": "failed",
                    "finished_at": fields.Datetime.now(),
                    "error_message": str(exc),
                }
            )
        return True
