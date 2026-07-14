import os

base = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base, 'admin', 'routes.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remplacer l'import défectueux
content = content.replace(
    "from flask import (Blueprint, abort, flash, jsonify, redirect, render_template,\n                   request, session, url_for)",
    "from flask import (abort, flash, jsonify, redirect, render_template,\n                   request, session, url_for)"
)

content = content.replace(
    'from admin.models import AdminLog, AdminUser, PlatformNotification, SystemConfig, UserNotification',
    'from admin import admin_bp\nfrom admin.models import AdminLog, AdminUser, PlatformNotification, SystemConfig, UserNotification'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('OK - routes.py fixed')