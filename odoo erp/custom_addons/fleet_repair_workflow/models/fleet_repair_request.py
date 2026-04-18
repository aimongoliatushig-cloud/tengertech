from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command

from .project_task import MAINTENANCE_CATEGORY_SELECTION


REQUEST_STATE_SELECTION = [
    ("draft", "Ноорог"),
    ("submitted", "Үзлэг илгээсэн"),
    ("waiting_accounting", "Санхүү хянаж байна"),
    ("waiting_admin", "Захиргаа хянаж байна"),
    ("waiting_ceo", "Захирлын баталгаа хүлээж байна"),
    ("approved_ceo", "Захирал зөвшөөрсөн"),
    ("admin_order_ready", "Захирлын тушаал бэлэн"),
    ("fund_prepared", "Хөрөнгө бэлэн"),
    ("purchasing", "Худалдан авч байна"),
    ("parts_received", "Сэлбэг ирсэн"),
    ("in_repair", "Засварт орсон"),
    ("waiting_repair_approval", "Засвар шалгагдаж байна"),
    ("done", "Дууссан"),
    ("rejected", "Татгалзсан"),
    ("cancelled", "Цуцлагдсан"),
]

PRIORITY_LEVEL_SELECTION = [
    ("0", "Бага"),
    ("1", "Дунд"),
    ("2", "Өндөр"),
    ("3", "Яаралтай"),
]


