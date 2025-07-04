from flask import Flask, request, render_template_string, send_file, url_for
from io import StringIO, BytesIO
from collections import defaultdict
import csv

app = Flask(__name__)

FINALS_UPLOAD_HTML = '''
<!doctype html>
<title>Create a Finals draw by uploading heats results</title>
<h2>Create a Finals draw by uploading heats results</h2>
<form method=post enctype=multipart/form-data>
  <input type=file name=finals_csv required>
  <input type=submit value=Upload style="background-color: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 4px;">
</form>
{% if table %}
  <h3>Edit Times</h3>
  <form method="post">
    <textarea name="csv_content" hidden>{{ csv_content }}</textarea>
    <table border="1" cellpadding="4">
      <tr>
        {% for col in header %}
          <th>{{ col }}</th>
        {% endfor %}
      </tr>
      {% for row in table %}
        {% set i = loop.index0 %}
        <tr>
          {% for cell in row %}
            {% set j = loop.index0 %}
            {% if header[j]|lower == 'time' %}
              <td>
                <input type="text" name="time_{{ i }}" value="{{ cell }}">
              </td>
            {% else %}
              <td>{{ cell }}</td>
            {% endif %}
          {% endfor %}
        </tr>
      {% endfor %}
    </table>
    <button type="submit" name="edit_times" value="1">Save Times</button>
  </form>
{% endif %}
'''

def get_lane_order(num_lanes):
    """
    Returns a list of lane numbers (1-based) in the desired order:
    - Start from the middle lane, then alternate right and left.
    """
    order = []
    if num_lanes == 0:
        return order
    mid = (num_lanes + 1) // 2
    order.append(mid)
    offset = 1
    while len(order) < num_lanes:
        if mid + offset <= num_lanes:
            order.append(mid + offset)
        if len(order) < num_lanes and mid - offset > 0:
            order.append(mid - offset)
        offset += 1
    return order

