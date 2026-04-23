import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from odoo import _, fields, models


def _normalize_vehicle_identifier(value):
    return "".join(str(value or "").upper().split())


def _extract_incoming_vehicle_identifiers(item):
    return {
        normalized
        for normalized in (
            _normalize_vehicle_identifier(item.get("vehicleCode")),
            _normalize_vehicle_identifier(item.get("vehicleLabel")),
            _normalize_vehicle_identifier(item.get("vehiclePlate")),
            _normalize_vehicle_identifier(item.get("vehiclePlateNumber")),
            _normalize_vehicle_identifier(item.get("licensePlate")),
            _normalize_vehicle_identifier(item.get("plateNumber")),
            _normalize_vehicle_identifier(item.get("carNumber")),
            _normalize_vehicle_identifier(item.get("vehicleNumber")),
        )
        if normalized
    }


class ProjectTaskWeightSync(models.Model):
    _inherit = "project.task"

    def _mfo_fetch_external_daily_weight_payloads(self, sync_log=False):
        self.ensure_one()
        shift_date = fields.Date.to_string(self.mfo_shift_date or fields.Date.context_today(self))
        vehicle_code = (self.mfo_vehicle_id.mfo_wrs_vehicle_code or "").strip()
        license_plate = (self.mfo_vehicle_id.license_plate or "").strip()
        vehicle_identifiers = {
            code
            for code in (
                _normalize_vehicle_identifier(vehicle_code),
                _normalize_vehicle_identifier(license_plate),
            )
            if code
        }
        url, token = self._mfo_get_wrs_sync_settings()

        if sync_log:
            sync_log.write(
                {
                    "task_id": self.id,
                    "vehicle_id": self.mfo_vehicle_id.id,
                    "payload_excerpt": json.dumps(
                        {
                            "url": url,
                            "shift_date": shift_date,
                            "vehicle_code": vehicle_code,
                            "license_plate": license_plate,
                        },
                        ensure_ascii=False,
                    ),
                }
            )

        if not url:
            if sync_log:
                sync_log.write(
                    {
                        "state": "warning",
                        "finished_at": fields.Datetime.now(),
                        "error_message": _(
                            "`municipal_field_ops.wrs_normalized_url` эсвэл `MFO_WRS_NORMALIZED_URL` тохируулаагүй байна."
                        ),
                    }
                )
            return []

        if not vehicle_identifiers:
            if sync_log:
                sync_log.write(
                    {
                        "state": "warning",
                        "finished_at": fields.Datetime.now(),
                        "error_message": _("Техникийн WRS код эсвэл улсын дугаар тохируулаагүй байна."),
                    }
                )
            return []

        request_url = f"{url}{'&' if '?' in url else '?'}date={quote(shift_date)}"
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            request = Request(request_url, headers=headers, method="GET")
            with urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if sync_log:
                sync_log.write(
                    {
                        "state": "failed",
                        "finished_at": fields.Datetime.now(),
                        "error_message": f"WRS endpoint HTTP {exc.code}",
                    }
                )
            return []
        except (URLError, TimeoutError, ValueError) as exc:
            if sync_log:
                sync_log.write(
                    {
                        "state": "failed",
                        "finished_at": fields.Datetime.now(),
                        "error_message": str(exc),
                    }
                )
            return []

        totals = payload.get("totals") if isinstance(payload, dict) else []
        matched_payloads = []
        for item in totals or []:
            incoming_vehicle_identifiers = _extract_incoming_vehicle_identifiers(item)
            if not incoming_vehicle_identifiers.intersection(vehicle_identifiers):
                continue
            matched_payloads.append(
                {
                    "shift_date": item.get("requestedDate") or shift_date,
                    "net_weight_total": float(item.get("netWeightTotal") or 0.0),
                    "external_reference": item.get("externalReference")
                    or f"{shift_date}:{license_plate or vehicle_code}",
                    "source": item.get("source") or "wrs_normalized",
                    "note": item.get("vehicleLabel")
                    or item.get("licensePlate")
                    or item.get("branchName"),
                }
            )

        if sync_log:
            sync_log.write(
                {
                    "response_excerpt": json.dumps(
                        matched_payloads,
                        ensure_ascii=False,
                    ),
                }
            )
        return matched_payloads
