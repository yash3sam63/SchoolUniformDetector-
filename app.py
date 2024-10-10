from flask import Flask, request, render_template, jsonify,send_from_directory
from inference_sdk import InferenceHTTPClient
from roboflow import Roboflow
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import io

# Initialize Flask app
app = Flask(__name__)

# Initialize Roboflow Client
CLIENT = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key="FiqvXX3eyrsTEX2mlOoL"
)

# Initialize Roboflow Client for video
rf = Roboflow(api_key="FiqvXX3eyrsTEX2mlOoL")
project = rf.workspace().project("uniform-detector-c4r2i")
model = project.version("1").model

# Set minimum and maximum sizes for resizing
MIN_SIZE = (640, 640)  # Min width, height
MAX_SIZE = (1280, 1280)  # Max width, height

def resize_image(image):
    """Resize image to fit within min and max size constraints."""
    img_width, img_height = image.size
    aspect_ratio = img_width / img_height

    # Resize based on min/max size
    if img_width < MIN_SIZE[0] or img_height < MIN_SIZE[1]:
        if img_width < img_height:
            new_width = MIN_SIZE[0]
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = MIN_SIZE[1]
            new_width = int(new_height * aspect_ratio)
    elif img_width > MAX_SIZE[0] or img_height > MAX_SIZE[1]:
        if img_width > img_height:
            new_width = MAX_SIZE[0]
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = MAX_SIZE[1]
            new_width = int(new_height * aspect_ratio)
    else:
        # No resizing needed
        return image

    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

# Image detection route
@app.route('/detect_image', methods=['POST'])
def detect_image():
    image_file = request.files['image']

    # Open the image from the uploaded file in-memory
    image = Image.open(image_file)
    
    # Resize image if necessary
    resized_image = resize_image(image)

    # Save the resized image to a file for further processing (standardize as JPEG)
    image_path = "static/uploaded_image.jpg"
    resized_image.save(image_path, format='JPEG')

    # Infer on the resized image using the path
    result = CLIENT.infer(image_path, model_id="yash-sam-2.0/2")

    # Draw bounding boxes on the resized image
    draw = ImageDraw.Draw(resized_image)

    # Define the font size
    try:
        font = ImageFont.truetype("arial.ttf", size=40)
    except IOError:
        font = ImageFont.load_default()

    detected_school_uniform = False
    detected_non_school_uniform = False

    # Draw bounding boxes and labels from inference results
    for prediction in result['predictions']:
        x_center, y_center = prediction['x'], prediction['y']
        width = prediction['width']
        height = prediction['height']
        x1 = int(x_center - width / 2)
        y1 = int(y_center - height / 2)
        x2 = int(x_center + width / 2)
        y2 = int(y_center + height / 2)
        
        # Check if the label is 'School Uniform'
        if prediction['class'] == 'School Uniform':
            color = "green"
            detected_school_uniform = True
        else:
            color = "red"
            detected_non_school_uniform = True

        draw.rectangle(((x1, y1), (x2, y2)), outline=color, width=2)
        draw.text((x1, y1 - 10), f"{prediction['class']} ({prediction['confidence']:.2f})", fill=color, font=font)

    # Save the final image with bounding boxes
    output_path = "static/detected_image.jpg"
    detected_image_path = "static/detected_image.jpg"
    resized_image.save(output_path, format='JPEG')

    # Return detection result
    if detected_school_uniform:
        return jsonify({"status": "uniform_detected"})
    elif detected_non_school_uniform:
        return jsonify({"status": "non_uniform_detected"})
    else:
        return jsonify({"status": "no_detection"})
    
# Download route
@app.route('/download_image')
def download_image():
    return send_from_directory(directory='static', path='detected_image.jpg')

# Main route for homepage
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/images')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(debug=True)
