from flask import Blueprint, render_template_string, request, send_file, url_for, redirect, session
from io import StringIO, BytesIO
from collections import defaultdict
import csv

finals_draw_bp = Blueprint('finals_draw', __name__)

FINALS_UPLOAD_HTML = '''
<!doctype html>
<title>Finals Draw Creation</title>
<h2>Create a Finals Draw</h2>
<label>Upload with or without places and times</label>
<br>
<label>You are then able to edit the places and time</label>
<div style="height:8px;"></div>
<style>
.upload-btn, .file-btn {
    background-color: #28a745;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    box-shadow: 2px 2px 8px rgba(40,167,69,0.3);
    cursor: pointer;
    font-size: 1em;
}
.upload-btn:hover, .file-btn:hover {
    outline: 2px solid #1e7e34;
    box-shadow: 2px 2px 12px rgba(40,167,69,0.5);
}
input[type="file"] {
    display: none;
}
</style>

<form method=post enctype=multipart/form-data>
  <label for="finals_csv" class="file-btn">Choose Upload File</label>
  <input type="file" id="finals_csv" name="finals_csv" required onchange="document.getElementById('file-name').textContent = this.files[0]?.name || '';">
  <input type="submit" value="Upload File" class="upload-btn">
</form>
<div id="file-name" style="margin-top:8px; color:#155724; font-weight:bold;"></div>

{% if table %}
  <h3>Edit Places & Times</h3>
  <form method="post">
    <textarea name="csv_content" hidden>{{ csv_content }}</textarea>
    <table border="1" cellpadding="4">
      <tr>
        <th>Heat</th>
        <th>Race</th>
        <th>Lane</th>
        <th>Team Name</th>
        <th>Division</th>
        <th style="width:60px;">Place</th>
        <th style="width:100px;">Time</th>   
        # Set width for time and placehere #
      </tr>
      {% for row in table %}
        {% set i = loop.index0 %}
        <tr>
          <td>{{ row[0] }}</td>
          <td>{{ row[1] }}</td>
          <td>{{ row[2] }}</td>
          <td>{{ row[3] }}</td>
          <td>{{ row[4] }}</td>
          <td style="width:60px;">
            <input type="text" name="place_{{ i }}" value="{{ request.form.get('place_' ~ i, row[5]) }}" style="width:50px;">
          </td>
          <td style="width:100px;">
            <input type="text" name="time_{{ i }}" value="{{ request.form.get('time_' ~ i, row[6]) }}" style="width:90px;">
          </td>
        </tr>
      {% endfor %}
    </table>
    <table style="width:100%; border:none;">
      <tr>
        <td style="text-align: left; border:none;" colspan="{{ header|length }}">
          <button type="submit" name="edit_times" value="1" class="upload-btn">Save Times</button>
        </td>
      </tr>
    </table>
  </form>
{% endif %}
'''

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

