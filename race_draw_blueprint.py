from flask import Blueprint, render_template_string, request, send_file, session, url_for
import random
import csv
import io
import os

race_draw_bp = Blueprint('race_draw', __name__, template_folder='templates')

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
                team_lanes[team['Team Name']] = lane_num
    return team_lanes

def get_race_opponents(heat):
    opponents = {}
    for race in heat:
        teams_in_race = [team['Team Name'] for team in race if team is not None]
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
    return set(team['Team Name'] for team in last_two if team is not None)

def generate_heat2_draw(teams, num_lanes, heat1_opponents, heat1_lanes, last_two_teams):
    teams = teams.copy()
    random.shuffle(teams)
    races = []
    num_races = (len(teams) + num_lanes - 1) // num_lanes
    assigned = set()
    for race_idx in range(num_races):
        race_teams = [None] * num_lanes
        available = [t for t in teams if t['Team Name'] not in assigned]  # <-- FIXED HERE
        avoid_set = last_two_teams if race_idx < 2 else set()
        for lane in range(num_lanes):
            possible_teams = [
                t for t in available
                if t['Team Name'] not in avoid_set
                and all(t['Team Name'] not in heat1_opponents.get(other, set()) for other in [rt['Team Name'] for rt in race_teams if rt])
                and heat1_lanes.get(t['Team Name'], -1) != lane
            ]
            if not possible_teams:
                possible_teams = [
                    t for t in available
                    if all(t['Team Name'] not in heat1_opponents.get(other, set()) for other in [rt['Team Name'] for rt in race_teams if rt])
                    and heat1_lanes.get(t['Team Name'], -1) != lane
                ]
            if not possible_teams:
                possible_teams = [
                    t for t in available
                    if all(t['Team Name'] not in heat1_opponents.get(other, set()) for other in [rt['Team Name'] for rt in race_teams if rt])
                ]
            if not possible_teams:
                possible_teams = available
            if possible_teams:
                team = random.choice(possible_teams)
                race_teams[lane] = team
                assigned.add(team['Team Name'])
                available.remove(team)
        races.append(race_teams)
    return races

def validate_teams_csv(reader):
    errors = []
    teams = []
    seen_names = set()
    duplicate_names = set()
    for idx, row in enumerate(reader, start=2):  # start=2 to account for header row
        name = (row.get('Team Name') or '').strip()
        division = (row.get('Division') or '').strip()
        if not name:
            errors.append(f"Row {idx}: Missing Team Name.")
        if not division:
            errors.append(f"Row {idx}: Missing Division for team '{name or '[blank]'}'.")
        if name:
            if name in seen_names:
                duplicate_names.add(name)
            seen_names.add(name)
        if name and division:
            teams.append({'Team Name': name, 'Division': division})
    for dup in duplicate_names:
        errors.append(f"Duplicate team name found: '{dup}'")
    return teams, errors, duplicate_names

