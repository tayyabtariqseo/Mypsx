import sys
import os
from psxdata import quote

try:
    print("Testing psxdata.quote('SYS')...")
    q = quote("SYS")
    print(f"Quote Result: {q}")
except Exception as e:
    print(f"Error: {e}")
