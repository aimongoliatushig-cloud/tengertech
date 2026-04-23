from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command


THRESHOLD_AMOUNT = 1000000.0

REQUEST_STATE_SELECTION = [
    ("draft", "Ноорог"),
    ("quotation_waiting", "Үнийн санал хүлээж байна"),
    ("quotations_ready", "3 үнийн санал оруулсан"),
    ("finance_review", "Санхүү хянаж байна"),
    ("order_preparing", "Тушаал бэлтгэж байна"),
    ("director_pending", "Захирлын шийдвэр хүлээж байна"),
    ("decision_approved", "Захирлын шийдвэр гарсан"),
    ("order_issued", "Тушаал гарсан"),
    ("contract_preparing", "Гэрээ байгуулж байна"),
    ("contract_signed", "Гэрээ байгуулсан"),
    ("paid", "Төлбөр хийсэн"),
    ("received", "Хүлээн авсан"),
    ("done", "Дууссан"),
    ("cancelled", "Цуцалсан"),
]

FLOW_TYPE_SELECTION = [
    ("low", "1 саяас доош"),
    ("high", "1 саяас дээш"),
]

PROCUREMENT_TYPE_SELECTION = [
    ("goods", "Бараа"),
    ("service", "Үйлчилгээ"),
    ("spare_part", "Сэлбэг"),
    ("other", "Бусад"),
]

URGENCY_SELECTION = [
    ("low", "Бага"),
    ("medium", "Дунд"),
    ("high", "Өндөр"),
    ("critical", "Яаралтай"),
]

PAYMENT_STATUS_SELECTION = [
    ("unpaid", "Төлбөр хүлээгдэж байна"),
    ("paid", "Төлбөр хийсэн"),
]

RECEIPT_STATUS_SELECTION = [
    ("pending", "Хүлээн авалт хүлээгдэж байна"),
    ("received", "Хүлээн авсан"),
]

DOCUMENT_TYPE_SELECTION = [
    ("quotation", "Үнийн санал"),
    ("director_order_draft", "Тушаалын ноорог"),
    ("director_order_final", "Эцсийн тушаал"),
    ("contract_draft", "Гэрээний ноорог"),
    ("contract_final", "Эцсийн гэрээ"),
    ("payment_proof", "Төлбөрийн баримт"),
    ("receipt_proof", "Хүлээн авалтын баримт"),
    ("other", "Бусад"),
]

NEXT_ROLE_BY_STATE = {
    "quotation_waiting": "municipal_procurement_workflow.group_mpw_storekeeper",
    "finance_review": "municipal_procurement_workflow.group_mpw_finance",
    "order_preparing": "municipal_procurement_workflow.group_mpw_office_clerk",
    "director_pending": "municipal_procurement_workflow.group_mpw_director",
    "decision_approved": "municipal_procurement_workflow.group_mpw_office_clerk",
    "order_issued": "municipal_procurement_workflow.group_mpw_contract_officer",
    "contract_preparing": "municipal_procurement_workflow.group_mpw_contract_officer",
    "contract_signed": "municipal_procurement_workflow.group_mpw_finance",
    "paid": "municipal_procurement_workflow.group_mpw_storekeeper",
}