HTML_FORM = '''
<!doctype html>
<title>Race Draw Generator</title>
<h2>Creating a Race Draw using a Template</h2>
<label>Either Download the template, fill it out then select Generate.</label>
<div style="height:8px;"></div>
<form action="{{ url_for('race_draw.download_template') }}" method="get" style="margin-bottom:16px;">
  <button type="submit" class="file-btn">Download Template</button>
</form>
<h3>OR</h3>
<label>Create a CSV (with "Team Name" and "Division" columns)</label>
<div style="height:12px;"></div>
<img src="{{ url_for('static', filename='Team Names.png') }}" alt="CSV Example" style="max-width:400px; width:100%; height:auto; margin-bottom:16px; border:2px solid black; display:block; margin-left:0;">
<form method="post" enctype="multipart/form-data">
  <label for="teams_csv" class="file-btn" style="margin-bottom:12px;">Choose Upload File</label>
  <input type="file" id="teams_csv" name="teams_csv" required onchange="document.getElementById('file-name').textContent = this.files[0]?.name || '';">
  <div id="file-name" style="margin-top:12px; color:#155724; font-weight:bold;"></div>
  <input type="number" name="num_lanes" min="1" required placeholder="Enter Number of lanes" style="margin-top:12px; margin-bottom:12px;">
  <br>
  <input type="submit" value="Generate Race Draw for Mixed Divisional Heats" class="file-btn">
</form>
<form action="{{ url_for('selector') }}" method="get" style="margin-top:20px;">
  <button type="submit" style="background-color:#6c757d; color:white; padding:8px 16px; border:none; border-radius:4px;">
      Back to Selector Page
  </button>
</form>
{% if errors %}
  <div style="color: red;">
    <h3>CSV Errors:</h3>
    <ul>
      {% for error in errors %}
        <li>{{ error }}</li>
      {% endfor %}
    </ul>
  </div>
{% endif %}
{% if upload_success %}
  <div style="color: green; font-weight: bold; margin-top: 10px;">
    Upload successful!
  </div>
{% endif %}
{% if heat1 %}
  <h3>--- Heat 1 Draw ---</h3>
  {% for race in heat1 %}
    <b>Race {{ loop.index }}:</b>
    <table border="1" cellpadding="4" style="margin-bottom:10px;">
      <tr>
        <th>Lane</th>
        <th style="width:220px;">Team Name</th>
        <th>Division</th>
      </tr>
      {% for team in race %}
      <tr>
        <td>{{loop.index}}</td>
        <td style="width:220px;{% if team['Team Name'] in duplicate_names %} background-color: #ffcccc;{% endif %}">
          {% if team and team['Team Name'] %}
            {{ team['Team Name'] }}
          {% else %}
            <span style="color:red;">EMPTY</span>
          {% endif %}
        </td>
        <td>{{team['Division'] if team else ""}}</td>
      </tr>
      {% endfor %}
    </table>
  {% endfor %}
  <h3>--- Heat 2 Draw ---</h3>
  {% set heat1_races = heat1|length %}
  {% for race in heat2 %}
    <b>Race {{ heat1_races + loop.index }}:</b>
    <table border="1" cellpadding="4" style="margin-bottom:10px;">
      <tr>
        <th>Lane</th>
        <th style="width:220px;">Team Name</th>
        <th>Division</th>
      </tr>
      {% for team in race %}
      <tr>
        <td>{{loop.index}}</td>
        <td style="width:220px;">
          {% if team and team['Team Name'] %}
            {{ team['Team Name'] }}
          {% else %}
            <span style="color:red;">EMPTY</span>
          {% endif %}
        </td>
        <td>{{team['Division'] if team else ""}}</td>
      </tr>
      {% endfor %}
    </table>
  {% endfor %}
  
  {% if heat1 and heat2 %}
      <label>Ensure you check the last two races of the 'Heat 1' and the first two races of 'Heat 2' so the teams are not the same</label> 
      <form action="{{ url_for('race_draw.export_csv') }}" method="post" style="margin-top:20px;">
        <button type="submit" class="file-btn">Export as CSV</button>
      </form>
    {% endif %}
    <form action="{{ url_for('selector') }}" method="get" style="margin-top:20px;">
      <button type="submit" style="background-color:#6c757d; color:white; padding:8px 16px; border:none; border-radius:4px;">
        Back to Selector Page
      </button>
    </form>
{% endif %}
<style>
.upload-btn {
    background-color: #28a745;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    box-shadow: 2px 2px 8px rgba(40,167,69,0.3);
    cursor: pointer;
    font-size: 1em;
}
.upload-btn:hover {
    outline: 2px solid #1e7e34;
    box-shadow: 2px 2px 12px rgba(40,167,69,0.5);
}
.file-btn {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    box-shadow: 2px 2px 8px rgba(0,123,255,0.3);
    cursor: pointer;
    font-size: 1em;
}
.file-btn:hover {
    outline: 2px solid #0056b3;
    box-shadow: 2px 2px 12px rgba(0,123,255,0.5);
}
input[type="file"] {
    display: none;
}
</style>
<script>
document.getElementById('add-row-btn').onclick = function() {
    // Find the table above the button
    var table = this.previousElementSibling;
    // Insert a new row at the end
    var row = table.insertRow(-1);
    // The new number is the current number of rows minus the header row
    var number = table.rows.length - 1;
    var cell1 = row.insertCell(0);
    var cell2 = row.insertCell(1);
    var cell3 = row.insertCell(2);
    cell1.innerHTML = number;
    cell2.innerHTML = '<input type="text" name="Team_Name">';
    cell3.innerHTML = `<select name="Team_Division">
        <option value="">--Select--</option>
        <option value="Mixed">Mixed</option>
        <option value="Womens">Womens</option>
        <option value="BCS">BCS</option>
        <option value="Open">Open</option>
    </select>`;
};
// Service worker registration for PWA
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('{{ url_for('static', filename='service-worker.js') }}');
}
</script>
'''

