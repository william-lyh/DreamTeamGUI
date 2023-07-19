from flask import Flask, request, render_template
from markupsafe import Markup
import parser
import secrets
import os
import threading

app = Flask(__name__)
parser_lock = threading.Lock()

@app.route('/', methods=["GET"])
def index():
    course_name = request.args.get("course_name", "CS10")
    student_mastery = request.args.get("student_mastery", "0")
    filename_token = secrets.token_urlsafe()
    with parser_lock:
        parser.generate_map(name=course_name, token=filename_token, student_mastery=student_mastery)
        with open("data/{}_{}.svg".format(course_name, filename_token)) as svg_file:
            svg = svg_file.read()
        if os.path.exists("data/{}_{}.svg".format(course_name, filename_token)):
            os.remove("data/{}_{}.dot".format(course_name, filename_token))
            os.remove("data/{}_{}.svg".format(course_name, filename_token))
    return render_template("web_ui.html",
                           student_mastery=student_mastery,
                           course_name=course_name,
                           graphviz_svg=Markup(svg))


if __name__ == '__main__':
    app.run(debug=False, port=33507)
