from odoo import fields, models


class OpsPeopleAuditRun(models.Model):
    _name = "ops.people.audit.run"
    _description = "Ажилтан бүртгэлийн аудит"
    _order = "create_date desc, id desc"

    name = fields.Char(string="Аудитын нэр", required=True, default="Шинэ аудит")
    source_label = fields.Char(string="Эх сурвалж")
    state = fields.Selection(
        [
            ("draft", "Ноорог"),
            ("done", "Дууссан"),
        ],
        string="Төлөв",
        default="draft",
        required=True,
    )
    executed_by = fields.Many2one(
        "res.users",
        string="Ажиллуулсан хэрэглэгч",
        default=lambda self: self.env.user,
        readonly=True,
    )
    total_rows = fields.Integer(string="Нийт мөр")
    updated_users = fields.Integer(string="Шинэчилсэн хэрэглэгч")
    linked_employees = fields.Integer(string="Холбосон ажилтан")
    created_employees = fields.Integer(string="Шинээр үүсгэсэн ажилтан")
    created_departments = fields.Integer(string="Шинээр үүсгэсэн алба нэгж")
    created_jobs = fields.Integer(string="Шинээр үүсгэсэн албан тушаал")
    unresolved_count = fields.Integer(string="Шийдэгдээгүй мөр")
    note = fields.Text(string="Тайлбар")
    summary_json = fields.Text(string="JSON хураангуй", readonly=True)
    line_ids = fields.One2many(
        "ops.people.audit.line",
        "run_id",
        string="Аудитын мөрүүд",
    )


class OpsPeopleAuditLine(models.Model):
    _name = "ops.people.audit.line"
    _description = "Ажилтан бүртгэлийн аудитын мөр"
    _order = "severity desc, id"

    run_id = fields.Many2one(
        "ops.people.audit.run",
        string="Аудит",
        required=True,
        ondelete="cascade",
    )
    severity = fields.Selection(
        [
            ("info", "Мэдээлэл"),
            ("warning", "Анхааруулга"),
            ("error", "Алдаа"),
        ],
        string="Түвшин",
        required=True,
        default="warning",
    )
    issue_type = fields.Selection(
        [
            ("missing_department", "Алба нэгж дутуу"),
            ("missing_job", "Албан тушаал дутуу"),
            ("missing_employee_link", "Employee холбоос дутуу"),
            ("unresolved_role", "Системийн эрх тодорхойгүй"),
            ("unresolved_manager", "Шууд удирдлага тодорхойгүй"),
            ("duplicate_employee", "Давхардсан ажилтан"),
            ("duplicate_job", "Давхардсан албан тушаал"),
            ("duplicate_department", "Давхардсан алба нэгж"),
            ("missing_user", "Хэрэглэгч олдсонгүй"),
            ("info", "Мэдээлэл"),
        ],
        string="Төрөл",
        required=True,
        default="info",
    )
    user_id = fields.Many2one("res.users", string="Хэрэглэгч")
    employee_id = fields.Many2one("hr.employee", string="Ажилтан")
    login = fields.Char(string="Нэвтрэх нэр")
    person_name = fields.Char(string="Нэр")
    raw_value = fields.Char(string="Эх утга")
    normalized_value = fields.Char(string="Маппинг")
    note = fields.Text(string="Тайлбар")
