from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FleetRepairRequestLine(models.Model):
    _name = "fleet.repair.request.line"
    _description = "Fleet Repair Request Line"
    _order = "sequence, id"

    request_id = fields.Many2one(
        "fleet.repair.request",
        string="Засварын хүсэлт",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one("product.product", string="Бараа / сэлбэг")
    name = fields.Char(string="Сэлбэг / материалын нэр", required=True)
    specification = fields.Char(string="Үзүүлэлт / specification")
    quantity = fields.Float(string="Тоо хэмжээ", default=1.0, required=True)
    uom_name = fields.Char(string="Нэгж", default="ш")
    estimated_unit_price = fields.Monetary(
        string="Тооцоот нэгж үнэ",
        currency_field="currency_id",
    )
    estimated_subtotal = fields.Monetary(
        string="Тооцоот дүн",
        currency_field="currency_id",
        compute="_compute_estimated_subtotal",
        store=True,
    )
    actual_unit_price = fields.Monetary(
        string="Бодит нэгж үнэ",
        currency_field="currency_id",
    )
    actual_subtotal = fields.Monetary(
        string="Бодит дүн",
        currency_field="currency_id",
        compute="_compute_actual_subtotal",
        store=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="request_id.currency_id",
        store=True,
        readonly=True,
    )
    is_critical = fields.Boolean(string="Яаралтай сэлбэг")
    note = fields.Char(string="Тайлбар")
    purchased = fields.Boolean(string="Авсан эсэх", default=False)

    @api.depends("quantity", "estimated_unit_price")
    def _compute_estimated_subtotal(self):
        for line in self:
            line.estimated_subtotal = line.quantity * (line.estimated_unit_price or 0.0)

    @api.depends("quantity", "actual_unit_price")
    def _compute_actual_subtotal(self):
        for line in self:
            line.actual_subtotal = line.quantity * (line.actual_unit_price or 0.0)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self.filtered("product_id"):
            product = line.product_id
            if not line.name:
                line.name = product.display_name
            if not line.specification and product.description_purchase:
                line.specification = product.description_purchase
            if not line.uom_name:
                line.uom_name = product.uom_po_id.name or product.uom_id.name or "ш"
            if not line.estimated_unit_price:
                line.estimated_unit_price = product.standard_price

    @api.constrains("quantity", "estimated_unit_price", "actual_unit_price")
    def _check_amounts(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError("Сэлбэгийн мөрийн тоо хэмжээ 0-ээс их байх ёстой.")
            if line.estimated_unit_price < 0:
                raise ValidationError("Тооцоот нэгж үнэ сөрөг байж болохгүй.")
            if line.actual_unit_price < 0:
                raise ValidationError("Бодит нэгж үнэ сөрөг байж болохгүй.")
