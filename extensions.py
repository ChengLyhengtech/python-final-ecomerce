from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["500 per day", "250 per hour","20 per minute"],
    storage_uri="memory://"
)

csrf = CSRFProtect()
cors = CORS(resources={r"/*": {"origins": "http://127.0.0.1:5000"}})
