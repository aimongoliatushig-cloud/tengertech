from odoo import fields, models, tools


class MfoPlanningDeviationReport(models.Model):
    _name = "mfo.planning.deviation.report"
    _description = "Төлөвлөлтийн зөрүүний тайлан"
    _auto = False
    _rec_name = "task_id"
    _order = "shift_date desc, task_id desc"

    task_id = fields.Many2one("project.task", string="Даалгавар", readonly=True)
    project_id = fields.Many2one("project.project", string="Төсөл", readonly=True)
    route_id = fields.Many2one("mfo.route", string="Маршрут", readonly=True)
    district_id = fields.Many2one("mfo.district", string="Дүүрэг", readonly=True)
    shift_date = fields.Date(string="Огноо", readonly=True)
    vehicle_id = fields.Many2one("fleet.vehicle", string="Техник", readonly=True)
    crew_team_id = fields.Many2one("mfo.crew.team", string="Экипаж", readonly=True)
    planned_stop_count = fields.Integer(string="Төлөвлөсөн цэг", readonly=True)
    completed_stop_count = fields.Integer(string="Гүйцэтгэсэн цэг", readonly=True)
    skipped_stop_count = fields.Integer(string="Алгассан цэг", readonly=True)
    deviation_stop_count = fields.Integer(string="Зөрүүний тоо", readonly=True)
    missing_proof = fields.Integer(string="Зураг дутсан эсэх", readonly=True)
    overdue_flag = fields.Integer(string="Хоцролт", readonly=True)

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
                    pt.mfo_shift_date AS shift_date,
                    pt.mfo_vehicle_id AS vehicle_id,
                    pt.mfo_crew_team_id AS crew_team_id,
                    COALESCE(route_data.planned_stop_count, 0) AS planned_stop_count,
                    COALESCE(stop_data.completed_stop_count, 0) AS completed_stop_count,
                    COALESCE(stop_data.skipped_stop_count, 0) AS skipped_stop_count,
                    ABS(COALESCE(route_data.planned_stop_count, 0) - COALESCE(stop_data.completed_stop_count, 0) - COALESCE(stop_data.skipped_stop_count, 0)) AS deviation_stop_count,
                    CASE WHEN COALESCE(proof_data.proof_count, 0) = 0 THEN 1 ELSE 0 END AS missing_proof,
                    CASE
                        WHEN pt.mfo_shift_date < CURRENT_DATE AND pt.mfo_state != 'verified' THEN 1
                        ELSE 0
                    END AS overdue_flag
                FROM project_task pt
                JOIN project_project pp ON pp.id = pt.project_id
                LEFT JOIN (
                    SELECT route_id, COUNT(*) AS planned_stop_count
                    FROM mfo_route_line
                    GROUP BY route_id
                ) route_data ON route_data.route_id = pt.mfo_route_id
                LEFT JOIN (
                    SELECT
                        task_id,
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
                WHERE pp.mfo_is_operation_project = TRUE
            )
            """
        )
