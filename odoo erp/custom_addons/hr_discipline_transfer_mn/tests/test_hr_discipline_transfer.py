from odoo.tests.common import TransactionCase


class TestHrDisciplineTransfer(TransactionCase):
    def setUp(self):
        super().setUp()
        base_user_group = self.env.ref("base.group_user")
        discipline_group = self.env.ref("hr_discipline_transfer_mn.group_hr_discipline_manager")
        transfer_group = self.env.ref("hr_discipline_transfer_mn.group_hr_transfer_manager")
        director_group = self.env.ref("hr_discipline_transfer_mn.group_hr_director_approval")
        self.hr_manager_user = self.env["res.users"].create(
            {
                "name": "HR Manager Test",
                "login": "hr_manager_test",
                "email": "hr_manager_test@example.com",
                "groups_id": [(6, 0, [base_user_group.id, discipline_group.id, transfer_group.id])],
            }
        )
        self.director_user = self.env["res.users"].create(
            {
                "name": "Director Test",
                "login": "director_test",
                "email": "director_test@example.com",
                "groups_id": [(6, 0, [base_user_group.id, director_group.id])],
            }
        )
        self.department_a = self.env["hr.department"].create({"name": "Department A"})
        self.department_b = self.env["hr.department"].create({"name": "Department B"})
        self.job_a = self.env["hr.job"].create({"name": "Specialist"})
        self.job_b = self.env["hr.job"].create({"name": "Senior Specialist"})
        self.employee = self.env["hr.employee"].create(
            {
                "name": "Employee Test",
                "department_id": self.department_a.id,
                "job_id": self.job_a.id,
            }
        )
        self.attachment = self.env["ir.attachment"].create(
            {
                "name": "director_order.pdf",
                "datas": "dGVzdA==",
                "mimetype": "application/pdf",
                "type": "binary",
            }
        )

    def test_discipline_approval_updates_employee_status(self):
        action = self.env["hr.disciplinary.action"].with_user(self.hr_manager_user).create(
            {
                "employee_id": self.employee.id,
                "action_type": "termination_proposal",
                "violation_date": "2026-04-20",
                "effective_date": "2026-04-21",
                "violation_title": "Serious violation",
                "violation_description": "Detailed reason",
                "director_order_attachment_ids": [(6, 0, [self.attachment.id])],
            }
        )
        self.assertEqual(action.employee_department_id, self.department_a)
        action.with_user(self.hr_manager_user).button_submit()
        self.assertEqual(action.state, "submitted")
        action.with_user(self.director_user).button_approve()
        self.assertEqual(action.state, "approved")
        self.assertEqual(self.employee.employment_status, "terminated")

    def test_transfer_approval_updates_employee_department(self):
        transfer = self.env["hr.employee.transfer"].with_user(self.hr_manager_user).create(
            {
                "employee_id": self.employee.id,
                "new_department_id": self.department_b.id,
                "new_job_id": self.job_b.id,
                "movement_type": "department_transfer",
                "reason": "Operational change",
                "effective_date": "2026-04-22",
            }
        )
        transfer.with_user(self.hr_manager_user).button_submit()
        transfer.with_user(self.director_user).button_approve()
        self.assertEqual(transfer.state, "approved")
        self.assertEqual(self.employee.department_id, self.department_b)
        self.assertEqual(self.employee.job_id, self.job_b)
