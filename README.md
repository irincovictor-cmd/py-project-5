# Project 5 — Student Clearance and Mandatory Event Compliance Monitoring System

An **offline, single-computer** Python/Tkinter classroom prototype. No database server, SQL, or external Python packages are required. Records are written to local JSON files.

## Run on Windows

Install Python 3.10+ with Tkinter. In PowerShell or CMD, open the extracted project folder:

```powershell
python -m tkinter
python main.py
```

On first launch, create the administrator account. Sign in and register departments (e.g., Registrar, Academic Department, Guidance, Finance/Cashier), staff accounts, students, and required events (e.g., Intramurals, seminar, acquaintance party). Staff accounts are assigned to one department and cannot approve other departments. Students can sign in with their Student ID plus an 8+ character PIN to see their **own** records.

## System rules

- Mandatory events must have `Attended`, `Excused`, or `Make-up Completed` status to count as complete. Excuse/make-up approval requires a remark and is entered by an administrator in this prototype.
- An `Absent` or `Pending` event does not count toward completion.
- Departments count as complete only with an `Approved` status. `With Requirements` requires remarks.
- Final clearance is **Cleared** only when at least one mandatory event and at least one active department exist, and every required event and active department has passed its checks. This protects against false 100% clearance when a checklist is empty.
- Active clearance period is stored in JSON. Event attendance and departmental decisions are isolated by period. Administrators can switch the active period using the Clearance Period tab.
- Student PINs and staff passwords are salted and hashed. No hardcoded demo accounts are used.
- Student lookups require a PIN, not Student ID alone. This is a teaching prototype, not a production privacy/security solution.
- Export printable HTML summaries; open the generated HTML in a browser and print via Ctrl+P or Save as PDF.

## Core files

- `main.py` — Tkinter UI with role-specific tabs
- `clearance.py` — validation, authorization, attendance, approvals, progress and printable report rules
- `storage.py` — validated JSON reads and atomic writes
- `tests/test_clearance.py` — automated business-logic tests
- `data/clearance_data.json` — created on first successful action; excluded from Git and ZIP

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Data safety

**Back up `data/clearance_data.json` before transferring or reinstalling the app.** Do not delete or overwrite that file if you want to keep records. JSON persistence is intended for one running application on one computer. There is no multi-device synchronization or concurrent-edit protection. Invalid saved JSON is rejected, not silently erased. The UI is suitable for use with fictional class demonstration data; do not load real confidential student details into an unapproved prototype.

## Known limitations

- All events created in a period are mandatory for every registered student; per-course/per-year assignment is not yet supported.
- Records can be added and decisions updated, but editing student demographics, deactivating departments, and advanced audit displays are not yet implemented.
- Report export is HTML (printable from a browser), not a native PDF generator.