class MPWProcurementRequest(models.Model):
    _name = "mpw.procurement.request"
    _description = "Procurement Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Дугаар", default="Шинэ", readonly=True, copy=False, tracking=True)
    title = fields.Char(string="Гарчиг", required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Компани",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Валют",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    project_id = fields.Many2one("project.project", string="Төсөл", tracking=True, index=True)
    task_id = fields.Many2one("project.task", string="Ажилбар", tracking=True, index=True)
    department_id = fields.Many2one("hr.department", string="Алба нэгж", tracking=True, index=True)
    requester_user_id = fields.Many2one(
        "res.users",
        string="Хүсэлт гаргагч",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
        tracking=True,
    )
    requester_employee_id = fields.Many2one(
        "hr.employee",
        string="Хүсэлт гаргагч ажилтан",
        default=lambda self: self._default_requester_employee(),
        readonly=True,
        tracking=True,
    )
    responsible_storekeeper_user_id = fields.Many2one(
        "res.users",
        string="Хариуцсан нярав",
        required=True,
        tracking=True,
    )
    available_storekeeper_user_ids = fields.Many2many(
        "res.users",
        string="Боломжтой нярав",
        compute="_compute_available_storekeeper_user_ids",
    )
    procurement_type = fields.Selection(
        PROCUREMENT_TYPE_SELECTION,
        string="Хэрэгцээний төрөл",
        default="goods",
        required=True,
        tracking=True,
    )
    urgency = fields.Selection(
        URGENCY_SELECTION,
        string="Яаралтай түвшин",
        default="medium",
        required=True,
        tracking=True,
    )
    description = fields.Text(string="Тайлбар / зорилго", tracking=True)
    required_date = fields.Date(string="Шаардлагатай огноо", tracking=True)
    state = fields.Selection(
        REQUEST_STATE_SELECTION,
        string="Төлөв",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    flow_type = fields.Selection(
        FLOW_TYPE_SELECTION,
        string="Урсгал",
        compute="_compute_flow_type",
        store=True,
        tracking=True,
    )
    selected_quotation_id = fields.Many2one(
        "mpw.procurement.quotation",
        string="Сонгосон үнийн санал",
        domain="[('request_id', '=', id)]",
        tracking=True,
    )
    selected_supplier_id = fields.Many2one(
        "res.partner",
        string="Сонгосон нийлүүлэгч",
        compute="_compute_selected_supplier_fields",
        store=True,
        tracking=True,
    )
    selected_supplier_total = fields.Monetary(
        string="Сонгосон нийлүүлэгчийн нийт дүн",
        currency_field="currency_id",
        compute="_compute_selected_supplier_fields",
        store=True,
        tracking=True,
    )
    payment_status = fields.Selection(
        PAYMENT_STATUS_SELECTION,
        string="Төлбөрийн төлөв",
        default="unpaid",
        required=True,
        tracking=True,
    )
    receipt_status = fields.Selection(
        RECEIPT_STATUS_SELECTION,
        string="Хүлээн авалтын төлөв",
        default="pending",
        required=True,
        tracking=True,
    )
    is_over_threshold = fields.Boolean(
        string="1 саяас дээш",
        compute="_compute_flow_type",
        store=True,
    )
    director_order_prepared_by = fields.Many2one("res.users", string="Тушаал бэлтгэсэн", tracking=True)
    director_order_attachment_count = fields.Integer(
        string="Тушаалын хавсралт",
        compute="_compute_document_counters",
    )
    contract_prepared_by = fields.Many2one("res.users", string="Гэрээ бэлтгэсэн", tracking=True)
    contract_attachment_count = fields.Integer(
        string="Гэрээний хавсралт",
        compute="_compute_document_counters",
    )
    finance_processed_by = fields.Many2one("res.users", string="Санхүүгийн ажилтан", tracking=True)
    received_by = fields.Many2one("res.users", string="Хүлээн авсан", tracking=True)
    date_quotation_submitted = fields.Datetime(string="Үнийн санал оруулсан огноо", tracking=True)
    date_director_decision = fields.Datetime(string="Захирлын шийдвэрийн огноо", tracking=True)
    date_order_issued = fields.Datetime(string="Тушаал гарсан огноо", tracking=True)
    date_contract_signed = fields.Datetime(string="Гэрээ байгуулсан огноо", tracking=True)
    date_paid = fields.Datetime(string="Төлбөр хийсэн огноо", tracking=True)
    date_received = fields.Datetime(string="Хүлээн авсан огноо", tracking=True)
    notes_internal = fields.Text(string="Дотоод тэмдэглэл")
    notes_user = fields.Text(string="Хэрэглэгчийн тэмдэглэл")
    payment_reference = fields.Char(string="Төлбөрийн лавлагаа", tracking=True)
    payment_date = fields.Date(string="Төлбөрийн өдөр", tracking=True)
    purchase_order_id = fields.Many2one("purchase.order", string="Холбогдсон худалдан авалтын захиалга")
    vendor_bill_id = fields.Many2one("account.move", string="Холбогдсон нийлүүлэгчийн нэхэмжлэл")
    receipt_picking_id = fields.Many2one("stock.picking", string="Холбогдсон орлогын баримт")
    workflow_started_at = fields.Datetime(default=fields.Datetime.now)
    last_state_change_at = fields.Datetime(default=fields.Datetime.now, tracking=True)
    current_stage_age_days = fields.Float(
        string="Одоогийн шатанд саатсан өдөр",
        compute="_compute_current_stage_age_days",
    )
    delay_days = fields.Float(string="Хоцролтын өдөр", compute="_compute_delay_metrics")
    is_delayed = fields.Boolean(
        string="Хоцорсон",
        compute="_compute_delay_metrics",
        search="_search_is_delayed",
    )
    current_responsible_user_id = fields.Many2one(
        "res.users",
        string="Одоогийн хариуцагч",
        compute="_compute_current_responsible_user_id",
        store=True,
    )
    stock_receipt_required = fields.Boolean(
        string="Агуулахын хүлээн авалт шаардлагатай",
        compute="_compute_receipt_requirements",
        store=True,
    )
    service_confirmation_only = fields.Boolean(
        string="Зөвхөн үйлчилгээ баталгаажуулна",
        compute="_compute_receipt_requirements",
        store=True,
    )
    quotation_count = fields.Integer(string="Үнийн санал", compute="_compute_document_counters")
    document_count = fields.Integer(string="Баримт", compute="_compute_document_counters")
    amount_approx_total = fields.Monetary(
        string="Ойролцоогоор нийт дүн",
        currency_field="currency_id",
        compute="_compute_amount_approx_total",
        store=True,
        tracking=True,
    )
    attachment_count = fields.Integer(string="Хавсралт", compute="_compute_attachment_count")
    state_label = fields.Char(string="Төлөвийн нэр", compute="_compute_state_label")
    line_ids = fields.One2many(
        "mpw.procurement.request.line",
        "request_id",
        string="Хүсэлтийн мөрүүд",
        copy=True,
    )
    quotation_ids = fields.One2many(
        "mpw.procurement.quotation",
        "request_id",
        string="Үнийн саналууд",
        copy=True,
    )
    document_ids = fields.One2many(
        "mpw.procurement.document",
        "request_id",
        string="Баримтууд",
        copy=False,
    )
    audit_log_ids = fields.One2many(
        "mpw.procurement.audit",
        "request_id",
        string="Өөрчлөлтийн түүх",
        copy=False,
    )

    @api.model
    def _default_requester_employee(self):
        employee = getattr(self.env.user, "employee_id", False)
        if employee:
            return employee
        return self.env["hr.employee"].search([("user_id", "=", self.env.user.id)], limit=1)

    @api.depends("state")
    def _compute_state_label(self):
        labels = dict(self._fields["state"].selection)
        for request in self:
            request.state_label = labels.get(request.state, "")

    @api.depends("line_ids.approx_subtotal")
    def _compute_amount_approx_total(self):
        for request in self:
            request.amount_approx_total = sum(request.line_ids.mapped("approx_subtotal"))

    @api.depends("selected_quotation_id.supplier_id", "selected_quotation_id.amount_total")
    def _compute_selected_supplier_fields(self):
        for request in self:
            request.selected_supplier_id = request.selected_quotation_id.supplier_id
            request.selected_supplier_total = request.selected_quotation_id.amount_total

    @api.depends("selected_supplier_total")
    def _compute_flow_type(self):
        for request in self:
            if request.selected_supplier_total:
                request.flow_type = "high" if request.selected_supplier_total >= THRESHOLD_AMOUNT else "low"
                request.is_over_threshold = request.selected_supplier_total >= THRESHOLD_AMOUNT
            else:
                request.flow_type = False
                request.is_over_threshold = False

    @api.depends("state", "last_state_change_at")
    def _compute_current_stage_age_days(self):
        now_dt = fields.Datetime.now()
        for request in self:
            start_dt = request.last_state_change_at or request.create_date
            if not start_dt:
                request.current_stage_age_days = 0.0
                continue
            stage_start = fields.Datetime.to_datetime(start_dt)
            request.current_stage_age_days = max((now_dt - stage_start).total_seconds(), 0.0) / 86400.0

    @api.depends("required_date", "state")
    def _compute_delay_metrics(self):
        today = fields.Date.context_today(self)
        final_states = {"done", "cancelled"}
        for request in self:
            if request.required_date and request.state not in final_states and request.required_date < today:
                request.delay_days = float((today - request.required_date).days)
                request.is_delayed = True
            else:
                request.delay_days = 0.0
                request.is_delayed = False

    def _search_is_delayed(self, operator, value):
        if operator not in ("=", "!="):
            raise UserError(_("Хоцролтын шүүлтүүрийг энэ хэлбэрээр ашиглах боломжгүй."))
        today = fields.Date.context_today(self)
        delayed_domain = [
            ("required_date", "<", today),
            ("state", "not in", ["done", "cancelled"]),
        ]
        if (operator == "=" and value) or (operator == "!=" and not value):
            return delayed_domain
        return ["!"] + delayed_domain

    @api.depends(
        "state",
        "responsible_storekeeper_user_id",
        "finance_processed_by",
        "director_order_prepared_by",
        "contract_prepared_by",
        "received_by",
        "requester_user_id",
        "project_id.user_id",
    )
    def _compute_current_responsible_user_id(self):
        for request in self:
            responsible = False
            if request.state == "draft":
                responsible = request.requester_user_id
            elif request.state == "quotation_waiting":
                responsible = request.responsible_storekeeper_user_id
            elif request.state in {"quotations_ready", "finance_review"} and request.flow_type == "low":
                responsible = request.finance_processed_by or request._get_first_group_user(
                    "municipal_procurement_workflow.group_mpw_finance"
                )
            elif request.state in {"quotations_ready", "order_preparing", "decision_approved"} and request.flow_type == "high":
                responsible = request.director_order_prepared_by or request._get_first_group_user(
                    "municipal_procurement_workflow.group_mpw_office_clerk"
                )
            elif request.state == "director_pending":
                responsible = request._get_first_group_user("municipal_procurement_workflow.group_mpw_director")
            elif request.state in {"order_issued", "contract_preparing"}:
                responsible = request.contract_prepared_by or request._get_first_group_user(
                    "municipal_procurement_workflow.group_mpw_contract_officer"
                )
            elif request.state == "contract_signed":
                responsible = request.finance_processed_by or request._get_first_group_user(
                    "municipal_procurement_workflow.group_mpw_finance"
                )
            elif request.state == "paid":
                responsible = request.responsible_storekeeper_user_id
            elif request.state in {"received", "done"}:
                responsible = request.requester_user_id or request.project_id.user_id
            request.current_responsible_user_id = responsible

    @api.depends("line_ids.product_id", "line_ids.product_id.type", "procurement_type")
    def _compute_receipt_requirements(self):
        for request in self:
            stock_lines = request.line_ids.filtered(
                lambda line: line.product_id and line.product_id.type in {"product", "consu"}
            )
            request.stock_receipt_required = bool(stock_lines) or request.procurement_type in {"goods", "spare_part"}
            request.service_confirmation_only = not request.stock_receipt_required

    @api.depends("quotation_ids", "quotation_ids.attachment_ids", "document_ids", "document_ids.attachment_ids")
    def _compute_document_counters(self):
        for request in self:
            director_docs = request.document_ids.filtered(
                lambda document: document.document_type in {"director_order_draft", "director_order_final"}
            )
            contract_docs = request.document_ids.filtered(
                lambda document: document.document_type in {"contract_draft", "contract_final"}
            )
            request.quotation_count = len(request.quotation_ids)
            request.document_count = len(request.document_ids)
            request.director_order_attachment_count = sum(len(doc.attachment_ids) for doc in director_docs)
            request.contract_attachment_count = sum(len(doc.attachment_ids) for doc in contract_docs)

    @api.depends("message_attachment_count", "quotation_ids.attachment_ids", "document_ids.attachment_ids")
    def _compute_attachment_count(self):
        for request in self:
            request.attachment_count = (
                request.message_attachment_count
                + sum(len(quotation.attachment_ids) for quotation in request.quotation_ids)
                + sum(len(document.attachment_ids) for document in request.document_ids)
            )

    @api.depends_context("uid")
    def _compute_available_storekeeper_user_ids(self):
        storekeeper_group = self.env.ref(
            "municipal_procurement_workflow.group_mpw_storekeeper",
            raise_if_not_found=False,
        )
        available_users = storekeeper_group.users.filtered(lambda user: not user.share) if storekeeper_group else self.env["res.users"]
        for request in self:
            request.available_storekeeper_user_ids = available_users

    @api.onchange("project_id")
    def _onchange_project_id(self):
        for request in self:
            if not request.project_id:
                continue
            department = getattr(request.project_id, "ops_department_id", False)
            if department:
                request.department_id = department
            if not request.required_date:
                request.required_date = request.project_id.date

    @api.onchange("task_id")
    def _onchange_task_id(self):
        for request in self:
            if request.task_id:
                request.project_id = request.task_id.project_id

    @api.constrains("responsible_storekeeper_user_id")
    def _check_storekeeper_user(self):
        for request in self:
            if (
                request.responsible_storekeeper_user_id
                and not request.responsible_storekeeper_user_id.has_group(
                    "municipal_procurement_workflow.group_mpw_storekeeper"
                )
                and not request.responsible_storekeeper_user_id.has_group("base.group_system")
            ):
                raise ValidationError(_("Хариуцсан ажилтнаар зөвхөн няравын эрхтэй хэрэглэгч сонгоно уу."))

    @api.constrains("selected_quotation_id", "flow_type")
    def _check_selected_quotation_matches_flow(self):
        for request in self:
            if request.selected_quotation_id and request.selected_quotation_id.request_id != request:
                raise ValidationError(_("Сонгосон үнийн санал энэ хүсэлтэд хамаарах ёстой."))

    @api.constrains("project_id", "task_id")
    def _check_task_project_consistency(self):
        for request in self:
            if request.task_id and request.project_id and request.task_id.project_id != request.project_id:
                raise ValidationError(_("Сонгосон ажилбар тухайн төсөлд хамаарах ёстой."))

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        for vals in vals_list:
            prepared = dict(vals)
            if prepared.get("name", "Шинэ") == "Шинэ":
                prepared["name"] = self.env["ir.sequence"].next_by_code("mpw.procurement.request") or "Шинэ"
            prepared.setdefault("requester_user_id", self.env.user.id)
            if not prepared.get("requester_employee_id"):
                employee = self._default_requester_employee()
                if employee:
                    prepared["requester_employee_id"] = employee.id
            if not prepared.get("department_id"):
                department = False
                if prepared.get("task_id"):
                    task = self.env["project.task"].browse(prepared["task_id"]).exists()
                    if task:
                        prepared["project_id"] = prepared.get("project_id") or task.project_id.id
                if prepared.get("project_id"):
                    project = self.env["project.project"].browse(prepared["project_id"]).exists()
                    department = getattr(project, "ops_department_id", False)
                if not department and prepared.get("requester_employee_id"):
                    employee = self.env["hr.employee"].browse(prepared["requester_employee_id"]).exists()
                    department = employee.department_id
                if department:
                    prepared["department_id"] = department.id
            prepared_vals_list.append(prepared)

        requests = super().create(prepared_vals_list)
        for request in requests:
            request.message_subscribe(partner_ids=request.requester_user_id.partner_id.ids)
            request._create_audit_entry(
                action_code="created",
                action_label="Хүсэлт үүсгэв",
                note=_("Худалдан авалтын хүсэлт үүсгэлээ."),
            )
        return requests

    def write(self, vals):
        if not self.env.context.get("mpw_allow_system_write"):
            self._check_direct_write_permissions(vals)

        tracked_before = {
            request.id: {
                "selected_quotation_id": request.selected_quotation_id.id,
                "payment_reference": request.payment_reference,
                "payment_date": request.payment_date,
            }
            for request in self
        }
        result = super().write(vals)

        if not self.env.context.get("mpw_skip_write_audit"):
            for request in self:
                before = tracked_before[request.id]
                if before["selected_quotation_id"] != request.selected_quotation_id.id:
                    request._create_audit_entry(
                        action_code="selected_quotation_changed",
                        action_label="Сонгосон нийлүүлэгч өөрчлөгдөв",
                        note=_("Сонгосон үнийн санал шинэчлэгдлээ."),
                    )
                if (
                    before["payment_reference"] != request.payment_reference
                    or before["payment_date"] != request.payment_date
                ) and (request.payment_reference or request.payment_date):
                    request._create_audit_entry(
                        action_code="payment_metadata_changed",
                        action_label="Төлбөрийн мэдээлэл шинэчлэгдэв",
                        note=_("Төлбөрийн лавлагаа эсвэл огноо шинэчлэгдлээ."),
                    )
        return result

    def _check_direct_write_permissions(self, vals):
        if self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin") or self.env.user.has_group(
            "base.group_system"
        ):
            return

        selected_only_fields = {"selected_quotation_id"}
        payment_fields = {"payment_reference", "payment_date", "notes_internal"}
        if set(vals) <= selected_only_fields and any(
            self.env.user.has_group(xmlid)
            for xmlid in [
                "municipal_procurement_workflow.group_mpw_storekeeper",
                "municipal_procurement_workflow.group_mpw_finance",
                "municipal_procurement_workflow.group_mpw_office_clerk",
                "municipal_procurement_workflow.group_mpw_director",
            ]
        ):
            return
        if set(vals) <= payment_fields and self.env.user.has_group(
            "municipal_procurement_workflow.group_mpw_finance"
        ):
            return
        if set(vals) <= {"notes_internal"} and any(
            self.env.user.has_group(xmlid)
            for xmlid in [
                "municipal_procurement_workflow.group_mpw_storekeeper",
                "municipal_procurement_workflow.group_mpw_office_clerk",
                "municipal_procurement_workflow.group_mpw_contract_officer",
                "municipal_procurement_workflow.group_mpw_director",
            ]
        ):
            return

        protected_fields = {
            "name",
            "requester_user_id",
            "requester_employee_id",
            "state",
            "flow_type",
            "selected_supplier_id",
            "selected_supplier_total",
            "payment_status",
            "receipt_status",
            "director_order_prepared_by",
            "contract_prepared_by",
            "finance_processed_by",
            "received_by",
            "date_quotation_submitted",
            "date_director_decision",
            "date_order_issued",
            "date_contract_signed",
            "date_paid",
            "date_received",
            "purchase_order_id",
            "vendor_bill_id",
            "receipt_picking_id",
            "workflow_started_at",
            "last_state_change_at",
            "audit_log_ids",
        }
        if protected_fields & set(vals):
            raise AccessError(_("Танд энэ мэдээллийг шууд өөрчлөх эрх алга. Тусгай үйлдлийн товч ашиглана уу."))

        for request in self:
            allowed_fields = {
                "title",
                "active",
                "company_id",
                "currency_id",
                "project_id",
                "task_id",
                "department_id",
                "responsible_storekeeper_user_id",
                "procurement_type",
                "urgency",
                "description",
                "required_date",
                "notes_user",
                "notes_internal",
            }
            if set(vals) - allowed_fields:
                raise AccessError(_("Танд энэ үйлдлийг хийх эрх алга."))
            if not request._can_requester_edit_content():
                raise AccessError(_("Хүсэлтийн энэ шатанд ерөнхий мэдээлэл засах боломжгүй."))

    def _can_requester_edit_content(self):
        self.ensure_one()
        if self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin") or self.env.user.has_group(
            "base.group_system"
        ):
            return True
        return self.state in {"draft", "quotation_waiting"} and (
            self.requester_user_id == self.env.user
            or self.project_id.user_id == self.env.user
            or self.department_id.manager_id.user_id == self.env.user
        )

    def _can_storekeeper_manage(self):
        self.ensure_one()
        return self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin") or self.env.user.has_group(
            "base.group_system"
        ) or self.responsible_storekeeper_user_id == self.env.user

    def _check_document_write_access(self, document_type):
        self.ensure_one()
        if self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin") or self.env.user.has_group(
            "base.group_system"
        ):
            return
        if document_type in {"quotation", "receipt_proof"} and self._can_storekeeper_manage():
            return
        if document_type in {"director_order_draft", "director_order_final"} and self.env.user.has_group(
            "municipal_procurement_workflow.group_mpw_office_clerk"
        ):
            return
        if document_type in {"contract_draft", "contract_final"} and self.env.user.has_group(
            "municipal_procurement_workflow.group_mpw_contract_officer"
        ):
            return
        if document_type == "payment_proof" and self.env.user.has_group(
            "municipal_procurement_workflow.group_mpw_finance"
        ):
            return
        if document_type in {"other"} and self._can_requester_edit_content():
            return
        raise AccessError(_("Танд энэ төрлийн баримт оруулах эрх алга."))

    def _get_first_group_user(self, xmlid):
        group = self.env.ref(xmlid, raise_if_not_found=False)
        if not group:
            return self.env["res.users"]
        return group.users.filtered(lambda user: not user.share)[:1]

    def _ensure_user_has_any_group(self, *xmlids):
        if any(self.env.user.has_group(xmlid) for xmlid in xmlids):
            return
        raise AccessError(_("Танд энэ үйлдлийг хийх эрх алга."))

    def _ensure_request_state(self, allowed_states):
        self.ensure_one()
        if self.state not in allowed_states:
            raise UserError(_("Энэ шатанд уг үйлдлийг хийх боломжгүй байна."))

    def _ensure_selected_quotation(self):
        self.ensure_one()
        if not self.selected_quotation_id:
            raise UserError(_("Нэг үнийн саналыг сонгож хадгална уу."))
        return self.selected_quotation_id

    def _ensure_quote_count(self):
        self.ensure_one()
        if len(self.quotation_ids) < 3:
            raise ValidationError(_("Хамгийн багадаа 3 үнийн санал оруулна уу."))

    def _ensure_payment_metadata(self):
        self.ensure_one()
        has_payment_document = bool(
            self.document_ids.filtered(lambda document: document.document_type == "payment_proof")
        )
        if not (self.payment_reference or self.payment_date or has_payment_document):
            raise ValidationError(_("Төлбөрийн лавлагаа эсвэл баримтыг бүртгэнэ үү."))

    def _ensure_document_exists(self, document_type):
        self.ensure_one()
        if not self.document_ids.filtered(lambda document: document.document_type == document_type and document.attachment_ids):
            raise ValidationError(_("Шаардлагатай баримтыг эхлээд хавсаргана уу."))

    def _ensure_flow(self, expected_flow):
        self.ensure_one()
        quotation = self._ensure_selected_quotation()
        if expected_flow == "low" and quotation.amount_total >= THRESHOLD_AMOUNT:
            raise ValidationError(_("Сонгосон нийлүүлэгчийн дүн 1,000,000 төгрөгөөс дээш тул өндөр урсгал ашиглана."))
        if expected_flow == "high" and quotation.amount_total < THRESHOLD_AMOUNT:
            raise ValidationError(_("Сонгосон нийлүүлэгчийн дүн 1,000,000 төгрөгөөс доош тул бага урсгал ашиглана."))

    def _prepare_purchase_order_vals(self):
        self.ensure_one()
        partner = self.selected_supplier_id
        if not partner:
            raise ValidationError(_("Сонгосон нийлүүлэгчийг заавал сонгоно уу."))
        unit_uom = self.env.ref("uom.product_uom_unit", raise_if_not_found=False)
        order_lines = []
        for line in self.line_ids:
            product = line.product_id
            line_name = line.product_name_manual or product.display_name or line.specification or self.title
            uom = line.uom_id or (product.uom_po_id if product else False) or (product.uom_id if product else False) or unit_uom
            order_lines.append(
                Command.create(
                    {
                        "product_id": product.id if product else False,
                        "name": line_name,
                        "product_qty": line.quantity or 1.0,
                        "product_uom": uom.id if uom else False,
                        "price_unit": line.final_unit_price or line.approx_unit_price or 0.0,
                        "date_planned": self.required_date or fields.Date.context_today(self),
                    }
                )
            )
        return {
            "partner_id": partner.id,
            "currency_id": self.currency_id.id,
            "date_order": fields.Datetime.now(),
            "origin": self.name,
            "company_id": self.company_id.id,
            "notes": "\n".join(filter(None, [self.title, self.description or ""])),
            "order_line": order_lines,
        }

    def _ensure_purchase_order(self):
        self.ensure_one()
        if self.purchase_order_id:
            return self.purchase_order_id
        purchase_order = self.env["purchase.order"].create(self._prepare_purchase_order_vals())
        self.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
            {"purchase_order_id": purchase_order.id}
        )
        return purchase_order

    def _clear_open_activities(self):
        self.ensure_one()
        self.activity_ids.unlink()

    def _create_audit_entry(self, action_code, action_label, note, old_state=False, new_state=False):
        self.ensure_one()
        self.env["mpw.procurement.audit"].sudo().create(
            {
                "request_id": self.id,
                "action_code": action_code,
                "action_label": action_label,
                "old_state": old_state or self.state,
                "new_state": new_state or self.state,
                "user_id": self.env.user.id,
                "note": note,
            }
        )

    def _schedule_next_activities(self):
        todo_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not todo_type:
            return
        for request in self:
            request._clear_open_activities()
            if request.state in {"received", "done", "cancelled"}:
                continue

            target_users = self.env["res.users"]
            if request.state == "quotation_waiting":
                target_users = request.responsible_storekeeper_user_id
            elif request.state == "quotations_ready":
                if request.flow_type == "low":
                    target_users = request.env.ref(
                        "municipal_procurement_workflow.group_mpw_finance"
                    ).users.filtered(lambda user: not user.share)
                elif request.flow_type == "high":
                    target_users = request.env.ref(
                        "municipal_procurement_workflow.group_mpw_office_clerk"
                    ).users.filtered(lambda user: not user.share)
            else:
                group_xmlid = NEXT_ROLE_BY_STATE.get(request.state)
                if group_xmlid:
                    target_users = request.env.ref(group_xmlid).users.filtered(lambda user: not user.share)
                elif request.state == "received":
                    target_users = request.requester_user_id

            for user in target_users:
                request.activity_schedule(
                    activity_type_id=todo_type.id,
                    user_id=user.id,
                    summary=request._get_activity_summary(),
                    note=request._get_activity_note(),
                )

    def _get_activity_summary(self):
        self.ensure_one()
        return _("%s - дараагийн шат") % (self.title or self.name)

    def _get_activity_note(self):
        self.ensure_one()
        label = dict(self._fields["state"].selection).get(self.state, self.state)
        return _("%(name)s хүсэлт %(state)s шатанд байна.") % {"name": self.name, "state": label}

    def _log_state_transition(self, new_state, action_code, action_label, note):
        self.ensure_one()
        old_state = self.state
        self.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
            {
                "state": new_state,
                "last_state_change_at": fields.Datetime.now(),
            }
        )
        self._create_audit_entry(
            action_code=action_code,
            action_label=action_label,
            note=note,
            old_state=old_state,
            new_state=new_state,
        )
        self.message_post(
            body=_("<p><b>Төлөв шинэчлэгдэв:</b> %(old)s → %(new)s</p><p>%(note)s</p>")
            % {
                "old": dict(self._fields["state"].selection).get(old_state, old_state),
                "new": dict(self._fields["state"].selection).get(new_state, new_state),
                "note": note,
            }
        )
        self._schedule_next_activities()

    def _sync_stage_from_documents(self):
        for request in self:
            if request.state == "order_preparing" and request.document_ids.filtered(
                lambda document: document.document_type == "director_order_draft" and document.attachment_ids
            ):
                request._log_state_transition(
                    "director_pending",
                    "director_order_draft_attached",
                    "Тушаалын ноорог хавсаргав",
                    _("Тушаалын ноорог хавсаргаж, захирлын шийдвэрт шилжүүллээ."),
                )
            elif request.state == "order_issued" and request.document_ids.filtered(
                lambda document: document.document_type == "contract_draft" and document.attachment_ids
            ):
                request._log_state_transition(
                    "contract_preparing",
                    "contract_draft_attached",
                    "Гэрээний ноорог хавсаргав",
                    _("Гэрээний ноорог хавсаргаж, гэрээ байгуулах шат руу шилжүүллээ."),
                )

    def action_submit_for_quotation(self):
        for request in self:
            request._ensure_request_state({"draft"})
            if not request._can_requester_edit_content() and not request.env.user.has_group(
                "municipal_procurement_workflow.group_mpw_admin"
            ):
                raise AccessError(_("Танд энэ үйлдлийг хийх эрх алга."))
            if not request.line_ids:
                raise ValidationError(_("Хамгийн багадаа нэг мөр нэмнэ үү."))
            request._log_state_transition(
                "quotation_waiting",
                "submit_for_quotation",
                "Үнийн саналд илгээлээ",
                _("Хүсэлтийг үнийн санал цуглуулах шат руу шилжүүллээ."),
            )

    def action_submit_quotations(self):
        for request in self:
            request._ensure_request_state({"quotation_waiting", "quotations_ready", "finance_review"})
            if not request._can_storekeeper_manage():
                raise AccessError(_("Танд энэ үйлдлийг хийх эрх алга."))
            request._ensure_quote_count()
            request._ensure_selected_quotation()
            request.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                {
                    "date_quotation_submitted": fields.Datetime.now(),
                    "last_state_change_at": fields.Datetime.now(),
                }
            )
            request._log_state_transition(
                "quotations_ready",
                "submit_quotations",
                "Үнийн саналуудыг бүртгэв",
                _("3 үнийн санал амжилттай бүртгэгдлээ."),
            )

    def action_move_to_finance_review(self):
        for request in self:
            request._ensure_request_state({"quotations_ready"})
            request._ensure_flow("low")
            request._ensure_user_has_any_group(
                "municipal_procurement_workflow.group_mpw_finance",
                "municipal_procurement_workflow.group_mpw_admin",
                "base.group_system",
            )
            request._log_state_transition(
                "finance_review",
                "move_to_finance_review",
                "Санхүүгийн хяналтад шилжүүлэв",
                _("Бага урсгалын хүсэлтийг санхүүгийн хяналтын шат руу шилжүүллээ."),
            )

    def action_prepare_director_order(self):
        for request in self:
            request._ensure_request_state({"quotations_ready"})
            request._ensure_flow("high")
            request._ensure_user_has_any_group(
                "municipal_procurement_workflow.group_mpw_office_clerk",
                "municipal_procurement_workflow.group_mpw_admin",
                "base.group_system",
            )
            request.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                {"director_order_prepared_by": self.env.user.id}
            )
            request._log_state_transition(
                "order_preparing",
                "prepare_director_order",
                "Тушаал бэлтгэж эхлэв",
                _("Өндөр урсгалын хүсэлтийн тушаалын бэлтгэлийг эхлүүллээ."),
            )

    def action_approve_order_decision(self):
        for request in self:
            request._ensure_request_state({"director_pending"})
            request._ensure_flow("high")
            request._ensure_user_has_any_group(
                "municipal_procurement_workflow.group_mpw_director",
                "municipal_procurement_workflow.group_mpw_admin",
                "base.group_system",
            )
            request._ensure_selected_quotation()
            request.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                {"date_director_decision": fields.Datetime.now()}
            )
            request._log_state_transition(
                "decision_approved",
                "director_decision",
                "Захирлын шийдвэрийг баталгаажуулав",
                _("Захирлын шийдвэр баталгаажиж, эцсийн тушаал хавсаргах шат руу шилжлээ."),
            )

    def action_attach_final_order(self):
        for request in self:
            request._ensure_request_state({"decision_approved"})
            request._ensure_flow("high")
            request._ensure_user_has_any_group(
                "municipal_procurement_workflow.group_mpw_office_clerk",
                "municipal_procurement_workflow.group_mpw_admin",
                "base.group_system",
            )
            request._ensure_document_exists("director_order_final")
            request.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                {
                    "date_order_issued": fields.Datetime.now(),
                    "director_order_prepared_by": self.env.user.id,
                }
            )
            request._log_state_transition(
                "order_issued",
                "attach_final_order",
                "Эцсийн тушаал хавсаргав",
                _("Эцсийн захирлын тушаал хавсаргаж, гэрээний шат руу шилжүүллээ."),
            )

    def action_mark_contract_signed(self):
        for request in self:
            request._ensure_request_state({"order_issued", "contract_preparing"})
            request._ensure_flow("high")
            request._ensure_user_has_any_group(
                "municipal_procurement_workflow.group_mpw_contract_officer",
                "municipal_procurement_workflow.group_mpw_admin",
                "base.group_system",
            )
            request._ensure_document_exists("contract_final")
            request.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                {
                    "date_contract_signed": fields.Datetime.now(),
                    "contract_prepared_by": self.env.user.id,
                }
            )
            request._ensure_purchase_order()
            request._log_state_transition(
                "contract_signed",
                "contract_signed",
                "Гэрээ байгуулж дуусгав",
                _("Эцсийн гэрээ баталгаажиж, төлбөрийн шат руу шилжүүллээ."),
            )

    def action_select_supplier_and_pay(self):
        for request in self:
            request._ensure_request_state({"quotations_ready", "finance_review"})
            request._ensure_flow("low")
            request._ensure_user_has_any_group(
                "municipal_procurement_workflow.group_mpw_finance",
                "municipal_procurement_workflow.group_mpw_admin",
                "base.group_system",
            )
            request._ensure_selected_quotation()
            request._ensure_payment_metadata()
            now_dt = fields.Datetime.now()
            request.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                {
                    "finance_processed_by": self.env.user.id,
                    "payment_status": "paid",
                    "date_paid": now_dt,
                    "payment_date": request.payment_date or fields.Date.context_today(self),
                }
            )
            request._ensure_purchase_order()
            request._log_state_transition(
                "paid",
                "finance_pay_low",
                "Санхүү төлбөр хийв",
                _("Бага урсгалын хүсэлтийн төлбөрийг баталгаажууллаа."),
            )

    def action_pay_high_flow(self):
        for request in self:
            request._ensure_request_state({"contract_signed"})
            request._ensure_flow("high")
            request._ensure_user_has_any_group(
                "municipal_procurement_workflow.group_mpw_finance",
                "municipal_procurement_workflow.group_mpw_admin",
                "base.group_system",
            )
            request._ensure_payment_metadata()
            now_dt = fields.Datetime.now()
            request.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                {
                    "finance_processed_by": self.env.user.id,
                    "payment_status": "paid",
                    "date_paid": now_dt,
                    "payment_date": request.payment_date or fields.Date.context_today(self),
                }
            )
            request._ensure_purchase_order()
            request._log_state_transition(
                "paid",
                "finance_pay_high",
                "Санхүү төлбөр хийв",
                _("Өндөр урсгалын хүсэлтийн төлбөрийг баталгаажууллаа."),
            )

    def action_mark_received(self):
        for request in self:
            request._ensure_request_state({"paid"})
            if not request._can_storekeeper_manage():
                raise AccessError(_("Танд энэ үйлдлийг хийх эрх алга."))
            request.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                {
                    "received_by": self.env.user.id,
                    "receipt_status": "received",
                    "date_received": fields.Datetime.now(),
                }
            )
            request._log_state_transition(
                "received",
                "received",
                "Хүлээн авалтыг баталгаажуулав",
                _("Бараа, ажил, үйлчилгээг хүлээн авсан гэж бүртгэлээ."),
            )

    def action_mark_done(self):
        for request in self:
            request._ensure_request_state({"received"})
            if not (
                request.requester_user_id == self.env.user
                or request.project_id.user_id == self.env.user
                or self.env.user.has_group("municipal_procurement_workflow.group_mpw_general_manager")
                or self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin")
                or self.env.user.has_group("base.group_system")
            ):
                raise AccessError(_("Танд энэ үйлдлийг хийх эрх алга."))
            request._log_state_transition(
                "done",
                "done",
                "Хүсэлтийг хаав",
                _("Хүлээн авалт баталгаажиж, хүсэлтийг дууссанд тооцлоо."),
            )

    def action_cancel(self):
        for request in self:
            if request.state in {"done", "cancelled"}:
                continue
            if not (
                request.requester_user_id == self.env.user
                or request.project_id.user_id == self.env.user
                or request._can_storekeeper_manage()
                or self.env.user.has_group("municipal_procurement_workflow.group_mpw_general_manager")
                or self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin")
                or self.env.user.has_group("base.group_system")
            ):
                raise AccessError(_("Танд энэ үйлдлийг хийх эрх алга."))
            request._log_state_transition(
                "cancelled",
                "cancelled",
                "Хүсэлтийг цуцлав",
                _("Худалдан авалтын хүсэлтийг цуцаллаа."),
            )

    def action_reset_to_draft(self):
        self._ensure_user_has_any_group(
            "municipal_procurement_workflow.group_mpw_admin",
            "base.group_system",
        )
        for request in self:
            request._log_state_transition(
                "draft",
                "reset_to_draft",
                "Ноорог төлөв рүү буцаав",
                _("Админ хэрэглэгч хүсэлтийг ноорог төлөв рүү буцаалаа."),
            )

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_order_id:
            raise UserError(_("Холбогдсон худалдан авалтын захиалга алга байна."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Худалдан авалтын захиалга"),
            "res_model": "purchase.order",
            "res_id": self.purchase_order_id.id,
            "view_mode": "form",
        }

    def action_view_attachments(self):
        self.ensure_one()
        attachment_ids = self._get_direct_attachment_records().ids
        attachment_ids.extend(self.quotation_ids.attachment_ids.ids)
        attachment_ids.extend(self.document_ids.attachment_ids.ids)
        return {
            "type": "ir.actions.act_window",
            "name": _("Хавсралтууд"),
            "res_model": "ir.attachment",
            "view_mode": "list,form",
            "domain": [("id", "in", list(set(attachment_ids)))],
        }

    def _get_direct_attachment_records(self):
        self.ensure_one()
        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
            ],
            order="id desc",
        )

    def action_open_project(self):
        self.ensure_one()
        if not self.project_id:
            raise UserError(_("Төсөл сонгогдоогүй байна."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Төсөл"),
            "res_model": "project.project",
            "res_id": self.project_id.id,
            "view_mode": "form",
        }

    def action_open_task(self):
        self.ensure_one()
        if not self.task_id:
            raise UserError(_("Ажилбар сонгогдоогүй байна."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Ажилбар"),
            "res_model": "project.task",
            "res_id": self.task_id.id,
            "view_mode": "form",
        }

    def action_open_activities(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Үйл ажиллагаа"),
            "res_model": "mail.activity",
            "view_mode": "list,form",
            "domain": [("res_model", "=", self._name), ("res_id", "=", self.id)],
        }

    def _prepare_api_payload(self, detail=False):
        self.ensure_one()
        state_label_map = dict(self._fields["state"].selection)
        flow_label_map = dict(self._fields["flow_type"].selection)
        payment_label_map = dict(self._fields["payment_status"].selection)
        receipt_label_map = dict(self._fields["receipt_status"].selection)

        payload = {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "project": {"id": self.project_id.id, "name": self.project_id.display_name} if self.project_id else None,
            "task": {"id": self.task_id.id, "name": self.task_id.display_name} if self.task_id else None,
            "department": {"id": self.department_id.id, "name": self.department_id.display_name} if self.department_id else None,
            "requester": {"id": self.requester_user_id.id, "name": self.requester_user_id.display_name}
            if self.requester_user_id
            else None,
            "storekeeper": {
                "id": self.responsible_storekeeper_user_id.id,
                "name": self.responsible_storekeeper_user_id.display_name,
            }
            if self.responsible_storekeeper_user_id
            else None,
            "procurement_type": {
                "code": self.procurement_type,
                "label": dict(self._fields["procurement_type"].selection).get(self.procurement_type),
            },
            "urgency": {
                "code": self.urgency,
                "label": dict(self._fields["urgency"].selection).get(self.urgency),
            },
            "description": self.description,
            "required_date": fields.Date.to_string(self.required_date) if self.required_date else None,
            "state": {"code": self.state, "label": state_label_map.get(self.state)},
            "flow_type": {
                "code": self.flow_type,
                "label": flow_label_map.get(self.flow_type),
            }
            if self.flow_type
            else None,
            "selected_supplier": {
                "id": self.selected_supplier_id.id,
                "name": self.selected_supplier_id.display_name,
                "total": self.selected_supplier_total,
            }
            if self.selected_supplier_id
            else None,
            "selected_quotation_id": self.selected_quotation_id.id or None,
            "selected_supplier_total": self.selected_supplier_total,
            "amount_approx_total": self.amount_approx_total,
            "payment_status": {"code": self.payment_status, "label": payment_label_map.get(self.payment_status)},
            "receipt_status": {"code": self.receipt_status, "label": receipt_label_map.get(self.receipt_status)},
            "is_over_threshold": self.is_over_threshold,
            "payment_reference": self.payment_reference,
            "payment_date": fields.Date.to_string(self.payment_date) if self.payment_date else None,
            "date_quotation_submitted": fields.Datetime.to_string(self.date_quotation_submitted)
            if self.date_quotation_submitted
            else None,
            "date_director_decision": fields.Datetime.to_string(self.date_director_decision)
            if self.date_director_decision
            else None,
            "date_order_issued": fields.Datetime.to_string(self.date_order_issued) if self.date_order_issued else None,
            "date_contract_signed": fields.Datetime.to_string(self.date_contract_signed)
            if self.date_contract_signed
            else None,
            "date_paid": fields.Datetime.to_string(self.date_paid) if self.date_paid else None,
            "date_received": fields.Datetime.to_string(self.date_received) if self.date_received else None,
            "current_responsible": {
                "id": self.current_responsible_user_id.id,
                "name": self.current_responsible_user_id.display_name,
            }
            if self.current_responsible_user_id
            else None,
            "current_stage_age_days": round(self.current_stage_age_days, 1),
            "delay_days": round(self.delay_days, 1),
            "is_delayed": self.is_delayed,
            "paid": self.payment_status == "paid",
            "received": self.receipt_status == "received",
            "purchase_order_id": self.purchase_order_id.id or None,
            "vendor_bill_id": self.vendor_bill_id.id or None,
            "stock_receipt_required": self.stock_receipt_required,
            "service_confirmation_only": self.service_confirmation_only,
            "available_actions": self._get_available_action_payloads(),
        }
        if detail:
            direct_attachments = self._get_direct_attachment_records()
            payload["lines"] = [line._prepare_api_payload() for line in self.line_ids.sorted("sequence")]
            payload["quotations"] = [quotation._prepare_api_payload() for quotation in self.quotation_ids]
            payload["documents"] = [document._prepare_api_payload() for document in self.document_ids]
            payload["audit"] = [audit._prepare_api_payload() for audit in self.audit_log_ids.sorted("changed_at desc")]
            payload["attachments"] = [
                {
                    "id": attachment.id,
                    "name": attachment.name,
                    "mimetype": attachment.mimetype,
                }
                for attachment in direct_attachments
            ]
        return payload

    def _get_available_action_payloads(self):
        self.ensure_one()
        actions = []
        if self.state == "draft" and self._can_requester_edit_content():
            actions.append({"code": "submit_for_quotation", "label": "Үнийн санал руу илгээх"})
        if self.state in {"quotation_waiting", "quotations_ready", "finance_review"} and self._can_storekeeper_manage():
            actions.append({"code": "submit_quotations", "label": "3 үнийн санал баталгаажуулах"})
        if self.state == "quotations_ready" and self.flow_type == "low" and (
            self.env.user.has_group("municipal_procurement_workflow.group_mpw_finance")
            or self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin")
            or self.env.user.has_group("base.group_system")
        ):
            actions.append({"code": "move_to_finance_review", "label": "Санхүүгийн шат эхлүүлэх"})
            actions.append({"code": "mark_paid", "label": "Төлбөр хийсэн гэж бүртгэх"})
        if self.state == "quotations_ready" and self.flow_type == "high" and (
            self.env.user.has_group("municipal_procurement_workflow.group_mpw_office_clerk")
            or self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin")
            or self.env.user.has_group("base.group_system")
        ):
            actions.append({"code": "prepare_order", "label": "Тушаал бэлтгэх"})
        if self.state == "director_pending" and (
            self.env.user.has_group("municipal_procurement_workflow.group_mpw_director")
            or self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin")
            or self.env.user.has_group("base.group_system")
        ):
            actions.append({"code": "director_decision", "label": "Захирлын шийдвэр бүртгэх"})
        if self.state == "decision_approved" and (
            self.env.user.has_group("municipal_procurement_workflow.group_mpw_office_clerk")
            or self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin")
            or self.env.user.has_group("base.group_system")
        ):
            actions.append({"code": "attach_final_order", "label": "Эцсийн тушаал хавсаргах"})
        if self.state in {"order_issued", "contract_preparing"} and (
            self.env.user.has_group("municipal_procurement_workflow.group_mpw_contract_officer")
            or self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin")
            or self.env.user.has_group("base.group_system")
        ):
            actions.append({"code": "mark_contract_signed", "label": "Гэрээ байгуулсан гэж бүртгэх"})
        if self.state == "contract_signed" and (
            self.env.user.has_group("municipal_procurement_workflow.group_mpw_finance")
            or self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin")
            or self.env.user.has_group("base.group_system")
        ):
            actions.append({"code": "mark_paid", "label": "Төлбөр хийсэн гэж бүртгэх"})
        if self.state == "paid" and self._can_storekeeper_manage():
            actions.append({"code": "mark_received", "label": "Хүлээн авсан гэж бүртгэх"})
        if self.state == "received" and (
            self.requester_user_id == self.env.user
            or self.project_id.user_id == self.env.user
            or self.env.user.has_group("municipal_procurement_workflow.group_mpw_general_manager")
            or self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin")
            or self.env.user.has_group("base.group_system")
        ):
            actions.append({"code": "mark_done", "label": "Дууссан гэж хаах"})
        if self.state not in {"done", "cancelled"}:
            actions.append({"code": "cancel", "label": "Цуцлах"})
        return actions

    def sync_quotations_from_payload(self, quotations_payload):
        self.ensure_one()
        if not self._can_storekeeper_manage():
            raise AccessError(_("Танд энэ үйлдлийг хийх эрх алга."))
        if self.state not in {"quotation_waiting", "quotations_ready", "finance_review"}:
            raise UserError(_("Энэ шатанд үнийн санал шинэчлэх боломжгүй байна."))
        if not quotations_payload or len(quotations_payload) < 3:
            raise ValidationError(_("Хамгийн багадаа 3 үнийн санал ирүүлэх шаардлагатай."))

        commands = [Command.clear()]
        selected_index = None
        for index, payload in enumerate(quotations_payload, start=1):
            supplier_id = int(payload.get("supplier_id") or 0)
            if not supplier_id:
                raise ValidationError(_("Үнийн санал бүрт нийлүүлэгч сонгоно уу."))
            attachment_ids = [int(attachment_id) for attachment_id in payload.get("attachment_ids", []) if attachment_id]
            commands.append(
                Command.create(
                    {
                        "sequence": payload.get("sequence") or index,
                        "supplier_id": supplier_id,
                        "quotation_ref": payload.get("quotation_ref"),
                        "quotation_date": payload.get("quotation_date"),
                        "amount_total": payload.get("amount_total") or 0.0,
                        "currency_id": self.currency_id.id,
                        "payment_terms_text": payload.get("payment_terms_text"),
                        "delivery_terms_text": payload.get("delivery_terms_text"),
                        "expected_delivery_date": payload.get("expected_delivery_date"),
                        "notes": payload.get("notes"),
                        "attachment_ids": [Command.set(attachment_ids)],
                    }
                )
            )
            if payload.get("is_selected"):
                selected_index = index - 1

        self.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write({"quotation_ids": commands})
        if selected_index is not None:
            ordered_quotations = self.quotation_ids.sorted("sequence")
            selected_quotation = ordered_quotations[selected_index:selected_index + 1]
            self.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                {"selected_quotation_id": selected_quotation.id}
            )
        return self.quotation_ids

    def add_document_with_attachments(self, document_type, attachment_ids, note=None):
        self.ensure_one()
        self._check_document_write_access(document_type)
        if not attachment_ids:
            raise ValidationError(_("Хавсралт хоосон байна."))
        existing_document = self.document_ids.filtered(lambda document: document.document_type == document_type)[:1]
        if existing_document:
            existing_document.with_context(mpw_allow_system_write=True).write(
                {
                    "attachment_ids": [Command.link(attachment_id) for attachment_id in attachment_ids],
                    "note": note or existing_document.note,
                }
            )
            document = existing_document
        else:
            document = self.env["mpw.procurement.document"].create(
                {
                    "request_id": self.id,
                    "document_type": document_type,
                    "note": note,
                    "attachment_ids": [Command.set(attachment_ids)],
                }
            )
        self._sync_stage_from_documents()
        return document


class MPWProcurementRequestLine(models.Model):
    _name = "mpw.procurement.request.line"
    _description = "Procurement Request Line"
    _order = "sequence asc, id asc"

    request_id = fields.Many2one("mpw.procurement.request", string="Хүсэлт", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one("product.product", string="Бараа")
    product_name_manual = fields.Char(string="Нэр")
    specification = fields.Text(string="Тодорхойлолт")
    quantity = fields.Float(string="Тоо хэмжээ", default=1.0, required=True)
    uom_id = fields.Many2one("uom.uom", string="Хэмжих нэгж")
    approx_unit_price = fields.Monetary(string="Ойролцоох нэгж үнэ", currency_field="currency_id", default=0.0)
    approx_subtotal = fields.Monetary(
        string="Ойролцоох нийт дүн",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    final_unit_price = fields.Monetary(string="Эцсийн нэгж үнэ", currency_field="currency_id", default=0.0)
    final_subtotal = fields.Monetary(
        string="Эцсийн нийт дүн",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    remark = fields.Char(string="Тэмдэглэл")
    currency_id = fields.Many2one(related="request_id.currency_id", store=True, readonly=True)

    @api.depends("quantity", "approx_unit_price", "final_unit_price")
    def _compute_amounts(self):
        for line in self:
            line.approx_subtotal = line.quantity * line.approx_unit_price
            line.final_subtotal = line.quantity * line.final_unit_price

    @api.model_create_multi
    def create(self, vals_list):
        requests = self.env["mpw.procurement.request"].browse(
            [vals.get("request_id") for vals in vals_list if vals.get("request_id")]
        )
        for request in requests:
            if not request._can_requester_edit_content():
                raise AccessError(_("Хүсэлтийн мөр нэмэх эрх алга."))
        return super().create(vals_list)

    def write(self, vals):
        for line in self:
            if not line.request_id._can_requester_edit_content():
                raise AccessError(_("Хүсэлтийн мөр засах эрх алга."))
        return super().write(vals)

    def unlink(self):
        for line in self:
            if not line.request_id._can_requester_edit_content():
                raise AccessError(_("Хүсэлтийн мөр устгах эрх алга."))
        return super().unlink()

    def _prepare_api_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "sequence": self.sequence,
            "product_id": self.product_id.id or None,
            "product_name": self.product_name_manual or self.product_id.display_name,
            "specification": self.specification,
            "quantity": self.quantity,
            "uom": {"id": self.uom_id.id, "name": self.uom_id.display_name} if self.uom_id else None,
            "approx_unit_price": self.approx_unit_price,
            "approx_subtotal": self.approx_subtotal,
            "final_unit_price": self.final_unit_price,
            "final_subtotal": self.final_subtotal,
            "remark": self.remark,
        }


class MPWProcurementQuotation(models.Model):
    _name = "mpw.procurement.quotation"
    _description = "Procurement Quotation"
    _order = "sequence asc, id asc"

    request_id = fields.Many2one("mpw.procurement.request", string="Хүсэлт", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    supplier_id = fields.Many2one(
        "res.partner",
        string="Нийлүүлэгч",
        required=True,
        domain="[('supplier_rank', '>', 0)]",
    )
    quotation_ref = fields.Char(string="Үнийн саналын дугаар")
    quotation_date = fields.Date(string="Үнийн саналын огноо")
    amount_total = fields.Monetary(string="Нийт дүн", currency_field="currency_id", required=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Валют",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    payment_terms_text = fields.Text(string="Төлбөрийн нөхцөл")
    delivery_terms_text = fields.Text(string="Нийлүүлэлтийн нөхцөл")
    expected_delivery_date = fields.Date(string="Хүлээгдэж буй нийлүүлэлтийн огноо")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "mpw_procurement_quotation_attachment_rel",
        "quotation_id",
        "attachment_id",
        string="Үнийн саналын файл",
    )
    is_selected = fields.Boolean(
        string="Сонгосон",
        compute="_compute_is_selected",
        inverse="_inverse_is_selected",
    )
    notes = fields.Text(string="Тэмдэглэл")

    @api.depends("request_id.selected_quotation_id")
    def _compute_is_selected(self):
        for quotation in self:
            quotation.is_selected = quotation.request_id.selected_quotation_id == quotation

    def _inverse_is_selected(self):
        for quotation in self:
            if quotation.is_selected:
                quotation.request_id.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                    {"selected_quotation_id": quotation.id}
                )
            elif quotation.request_id.selected_quotation_id == quotation:
                quotation.request_id.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                    {"selected_quotation_id": False}
                )

    @api.model_create_multi
    def create(self, vals_list):
        requests = self.env["mpw.procurement.request"].browse(
            [vals.get("request_id") for vals in vals_list if vals.get("request_id")]
        )
        for request in requests:
            if not request._can_storekeeper_manage():
                raise AccessError(_("Үнийн санал нэмэх эрх алга."))
        return super().create(vals_list)

    def write(self, vals):
        for quotation in self:
            if not quotation.request_id._can_storekeeper_manage():
                raise AccessError(_("Үнийн санал засах эрх алга."))
        return super().write(vals)

    def unlink(self):
        for quotation in self:
            if quotation.request_id.selected_quotation_id == quotation:
                quotation.request_id.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                    {"selected_quotation_id": False}
                )
            if not quotation.request_id._can_storekeeper_manage():
                raise AccessError(_("Үнийн санал устгах эрх алга."))
        return super().unlink()

    def _prepare_api_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "sequence": self.sequence,
            "supplier": {"id": self.supplier_id.id, "name": self.supplier_id.display_name},
            "quotation_ref": self.quotation_ref,
            "quotation_date": fields.Date.to_string(self.quotation_date) if self.quotation_date else None,
            "amount_total": self.amount_total,
            "currency": {"id": self.currency_id.id, "name": self.currency_id.name},
            "payment_terms_text": self.payment_terms_text,
            "delivery_terms_text": self.delivery_terms_text,
            "expected_delivery_date": fields.Date.to_string(self.expected_delivery_date)
            if self.expected_delivery_date
            else None,
            "is_selected": self.is_selected,
            "notes": self.notes,
            "attachments": [
                {"id": attachment.id, "name": attachment.name, "mimetype": attachment.mimetype}
                for attachment in self.attachment_ids
            ],
        }


