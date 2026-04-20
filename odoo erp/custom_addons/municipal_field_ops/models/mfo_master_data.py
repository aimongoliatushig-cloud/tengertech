from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .common import OPERATION_TYPE_SELECTION


class MfoDistrict(models.Model):
    _name = "mfo.district"
    _description = "Хотын дүүрэг"
    _order = "sequence, name"

    name = fields.Char(string="Нэр", required=True)
    code = fields.Char(string="Код")
    sequence = fields.Integer(string="Дараалал", default=10)
    active = fields.Boolean(string="Идэвхтэй", default=True)
    note = fields.Text(string="Тайлбар")
    subdistrict_ids = fields.One2many(
        "mfo.subdistrict",
        "district_id",
        string="Хороонууд",
    )
    route_ids = fields.One2many(
        "mfo.route",
        "district_id",
        string="Маршрутууд",
    )


class MfoSubdistrict(models.Model):
    _name = "mfo.subdistrict"
    _description = "Хотын хороо"
    _order = "sequence, name"

    name = fields.Char(string="Нэр", required=True)
    code = fields.Char(string="Код")
    sequence = fields.Integer(string="Дараалал", default=10)
    active = fields.Boolean(string="Идэвхтэй", default=True)
    district_id = fields.Many2one(
        "mfo.district",
        string="Дүүрэг",
        ondelete="set null",
    )
    note = fields.Text(string="Тайлбар")


class MfoCollectionPoint(models.Model):
    _name = "mfo.collection.point"
    _description = "Цуглуулалтын цэг"
    _order = "subdistrict_id, name"

    name = fields.Char(string="Нэр", required=True)
    code = fields.Char(string="Код")
    active = fields.Boolean(string="Идэвхтэй", default=True)
    district_id = fields.Many2one(
        "mfo.district",
        string="Дүүрэг",
        related="subdistrict_id.district_id",
        store=True,
        readonly=True,
    )
    subdistrict_id = fields.Many2one(
        "mfo.subdistrict",
        string="Хороо",
        required=True,
        ondelete="restrict",
    )
    operation_type = fields.Selection(
        selection=OPERATION_TYPE_SELECTION,
        string="Ажиллагааны төрөл",
        default="garbage",
        required=True,
    )
    address = fields.Char(string="Хаяг")
    latitude = fields.Float(string="Өргөрөг")
    longitude = fields.Float(string="Уртраг")
    note = fields.Text(string="Тайлбар")
    route_line_ids = fields.One2many(
        "mfo.route.line",
        "collection_point_id",
        string="Маршрутын мөрүүд",
    )

