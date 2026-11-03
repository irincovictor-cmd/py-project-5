import tempfile
import unittest
from pathlib import Path

from clearance import ClearanceSystem, ClearanceError
from storage import JsonStore, StorageError


class ClearanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'system.json'
        self.service = ClearanceSystem(JsonStore(self.path))
        self.service.initialize_admin('admin', 'password123')
        self.service.add_student('2026-0001', 'Sample Student', 'BSIT', '3', 'A', 'student123', 'admin')
        self.did = self.service.add_department('Registrar', 'admin')
        self.eid = self.service.add_event('Intramurals', '2026-11-05', 'admin')

    def tearDown(self):
        self.temp.cleanup()

    def test_admin_initialization_and_authentication(self):
        self.assertIsNone(self.service.login('admin', 'wrong'))
        self.assertEqual(self.service.login('ADMIN', 'password123')['role'], 'admin')
        with self.assertRaises(ClearanceError):
            self.service.initialize_admin('other', 'password123')

    def test_student_private_pin(self):
        self.assertIsNone(self.service.student_login('2026-0001', 'badpin'))
        self.assertEqual(self.service.student_login('2026-0001', 'student123')['name'], 'Sample Student')

    def test_empty_not_cleared(self):
        summary = self.service.summary('2026-0001')
        self.assertEqual((summary['event_pct'], summary['department_pct']), (0, 0))
        self.assertEqual(summary['overall'], 'Incomplete')

    def test_approved_both_completes(self):
        self.service.record_attendance('2026-0001', self.eid, 'Attended', '', 'admin')
        self.service.approve_department('2026-0001', self.did, 'Approved', '', 'admin')
        self.assertEqual(self.service.summary('2026-0001')['overall'], 'Cleared')

    def test_absence_blocks_clearance(self):
        self.service.record_attendance('2026-0001', self.eid, 'Absent', '', 'admin')
        self.service.approve_department('2026-0001', self.did, 'Approved', '', 'admin')
        self.assertEqual(self.service.summary('2026-0001')['overall'], 'Incomplete')

    def test_excused_requires_note_and_counts(self):
        with self.assertRaises(ClearanceError):
            self.service.record_attendance('2026-0001', self.eid, 'Excused', '', 'admin')
        self.service.record_attendance('2026-0001', self.eid, 'Excused', 'Approved medical excuse', 'admin')
        self.assertEqual(self.service.summary('2026-0001')['event_pct'], 100)

    def test_makeup_requires_note_and_counts(self):
        with self.assertRaises(ClearanceError):
            self.service.record_attendance('2026-0001', self.eid, 'Make-up Completed', '', 'admin')
        self.service.record_attendance('2026-0001', self.eid, 'Make-up Completed', 'Completed assigned activity', 'admin')
        self.assertEqual(self.service.summary('2026-0001')['event_pct'], 100)

    def test_department_requirements_note(self):
        with self.assertRaises(ClearanceError):
            self.service.approve_department('2026-0001', self.did, 'With Requirements', '', 'admin')

    def test_staff_permissions(self):
        second = self.service.add_department('Finance', 'admin')
        self.service.add_staff('cashier', 'password123', second, 'admin')
        with self.assertRaises(ClearanceError):
            self.service.approve_department('2026-0001', self.did, 'Approved', '', 'cashier')
        self.service.approve_department('2026-0001', second, 'Approved', '', 'cashier')
        with self.assertRaises(ClearanceError):
            self.service.add_event('Seminar', '2026-12-01', 'cashier')

    def test_replace_decision_not_duplicate(self):
        self.service.approve_department('2026-0001', self.did, 'Pending', '', 'admin')
        self.service.approve_department('2026-0001', self.did, 'Approved', '', 'admin')
        self.assertEqual(len(self.service.data['approvals']), 1)

    def test_persistence(self):
        self.service.record_attendance('2026-0001', self.eid, 'Attended', '', 'admin')
        other = ClearanceSystem(JsonStore(self.path))
        self.assertEqual(other.summary('2026-0001')['event_pct'], 100)
        self.assertTrue(other.login('admin', 'password123'))

    def test_period_isolation(self):
        self.service.record_attendance('2026-0001', self.eid, 'Attended', '', 'admin')
        self.service.approve_department('2026-0001', self.did, 'Approved', '', 'admin')
        self.service.set_period('2026-2027 / 2nd Semester', 'admin')
        self.assertEqual(self.service.summary('2026-0001')['overall'], 'Incomplete')
        self.assertEqual(self.service.summary('2026-0001', '2026-2027 / 1st Semester')['overall'], 'Cleared')

    def test_escaped_report(self):
        self.service.add_student('X02', '<script>bad</script>', 'IT', '1', 'A', 'student123', 'admin')
        report = self.service.report_html('X02')
        self.assertIn('&lt;script&gt;bad&lt;/script&gt;', report)
        self.assertNotIn('<script>', report)

    def test_rejects_bad_records(self):
        with self.assertRaises(ClearanceError):
            self.service.add_student('2026-0001', 'Second Student', 'IT', '1', 'A', 'password123', 'admin')
        with self.assertRaises(ClearanceError):
            self.service.add_event('Wrong Date', '11/05/2026', 'admin')

    def test_does_not_overwrite_invalid_saved_data(self):
        self.path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(StorageError):
            ClearanceSystem(JsonStore(self.path))
        self.assertEqual(self.path.read_text(encoding='utf-8'), '{broken')


if __name__ == '__main__':
    unittest.main()