@finals_draw_bp.route('/finals_draw', methods=['GET', 'POST'])
def finals_draw():
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
                reader = csv.reader(StringIO(csv_content))
                rows = list(reader)
                header = rows[0]
                time_idx = header.index('time') if 'time' in header else 5
                for i, row in enumerate(rows[1:]):
                    new_time = request.form.get(f"time_{i}", "").strip()
                    row[time_idx] = new_time
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
                # Use only the Time column (index 6) for calculations
                time = padded_row[6].strip()
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
                session['finals_draw'] = finals_draw

    # Calculate last heat race number
    last_heat_race_number = 0
    if 'heat1' in session and session['heat1']:
        last_heat_race_number += len(session['heat1'])
    if 'heat2' in session and session['heat2']:
        last_heat_race_number += len(session['heat2'])

    # Recalculate last_edit_race_number from session['edit_table'] or similar
    last_edit_race_number = 0
    if 'edit_table' in session:
        table = session['edit_table']
        race_col_index = 1  # Assuming 2nd column is 'Race'
        for row in table:
            try:
                race_num = int(row[race_col_index])
                if race_num > last_edit_race_number:
                    last_edit_race_number = race_num
            except (ValueError, IndexError):
                continue
    else:
        last_edit_race_number = 0  # fallback

    session['last_edit_race_number'] = last_edit_race_number

    # Render
    header = header or []
    return render_template_string(
        FINALS_UPLOAD_HTML + '''
    {% if division_groups %}
      <h3>Combined Times by Division (Heat 1 + Heat 2)</h3>
      <label>The table below shows the combined times for each team in each division, ranked first to last.</label>
      <Br>
      <div style="height:8px;"></div>                            
      <label>For this calculation the times are added together.</label>                                                                                   
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
      <Label>To create the finals draw, please enter the number of lanes for each division.</Label>        
      <div style="height:8px;"></div>                                                
      <form method="post">
        <textarea name="csv_content" hidden>{{ csv_content }}</textarea>
        {% for division, rows in division_groups.items() %}
          <label for="lanes_{{ division }}">Number of lanes for {{ division }}:</label>
          <input type="number" name="lanes_{{ division }}" min="1" required>
          <br>
        {% endfor %}
        <div style="height:8px;"></div>                          
        <button type="submit" style="background-color:#28a745; color:white; padding:8px 16px; border:none; border-radius:4px;">Generate Finals Draw</button>
      </form>
    {% endif %}

    {% if finals_draw %}
      {% set ns = namespace(global_race_number=race_offset) %}
      {% for division, races in finals_draw.items() %}
        <h4>Finals Draw - {{ division }}</h4>
        {% for race in races %}
          {% set ns.global_race_number = ns.global_race_number + 1 %}
          <b>Race {{ ns.global_race_number }}</b>
          <table border="1" cellpadding="4">
            <tr>
              <th>Lane</th>
              <th>Position</th>
              <th style="width:220px;">Team Name</th>
              <th style="width:120px;">Time</th>  {# Set your desired width here #}
            </tr>
            {% for lane_idx in range(race|length) %}
              <tr>
                <td>{{ lane_idx + 1 }}</td>
                <td>{{ race[lane_idx][0] }}</td>
                <td>{{ race[lane_idx][1] }}</td>
                <td style="width:120px;">
                  {{ race[lane_idx][6] if race[lane_idx]|length > 6 else '' }}
                </td>
              </tr>
            {% endfor %}
          </table>
        {% endfor %}
      {% endfor %}
      <form action="{{ url_for('finals_draw.exportfinal_csv') }}" method="post" style="margin-top:20px;">
        <button type="submit" class="file-btn">Export Finals Draw as CSV</button>
      </form>
    {% endif %}
    <form action="{{ url_for('selector') }}" method="get" style="margin-top:20px;">
    <button type="submit" style="background-color:#6c757d; color:white; padding:8px 16px; border:none; border-radius:4px;">Back to Selector Page</button>
</form>
<link rel="manifest" href="{{ url_for('static', filename='manifest.json') }}">
<meta name="theme-color" content="#007bff">
<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('{{ url_for('static', filename='service-worker.js') }}');
  }
</script>
''',
        table=table,
        header=header,
        division_groups=division_groups,
        finals_draw=finals_draw,
        csv_content=csv_content,
        last_edit_race_number=last_edit_race_number,
        race_offset=last_edit_race_number  # Use this as the offset for finals
    )

    # After building 'table' from the CSV (right after your for-loop that fills 'table')
    session['edit_table'] = table

@finals_draw_bp.route('/finals_draw/exportfinal_csv', methods=['POST'])
def exportfinal_csv():
    finals_draw = session.get('finals_draw')
    if not finals_draw:
        return "No finals draw data to export.", 400

    # Recalculate last_heat_race_number from session
    last_heat_race_number = 0
    if 'heat1' in session and session['heat1']:
        last_heat_race_number += len(session['heat1'])
    if 'heat2' in session and session['heat2']:
        last_heat_race_number += len(session['heat2'])

    output = StringIO()
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(['Division', 'Race', 'Lane', 'Position', 'Team Name', 'Time'])

    race_number = session.get('last_edit_race_number', 0)
    for division, races in finals_draw.items():
        for race in races:
            race_number += 1
            for lane_idx, team in enumerate(race, start=1):
                if team:
                    writer.writerow([
                        division,
                        f'Race {race_number}',
                        lane_idx,
                        team[0],  # Position
                        team[1],  # Team Name
                        team[6] if len(team) > 6 else ''  # Time, if available
                    ])
    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='finals_draw.csv'
    )