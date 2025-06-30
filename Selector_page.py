from flask import Flask, render_template_string, url_for
from race_draw_blueprint import race_draw_bp
from finals_draw_blueprint import finals_draw_bp

app = Flask(__name__)
app.secret_key = "your_super_secret_key"  # <-- Add this line

app.register_blueprint(race_draw_bp)
app.register_blueprint(finals_draw_bp)

SELECTOR_HTML = '''
<!doctype html>
<html>
<head>
  <title>ADBA Race Draw Generator</title>
  <link rel="manifest" href="{{ url_for('static', filename='manifest.json') }}">
  <meta name="theme-color" content="#007bff">
  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('{{ url_for('static', filename='service-worker.js') }}');
    }
  </script>
</head>
<body>
<img src="{{ url_for('static', filename='ADBALogo.png') }}" alt="Logo" style="max-width:300px; display:block; margin-bottom:16px;margin-left:200">
<h2>Please choose an action:</h2>
<div style="width:400px; margin-left:0;">
  <form action="{{ url_for('race_draw.race_draw') }}" method="get" style="margin-bottom:12px;">
      <button type="submit" style="width:100%; min-width:200px; background-color:#007bff; color:white; padding:10px 20px; border:none; border-radius:4px; text-align:left;">Create a Race Draw from Template</button>
  </form>
  <form action="{{ url_for('race_draw.race_draw_manual') }}" method="get" style="margin-bottom:12px;">
      <button type="submit" style="width:100%; min-width:200px; background-color:#17a2b8; color:white; padding:10px 20px; border:none; border-radius:4px; text-align:left;">Create a Race Draw Manually</button>
  </form>
  <form action="{{ url_for('finals_draw.finals_draw') }}" method="get">
      <button type="submit" style="width:100%; min-width:200px; background-color:#28a745; color:white; padding:10px 20px; border:none; border-radius:4px; text-align:left;">Create a Finals Draw</button>
  </form>
<h2>Current rules with heat generation:</h2>
<lable>1. Teams, where possible, will not race the same teams in consecutive heats.</lable><br>
<div style="height:8px;"></div>
<lable>2. Teams, where possible, will not race in the same lane.</lable><br>
<div style="height:8px;"></div>
<lable>3. Teams, where possible, who raced in the last two races of the preceding heat will not race in first two races of the next heat.</lable><br>
<h2>Current calculation for finals time:</h2>
<lable>1. Times from heat 1 and heat 2 are combined.</lable><br>
  </div>
</body>
</html>
'''

FINALS_UPLOAD_HTML = '''
<!doctype html>
<title>Finals Upload Page</title>
<h2>Upload your finals data:</h2>
<form action="{{ url_for('finals_draw.handle_upload') }}" method="post" enctype="multipart/form-data">
    <input type="file" name="file" accept=".csv, .xlsx" required>
    <button type="submit" style="background-color:#007bff; color:white; padding:10px 20px; border:none; border-radius:4px;">Upload</button>
</form>
<form action="{{ url_for('selector') }}" method="get" style="margin-top:20px;">
    <button type="submit" style="background-color:#6c757d; color:white; padding:8px 16px; border:none; border-radius:4px;">Back to Selector Page</button>
</form>
'''

@app.route('/')
def selector():
    return render_template_string(SELECTOR_HTML)

if __name__ == '__main__':
    app.run(debug=True)