@race_draw_bp.route('/race_draw', methods=['GET', 'POST'])
def race_draw():
    heat1 = heat2 = None
    errors = []
    duplicate_names = set()
    upload_success = False
    if request.method == 'POST':
        file = request.files['teams_csv']
        num_lanes = int(request.form['num_lanes'])
        teams = []
        if file:
            stream = io.StringIO(file.stream.read().decode("utf-8"))
            reader = csv.DictReader(stream)
            teams, errors, duplicate_names = validate_teams_csv(reader)
            if not errors and teams and num_lanes > 0:
                upload_success = True  # Set flag on successful upload
        if not errors and teams and num_lanes > 0:
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
    return render_template_string(
        HTML_FORM,
        errors=errors,
        upload_success=upload_success,
        heat1=heat1,
        heat2=heat2,
        duplicate_names=duplicate_names,
    )

@race_draw_bp.route('/race_draw/export_csv', methods=['POST'])
def export_csv():
    heat1 = session.get('heat1')
    heat2 = session.get('heat2')
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')

    # Write header
    writer.writerow(['Heat', 'Race', 'Lane', 'Team Name', 'Division','Place', 'time'])

    # Helper to write a heat
    def write_heat(heat, heat_label, race_offset=0):
        if not heat:
            return
        for race_idx, race in enumerate(heat, start=1):
            race_number = race_offset + race_idx
            for lane_idx, team in enumerate(race, start=1):
                row = [
                    heat_label if race_idx == 1 and lane_idx == 1 else '',
                    f'Race {race_number}' if lane_idx == 1 else '',
                    lane_idx,
                    team['Team Name'] if team else '',
                    team['Division'] if team else '',
                    '',  # Empty "Place" column
                    ''   # Empty "time" column
                ]
                writer.writerow(row)

    heat1_race_count = len(heat1) if heat1 else 0
    write_heat(heat1, 'Heat 1', race_offset=0)
    write_heat(heat2, 'Heat 2', race_offset=heat1_race_count)

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='heats.csv'
    )

