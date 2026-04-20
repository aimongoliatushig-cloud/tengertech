import json
import os
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command

from .common import (
    ISSUE_SEVERITY_SELECTION,
    ISSUE_STATE_SELECTION,
    ISSUE_TYPE_SELECTION,
    MFO_SHARED_FIELD_GROUPS,
    OPERATION_TYPE_SELECTION,
    PROOF_TYPE_SELECTION,
    SHIFT_TYPE_SELECTION,
    STOP_STATE_SELECTION,
    TASK_STATE_SELECTION,
    combine_date_float_hours,
)


class ProjectTask(models.Model):
    _inherit = "project.task"

    mfo_is_route_point_task = fields.Boolean(
        string="Маршрутын цэгийн ажилбар",
        default=False,
        index=True,
    )
    mfo_source_route_line_id = fields.Many2one(
        "mfo.route.line",
        string="Эх маршрут мөр",
        readonly=True,
        ondelete="set null",
    )
    mfo_is_operation_project = fields.Boolean(
        string="Хотын ажиллагааны төсөл",
        related="project_id.mfo_is_operation_project",
        store=True,
        readonly=True,
    )
    mfo_operation_type = fields.Selection(
        selection=OPERATION_TYPE_SELECTION,
        string="Ажиллагааны төрөл",
        related="project_id.mfo_operation_type",
        store=True,
        readonly=True,
    )
    mfo_state = fields.Selection(
        selection=TASK_STATE_SELECTION,
        string="Талбайн төлөв",
        default="draft",
        tracking=True,
        index=True,
    )
    mfo_shift_date = fields.Date(
        string="Ээлжийн огноо",
        default=fields.Date.today,
        tracking=True,
        index=True,
    )
    mfo_shift_type = fields.Selection(
        selection=SHIFT_TYPE_SELECTION,
        string="Ээлж",
        default="morning",
        required=True,
        tracking=True,
    )
    mfo_route_id = fields.Many2one(
        "mfo.route",
        string="Маршрут",
        tracking=True,
    )
    mfo_route_line_id = fields.Many2one(
        "mfo.route.line",
        string="Маршрутын мөр",
        tracking=True,
        ondelete="set null",
    )
    mfo_collection_point_id = fields.Many2one(
        "mfo.collection.point",
        string="Цэг",
        tracking=True,
        ondelete="restrict",
    )
    mfo_district_id = fields.Many2one(
        "mfo.district",
        string="Дүүрэг",
        tracking=True,
    )
    mfo_subdistrict_id = fields.Many2one(
        "mfo.subdistrict",
        string="Хороо",
        tracking=True,
    )
    mfo_subdistrict_ids = fields.Many2many(
        "mfo.subdistrict",
        "mfo_task_subdistrict_rel",
        "task_id",
        "subdistrict_id",
        string="Khoroos",
        tracking=True,
    )
    mfo_crew_team_id = fields.Many2one(
        "mfo.crew.team",
        string="Экипаж",
        tracking=True,
    )
    mfo_vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Техник",
        domain="[('mfo_active_for_ops', '=', True)]",
        tracking=True,
    )
    mfo_vehicle_ids = fields.Many2many(
        "fleet.vehicle",
        "mfo_task_vehicle_rel",
        "task_id",
        "vehicle_id",
        string="Vehicles",
        tracking=True,
    )
    mfo_driver_employee_id = fields.Many2one(
        "hr.employee",
        string="Жолооч",
        tracking=True,
    )
    mfo_collector_employee_ids = fields.Many2many(
        "hr.employee",
        "mfo_task_collector_rel",
        "task_id",
        "employee_id",
        string="Ачигчид",
        tracking=True,
    )
    mfo_inspector_employee_id = fields.Many2one(
        "hr.employee",
        string="Хянагч",
        tracking=True,
    )
    mfo_driver_name = fields.Char(
        string="Жолооч",
        compute="_compute_mfo_assignment_names",
    )
    mfo_collector_names = fields.Char(
        string="Ачигчид",
        compute="_compute_mfo_assignment_names",
    )
    mfo_inspector_name = fields.Char(
        string="Хянагч",
        compute="_compute_mfo_assignment_names",
    )
    mfo_planned_start = fields.Datetime(string="Төлөвлөсөн эхлэх цаг", tracking=True)
    mfo_planned_end = fields.Datetime(string="Төлөвлөсөн дуусах цаг", tracking=True)
    mfo_dispatch_datetime = fields.Datetime(string="Хуваарилсан огноо", readonly=True, tracking=True)
    mfo_start_datetime = fields.Datetime(string="Эхэлсэн огноо", readonly=True, tracking=True)
    mfo_end_datetime = fields.Datetime(string="Дууссан огноо", readonly=True, tracking=True)
    mfo_end_shift_summary = fields.Text(string="Ээлжийн тайлан")
    mfo_planning_template_line_id = fields.Many2one(
        "mfo.planning.template.line",
        string="Үүсгэсэн загварын мөр",
        readonly=True,
    )
    mfo_is_emergency_reassignment = fields.Boolean(
        string="Яаралтай дахин хуваарилалт",
        default=False,
        tracking=True,
    )
    mfo_last_reassignment_reason = fields.Text(
        string="Сүүлчийн дахин хуваарилалтын шалтгаан",
        readonly=True,
    )
    mfo_last_sync_log_id = fields.Many2one(
        "mfo.sync.log",
        string="Сүүлчийн синк лог",
        readonly=True,
    )
    mfo_stop_line_ids = fields.One2many(
        "mfo.stop.execution.line",
        "task_id",
        string="Зогсоолын мөрүүд",
    )
    mfo_primary_stop_line_id = fields.Many2one(
        "mfo.stop.execution.line",
        string="Үндсэн цэгийн мөр",
        compute="_compute_mfo_primary_stop_line_id",
    )
    mfo_proof_image_ids = fields.One2many(
        "mfo.proof.image",
        "task_id",
        string="Баталгаажуулалтын зургууд",
    )
    mfo_weight_measurement_ids = fields.One2many(
        "mfo.weight.measurement",
        "task_id",
        string="Жингийн бүртгэлүүд",
    )
    mfo_daily_weight_total_ids = fields.One2many(
        "mfo.daily.weight.total",
        "task_id",
        string="Өдөр тутмын жингийн нийтүүд",
    )

    @api.onchange("project_id")
    def _onchange_project_id_mfo_route_domain(self):
        for task in self:
            if task.mfo_route_id and task.mfo_route_id.project_id != task.project_id:
                task.mfo_route_id = False
            return {
                "domain": {
                    "mfo_route_id": [("project_id", "=", task.project_id.id)] if task.project_id else []
                }
            }
    mfo_issue_ids = fields.One2many(
        "mfo.issue.report",
        "task_id",
        string="Асуудлууд",
    )
    mfo_stop_count = fields.Integer(string="Нийт цэг", compute="_compute_mfo_stop_metrics")
    mfo_completed_stop_count = fields.Integer(
        string="Гүйцэтгэсэн цэг",
        compute="_compute_mfo_stop_metrics",
    )
    mfo_skipped_stop_count = fields.Integer(
        string="Алгассан цэг",
        compute="_compute_mfo_stop_metrics",
    )
    mfo_progress_percent = fields.Float(
        string="Гүйцэтгэлийн хувь",
        compute="_compute_mfo_stop_metrics",
    )
    mfo_proof_count = fields.Integer(
        string="Зургийн тоо",
        compute="_compute_mfo_related_counters",
    )
    mfo_issue_count = fields.Integer(
        string="Асуудлын тоо",
        compute="_compute_mfo_related_counters",
    )
    mfo_weight_measurement_count = fields.Integer(
        string="Жингийн бичлэг",
        compute="_compute_mfo_related_counters",
    )
    mfo_total_net_weight = fields.Float(
        string="Цэвэр жин",
        compute="_compute_mfo_related_counters",
    )
    mfo_can_dispatch = fields.Boolean(compute="_compute_mfo_action_flags")
    mfo_can_start = fields.Boolean(compute="_compute_mfo_action_flags")
    mfo_can_submit = fields.Boolean(compute="_compute_mfo_action_flags")
    mfo_can_verify = fields.Boolean(compute="_compute_mfo_action_flags")
    mfo_can_reopen = fields.Boolean(compute="_compute_mfo_action_flags")

    @api.depends(
        "mfo_driver_employee_id.name",
        "mfo_collector_employee_ids.name",
        "mfo_inspector_employee_id.name",
    )
    def _compute_mfo_assignment_names(self):
        for task in self:
            task.mfo_driver_name = task.mfo_driver_employee_id.name or False
            task.mfo_collector_names = ", ".join(task.mfo_collector_employee_ids.mapped("name"))
            task.mfo_inspector_name = task.mfo_inspector_employee_id.name or False

    @api.depends("mfo_stop_line_ids.sequence")
    def _compute_mfo_primary_stop_line_id(self):
        for task in self:
            task.mfo_primary_stop_line_id = task.mfo_stop_line_ids.sorted(
                key=lambda line: (line.sequence, line.id)
            )[:1]

    @api.depends("mfo_stop_line_ids.status")
    def _compute_mfo_stop_metrics(self):
        for task in self:
            stops = task.mfo_stop_line_ids
            done_count = len(stops.filtered(lambda line: line.status == "done"))
            skipped_count = len(stops.filtered(lambda line: line.status == "skipped"))
            total = len(stops)
            task.mfo_stop_count = total
            task.mfo_completed_stop_count = done_count
            task.mfo_skipped_stop_count = skipped_count
            task.mfo_progress_percent = (done_count / total * 100.0) if total else 0.0

    @api.depends(
        "mfo_proof_image_ids",
        "mfo_issue_ids",
        "mfo_daily_weight_total_ids.net_weight_total",
        "mfo_weight_measurement_ids.net_weight",
    )
    def _compute_mfo_related_counters(self):
        for task in self:
            task.mfo_proof_count = len(task.mfo_proof_image_ids)
            task.mfo_issue_count = len(task.mfo_issue_ids)
            if task.mfo_daily_weight_total_ids:
                task.mfo_weight_measurement_count = len(task.mfo_daily_weight_total_ids)
                task.mfo_total_net_weight = sum(
                    task.mfo_daily_weight_total_ids.mapped("net_weight_total")
                )
            else:
                task.mfo_weight_measurement_count = len(task.mfo_weight_measurement_ids)
                task.mfo_total_net_weight = sum(task.mfo_weight_measurement_ids.mapped("net_weight"))

    @api.depends("mfo_state", "user_ids")
    @api.depends_context("uid")
    def _compute_mfo_action_flags(self):
        for task in self:
            if not task.mfo_is_operation_project or task.mfo_is_route_point_task:
                task.mfo_can_dispatch = False
                task.mfo_can_start = False
                task.mfo_can_submit = False
                task.mfo_can_verify = False
                task.mfo_can_reopen = False
                continue
            is_dispatcher = task._mfo_is_dispatcher_or_manager()
            is_assigned = task._mfo_is_assigned_user()
            is_verifier = task._mfo_is_verifier()
            task.mfo_can_dispatch = is_dispatcher and task.mfo_state in {"draft"}
            task.mfo_can_start = (is_dispatcher or is_assigned) and task.mfo_state in {
                "draft",
                "dispatched",
            }
            task.mfo_can_submit = is_assigned and task.mfo_state in {
                "dispatched",
                "in_progress",
            }
            task.mfo_can_verify = is_verifier and task.mfo_state == "submitted"
            task.mfo_can_reopen = is_dispatcher and task.mfo_state in {
                "submitted",
                "verified",
                "cancelled",
            }

    @api.onchange("mfo_crew_team_id")
    def _onchange_mfo_crew_team_id(self):
        for task in self:
            if not task.mfo_crew_team_id:
                continue
            task.mfo_vehicle_id = task.mfo_crew_team_id.vehicle_id
            task.mfo_vehicle_ids |= task.mfo_crew_team_id.vehicle_id
            task.mfo_driver_employee_id = task.mfo_crew_team_id.driver_employee_id
            task.mfo_collector_employee_ids = task.mfo_crew_team_id.collector_employee_ids
            task.mfo_inspector_employee_id = task.mfo_crew_team_id.inspector_employee_id

    @api.onchange("mfo_route_id")
    def _onchange_mfo_route_id(self):
        for task in self:
            if task.mfo_route_id:
                task.mfo_district_id = task.mfo_route_id.district_id
                task.mfo_subdistrict_ids = task.mfo_route_id.subdistrict_ids
                task.mfo_subdistrict_id = (
                    task.mfo_route_id.subdistrict_ids[:1]
                    if len(task.mfo_route_id.subdistrict_ids) == 1
                    else False
                )
                if not task.mfo_shift_type:
                    task.mfo_shift_type = task.mfo_route_id.shift_type

    @api.onchange("mfo_route_line_id")
    def _onchange_mfo_route_line_id(self):
        for task in self:
            if not task.mfo_route_line_id:
                continue
            task.mfo_route_id = task.mfo_route_line_id.route_id
            task.mfo_collection_point_id = task.mfo_route_line_id.collection_point_id
            task.sequence = task.mfo_route_line_id.sequence

    @api.onchange("mfo_collection_point_id")
    def _onchange_mfo_collection_point_id(self):
        for task in self:
            if not task.mfo_collection_point_id:
                continue
            task.mfo_district_id = task.mfo_collection_point_id.district_id
            task.mfo_subdistrict_id = task.mfo_collection_point_id.subdistrict_id
            if task.mfo_collection_point_id.subdistrict_id:
                task.mfo_subdistrict_ids = [
                    Command.set([task.mfo_collection_point_id.subdistrict_id.id])
                ]

    @api.onchange("mfo_vehicle_id")
    def _onchange_mfo_vehicle_id(self):
        for task in self:
            if task.mfo_vehicle_id:
                task.mfo_vehicle_ids |= task.mfo_vehicle_id
                crew_team = self.env["mfo.crew.team"].search(
                    [
                        ("vehicle_id", "=", task.mfo_vehicle_id.id),
                        ("operation_type", "=", task.mfo_operation_type or "garbage"),
                        ("active", "=", True),
                    ],
                    limit=1,
                )
                if crew_team:
                    task.mfo_crew_team_id = crew_team
                    task.mfo_driver_employee_id = crew_team.driver_employee_id
                    task.mfo_collector_employee_ids = crew_team.collector_employee_ids
                    task.mfo_inspector_employee_id = crew_team.inspector_employee_id

    @api.onchange("mfo_subdistrict_id")
    def _onchange_mfo_subdistrict_id(self):
        for task in self:
            if task.mfo_subdistrict_id:
                task.mfo_subdistrict_ids |= task.mfo_subdistrict_id

    @api.constrains(
        "mfo_operation_type",
        "mfo_vehicle_id",
        "mfo_driver_employee_id",
        "mfo_collector_employee_ids",
        "mfo_route_id",
    )
    def _check_mfo_garbage_requirements(self):
        for task in self:
            if not task.mfo_is_operation_project:
                continue
            if task.mfo_is_route_point_task:
                continue
            if task.mfo_operation_type != "garbage":
                continue
            if task.mfo_state == "draft":
                continue
            if not task.mfo_route_id:
                raise ValidationError(_("Хог цуглуулалтын даалгаварт маршрут заавал байна."))
            if not task.mfo_vehicle_id:
                raise ValidationError(_("Хог цуглуулалтын даалгаварт техник заавал байна."))
            if not task.mfo_driver_employee_id:
                raise ValidationError(_("Хог цуглуулалтын даалгаварт жолооч заавал байна."))
            if len(task.mfo_collector_employee_ids) != 2:
                raise ValidationError(_("Хог цуглуулалтын даалгаварт яг 2 ачигч байна."))

    @api.constrains("mfo_district_id", "mfo_subdistrict_id")
    def _check_mfo_subdistrict_match(self):
        for task in self:
            if not task.mfo_is_operation_project:
                continue
            if task.mfo_is_route_point_task:
                continue
            if (
                task.mfo_subdistrict_id
                and task.mfo_subdistrict_id.district_id
                and task.mfo_subdistrict_id.district_id != task.mfo_district_id
            ):
                raise ValidationError(_("Хороо нь сонгосон дүүрэгтэй таарах ёстой."))

    @api.constrains("mfo_is_operation_project", "mfo_operation_type", "mfo_vehicle_id", "mfo_shift_date")
    def _check_mfo_unique_vehicle_shift(self):
        for task in self:
            if (
                not task.mfo_is_operation_project
                or task.mfo_is_route_point_task
                or task.mfo_collection_point_id
                or task.mfo_route_line_id
                or task.project_id.mfo_selected_route_id
                or task.mfo_operation_type != "garbage"
                or not task.mfo_vehicle_id
                or not task.mfo_shift_date
            ):
                continue
            duplicate_count = self.search_count(
                [
                    ("id", "!=", task.id),
                    ("mfo_is_operation_project", "=", True),
                    ("mfo_operation_type", "=", "garbage"),
                    ("mfo_vehicle_id", "=", task.mfo_vehicle_id.id),
                    ("mfo_shift_date", "=", task.mfo_shift_date),
                ]
            )
            if duplicate_count:
                raise ValidationError(
                    _(
                        "Нэг техник нэг өдөрт зөвхөн нэг хог цуглуулалтын даалгавартай байна."
                    )
                )

    def _mfo_is_dispatcher_or_manager(self):
        self.ensure_one()
        return self.env.user.has_group("municipal_field_ops.group_mfo_manager") or self.env.user.has_group(
            "municipal_field_ops.group_mfo_dispatcher"
        )

    def _mfo_is_verifier(self):
        self.ensure_one()
        return self.env.user.has_group("municipal_field_ops.group_mfo_manager") or self.env.user.has_group(
            "municipal_field_ops.group_mfo_inspector"
        )

    def _mfo_is_assigned_user(self):
        self.ensure_one()
        return self.env.user in self.user_ids

    def _mfo_get_stage(self, stage_code):
        self.ensure_one()
        stage = self.project_id.type_ids.filtered(lambda item: item.mfo_stage_code == stage_code)[:1]
        if stage:
            return stage
        return self.env["project.task.type"]

    def _mfo_sync_core_status(self):
        for task in self:
            if not task.mfo_is_operation_project:
                continue
            vals = {}
            if task.mfo_state in {"draft", "dispatched", "in_progress"}:
                vals["state"] = "01_in_progress"
            elif task.mfo_state == "submitted":
                vals["state"] = "04_waiting_normal"
            elif task.mfo_state == "verified":
                vals["state"] = "1_done"
                vals["date_end"] = fields.Datetime.now()
            elif task.mfo_state == "cancelled":
                vals["state"] = "1_canceled"

            stage_code = {
                "draft": "planned",
                "dispatched": "dispatched",
                "in_progress": "in_progress",
                "submitted": "review",
                "verified": "done",
                "cancelled": "done",
            }.get(task.mfo_state)
            stage = task._mfo_get_stage(stage_code)
            if stage:
                vals["stage_id"] = stage.id
            if vals:
                super(ProjectTask, task).write(vals)

    def _mfo_get_matching_crew_team(self, vehicle):
        self.ensure_one()
        if not vehicle:
            return self.env["mfo.crew.team"]
        domain = [
            ("vehicle_id", "=", vehicle.id),
            ("active", "=", True),
        ]
        if self.mfo_operation_type:
            domain.append(("operation_type", "=", self.mfo_operation_type))
        return self.env["mfo.crew.team"].search(domain, limit=1)

    @api.model
    def _mfo_prepare_single_stop_line_command(self, collection_point, route_line=False):
        values = {
            "sequence": route_line.sequence if route_line else 10,
            "collection_point_id": collection_point.id,
            "status": "draft",
        }
        if route_line:
            values.update(
                {
                    "route_line_id": route_line.id,
                    "planned_arrival_hour": route_line.planned_arrival_hour,
                    "planned_service_minutes": route_line.planned_service_minutes,
                    "note": route_line.note,
                }
            )
        return [Command.create(values)]

    def _mfo_prepare_assignment_defaults(self, vals):
        vals = dict(vals)
        route_point_task = vals.get("mfo_is_route_point_task")
        route_line = self.env["mfo.route.line"]
        if vals.get("mfo_route_line_id"):
            route_line = self.env["mfo.route.line"].browse(vals["mfo_route_line_id"]).exists()
            if route_line:
                vals.setdefault("mfo_collection_point_id", route_line.collection_point_id.id)
                vals.setdefault("mfo_route_id", route_line.route_id.id)
                vals.setdefault("mfo_district_id", route_line.collection_point_id.district_id.id)
                vals.setdefault("mfo_subdistrict_id", route_line.collection_point_id.subdistrict_id.id)
                vals.setdefault("sequence", route_line.sequence)
                if route_line.note and not vals.get("description"):
                    vals["description"] = (
                        route_line.note or route_line.collection_point_id.address or False
                    )
                if vals.get("mfo_shift_date") and route_line.planned_arrival_hour:
                    planned_start = combine_date_float_hours(
                        fields.Date.to_date(vals["mfo_shift_date"]),
                        route_line.planned_arrival_hour,
                    )
                    vals.setdefault("mfo_planned_start", fields.Datetime.to_string(planned_start))
                    if route_line.planned_service_minutes:
                        vals.setdefault(
                            "mfo_planned_end",
                            fields.Datetime.to_string(
                                planned_start + timedelta(minutes=route_line.planned_service_minutes)
                            ),
                        )
        if vals.get("mfo_vehicle_id") and not vals.get("mfo_crew_team_id"):
            vehicle = self.env["fleet.vehicle"].browse(vals["mfo_vehicle_id"]).exists()
            if vehicle:
                operation_type = vals.get("mfo_operation_type")
                if not operation_type and vals.get("project_id"):
                    project = self.env["project.project"].browse(vals["project_id"]).exists()
                    operation_type = project.mfo_operation_type
                crew_team = self.env["mfo.crew.team"].search(
                    [
                        ("vehicle_id", "=", vehicle.id),
                        ("operation_type", "=", operation_type or "garbage"),
                        ("active", "=", True),
                    ],
                    limit=1,
                )
                if crew_team:
                    vals.setdefault("mfo_crew_team_id", crew_team.id)
        if vals.get("mfo_crew_team_id"):
            team = self.env["mfo.crew.team"].browse(vals["mfo_crew_team_id"]).exists()
            if team:
                vals.setdefault("mfo_vehicle_id", team.vehicle_id.id)
                if team.vehicle_id and not vals.get("mfo_vehicle_ids"):
                    vals["mfo_vehicle_ids"] = [Command.set([team.vehicle_id.id])]
                vals.setdefault("mfo_driver_employee_id", team.driver_employee_id.id)
                vals.setdefault("mfo_inspector_employee_id", team.inspector_employee_id.id)
                if not vals.get("mfo_collector_employee_ids"):
                    vals["mfo_collector_employee_ids"] = [
                        Command.set(team.collector_employee_ids.ids)
                    ]
        if vals.get("mfo_route_id") and not vals.get("mfo_district_id"):
            route = self.env["mfo.route"].browse(vals["mfo_route_id"]).exists()
            if route:
                vals["mfo_district_id"] = route.district_id.id
                if route.subdistrict_ids and not vals.get("mfo_subdistrict_ids"):
                    vals["mfo_subdistrict_ids"] = [Command.set(route.subdistrict_ids.ids)]
                if not vals.get("mfo_subdistrict_id") and len(route.subdistrict_ids) == 1:
                    vals["mfo_subdistrict_id"] = route.subdistrict_ids[:1].id
                vals.setdefault("mfo_shift_type", route.shift_type)
        if vals.get("mfo_collection_point_id"):
            collection_point = self.env["mfo.collection.point"].browse(
                vals["mfo_collection_point_id"]
            ).exists()
            if collection_point:
                vals.setdefault("mfo_district_id", collection_point.district_id.id)
                vals.setdefault("mfo_subdistrict_id", collection_point.subdistrict_id.id)
                if collection_point.subdistrict_id and not vals.get("mfo_subdistrict_ids"):
                    vals["mfo_subdistrict_ids"] = [Command.set([collection_point.subdistrict_id.id])]
        if vals.get("mfo_vehicle_id") and not vals.get("mfo_vehicle_ids"):
            vals["mfo_vehicle_ids"] = [Command.set([vals["mfo_vehicle_id"]])]
        if vals.get("mfo_subdistrict_id") and not vals.get("mfo_subdistrict_ids"):
            vals["mfo_subdistrict_ids"] = [Command.set([vals["mfo_subdistrict_id"]])]
        if vals.get("mfo_collection_point_id") and not vals.get("mfo_stop_line_ids") and not route_point_task:
            collection_point = self.env["mfo.collection.point"].browse(
                vals["mfo_collection_point_id"]
            ).exists()
            if collection_point:
                vals["mfo_stop_line_ids"] = self._mfo_prepare_single_stop_line_command(
                    collection_point, route_line
                )
        return vals

    def _mfo_get_assigned_user_ids(self):
        self.ensure_one()
        users = (
            self.mfo_driver_employee_id.user_id
            | self.mfo_inspector_employee_id.user_id
            | self.mfo_collector_employee_ids.mapped("user_id")
        )
        return users.filtered(lambda user: user and not user.share).ids

    def _mfo_build_route_point_task_values(self, route_line):
        self.ensure_one()
        planned_start = False
        planned_end = False
        if self.mfo_shift_date and route_line.planned_arrival_hour:
            start_dt = combine_date_float_hours(self.mfo_shift_date, route_line.planned_arrival_hour)
            planned_start = fields.Datetime.to_string(start_dt)
            if route_line.planned_service_minutes:
                planned_end_dt = fields.Datetime.to_datetime(planned_start) + timedelta(
                    minutes=route_line.planned_service_minutes
                )
                planned_end = fields.Datetime.to_string(planned_end_dt)
        return {
            "name": route_line.collection_point_id.name,
            "project_id": self.project_id.id,
            "parent_id": self.id,
            "mfo_is_route_point_task": True,
            "mfo_source_route_line_id": route_line.id,
            "mfo_shift_date": self.mfo_shift_date,
            "mfo_shift_type": self.mfo_shift_type,
            "mfo_crew_team_id": self.mfo_crew_team_id.id,
            "mfo_vehicle_id": self.mfo_vehicle_id.id,
            "mfo_vehicle_ids": [Command.set((self.mfo_vehicle_ids | self.mfo_vehicle_id).ids)],
            "mfo_driver_employee_id": self.mfo_driver_employee_id.id,
            "mfo_collector_employee_ids": [Command.set(self.mfo_collector_employee_ids.ids)],
            "mfo_inspector_employee_id": self.mfo_inspector_employee_id.id,
            "mfo_route_id": self.mfo_route_id.id,
            "mfo_district_id": route_line.collection_point_id.district_id.id,
            "mfo_subdistrict_id": route_line.collection_point_id.subdistrict_id.id,
            "mfo_subdistrict_ids": [Command.set([route_line.collection_point_id.subdistrict_id.id])],
            "mfo_state": self.mfo_state,
            "mfo_planned_start": planned_start,
            "mfo_planned_end": planned_end,
            "description": route_line.note or route_line.collection_point_id.address or False,
            "user_ids": [Command.set(self.user_ids.ids)],
        }

    def _mfo_sync_route_point_tasks(self):
        if self.env.context.get("mfo_skip_route_point_tasks"):
            return
        Task = self.sudo().with_context(mfo_skip_route_point_tasks=True)
        for task in self.filtered(
            lambda item: item.mfo_is_operation_project
            and not item.mfo_is_route_point_task
            and item.mfo_operation_type == "garbage"
        ):
            existing_by_line = {
                child.mfo_source_route_line_id.id: child
                for child in task.child_ids.filtered("mfo_is_route_point_task")
                if child.mfo_source_route_line_id
            }
            target_line_ids = set()
            route_lines = task.mfo_route_id.line_ids.sorted(key=lambda line: (line.sequence, line.id)) if task.mfo_route_id else self.env["mfo.route.line"]
            for route_line in route_lines:
                target_line_ids.add(route_line.id)
                values = task._mfo_build_route_point_task_values(route_line)
                existing_task = existing_by_line.get(route_line.id)
                if existing_task:
                    existing_task.sudo().with_context(mfo_skip_route_point_tasks=True).write(values)
                else:
                    Task.create(values)
            extra_children = task.child_ids.filtered(
                lambda child: child.mfo_is_route_point_task
                and (
                    not child.mfo_source_route_line_id
                    or child.mfo_source_route_line_id.id not in target_line_ids
                )
            )
            if extra_children:
                extra_children.sudo().with_context(mfo_skip_route_point_tasks=True).unlink()

    def _mfo_sync_assignees(self):
        for task in self.filtered(lambda item: item.mfo_is_operation_project and not item.mfo_is_route_point_task):
            user_ids = task._mfo_get_assigned_user_ids()
            if set(task.user_ids.ids) == set(user_ids):
                continue
            super(ProjectTask, task).write({"user_ids": [Command.set(user_ids)]})

    def _mfo_sync_multi_selection_fields(self):
        for task in self:
            values = {}
            vehicle_ids = task.mfo_vehicle_ids | task.mfo_vehicle_id
            subdistrict_ids = task.mfo_subdistrict_ids | task.mfo_subdistrict_id
            if set(vehicle_ids.ids) != set(task.mfo_vehicle_ids.ids):
                values["mfo_vehicle_ids"] = [Command.set(vehicle_ids.ids)]
            if set(subdistrict_ids.ids) != set(task.mfo_subdistrict_ids.ids):
                values["mfo_subdistrict_ids"] = [Command.set(subdistrict_ids.ids)]
            if values:
                super(ProjectTask, task).write(values)

    def _mfo_sync_single_stop_line(self):
        for task in self.filtered("mfo_collection_point_id"):
            route_line = task.mfo_route_line_id
            values = {
                "sequence": task.sequence or (route_line.sequence if route_line else 10),
                "collection_point_id": task.mfo_collection_point_id.id,
                "status": "draft",
            }
            if route_line:
                values.update(
                    {
                        "route_line_id": route_line.id,
                        "planned_arrival_hour": route_line.planned_arrival_hour,
                        "planned_service_minutes": route_line.planned_service_minutes,
                        "note": route_line.note,
                    }
                )
            primary_line = task.mfo_primary_stop_line_id or task.mfo_stop_line_ids[:1]
            if primary_line:
                primary_line.write(values)
            else:
                super(ProjectTask, task).write(
                    {"mfo_stop_line_ids": self._mfo_prepare_single_stop_line_command(task.mfo_collection_point_id, route_line)}
                )
            extra_lines = task.mfo_stop_line_ids - primary_line
            if extra_lines:
                extra_lines.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create([self._mfo_prepare_assignment_defaults(vals) for vals in vals_list])
        tasks._mfo_sync_multi_selection_fields()
        tasks.filtered("mfo_collection_point_id")._mfo_sync_single_stop_line()
        tasks.filtered("mfo_is_operation_project")._mfo_sync_assignees()
        tasks.filtered("mfo_is_operation_project")._mfo_sync_core_status()
        return tasks

    def write(self, vals):
        result = super().write(self._mfo_prepare_assignment_defaults(vals))
        self._mfo_sync_multi_selection_fields()
        self.filtered("mfo_collection_point_id")._mfo_sync_single_stop_line()
        operation_tasks = self.filtered("mfo_is_operation_project")
        if {
            "mfo_crew_team_id",
            "mfo_vehicle_id",
            "mfo_vehicle_ids",
            "mfo_driver_employee_id",
            "mfo_collector_employee_ids",
                "mfo_inspector_employee_id",
        } & set(vals):
            operation_tasks._mfo_sync_assignees()
        if "mfo_state" in vals:
            operation_tasks._mfo_sync_core_status()
        return result

    def _mfo_check_dispatch_requirements(self):
        for task in self:
            if not task.mfo_vehicle_id:
                raise UserError(_("Техник сонгоно уу."))
            if not task.mfo_driver_employee_id:
                raise UserError(_("Жолооч сонгоно уу."))
            if task.mfo_operation_type == "garbage" and len(task.mfo_collector_employee_ids) != 2:
                raise UserError(_("Хог цуглуулалтын даалгаварт яг 2 ачигч сонгоно уу."))

    def _mfo_completed_stop_proof_gaps(self):
        self.ensure_one()
        gaps = []
        for line in self.mfo_stop_line_ids.filtered(lambda item: item.status == "done"):
            proof_types = set(line.proof_image_ids.mapped("proof_type"))
            missing_types = [proof_type for proof_type in ("before", "after") if proof_type not in proof_types]
            if missing_types:
                gaps.append((line, missing_types))
        return gaps

    def _mfo_check_submission_requirements(self):
        for task in self:
            if not task.mfo_collection_point_id and not task.mfo_end_shift_summary:
                raise UserError(_("Ээлжийн тайланг бөглөнө үү."))
            if not task.mfo_stop_line_ids:
                raise UserError(_("Цэгийн ажлын мөр үүссэн байх ёстой."))
            unresolved_stops = task.mfo_stop_line_ids.filtered(
                lambda line: line.status not in {"done", "skipped"}
            )
            if unresolved_stops:
                raise UserError(_("Бүх зогсоолыг гүйцэтгэсэн эсвэл алгассан төлөвт оруулсны дараа шалгалтад илгээнэ үү."))
            skipped_without_reason = task.mfo_stop_line_ids.filtered(
                lambda line: line.status == "skipped" and not line.skip_reason
            )
            if skipped_without_reason:
                raise UserError(_("Алгассан бүх зогсоолд шалтгаан заавал бичнэ үү."))
            proof_gaps = task._mfo_completed_stop_proof_gaps()
            if proof_gaps:
                line_names = ", ".join(line.collection_point_id.name for line, _missing in proof_gaps[:3])
                raise UserError(
                    _(
                        "Гүйцэтгэсэн зогсоол бүрт өмнөх ба дараах зураг хэрэгтэй. Дутуу цэгүүд: %(lines)s"
                    )
                    % {"lines": line_names}
                )

    def action_mfo_dispatch(self):
        for task in self:
            if not task._mfo_is_dispatcher_or_manager():
                raise AccessError(_("Энэ үйлдлийг зөвхөн менежер эсвэл диспетчер хийнэ."))
            task._mfo_check_dispatch_requirements()
            task.write(
                {
                    "mfo_state": "dispatched",
                    "mfo_dispatch_datetime": fields.Datetime.now(),
                }
            )
            task.message_post(body=_("Өдрийн даалгаврыг хуваариллаа."))
        return True

    def action_mfo_start_shift(self):
        for task in self:
            if not (task._mfo_is_dispatcher_or_manager() or task._mfo_is_assigned_user()):
                raise AccessError(_("Оноогдсон хэрэглэгч эсвэл диспетчер ээлжийг эхлүүлнэ."))
            update_vals = {
                "mfo_state": "in_progress",
                "mfo_start_datetime": task.mfo_start_datetime or fields.Datetime.now(),
            }
            if not task.mfo_dispatch_datetime:
                update_vals["mfo_dispatch_datetime"] = fields.Datetime.now()
            task.write(update_vals)
            task.message_post(body=_("Ээлжийн ажил эхэллээ."))
        return True

    def action_mfo_submit_for_verification(self):
        for task in self:
            if not task._mfo_is_assigned_user():
                raise AccessError(_("Оноогдсон хэрэглэгч л шалгалтад илгээнэ."))
            task._mfo_check_submission_requirements()
            task.write(
                {
                    "mfo_state": "submitted",
                    "mfo_end_datetime": fields.Datetime.now(),
                }
            )
            task.message_post(body=_("Шалгалтад илгээлээ."))
        return True

    def action_mfo_verify_completion(self):
        for task in self:
            if not task._mfo_is_verifier():
                raise AccessError(_("Энэ үйлдлийг менежер эсвэл хянагч баталгаажуулна."))
            task._mfo_check_submission_requirements()
            task.write({"mfo_state": "verified"})
            task.message_post(body=_("Ээлжийг баталгаажуулж хаалаа."))
        return True

    def action_mfo_reopen_execution(self):
        for task in self:
            if not task._mfo_is_dispatcher_or_manager():
                raise AccessError(_("Дахин нээх үйлдлийг зөвхөн менежер эсвэл диспетчер хийнэ."))
            task.write({"mfo_state": "in_progress"})
            task.message_post(body=_("Даалгаврыг дахин нээлээ."))
        return True

    def action_mfo_open_reassignment_wizard(self):
        self.ensure_one()
        return {
            "name": _("Дахин хуваарилалт"),
            "type": "ir.actions.act_window",
            "res_model": "mfo.task.reassignment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_task_id": self.id},
        }

    def action_mfo_request_weight_sync(self, sync_log=False):
        created_count = 0
        for task in self:
            if task.mfo_operation_type != "garbage" or not task.mfo_vehicle_id:
                continue
            log = sync_log or self.env["mfo.sync.log"].create(
                {
                    "name": _("Гараар пүүгээс татсан лог"),
                    "sync_type": "weighbridge",
                    "state": "running",
                    "task_id": task.id,
                    "vehicle_id": task.mfo_vehicle_id.id,
                    "requested_at": fields.Datetime.now(),
                }
            )
            payloads = task._mfo_fetch_external_daily_weight_payloads(log)
            created_count += task._mfo_upsert_external_daily_weight_totals(payloads, log)
            task.write({"mfo_last_sync_log_id": log.id})
        return created_count

    def _mfo_get_wrs_sync_settings(self):
        self.ensure_one()
        config = self.env["ir.config_parameter"].sudo()
        url = (
            config.get_param("municipal_field_ops.wrs_normalized_url")
            or os.environ.get("MFO_WRS_NORMALIZED_URL")
            or ""
        ).strip()
        token = (
            config.get_param("municipal_field_ops.wrs_api_token")
            or os.environ.get("MFO_WRS_API_TOKEN")
            or ""
        ).strip()
        return url, token

    def _mfo_fetch_external_daily_weight_payloads(self, sync_log=False):
        self.ensure_one()
        shift_date = fields.Date.to_string(self.mfo_shift_date or fields.Date.context_today(self))
        vehicle_code = (self.mfo_vehicle_id.mfo_wrs_vehicle_code or "").strip()
        url, token = self._mfo_get_wrs_sync_settings()

        if sync_log:
            sync_log.write(
                {
                    "task_id": self.id,
                    "vehicle_id": self.mfo_vehicle_id.id,
                    "payload_excerpt": json.dumps(
                        {
                            "url": url,
                            "shift_date": shift_date,
                            "vehicle_code": vehicle_code,
                        },
                        ensure_ascii=False,
                    ),
                }
            )

        if not url:
            if sync_log:
                sync_log.write(
                    {
                        "state": "warning",
                        "finished_at": fields.Datetime.now(),
                        "error_message": _(
                            "`municipal_field_ops.wrs_normalized_url` эсвэл `MFO_WRS_NORMALIZED_URL` тохируулаагүй байна."
                        ),
                    }
                )
            return []

        if not vehicle_code:
            if sync_log:
                sync_log.write(
                    {
                        "state": "warning",
                        "finished_at": fields.Datetime.now(),
                        "error_message": _("Техникийн WRS код тохируулаагүй байна."),
                    }
                )
            return []

        request_url = f"{url}{'&' if '?' in url else '?'}date={quote(shift_date)}"
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            request = Request(request_url, headers=headers, method="GET")
            with urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if sync_log:
                sync_log.write(
                    {
                        "state": "failed",
                        "finished_at": fields.Datetime.now(),
                        "error_message": f"WRS endpoint HTTP {exc.code}",
                    }
                )
            return []
        except (URLError, TimeoutError, ValueError) as exc:
            if sync_log:
                sync_log.write(
                    {
                        "state": "failed",
                        "finished_at": fields.Datetime.now(),
                        "error_message": str(exc),
                    }
                )
            return []

        totals = payload.get("totals") if isinstance(payload, dict) else []
        matched_payloads = []
        for item in totals or []:
            if str(item.get("vehicleCode") or "").strip() != vehicle_code:
                continue
            matched_payloads.append(
                {
                    "shift_date": item.get("requestedDate") or shift_date,
                    "net_weight_total": float(item.get("netWeightTotal") or 0.0),
                    "external_reference": item.get("externalReference")
                    or f"{shift_date}:{vehicle_code}",
                    "source": item.get("source") or "wrs_normalized",
                    "note": item.get("vehicleLabel") or item.get("branchName"),
                }
            )

        if sync_log:
            sync_log.write(
                {
                    "response_excerpt": json.dumps(
                        matched_payloads,
                        ensure_ascii=False,
                    ),
                }
            )
        return matched_payloads

    def _mfo_upsert_external_daily_weight_totals(self, payloads, sync_log):
        self.ensure_one()
        DailyWeightTotal = self.env["mfo.daily.weight.total"]
        upserted_count = 0
        for payload in payloads:
            values = {
                "task_id": self.id,
                "shift_date": payload.get("shift_date") or self.mfo_shift_date,
                "vehicle_id": self.mfo_vehicle_id.id,
                "route_id": self.mfo_route_id.id,
                "net_weight_total": payload.get("net_weight_total", 0.0),
                "source": payload.get("source") or "wrs_normalized",
                "external_reference": payload.get("external_reference"),
                "sync_log_id": sync_log.id,
                "note": payload.get("note"),
            }
            total = DailyWeightTotal.search(
                [
                    ("vehicle_id", "=", self.mfo_vehicle_id.id),
                    ("shift_date", "=", values["shift_date"]),
                ],
                limit=1,
            )
            if total:
                total.write(values)
            else:
                DailyWeightTotal.create(values)
            upserted_count += 1

        if sync_log and not payloads:
            sync_log.write(
                {
                    "state": "warning",
                    "finished_at": fields.Datetime.now(),
                    "task_id": self.id,
                    "vehicle_id": self.mfo_vehicle_id.id,
                    "error_message": _("Сонгосон техник, огноонд WRS өдөр тутмын нийт олдсонгүй."),
                }
            )
        elif sync_log:
            sync_log.write(
                {
                    "state": "success",
                    "finished_at": fields.Datetime.now(),
                    "task_id": self.id,
                    "vehicle_id": self.mfo_vehicle_id.id,
                    "result_count": upserted_count,
                }
            )
        return upserted_count


