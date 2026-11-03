"""Student Clearance and Mandatory Event Compliance Monitoring — offline Tkinter GUI."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
from datetime import date

from storage import JsonStore, StorageError
from clearance import ClearanceSystem, ClearanceError

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / 'data' / 'clearance_data.json'


class App:
    def __init__(self, root, store_path=DATA_FILE):
        self.root = root
        self.root.title('Student Clearance & Event Compliance — Project 5')
        self.root.geometry('1140x760')
        self.root.minsize(900, 620)
        self.system = ClearanceSystem(JsonStore(store_path))
        self.actor = None
        self.student = None
        style = ttk.Style(root)
        style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'))
        style.configure('Subtitle.TLabel', font=('Segoe UI', 10))
        style.configure('Treeview', rowheight=27)
        self.show_login()

    def clear(self):
        for child in self.root.winfo_children():
            child.destroy()

    def error(self, exc):
        messagebox.showerror('Action Not Completed', str(exc), parent=self.root)

    def run_action(self, fn):
        try:
            fn()
            self.show_workspace()
        except (ClearanceError, StorageError, ValueError) as exc:
            self.error(exc)

    def heading(self, parent, title, subtitle=''):
        ttk.Label(parent, text=title, style='Title.TLabel').pack(anchor='w', pady=(0, 4))
        if subtitle:
            ttk.Label(parent, text=subtitle, style='Subtitle.TLabel').pack(anchor='w', pady=(0, 16))

    def show_login(self):
        self.actor = None
        self.student = None
        self.clear()
        outer = ttk.Frame(self.root, padding=30)
        outer.pack(fill='both', expand=True)
        self.heading(outer, 'Student Clearance Monitoring System', 'Project 5  |  Offline Python Desktop Application')
        if not self.system.has_admin():
            ttk.Label(outer, text='FIRST LAUNCH — CREATE ADMINISTRATOR', font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=12)
            uname = self.entry(outer, 'Administrator username')
            pwd = self.entry(outer, 'Password (8+ characters)', mask='*')
            confirm = self.entry(outer, 'Confirm password', mask='*')
            def setup():
                if pwd.get() != confirm.get():
                    return self.error('Passwords do not match')
                try:
                    self.system.initialize_admin(uname.get(), pwd.get())
                    messagebox.showinfo('Created', 'Administrator created. Sign in to continue.', parent=self.root)
                    self.show_login()
                except (ClearanceError, StorageError) as exc:
                    self.error(exc)
            ttk.Button(outer, text='Create Administrator', command=setup).pack(anchor='w', pady=15)
            return
        grid = ttk.Frame(outer)
        grid.pack(fill='x', pady=20)
        staffbox = ttk.LabelFrame(grid, text='Administrator / Department Staff', padding=22)
        staffbox.pack(side='left', fill='both', expand=True, padx=(0, 10))
        user = self.entry(staffbox, 'Username')
        password = self.entry(staffbox, 'Password', mask='*')
        def staff_login():
            session = self.system.login(user.get(), password.get())
            if session is None:
                return self.error('Incorrect username or password')
            self.actor = session
            self.show_workspace()
        ttk.Button(staffbox, text='Sign In', command=staff_login).pack(anchor='w', pady=10)
        studentbox = ttk.LabelFrame(grid, text='Student Clearance Lookup', padding=22)
        studentbox.pack(side='left', fill='both', expand=True, padx=(10, 0))
        sid = self.entry(studentbox, 'Student ID')
        pin = self.entry(studentbox, 'Student PIN (8+ characters)', mask='*')
        def student_login():
            session = self.system.student_login(sid.get(), pin.get())
            if session is None:
                return self.error('Student ID or PIN not recognized')
            self.student = session
            self.show_workspace()
        ttk.Button(studentbox, text='View My Clearance', command=student_login).pack(anchor='w', pady=10)
        ttk.Label(outer, text='Classroom prototype: records are local to this computer. Do not use real student details for demonstrations.',
                  foreground='#555').pack(anchor='w', pady=12)

    @staticmethod
    def entry(parent, caption, mask=None, default=''):
        ttk.Label(parent, text=caption).pack(anchor='w', pady=(7, 2))
        # Keep inputs a readable width instead of stretching across the window.
        e = ttk.Entry(parent, width=36, show=mask)
        e.pack(anchor='w')
        if default:
            e.insert(0, default)
        return e

    def show_workspace(self):
        if not self.actor and not self.student:
            return self.show_login()
        self.clear()
        top = ttk.Frame(self.root, padding=(18, 12))
        top.pack(fill='x')
        identity = self.actor['username'] if self.actor else self.student['name']
        role = self.actor['role'].title() if self.actor else 'Student'
        ttk.Label(top, text=f'Student Clearance  |  {role}: {identity}', style='Title.TLabel').pack(side='left')
        ttk.Button(top, text='Sign Out', command=self.show_login).pack(side='right')
        ttk.Separator(self.root).pack(fill='x')
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill='both', expand=True, padx=14, pady=12)
        self.add_tab('Dashboard', self.tab_dashboard)
        if self.student:
            self.add_tab('My Clearance', self.tab_my_clearance)
            return
        if self.actor['role'] == 'admin':
            self.add_tab('Students', self.tab_students)
            self.add_tab('Clearance Period', self.tab_period)
            self.add_tab('Departments & Staff', self.tab_departments)
            self.add_tab('Events', self.tab_events)
            self.add_tab('Attendance', self.tab_attendance)
        self.add_tab('Department Approvals', self.tab_approvals)
        self.add_tab('Clearance Lookup', self.tab_lookup)

    def add_tab(self, name, build):
        area = ttk.Frame(self.tabs, padding=18)
        self.tabs.add(area, text=name)
        build(area)

    def table(self, parent, columns, rows, height=10):
        container = ttk.Frame(parent)
        container.pack(fill='both', expand=True, pady=(8, 12))
        tree = ttk.Treeview(container, columns=columns, show='headings', height=height)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=130, minwidth=80, stretch=True)
        scroller = ttk.Scrollbar(container, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroller.set)
        tree.pack(side='left', fill='both', expand=True)
        scroller.pack(side='right', fill='y')
        for row in rows:
            tree.insert('', 'end', values=row)
        return tree

    def tab_dashboard(self, parent):
        period = self.system.data['active_period']
        self.heading(parent, 'Clearance Dashboard', f'Active period: {period}')
        if self.student:
            self.render_summary(parent, self.student['id'])
            return
        total = len(self.system.data['students'])
        cleared = sum(self.system.summary(s['id'])['overall'] == 'Cleared' for s in self.system.data['students'])
        details = [('Registered Students', total), ('Fully Cleared', cleared),
                   ('Incomplete', total-cleared), ('Mandatory Events', len([e for e in self.system.data['events'] if e['period'] == period])),
                   ('Active Departments', len([d for d in self.system.data['departments'] if d['active']]))]
        boxes = ttk.Frame(parent)
        boxes.pack(fill='x', pady=(0, 15))
        for label, value in details:
            box = ttk.LabelFrame(boxes, text=label, padding=18)
            box.pack(side='left', fill='x', expand=True, padx=4)
            ttk.Label(box, text=str(value), font=('Segoe UI', 22, 'bold')).pack()
        self.table(parent, ('Student ID', 'Student', 'Event %', 'Department %', 'Status'), [
            (s['id'], s['name'], f"{self.system.summary(s['id'])['event_pct']}%",
             f"{self.system.summary(s['id'])['department_pct']}%", self.system.summary(s['id'])['overall'])
            for s in self.system.data['students']])

    def tab_period(self, parent):
        self.heading(parent, 'Clearance Period', 'Switch between semesters without deleting previous records.')
        ttk.Label(parent, text='Current period: ' + self.system.data['active_period'],
                  font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=10)
        period = self.entry(parent, 'New academic period label (e.g., 2026-2027 / 2nd Semester)',
                            default=self.system.data['active_period'])
        ttk.Label(parent, text='Changing the active period hides earlier events and decisions from current clearance calculations.\n'
                  'Previous records remain saved and are not deleted. Add required events for the new period.',
                  foreground='#555').pack(anchor='w', pady=12)
        def change():
            if messagebox.askyesno('Change Clearance Period',
                    'Switch the active period? Existing records will be retained.', parent=self.root):
                self.run_action(lambda: self.system.set_period(period.get(), self.actor['username']))
        ttk.Button(parent, text='Set Active Period', command=change).pack(anchor='w', pady=10)

    def tab_students(self, parent):
        self.heading(parent, 'Student Management', 'Register students and create an individual lookup PIN.')
        frm = ttk.Frame(parent)
        frm.pack(fill='x')
        entries = {}
        labels = ('Student ID', 'Full Name', 'Course', 'Year', 'Section', 'Student PIN (8+ characters)')
        for row_index in range(2):
            line = ttk.Frame(frm)
            line.pack(fill='x')
            for label in labels[row_index*3:(row_index+1)*3]:
                col = ttk.Frame(line, padding=(4, 0))
                col.pack(side='left', fill='x', expand=True)
                entries[label] = self.entry(col, label, '*' if 'PIN' in label else None)
        def add():
            self.run_action(lambda: self.system.add_student(*(entries[k].get() for k in entries), self.actor['username']))
        ttk.Button(parent, text='Register Student', command=add).pack(anchor='w', pady=12)
        self.table(parent, ('ID', 'Name', 'Course', 'Year', 'Section'), [
            (s['id'], s['name'], s['course'], s['year'], s['section']) for s in self.system.data['students']])

    def tab_departments(self, parent):
        self.heading(parent, 'Department and Staff Accounts', 'Assign staff permissions to a specific school office.')
        area = ttk.Frame(parent)
        area.pack(fill='x')
        left = ttk.LabelFrame(area, text='Add Department', padding=14)
        left.pack(side='left', fill='both', expand=True, padx=(0, 8))
        department = self.entry(left, 'Department name')
        ttk.Button(left, text='Add Department', command=lambda: self.run_action(
            lambda: self.system.add_department(department.get(), self.actor['username']))).pack(anchor='w', pady=10)
        right = ttk.LabelFrame(area, text='Create Department Staff Account', padding=14)
        right.pack(side='left', fill='both', expand=True)
        username = self.entry(right, 'Username')
        password = self.entry(right, 'Password (8+ characters)', '*')
        ttk.Label(right, text='Assigned department').pack(anchor='w', pady=(8, 2))
        departments = self.system.data['departments']
        options = {f"{d['id']} — {d['name']}": d['id'] for d in departments}
        selector = ttk.Combobox(right, values=list(options), state='readonly', width=36)
        selector.pack(anchor='w')
        if options:
            selector.current(0)
        ttk.Button(right, text='Create Staff Account', command=lambda: self.run_action(
            lambda: self.system.add_staff(username.get(), password.get(), options.get(selector.get()), self.actor['username']))).pack(anchor='w', pady=10)
        self.table(parent, ('Code', 'Department'), [(d['id'], d['name']) for d in departments], 6)

    def tab_events(self, parent):
        self.heading(parent, 'Mandatory Event Management', 'Events apply to registered students in the active clearance period.')
        frm = ttk.Frame(parent)
        frm.pack(fill='x')
        left = ttk.Frame(frm)
        left.pack(side='left', fill='x', expand=True, padx=(0, 12))
        name = self.entry(left, 'Event title')
        right = ttk.Frame(frm)
        right.pack(side='left', fill='x', expand=True)
        when = self.entry(right, 'Date (YYYY-MM-DD)', default=date.today().isoformat())
        ttk.Button(parent, text='Add Mandatory Event', command=lambda: self.run_action(
            lambda: self.system.add_event(name.get(), when.get(), self.actor['username']))).pack(anchor='w', pady=12)
        self.table(parent, ('Event Code', 'Name', 'Date', 'Period'), [
            (e['id'], e['title'], e['date'], e['period']) for e in self.system.data['events']])

    def choose(self, parent, label, options):
        ttk.Label(parent, text=label).pack(anchor='w', pady=(8, 2))
        choices = {f'{ident} — {name}': ident for ident, name in options}
        box = ttk.Combobox(parent, values=list(choices), state='readonly', width=36)
        box.pack(anchor='w')
        if choices:
            box.current(0)
        return box, choices

    def tab_attendance(self, parent):
        self.heading(parent, 'Mandatory Event Attendance', 'Record attendance or an approved resolution of a missed event.')
        frm = ttk.Frame(parent)
        frm.pack(fill='x')
        left = ttk.Frame(frm)
        left.pack(side='left', fill='x', expand=True, padx=(0, 12))
        stu, stumap = self.choose(left, 'Student', [(s['id'], s['name']) for s in self.system.data['students']])
        ev, evmap = self.choose(left, 'Event (active period)', [(e['id'], e['title']) for e in self.system.data['events'] if e['period'] == self.system.data['active_period']])
        right = ttk.Frame(frm)
        right.pack(side='left', fill='x', expand=True)
        status, statusmap = self.choose(right, 'Attendance result', [(v, v) for v in
             ('Attended', 'Absent', 'Excused', 'Make-up Completed', 'Pending')])
        note = self.entry(right, 'Remarks / excuse / make-up completion details')
        ttk.Button(parent, text='Save Attendance', command=lambda: self.run_action(lambda: self.system.record_attendance(
            stumap.get(stu.get(), ''), evmap.get(ev.get(), ''), statusmap.get(status.get(), ''), note.get(), self.actor['username']))).pack(anchor='w', pady=12)
        event_names = {e['id']: e['title'] for e in self.system.data['events']}
        self.table(parent, ('Student ID', 'Event', 'Status', 'Remarks'), [
            (a['student_id'], event_names.get(a['event_id'], a['event_id']), a['status'], a['note'])
            for a in self.system.data['attendance']])

    def tab_approvals(self, parent):
        self.heading(parent, 'Department Clearance Approvals', 'Department staff may only update their assigned office.')
        is_admin = self.actor['role'] == 'admin'
        departments = [d for d in self.system.data['departments'] if d['active'] and
           (is_admin or self.actor['department_id'] == d['id'])]
        form = ttk.Frame(parent)
        form.pack(fill='x')
        left = ttk.Frame(form)
        left.pack(side='left', fill='x', expand=True, padx=(0, 12))
        student, smap = self.choose(left, 'Student', [(s['id'], s['name']) for s in self.system.data['students']])
        dept, dmap = self.choose(left, 'Department', [(d['id'], d['name']) for d in departments])
        right = ttk.Frame(form)
        right.pack(side='left', fill='x', expand=True)
        status, statusmap = self.choose(right, 'Clearance status', [(v, v) for v in ('Approved', 'Pending', 'With Requirements')])
        remarks = self.entry(right, 'Remarks / pending obligation')
        ttk.Button(parent, text='Save Department Decision', command=lambda: self.run_action(
            lambda: self.system.approve_department(smap.get(student.get(), ''), dmap.get(dept.get(), ''),
                statusmap.get(status.get(), ''), remarks.get(), self.actor['username']))).pack(anchor='w', pady=12)
        dept_names = {d['id']: d['name'] for d in departments}
        self.table(parent, ('Student ID', 'Department', 'Decision', 'Remarks', 'Approved By'), [
            (a['student_id'], dept_names[a['department_id']], a['status'], a['note'], a['actor'])
            for a in self.system.data['approvals'] if a['department_id'] in dept_names
                and a['period'] == self.system.data['active_period']])

    def tab_lookup(self, parent):
        self.heading(parent, 'Clearance Lookup and Print Summary', 'Admin/staff may examine current records; students access only their own clearance.')
        choices = [(s['id'], s['name']) for s in self.system.data['students']]
        selection, mapping = self.choose(parent, 'Choose student', choices)
        content = ttk.Frame(parent)
        content.pack(fill='both', expand=True, pady=14)
        def lookup():
            for c in content.winfo_children():
                c.destroy()
            if selection.get() in mapping:
                self.render_summary(content, mapping[selection.get()])
        ttk.Button(parent, text='View Clearance', command=lookup).pack(anchor='w')

    def tab_my_clearance(self, parent):
        self.heading(parent, 'My Clearance', 'Read-only student access')
        self.render_summary(parent, self.student['id'])

    def render_summary(self, parent, student_id):
        summary = self.system.summary(student_id)
        s = summary['student']
        ttk.Label(parent, text=f"{s['name']}  |  {s['id']}  |  {s['course']} · {s['year']} · {s['section']}",
                  font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(5, 8))
        ttk.Label(parent, text=f"Event completion: {summary['event_pct']}%    Department approvals: {summary['department_pct']}%    Overall: {summary['overall']}",
                  font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 8))
        for label, rows in [('Mandatory School Events', summary['events']), ('Departmental Clearances', summary['departments'])]:
            ttk.Label(parent, text=label, font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(8, 2))
            frame = ttk.Frame(parent)
            frame.pack(fill='both', expand=True)
            tree = ttk.Treeview(frame, columns=('Item', 'Status', 'Remarks'), show='headings', height=5)
            for col in ('Item', 'Status', 'Remarks'):
                tree.heading(col, text=col)
                tree.column(col, width=220 if col != 'Remarks' else 320)
            tree.pack(fill='both', expand=True)
            for item in rows:
                tree.insert('', 'end', values=(item['name'], item['status'], item['note']))
        def export():
            filename = filedialog.asksaveasfilename(parent=self.root, title='Save printable clearance summary',
                 defaultextension='.html', filetypes=[('HTML document', '*.html')],
                 initialfile=f"clearance_{student_id}.html")
            if filename:
                try:
                    Path(filename).write_text(self.system.report_html(student_id), encoding='utf-8')
                    messagebox.showinfo('Report Saved', 'Open the HTML file in a browser and use Ctrl+P to print.', parent=self.root)
                except OSError as exc:
                    self.error(exc)
        ttk.Button(parent, text='Export Printable Summary (HTML)', command=export).pack(anchor='w', pady=12)


def main():
    root = tk.Tk()
    try:
        App(root)
    except StorageError as exc:
        messagebox.showerror('Unable to Open Saved Records', str(exc), parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == '__main__':
    main()
