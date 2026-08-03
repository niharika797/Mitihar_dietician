import sys
sys.path.insert(0, 'C:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician')
import inspect
from app.core.security import get_current_patient
src = inspect.getsource(get_current_patient)
print(src)
print("---")
print("'subscription' in src:", 'subscription' in src.lower())
for i, line in enumerate(src.split('\n'), 1):
    if 'subscri' in line.lower():
        print(f"  Line {i}: {line}")
