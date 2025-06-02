from flask import Flask, request, render_template, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
import io
import os
from collections import Counter
import random
import colorsys
import uuid
import base64
import logging
from logging.handlers import RotatingFileHandler
import sys

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Helper functions from original app ---
def get_dominant_color(image):
    image = image.resize((50, 50))
    pixels = list(image.getdata())
    pixels = [pixel[:3] for pixel in pixels if len(pixel) > 3 and pixel[3] > 0]
    most_common = Counter(pixels).most_common(1)
    return most_common[0][0] if most_common else (255, 255, 255)

def rgb_to_hsv(rgb):
    r, g, b = [x/255.0 for x in rgb]
    return colorsys.rgb_to_hsv(r, g, b)

def hsv_to_rgb(hsv):
    r, g, b = colorsys.hsv_to_rgb(*hsv)
    return (int(r*255), int(g*255), int(b*255))

def brightness(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]

def generate_contrasting_color(bg_rgb):
    h, s, v = rgb_to_hsv(bg_rgb)
    new_h = (h + 0.5 + random.uniform(-0.1, 0.1)) % 1.0
    new_s = 1.0
    bg_bright = brightness(bg_rgb)
    new_v = 0.95 if bg_bright < 128 else 0.2 + random.uniform(0.1, 0.2)
    new_rgb = hsv_to_rgb((new_h, new_s, new_v))
    
    def contrast(c1, c2):
        l1 = (0.2126 * c1[0] + 0.7152 * c1[1] + 0.0722 * c1[2]) / 255
        l2 = (0.2126 * c2[0] + 0.7152 * c2[1] + 0.0722 * c2[2]) / 255
        l1, l2 = max(l1, l2), min(l1, l2)
        return (l1 + 0.05) / (l2 + 0.05)
    
    if contrast(new_rgb, bg_rgb) < 3:
        return (255,255,255) if bg_bright < 128 else (0,0,0)
    return new_rgb

def draw_text_with_style(draw, position, text, font, text_color):
    x, y = position
    shadow_color = "black" if text_color == "white" else "gray"
    shadow_offset = 2
    
    # Draw shadow
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
    
    # Draw outline
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx != 0 or dy != 0:
                outline_color = "black" if text_color == "white" else "white"
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    
    # Draw main text
    draw.text((x, y), text, font=font, fill=text_color)

def process_image(image_data, text, is_double_line=True):
    # Convert bytes to image
    original = Image.open(io.BytesIO(image_data)).convert("RGBA")
    img_w, img_h = original.size
    
    # Remove background
    output_bytes = remove(
        image_data,
        alpha_matting=True,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10
    )
    
    # Convert to RGBA and clean up edges
    fg = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
    fg = fg.resize(original.size, Image.Resampling.LANCZOS)
    
    # Clean up semi-transparent pixels
    data = fg.getdata()
    newData = []
    for item in data:
        if item[3] < 128:
            newData.append((0, 0, 0, 0))
        else:
            newData.append(item)
    
    fg.putdata(newData)
    
    # Text processing
    is_landscape = img_w >= img_h
    if is_landscape and not is_double_line:
        message_lines = [text]
    else:
        if " " in text:
            parts = text.split(" ", 1)
            message_lines = [parts[0], parts[1]]
        else:
            message_lines = [text]

    dominant_color = get_dominant_color(original)
    rand_rgb = generate_contrasting_color(dominant_color)
    text_color = '#%02x%02x%02x' % rand_rgb

    # Calculate font size
    max_font_size = int(img_h * 0.3 / len(message_lines))
    font_size = max_font_size
    font_path = "arial.ttf"  # System font

    try:
        font = ImageFont.truetype(font_path, font_size)
    except OSError:
        font = ImageFont.load_default()

    # Create text layer
    text_layer = Image.new("RGBA", original.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    # Calculate text positioning
    y_offset_percent = random.uniform(0.05, 0.20)
    start_y = int(img_h * y_offset_percent)

    # Draw text
    for i, line in enumerate(message_lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = max((img_w - text_w) // 2, 0)
        y = start_y + i * (font_size + 10)
        
        if y + (bbox[3] - bbox[1]) >= img_h:
            break
            
        draw_text_with_style(draw, (x, y), line, font, text_color)

    # Compose final image
    composite = Image.alpha_composite(text_layer, fg)
    final = Image.alpha_composite(original.convert("RGBA"), composite)
    
    # Save to buffer
    buffer = io.BytesIO()
    final.save(buffer, format="PNG")
    buffer.seek(0)
    
    return buffer

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    # Read image data
    image_data = file.read()
    
    # Get text from form
    text = request.form.get('text', 'Happy Birthday')
    is_double_line = request.form.get('double_line', 'true').lower() == 'true'
    
    try:
        # Process image
        result_buffer = process_image(image_data, text, is_double_line)
        
        # Convert to base64 for preview
        base64_image = base64.b64encode(result_buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'image': f'data:image/png;base64,{base64_image}'
        })
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return jsonify({'error': 'Error processing image'}), 500

@app.route('/download', methods=['POST'])
def download():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    text = request.form.get('text', 'Happy Birthday')
    is_double_line = request.form.get('double_line', 'true').lower() == 'true'
    
    # Process image
    result_buffer = process_image(file.read(), text, is_double_line)
    
    # Send file for download
    return send_file(
        result_buffer,
        mimetype='image/png',
        as_attachment=True,
        download_name='birthday_image.png'
    )

# Setup error handling
@app.errorhandler(500)
def handle_500_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error occurred'}), 500

@app.errorhandler(404)
def handle_404_error(e):
    return jsonify({'error': 'Resource not found'}), 404

# Add startup logging
logger.info("Application starting...")
logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
