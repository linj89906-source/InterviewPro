p = r'C:\Users\30785\interview-system\backend\app\agents\location_agent.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()
old = '_get_cost_hint.get(\n                                p.get("typecode", ""), "unknown"\n                            )'
new = '_get_cost_hint(p.get("typecode", ""))'
c = c.replace(old, new)
with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('location_agent.py fixed')