@app.route('/', methods=['GET', 'POST'])
def upload_finals_csv():
    table = []
    header = []
    team_times = {}
    team_divisions = {}
    current_heat = None
    division_groups = defaultdict(list)
    finals_draw = {}
    csv_content = ''
    lanes_per_division = {}
    error_message = ''

    if request.method == 'POST':
        if 'finals_csv' in request.files and request.files['finals_csv']:
            file = request.files['finals_csv']
            csv_content = file.read().decode('utf-8')
        elif 'csv_content' in request.form:
            csv_content = request.form['csv_content']
            # Update times if editing
            if 'edit_times' in request.form:
                # Parse CSV and update times from form
                reader = csv.reader(StringIO(csv_content))
                rows = list(reader)
                # Find indices for Heat, Team, and Time columns
                header = rows[0]
                time_idx = header.index('time') if 'time' in header else 5
                # Update times in rows
                for i, row in enumerate(rows[1:]):
                    new_time = request.form.get(f"time_{i}", "").strip()
                    row[time_idx] = new_time
                # Rebuild csv_content
                output = StringIO()
                writer = csv.writer(output)
                for row in rows:
                    writer.writerow(row)
                csv_content = output.getvalue()
            # Get lanes per division from form
            for key in request.form:
                if key.startswith('lanes_'):
                    division = key.replace('lanes_', '')
                    try:
                        lanes_per_division[division] = int(request.form[key])
                    except Exception:
                        lanes_per_division[division] = None

    if csv_content:
        reader = csv.reader(StringIO(csv_content))
        for i, row in enumerate(reader):
            if i == 0:
                header = row
            else:
                padded_row = row + [''] * (len(header) - len(row))
                table.append(padded_row)
                heat = padded_row[0].strip() if padded_row[0].strip() else current_heat
                if padded_row[0].strip():
                    current_heat = padded_row[0].strip()
                team = padded_row[3].strip()
                division = padded_row[4].strip()
                time = padded_row[5].strip()
                if team:
                    if team not in team_times:
                        team_times[team] = {'Heat 1': '', 'Heat 2': ''}
                    if team not in team_divisions and division:
                        team_divisions[team] = division
                    if heat in ['Heat 1', 'Heat 2'] and time:
                        team_times[team][heat] = time

        # Prepare summary table
        summary = []
        for team, heats in team_times.items():
            try:
                t1 = float(heats['Heat 1']) if heats['Heat 1'] else 0
                t2 = float(heats['Heat 2']) if heats['Heat 2'] else 0
                total = t1 + t2 if t1 and t2 else None
            except ValueError:
                total = None
            division = team_divisions.get(team, '')
            summary.append([team, division, heats['Heat 1'], heats['Heat 2'], total])

        # Group by division and sort within each division
        division_groups = defaultdict(list)
        for row in summary:
            division = row[1]
            total = row[4]
            if isinstance(total, (int, float)) and total is not None and total != 0:
                division_groups[division].append(row)

        for division in division_groups:
            division_groups[division] = sorted(
                division_groups[division], key=lambda x: x[4]
            )
            # Add position column for each division and format total time
            for idx, row in enumerate(division_groups[division], start=1):
                row.insert(0, idx)
                row[5] = f"{row[5]:.3f}" if row[5] is not None else ''

        # Finals draw logic
        if lanes_per_division:
            for division, teams in division_groups.items():
                lanes = lanes_per_division.get(division)
                if not lanes or lanes < 1:
                    continue
                races = []
                lane_order = get_lane_order(lanes)
                for i in range(0, len(teams), lanes):
                    race_teams = teams[i:i+lanes]
                    race = [None] * lanes
                    for pos, team in enumerate(race_teams):
                        lane_idx = lane_order[pos] - 1
                        race[lane_idx] = team
                    races.append(race)
                races.reverse()
                finals_draw[division] = races

    # Render
    return render_template_string(FINALS_UPLOAD_HTML + '''
    {% if division_groups %}
      <h3>Combined Times by Division (Heat 1 + Heat 2)</h3>
      {% for division, rows in division_groups.items() %}
        <h4>{{ division }}</h4>
        <table border="1" cellpadding="4">
          <tr>
            <th>Position</th>
            <th>Team Name</th>
            <th>Division</th>
            <th>Heat 1 Time</th>
            <th>Heat 2 Time</th>
            <th>Total Time</th>
          </tr>
          {% for row in rows %}
            <tr>
              {% for cell in row %}
                <td>{{ cell }}</td>
              {% endfor %}
            </tr>
          {% endfor %}
        </table>
      {% endfor %}
      <hr>
      <h3>Finals Draw</h3>
      <form method="post">
        <textarea name="csv_content" hidden>{{ csv_content }}</textarea>
        {% for division, rows in division_groups.items() %}
          <label for="lanes_{{ division }}">Number of lanes for {{ division }}:</label>
          <input type="number" name="lanes_{{ division }}" min="1" required>
          <br>
        {% endfor %}
        <button type="submit">Generate Finals Draw</button>
      </form>
    {% endif %}

    {% if finals_draw %}
      {% for division, races in finals_draw.items() %}
        <h4>Finals Draw - {{ division }}</h4>
        {% for race in races %}
          <b>Race {{ loop.index }}</b>
          <table border="1" cellpadding="4">
            <tr>
              <th>Lane</th>
              <th>Position</th>
              <th>Team Name</th>
              <th>Total Time</th>
            </tr>
            {% for lane_idx in range(race|length) %}
              <tr>
                <td>{{ lane_idx + 1 }}</td>
                {% if race[lane_idx] %}
                  <td>{{ race[lane_idx][0] }}</td>
                  <td>{{ race[lane_idx][1] }}</td>
                  <td>{{ race[lane_idx][5] }}</td>
                {% else %}
                  <td></td><td></td><td></td>
                {% endif %}
              </tr>
            {% endfor %}
          </table>
        {% endfor %}
      {% endfor %}
    {% endif %}
    {% if division_groups %}
      <form method="post" action="/export_combined">
        <textarea name="csv_content" hidden>{{ csv_content }}</textarea>
        <button type="submit">Export Combined Times CSV</button>
      </form>
    {% endif %}
    {% if finals_draw %}
      <form method="post" action="/export_finals">
        <textarea name="csv_content" hidden>{{ csv_content }}</textarea>
        {% for division, races in finals_draw.items() %}
          <input type="hidden" name="lanes_{{ division }}" value="{{ races[0]|length }}">
        {% endfor %}
        <button type="submit">Export Finals Draw CSV</button>
      </form>
    {% endif %}
    <form action="{{ url_for('download_template') }}" method="get" style="margin-bottom: 1em;">
      <button type="submit">Download CSV Template to help with upload</button>
    </form>
    ''', table=table, header=header, division_groups=division_groups, finals_draw=finals_draw, csv_content=csv_content)

