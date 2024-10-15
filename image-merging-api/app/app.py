import os
import dotenv
import convertapi
from PIL import Image

if not hasattr(Image, 'Resampling'):  # Pillow<9.0
    Image.Resampling = Image
from flask import (
    Flask,
    jsonify,
    make_response,
    render_template,
    request,
    send_from_directory,
    url_for
)
from gh_md_to_html.core_converter import markdown
from rembg import remove

from .merger import Merger

# load environment variables from .env file, if defined
dotenv.load_dotenv()

app = Flask(__name__)
app.config.from_object(os.environ["APP_SETTINGS"])


@app.route("/", methods=["GET"])
def index():
    with open("README.md", "r") as f:
        readme_md = f.read()
    readme_html = markdown(readme_md)
    return render_template("index.html", content=readme_html)


@app.route("/api/v1.0/merge-gif/", methods=["OPTIONS", "POST"])
def merge_gif():
    if request.method == "OPTIONS":
        return make_response(jsonify({"Allow": "POST"}), 200)
    gif = request.json.get('gif')
    if not gif:
        return jsonify({"error": "required gif"}), 400

    curr_directory = os.path.dirname(os.path.abspath(__file__))
    images_dir = curr_directory + "/images/"
    images_without_bg_dir = curr_directory + "/images_without_bg/"
    convertapi.api_credentials = ' secret_bcb654OblSYpUUg0'
    urls = convertapi.convert('png', {
        'File': gif
    }, from_format='gif').save_files(images_dir)
    output_paths = []
    img = Image.open(urls[0])
    size = img.size
    for url in urls:
        name = os.path.basename(url)
        output_path = images_without_bg_dir + name
        output_paths.append(output_path)
        img = Image.open(url)
        result = Image.new("RGBA", size, (0, 0, 0, 0))
        out = remove(img)
        result.paste(out, mask=out)
        result.save(output_path)
    return jsonify(output_paths), 201


@app.route("/api/v1.0/merge-images/", methods=["OPTIONS", "POST"])
def merge():
    if request.method == "OPTIONS":
        return make_response(jsonify({"Allow": "POST"}), 200)

    urls = request.json.get("urls", [])
    background_color = request.json.get("backgroundColor", [0, 0, 0])
    foreground_color = request.json.get("foregroundColor", [255, 255, 255])
    if len(urls) < 2:
        return jsonify({"error": "required minimum 2 urls"}), 400
    if len(background_color) != 3:
        return jsonify({"error": "backgroundColor required RGB format, example: [255, 100, 0]"}), 400
    if len(foreground_color) != 3:
        return jsonify({"error": "foregroundColor required RGB format, example: [255, 100, 0]"}), 400
    for color in background_color:
        if 255 < color or 0 > color:
            return jsonify({"error": "backgroundColor required RGB format, example: [255, 100, 0]"}), 400
    for color in foreground_color:
        if 255 < color or 0 > color:
            return jsonify({"error": "backgroundColor required RGB format, example: [255, 100, 0]"}), 400

    try:
        m = Merger(urls, background_color, foreground_color)
        m.merge_images()
        response = {
            "output_image": {
                "name": m.get_output_image("name"),
                "url": url_for(
                    "get_image", image_name=m.get_output_image("name"), _external=True
                ),
                "base64": m.get_output_image("base64"),
            }
        }
        return jsonify(response), 201
    except Exception as e:
        err_msg = getattr(e, "message", None)
        if not err_msg:
            err_msg = "Internal Error. Please Try Again"
        return make_response(jsonify({"error": err_msg}), 500)


@app.route("/merged-images/<string:image_name>", methods=["GET"])
def get_image(image_name):
    return send_from_directory(app.config["OUTPUT_IMAGES_FOLDER"], image_name)


@app.errorhandler(500)
def internal_server_error(error):
    return make_response(jsonify({"error": "Internal Server Error"}), 500)


@app.errorhandler(405)
def method_not_allowed(error):
    return make_response(jsonify({"error": "Method Not Allowed"}), 405)


@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({"error": "Bad Request"}), 400)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({"error": "Not found"}), 404)
