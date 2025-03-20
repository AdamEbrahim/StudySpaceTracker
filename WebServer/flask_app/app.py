from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Simulated database (In production, use SQLite, MySQL, or PostgreSQL)
study_spaces = {}

@app.route('/')
def home():
    return render_template('index.html', spaces=study_spaces)

@app.route('/update', methods=['POST'])
def update_data():
    data = request.get_json()
    location = data.get('location')
    available_spaces = data.get('available_spaces')

    if location and available_spaces is not None:
        study_spaces[location] = available_spaces
        return jsonify({"status": "success"}), 200
    return jsonify({"error": "Invalid data"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)