class MPWProcurementDocument(models.Model):
    _name = "mpw.procurement.document"
    _description = "Procurement Document"
    _order = "create_date desc, id desc"

    request_id = fields.Many2one("mpw.procurement.request", string="Хүсэлт", required=True, ondelete="cascade")
    document_type = fields.Selection(DOCUMENT_TYPE_SELECTION, string="Баримтын төрөл", required=True)
    note = fields.Text(string="Тэмдэглэл")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "mpw_procurement_document_attachment_rel",
        "document_id",
        "attachment_id",
        string="Хавсралт",
    )
    is_required = fields.Boolean(string="Шаардлагатай эсэх", compute="_compute_is_required")

    @api.depends("document_type", "request_id.flow_type", "request_id.state")
    def _compute_is_required(self):
        for document in self:
            if document.document_type == "quotation":
                document.is_required = True
            elif document.document_type in {
                "director_order_draft",
                "director_order_final",
                "contract_draft",
                "contract_final",
            }:
                document.is_required = document.request_id.flow_type == "high"
            elif document.document_type in {"payment_proof", "receipt_proof"}:
                document.is_required = True
            else:
                document.is_required = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            document_request = self.env["mpw.procurement.request"].browse(vals.get("request_id")).exists()
            if document_request:
                document_request._check_document_write_access(vals.get("document_type"))
        documents = super().create(vals_list)
        documents.mapped("request_id")._sync_stage_from_documents()
        return documents

    def write(self, vals):
        for document in self:
            document.request_id._check_document_write_access(vals.get("document_type") or document.document_type)
        result = super().write(vals)
        self.mapped("request_id")._sync_stage_from_documents()
        return result

    def unlink(self):
        for document in self:
            document.request_id._check_document_write_access(document.document_type)
        return super().unlink()

    def _prepare_api_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "document_type": {
                "code": self.document_type,
                "label": dict(self._fields["document_type"].selection).get(self.document_type),
            },
            "note": self.note,
            "is_required": self.is_required,
            "attachments": [
                {"id": attachment.id, "name": attachment.name, "mimetype": attachment.mimetype}
                for attachment in self.attachment_ids
            ],
        }


