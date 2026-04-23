from datetime import datetime, timedelta, timezone

from odoo import _, api, fields, models

ULAANBAATAR_TZ = timezone(timedelta(hours=8))
PREVIOUS_DAY_SYNC_HOUR = 23
PREVIOUS_DAY_SYNC_MINUTE = 0


class MfoSyncLogExtension(models.Model):
    _inherit = "mfo.sync.log"

    @api.model
    def _mfo_compute_previous_day_sync_nextcall(self):
        local_now = datetime.now(timezone.utc).astimezone(ULAANBAATAR_TZ)
        next_local_run = local_now.replace(
            hour=PREVIOUS_DAY_SYNC_HOUR,
            minute=PREVIOUS_DAY_SYNC_MINUTE,
            second=0,
            microsecond=0,
        )
        if next_local_run <= local_now:
            next_local_run += timedelta(days=1)
        return next_local_run.astimezone(timezone.utc).replace(tzinfo=None)

    @api.model
    def _mfo_configure_previous_day_sync_cron(self):
        cron = self.env.ref("municipal_field_ops.ir_cron_mfo_weight_sync", raise_if_not_found=False)
        if not cron:
            return False
        cron.sudo().write(
            {
                "name": _("Өмнөх өдрийн машины жингийн синк"),
                "interval_number": 1,
                "interval_type": "days",
                "nextcall": fields.Datetime.to_string(self._mfo_compute_previous_day_sync_nextcall()),
                "active": True,
            }
        )
        return True

    def init(self):
        super().init()
        self._mfo_configure_previous_day_sync_cron()

    @api.model
    def cron_sync_weight_measurements(self):
        target_date = fields.Date.context_today(self) - timedelta(days=1)
        log = self.create(
            {
                "name": _("Автомат өмнөх өдрийн пүүгийн синк"),
                "sync_type": "weighbridge",
                "state": "running",
                "requested_at": fields.Datetime.now(),
                "payload_excerpt": '{"target":"previous_day","shift_date":"%s"}'
                % fields.Date.to_string(target_date),
            }
        )
        result_count = 0
        try:
            tasks = self.env["project.task"].search(
                [
                    ("mfo_operation_type", "=", "garbage"),
                    ("mfo_shift_date", "=", target_date),
                    ("mfo_vehicle_id", "!=", False),
                    ("mfo_state", "in", ["dispatched", "in_progress", "submitted", "verified"]),
                ],
                order="mfo_planned_start asc, id asc",
                limit=200,
            )
            for task in tasks:
                result_count += task.action_mfo_request_weight_sync(sync_log=log)
            log.write(
                {
                    "state": "warning" if not result_count else "success",
                    "finished_at": fields.Datetime.now(),
                    "result_count": result_count,
                    "response_excerpt": _(
                        "%(date)s өдрийн %(count)s мөрийн жингийн мэдээллийг машин тус бүрээр шинэчиллээ."
                    )
                    % {
                        "date": fields.Date.to_string(target_date),
                        "count": result_count,
                    },
                }
            )
        except Exception as exc:
            log.write(
                {
                    "state": "failed",
                    "finished_at": fields.Datetime.now(),
                    "error_message": str(exc),
                }
            )
        return True
