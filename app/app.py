from flask import Flask, request, jsonify

app = Flask(__name__)


def is_even(number):
    if number % 2 == 0:
        return True
    else:
        return False


@app.route("/")
def home():
    return "Even or odd checker. Try /check?number=10\n"


@app.route("/check")
def check():
    value = request.args.get("number")

    if value is None or value.strip() == "":
        return jsonify({"error": "number is required"}), 400

    try:
        number = int(value)
    except ValueError:
        return jsonify({"error": "number must be a whole number"}), 400

    return jsonify({"number": number, "even": is_even(number)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
