import os
import subprocess
from datetime import date, timedelta

USERNAME = os.environ.get("SCOLENGO_USERNAME")
PASSWORD = os.environ.get("SCOLENGO_PASSWORD")

MONTH_CONFIGS = [
    (2026, 9, "septembre 2026"),
    (2026, 10, "octobre 2026"),
    (2026, 11, "novembre 2026"),
    (2026, 12, "décembre 2026"),
    (2027, 1, "janvier 2027"),
    (2027, 2, "février 2027"),
    (2027, 3, "mars 2027"),
    (2027, 4, "avril 2027"),
    (2027, 5, "mai 2027"),
    (2027, 6, "juin 2027"),
    (2027, 7, "juillet 2027"),
]


def login_scolengo():
    if not USERNAME or not PASSWORD:
        raise ValueError("Identifiants manquants dans les secrets GitHub.")

    print(f"Tentative de connexion pour : {USERNAME}")
    cmd = ["npx", "scolengo-cli", "auth", "login", "-u", USERNAME, "-p", PASSWORD]

    res = subprocess.run(cmd, capture_output=True, text=True, shell=True)

    print("STDOUT Connexion:", res.stdout.strip())
    print("STDERR Connexion:", res.stderr.strip())

    if res.returncode != 0:
        raise RuntimeError("Échec de la connexion à Scolengo")


def parse_vevents(ics_content):
    events = []
    in_event = False
    current_event = []
    for line in ics_content.splitlines():
        clean_line = line.strip("\r")
        if clean_line.startswith("BEGIN:VEVENT"):
            in_event = True
            current_event = [clean_line]
        elif clean_line.startswith("END:VEVENT") and in_event:
            current_event.append(clean_line)
            events.append("\n".join(current_event))
            in_event = False
            current_event = []
        elif in_event:
            current_event.append(clean_line)
    return events


def extract_uid(vevent_str):
    for line in vevent_str.splitlines():
        if line.startswith("UID:"):
            return line.split(":", 1)[1].strip()
    return None


def fetch_range(start_date, end_date, temp_filename="temp.ics"):
    cmd = [
        "npx",
        "scolengo-cli",
        "export",
        "calendar",
        "-f",
        start_date.strftime("%Y-%m-%d"),
        "-t",
        end_date.strftime("%Y-%m-%d"),
        temp_filename,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, shell=True)

    if not os.path.exists(temp_filename):
        print(
            f"Erreur export ({start_date} -> {end_date}): {res.stderr.strip()}"
        )
        return []

    with open(temp_filename, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    os.remove(temp_filename)
    return parse_vevents(content)


def fetch_period_recursive(start_date, end_date):
    events = fetch_range(start_date, end_date)
    if len(events) >= 100:
        total_days = (end_date - start_date).days
        if total_days < 1:
            return events
        mid_days = total_days // 2
        mid_date = start_date + timedelta(days=mid_days)
        return fetch_period_recursive(
            start_date, mid_date
        ) + fetch_period_recursive(mid_date + timedelta(days=1), end_date)
    return events


def main():
    print("Connexion à Scolengo...")
    login_scolengo()

    unique_events = {}
    total_raw = 0

    for year, month, label in MONTH_CONFIGS:
        s_date = date(year, month, 1)
        if month == 12:
            e_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            e_date = date(year, month + 1, 1) - timedelta(days=1)

        events = fetch_period_recursive(s_date, e_date)
        total_raw += len(events)
        print(f"Récupération {label}: {len(events)} événements")

        for ev in events:
            uid = extract_uid(ev) or hash(ev)
            unique_events[uid] = ev

    print(f"Total récupéré: {total_raw} | Uniques: {len(unique_events)}")

    output_filename = "emploi-du-temps-2026-2027.ics"
    ics_header = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:-//Scolengo//FR\n"
        "CALSCALE:GREGORIAN\n"
        "METHOD:PUBLISH\n"
        "X-WR-CALNAME:Emploi du temps 2026-2027\n"
        "X-WR-TIMEZONE:Europe/Paris\n"
    )
    ics_footer = "END:VCALENDAR\n"

    with open(output_filename, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(ics_header)
        for ev in unique_events.values():
            f.write(ev + "\n")
        f.write(ics_footer)


if __name__ == "__main__":
    main()