@race_draw_bp.route('/race_draw_manual', methods=['GET', 'POST'])
def race_draw_manual():
    default_teams = [
        {'Team Name': 'Alon', 'Division': 'Mixed'},
        {'Team Name': 'Busting with Life', 'Division': 'BCS'},
        {'Team Name': 'City Dragons', 'Division': 'Mixed'},
        {'Team Name': 'Dragon Riders', 'Division': 'Mixed'},
        {'Team Name': 'Hauraki Blues', 'Division': 'Womens'},
        {'Team Name': 'Jaffettes', 'Division': 'Womens'},
        {'Team Name': 'Lion Pride', 'Division': 'Mixed'},
        {'Team Name': 'Lion Tsunami', 'Division': 'Mixed'},
        {'Team Name': 'Random Jaffas', 'Division': 'Mixed'},
        {'Team Name': 'The Pink Dragons', 'Division': 'BCS'},
        {'Team Name': 'Waitematā Warriors', 'Division': 'Mixed'},
        {'Team Name': 'Women of Steel', 'Division': 'Womens'},
        {'Team Name': 'Zombies', 'Division': 'Mixed'},
       
    ]
    teams = []
    heat1 = heat2 = None
    errors = []
    num_lanes = ''
    duplicate_names = set()
    # On GET, prepopulate; on POST, use submitted values
    if request.method == 'POST':
        # Read teams from form
        team_names = request.form.getlist('Team_Name')
        team_divisions = request.form.getlist('Team_Division')
        teams = [
            {'Team Name': name.strip(), 'Division': division.strip()}
            for name, division in zip(team_names, team_divisions)
            if name.strip()
        ]
        # Check for missing division if team name is present
        for name, division in zip(team_names, team_divisions):
            if name.strip() and not division.strip():
                errors.append(f"Please select division for team '{name.strip()}'.")

        # Duplicate check
        seen = set()
        duplicate_names = set()
        for team in teams:
            name = team['Team Name']
            if name in seen:
                duplicate_names.add(name)
            seen.add(name)
        # Validate num_lanes
        num_lanes = request.form.get('num_lanes', '')
        try:
            num_lanes = int(num_lanes)
        except Exception:
            errors.append("Number of lanes must be a number.")
            num_lanes = ''
        if not teams:
            errors.append("Please enter at least one team name and division.")
        if not errors and teams and num_lanes:
            heat1 = generate_heat_draw(teams.copy(), num_lanes)
            heat1_opponents = get_race_opponents(heat1)
            heat1_lanes = get_team_lanes(heat1)
            last_two_teams = get_last_two_race_teams(heat1)
            heat2 = generate_heat2_draw(teams, num_lanes, heat1_opponents, heat1_lanes, last_two_teams)
            session['manual_heat1'] = heat1
            session['manual_heat2'] = heat2
    else:
        teams = default_teams
        num_lanes = ''

    return render_template_string(
        """
        <!doctype html>
        <title>Create a Race Draw (Manual Entry)</title>
        <h2>Create a Race Draw (Manual Entry)</h2>
        <form method="post">
          <label>Enter Team Names and select Divisions:</label>
          <table border="1" cellpadding="4" style="margin-bottom:10px;">
            <tr>
              <th>#</th>
              <th>Team Name</th>
              <th>Division</th>
            </tr>
            {% for i in range(teams|length) %}
            <tr>
              <td>{{ i + 1 }}</td>
              <td>
                <input type="text" name="Team_Name" value="{{ teams[i]['Team Name'] }}" >
              </td>
              <td>
                <select name="Team_Division" >
                  {% set divval = teams[i]['Division'] %}
                  <option value="Mixed"  {% if divval == 'Mixed' %}selected{% endif %}>Mixed</option>
                  <option value="Womens" {% if divval == 'Womens' %}selected{% endif %}>Womens</option>
                  <option value="BCS"    {% if divval == 'BCS' %}selected{% endif %}>BCS</option>
                  <option value="Open"   {% if divval == 'Open' %}selected{% endif %}>Open</option>
                </select>
              </td>
            </tr>
            {% endfor %}
            {% for i in range(4 - teams|length) %}
            <tr>
              <td>{{ teams|length + i + 1 }}</td>
              <td><input type="text" name="Team_Name"></td>
              <td>
                <select name="Team_Division">
                  <option value="">--Select--</option>
                  <option value="Mixed">Mixed</option>
                  <option value="Womens">Womens</option>
                  <option value="BCS">BCS</option>
                  <option value="Open">Open</option>
                </select>
              </td>
            </tr>
            {% endfor %}
          </table>
          <button type="button" id="add-row-btn" class="file-btn" style="margin-bottom:10px;">+</button>
          <label>Add a new line for a team</label>                         
          <div style="height:8px;"></div>
                                  
          <label>If you want to delete a Team then just leave the line blank</label>
          <br>                                                                                     
          <input type="number" name="num_lanes" min="1" required placeholder="Enter Number of lanes" style="margin-top:12px; margin-bottom:12px;"><br>
          <input type="submit" value="Generate Race Draw for Mixed Divisional Heats" class="file-btn" style="margin-top:10px;">
          <div style="height:8px;"></div>
                                  <br>
          <Label>If you want to re-generate the list, enter in the number of lanes and click 'Generate....' again</label>
          <div style="height:8px;"></div>
          <label>If you see an 'EMPTY' in a team name for the draw, there is no error is is just an inform</label>
          <div style="height:8px;"></div>
          <label>If a team is highlighted in red, it means that team name is duplicated in the list</label>                            
        </form>
        {% if errors %}
          <div style="color: red;">
            <ul>
            {% for error in errors %}
              <li>{{ error }}</li>
            {% endfor %}
            </ul>
          </div>
        {% endif %}
        {% if heat1 %}
          <h3>--- Heat 1 Draw ---</h3>
          {% for race in heat1 %}
            <b>Race {{loop.index}}:</b>
            <table border="1" cellpadding="4" style="margin-bottom:10px;">
              <tr>
                <th>Lane</th>
                <th style="width:220px;">Team Name</th>
                <th>Division</th>
              </tr>
              {% for team in race %}
              <tr>
                <td>{{loop.index}}</td>
                <td style="width:220px;{% if team['Team Name'] in duplicate_names %} background-color: #ffcccc;{% endif %}">
                  {% if team and team['Team Name'] %}
                    {{ team['Team Name'] }}
                  {% else %}
                    <span style="color:red;">EMPTY</span>
                  {% endif %}
                </td>
                <td>{{team['Division'] if team else ""}}</td>
              </tr>
              {% endfor %}
            </table>
          {% endfor %}
          <h3>--- Heat 2 Draw ---</h3>
          {% for race in heat2 %}
            <b>Race {{heat1|length + loop.index}}:</b>
            <table border="1" cellpadding="4" style="margin-bottom:10px;">
              <tr>
                <th>Lane</th>
                <th style="width:220px;">Team Name</th>
                <th>Division</th>
              </tr>
              {% for team in race %}
              <tr>
                <td>{{loop.index}}</td>
                <td style="width:220px;">
                  {% if team and team['Team Name'] %}
                    {{ team['Team Name'] }}
                  {% else %}
                    <span style="color:red;">EMPTY</span>
                  {% endif %}
                </td>
                <td>{{team['Division'] if team else ""}}</td>
              </tr>
              {% endfor %}
            </table>                      
          {% endfor %}
        {% endif %}
        {% if heat1 and heat2 %}
            <label>Ensure you check the last two races of the 'Heat 1' and the first two races of 'Heat 2' so the teams are not the same</label>                             
            <form action="{{ url_for('race_draw.export_manual_csv') }}" method="post" style="margin-top:20px;">
              <button type="submit" class="file-btn">Export as CSV</button>
           </form>
         {% endif %}                                  
        <form action="{{ url_for('selector') }}" method="get" style="margin-top:20px;">
          <button type="submit" style="background-color:#6c757d; color:white; padding:8px 16px; border:none; border-radius:4px;">
            Back to Selector Page
          </button>
        </form>
        <style>
        .file-btn {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            box-shadow: 2px 2px 8px rgba(0,123,255,0.3);
            cursor: pointer;
            font-size: 1em;
        }
        .file-btn:hover {
            outline: 2px solid #0056b3;
            box-shadow: 2px 2px 12px rgba(0,123,255,0.5);
        }
        </style>
        <script>
document.getElementById('add-row-btn').onclick = function() {
    // Find the table above the button
    var table = this.previousElementSibling;
    // Insert a new row at the end
    var row = table.insertRow(-1);
    // The new number is the current number of rows minus the header row
    var number = table.rows.length - 1;
    var cell1 = row.insertCell(0);
    var cell2 = row.insertCell(1);
    var cell3 = row.insertCell(2);
    cell1.innerHTML = number;
    cell2.innerHTML = '<input type="text" name="Team_Name">';
    cell3.innerHTML = `<select name="Team_Division">
        <option value="">--Select--</option>
        <option value="Mixed">Mixed</option>
        <option value="Womens">Womens</option>
        <option value="BCS">BCS</option>
        <option value="Open">Open</option>
    </select>`;
};
// Service worker registration for PWA
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('{{ url_for('static', filename='service-worker.js') }}');
}
</script>
    """,
        heat1=heat1, heat2=heat2, errors=errors, teams=teams, num_lanes=num_lanes, duplicate_names=duplicate_names
    )

