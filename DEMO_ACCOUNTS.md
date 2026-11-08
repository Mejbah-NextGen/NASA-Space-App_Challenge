# Local demo accounts

These fictional accounts are created by:

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo
```

The command only runs with the development settings, `DEBUG=True`, and `DEMO_MODE=True`. All accounts use the local-development password `FarmDemo@2026!`.

| Role | Name | Email | Suggested walkthrough |
| --- | --- | --- | --- |
| Farmer | Rahim Mia | `farmer@farmtime.test` | Farms, rainfall history, decisions, and the consultation with Dr. Ayesha Rahman |
| Farmer | Salma Begum | `salma.farmer@farmtime.test` | Vegetable-farm records, tomato scenario, and the consultation with Dr. Farhana Akter |
| Agriculturalist | Dr. Ayesha Rahman | `agriculturalist@farmtime.test` | Assigned farmer, consultation thread, and published irrigation recommendation |
| Agriculturalist | Dr. Farhana Akter | `soil.expert@farmtime.test` | Soil/vegetable case, farm-data consent, and crop-care recommendation |
| Admin | System Admin | `admin@farmtime.test` | User, data-source, content, weather, support, and audit workspaces |
| Admin | Nadia Islam | `operations.admin@farmtime.test` | Secondary admin and review persona |

Farmer and agriculturalist profiles include fictional contact, location, experience, biography, and professional fields so profile pages are complete. Agriculturalist credential-review badges are informational; open registration and collaboration do not require an admin approval gate.

Never reuse this password for a real account, deploy these credentials publicly, or run the demo seeder against production data.

