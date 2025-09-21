from flask import Flask, request, send_file, render_template
from PIL import Image, PngImagePlugin
import numpy as np
import io

app = Flask(__name__)

# --- 1. LSB noise layer ---
def apply_steganography_noise(image_data, intensity=3):
    """
    Slightly tweak LSBs to confuse AI models.
    intensity: how much to change each pixel (1-5 is usually safe)
    """
    print("Applying steganography noise layer...")
    img = image_data.convert('RGB')
    data = np.array(img, dtype=np.int16)

    noise = np.random.randint(-intensity, intensity+1, size=data.shape)
    data = np.clip(data + noise, 0, 255).astype(np.uint8)

    return Image.fromarray(data, 'RGB')

# --- 2. Adversarial-like noise layer ---
def apply_adversarial_noise(image_data, epsilon=5):
    """
    Apply slightly stronger random noise to mimic adversarial effect.
    epsilon: max pixel change
    """
    print("Applying adversarial noise layer...")
    img = image_data.convert('RGB')
    data = np.array(img, dtype=np.int16)

    noise = np.random.randint(-epsilon, epsilon+1, size=data.shape)
    data = np.clip(data + noise, 0, 255).astype(np.uint8)

    return Image.fromarray(data, 'RGB')

# --- 3. Metadata injection ---
def inject_metadata(image_data, warning_message="DO NOT USE FOR AI TRAINING"):
    img_format = image_data.format or 'PNG'
    try:
        img_io = io.BytesIO()

        if img_format.upper() in ['JPEG', 'JPG']:
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
        return {'error': 'No file part in the request'}, 400

    file = request.files['image']
    if file.filename == '':
        return {'error': 'No file selected'}, 400

    try:
        img = Image.open(io.BytesIO(file.read()))

        # Apply each layer 5 times
        for _ in range(10):
            img = apply_steganography_noise(img, intensity=15)
            img = apply_adversarial_noise(img, epsilon=12)
        
        # Inject metadata once at the end
        img = inject_metadata(img)

        # Return protected image
        img_io = io.BytesIO()
        img.save(img_io, format=img.format or 'PNG')
        img_io.seek(0)

        return send_file(
            img_io,
            mimetype=f'image/{img.format.lower() if img.format else "png"}',
            as_attachment=True,
            download_name=f'protected_{file.filename}'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'error': str(e)}, 500



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)

