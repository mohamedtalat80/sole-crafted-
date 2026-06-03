import os
import uuid
from functools import partial


def upload_to_uuid(instance, filename, folder_name):
    """
    Generate a UUID-based upload path.

    Uses instance.pk as the folder when the record already exists; falls back
    to a fresh UUID for unsaved instances so the path never contains 'None'.
    The filename itself is also replaced with a UUID to prevent collisions.

    Intended to be used via functools.partial:
        upload_to=partial(upload_to_uuid, folder_name="my_app/images")
    """
    ext = filename.split(".")[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    folder = instance.pk or uuid.uuid4()
    return os.path.join(folder_name, str(folder), new_filename)
