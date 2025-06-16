from flask import Flask, request, render_template_string, send_file, session, url_for
import random
import csv
import io
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

def generate_heat_draw(teams, num_lanes):
    random.shuffle(teams)
    races = []
    num_races = (len(teams) + num_lanes - 1) // num_lanes
    for i in range(num_races):
        race_teams = []
        for lane in range(num_lanes):
            team_index = i * num_lanes + lane
            if team_index < len(teams):
                race_teams.append(teams[team_index])
            else:
                race_teams.append(None)
        races.append(race_teams)
    return races

def get_team_lanes(heat):
    team_lanes = {}
    for race in heat:
        for lane_num, team in enumerate(race):
            if team is not None:
                team_lanes[team['name']] = lane_num
    return team_lanes

def get_race_opponents(heat):
    opponents = {}
    for race in heat:
        teams_in_race = [team['name'] for team in race if team is not None]
        for team in teams_in_race:
            if team not in opponents:
                opponents[team] = set()
            opponents[team].update(t for t in teams_in_race if t != team)
    return opponents

def get_last_two_race_teams(heat):
    last_two = []
    if len(heat) >= 2:
        last_two = heat[-2] + heat[-1]
    elif len(heat) == 1:
        last_two = heat[-1]
    return set(team['name'] for team in last_two if team is not None)

def generate_heat2_draw(teams, num_lanes, heat1_opponents, heat1_lanes, last_two_teams):
    teams = teams.copy()
    random.shuffle(teams)
    races = []
    num_races = (len(teams) + num_lanes - 1) // num_lanes
    assigned = set()
    for race_idx in range(num_races):
        race_teams = [None] * num_lanes
        available = [t for t in teams if t['name'] not in assigned]
        avoid_set = last_two_teams if race_idx < 2 else set()
        for lane in range(num_lanes):
            possible_teams = [
                t for t in available
                if t['name'] not in avoid_set
                and all(t['name'] not in heat1_opponents.get(other, set()) for other in [rt['name'] for rt in race_teams if rt])
                and heat1_lanes.get(t['name'], -1) != lane
            ]
            if not possible_teams:
                possible_teams = [
                    t for t in available
                    if all(t['name'] not in heat1_opponents.get(other, set()) for other in [rt['name'] for rt in race_teams if rt])
                    and heat1_lanes.get(t['name'], -1) != lane
                ]
            if not possible_teams:
                possible_teams = [
                    t for t in available
                    if all(t['name'] not in heat1_opponents.get(other, set()) for other in [rt['name'] for rt in race_teams if rt])
                ]
            if not possible_teams:
                possible_teams = available
            if possible_teams:
                team = random.choice(possible_teams)
                race_teams[lane] = team
                assigned.add(team['name'])
                available.remove(team)
        races.append(race_teams)
    return races

HTML_FORM = '''
<!doctype html>
<title>Race Draw Generator</title>
<h2>Upload Teams CSV (with "name" and "division" columns) and Enter Number of Lanes</h2>
<form method=post enctype=multipart/form-data>
  <input type=file name=teams_csv required>
  <input type=number name=num_lanes min=1 required placeholder="Number of lanes">
  <input type=submit value=Generate>
</form>
{% if heat1 %}
  <h3>--- Heat 1 Draw ---</h3>
  {% for race in heat1 %}
    <b>Race {{loop.index}}:</b><br>
    {% for team in race %}
      Lane {{loop.index}}: {{team['name'] if team else "EMPTY"}} ({{team['division'] if team else ""}})<br>
    {% endfor %}
    <hr>
  {% endfor %}
  <h3>--- Heat 2 Draw ---</h3>
  {% for race in heat2 %}
    <b>Race {{loop.index}}:</b><br>
    {% for team in race %}
      Lane {{loop.index}}: {{team['name'] if team else "EMPTY"}} ({{team['division'] if team else ""}})<br>
    {% endfor %}
    <hr>
  {% endfor %}
  <form action="{{ url_for('export_csv') }}" method="post">
    <button type="submit">Export as CSV</button>
  </form>
{% endif %}
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    heat1 = heat2 = None
    if request.method == 'POST':
        file = request.files['teams_csv']
        num_lanes = int(request.form['num_lanes'])
        teams = []
        if file:
            stream = io.StringIO(file.stream.read().decode("utf-8"))
            reader = csv.DictReader(stream)
            for row in reader:
                if row.get('name') and row.get('division'):
                    teams.append({'name': row['name'], 'division': row['division']})
        if teams and num_lanes > 0:
            heat1 = generate_heat_draw(teams.copy(), num_lanes)
            heat1_opponents = get_race_opponents(heat1)
            heat1_lanes = get_team_lanes(heat1)
            last_two_teams = get_last_two_race_teams(heat1)
            heat2 = generate_heat2_draw(teams, num_lanes, heat1_opponents, heat1_lanes, last_two_teams)
            session['heat1'] = heat1
            session['heat2'] = heat2
    else:
        heat1 = session.get('heat1')
        heat2 = session.get('heat2')
    return render_template_string(HTML_FORM, heat1=heat1, heat2=heat2)

@app.route('/export_csv', methods=['POST'])
def export_csv():
    heat1 = session.get('heat1')
    heat2 = session.get('heat2')
    output = io.StringIO()
    writer = csv.writer(output)
    if heat1:
        writer.writerow(['Heat 1'])
        for i, race in enumerate(heat1, 1):
            writer.writerow([f'Race {i}'] + [f"{team['name']} ({team['division']})" if team else "EMPTY" for team in race])
    if heat2:
        writer.writerow([])
        writer.writerow(['Heat 2'])
        for i, race in enumerate(heat2, 1):
            writer.writerow([f'Race {i}'] + [f"{team['name']} ({team['division']})" if team else "EMPTY" for team in race])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='heats.csv'
    )

if __name__ == '__main__':
    app.run(debug=True)