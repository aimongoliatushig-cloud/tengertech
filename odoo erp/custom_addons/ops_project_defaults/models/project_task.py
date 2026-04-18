from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    ops_department_id = fields.Many2one(
        "hr.department",
        string="Алба нэгж",
        related="project_id.ops_department_id",
        store=True,
        readonly=True,
        index=True,
    )
