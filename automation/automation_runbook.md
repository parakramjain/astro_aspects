# automation_runbook.md
## Astro Aspects – systemd automation runbook (EC2 Ubuntu)

**Purpose:** Run weekly batch forecast job using `systemd` timer + service.  
**App root:** `/astro_aspects`  
**Run as user:** `ubuntu`  
**Schedule:** Every **Monday** at **05:00** (server local time)  
**Service name:** `astro_weekly.service`  
**Timer name:** `astro_weekly.timer`

---

## 0) Job definition

| Item | Value |
|---|---|
| WorkingDirectory | `/astro_aspects` |
| Command | `/astro_aspects/venv/bin/python3 -m automation.batch_report_runner_daily --csv /astro_aspects/automation/natal_inputs_for_daily_forecast_v1.csv --output /astro_aspects/output --send-email` |
| Trigger | systemd timer |
| OnCalendar | `Mon *-*-* 05:00:00` |
| Persistent | `false` |

---

## 1) Pre-checks (one-time)

| # | Command | Why / Expected |
|---:|---|---|
| 1 | `ls -la /astro_aspects` | Confirm app folder exists. |
| 2 | `ls -la /astro_aspects/venv/bin/` | Confirm venv exists and contains `python3`. |
| 3 | `/astro_aspects/venv/bin/python3 -V` | Confirm interpreter runs. |
| 4 | `ls -la /astro_aspects/automation/natal_inputs_for_daily_forecast_v1.csv` | Confirm CSV exists. |
| 5 | `mkdir -p /astro_aspects/output && ls -la /astro_aspects/output` | Ensure output folder exists. |
| 6 | `sudo -u ubuntu /astro_aspects/venv/bin/python3 -m automation.batch_report_runner_daily --csv /astro_aspects/automation/natal_inputs_for_daily_forecast_v1.csv --output /astro_aspects/output --send-email` | Validate job runs manually as the same user as systemd. |

---

## 2) Create the systemd service (one-time)

| # | Command | Why / Expected |
|---:|---|---|
| 1 | `sudo nano /etc/systemd/system/astro_weekly.service` | Create/edit the service unit file. |
| 2 | `sudo systemctl daemon-reload` | Load new unit definitions. |

**Paste this service file exactly:**
```ini
[Unit]
Description=Astro Weekly Forecast Batch Job
After=network.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/astro_aspects
ExecStart=/astro_aspects/venv/bin/python3 -m automation.batch_report_runner_daily --csv /astro_aspects/automation/natal_inputs_for_daily_forecast_v1.csv --output /astro_aspects/output --send-email
Environment=PYTHONUNBUFFERED=1
TimeoutStartSec=900

[Install]
WantedBy=multi-user.target
```

---

## 3) Create the systemd timer (one-time)

| # | Command | Why / Expected |
|---:|---|---|
| 1 | `sudo nano /etc/systemd/system/astro_weekly.timer` | Create/edit the timer unit file. |
| 2 | `sudo systemctl daemon-reload` | Load timer definition changes. |

**Paste this timer file exactly (Monday 5 AM):**
```ini
[Unit]
Description=Run Astro Weekly Forecast Every Monday 5 AM

[Timer]
OnCalendar=Mon *-*-* 05:00:00
Persistent=false
Unit=astro_weekly.service

[Install]
WantedBy=timers.target
```

---

## 4) Enable + start the automation

| # | Command | Why / Expected |
|---:|---|---|
| 1 | `sudo systemctl enable astro_weekly.timer` | Start timer on reboot. |
| 2 | `sudo systemctl start astro_weekly.timer` | Start the timer now. |
| 3 | `systemctl list-timers --all | grep astro_weekly` | Confirm next run time is Monday 05:00. |

---

## 5) Manual run (on-demand)

| # | Command | Why / Expected |
|---:|---|---|
| 1 | `sudo systemctl start astro_weekly.service` | Trigger the job immediately. |
| 2 | `sudo systemctl status astro_weekly.service --no-pager -l` | Check success/failure quickly. |

---

## 6) Monitoring & logs

| # | Command | Why / Expected |
|---:|---|---|
| 1 | `sudo systemctl status astro_weekly.timer --no-pager -l` | Timer health + next run. |
| 2 | `systemctl list-timers --all | grep astro_weekly` | Next/last run timestamps. |
| 3 | `journalctl -u astro_weekly.service -n 200 --no-pager` | Last 200 log lines of the job run. |
| 4 | `journalctl -u astro_weekly.service --since "1 day ago" --no-pager` | Logs for the last day. |
| 5 | `journalctl -u astro_weekly.timer -n 200 --no-pager` | Timer-specific logs. |

