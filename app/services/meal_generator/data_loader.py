import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / 'data'

def load_normalized_dataset(dataset_name: str):
    file_map = {
        'Breakfast': 'Breakfast.xlsx',
        'Morning_Snacks': 'Morning_Snack (1).xlsx',
        'Lunch': 'Lunch.xlsx',
        'Dinner': 'Dinner.xlsx',
    }
    file_path = DATA_DIR / file_map[dataset_name]
    
    if file_path.suffix == '.csv':
        return pd.read_csv(file_path, encoding='ISO-8859-1')
    elif file_path.suffix == '.xlsx':
        return pd.read_excel(file_path)
    raise ValueError("Unsupported file format")