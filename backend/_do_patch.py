import re

path = r"C:\Users\30785\interview-system\backend\app\services\map_service.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

print("Original ACCOMMODATION_TYPES:")
idx = content.find("ACCOMMODATION_TYPES")
if idx > 0:
    print(content[idx:idx+400])
else:
    print("NOT FOUND")