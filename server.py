# all the imports
import os
from flask import Flask, request, redirect, url_for, abort, \
    render_template, send_from_directory

ALLOWED_EXTENSIONS = set(['txt','csv', 'xlsx', 'xls'])

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

# Index Initialized


@app.route("/", methods=['GET', 'POST'])
def index():
    return render_template('network.html')


@app.route("/network")
def network():
    return render_template('network.html')


@app.route("/previous")
def previous():
    return render_template('network_previous.html')


@app.route("/report")
def report():
    return render_template('LoLChampRelationships.html')


@app.route("/graph_raw.html")
def graph_raw():
    return render_template('graph_raw.html')


IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "R_analysis", "img")


@app.route("/img/<path:filename>")
def champion_image(filename):
    return send_from_directory(IMG_DIR, filename)


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5001, debug=False)
