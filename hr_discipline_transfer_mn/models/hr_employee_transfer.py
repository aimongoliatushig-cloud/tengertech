from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class HrEmployeeTransfer(models.Model):
    _name = "hr.employee.transfer"
    _description = "Employee Transfer History"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "effective_date desc, id desc"
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
    current_department_id = fields.Many2one(
        "hr.department",
        string="Одоогийн хэлтэс",
        required=True,
        tracking=True,
        check_company=True,
    )
    new_department_id = fields.Many2one(
        "hr.department",
        string="Шинэ хэлтэс",
        required=True,
        tracking=True,
        check_company=True,
    )
    current_job_id = fields.Many2one("hr.job", string="Одоогийн албан тушаал", tracking=True, check_company=True)
    new_job_id = fields.Many2one("hr.job", string="Шинэ албан тушаал", tracking=True, check_company=True)
    movement_type = fields.Selection(
        [
            ("department_transfer", "Хэлтэс шилжүүлэлт"),
            ("job_change", "Албан тушаал өөрчлөлт"),
            ("unit_transfer", "Алба хоорондын шилжилт"),
            ("temporary_assignment", "Түр томилолт"),
        ],
        string="Шилжилтийн төрөл",
        required=True,
        tracking=True,
    )
    reason = fields.Text(string="Шалтгаан", required=True, tracking=True)
    order_date = fields.Date(string="Тушаалын огноо", tracking=True)
    effective_date = fields.Date(string="Хүчин төгөлдөр огноо", required=True, tracking=True)
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_employee_transfer_attachment_rel",
        "transfer_id",
        "attachment_id",
        string="Хавсралтууд",
        copy=False,
    )
    director_order_attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_employee_transfer_director_order_rel",
        "transfer_id",
        "attachment_id",
        string="Захирлын тушаал",
        copy=False,
    )
    state = fields.Selection(
        [
            ("draft", "Ноорог"),
            ("submitted", "Батлуулахаар илгээсэн"),
            ("approved", "Батлагдсан"),
            ("rejected", "Цуцлагдсан"),
        ],
        string="Төлөв",
        required=True,
        default="draft",
        tracking=True,
    )
    requested_by_id = fields.Many2one(
        "res.users",
        string="Хүсэлт гаргасан",
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    approved_by_id = fields.Many2one("res.users", string="Баталсан", readonly=True, tracking=True)
    approved_date = fields.Datetime(string="Баталсан огноо", readonly=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        string="Компани",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )
    note = fields.Text(string="Тэмдэглэл")

    @api.model_create_multi
    def create(self, vals_list):
        self._check_create_access()
        vals_list = self._normalize_create_vals_list(vals_list)
        prepared_vals_list = []
        for vals in vals_list:
            vals = self._normalize_vals_dict(vals)
            vals = self._prepare_employee_snapshot(vals)
            if vals.get("name", _("Шинэ")) == _("Шинэ"):
                vals["name"] = self.env["ir.sequence"].next_by_code("hr.employee.transfer") or _("Шинэ")
            prepared_vals_list.append(vals)
        return super().create(prepared_vals_list)

    def write(self, vals):
        self._check_write_access(vals)
        if vals.get("employee_id"):
            vals = self._prepare_employee_snapshot(vals)
        return super().write(vals)

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        for record in self:
            record.current_department_id = record.employee_id.department_id
            record.current_job_id = record.employee_id.job_id

    @api.constrains("current_department_id", "new_department_id", "movement_type")
    def _check_department_difference(self):
        for record in self:
            if (
                record.movement_type in ("department_transfer", "unit_transfer")
                and record.current_department_id
                and record.new_department_id
                and record.current_department_id == record.new_department_id
            ):
                raise ValidationError(_("Шилжүүлэлтийн үед одоогийн болон шинэ хэлтэс ижил байж болохгүй."))

    def _prepare_employee_snapshot(self, vals):
        employee_id = vals.get("employee_id")
        if isinstance(employee_id, (list, tuple)):
            employee_id = employee_id[0] if employee_id else False
        if not employee_id:
            return vals
        employee = self.env["hr.employee"].browse(employee_id)
        vals.setdefault("current_department_id", employee.department_id.id)
        vals.setdefault("current_job_id", employee.job_id.id)
        vals.setdefault("company_id", employee.company_id.id or self.env.company.id)
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

    def _is_transfer_user(self):
        user = self.env.user
        return (
            user.has_group("hr_discipline_transfer_mn.group_hr_transfer_user")
            or user.has_group("hr_discipline_transfer_mn.group_hr_transfer_manager")
            or user.has_group("hr.group_hr_manager")
            or user.has_group("base.group_system")
        )

    def _is_transfer_manager(self):
        user = self.env.user
        return (
            user.has_group("hr_discipline_transfer_mn.group_hr_transfer_manager")
            or user.has_group("hr.group_hr_manager")
            or user.has_group("base.group_system")
        )

    def _is_director_approver(self):
        user = self.env.user
        return (
            user.has_group("hr_discipline_transfer_mn.group_hr_director_approval")
            or self._is_transfer_manager()
        )

    def _check_create_access(self):
        if not self._is_transfer_user():
            raise AccessError(_("Танд шилжилт хөдөлгөөний бүртгэл үүсгэх эрх алга."))

    def _check_write_access(self, vals):
        if self.env.su:
            return
        if self.env.context.get("hr_transfer_submit_action") or self.env.context.get("hr_transfer_approval_action"):
            return
        if self._is_director_approver() and not self._is_transfer_manager():
            raise AccessError(_("Баталгаажуулагч хэрэглэгч зөвхөн батлах эсвэл цуцлах товч ашиглана."))
        if not self._is_transfer_user():
            raise AccessError(_("Танд шилжилт хөдөлгөөний бүртгэл засах эрх алга."))
        if any(record.state in ("approved", "rejected") for record in self) and not self._is_transfer_manager():
            raise UserError(_("Батлагдсан эсвэл цуцлагдсан бүртгэлийг зөвхөн менежер засна."))
        protected = {"approved_by_id", "approved_date"}
        if protected.intersection(vals) and not self._is_transfer_manager():
            raise AccessError(_("Энэ талбарыг зөвхөн менежер өөрчилнө."))

    def _ensure_submittable(self):
        for record in self:
            if not record.reason:
                raise ValidationError(_("Шилжилтийн шалтгааныг бөглөнө үү."))
            if not record.effective_date:
                raise ValidationError(_("Хүчин төгөлдөр огноог бөглөнө үү."))

    def _ensure_approvable(self):
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Зөвхөн илгээсэн бүртгэлийг батална."))
            if not record.effective_date:
                raise ValidationError(_("Хүчин төгөлдөр огноо заавал бөглөгдсөн байна."))
            if not record.employee_id.active:
                raise ValidationError(_("Архивлагдсан ажилтны шилжилтийг батлах боломжгүй."))

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
                "Шилжилт хөдөлгөөний бүртгэл батлах шаардлагатай байна: %(number)s / %(employee)s",
                number=record.name,
                employee=record.employee_id.name,
            )
            for user in directors:
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    date_deadline=fields.Date.context_today(record),
                    summary=_("Шилжилт хөдөлгөөн батлах"),
                    note=note,
                    user_id=user.id,
                )

    def _notify_creator(self, title, body):
        for record in self:
            partner_ids = record.requested_by_id.partner_id.ids
            record.message_post(body=body, partner_ids=partner_ids)
            if record.requested_by_id and record.requested_by_id.active:
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    date_deadline=fields.Date.context_today(record),
                    summary=title,
                    note=body,
                    user_id=record.requested_by_id.id,
                )

    def button_submit(self):
        if not self._is_transfer_user():
            raise AccessError(_("Танд илгээх эрх алга."))
        self._ensure_submittable()
        for record in self:
            if record.state != "draft":
                raise UserError(_("Зөвхөн ноорог бүртгэлийг илгээж болно."))
        self.with_context(hr_transfer_submit_action=True).write({"state": "submitted"})
        self._schedule_approval_activities()
        self.message_post(body=_("Бүртгэлийг батлуулахаар илгээлээ."))
        return True

    def button_approve(self):
        if not self._is_director_approver():
            raise AccessError(_("Танд батлах эрх алга."))
        self._ensure_approvable()
        now = fields.Datetime.now()
        for record in self:
            vals = {
                "state": "approved",
                "approved_by_id": self.env.user.id,
                "approved_date": now,
            }
            record.with_context(hr_transfer_approval_action=True).write(vals)
            employee_vals = {"department_id": record.new_department_id.id}
            if record.new_job_id:
                employee_vals["job_id"] = record.new_job_id.id
            record.employee_id.write(employee_vals)
            record.employee_id.message_post(
                body=_(
                    "Шилжилт хөдөлгөөн батлагдлаа: %(from_dep)s -> %(to_dep)s",
                    from_dep=record.current_department_id.display_name,
                    to_dep=record.new_department_id.display_name,
                )
            )
            record.activity_feedback(
                ["mail.mail_activity_data_todo"],
                feedback=_("Шилжилт хөдөлгөөний бүртгэл батлагдлаа."),
                only_automated=True,
            )
            record.message_post(
                body=_(
                    "%(user)s бүртгэлийг баталлаа.",
                    user=self.env.user.display_name,
                )
            )
        self._notify_creator(_("Шилжилт хөдөлгөөн батлагдлаа"), _("Таны илгээсэн шилжилт хөдөлгөөний бүртгэл батлагдлаа."))
        return True

    def button_reject(self):
        if not self._is_director_approver():
            raise AccessError(_("Танд цуцлах эрх алга."))
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Зөвхөн илгээсэн бүртгэлийг цуцална."))
            record.with_context(hr_transfer_approval_action=True).write(
                {
                    "state": "rejected",
                    "approved_by_id": False,
                    "approved_date": False,
                }
            )
            record.activity_feedback(
                ["mail.mail_activity_data_todo"],
                feedback=_("Шилжилт хөдөлгөөний бүртгэл цуцлагдлаа."),
                only_automated=True,
            )
            record.message_post(
                body=_(
                    "%(user)s бүртгэлийг цуцаллаа.",
                    user=self.env.user.display_name,
                )
            )
        self._notify_creator(_("Шилжилт хөдөлгөөн цуцлагдлаа"), _("Таны илгээсэн шилжилт хөдөлгөөний бүртгэл цуцлагдлаа."))
        return True

    def button_reset_to_draft(self):
        if not self._is_transfer_manager():
            raise AccessError(_("Зөвхөн менежер ноорог төлөв рүү буцаана."))
        self.with_context(hr_transfer_submit_action=True).write(
            {
                "state": "draft",
                "approved_by_id": False,
                "approved_date": False,
            }
        )
        self.activity_unlink(["mail.mail_activity_data_todo"], only_automated=True)
        self.message_post(body=_("Бүртгэлийг ноорог төлөв рүү буцаалаа."))
        return True
