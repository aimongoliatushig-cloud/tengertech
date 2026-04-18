from odoo import fields, models

from .common import STAGE_CODE_SELECTION


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    mfo_stage_code = fields.Selection(
        selection=STAGE_CODE_SELECTION,
        string="Хотын ажиллагааны шат",
        copy=False,
    )
