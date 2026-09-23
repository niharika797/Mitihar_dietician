"""Wrapper: runs the security test and writes plain-text output to a file."""
import subprocess, sys, os

os.chdir(r"C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician")
result = subprocess.run(
    [sys.executable, "tests/security_verification_test.py"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
# Strip ANSI colour codes so the file is readable
import re
ansi = re.compile(r'\x1b\[[0-9;]*m')
out = ansi.sub("", result.stdout + result.stderr)
with open("test_results_security.txt", "w", encoding="utf-8") as f:
    f.write(out)
print("Done. Exit code:", result.returncode)