@app.route('/export_combined', methods=['POST'])
def export_combined():
    csv_content = request.form['csv_content']
    team_times = {}
    team_divisions = {}
    current_heat = None
    reader = csv.reader(StringIO(csv_content))
    header = []
    table = []
    for i, row in enumerate(reader):
        if i == 0:
            header = row
        else:
            padded_row = row + [''] * (len(header) - len(row))
            table.append(padded_row)
            heat = padded_row[0].strip() if padded_row[0].strip() else current_heat
            if padded_row[0].strip():
                current_heat = padded_row[0].strip()
            team = padded_row[3].strip()
            division = padded_row[4].strip()
            time = padded_row[5].strip()
            if team:
                if team not in team_times:
                    team_times[team] = {'Heat 1': '', 'Heat 2': ''}
                if team not in team_divisions and division:
                    team_divisions[team] = division
                if heat in ['Heat 1', 'Heat 2'] and time:
                    team_times[team][heat] = time

    summary = []
    for team, heats in team_times.items():
        try:
            t1 = float(heats['Heat 1']) if heats['Heat 1'] else 0
            t2 = float(heats['Heat 2']) if heats['Heat 2'] else 0
            total = t1 + t2 if t1 and t2 else None
        except ValueError:
            total = None
        division = team_divisions.get(team, '')
        summary.append([team, division, heats['Heat 1'], heats['Heat 2'], total])

    division_groups = defaultdict(list)
    for row in summary:
        division = row[1]
        total = row[4]
        if isinstance(total, (int, float)) and total is not None and total != 0:
            division_groups[division].append(row)

    for division in division_groups:
        division_groups[division] = sorted(
            division_groups[division], key=lambda x: x[4]
        )
        for idx, row in enumerate(division_groups[division], start=1):
            row.insert(0, idx)
            row[5] = f"{row[5]:.3f}" if row[5] is not None else ''

    # Write CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Division', 'Position', 'Team Name', 'Heat 1 Time', 'Heat 2 Time', 'Total Time'])
    for division, rows in division_groups.items():
        for row in rows:
            writer.writerow([division, row[0], row[1], row[3], row[4], row[5]])
    output.seek(0)
    return send_file(BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='combined_times.csv')

@app.route('/export_finals', methods=['POST'])
def export_finals():
    csv_content = request.form['csv_content']
    lanes_per_division = {}
    for key in request.form:
        if key.startswith('lanes_'):
            division = key.replace('lanes_', '')
            try:
                lanes_per_division[division] = int(request.form[key])
            except Exception:
                lanes_per_division[division] = None

    # Rebuild division_groups as above
    team_times = {}
    team_divisions = {}
    current_heat = None
    import csv
    reader = csv.reader(StringIO(csv_content))
    header = []
    table = []
    for i, row in enumerate(reader):
        if i == 0:
            header = row
        else:
            padded_row = row + [''] * (len(header) - len(row))
            table.append(padded_row)
            heat = padded_row[0].strip() if padded_row[0].strip() else current_heat
            if padded_row[0].strip():
                current_heat = padded_row[0].strip()
            team = padded_row[3].strip()
            division = padded_row[4].strip()
            time = padded_row[5].strip()
            if team:
                if team not in team_times:
                    team_times[team] = {'Heat 1': '', 'Heat 2': ''}
                if team not in team_divisions and division:
                    team_divisions[team] = division
                if heat in ['Heat 1', 'Heat 2'] and time:
                    team_times[team][heat] = time

    summary = []
    for team, heats in team_times.items():
        try:
            t1 = float(heats['Heat 1']) if heats['Heat 1'] else 0
            t2 = float(heats['Heat 2']) if heats['Heat 2'] else 0
            total = t1 + t2 if t1 and t2 else None
        except ValueError:
            total = None
        division = team_divisions.get(team, '')
        summary.append([team, division, heats['Heat 1'], heats['Heat 2'], total])

    division_groups = defaultdict(list)
    for row in summary:
        division = row[1]
        total = row[4]
        if isinstance(total, (int, float)) and total is not None and total != 0:
            division_groups[division].append(row)

    for division in division_groups:
        division_groups[division] = sorted(
            division_groups[division], key=lambda x: x[4]
        )
        for idx, row in enumerate(division_groups[division], start=1):
            row.insert(0, idx)
            row[5] = f"{row[5]:.3f}" if row[5] is not None else ''

    # Finals draw logic
    def get_lane_order(num_lanes):
        order = []
        if num_lanes == 0:
            return order
        mid = (num_lanes + 1) // 2
        order.append(mid)
        offset = 1
        while len(order) < num_lanes:
            if mid + offset <= num_lanes:
                order.append(mid + offset)
            if len(order) < num_lanes and mid - offset > 0:
                order.append(mid - offset)
            offset += 1
        return order

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Division', 'Race', 'Lane', 'Team Name', 'Total Time', 'Position'])
    for division, teams in division_groups.items():
        lanes = lanes_per_division.get(division)
        if not lanes or lanes < 1:
            continue
        races = []
        lane_order = get_lane_order(lanes)
        for i in range(0, len(teams), lanes):
            race_teams = teams[i:i+lanes]
            race = [None] * lanes
            for pos, team in enumerate(race_teams):
                lane_idx = lane_order[pos] - 1
                race[lane_idx] = team
            races.append(race)
        races.reverse()
        for race_idx, race in enumerate(races, 1):
            for lane_idx, team in enumerate(race, 1):
                # Only show division for first row of division, race for first row of race
                show_division = division if race_idx == 1 and lane_idx == 1 else ''
                show_race = race_idx if lane_idx == 1 else ''
                if team:
                    writer.writerow([
                        show_division,
                        show_race,
                        lane_idx,
                        team[1],  # Team Name
                        team[5],  # Total Time
                        team[0],  # Position
                    ])
                else:
                    writer.writerow([
                        show_division,
                        show_race,
                        lane_idx,
                        '', '', ''
                    ])
            # Blank row after each race
            writer.writerow(['', '', '', '', '', ''])
    output.seek(0)
    return send_file(BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='finals_draw.csv')