class FleetRepairRequest(models.Model):
    _name = "fleet.repair.request"
    _description = "Fleet Repair Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(default="New", readonly=True, copy=False, tracking=True)
    active = fields.Boolean(default=True)
    state = fields.Selection(
        REQUEST_STATE_SELECTION,
        default="draft",
        tracking=True,
        index=True,
    )

    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Машин",
        required=True,
        tracking=True,
        index=True,
    )
    repair_task_id = fields.Many2one("project.task", string="Засварын task", tracking=True)
    project_id = fields.Many2one("project.project", string="Төсөл")
    license_plate = fields.Char(related="vehicle_id.license_plate", store=True)
    vehicle_model_display = fields.Char(
        string="Загвар",
        compute="_compute_vehicle_model_display",
    )

    inspection_date = fields.Datetime(
        string="Үзлэг хийсэн огноо",
        default=fields.Datetime.now,
        tracking=True,
    )
    mechanic_id = fields.Many2one(
        "res.users",
        string="Механик / үзлэг хийсэн",
        default=lambda self: self.env.user,
        tracking=True,
    )
    team_leader_id = fields.Many2one("res.users", string="Багийн ахлагч", tracking=True)
    issue_summary = fields.Char(string="Асуудлын товч", required=True, tracking=True)
    diagnosis_note = fields.Text(string="Онош")
    problem_description = fields.Text(string="Яг юу эвдэрсэн / юу засах шаардлагатай")
    recommended_work = fields.Text(string="Хийх шаардлагатай ажил")
    urgent_reason = fields.Text(string="Яаралтай шалтгаан")
    maintenance_category = fields.Selection(
        MAINTENANCE_CATEGORY_SELECTION,
        string="Төрөл",
        default="repair",
        required=True,
        tracking=True,
    )
    priority_level = fields.Selection(
        PRIORITY_LEVEL_SELECTION,
        default="1",
        string="Яаралтын түвшин",
        tracking=True,
    )

    odometer_value = fields.Float(string="Одометр / км")
    estimated_repair_hours = fields.Float(string="Тооцоот засварын цаг")
    expected_ready_datetime = fields.Datetime(string="Бэлэн болох хүлээгдэж буй хугацаа")
    breakdown_datetime = fields.Datetime(string="Эвдрэл гарсан хугацаа")
    downtime_start = fields.Datetime(string="Зогсолт эхэлсэн")
    downtime_end = fields.Datetime(string="Зогсолт дууссан")
    total_downtime_hours = fields.Float(
        string="Нийт зогсолтын цаг",
        compute="_compute_total_downtime_hours",
        store=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id.id,
        required=True,
    )
    estimated_amount = fields.Monetary(
        string="Тооцоот нийт дүн",
        currency_field="currency_id",
        compute="_compute_estimated_amount",
        store=True,
        tracking=True,
    )
    approved_amount = fields.Monetary(
        string="Батлагдсан дүн",
        currency_field="currency_id",
        tracking=True,
    )
    actual_purchase_amount = fields.Monetary(
        string="Бодит худалдан авалтын дүн",
        currency_field="currency_id",
        tracking=True,
    )
    approval_threshold_amount = fields.Monetary(
        string="CEO босго дүн",
        currency_field="currency_id",
        compute="_compute_threshold_amount",
    )
    needs_ceo_approval = fields.Boolean(
        string="CEO баталгаа шаардлагатай",
        compute="_compute_needs_ceo_approval",
        store=True,
        tracking=True,
    )

    accounting_reviewer_id = fields.Many2one("res.users", string="Санхүү хянагч", tracking=True)
    accounting_review_datetime = fields.Datetime(string="Санхүү хянасан хугацаа")
    admin_reviewer_id = fields.Many2one("res.users", string="Захиргаа хариуцсан", tracking=True)
    admin_review_datetime = fields.Datetime(string="Захиргаа хянасан хугацаа")
    ceo_approver_id = fields.Many2one("res.users", string="Захирал", tracking=True)
    ceo_approval_datetime = fields.Datetime(string="Захирал шийдвэрлэсэн хугацаа")
    finance_prepared_by_id = fields.Many2one("res.users", string="Хөрөнгө бэлдсэн санхүү", tracking=True)
    finance_prepared_datetime = fields.Datetime(string="Хөрөнгө бэлэн болсон хугацаа")
    purchaser_id = fields.Many2one("res.users", string="Нярав / худалдан авалт", tracking=True)
    purchase_datetime = fields.Datetime(string="Худалдан авалт хийсэн хугацаа")
    parts_received_datetime = fields.Datetime(string="Сэлбэг хүлээн авсан хугацаа")
    repair_completed_datetime = fields.Datetime(string="Засвар бүрэн дууссан хугацаа")
    general_manager_id = fields.Many2one("res.users", string="Ерөнхий менежер", tracking=True)

    director_order_number = fields.Char(string="Захирлын тушаалын дугаар", tracking=True)
    director_order_date = fields.Date(string="Захирлын тушаалын огноо", tracking=True)
    director_order_attachment_id = fields.Many2one("ir.attachment", string="Захирлын тушаал файл")
    rejection_reason = fields.Text(string="Татгалзсан шалтгаан")
    internal_note = fields.Text(string="Дотоод тэмдэглэл")

    line_ids = fields.One2many(
        "fleet.repair.request.line",
        "request_id",
        string="Сэлбэгийн мөрүүд",
    )
    vendor_id = fields.Many2one(
        "res.partner",
        string="Нийлүүлэгч",
        domain="[('supplier_rank', '>', 0)]",
        tracking=True,
    )
    purchase_order_id = fields.Many2one("purchase.order", string="Холбогдсон PO/RFQ")
    purchase_count = fields.Integer(compute="_compute_procurement_counters")
    line_count = fields.Integer(compute="_compute_procurement_counters")
    can_create_purchase = fields.Boolean(compute="_compute_procurement_counters")

    current_responsible_user_id = fields.Many2one(
        "res.users",
        string="Одоогийн хариуцагч",
        compute="_compute_current_responsible_user",
        store=True,
    )
    current_stage_age_days = fields.Float(
        string="Одоогийн шатанд саатсан өдөр",
        compute="_compute_current_stage_age_days",
    )
    workflow_started_at = fields.Datetime(default=fields.Datetime.now)
    last_state_change_at = fields.Datetime(tracking=True)
    total_cycle_hours = fields.Float(
        string="Нийт цикл цаг",
        compute="_compute_total_cycle_hours",
    )
    blocked_reason = fields.Char(string="Саатлын шалтгаан")
    is_overdue = fields.Boolean(
        string="Хугацаа хэтэрсэн",
        compute="_compute_is_overdue",
        search="_search_is_overdue",
    )

    inspection_image_ids = fields.Many2many(
        "ir.attachment",
        "fleet_repair_request_inspection_rel",
        "request_id",
        "attachment_id",
        string="Үзлэгийн зураг",
    )
    repair_result_image_ids = fields.Many2many(
        "ir.attachment",
        "fleet_repair_request_result_rel",
        "request_id",
        "attachment_id",
        string="Засварын дараах зураг",
    )

    @api.model
    def _get_ceo_threshold_amount(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "fleet_repair_workflow.repair_ceo_threshold_amount",
            default="1000000",
        )
        try:
            return float(value)
        except (TypeError, ValueError):
            return 1000000.0

    @api.depends("vehicle_id.model_id", "vehicle_id.model_id.brand_id")
    def _compute_vehicle_model_display(self):
        for request in self:
            if request.vehicle_id.model_id:
                brand = request.vehicle_id.model_id.brand_id.display_name or ""
                model = request.vehicle_id.model_id.display_name or ""
                request.vehicle_model_display = " ".join(part for part in [brand, model] if part).strip()
            else:
                request.vehicle_model_display = request.vehicle_id.display_name or ""

    @api.depends("line_ids.estimated_subtotal")
    def _compute_estimated_amount(self):
        for request in self:
            request.estimated_amount = sum(request.line_ids.mapped("estimated_subtotal"))

    def _compute_threshold_amount(self):
        threshold = self._get_ceo_threshold_amount()
        for request in self:
            request.approval_threshold_amount = threshold

    @api.depends("estimated_amount")
    def _compute_needs_ceo_approval(self):
        threshold = self._get_ceo_threshold_amount()
        for request in self:
            request.needs_ceo_approval = request.estimated_amount > threshold

    @api.depends("downtime_start", "downtime_end")
    def _compute_total_downtime_hours(self):
        now_dt = fields.Datetime.now()
        for request in self:
            if not request.downtime_start:
                request.total_downtime_hours = 0.0
                continue
            start_dt = fields.Datetime.to_datetime(request.downtime_start)
            end_dt = fields.Datetime.to_datetime(request.downtime_end or now_dt)
            request.total_downtime_hours = max((end_dt - start_dt).total_seconds(), 0.0) / 3600.0

    @api.depends(
        "state",
        "accounting_reviewer_id",
        "admin_reviewer_id",
        "ceo_approver_id",
        "finance_prepared_by_id",
        "purchaser_id",
        "mechanic_id",
        "team_leader_id",
        "repair_task_id.user_ids",
    )
    def _compute_current_responsible_user(self):
        for request in self:
            responsible = False
            if request.state == "waiting_accounting":
                responsible = request.accounting_reviewer_id or request._get_first_group_user(
                    "fleet_repair_workflow.group_fleet_repair_accounting"
                )
            elif request.state == "waiting_admin":
                responsible = request.admin_reviewer_id or request._get_first_group_user(
                    "fleet_repair_workflow.group_fleet_repair_administration"
                )
            elif request.state == "waiting_ceo":
                responsible = request.ceo_approver_id or request._get_first_group_user(
                    "fleet_repair_workflow.group_fleet_repair_ceo"
                )
            elif request.state == "admin_order_ready":
                responsible = request.finance_prepared_by_id or request._get_first_group_user(
                    "fleet_repair_workflow.group_fleet_repair_finance"
                )
            elif request.state in {"fund_prepared", "purchasing"}:
                responsible = request.purchaser_id or request._get_first_group_user(
                    "fleet_repair_workflow.group_fleet_repair_purchaser"
                )
            elif request.state in {"parts_received", "in_repair"}:
                responsible = request.mechanic_id or request.repair_task_id.user_ids[:1]
            elif request.state == "waiting_repair_approval":
                responsible = request.team_leader_id or request._get_first_group_user(
                    "fleet_repair_workflow.group_fleet_repair_manager"
                )
            request.current_responsible_user_id = responsible

    def _compute_current_stage_age_days(self):
        now_dt = fields.Datetime.now()
        for request in self:
            if request.last_state_change_at:
                start_dt = fields.Datetime.to_datetime(request.last_state_change_at)
                request.current_stage_age_days = max((now_dt - start_dt).total_seconds(), 0.0) / 86400.0
            else:
                request.current_stage_age_days = 0.0

    def _compute_total_cycle_hours(self):
        now_dt = fields.Datetime.now()
        for request in self:
            start_dt = request.workflow_started_at or request.create_date
            end_dt = request.repair_completed_datetime or (now_dt if request.state not in {"draft", "cancelled"} else False)
            if start_dt and end_dt:
                start_dt = fields.Datetime.to_datetime(start_dt)
                end_dt = fields.Datetime.to_datetime(end_dt)
                request.total_cycle_hours = max((end_dt - start_dt).total_seconds(), 0.0) / 3600.0
            else:
                request.total_cycle_hours = 0.0

    def _compute_is_overdue(self):
        now_dt = fields.Datetime.now()
        for request in self:
            request.is_overdue = bool(
                request.expected_ready_datetime
                and request.expected_ready_datetime < now_dt
                and request.state not in {"done", "cancelled", "rejected"}
            )

    def _search_is_overdue(self, operator, value):
        overdue_domain = [
            ("expected_ready_datetime", "<", fields.Datetime.now()),
            ("state", "not in", ["done", "cancelled", "rejected"]),
        ]
        if (operator in ("=", "==") and value) or (operator == "!=" and not value):
            return overdue_domain
        return ["!"] + overdue_domain

    def _compute_procurement_counters(self):
        for request in self:
            request.line_count = len(request.line_ids)
            request.purchase_count = 1 if request.purchase_order_id else 0
            request.can_create_purchase = bool(
                request.state in {"fund_prepared", "purchasing"}
                and not request.purchase_order_id
                and request.line_ids
            )

    @api.constrains("estimated_amount", "actual_purchase_amount", "downtime_start", "downtime_end")
    def _check_request_values(self):
        for request in self:
            if request.estimated_amount < 0:
                raise ValidationError("Тооцоот нийт дүн сөрөг байж болохгүй.")
            if request.actual_purchase_amount < 0:
                raise ValidationError("Бодит худалдан авалтын дүн сөрөг байж болохгүй.")
            if (
                request.downtime_start
                and request.downtime_end
                and request.downtime_end < request.downtime_start
            ):
                raise ValidationError("Зогсолт дууссан хугацаа эхэлсэн хугацаанаас өмнө байж болохгүй.")

    @api.model_create_multi
    def create(self, vals_list):
        now_dt = fields.Datetime.now()
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("fleet.repair.request") or "New"
            vals.setdefault("last_state_change_at", now_dt)
            vals.setdefault("workflow_started_at", now_dt)
            if not vals.get("downtime_start") and vals.get("breakdown_datetime"):
                vals["downtime_start"] = vals["breakdown_datetime"]
        return super().create(vals_list)

    def write(self, vals):
        if "state" in vals and "last_state_change_at" not in vals:
            vals = dict(vals, last_state_change_at=fields.Datetime.now())
        result = super().write(vals)
        if "state" in vals and not self.env.context.get("skip_task_sync"):
            self._sync_task_for_request_state()
        return result

    def action_open_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "fleet.repair.request",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }

    def action_view_vehicle(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.vehicle_id.display_name,
            "res_model": "fleet.vehicle",
            "view_mode": "form",
            "view_id": self.env.ref("fleet.fleet_vehicle_view_form").id,
            "res_id": self.vehicle_id.id,
            "target": "current",
        }

    def action_view_repair_task(self):
        self.ensure_one()
        if not self.repair_task_id:
            raise UserError("Холбогдсон засварын task үүсээгүй байна.")
        return {
            "type": "ir.actions.act_window",
            "name": self.repair_task_id.display_name,
            "res_model": "project.task",
            "view_mode": "form",
            "view_id": self.env.ref("project.view_task_form2").id,
            "res_id": self.repair_task_id.id,
            "target": "current",
        }

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_order_id:
            raise UserError("Холбогдсон худалдан авалтын баримт алга байна.")
        return {
            "type": "ir.actions.act_window",
            "name": self.purchase_order_id.display_name,
            "res_model": "purchase.order",
            "view_mode": "form",
            "view_id": self.env.ref("purchase.purchase_order_form").id,
            "res_id": self.purchase_order_id.id,
            "target": "current",
        }

    def action_view_activities(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Үйл ажиллагаанууд",
            "res_model": "mail.activity",
            "view_mode": "list,form",
            "domain": [("res_model", "=", self._name), ("res_id", "=", self.id)],
            "context": {"default_res_model": self._name, "default_res_id": self.id},
            "target": "current",
        }

    def action_view_attachments(self):
        self.ensure_one()
        attachment_ids = (
            self.inspection_image_ids
            | self.repair_result_image_ids
            | self.director_order_attachment_id
        ).ids
        return {
            "type": "ir.actions.act_window",
            "name": "Хавсралтууд",
            "res_model": "ir.attachment",
            "view_mode": "list,form",
            "domain": [("id", "in", attachment_ids)],
            "target": "current",
        }

    def _get_first_group_user(self, xmlid_group):
        group = self.env.ref(xmlid_group, raise_if_not_found=False)
        if not group:
            return self.env["res.users"]
        return group.sudo().users.filtered(lambda user: user.active)[:1]

    def _get_group_users(self, xmlid_group):
        group = self.env.ref(xmlid_group, raise_if_not_found=False)
        if not group:
            return self.env["res.users"]
        return group.sudo().users.filtered(lambda user: user.active)

    def _get_activity_type(self):
        return self.env.ref(
            "fleet_repair_workflow.mail_activity_type_repair_workflow",
            raise_if_not_found=False,
        ) or self.env.ref("mail.mail_activity_data_todo")

    def _activity_schedule_for_group(self, xmlid_group, summary, note=None):
        self._activity_schedule_for_users(self._get_group_users(xmlid_group), summary, note=note)

    def _activity_schedule_for_users(self, user_ids, summary, note=None):
        activity_type = self._get_activity_type()
        for record in self:
            for user in user_ids:
                existing = record.activity_ids.filtered(
                    lambda activity: activity.user_id == user
                    and activity.summary == summary
                    and activity.activity_type_id == activity_type
                )
                if existing:
                    continue
                record.activity_schedule(
                    activity_type_id=activity_type.id,
                    user_id=user.id,
                    summary=summary,
                    note=note or "",
                    date_deadline=fields.Date.today(),
                )

    def _activity_mark_done_for_current_users(self):
        activity_type = self._get_activity_type()
        for record in self:
            activities = record.activity_ids.filtered(
                lambda activity: activity.user_id == self.env.user and activity.activity_type_id == activity_type
            )
            for activity in activities:
                activity.action_feedback(feedback=_("Шат ахисан."))

    def _ensure_users_or_raise(self, specific_user, xmlid_group, role_label):
        users = specific_user or self._get_group_users(xmlid_group)
        if not users:
            raise UserError(_("%s хэрэглэгч тохируулагдаагүй байна. Хэрэглэгчийг бүлэгт онооно уу.") % role_label)
        return users

    def _check_any_group(self, xmlids):
        if self.env.is_superuser():
            return True
        return any(self.env.user.has_group(xmlid) for xmlid in xmlids)

    def _check_state(self, allowed_states):
        for request in self:
            if request.state not in allowed_states:
                state_label = dict(self._fields["state"].selection).get(request.state, request.state)
                raise UserError(_("Энэ үйлдлийг '%s' төлөвөөс хийх боломжгүй.") % state_label)

    def _post_transition_message(self, body):
        for request in self:
            request.message_post(body=body)

    def _set_state(self, new_state):
        self.write({"state": new_state, "last_state_change_at": fields.Datetime.now()})

    def _prepare_task_name(self):
        self.ensure_one()
        vehicle_name = self.vehicle_model_display or self.vehicle_id.display_name or ""
        parts = [self.license_plate or "", vehicle_name, self.issue_summary or ""]
        return " - ".join(part.strip() for part in parts if part and part.strip())

    def _prepare_task_values(self):
        self.ensure_one()
        user_ids = [user.id for user in (self.team_leader_id | self.mechanic_id) if user]
        values = {
            "name": self._prepare_task_name(),
            "is_vehicle_repair_task": True,
            "vehicle_id": self.vehicle_id.id,
            "repair_request_id": self.id,
            "issue_summary": self.issue_summary,
            "diagnosis_note": self.diagnosis_note,
            "estimated_repair_hours": self.estimated_repair_hours,
            "expected_ready_datetime": self.expected_ready_datetime,
            "maintenance_category": self.maintenance_category,
            "project_id": self.project_id.id or False,
            "repair_result": "waiting_parts" if self.line_ids else False,
        }
        if user_ids:
            values["user_ids"] = [Command.set(user_ids)]
        return values

    def _ensure_repair_task(self):
        task_model = self.env["project.task"]
        for request in self:
            task_values = request._prepare_task_values()
            if request.repair_task_id:
                request.repair_task_id.with_context(skip_repair_request_sync=True).write(task_values)
            else:
                request.repair_task_id = task_model.with_context(skip_repair_request_sync=True).create(task_values)

    def _find_project_stage(self, stage_names):
        self.ensure_one()
        stage_model = self.env["project.task.type"]
        domain = []
        if self.project_id:
            domain = ["|", ("project_ids", "=", False), ("project_ids", "=", self.project_id.id)]
        for stage_name in stage_names:
            stage = stage_model.search(domain + [("name", "ilike", stage_name)], limit=1)
            if stage:
                return stage
        return stage_model

    def _sync_task_for_request_state(self):
        in_progress_names = ["In Progress", "Progress", "Засварт", "Хийгдэж байна", "In Repair"]
        done_names = ["Done", "Completed", "Дууссан", "Хаагдсан"]
        for request in self.filtered("repair_task_id"):
            task = request.repair_task_id.with_context(skip_repair_request_sync=True)
            if request.state in {"parts_received", "in_repair", "waiting_repair_approval"}:
                stage = request._find_project_stage(in_progress_names)
                if stage:
                    task.write({"stage_id": stage.id})
            elif request.state == "done":
                values = {"repair_end_datetime": request.repair_completed_datetime or fields.Datetime.now()}
                stage = request._find_project_stage(done_names)
                if stage:
                    values["stage_id"] = stage.id
                if task.repair_start_datetime and not task.actual_repair_hours:
                    start_dt = fields.Datetime.to_datetime(task.repair_start_datetime)
                    end_dt = fields.Datetime.to_datetime(values["repair_end_datetime"])
                    values["actual_repair_hours"] = max((end_dt - start_dt).total_seconds(), 0.0) / 3600.0
                if not task.repair_result:
                    values["repair_result"] = "fixed"
                task.write(values)

    def _mark_waiting_repair_approval_from_task(self):
        for request in self.filtered(lambda record: record.state in {"parts_received", "in_repair"}):
            request._set_state("waiting_repair_approval")
            request._activity_schedule_for_users(
                (request.team_leader_id | request.general_manager_id)
                or request._get_group_users("fleet_repair_workflow.group_fleet_repair_manager"),
                "Засвар баталгаажуулах хүлээгдэж байна",
                note=_("Холбогдсон task дууссан тул засварын хүсэлтийг шалгана уу."),
            )
            request._post_transition_message("Холбогдсон task дууссан тул хүсэлт шалгалтын шат руу шилжлээ.")

    def _prepare_purchase_line_commands(self):
        self.ensure_one()
        commands = []
        for line in self.line_ids.sorted(key=lambda item: (item.sequence, item.id)):
            if line.product_id:
                description = line.name
                if line.specification:
                    description = "%s\n%s" % (description, line.specification)
                commands.append(
                    Command.create(
                        {
                            "product_id": line.product_id.id,
                            "name": description,
                            "product_qty": line.quantity,
                            "product_uom_id": line.product_id.uom_po_id.id or line.product_id.uom_id.id,
                            "price_unit": line.estimated_unit_price or 0.0,
                            "date_planned": fields.Datetime.now(),
                        }
                    )
                )
            else:
                note = line.name
                if line.specification:
                    note = "%s (%s)" % (note, line.specification)
                if line.note:
                    note = "%s\n%s" % (note, line.note)
                commands.append(Command.create({"display_type": "line_note", "name": note}))

        return commands

    def _infer_vendor(self):
        self.ensure_one()
        if self.vendor_id:
            return self.vendor_id
        vendor_candidates = self.env["res.partner"]
        for line in self.line_ids.filtered("product_id"):
            seller = line.product_id.product_tmpl_id.seller_ids[:1].name
            if seller:
                vendor_candidates |= seller
        return vendor_candidates if len(vendor_candidates) == 1 else self.env["res.partner"]

    def action_submit_inspection(self):
        self._check_state({"draft"})
        accounting_group = "fleet_repair_workflow.group_fleet_repair_accounting"
        for request in self:
            if not request.issue_summary:
                raise UserError("Асуудлын товчыг бөглөнө үү.")
            if not request.line_ids and not request.problem_description:
                raise UserError("Сэлбэгийн мөр эсвэл эвдрэлийн тайлбарын аль нэгийг бөглөнө үү.")
            request._ensure_users_or_raise(request.accounting_reviewer_id, accounting_group, "Санхүүгийн хянагч")
            request._ensure_repair_task()
            if not request.downtime_start:
                request.downtime_start = request.breakdown_datetime or fields.Datetime.now()
            request._activity_mark_done_for_current_users()
            request._set_state("waiting_accounting")
            request._activity_schedule_for_users(
                request.accounting_reviewer_id or request._get_group_users(accounting_group),
                "Засварын хүсэлтийг шалгана уу",
                note=_("%s хүсэлтийн тооцоо болон бүрдлийг шалгана уу.") % request.name,
            )
            request._post_transition_message("Үзлэгийн мэдээлэл илгээгдэж, санхүүгийн хяналтын шатанд шилжлээ.")
        return True

    def action_accounting_review_pass(self):
        self._check_state({"waiting_accounting"})
        if not self._check_any_group(
            ["fleet_repair_workflow.group_fleet_repair_accounting", "fleet_repair_workflow.group_fleet_repair_manager"]
        ):
            raise AccessError("Энэ үйлдлийг зөвхөн санхүүгийн хэрэглэгч хийж болно.")
        admin_group = "fleet_repair_workflow.group_fleet_repair_administration"
        for request in self:
            request._ensure_users_or_raise(request.admin_reviewer_id, admin_group, "Захиргааны хэрэглэгч")
            request._activity_mark_done_for_current_users()
            request.write(
                {
                    "accounting_reviewer_id": self.env.user.id,
                    "accounting_review_datetime": fields.Datetime.now(),
                }
            )
            request._set_state("waiting_admin")
            request._activity_schedule_for_users(
                request.admin_reviewer_id or request._get_group_users(admin_group),
                "Захиргааны хяналт шаардлагатай",
                note=_("%s хүсэлтийн худалдан авалтын хэрэгцээг шалгана уу.") % request.name,
            )
            request._post_transition_message("Санхүүгийн хяналт дуусч, хүсэлт захиргааны шат руу шилжлээ.")
        return True

    def action_admin_review_pass(self):
        self._check_state({"waiting_admin"})
        if not self._check_any_group(
            ["fleet_repair_workflow.group_fleet_repair_administration", "fleet_repair_workflow.group_fleet_repair_manager"]
        ):
            raise AccessError("Энэ үйлдлийг зөвхөн захиргааны хэрэглэгч хийж болно.")
        ceo_group = "fleet_repair_workflow.group_fleet_repair_ceo"
        for request in self:
            request._activity_mark_done_for_current_users()
            values = {
                "admin_reviewer_id": self.env.user.id,
                "admin_review_datetime": fields.Datetime.now(),
            }
            if not request.needs_ceo_approval and not request.approved_amount:
                values["approved_amount"] = request.estimated_amount
            request.write(values)
            if request.needs_ceo_approval:
                request._ensure_users_or_raise(request.ceo_approver_id, ceo_group, "Захирал")
                request._set_state("waiting_ceo")
                request._activity_schedule_for_users(
                    request.ceo_approver_id or request._get_group_users(ceo_group),
                    "CEO баталгаа шаардлагатай",
                    note=_("%s хүсэлт босго дүнгээс давсан тул шийдвэрлэнэ үү.") % request.name,
                )
                request._post_transition_message("Захиргааны хяналт дуусч, хүсэлт захирлын баталгааны шатанд шилжлээ.")
            else:
                request._set_state("admin_order_ready")
                request._post_transition_message("Захиргааны хяналт дуусч, тушаал бэлтгэх шатанд шилжлээ.")
        return True

    def action_ceo_approve(self):
        self._check_state({"waiting_ceo"})
        if not self._check_any_group(
            ["fleet_repair_workflow.group_fleet_repair_ceo", "fleet_repair_workflow.group_fleet_repair_manager"]
        ):
            raise AccessError("Энэ үйлдлийг зөвхөн захирал хийж болно.")
        admin_group = "fleet_repair_workflow.group_fleet_repair_administration"
        for request in self:
            request._ensure_users_or_raise(request.admin_reviewer_id, admin_group, "Захиргааны хэрэглэгч")
            request._activity_mark_done_for_current_users()
            request.write(
                {
                    "ceo_approver_id": self.env.user.id,
                    "ceo_approval_datetime": fields.Datetime.now(),
                    "approved_amount": request.approved_amount or request.estimated_amount,
                }
            )
            request._set_state("admin_order_ready")
            request._activity_schedule_for_users(
                request.admin_reviewer_id or request._get_group_users(admin_group),
                "Захирлын тушаал бэлтгэнэ үү",
                note=_("%s хүсэлтийг захирал зөвшөөрсөн.") % request.name,
            )
            request._post_transition_message("Захирал хүсэлтийг зөвшөөрч, тушаал бэлтгэх шат руу шилжүүллээ.")
        return True

    def action_ceo_reject(self):
        self.ensure_one()
        self._check_state({"waiting_ceo"})
        if not self._check_any_group(
            ["fleet_repair_workflow.group_fleet_repair_ceo", "fleet_repair_workflow.group_fleet_repair_manager"]
        ):
            raise AccessError("Энэ үйлдлийг зөвхөн захирал хийж болно.")
        return {
            "type": "ir.actions.act_window",
            "name": "Татгалзсан шалтгаан",
            "res_model": "fleet.repair.request.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_apply_rejection_reason(self, rejection_reason):
        gm_users = self.general_manager_id or self._get_group_users(
            "fleet_repair_workflow.group_fleet_repair_general_manager"
        )
        for request in self:
            request._activity_mark_done_for_current_users()
            request.write(
                {
                    "rejection_reason": rejection_reason,
                    "ceo_approver_id": request.ceo_approver_id or self.env.user.id,
                    "ceo_approval_datetime": request.ceo_approval_datetime or fields.Datetime.now(),
                }
            )
            request._set_state("rejected")
            request._activity_schedule_for_users(
                request.mechanic_id | request.team_leader_id | gm_users,
                "Хүсэлт татгалзагдсан",
                note=rejection_reason,
            )
            request._post_transition_message("Захирал хүсэлтийг татгалзлаа.<br/>Шалтгаан: %s" % rejection_reason)
        return True

    def action_admin_mark_order_ready(self):
        self._check_state({"admin_order_ready"})
        if not self._check_any_group(
            ["fleet_repair_workflow.group_fleet_repair_administration", "fleet_repair_workflow.group_fleet_repair_manager"]
        ):
            raise AccessError("Энэ үйлдлийг зөвхөн захиргааны хэрэглэгч хийж болно.")
        finance_group = "fleet_repair_workflow.group_fleet_repair_finance"
        for request in self:
            if not (
                request.director_order_number
                or request.director_order_attachment_id
                or request.director_order_date
            ):
                raise UserError("Тушаалын дугаар, огноо эсвэл хавсралтын аль нэгийг бүртгэнэ үү.")
            request._ensure_users_or_raise(request.finance_prepared_by_id, finance_group, "Санхүүгийн хэрэглэгч")
            request._activity_mark_done_for_current_users()
            if not request.director_order_date:
                request.write({"director_order_date": fields.Date.today()})
            request._activity_schedule_for_users(
                request.finance_prepared_by_id or request._get_group_users(finance_group),
                "Хөрөнгө бэлтгэнэ үү",
                note=_("%s хүсэлтийн тушаал бэлэн болсон.") % request.name,
            )
            request._post_transition_message("Захирлын тушаал бэлэн болж, санхүүд мэдэгдлээ.")
        return True

    def action_finance_prepare_fund(self):
        self._check_state({"admin_order_ready"})
        if not self._check_any_group(
            ["fleet_repair_workflow.group_fleet_repair_finance", "fleet_repair_workflow.group_fleet_repair_manager"]
        ):
            raise AccessError("Энэ үйлдлийг зөвхөн санхүүгийн хэрэглэгч хийж болно.")
        purchaser_group = "fleet_repair_workflow.group_fleet_repair_purchaser"
        for request in self:
            request._ensure_users_or_raise(request.purchaser_id, purchaser_group, "Худалдан авалтын хэрэглэгч")
            request._activity_mark_done_for_current_users()
            request.write(
                {
                    "finance_prepared_by_id": self.env.user.id,
                    "finance_prepared_datetime": fields.Datetime.now(),
                    "approved_amount": request.approved_amount or request.estimated_amount,
                }
            )
            request._set_state("fund_prepared")
            request._activity_schedule_for_users(
                request.purchaser_id or request._get_group_users(purchaser_group),
                "Худалдан авалт эхлүүлнэ үү",
                note=_("%s хүсэлтийн хөрөнгө бэлэн боллоо.") % request.name,
            )
            request._post_transition_message("Санхүү хөрөнгийг баталгаажуулж, худалдан авалтын шат руу шилжүүллээ.")
        return True

    def action_start_purchasing(self):
        self._check_state({"fund_prepared"})
        if not self._check_any_group(
            ["fleet_repair_workflow.group_fleet_repair_purchaser", "fleet_repair_workflow.group_fleet_repair_manager"]
        ):
            raise AccessError("Энэ үйлдлийг зөвхөн худалдан авалтын хэрэглэгч хийж болно.")
        for request in self:
            request._activity_mark_done_for_current_users()
            request.write(
                {
                    "purchaser_id": request.purchaser_id.id or self.env.user.id,
                    "purchase_datetime": request.purchase_datetime or fields.Datetime.now(),
                }
            )
            request._set_state("purchasing")
            request._post_transition_message("Худалдан авалтын ажиллагаа эхэллээ.")
        return True

    def action_mark_parts_received(self):
        self._check_state({"purchasing"})
        if not self._check_any_group(
            ["fleet_repair_workflow.group_fleet_repair_purchaser", "fleet_repair_workflow.group_fleet_repair_manager"]
        ):
            raise AccessError("Энэ үйлдлийг зөвхөн худалдан авалтын хэрэглэгч хийж болно.")
        for request in self:
            request._activity_mark_done_for_current_users()
            request.write(
                {
                    "parts_received_datetime": fields.Datetime.now(),
                    "actual_purchase_amount": request.actual_purchase_amount
                    or sum(request.line_ids.mapped("actual_subtotal"))
                    or (request.purchase_order_id.amount_total if request.purchase_order_id else 0.0),
                }
            )
            request.line_ids.write({"purchased": True})
            request._set_state("parts_received")
            if request.repair_task_id and request.repair_task_id.repair_result == "waiting_parts":
                request.repair_task_id.with_context(skip_repair_request_sync=True).message_post(
                    body="Сэлбэг хүлээн авсан тул засварыг үргэлжлүүлэх боломжтой боллоо."
                )
            request._activity_schedule_for_users(
                request.mechanic_id | request.team_leader_id,
                "Сэлбэг ирсэн тул засварыг эхлүүлнэ үү",
                note=_("%s хүсэлтийн сэлбэг ирсэн байна.") % request.name,
            )
            request._post_transition_message("Сэлбэг хүлээн авч, засварт оруулахад бэлэн боллоо.")
        return True

    def action_start_repair(self):
        self._check_state({"parts_received"})
        if not self._check_any_group(
            [
                "fleet_repair_workflow.group_fleet_repair_mechanic",
                "fleet_repair_workflow.group_fleet_repair_team_leader",
                "fleet_repair_workflow.group_fleet_repair_manager",
            ]
        ):
            raise AccessError("Энэ үйлдлийг механик, багийн ахлагч эсвэл менежер хийж болно.")
        for request in self:
            request._activity_mark_done_for_current_users()
            request._set_state("in_repair")
            if request.repair_task_id and not request.repair_task_id.repair_start_datetime:
                request.repair_task_id.with_context(skip_repair_request_sync=True).write(
                    {"repair_start_datetime": fields.Datetime.now()}
                )
            request._post_transition_message("Засварын ажил эхэллээ.")
        return True

    def action_submit_repair_for_approval(self):
        self._check_state({"in_repair"})
        if not self._check_any_group(
            [
                "fleet_repair_workflow.group_fleet_repair_mechanic",
                "fleet_repair_workflow.group_fleet_repair_team_leader",
                "fleet_repair_workflow.group_fleet_repair_manager",
            ]
        ):
            raise AccessError("Энэ үйлдлийг механик, багийн ахлагч эсвэл менежер хийж болно.")
        for request in self:
            request._activity_mark_done_for_current_users()
            request._set_state("waiting_repair_approval")
            request._activity_schedule_for_users(
                (request.team_leader_id | request.general_manager_id)
                or request._get_group_users("fleet_repair_workflow.group_fleet_repair_manager"),
                "Засварын үр дүнг шалгана уу",
                note=_("%s хүсэлтийн засвар дуусч шалгалт хүлээж байна.") % request.name,
            )
            request._post_transition_message("Засварын ажил дуусч, шалгалтын шатанд илгээгдлээ.")
        return True

    def action_complete_repair(self):
        self._check_state({"waiting_repair_approval"})
        if not self._check_any_group(
            ["fleet_repair_workflow.group_fleet_repair_team_leader", "fleet_repair_workflow.group_fleet_repair_manager"]
        ):
            raise AccessError("Энэ үйлдлийг багийн ахлагч эсвэл менежер хийж болно.")
        for request in self:
            if not request.parts_received_datetime:
                raise UserError("Сэлбэг хүлээн авсан бүртгэлгүй хүсэлтийг дуусгах боломжгүй.")
            now_dt = fields.Datetime.now()
            request._activity_mark_done_for_current_users()
            request.write(
                {
                    "repair_completed_datetime": now_dt,
                    "downtime_end": request.downtime_end or now_dt,
                }
            )
            request._set_state("done")
            if request.repair_task_id:
                values = {
                    "repair_end_datetime": now_dt,
                    "approved_by_id": self.env.user.id,
                    "repair_result": request.repair_task_id.repair_result or "fixed",
                }
                if request.repair_task_id.repair_start_datetime and not request.repair_task_id.actual_repair_hours:
                    start_dt = fields.Datetime.to_datetime(request.repair_task_id.repair_start_datetime)
                    values["actual_repair_hours"] = max((now_dt - start_dt).total_seconds(), 0.0) / 3600.0
                request.repair_task_id.with_context(skip_repair_request_sync=True).write(values)
            request._post_transition_message("Засварын хүсэлт бүрэн дууслаа.")
        return True

    def action_cancel(self):
        self._check_state(set(state for state, _label in REQUEST_STATE_SELECTION if state != "done"))
        for request in self.filtered(lambda record: record.state != "done"):
            request._activity_mark_done_for_current_users()
            request._set_state("cancelled")
            request._post_transition_message("Засварын хүсэлтийг цуцаллаа.")
        return True

    def action_reset_to_draft(self):
        self._check_state(
            {
                "waiting_accounting",
                "waiting_admin",
                "waiting_ceo",
                "admin_order_ready",
                "fund_prepared",
                "purchasing",
                "parts_received",
                "in_repair",
                "waiting_repair_approval",
                "rejected",
                "cancelled",
            }
        )
        if not self._check_any_group(["fleet_repair_workflow.group_fleet_repair_manager"]):
            raise AccessError("Энэ үйлдлийг зөвхөн менежер хийж болно.")
        for request in self:
            request._activity_mark_done_for_current_users()
            request._set_state("draft")
            request._post_transition_message("Хүсэлтийг ноорог төлөв рүү буцаалаа.")
        return True

    def action_create_purchase_order(self):
        self.ensure_one()
        if self.purchase_order_id:
            return self.action_view_purchase_order()
        if self.state not in {"fund_prepared", "purchasing"}:
            raise UserError("PO/RFQ-г зөвхөн хөрөнгө бэлэн эсвэл худалдан авалтын шатанд үүсгэнэ.")
        vendor = self._infer_vendor()
        if not vendor or len(vendor) != 1:
            raise UserError("Odoo-ийн Purchase Order нь нийлүүлэгч шаарддаг. Нийлүүлэгчийг сонгоно уу.")
        line_commands = self._prepare_purchase_line_commands()
        if not line_commands:
            raise UserError("PO/RFQ үүсгэхэд дор хаяж нэг мөр шаардлагатай.")
        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": vendor.id,
                "origin": self.name,
                "date_order": fields.Datetime.now(),
                "order_line": line_commands,
            }
        )
        self.write({"purchase_order_id": purchase_order.id, "vendor_id": vendor.id})
        self.message_post(body="Худалдан авалтын RFQ/PO үүсгэлээ: %s" % purchase_order.display_name)
        return self.action_view_purchase_order()

    @api.model
    def _cron_check_stalled_requests(self):
        reminder_states = {
            "waiting_accounting": "Санхүүгийн хяналт саатсан хүсэлт",
            "waiting_admin": "Захиргааны хяналт саатсан хүсэлт",
            "waiting_ceo": "CEO шийдвэр саатсан хүсэлт",
            "admin_order_ready": "Тушаал/санхүүжилт саатсан хүсэлт",
            "fund_prepared": "Худалдан авалт эхлээгүй хүсэлт",
            "purchasing": "Сэлбэг хүлээн авалт саатсан хүсэлт",
        }
        requests = self.search(
            [
                ("state", "in", list(reminder_states.keys())),
                ("last_state_change_at", "!=", False),
            ]
        )
        for request in requests.filtered(lambda record: record.current_stage_age_days >= 2.0):
            responsible = request.current_responsible_user_id
            if responsible:
                request._activity_schedule_for_users(
                    responsible,
                    reminder_states[request.state],
                    note=_("%s хүсэлт %s хоногоос дээш хугацаанд энэ шатанд байна.")
                    % (request.name, round(request.current_stage_age_days, 1)),
                )
            request.message_post(
                body=_("Автомат сануулга: хүсэлт %s шатанд %s өдөр саатаж байна.")
                % (
                    dict(request._fields["state"].selection).get(request.state),
                    round(request.current_stage_age_days, 1),
                )
            )
