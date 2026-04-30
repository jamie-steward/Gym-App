import pandas as pd
from supabase import create_client

SUPABASE_URL = "https://imemgpywwrsrplbjbhye.supabase.co"
SUPABASE_KEY = "sb_publishable_HcrWGK_iozD8vWBXKYzziQ_UC2B55dp"

NEW_USER_ID = "677bad59-2bf7-49a2-831c-5b6279b34a95"

csv_path = "logs.csv"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logs = pd.read_csv(csv_path)

# Clean dates
logs["date"] = pd.to_datetime(logs["date"], errors="coerce").dt.date

# Replace old local user_id with your Supabase UUID
logs["user_id"] = NEW_USER_ID

# Make sure numbers are clean
logs["weight"] = pd.to_numeric(logs["weight"], errors="coerce")
logs["calories"] = pd.to_numeric(logs["calories"], errors="coerce").fillna(0).astype(int)
logs["protein"] = pd.to_numeric(logs["protein"], errors="coerce").fillna(0).astype(int)

# Keep only needed columns
logs = logs[["user_id", "date", "goal", "weight", "calories", "protein"]]

# Drop rows without a date
logs = logs.dropna(subset=["date"])

# Convert date to string for Supabase
logs["date"] = logs["date"].astype(str)

# Remove duplicate dates
logs = logs.drop_duplicates(subset=["user_id", "date"], keep="last")

logs = logs.where(pd.notnull(logs), None)

records = logs.to_dict(orient="records")

# Force any leftover NaN values to become None
for record in records:
    for key, value in record.items():
        if pd.isna(value):
            record[key] = None

print(f"Importing {len(records)} rows...")

for record in records:
    supabase.table("logs").insert(record).execute()

print("Import complete ✅")