from odoo.tests.common import TransactionCase


class TestHrClearance(TransactionCase):
    def setUp(self):
        super().setUp()
        user_group = self.env.ref("base.group_user")
        clearance_group = self.env.ref("hr_clearance_mn.group_hr_clearance_user")
        self.clearance_user = self.env["res.users"].create(
            {
                "name": "Clearance User",
                "login": "clearance_user_test",
                "email": "clearance_user_test@example.com",
                "groups_id": [(6, 0, [user_group.id, clearance_group.id])],
            }
        )
        self.department = self.env["hr.department"].create({"name": "HR"})
        self.job = self.env["hr.job"].create({"name": "Officer"})
        self.employee = self.env["hr.employee"].create(
            {
                "name": "Clearance Employee",
                "department_id": self.department.id,
                "job_id": self.job.id,
            }
        )

    def test_done_requires_all_checks(self):
        clearance = self.env["hr.employee.clearance"].with_user(self.clearance_user).create(
            {
                "employee_id": self.employee.id,
                "effective_date": "2026-04-25",
                "clearance_type": "resignation",
            }
        )
        clearance.with_user(self.clearance_user).button_start_progress()
        clearance.write(
            {
                "hr_check_done": True,
                "finance_check_done": True,
                "it_check_done": True,
                "asset_check_done": True,
                "manager_check_done": True,
                "final_hr_done": True,
            }
        )
        clearance.with_user(self.clearance_user).button_done()
        self.assertEqual(clearance.state, "done")
        self.assertTrue(clearance.final_hr_date)