@race_draw_bp.route('/race_draw/download_template')
def download_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Team Name', 'Division'])
    writer.writerow(['Team 1', 'Mixed'])
    writer.writerow(['Team 2', 'Mixed'])
    writer.writerow(['Team 3', 'Womens'])
    writer.writerow(['Team 4', 'BCS'])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='race_draw_template.csv'
    )

@race_draw_bp.route('/race_draw_manual/export_csv', methods=['POST'])
def export_manual_csv():
    heat1 = session.get('manual_heat1')
    heat2 = session.get('manual_heat2')
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')

    writer.writerow(['Heat', 'Race', 'Lane', 'Team Name', 'Division', 'Place', 'time'])

    def write_heat(heat, heat_label, race_offset=0):
        if not heat:
            return
        for race_idx, race in enumerate(heat, start=1):
            race_number = race_offset + race_idx
            for lane_idx, team in enumerate(race, start=1):
                row = [
                    heat_label if race_idx == 1 and lane_idx == 1 else '',
                    f'Race {race_number}' if lane_idx == 1 else '',
                    lane_idx,
                    team['Team Name'] if team else '',
                    team['Division'] if team else '',
                    '',  # Place (empty)
                    ''   # time (empty)
                ]
                writer.writerow(row)

    heat1_race_count = len(heat1) if heat1 else 0
    write_heat(heat1, 'Heat 1', race_offset=0)
    write_heat(heat2, 'Heat 2', race_offset=heat1_race_count)

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='manual_heats.csv'
    )

@race_draw_bp.route('/manifest.json')
def manifest():
    return {
        "name": "Race Draw Generator",
        "short_name": "RaceDraw",
        "start_url": "/race_draw",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#007bff",
        "icons": [
            {
                "src": "/static/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }
