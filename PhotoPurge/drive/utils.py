import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials

# Mime
FOLDER_MIME = "application/vnd.google-apps.folder"

EXPORT_MAP = {
    "application/vnd.google-apps.document":
        [
            ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
            ("application/vnd.oasis.opendocument.text", ".odt"),
            ("application/rtf", ".rtf"),
            ("application/pdf", ".pdf"),
            ("text/plain", ".txt"),
            ("application/zip", ".zip"),
            ("application/epub+zip", ".epub"),
            ("text/markdown", ".md")
        ],
    "application/vnd.google-apps.presentation":
        [
            ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
            ("application/vnd.oasis.opendocument.presentation", ".odp"),
            ("application/pdf", ".pdf"),
            ("text/plain", ".txt"),
            ("image/jpeg", ".jpg"),
            ("image/png", ".png"),
            ("image/svg+xml", ".svg")
        ],
    "application/vnd.google-apps.spreadsheet":
        [
            ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
            ("application/vnd.oasis.opendocument.spreadsheet", ".ods"),
            ("application/pdf", ".pdf"),
            ("application/zip", ".zip"),
            ("text/csv", ".csv"),
            ("text/tab-separated-values", ".tsv")
        ],
    "application/vnd.google-apps.drawing":
        [
            ("application/pdf", ".pdf"),
            ("image/jpeg", ".jpg"),
            ("image/png", ".png"),
            ("image/svg+xml", ".svg")
        ],

    "application/vnd.google-apps.script":
        ("application/vnd.google-apps.script+json", ".json"),
    # Forms and Sites have no supported binary export — skip them downstream
    "application/vnd.google-apps.form": None,
    "application/vnd.google-apps.site": None,
}


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


def download_all_formats(src_service, file_id: str, file_name: str, mime_type: str):

    if mime_type not in EXPORT_MAP:
        request = src_service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(
            buffer,
            request,
            chunksize=10 * 1024 * 1024)
        done = False
        while not done:
            var, done = downloader.next_chunk()
        return [(buffer.getvalue(), file_name, mime_type)]

    results = []
    for export_mime, extension in EXPORT_MAP[mime_type]:
        try:
            request = src_service.files().export_media(
                fileId=file_id, mimeType=export_mime)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(
                buffer, request, chunksize=10 * 1024 * 1024)
            done = False
            while not done:
                var, done = downloader.next_chunk()

            file_bytes = buffer.getvalue()
            if file_bytes:
                results.append(
                    (file_bytes, f"{file_name}{extension}", export_mime))

        except Exception as e:
            logger.warning(f"Could not export {file_name} as {extension}: {e}")
            continue

    return results


def upload_all_formats(dst_service, downloads: list, parent_folder_id: str = None):

    uploaded = 0
    for file_bytes, upload_name, upload_mime in downloads:
        try:
            upload_drive_file(
                dst_service,
                file_bytes=file_bytes,
                file_name=upload_name,
                mime_type=upload_mime,
                parent_folder_id=parent_folder_id,
            )
            uploaded += 1
        except Exception as e:
            logger.warning(f"Could not upload {upload_name}: {e}")
            continue

    return uploaded


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
