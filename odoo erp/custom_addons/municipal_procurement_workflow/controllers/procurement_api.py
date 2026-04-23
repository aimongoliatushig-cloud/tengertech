import base64

from odoo import fields, http
from odoo.fields import Command
from odoo.http import request


PROCUREMENT_ROLE_XMLIDS = (
    "municipal_procurement_workflow.group_mpw_requester",
    "municipal_procurement_workflow.group_mpw_storekeeper",
    "municipal_procurement_workflow.group_mpw_finance",
    "municipal_procurement_workflow.group_mpw_office_clerk",
    "municipal_procurement_workflow.group_mpw_contract_officer",
    "municipal_procurement_workflow.group_mpw_director",
    "municipal_procurement_workflow.group_mpw_general_manager",
    "municipal_procurement_workflow.group_mpw_admin",
    "base.group_system",
)


class ProcurementApiController(http.Controller):
    def _json_body(self):
        return request.httprequest.get_json(silent=True) or {}

    def _ok(self, data, status=200):
        payload = {"ok": True}
        payload.update(data)
        return request.make_json_response(payload, status=status)

    def _error(self, message, status=400, code="error"):
        return request.make_json_response(
            {
                "ok": False,
                "error": {
                    "code": code,
                    "message": message,
                },
            },
            status=status,
        )

    def _serialize_user(self, user):
        return {
            "id": user.id,
            "name": user.display_name,
            "login": user.login,
            "company": user.company_id.display_name,
            "flags": {
                "requester": user.has_group("municipal_procurement_workflow.group_mpw_requester"),
                "storekeeper": user.has_group("municipal_procurement_workflow.group_mpw_storekeeper"),
                "finance": user.has_group("municipal_procurement_workflow.group_mpw_finance"),
                "office_clerk": user.has_group("municipal_procurement_workflow.group_mpw_office_clerk"),
                "contract_officer": user.has_group("municipal_procurement_workflow.group_mpw_contract_officer"),
                "director": user.has_group("municipal_procurement_workflow.group_mpw_director"),
                "general_manager": user.has_group("municipal_procurement_workflow.group_mpw_general_manager"),
                "admin": user.has_group("municipal_procurement_workflow.group_mpw_admin")
                or user.has_group("base.group_system"),
            },
        }

    def _has_procurement_role(self, user=None):
        user = user or request.env.user
        return any(user.has_group(xmlid) for xmlid in PROCUREMENT_ROLE_XMLIDS)

    def _employee_visibility_domain(self, user=None):
        user = user or request.env.user
        return [
            "|",
            "|",
            "|",
            ("requester_user_id", "=", user.id),
            ("project_id.user_id", "=", user.id),
            ("task_id.user_ids", "in", user.id),
            ("department_id.manager_id.user_id", "=", user.id),
        ]

    def _get_request_read_context(self, domain=None):
        Request = request.env["mpw.procurement.request"]
        normalized_domain = domain or []
        if self._has_procurement_role():
            return Request, normalized_domain, False
        return Request.sudo(), normalized_domain + self._employee_visibility_domain(), True

    def _serialize_request(self, procurement_request, *, detail=False, read_only=False):
        payload = procurement_request._prepare_api_payload(detail=detail)
        if read_only:
            payload["available_actions"] = []
        return payload

    def _get_procurement_request(self, request_id):
        procurement_request = request.env["mpw.procurement.request"].browse(request_id).exists()
        if not procurement_request:
            return None
        procurement_request.check_access("read")
        procurement_request.check_access_rule("read")
        return procurement_request

    def _get_procurement_request_for_read(self, request_id):
        Request, domain, read_only = self._get_request_read_context([("id", "=", request_id)])
        procurement_request = Request.search(domain, limit=1)
        return procurement_request, read_only

    def _parse_request_filters(self):
        args = request.httprequest.args
        domain = []

        scope = args.get("scope")
        if scope == "mine":
            domain.append(("requester_user_id", "=", request.env.user.id))
        elif scope == "assigned":
            domain.append(("current_responsible_user_id", "=", request.env.user.id))

        state = args.get("state")
        if state:
            domain.append(("state", "=", state))

        flow_type = args.get("flow_type")
        if flow_type:
            domain.append(("flow_type", "=", flow_type))

        project_id = args.get("project_id")
        if project_id and project_id.isdigit():
            domain.append(("project_id", "=", int(project_id)))

        department_id = args.get("department_id")
        if department_id and department_id.isdigit():
            domain.append(("department_id", "=", int(department_id)))

        storekeeper_id = args.get("storekeeper_id")
        if storekeeper_id and storekeeper_id.isdigit():
            domain.append(("responsible_storekeeper_user_id", "=", int(storekeeper_id)))

        date_from = args.get("date_from")
        if date_from:
            domain.append(("create_date", ">=", date_from))

        date_to = args.get("date_to")
        if date_to:
            domain.append(("create_date", "<=", f"{date_to} 23:59:59"))

        search_term = (args.get("search") or "").strip()
        if search_term:
            domain.extend(
                [
                    "|",
                    "|",
                    ("name", "ilike", search_term),
                    ("title", "ilike", search_term),
                    ("selected_supplier_id.name", "ilike", search_term),
                ]
            )

        return domain

    def _create_attachment(self, *, file_name, mimetype, base64_data, res_model, res_id):
        if not file_name or not base64_data:
            raise ValueError("Файлын нэр болон өгөгдөл хоосон байна.")
        raw_data = base64_data
        if "," in base64_data and base64_data.split(",", 1)[0].startswith("data:"):
            raw_data = base64_data.split(",", 1)[1]
        base64.b64decode(raw_data, validate=True)
        return request.env["ir.attachment"].create(
            {
                "name": file_name,
                "datas": raw_data,
                "mimetype": mimetype or "application/octet-stream",
                "res_model": res_model,
                "res_id": res_id,
            }
        )

    def _apply_selected_quotation(self, procurement_request, payload):
        selected_quotation_id = payload.get("selected_quotation_id")
        if selected_quotation_id:
            quotation = procurement_request.quotation_ids.filtered(lambda item: item.id == int(selected_quotation_id))
            if not quotation:
                raise ValueError("Сонгосон үнийн санал буруу байна.")
            procurement_request.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(
                {"selected_quotation_id": quotation.id}
            )

    @http.route("/mpw/api/login", type="http", auth="public", methods=["POST"], csrf=False)
    def login(self, **kwargs):
        payload = self._json_body()
        db_name = payload.get("db") or request.env.cr.dbname
        login = (payload.get("login") or "").strip()
        password = payload.get("password") or ""
        if not login or not password:
            return self._error("Нэвтрэх нэр болон нууц үгээ оруулна уу.", status=400, code="missing_credentials")

        credential = {
            "login": login,
            "password": password,
            "type": "password",
        }
        auth_info = request.session.authenticate(request.env, credential)
        uid = auth_info.get("uid")
        if not uid:
            return self._error("Нэвтрэх мэдээлэл буруу байна.", status=401, code="invalid_credentials")

        user = request.env["res.users"].browse(uid)
        return self._ok({"user": self._serialize_user(user)})

    @http.route("/mpw/api/me", type="http", auth="user", methods=["GET"], csrf=False)
    def me(self, **kwargs):
        return self._ok({"user": self._serialize_user(request.env.user)})

    @http.route("/mpw/api/meta", type="http", auth="user", methods=["GET"], csrf=False)
    def meta(self, **kwargs):
        Project = request.env["project.project"].sudo()
        Task = request.env["project.task"].sudo()
        Department = request.env["hr.department"].sudo()
        Partner = request.env["res.partner"].sudo()
        Uom = request.env["uom.uom"].sudo()

        storekeeper_group = request.env.ref(
            "municipal_procurement_workflow.group_mpw_storekeeper",
            raise_if_not_found=False,
        )
        storekeepers = (
            storekeeper_group.user_ids.filtered(lambda user: not user.share)
            if storekeeper_group
            else request.env["res.users"].sudo()
        )

        return self._ok(
            {
                "projects": [
                    {"id": project.id, "name": project.display_name}
                    for project in Project.search([], limit=200, order="name asc")
                ],
                "tasks": [
                    {
                        "id": task.id,
                        "name": task.display_name,
                        "project_id": task.project_id.id,
                    }
                    for task in Task.search([], limit=300, order="project_id asc, name asc")
                ],
                "departments": [
                    {"id": department.id, "name": department.display_name}
                    for department in Department.search([], limit=200, order="name asc")
                ],
                "storekeepers": [
                    {"id": user.id, "name": user.display_name}
                    for user in storekeepers
                ],
                "suppliers": [
                    {"id": partner.id, "name": partner.display_name}
                    for partner in Partner.search([("supplier_rank", ">", 0)], limit=300, order="name asc")
                ],
                "uoms": [
                    {"id": uom.id, "name": uom.display_name}
                    for uom in Uom.search([], limit=300, order="name asc")
                ],
            }
        )

    @http.route("/mpw/api/requests", type="http", auth="user", methods=["GET"], csrf=False)
    def list_requests(self, **kwargs):
        page = max(int(request.httprequest.args.get("page", 1) or 1), 1)
        limit = max(min(int(request.httprequest.args.get("limit", 20) or 20), 100), 1)
        Request, domain, read_only = self._get_request_read_context(self._parse_request_filters())
        total = Request.search_count(domain)
        items = Request.search(domain, offset=(page - 1) * limit, limit=limit, order="create_date desc, id desc")
        return self._ok(
            {
                "items": [self._serialize_request(item, detail=False, read_only=read_only) for item in items],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": max((total + limit - 1) // limit, 1),
                },
            }
        )

    @http.route("/mpw/api/requests/<int:request_id>", type="http", auth="user", methods=["GET"], csrf=False)
    def request_detail(self, request_id, **kwargs):
        procurement_request, read_only = self._get_procurement_request_for_read(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        return self._ok({"item": self._serialize_request(procurement_request, detail=True, read_only=read_only)})

    @http.route("/mpw/api/requests", type="http", auth="user", methods=["POST"], csrf=False)
    def create_request(self, **kwargs):
        payload = self._json_body()
        try:
            line_commands = []
            for line in payload.get("lines", []):
                line_commands.append(
                    Command.create(
                        {
                            "sequence": line.get("sequence") or 10,
                            "product_id": int(line["product_id"]) if line.get("product_id") else False,
                            "product_name_manual": line.get("product_name"),
                            "specification": line.get("specification"),
                            "quantity": line.get("quantity") or 1.0,
                            "uom_id": int(line["uom_id"]) if line.get("uom_id") else False,
                            "approx_unit_price": line.get("approx_unit_price") or 0.0,
                            "final_unit_price": line.get("final_unit_price") or 0.0,
                            "remark": line.get("remark"),
                        }
                    )
                )

            values = {
                "title": payload.get("title"),
                "project_id": int(payload["project_id"]) if payload.get("project_id") else False,
                "task_id": int(payload["task_id"]) if payload.get("task_id") else False,
                "department_id": int(payload["department_id"]) if payload.get("department_id") else False,
                "description": payload.get("description"),
                "procurement_type": payload.get("procurement_type") or "goods",
                "urgency": payload.get("urgency") or "medium",
                "required_date": payload.get("required_date"),
                "responsible_storekeeper_user_id": int(payload["responsible_storekeeper_user_id"]),
                "notes_user": payload.get("notes_user"),
                "line_ids": line_commands,
            }
            procurement_request = request.env["mpw.procurement.request"].create(values)

            attachment_ids = []
            for attachment in payload.get("attachments", []):
                created_attachment = self._create_attachment(
                    file_name=attachment.get("name"),
                    mimetype=attachment.get("mimetype"),
                    base64_data=attachment.get("data"),
                    res_model=procurement_request._name,
                    res_id=procurement_request.id,
                )
                attachment_ids.append(created_attachment.id)

            if attachment_ids:
                procurement_request.add_document_with_attachments("other", attachment_ids, note=payload.get("notes_user"))
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)

        return self._ok({"item": procurement_request._prepare_api_payload(detail=True)}, status=201)

    @http.route(
        "/mpw/api/requests/<int:request_id>/submit",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def submit_request(self, request_id, **kwargs):
        procurement_request = self._get_procurement_request(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        try:
            procurement_request.action_submit_for_quotation()
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)
        return self._ok({"item": procurement_request._prepare_api_payload(detail=True)})

    @http.route(
        "/mpw/api/requests/<int:request_id>/submit_quotations",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def submit_quotations(self, request_id, **kwargs):
        procurement_request = self._get_procurement_request(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        payload = self._json_body()
        try:
            procurement_request.sync_quotations_from_payload(payload.get("quotations", []))
            self._apply_selected_quotation(procurement_request, payload)
            procurement_request.action_submit_quotations()
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)
        return self._ok({"item": procurement_request._prepare_api_payload(detail=True)})

    @http.route(
        "/mpw/api/requests/<int:request_id>/move_to_finance_review",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def move_to_finance_review(self, request_id, **kwargs):
        procurement_request = self._get_procurement_request(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        try:
            procurement_request.action_move_to_finance_review()
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)
        return self._ok({"item": procurement_request._prepare_api_payload(detail=True)})

    @http.route(
        "/mpw/api/requests/<int:request_id>/prepare_order",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def prepare_order(self, request_id, **kwargs):
        procurement_request = self._get_procurement_request(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        try:
            procurement_request.action_prepare_director_order()
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)
        return self._ok({"item": procurement_request._prepare_api_payload(detail=True)})

    @http.route(
        "/mpw/api/requests/<int:request_id>/director_decision",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def director_decision(self, request_id, **kwargs):
        procurement_request = self._get_procurement_request(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        payload = self._json_body()
        try:
            self._apply_selected_quotation(procurement_request, payload)
            procurement_request.action_approve_order_decision()
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)
        return self._ok({"item": procurement_request._prepare_api_payload(detail=True)})

    @http.route(
        "/mpw/api/requests/<int:request_id>/attach_final_order",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def attach_final_order(self, request_id, **kwargs):
        procurement_request = self._get_procurement_request(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        payload = self._json_body()
        try:
            attachment_ids = [int(attachment_id) for attachment_id in payload.get("attachment_ids", []) if attachment_id]
            if attachment_ids:
                procurement_request.add_document_with_attachments(
                    "director_order_final",
                    attachment_ids,
                    note=payload.get("note"),
                )
            procurement_request.action_attach_final_order()
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)
        return self._ok({"item": procurement_request._prepare_api_payload(detail=True)})

    @http.route(
        "/mpw/api/requests/<int:request_id>/mark_contract_signed",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def mark_contract_signed(self, request_id, **kwargs):
        procurement_request = self._get_procurement_request(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        payload = self._json_body()
        try:
            attachment_ids = [int(attachment_id) for attachment_id in payload.get("attachment_ids", []) if attachment_id]
            if attachment_ids:
                procurement_request.add_document_with_attachments(
                    "contract_final",
                    attachment_ids,
                    note=payload.get("note"),
                )
            procurement_request.action_mark_contract_signed()
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)
        return self._ok({"item": procurement_request._prepare_api_payload(detail=True)})

    @http.route(
        "/mpw/api/requests/<int:request_id>/mark_paid",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def mark_paid(self, request_id, **kwargs):
        procurement_request = self._get_procurement_request(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        payload = self._json_body()
        try:
            self._apply_selected_quotation(procurement_request, payload)
            update_values = {}
            if payload.get("payment_reference"):
                update_values["payment_reference"] = payload.get("payment_reference")
            if payload.get("payment_date"):
                update_values["payment_date"] = payload.get("payment_date")
            if update_values:
                procurement_request.with_context(mpw_allow_system_write=True, mpw_skip_write_audit=True).write(update_values)

            attachment_ids = [int(attachment_id) for attachment_id in payload.get("attachment_ids", []) if attachment_id]
            if attachment_ids:
                procurement_request.add_document_with_attachments(
                    "payment_proof",
                    attachment_ids,
                    note=payload.get("note"),
                )

            if procurement_request.flow_type == "high":
                procurement_request.action_pay_high_flow()
            else:
                if procurement_request.state == "quotations_ready":
                    procurement_request.action_move_to_finance_review()
                procurement_request.action_select_supplier_and_pay()
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)
        return self._ok({"item": procurement_request._prepare_api_payload(detail=True)})

    @http.route(
        "/mpw/api/requests/<int:request_id>/mark_received",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def mark_received(self, request_id, **kwargs):
        procurement_request = self._get_procurement_request(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        payload = self._json_body()
        try:
            attachment_ids = [int(attachment_id) for attachment_id in payload.get("attachment_ids", []) if attachment_id]
            if attachment_ids:
                procurement_request.add_document_with_attachments(
                    "receipt_proof",
                    attachment_ids,
                    note=payload.get("note"),
                )
            procurement_request.action_mark_received()
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)
        return self._ok({"item": procurement_request._prepare_api_payload(detail=True)})

    @http.route(
        "/mpw/api/requests/<int:request_id>/mark_done",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def mark_done(self, request_id, **kwargs):
        procurement_request = self._get_procurement_request(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        try:
            procurement_request.action_mark_done()
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)
        return self._ok({"item": procurement_request._prepare_api_payload(detail=True)})

    @http.route(
        "/mpw/api/requests/<int:request_id>/cancel",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def cancel(self, request_id, **kwargs):
        procurement_request = self._get_procurement_request(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        try:
            procurement_request.action_cancel()
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)
        return self._ok({"item": procurement_request._prepare_api_payload(detail=True)})

    @http.route(
        "/mpw/api/requests/<int:request_id>/upload_attachment",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def upload_attachment(self, request_id, **kwargs):
        procurement_request = self._get_procurement_request(request_id)
        if not procurement_request:
            return self._error("Хүсэлт олдсонгүй.", status=404, code="not_found")
        payload = self._json_body()
        try:
            created_attachment = self._create_attachment(
                file_name=payload.get("name"),
                mimetype=payload.get("mimetype"),
                base64_data=payload.get("data"),
                res_model=procurement_request._name,
                res_id=procurement_request.id,
            )
            target = payload.get("target") or "request"
            if target == "quotation":
                quotation_id = int(payload.get("quotation_id") or 0)
                quotation = procurement_request.quotation_ids.filtered(lambda item: item.id == quotation_id)
                if not quotation:
                    raise ValueError("Үнийн санал олдсонгүй.")
                quotation.write({"attachment_ids": [Command.link(created_attachment.id)]})
            elif target == "document":
                procurement_request.add_document_with_attachments(
                    payload.get("document_type") or "other",
                    [created_attachment.id],
                    note=payload.get("note"),
                )
        except Exception as error:  # pylint: disable=broad-except
            return self._error(str(error), status=400)
        return self._ok(
            {
                "attachment": {
                    "id": created_attachment.id,
                    "name": created_attachment.name,
                    "mimetype": created_attachment.mimetype,
                }
            },
            status=201,
        )

    @http.route("/mpw/api/dashboard", type="http", auth="user", methods=["GET"], csrf=False)
    def dashboard(self, **kwargs):
        Request, domain, read_only = self._get_request_read_context(self._parse_request_filters())
        records = Request.search(domain, order="create_date desc, id desc")

        today = fields.Date.context_today(Request)
        average_resolution_days = 0.0
        completed_records = records.filtered(lambda item: item.date_received)
        if completed_records:
            durations = []
            for item in completed_records:
                start_date = fields.Datetime.to_datetime(item.create_date)
                end_date = fields.Datetime.to_datetime(item.date_received)
                durations.append(max((end_date - start_date).total_seconds(), 0.0) / 86400.0)
            average_resolution_days = sum(durations) / len(durations)

        storekeeper_load = []
        for item in Request.read_group(domain, ["responsible_storekeeper_user_id"], ["responsible_storekeeper_user_id"]):
            if item["responsible_storekeeper_user_id"]:
                storekeeper_load.append(
                    {
                        "id": item["responsible_storekeeper_user_id"][0],
                        "name": item["responsible_storekeeper_user_id"][1],
                        "count": item["responsible_storekeeper_user_id_count"],
                    }
                )

        project_progress = []
        for item in Request.read_group(domain, ["project_id"], ["project_id"]):
            if item["project_id"]:
                project_progress.append(
                    {
                        "id": item["project_id"][0],
                        "name": item["project_id"][1],
                        "count": item["project_id_count"],
                    }
                )

        supplier_counts = []
        for item in Request.read_group(
            domain + [("selected_supplier_id", "!=", False)],
            ["selected_supplier_id"],
            ["selected_supplier_id"],
        ):
            supplier_counts.append(
                {
                    "id": item["selected_supplier_id"][0],
                    "name": item["selected_supplier_id"][1],
                    "count": item["selected_supplier_id_count"],
                }
            )

        return self._ok(
            {
                "metrics": {
                    "total": len(records),
                    "low_flow": len(records.filtered(lambda item: item.flow_type == "low")),
                    "high_flow": len(records.filtered(lambda item: item.flow_type == "high")),
                    "payment_pending": len(records.filtered(lambda item: item.payment_status != "paid")),
                    "receipt_pending": len(records.filtered(lambda item: item.receipt_status != "received")),
                    "delayed": len(records.filtered("is_delayed")),
                    "average_resolution_days": round(average_resolution_days, 1),
                    "generated_on": fields.Date.to_string(today),
                },
                "storekeeper_load": storekeeper_load,
                "project_progress": project_progress,
                "supplier_counts": supplier_counts,
                "items": [self._serialize_request(item, detail=False, read_only=read_only) for item in records[:20]],
            }
        )
