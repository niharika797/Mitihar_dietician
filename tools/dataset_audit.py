import pandas as pd
import json
import os
import glob

# Ensure openpyxl is installed for reading xlsx (should be based on requirements.txt)

files = [
    r"app\services\datasets for eyantra\datasets for eyantra\datasets for eyantra\Updated_breakfast - Sheet1 (1).csv",
    r"app\services\datasets for eyantra\datasets for eyantra\datasets for eyantra\breakfast_final.csv",
    r"app\services\datasets for eyantra\datasets for eyantra\datasets for eyantra\dinner_veg (1).xlsx",
    r"app\services\datasets for eyantra\datasets for eyantra\datasets for eyantra\dinner_veg+nonveg(abc).xlsx",
    r"app\services\datasets for eyantra\datasets for eyantra\datasets for eyantra\fruits_final.csv",
    r"app\services\datasets for eyantra\datasets for eyantra\datasets for eyantra\lunch_veg(asd).xlsx",
    r"app\services\datasets for eyantra\datasets for eyantra\datasets for eyantra\lunch_veg+nonveg(dinner (1)).xlsx",
    r"app\services\meal_generator\data\Breakfast.xlsx",
    r"app\services\meal_generator\data\Breakfast_new.xlsx",
    r"app\services\meal_generator\data\Dinner.xlsx",
    r"app\services\meal_generator\data\Dinner_new.xlsx",
    r"app\services\meal_generator\data\Lunch.xlsx",
    r"app\services\meal_generator\data\Lunch_new.xlsx",
    r"app\services\meal_generator\data\Morning_Snack (1).xlsx"
]

report = ""

for file in files:
    full_path = os.path.abspath(file)
    if not os.path.exists(full_path):
        report += f"### {file}\nFile missing!\n\n"
        continue
    
    try:
        if file.endswith('.csv'):
            df = pd.read_csv(full_path)
        else:
            df = pd.read_excel(full_path)
        
        report += f"### {file}\n"
        report += f"**Total Rows:** {len(df)}\n\n"
        
        # Columns info
        cols_info = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            null_count = df[col].isnull().sum()
            sample_vals = df[col].dropna().head(2).tolist()
            # Clean string repr of sample
            sample_str = str(sample_vals)
            if len(sample_str) > 100:
                sample_str = sample_str[:100] + "..."
            
            null_status = f"Yes ({null_count} nulls)" if null_count > 0 else "No"
            cols_info.append(f"| `{col}` | {dtype} | {null_status} | {sample_str} |")
            
        report += "| Column Name | Data Type | Has Nulls? | Sample (2 rows) |\n"
        report += "|---|---|---|---|\n"
        report += "\n".join(cols_info) + "\n\n"
        
    except Exception as e:
        report += f"### {file}\nError reading file: {str(e)}\n\n"

with open("dataset_audit_temp.md", "w", encoding="utf-8") as f:
    f.write(report)
print("done")
