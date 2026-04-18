from odoo import fields, models, tools


class MfoDailyOperationReport(models.Model):
    _name = "mfo.daily.operation.report"
    _description = "Өдрийн ажиллагааны тайлан"
    _auto = False
    _rec_name = "task_id"
    _order = "shift_date desc, task_id desc"

    task_id = fields.Many2one("project.task", string="Даалгавар", readonly=True)
    project_id = fields.Many2one("project.project", string="Төсөл", readonly=True)
    route_id = fields.Many2one("mfo.route", string="Маршрут", readonly=True)
    district_id = fields.Many2one("mfo.district", string="Дүүрэг", readonly=True)
    crew_team_id = fields.Many2one("mfo.crew.team", string="Экипаж", readonly=True)
    vehicle_id = fields.Many2one("fleet.vehicle", string="Техник", readonly=True)
    shift_date = fields.Date(string="Огноо", readonly=True)
    operation_type = fields.Selection(
        selection=[
            ("garbage", "Хог цуглуулалт"),
            ("street_cleaning", "Гудамж цэвэрлэгээ"),
            ("green_maintenance", "Ногоон байгууламж"),
        ],
        string="Ажиллагааны төрөл",
        readonly=True,
    )
    mfo_state = fields.Selection(
        selection=[
            ("draft", "Төлөвлөгдсөн"),
            ("dispatched", "Хуваарилсан"),
            ("in_progress", "Гүйцэтгэж байна"),
            ("submitted", "Шалгахаар илгээсэн"),
            ("verified", "Баталгаажсан"),
            ("cancelled", "Цуцалсан"),
        ],
        string="Төлөв",
        readonly=True,
    )
    stop_count = fields.Integer(string="Нийт цэг", readonly=True)
    completed_stop_count = fields.Integer(string="Гүйцэтгэсэн", readonly=True)
    skipped_stop_count = fields.Integer(string="Алгассан", readonly=True)
    proof_count = fields.Integer(string="Зураг", readonly=True)
    issue_count = fields.Integer(string="Асуудал", readonly=True)
    weight_count = fields.Integer(string="Жингийн бүртгэл", readonly=True)
    total_net_weight = fields.Float(string="Цэвэр жин", readonly=True)
    actual_duration_hours = fields.Float(string="Бодит үргэлжлэх хугацаа", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    pt.id AS id,
                    pt.id AS task_id,
                    pt.project_id AS project_id,
                    pt.mfo_route_id AS route_id,
                    pt.mfo_district_id AS district_id,
                    pt.mfo_crew_team_id AS crew_team_id,
                    pt.mfo_vehicle_id AS vehicle_id,
                    pt.mfo_shift_date AS shift_date,
                    pt.mfo_operation_type AS operation_type,
                    pt.mfo_state AS mfo_state,
                    COALESCE(stop_data.stop_count, 0) AS stop_count,
                    COALESCE(stop_data.completed_stop_count, 0) AS completed_stop_count,
                    COALESCE(stop_data.skipped_stop_count, 0) AS skipped_stop_count,
                    COALESCE(proof_data.proof_count, 0) AS proof_count,
                    COALESCE(issue_data.issue_count, 0) AS issue_count,
                    COALESCE(daily_weight_data.weight_total_count, weight_data.weight_count, 0) AS weight_count,
                    COALESCE(daily_weight_data.total_net_weight, weight_data.total_net_weight, 0) AS total_net_weight,
                    COALESCE(EXTRACT(EPOCH FROM (pt.mfo_end_datetime - pt.mfo_start_datetime)) / 3600.0, 0) AS actual_duration_hours
                FROM project_task pt
                JOIN project_project pp ON pp.id = pt.project_id
                LEFT JOIN (
                    SELECT
                        task_id,
                        COUNT(*) AS stop_count,
                        COUNT(*) FILTER (WHERE status = 'done') AS completed_stop_count,
                        COUNT(*) FILTER (WHERE status = 'skipped') AS skipped_stop_count
                    FROM mfo_stop_execution_line
                    GROUP BY task_id
                ) stop_data ON stop_data.task_id = pt.id
                LEFT JOIN (
                    SELECT task_id, COUNT(*) AS proof_count
                    FROM mfo_proof_image
                    GROUP BY task_id
                ) proof_data ON proof_data.task_id = pt.id
                LEFT JOIN (
                    SELECT task_id, COUNT(*) AS issue_count
                    FROM mfo_issue_report
                    GROUP BY task_id
                ) issue_data ON issue_data.task_id = pt.id
                LEFT JOIN (
                    SELECT
                        task_id,
                        COUNT(*) AS weight_total_count,
                        COALESCE(SUM(net_weight_total), 0) AS total_net_weight
                    FROM mfo_daily_weight_total
                    GROUP BY task_id
                ) daily_weight_data ON daily_weight_data.task_id = pt.id
                LEFT JOIN (
                    SELECT
                        task_id,
                        COUNT(*) AS weight_count,
                        COALESCE(SUM(net_weight), 0) AS total_net_weight
                    FROM mfo_weight_measurement
                    GROUP BY task_id
                ) weight_data ON weight_data.task_id = pt.id
                WHERE pp.mfo_is_operation_project = TRUE
            )
            """
        )
