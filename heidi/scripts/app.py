from flask import Flask, render_template, request, Response, stream_with_context
import subprocess

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/run_process', methods=['POST'])
def run_process():
    user_input = request.form['user_input']

    def generate():
        # Call process.py and stream its stdout
        process = subprocess.Popen(
            ['python', 'run_server_main.py', user_input],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in process.stdout:
            yield f"data:{line}"
        process.stdout.close()
        process.wait()
        # Optionally, yield a marker for completion
        yield "data:__PROCESS_DONE__\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
