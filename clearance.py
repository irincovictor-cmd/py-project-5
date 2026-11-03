"""Domain rules independent from Tkinter. All changes are persisted atomically."""
from __future__ import annotations
import copy
import hashlib
import hmac
import os
from datetime import date, datetime
from html import escape
from pathlib import Path


class ClearanceError(ValueError):
    pass


def _hash(secret: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, 200_000).hex()


def _credential(secret: str) -> dict:
    if len(secret) < 8:
        raise ClearanceError("Password/PIN must be at least 8 characters")
    salt = os.urandom(16)
    return {"salt": salt.hex(), "hash": _hash(secret, salt)}


def _verify(secret: str, record: dict) -> bool:
    try:
        return hmac.compare_digest(_hash(secret, bytes.fromhex(record["salt"])), record["hash"])
    except (KeyError, ValueError, TypeError):
        return False


def _required(value: str, label: str, limit: int = 100) -> str:
    value = str(value).strip()
    if not value or len(value) > limit:
        raise ClearanceError(f"{label} must be 1–{limit} characters")
    return value


class ClearanceSystem:
    def __init__(self, store):
        self.store = store
        self.data = store.load()

    def _save(self, changed: dict, actor: str, action: str, detail: str) -> None:
        changed["audit"].append({"time": datetime.now().isoformat(timespec="seconds"),
                                 "actor": actor, "action": action, "detail": detail})
        self.store.save(changed)
        self.data = changed

    def has_admin(self) -> bool:
        return any(u["role"] == "admin" for u in self.data["users"])

    def initialize_admin(self, username: str, password: str) -> None:
        if self.has_admin():
            raise ClearanceError("An administrator already exists")
        self._new_user(username, password, "admin", None, actor="setup")

    def _new_user(self, username, password, role, department_id, actor):
        username = _required(username.lower(), "Username", 30)
        if not all(c.isascii() and (c.isalnum() or c == "_") for c in username):
            raise ClearanceError("Username may only contain letters, numbers and underscores")
        if any(u["username"] == username for u in self.data["users"]):
            raise ClearanceError("Username already exists")
        if role not in ("admin", "staff"):
            raise ClearanceError("Invalid user role")
        if role == "staff" and not self._find("departments", department_id):
            raise ClearanceError("Choose an existing department")
        changed = copy.deepcopy(self.data)
        changed["users"].append({"username": username, "role": role, "department_id": department_id,
                                 **_credential(password)})
        self._save(changed, actor, "create_account", username)

    def add_staff(self, username, password, department_id, actor):
        self.require_admin(actor)
        self._new_user(username, password, "staff", department_id, actor)

    def login(self, username: str, password: str) -> dict | None:
        username = username.strip().lower()
        for user in self.data["users"]:
            if user["username"] == username and _verify(password, user):
                return {"username": user["username"], "role": user["role"],
                        "department_id": user["department_id"]}
        return None

    def student_login(self, student_id: str, pin: str) -> dict | None:
        student = self._find("students", student_id.strip())
        if student and _verify(pin, student):
            return {k: student[k] for k in ("id", "name", "course", "year", "section")}
        return None

    def _find(self, section: str, identifier: str) -> dict | None:
        return next((item for item in self.data[section] if item["id"] == identifier), None)

    def _actor(self, username: str) -> dict:
        user = next((u for u in self.data["users"] if u["username"] == username), None)
        if not user:
            raise ClearanceError("Account not found")
        return user

    def require_admin(self, username: str) -> None:
        if self._actor(username)["role"] != "admin":
            raise ClearanceError("Administrator permission required")

    def set_period(self, period: str, actor: str) -> None:
        self.require_admin(actor)
        changed = copy.deepcopy(self.data)
        changed["active_period"] = _required(period, "Period", 80)
        self._save(changed, actor, "set_period", period)

    def add_student(self, student_id: str, name: str, course: str, year: str, section: str, pin: str, actor: str) -> None:
        self.require_admin(actor)
        student_id = _required(student_id, "Student ID", 30)
        if self._find("students", student_id):
            raise ClearanceError("Student ID already exists")
        changed = copy.deepcopy(self.data)
        changed["students"].append({"id": student_id,
           "name": _required(name, "Name"), "course": _required(course, "Course", 50),
           "year": _required(year, "Year", 20), "section": _required(section, "Section", 30),
           **_credential(pin)})
        self._save(changed, actor, "add_student", student_id)

    def add_department(self, name: str, actor: str) -> str:
        self.require_admin(actor)
        name = _required(name, "Department", 80)
        if any(d["name"].casefold() == name.casefold() for d in self.data["departments"]):
            raise ClearanceError("Department already exists")
        changed = copy.deepcopy(self.data)
        new_id = f"D{max((int(d['id'][1:]) for d in changed['departments']), default=0)+1:03d}"
        changed["departments"].append({"id": new_id, "name": name, "active": True})
        self._save(changed, actor, "add_department", name)
        return new_id

    def add_event(self, title: str, event_date: str, actor: str) -> str:
        self.require_admin(actor)
        title = _required(title, "Event title", 100)
        try:
            date.fromisoformat(event_date)
        except ValueError:
            raise ClearanceError("Date must be YYYY-MM-DD") from None
        changed = copy.deepcopy(self.data)
        new_id = f"E{max((int(e['id'][1:]) for e in changed['events']), default=0)+1:03d}"
        changed["events"].append({"id": new_id, "title": title, "date": event_date,
                                  "period": changed["active_period"], "required": True})
        self._save(changed, actor, "add_event", title)
        return new_id

    def record_attendance(self, student_id: str, event_id: str, status: str, note: str, actor: str) -> None:
        self.require_admin(actor)  # Event officer duties are represented by administrator in this prototype.
        if not self._find("students", student_id) or not self._find("events", event_id):
            raise ClearanceError("Student or event not found")
        if status not in ("Attended", "Absent", "Excused", "Make-up Completed", "Pending"):
            raise ClearanceError("Invalid attendance status")
        note = str(note).strip()[:300]
        if status in ("Excused", "Make-up Completed") and not note:
            raise ClearanceError("Explain the accepted excuse or completed make-up activity")
        changed = copy.deepcopy(self.data)
        period = changed["active_period"]
        event = self._find("events", event_id)
        if event["period"] != period:
            raise ClearanceError("Event belongs to a different clearance period")
        changed["attendance"] = [a for a in changed["attendance"] if not
           (a["student_id"] == student_id and a["event_id"] == event_id)]
        changed["attendance"].append({"student_id": student_id, "event_id": event_id,
           "status": status, "note": note, "actor": actor})
        self._save(changed, actor, "attendance", f"{student_id}: {event_id} → {status}")

    def approve_department(self, student_id: str, department_id: str, status: str, note: str, actor: str) -> None:
        user = self._actor(actor)
        if user["role"] != "admin" and user["department_id"] != department_id:
            raise ClearanceError("You may only approve your assigned department")
        if not self._find("students", student_id) or not self._find("departments", department_id):
            raise ClearanceError("Student or department not found")
        if status not in ("Approved", "Pending", "With Requirements"):
            raise ClearanceError("Invalid department status")
        note = str(note).strip()[:300]
        if status == "With Requirements" and not note:
            raise ClearanceError("Describe the outstanding requirement")
        changed = copy.deepcopy(self.data)
        period = changed["active_period"]
        changed["approvals"] = [a for a in changed["approvals"] if not
             (a["student_id"] == student_id and a["department_id"] == department_id and a["period"] == period)]
        changed["approvals"].append({"student_id": student_id, "department_id": department_id,
            "period": period, "status": status, "note": note, "actor": actor})
        self._save(changed, actor, "department_approval", f"{student_id}: {department_id} → {status}")

    def summary(self, student_id: str, period: str | None = None) -> dict:
        student = self._find("students", student_id)
        if not student:
            raise ClearanceError("Student not found")
        period = period or self.data["active_period"]
        events = [e for e in self.data["events"] if e["period"] == period and e["required"]]
        departments = [d for d in self.data["departments"] if d["active"]]
        erows, drows = [], []
        for e in events:
            record = next((a for a in self.data["attendance"] if a["student_id"] == student_id and a["event_id"] == e["id"]), None)
            erows.append({"name": e["title"], "date": e["date"], "status": record["status"] if record else "Pending",
                          "note": record["note"] if record else ""})
        for d in departments:
            record = next((a for a in self.data["approvals"] if a["student_id"] == student_id
                           and a["department_id"] == d["id"] and a["period"] == period), None)
            drows.append({"name": d["name"], "status": record["status"] if record else "Pending",
                          "note": record["note"] if record else ""})
        done_events = sum(r["status"] in ("Attended", "Excused", "Make-up Completed") for r in erows)
        done_depts = sum(r["status"] == "Approved" for r in drows)
        complete = bool(erows and drows and done_events == len(erows) and done_depts == len(drows))
        return {"student": {k: student[k] for k in ("id", "name", "course", "year", "section")},
                "period": period, "events": erows, "departments": drows,
                "event_pct": round(100 * done_events / len(erows)) if erows else 0,
                "department_pct": round(100 * done_depts / len(drows)) if drows else 0,
                "overall": "Cleared" if complete else "Incomplete"}

    def report_html(self, student_id: str) -> str:
        s = self.summary(student_id)
        student = s["student"]
        def table(rows):
            return "".join(f"<tr><td>{escape(r['name'])}</td><td>{escape(r['status'])}</td><td>{escape(r['note'])}</td></tr>" for r in rows)
        return f'''<!doctype html><html><head><meta charset="utf-8"><title>Student Clearance Summary</title>
<style>body{{font-family:serif;max-width:780px;margin:35px auto;color:#111}}h1,h2{{text-align:center}}table{{border-collapse:collapse;width:100%;margin:16px 0}}th,td{{border:1px solid #444;padding:8px;text-align:left}}@media print{{body{{margin:0}}}}</style></head><body>
<h1>STUDENT CLEARANCE SUMMARY</h1><p><b>Student:</b> {escape(student['name'])} &nbsp; <b>ID:</b> {escape(student['id'])}</p>
<p><b>Course/Year/Section:</b> {escape(student['course'])} / {escape(student['year'])} / {escape(student['section'])}</p>
<p><b>Clearance Period:</b> {escape(s['period'])}</p>
<h2>Mandatory Event Attendance ({s['event_pct']}%)</h2><table><tr><th>Event</th><th>Status</th><th>Remarks</th></tr>{table(s['events'])}</table>
<h2>Departmental Approvals ({s['department_pct']}%)</h2><table><tr><th>Department</th><th>Status</th><th>Remarks</th></tr>{table(s['departments'])}</table>
<h2>Overall Status: {escape(s['overall'])}</h2><p><small>Generated by an offline classroom prototype. Verify records with authorized school staff.</small></p></body></html>'''
