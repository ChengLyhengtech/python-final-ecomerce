import os
from werkzeug.utils import secure_filename

# Upload Configuration Settings
DEFAULT_UPLOAD_FOLDER = 'static/admin/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max limit


def init_upload_config(app, subfolder=DEFAULT_UPLOAD_FOLDER):
    """
    Initialize upload configurations on the Flask app instance.
    """
    upload_path = os.path.join(app.root_path, subfolder)
    os.makedirs(upload_path, exist_ok=True)
    
    app.config['UPLOAD_FOLDER'] = upload_path
    app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    return upload_path


def allowed_file(filename):
    """
    Check if the file extension is allowed.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage, upload_folder=None, default_filename=None):
    if not file_storage or not file_storage.filename or not file_storage.filename.strip():
        return default_filename

    # Validate file extension
    if not allowed_file(file_storage.filename):
        raise ValueError("File extension not allowed.")

    filename = secure_filename(file_storage.filename)
    if not filename:
        return default_filename

    if upload_folder is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        upload_folder = os.path.join(base_dir, DEFAULT_UPLOAD_FOLDER)

    os.makedirs(upload_folder, exist_ok=True)
    save_path = os.path.join(upload_folder, filename)
    file_storage.save(save_path)

    return filename
