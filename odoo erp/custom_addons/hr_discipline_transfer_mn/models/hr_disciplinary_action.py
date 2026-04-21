from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class HrDisciplinaryAction(models.Model):
    _name = "hr.disciplinary.action"
    _description = "Ажилтны сахилгын бүртгэл"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "violation_date desc, id desc"
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
    action_type = fields.Selection(
        [
            ("warning", "Сануулга"),
            ("salary_deduction_20", "20% цалингийн суутгал"),
            ("termination_proposal", "Ажлаас халах санал"),
        ],
        string="Шийтгэлийн төрөл",
        required=True,
        tracking=True,
    )
    violation_date = fields.Date(string="Зөрчил гарсан огноо", required=True, tracking=True)
    report_date = fields.Date(
        string="Бүртгэсэн огноо",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    violation_title = fields.Char(string="Товч гарчиг", required=True, tracking=True)
    violation_description = fields.Text(string="Дэлгэрэнгүй зөрчил", required=True, tracking=True)
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_disciplinary_action_attachment_rel",
        "action_id",
        "attachment_id",
        string="Хавсралтууд",
        copy=False,
    )
    director_order_attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_disciplinary_director_order_rel",
        "action_id",
        "attachment_id",
        string="Захирлын тушаал",
        copy=False,
    )
    created_by_id = fields.Many2one(
        "res.users",
        string="Бүртгэсэн хэрэглэгч",
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    hr_responsible_id = fields.Many2one(
        "res.users",
        string="Хүний нөөц хариуцсан",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Ноорог"),
            ("submitted", "Батлуулахаар илгээсэн"),
            ("approved", "Батлагдсан"),
            ("rejected", "Цуцлагдсан"),
        ],
        string="Төлөв",
        default="draft",
        required=True,
        tracking=True,
    )
    approved_by_id = fields.Many2one("res.users", string="Баталсан", readonly=True, tracking=True)
    approved_date = fields.Datetime(string="Баталсан огноо", readonly=True, tracking=True)
    rejection_reason = fields.Text(string="Цуцалсан шалтгаан", tracking=True)
    salary_deduction_percent = fields.Float(
        string="Суутгалын хувь",
        default=20.0,
        tracking=True,
    )
    effective_date = fields.Date(string="Хүчин төгөлдөр огноо", tracking=True)
    company_id = fields.Many2one(
        "res.company",
        string="Компани",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )
    active = fields.Boolean(string="Идэвхтэй", default=True)

    @api.model_create_multi
    def create(self, vals_list):
        self._check_create_access()
        vals_list = self._normalize_create_vals_list(vals_list)
        prepared_vals_list = []
        for vals in vals_list:
            vals = self._normalize_vals_dict(vals)
            vals = self._prepare_employee_snapshot(vals)
            if vals.get("name", _("Шинэ")) == _("Шинэ"):
                vals["name"] = self.env["ir.sequence"].next_by_code("hr.disciplinary.action") or _("Шинэ")
            if vals.get("action_type") == "salary_deduction_20":
                vals["salary_deduction_percent"] = 20.0
            prepared_vals_list.append(vals)
        return super().create(prepared_vals_list)

    def write(self, vals):
        self._check_write_access(vals)
        if vals.get("employee_id"):
            vals = self._prepare_employee_snapshot(vals)
        if vals.get("action_type") == "salary_deduction_20":
            vals["salary_deduction_percent"] = 20.0
        return super().write(vals)

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        for record in self:
            record.employee_department_id = record.employee_id.department_id
            record.employee_job_id = record.employee_id.job_id
            if not record.hr_responsible_id:
                record.hr_responsible_id = record.env.user

    @api.onchange("action_type")
    def _onchange_action_type(self):
        for record in self:
            if record.action_type == "salary_deduction_20":
                record.salary_deduction_percent = 20.0

    @api.constrains("salary_deduction_percent", "action_type")
    def _check_salary_deduction_percent(self):
        for record in self:
            if record.action_type == "salary_deduction_20" and record.salary_deduction_percent != 20.0:
                raise ValidationError(_("20 хувийн суутгалын бүртгэл дээр хувь 20 байх ёстой."))

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

    def _normalize_create_vals_list(self, vals_list):
        if isinstance(vals_list, dict):
            return [vals_list]
        if isinstance(vals_list, list) and len(vals_list) == 1 and isinstance(vals_list[0], list):
            return vals_list[0]
        return vals_list

    def _normalize_vals_dict(self, vals):
        if isinstance(vals, dict):
            return dict(vals)
        if isinstance(vals, list):
            return dict(vals)
        return dict(vals)

    def _is_discipline_user(self):
        user = self.env.user
        return (
            user.has_group("hr_discipline_transfer_mn.group_hr_discipline_user")
            or user.has_group("hr_discipline_transfer_mn.group_hr_discipline_manager")
            or user.has_group("hr.group_hr_manager")
            or user.has_group("base.group_system")
        )

    def _is_discipline_manager(self):
        user = self.env.user
        return (
            user.has_group("hr_discipline_transfer_mn.group_hr_discipline_manager")
            or user.has_group("hr.group_hr_manager")
            or user.has_group("base.group_system")
        )

    def _is_director_approver(self):
        user = self.env.user
        return (
            user.has_group("hr_discipline_transfer_mn.group_hr_director_approval")
            or self._is_discipline_manager()
        )

    def _check_create_access(self):
        if not self._is_discipline_user():
            raise AccessError(_("Танд сахилгын бүртгэл үүсгэх эрх алга."))

    def _check_write_access(self, vals):
        if self.env.su:
            return
        if self.env.context.get("hr_discipline_submit_action") or self.env.context.get("hr_discipline_approval_action"):
            return
        if self._is_director_approver() and not self._is_discipline_manager():
            raise AccessError(_("Баталгаажуулагч хэрэглэгч зөвхөн батлах эсвэл цуцлах товч ашиглана."))
        if not self._is_discipline_user():
            raise AccessError(_("Танд сахилгын бүртгэл засах эрх алга."))
        if any(record.state in ("approved", "rejected") for record in self) and not self._is_discipline_manager():
            raise UserError(_("Батлагдсан эсвэл цуцлагдсан бүртгэлийг зөвхөн менежер засна."))
        protected = {"approved_by_id", "approved_date"}
        if protected.intersection(vals) and not self._is_discipline_manager():
            raise AccessError(_("Энэ талбарыг зөвхөн менежер өөрчилнө."))

    def _ensure_submittable(self):
        for record in self:
            if not record.violation_description:
                raise ValidationError(_("Зөрчлийн дэлгэрэнгүй мэдээллийг бөглөнө үү."))
            if not record.employee_id.active:
                raise ValidationError(_("Архивлагдсан ажилтанд бүртгэл илгээх боломжгүй."))

    def _ensure_approvable(self):
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Зөвхөн илгээсэн бүртгэлийг батална."))
            if not record.violation_description:
                raise ValidationError(_("Зөрчлийн дэлгэрэнгүй мэдээллийг бөглөнө үү."))
            if not record.employee_id.active:
                raise ValidationError(_("Архивлагдсан ажилтны бүртгэлийг батлах боломжгүй."))
            if record.action_type == "termination_proposal":
                if not record.effective_date:
                    raise ValidationError(_("Ажлаас халах санал дээр хүчин төгөлдөр огноо заавал бөглөнө."))
                if not record.director_order_attachment_ids:
                    raise ValidationError(_("Ажлаас халах санал батлахын өмнө захирлын тушаалыг хавсаргана уу."))
            if record.action_type == "salary_deduction_20":
                if not record.effective_date:
                    raise ValidationError(_("Цалингийн суутгал дээр хүчин төгөлдөр огноо заавал бөглөнө."))
                if not record.director_order_attachment_ids:
                    raise ValidationError(_("Цалингийн суутгал батлахын өмнө захирлын тушаалыг хавсаргана уу."))

    def _get_director_users(self):
        group = self.env.ref("hr_discipline_transfer_mn.group_hr_director_approval")
        return group.user_ids.filtered(lambda user: user.active)

    def _schedule_approval_activities(self):
        directors = self._get_director_users()
        if not directors:
            return
        for record in self:
            record.activity_unlink(["mail.mail_activity_data_todo"], only_automated=True)
            note = _(
                "Сахилгын бүртгэл батлах шаардлагатай байна: %(number)s / %(employee)s",
                number=record.name,
                employee=record.employee_id.name,
            )
            for user in directors:
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    date_deadline=fields.Date.context_today(record),
                    summary=_("Сахилгын бүртгэл батлах"),
                    note=note,
                    user_id=user.id,
                )

    def _notify_creator(self, title, body):
        for record in self:
            partner_ids = record.created_by_id.partner_id.ids
            record.message_post(body=body, partner_ids=partner_ids)
            if record.created_by_id and record.created_by_id.active:
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    date_deadline=fields.Date.context_today(record),
                    summary=title,
                    note=body,
                    user_id=record.created_by_id.id,
                )

    def _apply_salary_deduction_effects(self):
        self.message_post(
            body=_(
                "Цалингийн суутгал батлагдлаа. Цаашид contract/payroll модуль нэмэгдэх үед энэ логикийг өргөтгөж ашиглаж болно."
            )
        )

    def button_submit(self):
        if not self._is_discipline_user():
            raise AccessError(_("Танд илгээх эрх алга."))
        self._ensure_submittable()
        for record in self:
            if record.state != "draft":
                raise UserError(_("Зөвхөн ноорог бүртгэлийг илгээж болно."))
        self.with_context(hr_discipline_submit_action=True).write({"state": "submitted"})
        self._schedule_approval_activities()
        for record in self:
            record.message_post(body=_("Бүртгэлийг батлуулахаар илгээлээ."))
        return True

    def button_approve(self):
        if not self._is_director_approver():
            raise AccessError(_("Танд батлах эрх алга."))
        self._ensure_approvable()
        now = fields.Datetime.now()
        for record in self:
            record.with_context(hr_discipline_approval_action=True).write(
                {
                    "state": "approved",
                    "approved_by_id": self.env.user.id,
                    "approved_date": now,
                }
            )
            record.activity_feedback(
                ["mail.mail_activity_data_todo"],
                feedback=_("Сахилгын бүртгэл батлагдлаа."),
                only_automated=True,
            )
            if record.action_type == "termination_proposal":
                record.employee_id.write(
                    {
                        "employment_status": "terminated",
                        "termination_date": record.effective_date,
                        "termination_reason": record.violation_title,
                    }
                )
                record.employee_id.message_post(
                    body=_(
                        "Ажилтны ажлаас чөлөөлөх шийдвэр батлагдлаа: %(title)s",
                        title=record.violation_title,
                    )
                )
            elif record.action_type == "salary_deduction_20":
                record._apply_salary_deduction_effects()
            else:
                record.employee_id.message_post(
                    body=_(
                        "Сахилгын шийтгэл батлагдлаа: %(title)s",
                        title=record.violation_title,
                    )
                )
            record.message_post(
                body=_(
                    "%(user)s бүртгэлийг баталлаа.",
                    user=self.env.user.display_name,
                )
            )
        self._notify_creator(_("Сахилгын бүртгэл батлагдлаа"), _("Таны илгээсэн сахилгын бүртгэл батлагдлаа."))
        return True

    def button_reject(self):
        if not self._is_director_approver():
            raise AccessError(_("Танд цуцлах эрх алга."))
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Зөвхөн илгээсэн бүртгэлийг цуцална."))
            if not record.rejection_reason:
                raise ValidationError(_("Цуцлах шалтгааныг заавал бөглөнө үү."))
            record.with_context(hr_discipline_approval_action=True).write(
                {
                    "state": "rejected",
                    "approved_by_id": False,
                    "approved_date": False,
                }
            )
            record.activity_feedback(
                ["mail.mail_activity_data_todo"],
                feedback=_("Сахилгын бүртгэл цуцлагдлаа."),
                only_automated=True,
            )
            record.message_post(
                body=_(
                    "%(user)s бүртгэлийг цуцаллаа. Шалтгаан: %(reason)s",
                    user=self.env.user.display_name,
                    reason=record.rejection_reason,
                )
            )
        self._notify_creator(_("Сахилгын бүртгэл цуцлагдлаа"), _("Таны илгээсэн сахилгын бүртгэл цуцлагдлаа."))
        return True

    def button_reset_to_draft(self):
        if not self._is_discipline_manager():
            raise AccessError(_("Зөвхөн менежер ноорог төлөв рүү буцаана."))
        self.with_context(hr_discipline_submit_action=True).write(
            {
                "state": "draft",
                "approved_by_id": False,
                "approved_date": False,
                "rejection_reason": False,
            }
        )
        self.activity_unlink(["mail.mail_activity_data_todo"], only_automated=True)
        self.message_post(body=_("Бүртгэлийг ноорог төлөв рүү буцаалаа."))
        return True
