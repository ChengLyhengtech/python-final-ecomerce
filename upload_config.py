import os
import time
import uuid
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


def save_uploaded_file(file_storage, upload_folder=None, default_filename=None, use_unique_name=True):
    """
    Saves a single FileStorage object and returns the saved filename.
    """
    if not file_storage or not hasattr(file_storage, 'filename') or not file_storage.filename or not file_storage.filename.strip():
        return default_filename

    original_filename = file_storage.filename.strip()

    # Validate file extension
    if not allowed_file(original_filename):
        raise ValueError(f"File extension not allowed for '{original_filename}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    # Extract extension
    if '.' in original_filename:
        ext = original_filename.rsplit('.', 1)[1].lower()
    else:
        ext = 'png'

    raw_name = secure_filename(original_filename)
    # If secure_filename stripped everything (e.g. non-ascii / unicode names)
    if not raw_name or raw_name == f".{ext}":
        base_name = f"image_{int(time.time())}"
        raw_name = f"{base_name}.{ext}"
    else:
        base_name = raw_name.rsplit('.', 1)[0] if '.' in raw_name else raw_name

    if use_unique_name:
        filename = f"{int(time.time())}_{uuid.uuid4().hex[:6]}_{base_name}.{ext}"
    else:
        filename = raw_name

    if upload_folder is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        upload_folder = os.path.join(base_dir, DEFAULT_UPLOAD_FOLDER)

    os.makedirs(upload_folder, exist_ok=True)
    save_path = os.path.join(upload_folder, filename)
    file_storage.save(save_path)

    return filename


def save_multiple_uploaded_files(files_list, upload_folder=None):
    """
    Saves a list of FileStorage objects and returns a list of saved filenames.
    """
    saved_filenames = []
    if not files_list:
        return saved_filenames

    for file_storage in files_list:
        if file_storage and file_storage.filename and file_storage.filename.strip():
            filename = save_uploaded_file(file_storage, upload_folder=upload_folder, use_unique_name=True)
            if filename:
                saved_filenames.append(filename)

    return saved_filenames

