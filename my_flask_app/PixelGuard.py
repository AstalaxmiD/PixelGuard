from flask import Flask, request, send_file, render_template, Response
from PIL import Image, PngImagePlugin
import numpy as np
import io
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB upload limit

# --- 1. LSB noise layer ---
def apply_steganography_noise(image_data, intensity=3):
    print("Applying steganography noise layer...")
    img = image_data.convert('RGB')
    data = np.array(img, dtype=np.int16)

    noise = np.random.randint(-intensity, intensity + 1, size=data.shape)
    data = np.clip(data + noise, 0, 255).astype(np.uint8)

    return Image.fromarray(data, 'RGB')

# --- 2. Adversarial-like noise layer ---
def apply_adversarial_noise(image_data, epsilon=5):
    print("Applying adversarial noise layer...")
    img = image_data.convert('RGB')
    data = np.array(img, dtype=np.int16)

    noise = np.random.randint(-epsilon, epsilon + 1, size=data.shape)
    data = np.clip(data + noise, 0, 255).astype(np.uint8)

    return Image.fromarray(data, 'RGB')

# --- 3. Metadata injection ---
def inject_metadata(image_data, warning_message="DO NOT USE FOR AI TRAINING"):
    img_format = (image_data.format or 'PNG').upper()
    try:
        img_io = io.BytesIO()

        if img_format in ['JPEG', 'JPG']:
            exif_dict = image_data.getexif() or {}
            exif_dict[0x9286] = warning_message  # UserComment
            image_data.save(img_io, format='JPEG', exif=exif_dict)
        else:
            info = PngImagePlugin.PngInfo()
            info.add_text("Warning", warning_message)
            image_data.save(img_io, format='PNG', pnginfo=info)

        img_io.seek(0)
        return Image.open(img_io)

    except Exception as e:
        print("Metadata injection error:", e)
        raise

# --- Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/protect-layered', methods=['POST'])
def protect_image_layered():
    if 'image' not in request.files:
        return Response("No file part in the request", status=400)

    file = request.files['image']
    if file.filename == '':
        return Response("No file selected", status=400)

    try:
        img = Image.open(io.BytesIO(file.read()))

        # Apply each layer multiple times
        for _ in range(10):
            img = apply_steganography_noise(img, intensity=15)
            img = apply_adversarial_noise(img, epsilon=12)

        # Inject metadata once at the end
        img = inject_metadata(img)

        # Return protected image
        img_io = io.BytesIO()
        out_format = img.format or 'PNG'
        img.save(img_io, format=out_format)
        img_io.seek(0)

        return send_file(
            img_io,
            mimetype=f'image/{out_format.lower()}',
            as_attachment=True,
            download_name=f'protected_{file.filename}'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()  # logs to Render
        return Response(f"Error processing image: {str(e)}", status=500)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
