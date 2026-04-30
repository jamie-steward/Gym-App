import pandas as pd

logs_path = "logs.csv"

logs = pd.read_csv(logs_path)

logs["date"] = pd.to_datetime(logs["date"])

# Change this date if needed
mexico_return_date = pd.to_datetime("2026-03-01")

# Everything before Mexico return = Recomp
logs.loc[logs["date"] < mexico_return_date, "goal"] = "Recomp"

# Everything from Mexico return onwards = Cut
logs.loc[logs["date"] >= mexico_return_date, "goal"] = "Cut"

logs["date"] = logs["date"].dt.date

logs.to_csv(logs_path, index=False)

print("Historical goals updated ✅")
print(logs["goal"].value_counts())