class MPWProcurementAudit(models.Model):
    _name = "mpw.procurement.audit"
    _description = "Procurement Audit Log"
    _order = "changed_at desc, id desc"
    _rec_name = "action_label"

    request_id = fields.Many2one("mpw.procurement.request", string="Хүсэлт", required=True, ondelete="cascade")
    action_code = fields.Char(string="Үйлдлийн код", required=True, readonly=True)
    action_label = fields.Char(string="Үйлдлийн нэр", required=True, readonly=True)
    old_state = fields.Selection(REQUEST_STATE_SELECTION, string="Өмнөх төлөв", readonly=True)
    new_state = fields.Selection(REQUEST_STATE_SELECTION, string="Шинэ төлөв", readonly=True)
    user_id = fields.Many2one("res.users", string="Өөрчилсөн хэрэглэгч", required=True, readonly=True)
    changed_at = fields.Datetime(string="Өөрчлөгдсөн огноо", default=fields.Datetime.now, required=True, readonly=True)
    note = fields.Text(string="Тайлбар", readonly=True)

    def write(self, vals):
        raise AccessError(_("Аудитын түүхийг шууд засах боломжгүй."))

    def unlink(self):
        if not (
            self.env.user.has_group("municipal_procurement_workflow.group_mpw_admin")
            or self.env.user.has_group("base.group_system")
        ):
            raise AccessError(_("Аудитын түүхийг устгах эрх алга."))
        return super().unlink()

    def _prepare_api_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "action_code": self.action_code,
            "action_label": self.action_label,
            "old_state": {
                "code": self.old_state,
                "label": dict(self._fields["old_state"].selection).get(self.old_state),
            }
            if self.old_state
            else None,
            "new_state": {
                "code": self.new_state,
                "label": dict(self._fields["new_state"].selection).get(self.new_state),
            }
            if self.new_state
            else None,
            "user": {"id": self.user_id.id, "name": self.user_id.display_name},
            "changed_at": fields.Datetime.to_string(self.changed_at),
            "note": self.note,
        }


