import flask

import config

'''
home_page

setup_page
    select lang
    upload images (2-15)
    begin exam

exam_page
    serve two images
    start recording
    websocket connection to server
    transcription api
'''

app = flask.Flask(__name__)

@app.route("/res/<filename>")
def resource_access(filename):
    return flask.send_from_directory(config.res_folder, filename)

@app.route("/")
def index():
    return flask.render_template("index.html")

@app.route("/setup")
def setup_exam():
    return flask.render_template("setup_exam.html", lang=flask.request.args["lang"], config=config)

if __name__ == "__main__":
    app.run(debug=True)