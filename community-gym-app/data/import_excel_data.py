import pandas as pd

excel_path = "Data.xlsx"
logs_path = "logs.csv"

USER_ID = 1
GOAL = "Cut"

sheets_to_import = ["Macros", "Post Mexico Cut"]

all_rows = []

for sheet_name in sheets_to_import:
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=2)

    df = df.rename(columns={
        "Column 1": "date",
        "Weight": "weight",
        "Calories": "calories",
        "Protein (g)": "protein"
    })

    df = df[["date", "weight", "calories", "protein"]]

    df = df.dropna(subset=["date"])

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df["calories"] = pd.to_numeric(df["calories"], errors="coerce")
    df["protein"] = pd.to_numeric(df["protein"], errors="coerce")

    df = df.dropna(subset=["date", "calories", "protein"])

    df["user_id"] = USER_ID
    df["goal"] = GOAL

    df = df[["user_id", "date", "goal", "weight", "calories", "protein"]]

    all_rows.append(df)

combined = pd.concat(all_rows, ignore_index=True)

combined = combined.sort_values("date")

combined = combined.drop_duplicates(subset=["user_id", "date"], keep="last")

combined.to_csv(logs_path, index=False)

print(f"Imported {len(combined)} rows into {logs_path}")