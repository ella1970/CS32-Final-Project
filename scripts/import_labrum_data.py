#!/usr/bin/env python3
"""
scripts/import_labrum_data.py

Merges Acc + Gyr CSV files for each subject/arm and imports them.
Tailored for the exact file naming: Subject05_Acc_Left.csv + Subject05_Gyr_Left.csv etc.

Gyro data is in deg/s — converted to rad/s on import.

Injured arm mapping:
  Subject 05 (Manny)      → Right
  Subject 10 (Lukas)      → Right
  Subject 12 (Apo)        → Left
  Subject 15 (Alicia)     → Right
  Subject 22 (Laia)       → Left
  Subject 29 (Malta Jawn) → Right
  Subject 13 (Diana)      → Right
"""
import os, math, csv, io, requests

DATA_DIR  = "/Users/ellamcritchie/CSV-Files-LabrumTears/Swimming Labral Tear Subjects/Labrum Tears"
BASE_URL  = "http://localhost:8000"

# Injured arm for each subject number
INJURED = {
    "05": "right",
    "10": "right",
    "12": "left",
    "15": "right",
    "22": "left",
    "29": "right",
    "13": "right",
}

DEG_TO_RAD = math.pi / 180.0


def find_files():
    """Group files by subject number and arm side."""
    groups = {}  # key: (subject_num, arm) → {"acc": path, "gyr": path}
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith(".csv"):
            continue
        lower = fname.lower()
        # Extract subject number
        if "subject" not in lower:
            continue
        parts = fname.replace(".csv", "").split("_")
        # parts like ['Subject05', 'Acc', 'Left']
        subj_num = parts[0].replace("Subject", "").replace("subject", "")
        file_type = parts[1].lower()  # 'acc' or 'gyr'
        arm = parts[2].lower()        # 'left' or 'right'
        key = (subj_num, arm)
        if key not in groups:
            groups[key] = {}
        groups[key][file_type] = os.path.join(DATA_DIR, fname)
    return groups


def read_csv_rows(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def merge_acc_gyr(acc_path, gyr_path):
    """
    Merge accelerometer and gyroscope rows by epoch_ms.
    Returns list of dicts with all 6 axes.
    Gyro converted from deg/s to rad/s.
    """
    acc_rows, _ = read_csv_rows(acc_path)
    gyr_rows, _ = read_csv_rows(gyr_path)

    # Index gyro by epoch
    gyr_by_epoch = {}
    for row in gyr_rows:
        epoch = row.get("epoc (ms)") or row.get("epoch (ms)") or list(row.values())[0]
        gyr_by_epoch[epoch.strip()] = row

    merged = []
    for row in acc_rows:
        epoch = row.get("epoc (ms)") or row.get("epoch (ms)") or list(row.values())[0]
        epoch = epoch.strip()
        elapsed = float(row.get("elapsed (s)", 0))

        ax = float(row.get("x-axis (g)", 0))
        ay = float(row.get("y-axis (g)", 0))
        az = float(row.get("z-axis (g)", 0))

        gyr = gyr_by_epoch.get(epoch, {})
        gx_deg = float(gyr.get("x-axis (deg/s)", 0))
        gy_deg = float(gyr.get("y-axis (deg/s)", 0))
        gz_deg = float(gyr.get("z-axis (deg/s)", 0))

        merged.append({
            "epoch_ms":  float(epoch),
            "elapsed_s": elapsed,
            "accel_x":   ax,
            "accel_y":   ay,
            "accel_z":   az,
            "gyro_x":    gx_deg * DEG_TO_RAD,
            "gyro_y":    gy_deg * DEG_TO_RAD,
            "gyro_z":    gz_deg * DEG_TO_RAD,
        })
    return merged


def get_or_create_subject(subj_num, injured_arm):
    code = f"Subject{subj_num}"
    # Try to create
    r = requests.post(f"{BASE_URL}/subjects", json={
        "code": code,
        "injured_arm": injured_arm,
    })
    if r.status_code == 200:
        return r.json()["id"]
    # Already exists — find it
    subjects = requests.get(f"{BASE_URL}/subjects").json()
    match = next((s for s in subjects if s["code"] == code), None)
    if match:
        return match["id"]
    raise Exception(f"Could not create or find subject {code}")


def main():
    groups = find_files()
    if not groups:
        print(f"No matching files found in:\n  {DATA_DIR}")
        print("Check the path is correct.")
        return

    print(f"Found {len(groups)} subject/arm combinations:\n")
    for (subj, arm) in sorted(groups.keys()):
        files = groups[(subj, arm)]
        print(f"  Subject{subj} {arm}: acc={'✓' if 'acc' in files else '✗'} gyr={'✓' if 'gyr' in files else '✗'}")

    print()

    for (subj_num, arm) in sorted(groups.keys()):
        files = groups[(subj_num, arm)]
        if "acc" not in files or "gyr" not in files:
            print(f"⚠ Subject{subj_num} {arm}: missing acc or gyr file, skipping")
            continue

        injured_arm = INJURED.get(subj_num, "right")
        print(f"Processing Subject{subj_num} {arm} arm (injured={injured_arm})…")

        # Get or create subject
        subject_id = get_or_create_subject(subj_num, injured_arm)
        print(f"  Subject ID: {subject_id}")

        # Merge acc + gyr
        samples = merge_acc_gyr(files["acc"], files["gyr"])
        print(f"  Merged {len(samples)} samples")

        # Start session
        r = requests.post(f"{BASE_URL}/sessions/start", json={
            "subject_id": subject_id,
            "arm_side":   arm,
        })
        r.raise_for_status()
        session_id = r.json()["id"]
        session_num = r.json()["session_number"]
        print(f"  Session #{session_num} started (id={session_id})")

        # Upload in batches of 500
        batch_size = 500
        for i in range(0, len(samples), batch_size):
            batch = samples[i:i+batch_size]
            r = requests.post(f"{BASE_URL}/imu/{session_id}/batch", json=batch)
            r.raise_for_status()

        print(f"  Uploaded {len(samples)} samples")

        # End session
        r = requests.post(f"{BASE_URL}/sessions/{session_id}/end", json={})
        r.raise_for_status()
        print(f"  ✓ Done — load computed\n")

    print("All subjects imported! Open http://localhost:5173 to see the data.")


if __name__ == "__main__":
    main()