class ProjectProject(models.Model):
    _inherit = "project.project"

    procurement_request_ids = fields.One2many("mpw.procurement.request", "project_id", string="Худалдан авалт")
    procurement_request_count = fields.Integer(string="Худалдан авалт", compute="_compute_procurement_request_count")

    def _compute_procurement_request_count(self):
        grouped = self.env["mpw.procurement.request"].read_group(
            [("project_id", "in", self.ids)],
            ["project_id"],
            ["project_id"],
        )
        counts = {item["project_id"][0]: item["project_id_count"] for item in grouped if item["project_id"]}
        for project in self:
            project.procurement_request_count = counts.get(project.id, 0)

    def action_open_procurement_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Худалдан авалт"),
            "res_model": "mpw.procurement.request",
            "view_mode": "list,kanban,form,graph,pivot",
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }


class ProjectTask(models.Model):
    _inherit = "project.task"

    procurement_request_ids = fields.One2many("mpw.procurement.request", "task_id", string="Худалдан авалт")
    procurement_request_count = fields.Integer(string="Худалдан авалт", compute="_compute_procurement_request_count")

    def _compute_procurement_request_count(self):
        grouped = self.env["mpw.procurement.request"].read_group(
            [("task_id", "in", self.ids)],
            ["task_id"],
            ["task_id"],
        )
        counts = {item["task_id"][0]: item["task_id_count"] for item in grouped if item["task_id"]}
        for task in self:
            task.procurement_request_count = counts.get(task.id, 0)

    def action_open_procurement_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Худалдан авалт"),
            "res_model": "mpw.procurement.request",
            "view_mode": "list,kanban,form,graph,pivot",
            "domain": [("task_id", "=", self.id)],
            "context": {
                "default_task_id": self.id,
                "default_project_id": self.project_id.id,
            },
        }
