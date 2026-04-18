from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    mfo_unresolved_stop_count = fields.Integer(
        string="Нээлттэй цэг",
        compute="_compute_mfo_quality_metrics",
    )
    mfo_expected_stop_count = fields.Integer(
        string="Төлөвлөсөн цэг",
        compute="_compute_mfo_quality_metrics",
    )
    mfo_skipped_without_reason_count = fields.Integer(
        string="Шалтгаангүй алгассан",
        compute="_compute_mfo_quality_metrics",
    )
    mfo_missing_proof_stop_count = fields.Integer(
        string="Зураг дутсан цэг",
        compute="_compute_mfo_quality_metrics",
    )
    mfo_route_deviation_stop_count = fields.Integer(
        string="Маршрутын зөрүүтэй цэг",
        compute="_compute_mfo_quality_metrics",
    )
    mfo_has_weight_data = fields.Boolean(
        string="Жингийн өгөгдөлтэй",
        compute="_compute_mfo_quality_metrics",
    )
    mfo_weight_sync_warning = fields.Boolean(
        string="Жингийн синкийн анхааруулга",
        compute="_compute_mfo_quality_metrics",
    )
    mfo_quality_exception_count = fields.Integer(
        string="Чанарын анхааруулга",
        compute="_compute_mfo_quality_metrics",
    )

    @api.depends(
        "mfo_is_operation_project",
        "mfo_operation_type",
        "mfo_state",
        "mfo_route_id.line_ids",
        "mfo_stop_line_ids.status",
        "mfo_stop_line_ids.skip_reason",
        "mfo_stop_line_ids.proof_image_ids.proof_type",
        "mfo_daily_weight_total_ids.net_weight_total",
        "mfo_weight_measurement_ids.net_weight",
        "mfo_last_sync_log_id.state",
    )
    def _compute_mfo_quality_metrics(self):
        for task in self:
            if not task.mfo_is_operation_project:
                task.mfo_unresolved_stop_count = 0
                task.mfo_expected_stop_count = 0
                task.mfo_skipped_without_reason_count = 0
                task.mfo_missing_proof_stop_count = 0
                task.mfo_route_deviation_stop_count = 0
                task.mfo_has_weight_data = False
                task.mfo_weight_sync_warning = False
                task.mfo_quality_exception_count = 0
                continue

            stops = task.mfo_stop_line_ids
            unresolved_stop_count = len(
                stops.filtered(lambda line: line.status not in {"done", "skipped"})
            )
            skipped_without_reason_count = len(
                stops.filtered(lambda line: line.status == "skipped" and not line.skip_reason)
            )
            missing_proof_stop_count = len(
                stops.filtered(
                    lambda line: line.status == "done"
                    and not {"before", "after"}.issubset(
                        set(line.proof_image_ids.mapped("proof_type"))
                    )
                )
            )
            expected_stop_count = len(task.mfo_route_id.line_ids) or len(stops)
            handled_stop_count = len(
                stops.filtered(lambda line: line.status in {"done", "skipped"})
            )
            route_deviation_stop_count = abs(expected_stop_count - handled_stop_count)
            has_weight_data = bool(
                task.mfo_daily_weight_total_ids or task.mfo_weight_measurement_ids
            )
            sync_state = task.mfo_last_sync_log_id.state if task.mfo_last_sync_log_id else False
            weight_sync_warning = bool(
                sync_state in {"warning", "failed"}
                or (
                    task.mfo_operation_type == "garbage"
                    and task.mfo_state in {"submitted", "verified"}
                    and not has_weight_data
                )
            )

            task.mfo_unresolved_stop_count = unresolved_stop_count
            task.mfo_expected_stop_count = expected_stop_count
            task.mfo_skipped_without_reason_count = skipped_without_reason_count
            task.mfo_missing_proof_stop_count = missing_proof_stop_count
            task.mfo_route_deviation_stop_count = route_deviation_stop_count
            task.mfo_has_weight_data = has_weight_data
            task.mfo_weight_sync_warning = weight_sync_warning
            task.mfo_quality_exception_count = (
                unresolved_stop_count
                + skipped_without_reason_count
                + missing_proof_stop_count
                + route_deviation_stop_count
                + (1 if weight_sync_warning else 0)
            )
