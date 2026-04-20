from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command

from .common import OPERATION_TYPE_SELECTION, SHIFT_TYPE_SELECTION, combine_date_float_hours, monday_for


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
    )
    mfo_operation_type = fields.Selection(
        selection=OPERATION_TYPE_SELECTION,
        string="Ажиллагааны төрөл",
        default="garbage",
        required=True,
        tracking=True,
    )
    mfo_district_ids = fields.Many2many(
        "mfo.district",
        "mfo_project_district_rel",
        "project_id",
        "district_id",
        string="Хариуцах дүүргүүд",
    )
    mfo_district_names = fields.Char(
        string="Дүүрэг",
        compute="_compute_mfo_district_names",
    )
    mfo_default_shift_type = fields.Selection(
        selection=SHIFT_TYPE_SELECTION,
        string="Анхны ээлж",
        default="morning",
    )
    mfo_default_shift_start = fields.Float(
        string="Ээлж эхлэх цаг",
        default=6.0,
    )
    mfo_default_shift_end = fields.Float(
        string="Ээлж дуусах цаг",
        default=14.0,
    )
    mfo_route_ids = fields.One2many(
        "mfo.route",
        "project_id",
        string="Маршрутууд",
    )
    mfo_selected_route_id = fields.Many2one(
        "mfo.route",
        string="Сонгосон маршрут",
        tracking=True,
    )
    mfo_selected_vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Сонгосон машин",
        domain="[('mfo_active_for_ops', '=', True)]",
        tracking=True,
    )
    mfo_work_date = fields.Date(
        string="Ажлын огноо",
        tracking=True,
    )
    mfo_selected_shift_type = fields.Selection(
        selection=SHIFT_TYPE_SELECTION,
        string="Ажлын ээлж",
        tracking=True,
    )
    mfo_crew_team_id = fields.Many2one(
        "mfo.crew.team",
        string="Экипаж",
        tracking=True,
    )
    mfo_driver_employee_id = fields.Many2one(
        "hr.employee",
        string="Жолооч",
        tracking=True,
    )
    mfo_collector_employee_ids = fields.Many2many(
        "hr.employee",
        "mfo_project_collector_rel",
        "project_id",
        "employee_id",
        string="Ачигчид",
        tracking=True,
    )
    mfo_inspector_employee_id = fields.Many2one(
        "hr.employee",
        string="Хянагч",
        tracking=True,
    )
    mfo_planning_template_ids = fields.One2many(
        "mfo.planning.template",
        "project_id",
        string="7 хоногийн загварууд",
    )
    mfo_route_count = fields.Integer(
        string="Маршрутын тоо",
        compute="_compute_mfo_counts",
    )
    mfo_planning_template_count = fields.Integer(
        string="Загварын тоо",
        compute="_compute_mfo_counts",
    )
    mfo_stop_task_count = fields.Integer(
        string="Цэгийн ажилбарын тоо",
        compute="_compute_mfo_execution_summary",
    )
    mfo_overall_progress = fields.Float(
        string="Нийт гүйцэтгэл",
        compute="_compute_mfo_execution_summary",
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

    @api.depends("task_ids.mfo_progress_percent", "task_ids.active")
    def _compute_mfo_execution_summary(self):
        for project in self:
            tasks = project.task_ids.filtered(lambda task: task.active)
            project.mfo_stop_task_count = len(tasks)
            project.mfo_overall_progress = (
                sum(tasks.mapped("mfo_progress_percent")) / len(tasks) if tasks else 0.0
            )

    @api.constrains(
        "mfo_is_operation_project",
        "mfo_operation_type",
        "mfo_selected_vehicle_id",
        "mfo_selected_route_id",
        "mfo_work_date",
        "mfo_selected_shift_type",
    )
    def _check_mfo_unique_garbage_daily_project(self):
        for project in self:
            if (
                not project.mfo_is_operation_project
                or project.mfo_operation_type != "garbage"
                or not project.mfo_selected_vehicle_id
                or not project.mfo_selected_route_id
                or not project.mfo_work_date
                or not project.mfo_selected_shift_type
            ):
                continue
            duplicate_count = self.search_count(
                [
                    ("id", "!=", project.id),
                    ("mfo_is_operation_project", "=", True),
                    ("mfo_operation_type", "=", "garbage"),
                    ("mfo_selected_vehicle_id", "=", project.mfo_selected_vehicle_id.id),
                    ("mfo_selected_route_id", "=", project.mfo_selected_route_id.id),
                    ("mfo_work_date", "=", project.mfo_work_date),
                    ("mfo_selected_shift_type", "=", project.mfo_selected_shift_type),
                ]
            )
            if duplicate_count:
                raise ValidationError(
                    _(
                        "Сонгосон машин, маршрут, огноо, ээлж дээр ажил аль хэдийн үүссэн байна."
                    )
                )

    def _mfo_ensure_default_stages(self):
        stage_model = self.env["project.task.type"].sudo()
        for project in self.filtered("mfo_is_operation_project"):
            if project.type_ids:
                continue
            stage_ids = []
            for code, name, sequence, fold in DEFAULT_STAGE_MAP:
                stage = stage_model.create(
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

    @api.model
    def _mfo_get_route_short_label(self, route):
        return route.code or route.name or _("Маршрут")

    @api.model
    def _mfo_get_matching_garbage_crew(self, vehicle):
        return self.env["mfo.crew.team"].search(
            [
                ("vehicle_id", "=", vehicle.id),
                ("operation_type", "=", "garbage"),
                ("active", "=", True),
            ],
            limit=1,
        )

    @api.model
    def _mfo_find_existing_garbage_daily_project(self, vehicle, route, work_date, shift_type):
        return self.search(
            [
                ("mfo_is_operation_project", "=", True),
                ("mfo_operation_type", "=", "garbage"),
                ("mfo_selected_vehicle_id", "=", vehicle.id),
                ("mfo_selected_route_id", "=", route.id),
                ("mfo_work_date", "=", work_date),
                ("mfo_selected_shift_type", "=", shift_type),
            ],
            limit=1,
        )

    @api.model
    def _mfo_prepare_garbage_daily_project_vals(self, route, vehicle, work_date, shift_type):
        source_project = route.project_id
        crew_team = self._mfo_get_matching_garbage_crew(vehicle)
        work_date_string = fields.Date.to_string(work_date)
        route_label = self._mfo_get_route_short_label(route)
        vals = {
            "name": f"{vehicle.license_plate or vehicle.name} - {route_label} / {work_date_string}",
            "active": True,
            "date_start": work_date_string,
            "date": work_date_string,
            "mfo_is_operation_project": True,
            "mfo_operation_type": "garbage",
            "mfo_default_shift_type": shift_type,
            "mfo_selected_route_id": route.id,
            "mfo_selected_vehicle_id": vehicle.id,
            "mfo_work_date": work_date,
            "mfo_selected_shift_type": shift_type,
        }
        if source_project.user_id:
            vals["user_id"] = source_project.user_id.id
        if getattr(source_project, "ops_department_id", False):
            vals["ops_department_id"] = source_project.ops_department_id.id
        if route.district_id:
            vals["mfo_district_ids"] = [Command.set([route.district_id.id])]
        if crew_team:
            vals.update(
                {
                    "mfo_crew_team_id": crew_team.id,
                    "mfo_driver_employee_id": crew_team.driver_employee_id.id,
                    "mfo_collector_employee_ids": [Command.set(crew_team.collector_employee_ids.ids)],
                    "mfo_inspector_employee_id": crew_team.inspector_employee_id.id,
                }
            )
        for field_name in ("company_id", "partner_id"):
            if field_name in self._fields and getattr(source_project, field_name, False):
                vals[field_name] = getattr(source_project, field_name).id
        if "analytic_account_id" in self._fields and getattr(
            source_project, "analytic_account_id", False
        ):
            vals["analytic_account_id"] = source_project.analytic_account_id.id
        return vals

    def _mfo_get_project_assignee_ids(self):
        self.ensure_one()
        users = (
            self.mfo_driver_employee_id.user_id
            | self.mfo_inspector_employee_id.user_id
            | self.mfo_collector_employee_ids.mapped("user_id")
        )
        return users.filtered(lambda user: user and not user.share).ids

    def _mfo_prepare_garbage_stop_task_vals(self, route_line):
        self.ensure_one()
        planned_start = False
        planned_end = False
        if self.mfo_work_date and route_line.planned_arrival_hour:
            start_dt = combine_date_float_hours(self.mfo_work_date, route_line.planned_arrival_hour)
            planned_start = fields.Datetime.to_string(start_dt)
            if route_line.planned_service_minutes:
                planned_end = fields.Datetime.to_string(
                    fields.Datetime.to_datetime(planned_start)
                    + timedelta(minutes=route_line.planned_service_minutes)
                )

        stage = self.type_ids.filtered(lambda item: item.mfo_stage_code == "planned")[:1]
        stop_name = route_line.collection_point_id.name or _("Цэг")
        task_vals = {
            "project_id": self.id,
            "name": f"{route_line.sequence}. {stop_name}",
            "sequence": route_line.sequence,
            "stage_id": stage.id if stage else False,
            "mfo_is_route_point_task": False,
            "mfo_source_route_line_id": route_line.id,
            "mfo_route_line_id": route_line.id,
            "mfo_collection_point_id": route_line.collection_point_id.id,
            "mfo_route_id": route_line.route_id.id,
            "mfo_shift_date": self.mfo_work_date,
            "mfo_shift_type": self.mfo_selected_shift_type,
            "mfo_crew_team_id": self.mfo_crew_team_id.id,
            "mfo_vehicle_id": self.mfo_selected_vehicle_id.id,
            "mfo_vehicle_ids": [Command.set([self.mfo_selected_vehicle_id.id])],
            "mfo_driver_employee_id": self.mfo_driver_employee_id.id,
            "mfo_collector_employee_ids": [Command.set(self.mfo_collector_employee_ids.ids)],
            "mfo_inspector_employee_id": self.mfo_inspector_employee_id.id,
            "mfo_district_id": route_line.collection_point_id.district_id.id,
            "mfo_subdistrict_id": route_line.collection_point_id.subdistrict_id.id,
            "mfo_subdistrict_ids": [
                Command.set([route_line.collection_point_id.subdistrict_id.id])
            ]
            if route_line.collection_point_id.subdistrict_id
            else False,
            "mfo_state": "draft",
            "mfo_planned_start": planned_start,
            "mfo_planned_end": planned_end,
            "description": route_line.note or route_line.collection_point_id.address or False,
            "user_ids": [Command.set(self._mfo_get_project_assignee_ids())],
            "mfo_stop_line_ids": [
                Command.create(
                    {
                        "sequence": route_line.sequence,
                        "route_line_id": route_line.id,
                        "collection_point_id": route_line.collection_point_id.id,
                        "planned_arrival_hour": route_line.planned_arrival_hour,
                        "planned_service_minutes": route_line.planned_service_minutes,
                        "status": "draft",
                        "note": route_line.note,
                    }
                )
            ],
        }
        return task_vals

    @api.model
    def action_mfo_create_garbage_daily_project(self, payload):
        payload = payload or {}
        vehicle_id = payload.get("vehicle_id")
        route_id = payload.get("route_id")
        shift_date = payload.get("shift_date")
        shift_type = payload.get("shift_type")

        if not vehicle_id:
            raise ValidationError(_("Машинаа сонгоно уу."))
        if not route_id:
            raise ValidationError(_("Маршрутаа сонгоно уу."))
        if not shift_date:
            raise ValidationError(_("Огноогоо сонгоно уу."))

        vehicle = self.env["fleet.vehicle"].browse(vehicle_id).exists()
        route = self.env["mfo.route"].browse(route_id).exists()
        work_date = fields.Date.to_date(shift_date)
        if not vehicle:
            raise ValidationError(_("Сонгосон машин олдсонгүй."))
        if not route:
            raise ValidationError(_("Сонгосон маршрут олдсонгүй."))
        if route.operation_type != "garbage":
            raise ValidationError(_("Зөвхөн хог тээвэрлэлтийн маршрут ашиглана."))

        route_lines = route.line_ids.sorted(key=lambda line: (line.sequence, line.id))
        if not route_lines:
            raise ValidationError(_("Сонгосон маршрутад дор хаяж нэг цэг бүртгэлтэй байх ёстой."))

        shift_type = shift_type or route.shift_type or "morning"
        existing_project = self._mfo_find_existing_garbage_daily_project(
            vehicle, route, work_date, shift_type
        )
        if existing_project:
            return {
                "project_id": existing_project.id,
                "created": False,
                "message": _(
                    "Сонгосон машин, маршрут, огноо, ээлжийн ажил өмнө нь үүссэн тул өмнөх ажлыг нээлээ."
                ),
            }

        project = self.create(
            self._mfo_prepare_garbage_daily_project_vals(route, vehicle, work_date, shift_type)
        )
        task_values = [
            project._mfo_prepare_garbage_stop_task_vals(route_line) for route_line in route_lines
        ]
        tasks = self.env["project.task"].create(task_values)

        project.message_post(body=_("Хог тээвэрлэлтийн өдрийн ажил автоматаар үүсгэгдлээ."))
        for task in tasks:
            task.message_post(body=_("Маршрутын цэгийн ажил автоматаар үүсгэгдлээ."))

        return {
            "project_id": project.id,
            "created": True,
            "message": _(
                "Сонгосон машин, маршрут, огноогоор нэг ажил үүсэж, маршрутын цэг бүр тусдаа ажилбар болж нэмэгдлээ."
            ),
        }

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
                body=_("%(date)s эхлэх 7 хоногт %(count)s өдөр тутмын даалгавар үүслээ.")
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