class MfoStopExecutionLine(models.Model):
    _name = "mfo.stop.execution.line"
    _description = "Зогсоолын гүйцэтгэлийн мөр"
    _order = "task_id, sequence, id"

    task_id = fields.Many2one(
        "project.task",
        string="Даалгавар",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Дараалал", default=10)
    route_line_id = fields.Many2one(
        "mfo.route.line",
        string="Маршрутын мөр",
        ondelete="set null",
    )
    collection_point_id = fields.Many2one(
        "mfo.collection.point",
        string="Цэг",
        required=True,
        ondelete="restrict",
    )
    district_id = fields.Many2one(
        "mfo.district",
        string="Дүүрэг",
        related="collection_point_id.district_id",
        store=True,
        readonly=True,
    )
    subdistrict_id = fields.Many2one(
        "mfo.subdistrict",
        string="Хороо",
        related="collection_point_id.subdistrict_id",
        store=True,
        readonly=True,
    )
    planned_arrival_hour = fields.Float(string="Төлөвлөсөн очих цаг")
    planned_service_minutes = fields.Integer(string="Төлөвлөсөн үйлчилгээ (мин)")
    arrival_datetime = fields.Datetime(string="Бодит очсон цаг")
    departure_datetime = fields.Datetime(string="Бодит дууссан цаг")
    status = fields.Selection(
        selection=STOP_STATE_SELECTION,
        string="Төлөв",
        default="draft",
        required=True,
    )
    note = fields.Char(string="Тэмдэглэл")
    skip_reason = fields.Char(string="Алгассан шалтгаан")
    proof_image_ids = fields.One2many(
        "mfo.proof.image",
        "stop_line_id",
        string="Зургууд",
    )
    issue_ids = fields.One2many(
        "mfo.issue.report",
        "stop_line_id",
        string="Асуудлууд",
    )
    proof_count = fields.Integer(string="Зураг", compute="_compute_counts")
    issue_count = fields.Integer(string="Асуудал", compute="_compute_counts")

    @api.depends("proof_image_ids", "issue_ids")
    def _compute_counts(self):
        for line in self:
            line.proof_count = len(line.proof_image_ids)
            line.issue_count = len(line.issue_ids)

    @api.constrains("status", "skip_reason")
    def _check_skip_reason(self):
        for line in self:
            if line.status == "skipped" and not line.skip_reason:
                raise ValidationError(_("Алгассан зогсоолд шалтгаан заавал байна."))

    def _check_required_completion_proofs(self):
        for line in self:
            proof_types = set(line.proof_image_ids.mapped("proof_type"))
            missing_types = [proof_type for proof_type in ("before", "after") if proof_type not in proof_types]
            if missing_types:
                raise UserError(_("Энэ зогсоолыг гүйцэтгэсэн бол өмнөх болон дараах зураг хоёуланг нь оруулна уу."))

    def action_mark_arrived(self):
        self.write(
            {
                "status": "arrived",
                "arrival_datetime": fields.Datetime.now(),
            }
        )
        return True

    def action_mark_done(self):
        now = fields.Datetime.now()
        for line in self:
            line._check_required_completion_proofs()
            line.write(
                {
                    "status": "done",
                    "arrival_datetime": line.arrival_datetime or now,
                    "departure_datetime": now,
                    "skip_reason": False,
                }
            )
        return True

    def action_mark_skipped(self):
        now = fields.Datetime.now()
        for line in self:
            if not line.skip_reason:
                raise UserError(_("Алгассан шалтгаанаа бичсний дараа хадгална уу."))
            line.write(
                {
                    "status": "skipped",
                    "arrival_datetime": line.arrival_datetime or now,
                    "departure_datetime": now,
                }
            )
        return True


class MfoProofImage(models.Model):
    _name = "mfo.proof.image"
    _description = "Баталгаажуулалтын зураг"
    _order = "capture_datetime desc, id desc"

    name = fields.Char(string="Нэр", required=True, default=lambda self: _("Баталгаажуулалтын зураг"))
    task_id = fields.Many2one(
        "project.task",
        string="Даалгавар",
        required=True,
        ondelete="cascade",
    )
    stop_line_id = fields.Many2one(
        "mfo.stop.execution.line",
        string="Зогсоол",
        ondelete="set null",
    )
    proof_type = fields.Selection(
        selection=PROOF_TYPE_SELECTION,
        string="Зургийн төрөл",
        default="completion",
        required=True,
    )
    capture_datetime = fields.Datetime(
        string="Оруулсан огноо",
        default=fields.Datetime.now,
        required=True,
    )
    uploader_user_id = fields.Many2one(
        "res.users",
        string="Оруулсан хэрэглэгч",
        default=lambda self: self.env.user,
        readonly=True,
    )
    uploader_employee_id = fields.Many2one(
        "hr.employee",
        string="Оруулсан ажилтан",
        readonly=True,
    )
    latitude = fields.Float(string="Өргөрөг")
    longitude = fields.Float(string="Уртраг")
    description = fields.Char(string="Тайлбар")
    image_1920 = fields.Image(string="Зураг", required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("uploader_user_id", self.env.user.id)
            employee = self.env["hr.employee"].sudo().search(
                [("user_id", "=", vals["uploader_user_id"])],
                limit=1,
            )
            if employee:
                vals.setdefault("uploader_employee_id", employee.id)
            if not vals.get("name"):
                vals["name"] = _("Баталгаажуулалтын зураг")
        return super().create(vals_list)

    @api.constrains("task_id", "stop_line_id")
    def _check_task_stop_match(self):
        for image in self:
            if image.stop_line_id and image.stop_line_id.task_id != image.task_id:
                raise ValidationError(_("Зогсоол нь сонгосон даалгаварт хамаарах ёстой."))
            if image.proof_type in {"before", "after"} and not image.stop_line_id:
                raise ValidationError(_("Өмнөх ба дараах зураг нь заавал зогсоолтой холбогдсон байна."))


class MfoWeightMeasurement(models.Model):
    _name = "mfo.weight.measurement"
    _description = "Жингийн бүртгэл"
    _order = "measured_at desc, id desc"

    task_id = fields.Many2one(
        "project.task",
        string="Даалгавар",
        required=True,
        ondelete="cascade",
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Техник",
        ondelete="restrict",
    )
    measured_at = fields.Datetime(
        string="Хэмжсэн огноо",
        default=fields.Datetime.now,
        required=True,
    )
    ticket_number = fields.Char(string="Тасалбарын дугаар")
    source = fields.Selection(
        selection=[("manual", "Гараар"), ("external", "Гадаад синк")],
        string="Эх сурвалж",
        default="manual",
        required=True,
    )
    gross_weight = fields.Float(string="Брутто жин")
    tare_weight = fields.Float(string="Хоосон жин")
    net_weight = fields.Float(
        string="Цэвэр жин",
        compute="_compute_net_weight",
        store=True,
    )
    external_reference = fields.Char(string="Гадаад лавлагаа")
    sync_log_id = fields.Many2one(
        "mfo.sync.log",
        string="Синк лог",
        ondelete="set null",
    )
    note = fields.Char(string="Тэмдэглэл")

    @api.depends("gross_weight", "tare_weight")
    def _compute_net_weight(self):
        for measurement in self:
            measurement.net_weight = measurement.gross_weight - measurement.tare_weight

    @api.constrains("gross_weight", "tare_weight")
    def _check_weight_values(self):
        for measurement in self:
            if measurement.tare_weight < 0 or measurement.gross_weight < 0:
                raise ValidationError(_("Жингийн утга сөрөг байж болохгүй."))
            if measurement.gross_weight and measurement.tare_weight > measurement.gross_weight:
                raise ValidationError(_("Хоосон жин нь брутто жингээс их байж болохгүй."))


class MfoIssueReport(models.Model):
    _name = "mfo.issue.report"
    _description = "Гүйцэтгэлийн асуудлын бүртгэл"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "report_datetime desc, id desc"

    name = fields.Char(string="Гарчиг", required=True)
    task_id = fields.Many2one(
        "project.task",
        string="Даалгавар",
        required=True,
        ondelete="cascade",
    )
    stop_line_id = fields.Many2one(
        "mfo.stop.execution.line",
        string="Зогсоол",
        ondelete="set null",
    )
    reporter_user_id = fields.Many2one(
        "res.users",
        string="Оруулсан хэрэглэгч",
        default=lambda self: self.env.user,
        readonly=True,
    )
    reporter_employee_id = fields.Many2one(
        "hr.employee",
        string="Оруулсан ажилтан",
        readonly=True,
    )
    report_datetime = fields.Datetime(
        string="Бүртгэсэн огноо",
        default=fields.Datetime.now,
        required=True,
    )
    issue_type = fields.Selection(
        selection=ISSUE_TYPE_SELECTION,
        string="Асуудлын төрөл",
        default="other",
        required=True,
        tracking=True,
    )
    severity = fields.Selection(
        selection=ISSUE_SEVERITY_SELECTION,
        string="Ноцтой байдал",
        default="medium",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=ISSUE_STATE_SELECTION,
        string="Төлөв",
        default="new",
        required=True,
        tracking=True,
    )
    description = fields.Text(string="Тайлбар", required=True)
    resolution_note = fields.Text(string="Шийдлийн тэмдэглэл")
    district_id = fields.Many2one(
        "mfo.district",
        string="Дүүрэг",
        related="task_id.mfo_district_id",
        store=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("reporter_user_id", self.env.user.id)
            employee = self.env["hr.employee"].sudo().search(
                [("user_id", "=", vals["reporter_user_id"])],
                limit=1,
            )
            if employee:
                vals.setdefault("reporter_employee_id", employee.id)
        return super().create(vals_list)

    def action_mark_in_progress(self):
        self.write({"state": "in_progress"})
        return True

    def action_mark_resolved(self):
        self.write({"state": "resolved"})
        return True
