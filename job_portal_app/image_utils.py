
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import UploadedFile

def compress_image(uploaded_image, max_size=(500, 500), quality=85, output_format='JPEG'):
    """
    Compresses and resizes an uploaded image while maintaining aspect ratio

    Args:
        uploaded_image: Django UploadedFile object
        max_size: Tuple (width, height) for maximum dimensions
        quality: Compression quality (1-100)
        output_format: Output format ('JPEG', 'PNG', etc.)

    Returns:
        UploadedFile: Compressed image as UploadedFile

    Raises:
        ValueError: If image processing fails
    """
    try:
        # Open the image
        img = Image.open(uploaded_image)

        # Convert to RGB if needed (for JPEG)
        if output_format == 'JPEG' and img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Resize maintaining aspect ratio
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Compress to BytesIO buffer
        output = BytesIO()
        img.save(output, format=output_format, quality=quality, optimize=True)
        output.seek(0)

        # Create new UploadedFile with compressed image
        file_name = uploaded_image.name.split('.')[0] + f'.{output_format.lower()}'
        compressed_file = UploadedFile(
            file=output,
            name=file_name,
            content_type=f'image/{output_format.lower()}',
            size=len(output.getvalue())
        )

        return compressed_file

    except Exception as e:
        raise ValueError(f"Image processing failed: {str(e)}")