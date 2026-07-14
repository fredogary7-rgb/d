"""Admin Blueprint – Back Office TransAfrik"""

from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', static_folder='static',
                     template_folder='templates')

from . import routes  # noqa: E402, F401