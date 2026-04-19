from odoo import _, fields, models


class MunicipalProjectReportPhoto(models.Model):
    _name = "municipal.project.report.photo"
    _description = "Тайлангийн зураг"
    _order = "capture_datetime desc, id desc"

    name = fields.Char(
        string="Нэр",
        default=lambda self: _("Тайлангийн зураг"),
        required=True,
    )
    task_id = fields.Many2one(
        "project.task",
        string="Ажил",
        required=True,
        ondelete="cascade",
        index=True,
    )
    image_1920 = fields.Image(
        string="Зураг",
        required=True,
    )
    note = fields.Char(string="Тайлбар")
    capture_datetime = fields.Datetime(
        string="Оруулсан цаг",
        default=fields.Datetime.now,
        required=True,
    )
    uploaded_by_id = fields.Many2one(
        "res.users",
        string="Оруулсан хүн",
        default=lambda self: self.env.user,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="task_id.company_id",
        store=True,
        readonly=True,
    )
