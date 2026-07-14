path = r'C:\Users\30785\interview-system\backend\app\services\map_service.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix 1: code_ok -> code_ok and not name_bad
lines[160] = lines[160].replace('if code_ok:', 'if code_ok and not name_bad:')

# Fix 2: _get_cost_hint call - remove extra arg "unknown"
# lines[197] is the _get_cost_hint( line, lines[198] is the arg line, lines[199] is )
lines[197] = '                p["_cost_hint"] = _get_cost_hint(p.get("typecode", ""))\n'
del lines[199]  # the "unknown" ) line
del lines[198]  # the old arg line

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Both fixes applied.')
