import io

import qrcode


def generate_animal_qr(
    animal_id: str,
    farm_id: str,
    tag_id: str
) -> bytes:
    """
    Generate a QR code containing the VETRA animal identifier.
    """

    qr_data = (
        f"VETRA|animal_id={animal_id}"
        f"|farm_id={farm_id}"
        f"|tag_id={tag_id}"
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )

    qr.add_data(qr_data)
    qr.make(fit=True)

    image = qr.make_image()

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG"
    )

    buffer.seek(0)

    return buffer.getvalue()