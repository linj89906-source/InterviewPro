import sys
p = r'C:\Users\30785\interview-system\backend\app\services\map_service.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# Fix 1: apply name_bad exclusion
old1 = 'if code_ok:  # temporarily relaxed filter for debugging'
new1 = 'if code_ok and not name_bad:'
c = c.replace(old1, new1)

# Fix 2: fix _get_cost_hint call with extra arg
old2 = '_get_cost_hint(\n                    p.get("typecode", ""), "unknown"\n                )'
new2 = '_get_cost_hint(p.get("typecode", ""))'
c = c.replace(old2, new2)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('Fixes applied')
