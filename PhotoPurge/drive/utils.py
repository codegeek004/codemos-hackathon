import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials

# Mime
FOLDER_MIME = "application/vnd.google-apps.folder"

EXPORT_MAP = {
    "application/vnd.google-apps.document":
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "application/vnd.oasis.opendocument.text"
    "application/vnd.google-apps.spreadsheet":
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    "application/vnd.google-apps.presentation":
        ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
    "application/vnd.google-apps.drawing":
        ("application/pdf", ".pdf"),
    "application/vnd.google-apps.script":
        ("application/vnd.google-apps.script+json", ".json"),
    # Forms and Sites have no supported binary export — skip them downstream
    "application/vnd.google-apps.form": None,
    "application/vnd.google-apps.site": None,
}


SKIP_MIME_PREFIXES = ("application/vnd.google-apps.",)


def get_drive_service(credentials_dict: dict):
    creds = Credentials(
        token=credentials_dict["token"],
        refresh_token=credentials_dict.get("refresh_token"),
        token_uri=credentials_dict.get(
            "token_uri", "https://oauth2.googleapis.com/token"),
        client_id=credentials_dict["client_id"],
        client_secret=credentials_dict["client_secret"],
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return service


def get_drive_files(
        credentials_dict: dict,
        page_token: str = None,
        page_size: int = 100
):
    service = get_drive_service(credentials_dict)
    params = {
        "pageSize": min(page_size, 1000),          # API hard cap is 1000
        "fields": "nextPageToken, files(id, name, mimeType, parents, size)",
        "q": "trashed = false",
        # folders first — critical for hierarchy map
        "orderBy": "folder,name",
    }

    if page_token:
        params["pageToken"] = page_token

    result = service.files().list(**params).execute()
    files = result.get("files", [])
    next_token = result.get("nextPageToken")
    return files, next_token


def download_drive_file(
        service,
        file_id: str,
        mime_type: str
):
    if mime_type in EXPORT_MAP:
        export_target = EXPORT_MAP[mime_type]
        if export_target is None:
            # Forms / Sites / Maps — no binary export available
            raise ValueError(f"No export available for mime type: {mime_type}")
        export_mime, extension = export_target
        # Correct API call: files().export_media() → GET /files/{id}/export?mimeType=...
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)

    elif mime_type.startswith("application/vnd.google-apps."):
        # Catch-all for any other vnd.google-apps.* not in our map
        raise ValueError(
            f"Unsupported Google Workspace mime type: {mime_type}")

    else:
        # Binary file — correct API call: files().get_media() → GET /files/{id}?alt=media
        extension = None
        request = service.files().get_media(fileId=file_id)

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(
        buffer,
        request,
        chunksize=10 * 1024 * 1024)

    done = False

   while not done:
        var, done = downloader.next_chunk()

    return buffer.getvalue(), extension


def upload_drive_file(
    service,
    file_bytes: bytes,
    file_name: str,
    mime_type: str,
    parent_folder_id: str = None,
):
    metadata = {"name": file_name}
    if parent_folder_id:
        metadata["parents"] = [parent_folder_id]
 
    # Workspace types were exported to Office format — use the Office MIME for upload.
    # Binary files keep their original MIME.
    if mime_type in EXPORT_MAP and EXPORT_MAP[mime_type] is not None:
        upload_mime = EXPORT_MAP[mime_type][0]   # e.g. "application/vnd.openxmlformats-..."
    else:
        upload_mime = mime_type
 
    media = MediaIoBaseUpload(
        io.BytesIO(file_bytes),
        mimetype=upload_mime,
        resumable=True,
        chunksize=10 * 1024 * 1024,   # 10 MB chunks that matches download chunk size
    )
    uploaded = (
        service.files().create(
            body=metadata, 
            media_body=media, 
            fields="id"
        ).execute()
    )
    return uploaded.get("id")    


def create_drive_folder(service, folder_name: str, parent_folder_id: str = None):
    metadata = {
        "name": folder_name,
        "mimeType": FOLDER_MIME,
    }
    if parent_folder_id:
        metadata["parents"] = [parent_folder_id]
 
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder.get("id")


def trash_drive_file(service, file_id: str):
    service.files().update(
            fileId=file_id, 
            body={"trashed": True}
    ).execute()
print()