---

## 7) Update the schedule (change day/time)

**Example: change to Monday 05:00** (already set).

| # | Command | Why / Expected |
|---:|---|---|
| 1 | `sudo nano /etc/systemd/system/astro_weekly.timer` | Edit schedule. |
| 2 | `sudo systemctl daemon-reload` | Reload unit files. |
| 3 | `sudo systemctl restart astro_weekly.timer` | Apply the new schedule. |
| 4 | `systemctl list-timers --all | grep astro_weekly` | Verify next run time. |

**Reference OnCalendar patterns:**
- `Mon *-*-* 05:00:00` = every Monday 05:00
- `Sun *-*-* 05:00:00` = every Sunday 05:00
- `*-*-* 03:00:00` = daily 03:00

---

## 8) Update the command (CSV path/module/flags)

| # | Command | Why / Expected |
|---:|---|---|
| 1 | `sudo nano /etc/systemd/system/astro_weekly.service` | Edit `ExecStart` or other service fields. |
| 2 | `sudo systemctl daemon-reload` | Reload changes. |
| 3 | `sudo systemctl restart astro_weekly.timer` | Ensure timer points to updated service. |
| 4 | `sudo systemctl start astro_weekly.service` | Smoke-test the updated command. |
| 5 | `journalctl -u astro_weekly.service -n 200 --no-pager` | Confirm it runs cleanly. |

---

## 9) Stop / disable / remove

| # | Command | Why / Expected |
|---:|---|---|
| 1 | `sudo systemctl stop astro_weekly.timer` | Stop future scheduled runs. |
| 2 | `sudo systemctl disable astro_weekly.timer` | Prevent auto-start on reboot. |
| 3 | `sudo systemctl stop astro_weekly.service` | Stop a running job (rare for oneshot). |
| 4 | `sudo rm -f /etc/systemd/system/astro_weekly.timer /etc/systemd/system/astro_weekly.service` | Remove unit files. |
| 5 | `sudo systemctl daemon-reload` | Forget removed units. |
| 6 | `sudo systemctl reset-failed` | Clear failed states. |

---

## 10) Common failures & fixes

### A) `status=203/EXEC`
Systemd cannot execute `ExecStart`.

| # | Command | Fix |
|---:|---|---|
| 1 | `ls -la /astro_aspects/venv/bin/python3` | If missing, venv path is wrong or venv not created. |
| 2 | `file /astro_aspects/venv/bin/python3` | Confirm it is a valid executable. |
| 3 | `sudo -u ubuntu /astro_aspects/venv/bin/python3 -V` | Confirm it runs as `ubuntu`. |
| 4 | `systemctl cat astro_weekly.service` | Confirm final merged unit has the expected `ExecStart`. |

**If venv is missing, recreate:**
| # | Command | Why / Expected |
|---:|---|---|
| 1 | `cd /astro_aspects` | Go to project root. |
| 2 | `rm -rf venv` | Remove broken venv. |
| 3 | `python3 -m venv venv` | Recreate venv. |
| 4 | `./venv/bin/pip install -r requirements.txt` | Reinstall deps. |

### B) Import/module errors
| # | Command | Fix |
|---:|---|---|
| 1 | `sudo -u ubuntu /astro_aspects/venv/bin/python3 -c "import automation"` | Confirms module import works. |
| 2 | `sudo -u ubuntu /astro_aspects/venv/bin/python3 -m automation.batch_report_runner_daily --help` | Confirms module entrypoint works. |

### C) Timezone mismatch (runs at unexpected time)
| # | Command | Fix |
|---:|---|---|
| 1 | `timedatectl` | Check current timezone. |
| 2 | `cat /etc/timezone` | Confirm configured timezone (Ubuntu). |

---

## 11) Operational improvements (recommended)

| Area | Suggestion | Benefit |
|---|---|---|
| Functionality | Add a lock (`flock`) wrapper to prevent overlapping runs | Avoid duplicates if triggered manually + scheduled close together. |
| Performance | Batch email sends; add provider rate limiting | Prevent throttling / failures at scale. |
| Reliability | `Persistent=true` if you want missed runs after reboot to execute | Reduces missed jobs during downtime. |
| Security | Store secrets in AWS SSM Parameter Store; avoid plaintext files | Better key management and auditability. |
| Operations | Ship journald logs to CloudWatch + alarm on failure | Faster incident response. |