class MfoRoute(models.Model):
    _name = "mfo.route"
    _description = "Үйл ажиллагааны маршрут"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "project_id, code, name"

    name = fields.Char(string="Нэр", required=True, tracking=True)
    code = fields.Char(string="Код", tracking=True)
    active = fields.Boolean(string="Идэвхтэй", default=True, tracking=True)
    project_id = fields.Many2one(
        "project.project",
        string="Төсөл",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    operation_type = fields.Selection(
        selection=OPERATION_TYPE_SELECTION,
        string="Ажиллагааны төрөл",
        related="project_id.mfo_operation_type",
        store=True,
        readonly=True,
    )
    district_id = fields.Many2one(
        "mfo.district",
        string="Дүүрэг",
        compute="_compute_area_fields",
        store=True,
        readonly=True,
        compute_sudo=True,
        tracking=True,
    )
    subdistrict_ids = fields.Many2many(
        "mfo.subdistrict",
        compute="_compute_area_fields",
        string="Хорооны жагсаалт",
        store=True,
        readonly=True,
        compute_sudo=True,
    )
    subdistrict_names = fields.Char(
        string="Хороодууд",
        compute="_compute_area_fields",
        store=True,
        readonly=True,
        compute_sudo=True,
    )
    shift_type = fields.Selection(
        selection=[
            ("morning", "Өглөө"),
            ("day", "Өдөр"),
            ("evening", "Орой"),
            ("night", "Шөнө"),
        ],
        string="Ээлж",
        default="morning",
        required=True,
        tracking=True,
    )
    estimated_duration_hours = fields.Float(string="Төлөвлөсөн үргэлжлэх хугацаа")
    estimated_distance_km = fields.Float(string="Төлөвлөсөн зай (км)")
    note = fields.Text(string="Тайлбар")
    line_ids = fields.One2many(
        "mfo.route.line",
        "route_id",
        string="Маршрутын мөрүүд",
    )
    collection_point_count = fields.Integer(
        string="Цэгийн тоо",
        compute="_compute_collection_point_count",
    )

    @api.depends("line_ids.collection_point_id")
    def _compute_collection_point_count(self):
        for route in self:
            route.collection_point_count = len(route.line_ids.mapped("collection_point_id"))

    @api.depends(
        "line_ids.collection_point_id.district_id",
        "line_ids.collection_point_id.subdistrict_id",
    )
    def _compute_area_fields(self):
        for route in self:
            subdistricts = route.line_ids.mapped("collection_point_id.subdistrict_id")
            districts = route.line_ids.mapped("collection_point_id.district_id")
            route.subdistrict_ids = subdistricts
            route.subdistrict_names = ", ".join(subdistricts.mapped("name"))
            route.district_id = districts[:1] if len(districts) == 1 else False


class MfoRouteLine(models.Model):
    _name = "mfo.route.line"
    _description = "Маршрутын мөр"
    _order = "route_id, sequence, id"

    route_id = fields.Many2one(
        "mfo.route",
        string="Маршрут",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Дараалал", default=10)
    collection_point_id = fields.Many2one(
        "mfo.collection.point",
        string="Хогийн цэг",
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
    planned_service_minutes = fields.Integer(string="Төлөвлөсөн үйлчилгээ (мин)", default=10)
    note = fields.Char(string="Тэмдэглэл")

    @api.onchange("route_id")
    def _onchange_route_id_collection_point_domain(self):
        for line in self:
            domain = [("active", "=", True)]
            if line.route_id and line.route_id.operation_type:
                domain.append(("operation_type", "=", line.route_id.operation_type))
            if (
                line.collection_point_id
                and line.route_id
                and line.collection_point_id.operation_type != line.route_id.operation_type
            ):
                line.collection_point_id = False
            return {"domain": {"collection_point_id": domain}}


class MfoCrewTeam(models.Model):
    _name = "mfo.crew.team"
    _description = "Экипажийн баг"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(string="Багийн нэр", required=True, tracking=True)
    code = fields.Char(string="Код", tracking=True)
    active = fields.Boolean(string="Идэвхтэй", default=True, tracking=True)
    operation_type = fields.Selection(
        selection=OPERATION_TYPE_SELECTION,
        string="Ажиллагааны төрөл",
        default="garbage",
        required=True,
        tracking=True,
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Техник",
        domain="[('mfo_active_for_ops', '=', True)]",
        tracking=True,
    )
    driver_employee_id = fields.Many2one(
        "hr.employee",
        string="Жолооч",
        domain="[('mfo_is_field_active', '=', True), ('mfo_field_role', '=', 'driver')]",
        tracking=True,
    )
    collector_employee_ids = fields.Many2many(
        "hr.employee",
        "mfo_crew_collector_rel",
        "crew_team_id",
        "employee_id",
        string="Ачигчид",
        domain="[('mfo_is_field_active', '=', True), ('mfo_field_role', '=', 'collector')]",
        tracking=True,
    )
    inspector_employee_id = fields.Many2one(
        "hr.employee",
        string="Хянагч",
        domain="[('mfo_is_field_active', '=', True), ('mfo_field_role', '=', 'inspector')]",
        tracking=True,
    )
    note = fields.Text(string="Тайлбар")
    member_user_ids = fields.Many2many(
        "res.users",
        compute="_compute_member_user_ids",
        string="Хэрэглэгчид",
    )

    @api.depends(
        "driver_employee_id.user_id",
        "collector_employee_ids.user_id",
        "inspector_employee_id.user_id",
    )
    def _compute_member_user_ids(self):
        for team in self:
            users = (
                team.driver_employee_id.user_id
                | team.collector_employee_ids.mapped("user_id")
                | team.inspector_employee_id.user_id
            )
            team.member_user_ids = users.filtered(lambda user: user and not user.share)

    @api.constrains("operation_type", "collector_employee_ids", "driver_employee_id")
    def _check_garbage_team_shape(self):
        for team in self:
            if team.operation_type != "garbage":
                continue
            if not team.driver_employee_id:
                raise ValidationError(_("Хог цуглуулалтын багт жолооч заавал байна."))
            if len(team.collector_employee_ids) != 2:
                raise ValidationError(_("Хог цуглуулалтын баг яг 2 ачигчтай байх ёстой."))
