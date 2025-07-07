from flask import Blueprint, render_template_string, request, send_file, url_for, redirect, session, flash
from io import StringIO, BytesIO
from collections import defaultdict
import csv
import io

finals_draw_bp = Blueprint('finals_draw', __name__)

FINALS_UPLOAD_HTML = '''
<!doctype html>
<html>
<head>
  <title>Finals Draw Creation</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="{{ url_for('static', filename='Shared.css') }}">
  <style>
    .container {
      max-width: 1200px;
      margin: 0 auto;
      background-color: #2d2d2d;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    .form-section {
      margin-bottom: 30px;
      padding: 20px;
      background-color: #3d3d3d;
      border-radius: 6px;
      border-left: 4px solid #28a745;
    }
    .input-group {
      margin-bottom: 16px;
    }
    .input-group label {
      display: block;
      margin-bottom: 8px;
      font-weight: 500;
      color: #ffffff;
    }
    .example-image {
      margin: 16px 0;
      border: 2px solid #555;
      border-radius: 4px;
    }
    .file-upload-area {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      margin: 16px 0;
    }
    .data-table, .summary-table, .finals-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 20px;
      overflow-x: auto;
      display: block;
      white-space: nowrap;
    }
    .data-table th, .data-table td,
    .summary-table th, .summary-table td,
    .finals-table th, .finals-table td {
      border: 1px solid #555;
      padding: 8px;
      text-align: left;
    }
    .data-table th, .summary-table th, .finals-table th {
      font-weight: 600;
      color: #ffffff;
    }
    .data-table th { background-color: #4d4d4d; position: sticky; top: 0; }
    .summary-table th { background-color: #2d4d2d; }
    .finals-table th { background-color: #5d4e2d; }
    .data-table input[type="text"] {
      width: 100%;
      padding: 4px;
      border: 1px solid #555;
      border-radius: 3px;
      font-size: 14px;
      background-color: #4d4d4d;
      color: #ffffff;
    }
    .success-message {
      background-color: #2d4d2d;
      color: #4caf50;
      padding: 15px;
      border-radius: 4px;
      border: 1px solid #4a8b4a;
      margin: 16px 0;
      font-weight: bold;
    }
    .info-section {
      background-color: #2d4a5d;
      color: #17a2b8;
      padding: 15px;
      border-radius: 4px;
      border: 1px solid #4a7c95;
      margin: 16px 0;
    }
    .file-name-display {
      margin-top: 12px;
      color: #4caf50;
      font-weight: bold;
      padding: 8px;
      background-color: #2d4d2d;
      border-radius: 4px;
      display: none;
    }
    input[type="file"] {
      display: none;
    }
    /* Responsive and other page-specific styles ... */
    @media (max-width: 480px) {
      /* Make Lane and Division columns as small as possible */
      .finals-table th:nth-child(1),
      .finals-table td:nth-child(1) {
        width: 22px !important;
        min-width: 16px !important;
        max-width: 30px !important;
        padding-left: 1px;
        padding-right: 1px;
        text-align: center;
      }
      .finals-table th:nth-child(2),
      .finals-table td:nth-child(2) {
        width: 40px !important;
        min-width: 30px !important;
        max-width: 60px !important;
        padding-left: 1px;
        padding-right: 1px;
        text-align: center;
      }
      .finals-table th:nth-child(3),
      .finals-table td:nth-child(3) {
        width: 80px !important;
        min-width: 50px !important;
        max-width: 120px !important;
        padding-left: 2px;
        padding-right: 2px;
        white-space: normal !important;
        word-break: break-word !important;
        overflow-wrap: break-word !important;
      }
      .finals-table th:nth-child(4),
      .finals-table td:nth-child(4) {
        white-space: nowrap !important;   /* Prevent wrapping */
        overflow-x: auto;
        text-overflow: ellipsis;
        max-width: 90px;                  /* Adjust as needed for your layout */
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <h2>Create a Finals Draw</h2>
    
    <div class="form-section">
      <div class="info-section">
        <div>• Upload with or without places and times</div>
        <div>• You are then able to edit the places and time</div>
        <div>• Example format below:</div>
      </div>
      
      <img src="{{ url_for('static', filename='heats and times.png') }}" alt="Example Format" class="example-image">
      
      <form method="post" enctype="multipart/form-data">
        <!-- File upload area -->
        <div class="file-upload-area">
          <label for="finals_csv" class="file-btn">1. Choose Upload File</label>
          <input type="file" id="finals_csv" name="finals_csv" required onchange="document.getElementById('file-name').textContent = this.files[0]?.name || ''; document.getElementById('file-name').style.display = this.files[0] ? 'block' : 'none';">
          <input type="submit" value="2. Upload and Generate Finals" class="file-btn">
        </div>
        <div id="file-name" class="file-name-display"></div>
      </form>
    </div>

    
    {% if upload_success %}
      <div class="success-message">
        Upload successful!
      </div>
    {% endif %}

    {% if table %}
      <h3>Edit Places & Times</h3>
      <div class="info-section">
        <div>• Here you can edit the place and time in the table below</div>
        <div>• Just hit save at the bottom of the table when you are done</div>
        <div>• To have the finals draw created a time is needed for at least 1 team across both heats</div>
      </div>
      
      <form method="post" action="#combined-times">
        <textarea name="csv_content" hidden>{{ csv_content }}</textarea>
        <div class="data-table table-scroll-x">
          <table>
            <tr>
              <th>Heat</th>
              <th>Race</th>
              <th>Lane</th>
              <th>Team Name</th>
              <th>Division</th>
              <th style="width:80px;">Place</th>
              <th style="width:100px;">Time</th>   
            </tr>
            {% for row in table %}
              {% set i = loop.index0 %}
              <tr>
                <td>{{ row[0] }}</td>
                <td>{{ row[1] }}</td>
                <td>{{ row[2] }}</td>
                <td>{{ row[3] }}</td>
                <td>{{ row[4] }}</td>
                <td style="width:80px;">
                  <input type="text" name="place_{{ i }}" value="{{ request.form.get('place_' ~ i, row[5]) }}">
                </td>
                <td style="width:100px;">
                  <input type="text" name="time_{{ i }}" value="{{ request.form.get('time_' ~ i, row[6]) }}">
                </td>
              </tr>
            {% endfor %}
          </table>
        </div>
        
        <!-- Save Times button -->
        <button type="submit" name="edit_times" value="1" class="upload-btn">Save Times</button>
      </form>
    {% endif %}
    
    {% if table %}
      <!-- Flash messages -->
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          <div class="flashes">
            {% for category, message in messages %}
              <div class="flash-message {{ category }}">{{ message }}</div>
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}

      <!-- Save/Load Table Section -->
      <form method="post" style="margin-bottom:16px; display:flex; gap:8px; align-items:center;">
        <input type="text" name="save_table_name" placeholder="Enter table name to save/load" style="padding:4px; border-radius:4px; border:1px solid #555; background:#444; color:#fff;">
        <button type="submit" name="action" value="save_table" class="file-btn" style="min-width:90px;">Save Table</button>
        {% if saved_tables %}
          <select name="load_table_name" style="padding:4px; border-radius:4px; border:1px solid #555; background:#444; color:#fff;">
            <option value="">Select saved table</option>
            {% for name in saved_tables %}
              <option value="{{ name }}">{{ name }}</option>
            {% endfor %}
          </select>
          <button type="submit" name="action" value="load_table" class="file-btn" style="min-width:90px;">Load Table</button>
        {% endif %}
      </form>
    {% endif %}
  </div>
  
  
</body>
</html>'''

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
    upload_success = False
    saved_tables = session.get('saved_tables', {})

    if request.method == 'POST':
        # Handle Save Table
        if request.form.get('action') == 'save_table':
            save_name = request.form.get('save_table_name', '').strip()
            if save_name:
                saved_tables[save_name] = csv_content
                session['saved_tables'] = saved_tables
                flash(f"Table saved as '{save_name}'", "success")
            else:
                flash("Please enter a name to save the table.", "error")

        # Handle Load Table
        elif request.form.get('action') == 'load_table':
            load_name = request.form.get('load_table_name', '').strip()
            if load_name and load_name in saved_tables:
                csv_content = saved_tables[load_name]
                flash(f"Loaded table '{load_name}'", "success")
            else:
                flash("Please select a valid table to load.", "error")

        # File upload and editing
        if 'finals_csv' in request.files and request.files['finals_csv']:
            file = request.files['finals_csv']
            csv_content = file.read().decode('utf-8')
            if csv_content:
                upload_success = True
        elif 'csv_content' in request.form:
            csv_content = request.form['csv_content']
            # Update times if editing
            if 'edit_times' in request.form:
                reader = csv.reader(StringIO(csv_content))
                rows = [row for row in reader if any(cell.strip() for cell in row)]
                if rows:
                    header = rows[0]
                    time_idx = header.index('Time') if 'Time' in header else 6
                    place_idx = header.index('Place') if 'Place' in header else 5
                    for i, row in enumerate(rows[1:]):
                        new_place = request.form.get(f"place_{i}", "").strip()
                        new_time = request.form.get(f"time_{i}", "").strip()
                        if place_idx < len(row):
                            row[place_idx] = new_place
                        if time_idx < len(row):
                            row[time_idx] = new_time
                    output = io.StringIO()
                    writer = csv.writer(output)
                    for row in rows:
                        writer.writerow(row)
                    csv_content = output.getvalue()
            for key in request.form:
                if key.startswith('lanes_'):
                    division = key.replace('lanes_', '')
                    try:
                        lanes_per_division[division] = int(request.form[key])
                    except Exception:
                        lanes_per_division[division] = None

    # Always re-parse the (possibly updated) csv_content to rebuild tables
    if csv_content:
        table = []
        header = header if isinstance(header, list) else []
        team_times = {}
        team_divisions = {}
        current_heat = None
        division_groups = defaultdict(list)
        finals_draw = {}
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

    # Recalculate last_edit_race_number directly from the current table
    last_edit_race_number = 0
    race_col_index = 1  # Assuming 2nd column is 'Race'
    for row in table:
        try:
            race_num = int(row[race_col_index])
            if race_num > last_edit_race_number:
                last_edit_race_number = race_num
        except (ValueError, IndexError):
            continue

    session['last_edit_race_number'] = last_edit_race_number

    header = header if isinstance(header, list) else []
    
    return render_template_string(
        FINALS_UPLOAD_HTML + '''
    <div class="container">
      {% if division_groups %}
        <a id="combined-times"></a>
        <h3>Combined Times by Division (Heat 1 + Heat 2)</h3>
        <div class="info-section">
          <div>• The table below shows the combined times for each team in each division, ranked first to last</div>
          <div>• For this calculation the times are added together</div>
        </div>
        
        {% for division, rows in division_groups.items() %}
          <h4>{{ division }}</h4>
          <div class="summary-table">
            <table>
              <tr>
                <th>Position</th>
                <th style="width:220px;">Team Name</th>
                <th>Division</th>
                <th>Heat 1 Time</th>
                <th>Heat 2 Time</th>
                <th>Total Time</th>
              </tr>
              {% for row in rows %}
                <tr>
                  <td>{{ row[0] }}</td>
                  <td style="width:220px;">{{ row[1] }}</td>
                  <td>{{ row[2] }}</td>
                  <td>{{ row[3] }}</td>
                  <td>{{ row[4] }}</td>
                  <td>{{ row[5] }}</td>
                </tr>
              {% endfor %}
            </table>
          </div>
        {% endfor %}
        
        <hr style="margin: 30px 0; border: 1px solid #555;">
        
        <a id="finals-draw"></a>
        <h3>Finals Draw</h3>
        <div class="info-section">
          To create the finals draw, please enter the number of lanes for each division.
        </div>
        
        <form method="post" action="#finals-draw">
          <textarea name="csv_content" hidden>{{ csv_content }}</textarea>
          <div class="lanes-input-group">
            {% for division, rows in division_groups.items() %}
              <div class="lanes-input-item">
                <label for="lanes_{{ division }}">Number of lanes for {{ division }}:</label>
                <input type="number" name="lanes_{{ division }}" min="1" required>
              </div>
            {% endfor %}
          </div>
          <!-- Generate Finals Draw button -->
          <button type="submit" class="upload-btn">Generate Finals Draw</button>
        </form>
      {% endif %}

      {% if finals_draw %}
        {% set ns = namespace(global_race_number=race_offset) %}
        {% for division, races in finals_draw.items() %}
          <h4>Finals Draw - {{ division }}</h4>
          {% for race in races %}
            {% set ns.global_race_number = ns.global_race_number + 1 %}
            <div style="margin-bottom:20px;">
              <b>Race {{ ns.global_race_number }}</b>
              <div class="finals-table table-scroll-x">
                <table>
                  <tr>
                    <th>Lane</th>
                    <th>Position</th>
                    <th style="width:220px;">Team Name</th>
                    <th style="width:120px;">Time</th>
                  </tr>
                  {% for lane_idx in range(race|length) %}
                    <tr>
                      <td>{{ lane_idx + 1 }}</td>
                      <td>{{ race[lane_idx][0] if race[lane_idx] else '' }}</td>
                      <td style="width:220px;">{{ race[lane_idx][1] if race[lane_idx] else '' }}</td>
                      <td style="width:120px;">
                        {{ race[lane_idx][6] if race[lane_idx] and race[lane_idx]|length > 6 else '' }}
                      </td>
                    </tr>
                  {% endfor %}
                </table>
              </div>
            </div>
          {% endfor %}
        {% endfor %}
        
        <form action="{{ url_for('finals_draw.exportfinal_csv') }}" method="post" style="margin-top:20px;">
          <!-- Export Finals Draw as CSV button -->
          <button type="submit" class="file-btn">Export Finals Draw as CSV</button>
        </form>
      {% endif %}
      
      <form action="{{ url_for('selector') }}" method="get" style="margin-top:20px;">
        <button type="submit" style="background-color:#6c757d; color:white; padding:10px 20px; border:none; border-radius:4px; transition:all 0.3s ease;">
          Back to Selector Page
        </button>
      </form>
    </div>
    
    <link rel="manifest" href="{{ url_for('static', filename='manifest.json') }}">
    <meta name="theme-color" content="#007bff">
    <script>
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('{{ url_for('static', filename='service-worker.js') }}');
      }

      // If the URL contains the anchor, scroll to it
      if (window.location.hash === "#finals-draw") {
        document.getElementById("finals-draw").scrollIntoView({behavior: "smooth"});
      }
    </script>
  </body>
  </html>
''',
        table=table,
        header=header,
        division_groups=division_groups,
        finals_draw=finals_draw,
        csv_content=csv_content,
        last_edit_race_number=last_edit_race_number,
        race_offset=last_edit_race_number,  # Use this as the offset for finals
        upload_success=upload_success,  # Pass to template
        saved_tables=saved_tables.keys()  # Pass saved table names to template
    )

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