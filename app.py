from flask import Flask, request, render_template
import json
from markupsafe import Markup
import parser

app = Flask(__name__)

@app.route('/', methods=["GET"])
def index():
    course_name = request.args.get("course_name", "CS10")
    start_date = request.args.get("start_date", "2022-01-01")
    student_mastery = request.args.get("student_mastery", "000000")
    parser.generate_map("CS10")
    with open("data/CS10.svg") as svg_file:
        svg = svg_file.read()
    return render_template("web_ui.html",
                           start_date=start_date,
                           student_mastery=student_mastery,
                           course_name=course_name,
                           graphviz_svg=Markup(svg))


if __name__ == '__main__':
    app.run(debug=True)
