import json
import logging
import os
import sys
import time
import uuid

from flask import Flask, request, jsonify, g, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from app import tracing

APP_VERSION = os.environ.get("APP_VERSION", "dev")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
SHOW_MESSAGE = os.environ.get("SHOW_MESSAGE", "false").lower() == "true"
MAX_DIGITS = 100

app = Flask(__name__)
tracing.setup(app)

REQUESTS = Counter(
    "evenodd_requests_total",
    "Number of HTTP requests",
    ["endpoint", "method", "status"],
)
LATENCY = Histogram(
    "evenodd_request_duration_seconds",
    "Time taken to handle a request",
    ["endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5],
)
RESULTS = Counter(
    "evenodd_checks_total",
    "Number of successful checks by result",
    ["result"],
)
BUILD_INFO = Gauge(
    "evenodd_build_info",
    "Running version of the app",
    ["version"],
)
BUILD_INFO.labels(version=APP_VERSION).set(1)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        line = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage(),
            "version": APP_VERSION,
        }
        extra = getattr(record, "extra_fields", None)
        if extra:
            line.update(extra)
        return json.dumps(line)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
log = logging.getLogger("evenodd")
log.setLevel(LOG_LEVEL)
log.addHandler(handler)
log.propagate = False

logging.getLogger("werkzeug").setLevel(logging.WARNING)


def is_even(number):
    if number % 2 == 0:
        return True
    else:
        return False


@app.before_request
def start_timer():
    g.start = time.time()
    g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))


@app.after_request
def record_request(response):
    endpoint = request.url_rule.rule if request.url_rule else "unknown"

    if endpoint in ["/healthz", "/readyz", "/metrics"]:
        return response

    duration = time.time() - g.start
    REQUESTS.labels(endpoint=endpoint, method=request.method, status=response.status_code).inc()
    LATENCY.labels(endpoint=endpoint).observe(duration)

    response.headers["X-Request-ID"] = g.request_id
    response.headers["X-App-Version"] = APP_VERSION

    log.info("request", extra={"extra_fields": {
        "request_id": g.request_id,
        "trace_id": tracing.current_trace_id(),
        "method": request.method,
        "path": request.path,
        "query": request.query_string.decode()[:200],
        "status": response.status_code,
        "duration_ms": round(duration * 1000, 2),
    }})
    return response


@app.route("/")
def home():
    return "Even or odd checker. Try /check?number=10\n"


@app.route("/check")
def check():
    value = request.args.get("number")

    if value is None or value.strip() == "":
        return jsonify({"error": "number is required"}), 400

    if len(value.strip()) > MAX_DIGITS:
        return jsonify({"error": "number is too long, max %d digits" % MAX_DIGITS}), 400

    try:
        number = int(value)
    except ValueError:
        return jsonify({"error": "number must be a whole number"}), 400

    even = is_even(number)
    if even:
        RESULTS.labels(result="even").inc()
    else:
        RESULTS.labels(result="odd").inc()

    body = {"number": number, "even": even}
    if SHOW_MESSAGE:
        if even:
            body["message"] = "%d is even" % number
        else:
            body["message"] = "%d is odd" % number

    return jsonify(body)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.route("/readyz")
def readyz():
    return jsonify({"status": "ready"})


@app.route("/version")
def version():
    return jsonify({"version": APP_VERSION})


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
