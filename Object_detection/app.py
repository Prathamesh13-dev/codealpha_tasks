from flask import Flask, render_template, Response
from tracker import generate_frames

app = Flask(__name__)

@app.route('/')
def index():
    """Render the main web page."""
    return render_template('index.html')
@app.route('/video_feed')
def video_feed():
    # Added conf=0.15 to make the AI much more sensitive
    return Response(generate_frames(source=0, conf=0.15, demo=False),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)