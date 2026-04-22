import json

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import HttpCase, SavepointCase
from odoo.fields import Command


class TestProcurementWorkflow(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency = cls.env.company.currency_id
        cls.department = cls.env["hr.department"].create({"name": "Туршилтын алба"})
        cls.project = cls.env["project.project"].create({"name": "Туршилтын төсөл"})
        cls.task = cls.env["project.task"].create({"name": "Туршилтын ажилбар", "project_id": cls.project.id})

        group_user = cls.env.ref("base.group_user")
        cls.group_requester = cls.env.ref("municipal_procurement_workflow.group_mpw_requester")
        cls.group_storekeeper = cls.env.ref("municipal_procurement_workflow.group_mpw_storekeeper")
        cls.group_finance = cls.env.ref("municipal_procurement_workflow.group_mpw_finance")
        cls.group_office = cls.env.ref("municipal_procurement_workflow.group_mpw_office_clerk")
        cls.group_contract = cls.env.ref("municipal_procurement_workflow.group_mpw_contract_officer")
        cls.group_director = cls.env.ref("municipal_procurement_workflow.group_mpw_director")
        cls.group_gm = cls.env.ref("municipal_procurement_workflow.group_mpw_general_manager")

        cls.requester_user = cls._create_user("mpw_requester", [group_user.id, cls.group_requester.id], "requester")
        cls.storekeeper_user = cls._create_user("mpw_storekeeper", [group_user.id, cls.group_storekeeper.id], "storekeeper")
        cls.storekeeper_user_two = cls._create_user("mpw_storekeeper_2", [group_user.id, cls.group_storekeeper.id], "storekeeper2")
        cls.finance_user = cls._create_user("mpw_finance", [group_user.id, cls.group_finance.id], "finance")
        cls.office_user = cls._create_user("mpw_office", [group_user.id, cls.group_office.id], "office")
        cls.contract_user = cls._create_user("mpw_contract", [group_user.id, cls.group_contract.id], "contract")
        cls.director_user = cls._create_user("mpw_director", [group_user.id, cls.group_director.id], "director")
        cls.gm_user = cls._create_user("mpw_gm", [group_user.id, cls.group_gm.id], "gm")

        requester_employee = cls.env["hr.employee"].create(
            {
                "name": "Хэлтсийн дарга",
                "user_id": cls.requester_user.id,
                "department_id": cls.department.id,
            }
        )
        cls.department.manager_id = requester_employee

        cls.supplier_a = cls.env["res.partner"].create({"name": "Нийлүүлэгч А", "supplier_rank": 1})
        cls.supplier_b = cls.env["res.partner"].create({"name": "Нийлүүлэгч Б", "supplier_rank": 1})
        cls.supplier_c = cls.env["res.partner"].create({"name": "Нийлүүлэгч В", "supplier_rank": 1})

    @classmethod
    def _create_user(cls, name, group_ids, password):
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": name,
                "login": name,
                "password": password,
                "groups_id": [Command.set(group_ids)],
            }
        )

    def _create_request(self):
        return self.env["mpw.procurement.request"].with_user(self.requester_user).create(
            {
                "title": "Нөөцийн хүсэлт",
                "project_id": self.project.id,
                "task_id": self.task.id,
                "department_id": self.department.id,
                "description": "Тест хүсэлт",
                "responsible_storekeeper_user_id": self.storekeeper_user.id,
                "required_date": "2026-04-30",
                "line_ids": [
                    Command.create(
                        {
                            "product_name_manual": "Шаардлагатай бараа",
                            "quantity": 2,
                            "approx_unit_price": 400000,
                        }
                    )
                ],
            }
        )

    def _submit_quotes(self, procurement_request, selected_total):
        procurement_request.with_user(self.requester_user).action_submit_for_quotation()
        procurement_request.with_user(self.storekeeper_user).sync_quotations_from_payload(
            [
                {"supplier_id": self.supplier_a.id, "amount_total": selected_total, "is_selected": True},
                {"supplier_id": self.supplier_b.id, "amount_total": selected_total + 10000},
                {"supplier_id": self.supplier_c.id, "amount_total": selected_total + 20000},
            ]
        )
        procurement_request.with_user(self.storekeeper_user).action_submit_quotations()

    def _create_attachment(self, name):
        return self.env["ir.attachment"].create(
            {
                "name": name,
                "datas": "VEVTVA==",
                "mimetype": "text/plain",
                "res_model": "mpw.procurement.request",
                "res_id": 0,
            }
        )

    def test_threshold_routing_low(self):
        procurement_request = self._create_request()
        self._submit_quotes(procurement_request, 999999)

        self.assertEqual(procurement_request.flow_type, "low")
        self.assertEqual(procurement_request.responsible_storekeeper_user_id, self.storekeeper_user)

        procurement_request.with_user(self.finance_user).write({"payment_reference": "PAY-LOW"})
        procurement_request.with_user(self.finance_user).action_move_to_finance_review()
        procurement_request.with_user(self.finance_user).action_select_supplier_and_pay()

        self.assertEqual(procurement_request.state, "paid")
        self.assertEqual(procurement_request.payment_status, "paid")

    def test_threshold_routing_high(self):
        procurement_request = self._create_request()
        self._submit_quotes(procurement_request, 1000000)

        self.assertEqual(procurement_request.flow_type, "high")

        procurement_request.with_user(self.office_user).action_prepare_director_order()
        draft_attachment = self._create_attachment("noorog.txt")
        procurement_request.with_user(self.office_user).add_document_with_attachments(
            "director_order_draft",
            [draft_attachment.id],
        )
        self.assertEqual(procurement_request.state, "director_pending")

        procurement_request.with_user(self.director_user).action_approve_order_decision()
        final_order_attachment = self._create_attachment("tushaal.txt")
        procurement_request.with_user(self.office_user).add_document_with_attachments(
            "director_order_final",
            [final_order_attachment.id],
        )
        procurement_request.with_user(self.office_user).action_attach_final_order()

        contract_attachment = self._create_attachment("geree.txt")
        procurement_request.with_user(self.contract_user).add_document_with_attachments(
            "contract_final",
            [contract_attachment.id],
        )
        procurement_request.with_user(self.contract_user).action_mark_contract_signed()
        procurement_request.with_user(self.finance_user).write({"payment_reference": "PAY-HIGH"})
        procurement_request.with_user(self.finance_user).action_pay_high_flow()
        procurement_request.with_user(self.storekeeper_user).action_mark_received()

        self.assertEqual(procurement_request.state, "received")
        self.assertEqual(procurement_request.receipt_status, "received")

    def test_high_flow_cannot_pay_before_contract(self):
        procurement_request = self._create_request()
        self._submit_quotes(procurement_request, 1000000)
        with self.assertRaises(UserError):
            procurement_request.with_user(self.finance_user).action_pay_high_flow()

    def test_requester_cannot_fake_finance_step(self):
        procurement_request = self._create_request()
        self._submit_quotes(procurement_request, 999999)
        procurement_request.with_user(self.requester_user).write({"notes_user": "Шинэ тэмдэглэл"})
        with self.assertRaises(AccessError):
            procurement_request.with_user(self.requester_user).action_select_supplier_and_pay()

    def test_general_manager_can_see_all_requests(self):
        procurement_request = self._create_request()
        visible_requests = self.env["mpw.procurement.request"].with_user(self.gm_user).search([])
        self.assertIn(procurement_request, visible_requests)

    def test_storekeeper_assignment_stays_specific(self):
        procurement_request = self._create_request()
        self.assertEqual(procurement_request.responsible_storekeeper_user_id, self.storekeeper_user)
        visible_requests_other_storekeeper = self.env["mpw.procurement.request"].with_user(
            self.storekeeper_user_two
        ).search([])
        self.assertNotIn(procurement_request, visible_requests_other_storekeeper)


class TestProcurementApi(HttpCase):
    def test_login_and_me_endpoints(self):
        payload = json.dumps(
            {
                "db": self.env.cr.dbname,
                "login": self.env.ref("base.user_admin").login,
                "password": "admin",
            }
        ).encode()
        response = self.url_open(
            "/mpw/api/login",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        me_response = self.url_open("/mpw/api/me")
        self.assertEqual(me_response.status_code, 200)
