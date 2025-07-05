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
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="manifest" href="{{ url_for('static', filename='manifest.json') }}">
  <meta name="theme-color" content="#007bff">
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 20px;
      background-color: #1a1a1a;
      color: #ffffff;
    }
    .container {
      max-width: 800px;
      margin: 0 auto;
      background-color: #2d2d2d;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    .logo {
      max-width: 100%;
      height: auto;
      display: block;
      margin: 0 auto 20px auto;
    }
    .button-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 30px;
    }
    .btn {
      width: 100%;
      padding: 15px 20px;
      border: none;
      border-radius: 6px;
      font-size: 16px;
      cursor: pointer;
      transition: all 0.3s ease;
      text-align: left;
      font-weight: 500;
    }
    .btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .btn-primary { background-color: #007bff; color: white; }
    .btn-info { background-color: #17a2b8; color: white; }
    .btn-success { background-color: #28a745; color: white; }
    .rules-section {
      margin-top: 30px;
      padding: 20px;
      background-color: #3d3d3d;
      border-radius: 6px;
      border-left: 4px solid #007bff;
    }
    .rule-item {
      margin-bottom: 12px;
      line-height: 1.5;
    }
    h2 {
      color: #ffffff;
      margin-bottom: 20px;
      font-size: 1.5rem;
    }
    h3 {
      color: #ffffff;
      margin-bottom: 15px;
      font-size: 1.2rem;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
      body {
        padding: 10px;
      }
      .container {
        padding: 15px;
      }
      .logo {
        max-width: 250px;
      }
      h2 {
        font-size: 1.3rem;
      }
      h3 {
        font-size: 1.1rem;
      }
      .btn {
        padding: 12px 16px;
        font-size: 15px;
      }
    }
    
    @media (max-width: 480px) {
      body {
        padding: 5px;
      }
      .container {
        padding: 10px;
      }
      .logo {
        max-width: 200px;
      }
      h2 {
        font-size: 1.2rem;
      }
      .btn {
        padding: 10px 14px;
        font-size: 14px;
      }
    }
  </style>
  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('{{ url_for('static', filename='service-worker.js') }}');
    }
  </script>
</head>
<body>
  <div class="container">
    <img src="{{ url_for('static', filename='ADBALogo.png') }}" alt="ADBA Logo" class="logo">
    <h2>Please choose an action:</h2>
      <form action="{{ url_for('race_draw.race_draw') }}" method="get">
        <button type="submit" class="btn btn-primary">Create a Race Draw from Template</button>
      </form>
      <form action="{{ url_for('race_draw.race_draw_manual') }}" method="get">
        <button type="submit" class="btn btn-info">Create a Race Draw Manually</button>
      </form>
      <form action="{{ url_for('finals_draw.finals_draw') }}" method="get">
        <button type="submit" class="btn btn-success">Create a Finals Draw</button>
      </form>
    
    <div class="rules-section">
      <h2>Current rules with heat generation:</h2>
      <div class="rule-item">Teams, where possible, will not race the same teams in consecutive heats or the same lanes.</div>
      <div class="rule-item">Teams, where possible, who raced in the last two races of the preceding heat will not race in first two races of the next heat.</div>
      <div class="rule-item">Times from Heat 1 and Heat 2 are combined for the Finals time.</div>
    </div>
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
    # Force restart - change made to ensure reload
    app.run(debug=True, host='127.0.0.1', port=5000)
