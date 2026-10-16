"""Keep uploaded image bytes out of message-list JSON responses."""
import base64
import binascii
from fastapi import HTTPException
from app import models


def attach_user_image(message, image_url, db):
    if not image_url or not image_url.startswith("data:"):
        return
    try:
        header, encoded = image_url.split(",", 1)
        raw = base64.b64decode(encoded, validate=True)
        mime = header.split(";", 1)[0][5:]
        valid = ((mime == "image/png" and raw.startswith(b"\x89PNG\r\n\x1a\n"))
                 or (mime == "image/jpeg" and raw.startswith(b"\xff\xd8\xff"))
                 or (mime == "image/webp" and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"))
        if not valid or len(raw) > 2621440:
            raise ValueError()
    except (ValueError, binascii.Error):
        raise HTTPException(400, "Attach a valid PNG, JPEG or WebP image under 2.5 MB") from None
    image = models.GeneratedImage(data=encoded, mime_type=mime)
    message.generated_image = image
    db.flush()
    message.image_url = f"/images/{image.id}"
