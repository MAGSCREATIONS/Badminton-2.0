from flask import Flask, request, jsonify, render_template
from logic import (
    load_players, add_player, remove_player, generate_balanced_groups,
    mark_attendance,
    get_attendance_by_date, get_all_attendance, get_attendance_by_player,
)

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html", players=load_players())

@app.route("/add_player", methods=["POST"])
def add():
    data = request.json
    add_player(data['name'], data['skill'])
    return jsonify({"success": True})

@app.route("/remove_player", methods=["POST"])
def remove():
    data = request.json
    remove_player(data['name'])
    return jsonify({"success": True})

@app.route("/randomize", methods=["POST"])
def randomize():
    data = request.json
    present_names = data.get("present_players", [])
    try:
        groups = generate_balanced_groups(present_names)
        output = [
            {
                "group_number": g.get_group_number(),
                "team1": [p.get_name() for p in g.get_team1().get_players()],
                "team2": [p.get_name() for p in g.get_team2().get_players()]
            }
            for g in groups
        ]
        return jsonify({"groups": output})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/mark_attendance", methods=["POST"])
def attendance_mark():
    data = request.json
    present_names = data.get("present_players", [])
    date = data.get("date", None)
    try:
        summary = mark_attendance(present_names, date)
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/attendance/today")
def attendance_today():
    return jsonify(get_attendance_by_date())

@app.route("/attendance/<date>")
def attendance_by_date(date):
    try:
        return jsonify(get_attendance_by_date(date))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/attendance/player/<player_name>")
def attendance_by_player(player_name):
    return jsonify(get_attendance_by_player(player_name))

@app.route("/attendance/all")
def attendance_all():
    return jsonify(get_all_attendance())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)