@app.route('/download_template')
def download_template():
    import io
    import csv

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Heat', 'Race', 'Lane', 'Team Name', 'Division', 'time'])

    # Example data as shown in your screenshot/prompt
    heats = [
        ('Heat 1', [
            ('Race 1', 'Division 1'),
            ('Race 2', 'Division 1'),
            ('Race 3', 'Division 2'),
            ('Race 4', 'Division 2'),
        ])
    ]
    teams = ['Team 1', 'Team 2', 'Team 3', 'Team 4']

    for heat_name, races in heats:
        for race_idx, (race_name, division) in enumerate(races):
            for lane, team in enumerate(teams, 1):
                row = [
                    heat_name if lane == 1 else '',
                    race_name if lane == 1 else '',
                    lane,
                    team,
                    division,
                    0
                ]
                writer.writerow(row)

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='teams_template.csv'
    )

# Example in-memory storage (replace with DB or file for persistence)
times_data = [
    {'team': 'Team A', 'division': 'Div 1', 'time': '56.2'},
    {'team': 'Team B', 'division': 'Div 1', 'time': 'NTE'},
    {'team': 'Team C', 'division': 'Div 2', 'time': '60.1'},
]

RESULTS_HTML = '''
<h2>Results</h2>
<form action="{{ url_for('edit_times') }}" method="get">
    <button type="submit">Edit Times</button>
</form>
<table border="1">
    <tr>
        <th>Team</th>
        <th>Division</th>
        <th>Time</th>
    </tr>
    {% for row in times_data %}
    <tr>
        <td>{{ row.team }}</td>
        <td>{{ row.division }}</td>
        <td>{{ row.time }}</td>
    </tr>
    {% endfor %}
</table>
'''

EDIT_TIMES_HTML = '''
<h2>Edit Times</h2>
<form method="post">
    <table border="1">
        <tr>
            <th>Team</th>
            <th>Division</th>
            <th>Time</th>
        </tr>
        {% for idx, row in enumerate(times_data) %}
        <tr>
            <td>{{ row.team }}</td>
            <td>{{ row.division }}</td>
            <td>
                <input type="text" name="time_{{ idx }}" value="{{ row.time }}">
            </td>
        </tr>
        {% endfor %}
    </table>
    <button type="submit">Save Changes</button>
</form>
'''

@app.route('/')
def results():
    return render_template_string(RESULTS_HTML, times_data=times_data, url_for=url_for)

@app.route('/edit_times', methods=['GET', 'POST'])
def edit_times():
    global times_data
    if request.method == 'POST':
        for idx, row in enumerate(times_data):
            times_data[idx]['time'] = request.form.get(f'time_{idx}', '').strip()
        return redirect(url_for('results'))
    return render_template_string(EDIT_TIMES_HTML, times_data=times_data)

if __name__ == '__main__':
    app.run(debug=True)