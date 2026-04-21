from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class HrEmployeeClearance(models.Model):
    _name = "hr.employee.clearance"
    _description = "Ажилтны тойрох хуудас"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "request_date desc, id desc"
    _mail_post_access = "read"
    _check_company_auto = True

    name = fields.Char(
        string="Дугаар",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("Шинэ"),
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Ажилтан",
        required=True,
        tracking=True,
        check_company=True,
    )
    employee_department_id = fields.Many2one(
        "hr.department",
        string="Хэлтэс",
        tracking=True,
        check_company=True,
    )
    employee_job_id = fields.Many2one(
        "hr.job",
        string="Албан тушаал",
        tracking=True,
        check_company=True,
    )
    request_date = fields.Date(
        string="Хүсэлтийн огноо",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    effective_date = fields.Date(
        string="Хүчинтэй огноо",
        required=True,
        tracking=True,
    )
    clearance_type = fields.Selection(
        [
            ("resignation", "Өөрийн хүсэлтээр гарах"),
            ("termination", "Ажлаас чөлөөлөх"),
            ("transfer", "Шилжилт хөдөлгөөн"),
        ],
        string="Төрөл",
        required=True,
        tracking=True,
    )
    reason = fields.Text(string="Шалтгаан")
    state = fields.Selection(
        [
            ("draft", "Ноорог"),
            ("in_progress", "Явцад"),
            ("done", "Дууссан"),
            ("cancelled", "Цуцлагдсан"),
        ],
        string="Төлөв",
        required=True,
        default="draft",
        tracking=True,
    )
    note = fields.Text(string="Нэмэлт тэмдэглэл")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_employee_clearance_attachment_rel",
        "clearance_id",
        "attachment_id",
        string="Хавсралт",
        copy=False,
    )
    created_by_id = fields.Many2one(
        "res.users",
        string="Үүсгэсэн хэрэглэгч",
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    hr_responsible_id = fields.Many2one(
        "res.users",
        string="Хүний нөөц хариуцсан",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Компани",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )
    active = fields.Boolean(string="Идэвхтэй", default=True)

    hr_check_done = fields.Boolean(string="Хүний нөөц шалгасан", tracking=True)
    hr_check_date = fields.Date(string="Хүний нөөцийн огноо", tracking=True)
    hr_note = fields.Text(string="Хүний нөөцийн тэмдэглэл")

    finance_check_done = fields.Boolean(string="Санхүү шалгасан", tracking=True)
    finance_check_date = fields.Date(string="Санхүүгийн огноо", tracking=True)
    finance_note = fields.Text(string="Санхүүгийн тэмдэглэл")

    it_check_done = fields.Boolean(string="МТ / хандалт шалгасан", tracking=True)
    it_check_date = fields.Date(string="МТ огноо", tracking=True)
    it_note = fields.Text(string="МТ тэмдэглэл")

    asset_check_done = fields.Boolean(string="Эд хөрөнгө шалгасан", tracking=True)
    asset_check_date = fields.Date(string="Эд хөрөнгийн огноо", tracking=True)
    asset_note = fields.Text(string="Эд хөрөнгийн тэмдэглэл")

    manager_check_done = fields.Boolean(string="Удирдлага шалгасан", tracking=True)
    manager_check_date = fields.Date(string="Удирдлагын огноо", tracking=True)
    manager_note = fields.Text(string="Удирдлагын тэмдэглэл")

    final_hr_done = fields.Boolean(string="Эцсийн хүний нөөцийн баталгаажуулалт", tracking=True)
    final_hr_date = fields.Date(string="Эцсийн хүний нөөцийн огноо", tracking=True)
    final_hr_note = fields.Text(string="Эцсийн тайлбар")

    @api.model_create_multi
    def create(self, vals_list):
        self._check_create_access()
        vals_list = self._normalize_create_vals_list(vals_list)
        prepared_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            vals = self._prepare_employee_snapshot(vals)
            vals = self._prepare_check_dates(vals)
            if vals.get("name", _("Шинэ")) == _("Шинэ"):
                vals["name"] = self.env["ir.sequence"].next_by_code("hr.employee.clearance") or _("Шинэ")
            prepared_vals_list.append(vals)
        return super().create(prepared_vals_list)

    def write(self, vals):
        self._check_write_access(vals)
        vals = dict(vals)
        if vals.get("employee_id"):
            vals = self._prepare_employee_snapshot(vals)
        vals = self._prepare_check_dates(vals)
        completion_messages = self._get_section_completion_messages(vals)
        result = super().write(vals)
        for record_id, messages in completion_messages.items():
            record = self.browse(record_id)
            for message in messages:
                record.message_post(body=message)
        return result

    def unlink(self):
        if any(record.state == "done" for record in self) and not self._is_clearance_manager():
            raise UserError(_("Дууссан тойрох хуудсыг зөвхөн менежер устгана."))
        return super().unlink()

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        for record in self:
            record.employee_department_id = record.employee_id.department_id
            record.employee_job_id = record.employee_id.job_id
            if not record.hr_responsible_id:
                record.hr_responsible_id = record.env.user

    @api.onchange(
        "hr_check_done",
        "finance_check_done",
        "it_check_done",
        "asset_check_done",
        "manager_check_done",
        "final_hr_done",
    )
    def _onchange_check_dates(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.hr_check_done and not record.hr_check_date:
                record.hr_check_date = today
            if record.finance_check_done and not record.finance_check_date:
                record.finance_check_date = today
            if record.it_check_done and not record.it_check_date:
                record.it_check_date = today
            if record.asset_check_done and not record.asset_check_date:
                record.asset_check_date = today
            if record.manager_check_done and not record.manager_check_date:
                record.manager_check_date = today
            if record.final_hr_done and not record.final_hr_date:
                record.final_hr_date = today

    def _prepare_employee_snapshot(self, vals):
        employee_id = vals.get("employee_id")
        if isinstance(employee_id, (list, tuple)):
            employee_id = employee_id[0] if employee_id else False
        if not employee_id:
            return vals
        employee = self.env["hr.employee"].browse(employee_id)
        vals.setdefault("employee_department_id", employee.department_id.id)
        vals.setdefault("employee_job_id", employee.job_id.id)
        vals.setdefault("company_id", employee.company_id.id or self.env.company.id)
        vals.setdefault("hr_responsible_id", self.env.user.id)
        return vals

    def _prepare_check_dates(self, vals):
        today = fields.Date.context_today(self)
        check_map = {
            "hr_check_done": "hr_check_date",
            "finance_check_done": "finance_check_date",
            "it_check_done": "it_check_date",
            "asset_check_done": "asset_check_date",
            "manager_check_done": "manager_check_date",
            "final_hr_done": "final_hr_date",
        }
        for done_field, date_field in check_map.items():
            if vals.get(done_field) and not vals.get(date_field):
                vals[date_field] = today
        return vals

    def _get_missing_check_dates_vals(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        vals = {}
        check_map = {
            "hr_check_done": "hr_check_date",
            "finance_check_done": "finance_check_date",
            "it_check_done": "it_check_date",
            "asset_check_done": "asset_check_date",
            "manager_check_done": "manager_check_date",
            "final_hr_done": "final_hr_date",
        }
        for done_field, date_field in check_map.items():
            if self[done_field] and not self[date_field]:
                vals[date_field] = today
        return vals

    def _normalize_create_vals_list(self, vals_list):
        if isinstance(vals_list, dict):
            return [vals_list]
        if isinstance(vals_list, list) and len(vals_list) == 1 and isinstance(vals_list[0], list):
            return vals_list[0]
        return vals_list

    def _get_section_completion_messages(self, vals):
        section_labels = {
            "hr_check_done": "Хүний нөөцийн шалгалт дууслаа.",
            "finance_check_done": "Санхүүгийн шалгалт дууслаа.",
            "it_check_done": "МТ / хандалтын шалгалт дууслаа.",
            "asset_check_done": "Эд хөрөнгийн шалгалт дууслаа.",
            "manager_check_done": "Удирдлагын шалгалт дууслаа.",
            "final_hr_done": "Эцсийн хүний нөөцийн баталгаажуулалт хийгдлээ.",
        }
        completion_messages = {}
        for record in self:
            messages = []
            for field_name, message in section_labels.items():
                if vals.get(field_name) and not record[field_name]:
                    messages.append(message)
            completion_messages[record.id] = messages
        return completion_messages

    def _is_clearance_user(self):
        user = self.env.user
        return (
            user.has_group("hr_clearance_mn.group_hr_clearance_user")
            or user.has_group("hr_clearance_mn.group_hr_clearance_manager")
            or user.has_group("hr.group_hr_manager")
            or user.has_group("base.group_system")
        )

    def _is_clearance_manager(self):
        user = self.env.user
        return (
            user.has_group("hr_clearance_mn.group_hr_clearance_manager")
            or user.has_group("hr.group_hr_manager")
            or user.has_group("base.group_system")
        )

    def _check_create_access(self):
        if not self._is_clearance_user():
            raise AccessError(_("Танд тойрох хуудас үүсгэх эрх алга."))

    def _check_write_access(self, vals):
        if self.env.su:
            return
        if self.env.context.get("hr_clearance_state_action"):
            return
        if not self._is_clearance_user():
            raise AccessError(_("Танд тойрох хуудас засах эрх алга."))
        if any(record.state == "done" for record in self) and not self._is_clearance_manager():
            raise UserError(_("Дууссан тойрох хуудсыг зөвхөн менежер засна."))
        protected = {"state"}
        if protected.intersection(vals) and not self._is_clearance_manager():
            raise AccessError(_("Төлөвийг зөвхөн workflow товчоор өөрчилнө."))

    def _validate_done_requirements(self):
        for record in self:
            missing = []
            if not record.hr_check_done:
                missing.append(_("Хүний нөөц"))
            if not record.finance_check_done:
                missing.append(_("Санхүү"))
            if not record.it_check_done:
                missing.append(_("МТ / Хандалт"))
            if not record.asset_check_done:
                missing.append(_("Эд хөрөнгө"))
            if not record.manager_check_done:
                missing.append(_("Удирдлага"))
            if not record.final_hr_done:
                missing.append(_("Эцсийн хүний нөөцийн баталгаажуулалт"))
            if missing:
                raise ValidationError(
                    _("Дараах шалгалтууд дутуу байна: %s") % ", ".join(missing)
                )

    def button_start_progress(self):
        if not self._is_clearance_user():
            raise AccessError(_("Танд явцад оруулах эрх алга."))
        for record in self:
            if record.state != "draft":
                raise UserError(_("Зөвхөн ноорог тойрох хуудсыг явцад оруулна."))
        self.with_context(hr_clearance_state_action=True).write({"state": "in_progress"})
        self.message_post(body=_("Тойрох хуудсыг явцад орууллаа."))
        return True

    def button_done(self):
        if not self._is_clearance_user():
            raise AccessError(_("Танд дуусгах эрх алга."))
        for record in self:
            if record.state != "in_progress":
                raise UserError(_("Зөвхөн явцад байгаа тойрох хуудсыг дуусгана."))
            missing_date_vals = record._get_missing_check_dates_vals()
            if missing_date_vals:
                record.write(missing_date_vals)
        self._validate_done_requirements()
        self.with_context(hr_clearance_state_action=True).write({"state": "done"})
        self.message_post(body=_("Тойрох хуудсыг дууссан төлөвт шилжүүллээ."))
        return True

    def button_cancel(self):
        if not self._is_clearance_user():
            raise AccessError(_("Танд цуцлах эрх алга."))
        for record in self:
            if record.state not in ("draft", "in_progress"):
                raise UserError(_("Зөвхөн ноорог эсвэл явцад байгаа тойрох хуудсыг цуцална."))
        self.with_context(hr_clearance_state_action=True).write({"state": "cancelled"})
        self.message_post(body=_("Тойрох хуудсыг цуцаллаа."))
        return True

    def button_reset_to_draft(self):
        if not self._is_clearance_manager():
            raise AccessError(_("Зөвхөн менежер ноорог төлөв рүү буцаана."))
        for record in self:
            if record.state != "cancelled":
                raise UserError(_("Зөвхөн цуцлагдсан тойрох хуудсыг ноорог болгоно."))
        self.with_context(hr_clearance_state_action=True).write({"state": "draft"})
        self.message_post(body=_("Тойрох хуудсыг ноорог төлөв рүү буцаалаа."))
        return True
