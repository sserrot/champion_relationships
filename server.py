# all the imports
import os
from flask import Flask, request, redirect, url_for, abort, \
    render_template

ALLOWED_EXTENSIONS = set(['txt','csv', 'xlsx', 'xls'])

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

# Index Initialized


@app.route("/", methods=['GET', 'POST'])
def index():
    return render_template('LoLChampRelationships.html')


@app.route("/network")
def network():
    return render_template('network.html')


@app.route("/graph_raw.html")
def graph_raw():
    return render_template('graph_raw.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
