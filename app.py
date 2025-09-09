import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, flash, abort
import os
import smtplib
from email.mime.text import MIMEText
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


#from datetime import timedelta
# app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)  # or days=1
#Thus is for the time for session after login, directly see session permanent=true line

# Create a Flask app
app = Flask(__name__)

# Database connection (Render provides DATABASE_URL in env vars)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sustainabos_db_user:iNmAcRXSGKOSHgvQGzltdBUSMcDz0dZN@dpg-d2r54315pdvs738sd3i0-a/sustainabos_db")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- models ---
class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vessel_name = db.Column(db.String(100))
    date = db.Column(db.Date)
    responses = db.Column(db.JSON)

class Metric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    metric_name = db.Column(db.String(100))
    value = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=db.func.now())

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(50))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.now())

class DeviceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100))
    vessel_name = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=db.func.now())

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class User2(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)


# To ignore warnings of openxyl, excel sheet weird format
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# For the password later
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-now")  # set a real value in Render later

# --- Simple users (change these!) ---
users = {
    "Axel": "BOSaxfa*",
    "admin": "secret123",
    "Mohit": "BOSmosa*",
    "Florent": "BOSflki*",
    "Julian": "BOSjuoh*",
    "Richard": "BOSrihi*",
    "Ernest": "BOSerlo*",
    "Sundar": "BOSsucc*",
    "Ser Boon": "BOSseta*",
    "Siva": "BOSsira*",
    "Alessandro":"BOSalba*",
}

def seed_users():
    # hardcoded users (your current dictionary)
    default_users = {
        "Axel": "BOSaxfa*",
        "admin": "secret123",
        "Mohit": "BOSmosa*",
        "Florent": "BOSflki*",
        "Julian": "BOSjuoh*",
        "Richard": "BOSrihi*",
        "Ernest": "BOSerlo*",
        "Sundar": "BOSsucc*",
        "Ser Boon": "BOSseta*",
        "Siva": "BOSsira*",
        "Alessandro": "BOSalba*",
    }

    for username, password in default_users.items():
        existing_user = User2.query.filter_by(username=username).first()
        if not existing_user:
            hashed_pw = generate_password_hash(password)
            new_user = User2(username=username, password_hash=hashed_pw)
            db.session.add(new_user)

    db.session.commit()



# Load the Excel file with specified column names starting from row 8 and column B
file_path = 'Vessel_Device_Installation_Tracker NV.xlsx'
column_names = ['Vessel Name/ ID', 'Spec', 'Devices', 'Installation Status', 'Date of Installation', 'Savings/year (fuel efficiency)', 'Savings/year (Maitenance)', 'Co2 savings ton/year']
df = pd.read_excel(file_path, engine='openpyxl', names=column_names, skiprows=7, usecols="B:I")

list_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Tracker', skiprows=6, nrows=466, usecols="B:J")

# Load the summary sheet
summary_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=0,  nrows=16, usecols="A:F")

summary2_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=15,  nrows=3, usecols="B:C")

summary3_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=0,  nrows=4, usecols="I:K")

# --- KPIs for Home (Summary!C21:C23) ---
# We read the sheet without headers so we can address Excel cells by (row-1, col-1)
summary_raw = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', header=None)

def _num(i, j):
    v = pd.to_numeric(summary_raw.iat[i, j], errors='coerce')
    return 0 if pd.isna(v) else float(v)

kpi_devices_raw     = int(_num(22, 2))   # C23 (row index -1, col index -1)
kpi_gain_raw  = _num(4, 9) *100       # J5
kpi_co2_raw         = _num(21, 2)        # C22

# Clean / round:
kpi_devices = int(round(kpi_devices_raw))            # integer count
kpi_gain = round(kpi_gain_raw, 2)        # two decimal for %
kpi_co2 = round(kpi_co2_raw, 0)                      # zero decimal for tonnes

# Prepare a list for the template (we’ll animate these later)
kpis = [
    {"title": "Initiatives", "value": kpi_devices,    "suffix": "",
        "back": ["8 initiatives certified", "7 initiatives on POC"]},
    {"title": "2025 Fuel Gain",        "value": kpi_gain, "suffix": "%",
        "back": ["Scope 1 Only. Goal 2026:", "20% Fuel savings"]},
    {"title": "CO₂ Savings",       "value": kpi_co2,        "suffix": " t",
        "back": ["Expected savings", "based on fuel savings"]},
]

# --- KPIs for KPI's section ---
# --- KPIs for KPI Section (Summary!J7, J8, J4) ---
kpi_tfc_raw       = _num(6, 9)   # J7
kpi_vessels_raw   = _num(7, 9)   # J8
kpi_update_raw    = _num(3, 9)*100   # J4

# Clean
kpi_tfc = int(round(kpi_tfc_raw))
kpi_vessels = int(round(kpi_vessels_raw))
kpi_update = int(round(kpi_update_raw))   # probably a string/date? keep as is. If not check

# Prepare for template
kpis_section = [
    {"title": "Last 12 months TFC", "value": kpi_tfc, "suffix": "t"},
    {"title": "Number of Vessels", "value": kpi_vessels, "suffix": ""},
    {"title": "Updated Info", "value": kpi_update, "suffix": "%"},
]

#print(kpis_section)

def get_vessel_summary(vessel_name):

    #print(list_df.iloc[:, 1])
   
    # Find the row index where vessel_name appears in column A
    start_idx = list_df[list_df.iloc[:, 1] == vessel_name].index
    if len(start_idx) == 0:
        return None  # Vessel not found

    #print(start_idx)

    start = start_idx[0]  # First occurrence
    end = start + 1

    # Loop to find the next non-empty cell in column A
    while end < len(list_df) and pd.isna(list_df.iloc[end, 0]):
        end += 1

    # Extract the relevant part of the DataFrame
    summaryBIS_df = list_df.iloc[start:end].copy()
    #print(summaryBIS_df)
    return summaryBIS_df

@app.route('/get_vessel_summary', methods=['POST'])
def get_vessel_summary_route():
    vessel_name = request.json.get('vesselName')
    summaryBIS_df = get_vessel_summary(vessel_name)

    # Replace NaNs with empty strings
    summaryBIS_df = summaryBIS_df.fillna('')
    #print(summaryBIS_df)

    # Remove unnamed columns (those usually from index column)
    column_names2 = [
        'N',
        'Vessel Name/ ID',
        'Spec',
        'Devices',
        'Installation Status',
        'Date of Installation',
        'Savings/year (fuel efficiency)',
        'Savings/year (Maitenance)',
        'Co2 savings ton/year' ]
    summaryBIS_df.columns = column_names2

    # Return as clean HTML
    return summaryBIS_df.to_html(index=False, classes='table table-bordered table-striped', border=0)

def get_device_summary(device_name):

    # TO DO

    # print(list_df.iloc[:, 3])
    # For debug
    # print(device_name)
    # filtered_df = list_df[list_df.iloc[:, 3] == device_name].copy()
    # print(filtered_df)

    # Step 1: Filter relevant rows
    filtered_df = list_df[
        (list_df.iloc[:, 3] == device_name) &
        (list_df.iloc[:, 4].isin(["Done", "In Process"]))
    ].copy()
    #print(filtered_df)

    # Step 2: For each row, find the corresponding vessel name by looking upwards
    vessel_names = []
    for idx in filtered_df.index:
        vessel_name = None
        search_idx = idx
        while search_idx >= 0:
            val = list_df.iloc[search_idx, 1]  # Column C is index 1
            if pd.notna(val):
                vessel_name = val
                break
            search_idx -= 1
        vessel_names.append(vessel_name)

    #print(vessel_names)

    # Step 3: Add this info to the result
    filtered_df.insert(0, "Vessel Name", vessel_names)  #Insert en position 0 ? Oui
    # print(filtered_df)

    # Optional: Keep only the meaningful columns
    return filtered_df[["Vessel Name", filtered_df.columns[4], filtered_df.columns[5],filtered_df.columns[6],filtered_df.columns[7],filtered_df.columns[8],filtered_df.columns[9]]]  # Vessel, Device, Status

    #print(filtered_df)
    return filtered_df

@app.route('/get_device_summary', methods=['POST'])
def get_device_summary_route():
    device_name = request.json.get('deviceName')
    filtered_df = get_device_summary(device_name)

    # Replace NaNs with empty strings
    filtered_df = filtered_df.fillna('').infer_objects(copy=False)
    #print(filtered_df)

    # Remove unnamed columns (those usually from index column)
    column_names3 = [
        'Vessel Name',
        'Devices',
        'Installation Status',
        'Date of Installation',
        'Savings/year (fuel efficiency)',
        'Savings/year (Maitenance)',
        'Co2 savings ton/year' ]
    filtered_df.columns = column_names3
    #print(filtered_df)

    # Return as clean HTML
    return filtered_df.to_html(index=False, classes='table table-bordered table-striped', border=0)


#summaryBIS_df = get_vessel_summary("Britoil 80")
#print(summaryBIS_df)
#M=summaryBIS_df.dropna().tolist()
#print(M)

# Load the list of vessel
listvessel_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=24,  nrows=73, usecols="A")

# Load the list of devices
listdevice_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=1,  nrows=15, usecols="A")
#print(listdevice_df)


       # vessel_names = listvessel_df.dropna().tolist()
# print(listvessel_df)
# print(listvessel_df.columns)

# Filter the relevant vessels
vessels_of_interest = df[df['Vessel Name/ ID'].astype(str).str.contains('Britoil|ENA Habitat|BOS|Lewek Hydra|Nautical Aisia|Nautical Anisha|Paragon Sentinel', na=False)]

# Extract relevant columns
vessel_devices = vessels_of_interest[['Vessel Name/ ID', 'Devices', 'Installation Status', 'Savings/year (fuel efficiency)', 'Savings/year (Maitenance)', 'Co2 savings ton/year']]

# Convert all savings columns to numeric, forcing errors to NaN
vessel_devices['Savings/year (fuel efficiency)'] = pd.to_numeric(vessel_devices['Savings/year (fuel efficiency)'], errors='coerce')
vessel_devices['Savings/year (Maitenance)'] = pd.to_numeric(vessel_devices['Savings/year (Maitenance)'], errors='coerce')
vessel_devices['Co2 savings ton/year'] = pd.to_numeric(vessel_devices['Co2 savings ton/year'], errors='coerce')

# Calculate total savings for each vessel
vessel_devices['Total Savings'] = vessel_devices['Savings/year (fuel efficiency)'].fillna(0) + vessel_devices['Savings/year (Maitenance)'].fillna(0) + vessel_devices['Co2 savings ton/year'].fillna(0)

# Get the top 10 vessels with the best performance
top_vessels = vessel_devices.groupby('Vessel Name/ ID')['Total Savings'].sum().nlargest(10).reset_index()

# Create a bar chart for the top 10 vessels
plt.figure(figsize=(10, 6))
plt.bar(top_vessels['Vessel Name/ ID'], top_vessels['Total Savings'], color='blue')
plt.xlabel('Vessel Name')
plt.ylabel('Total Savings')
plt.title('Top 10 Vessels with Best Performance')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('static/top_vessels_chart.png')

#region HTML section
# HTML template for the website with improved design and images
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>SustainaBOS</title>
    <link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}" type="image/x-icon">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        body { font-family: Arial, sans-serif; background-color: #E8F5E9; margin: 0; padding: 0; }
        .container { width: 80%; margin: auto; overflow: hidden; }
        header { background: #D0E8D0; color: #800080; padding-top: 20px; min-height: auto; border-bottom: #800080 2px solid; }
        header a { color: #800080; text-decoration: none; text-transform: none; font-size: 16px; font-weight: bold;}
        header ul { padding: 0; list-style: none; }
        header li { display: inline; padding: 0 10px 0 20px; }
        header #branding { float: left; }
        header #branding h1 { font-size: 19px; }
        header nav { float: right; margin-top: 10px; }
        .menu a { margin-right: 20px; text-decoration: none; color: #800080; font-weight: bold; }
        .menu a:hover { color: #0779e4; }
        .content { padding: 20px; background-color: #fff; border-radius: 5px; margin-top: 20px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #0779e4; color: white; }
        h2 { color: #333; }
        .hidden { display: none; }
        .show { display: table-row-group; }
        
        table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        box-shadow: 0 2px 3px rgba(0,0,0,0.1);
        }
        th, td {
        border: 1px solid #ddd;
        padding: 12px;
        text-align: left;
        }
        th {
        background-color: #4CAF50;
        color: white;
        }
        tr:nth-child(even) {
        background-color: #f2f2f2;
        }
        tr:hover {
        background-color: #ddd;
        }

        @keyframes glow {
            0% {
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
            }
            50% {
            box-shadow: 0 0 20px rgba(0, 255, 0, 1);
            transform: scale(1.05);
            }
            100% {
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
            }
            }

        #fab-button {
           position: fixed;
           bottom: 20px;
           right: 20px;
           background-color: #ffffff;
           border-radius: 50%;
           box-shadow: 0 4px 8px rgba(0,0,0,0.2);
           height: 70px;
           width: 70px;
           display: flex;
           justify-content: center;
           align-items: center;
           z-index: 10000;
           transition: transform 0.3s ease;
           animation: glow 1.5s ease-in-out infinite alternate;
           }

        #fab-button:hover {
           transform: scale(1.05);
           }

        #fab-button img {
           height: 40px;
           width: 40px;
           object-fit: contain;
           }

        #fab-menu {
          position: fixed;
          bottom: 110px;  /* stack above FAB */
          right: 20px;
          display: flex;
          flex-direction: column;
          gap: 10px;
          opacity: 0;
          transform: translateY(20px);
          transition: opacity 0.3s, transform 0.3s;
          z-index: 999;
        }

        #fab-menu.show {
          opacity: 1;
          transform: translateY(0);
        }

        #fab-menu button {
          background: var(--brand-purple);
          color: #fff;
          border: none;
          border-radius: 20px;
          padding: 8px 14px;
          cursor: pointer;
          box-shadow: 0 3px 8px rgba(0,0,0,0.2);
          font-size: 0.9rem;
        }

        #splash {
           position: fixed;
           top: 0;
           left: 0;
           width: 100%;
           height: 100%;
           background-color: white;
           display: flex;
           flex-direction: column;
           justify-content: center;
           align-items: center;
           z-index: 9999;
           animation: fadeOut 1s ease 1 forwards;
           animation-delay: 1.5s;
        }

        #splash-title {
            font-size: 46px;
            font-weight: bold;
            display: flex;
            justify-content: center;
            align-items: center;
            animation: slideLeft 1s ease 1 forwards;
            animation-delay: 1.5s; 
            margin-top: 20px; /* Adds space between the logo and the title */
            }

            .green {
               color: green;
            }

            .purple {
                 color: purple;
            }

        #splash-logo {
           height: 140px;
           animation: slideLeft 1s ease 1 forwards;
           animation-delay: 1.5s;
        }

        @keyframes slideLeft {
          0% {
              transform: translateX(0);
              opacity: 1;
          }
          100% {
              transform: translateX(-300%);
              opacity: 0;
          }
        }

         @keyframes fadeOut {
           to {
              opacity: 0;
              visibility: hidden;
              }
         }

         .active-nav {
            color: green;
            font-weight: bold;
            font-size: 1.2em;  /* <--- this line increases the font size */

         }

         .report-section ul li a {
            text-decoration: none;
            color: #007bff;
            font-weight: 600;
          }

         .report-section ul li a:hover {
            text-decoration: underline;
            color: #0056b3;
         }

    /* ===== Design Uplift – paste at end of <style> ===== */
    :root{
       --brand-purple:#6a1b9a;
       --brand-green:#2e7d32;
       --ink:#1b1b1b;
       --muted:#667085;
       --bg:#f7f8fa;
       --card:#ffffff;
       --border:#e9ecef;
       --radius:14px;
     }

     html,body{scroll-behavior:smooth;}
     body{
       font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
       color: var(--ink);
       background: var(--bg);
       line-height:1.55;
     }

     .container{max-width:1140px; padding: 0 16px;}

     header{
      background:#eaffea; /* Light light green */
      border-bottom: 1px solid var(--border);
      color: var(--ink);
      position: sticky; top: 0; z-index: 1000;
      box-shadow: 0 6px 20px rgba(0,0,0,.06);
     }

     #branding h1{ color: var(--brand-purple); font-weight: 800; letter-spacing:.2px; }

     .section.content{
       background: var(--card);
       border:1px solid var(--border);
       border-radius: var(--radius);
       box-shadow: 0 10px 30px rgba(0,0,0,.04);
     }

     .menu a, header a{ color: var(--brand-purple); }
     .menu a:hover, header a:hover{ color: var(--brand-green); }

     .active-nav{
       color: var(--brand-green) !important;
       font-weight: 700;
       position: relative;
     }
     .active-nav::after{
       content:"";
       position:absolute; left:0; right:0; bottom:-8px; height:3px;
       background: linear-gradient(90deg, var(--brand-green), var(--brand-purple));
       border-radius:3px;
      }

     button{
       border-radius:12px;
       border:1px solid var(--border);
       background:#fff;
       font-weight:600;
       transition: transform .06s ease, box-shadow .2s ease;
     }
     button:hover{ transform: translateY(-1px); box-shadow:0 8px 24px rgba(0,0,0,.08); }
     button:active{ transform: translateY(0); }

     table{
       border:1px solid var(--border);
       border-radius: 10px;
       overflow: hidden;
     }
     th{
        background: var(--brand-purple);
        color:#fff; font-weight:700; letter-spacing:.2px;
        position: sticky; top:0; z-index:1;
     }
     td, th{ border-color: var(--border) !important; }
     tr:nth-child(even){ background:#fafafa; }
     tr:hover{ background:#f3f6ff; }

     /* Fab: soften */
     #fab-button{ background:#fff; border:1px solid var(--border); }

     /* Smaller splash duration tweak (feels snappier) */
     #splash{ animation-delay:.9s; }

    /* ===== Initiatives Carousel ===== */
    .carousel{
      position: relative; margin: 18px 0 8px;
    }
    .carousel-track{
       display:flex; gap:16px; overflow-x:auto; padding:8px 8px 16px;
       scroll-snap-type: x mandatory; scrollbar-width: thin;
    }
    .carousel-track::-webkit-scrollbar{ height:8px; }
    .carousel-track::-webkit-scrollbar-thumb{ background:#c7c9d1; border-radius:8px; }

    .initiative-card{
      display:flex;
      flex-direction:column;
      align-items:center;
      text-align:center;
      scroll-snap-align: start;
      min-width: 220px;
      max-width: 260px;
      flex: 0 0 auto;
      background:#fff;
      border:1px solid var(--border);
      border-radius:16px;
      padding:24px 18px;
      cursor:pointer;
      user-select:none;
      box-shadow:0 6px 18px rgba(0,0,0,.06);
      transition: transform .06s ease, box-shadow .2s ease;
    }

    .initiative-card:hover{
      transform: translateY(-2px);
      box-shadow:0 12px 26px rgba(0,0,0,.1);
    }

    .initiative-title{
      font-weight:700;
      color: var(--brand-purple);
      margin:8px 0 6px;
    }

    .initiative-card i{
      width:36px;
      height:36px;
      margin:8px 0;
      stroke-width:2.4;
      color: var(--brand-green);
    }

    .initiative-sub{
      color: var(--muted);
      font-size:.92rem;
      margin-top:6px;
    }

     .carousel-nav{
        position:absolute; top:50%; transform:translateY(-50%);
        border:none; background:#fff; border:1px solid var(--border);
        height:40px; width:40px; border-radius:50%;
        display:flex; align-items:center; justify-content:center;
        box-shadow:0 8px 18px rgba(0,0,0,.08);
     }
     .carousel-nav:hover{ box-shadow:0 10px 28px rgba(0,0,0,.12); }
     .carousel-prev{ left:-12px; } .carousel-next{ right:-12px; }

     @media (max-width: 640px){
        .carousel-prev{ left:-6px;} .carousel-next{ right:-6px;}
     }

    /* Stronger table card effect */
    .section.content table {
      box-shadow: 0 10px 28px rgba(0,0,0,.08);
      border-radius: 14px;
    }

    /* Make the 4 action buttons look like initiative cards */
    .action-buttons{
      display:flex;
      flex-wrap:wrap;
      justify-content:center;
      gap:20px;
      margin: 20px 0;
    }

    .action-buttons button{
      background:#fff;
      border:1px solid var(--border);
      border-radius:16px;
      padding:22px 34px;
      font-size:20px;
      font-weight:600;
      color:var(--brand-purple);
      cursor:pointer;
      box-shadow:0 6px 18px rgba(0,0,0,.06);
      transition: transform .08s ease, box-shadow .18s ease;
    }

    .action-buttons button:hover{
       transform: translateY(-2px);
       box-shadow:0 12px 28px rgba(0,0,0,.12);
    }

    /* Icons inside buttons & cards */
    .action-buttons i,
    .initiative-card i {
      width:20px;
      height:20px;
      margin-right:12px;
      vertical-align:middle;
      stroke-width:2.2;
    }

    /* ===== Home redesign ===== */
    .home-feature-grid{
      display:grid;
      grid-template-columns: repeat(auto-fit, minmax(260px,1fr));
      gap:22px;
      margin:18px 0 8px;
    }
    .feature-card{
      background:#fff;
      border:1px solid var(--border);
      border-radius:18px;
      overflow:hidden;
      box-shadow:0 8px 24px rgba(0,0,0,.06);
      transition:transform .08s ease, box-shadow .18s ease;
    }
    .feature-card:hover{ transform:translateY(-2px); box-shadow:0 14px 32px rgba(0,0,0,.10); }
    .feature-card .media{
      height:160px; display:flex; align-items:center; justify-content:center;
      background:#f4f6ff; position:relative;
    }
    .feature-card .media.media-img{
      background-size:cover; background-position:center; filter:saturate(1.05);
    }
    .feature-card .media i{ width:44px; height:44px; stroke-width:2.4; color:var(--brand-green); }
    .feature-card .body{ padding:18px 18px 16px; }
    .feature-card h4{ margin:0 0 8px; font-size:1.1rem; }
    .feature-card p{ color:var(--muted); margin:0 0 12px; }
    .feature-card .readmore{
      font-weight:600; text-decoration:none; color:var(--brand-purple);
      display:inline-flex; align-items:center; gap:6px;
    }
    .feature-card .readmore:hover{ color:var(--brand-green); }

    /* Detail blocks */
    .section-block{
      background:#fff; border:1px solid var(--border); border-radius:18px;
      padding:26px; margin-top:26px; box-shadow:0 10px 28px rgba(0,0,0,.06);
    }
    .split{ display:grid; grid-template-columns: 1.2fr 1fr; gap:26px; align-items:center; }
    .split img{ width:100%; border-radius:14px; border:1px solid var(--border); box-shadow:0 8px 22px rgba(0,0,0,.06); }
    @media (max-width: 900px){ .split{ grid-template-columns:1fr; } }

    /* Chips & lists */
    .chips{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
    .chip{ background:#f3f5f7; border:1px solid var(--border); padding:6px 10px; border-radius:999px; font-size:.9rem; }
    .checklist{ padding-left:0; list-style:none; }
    .checklist li{ display:flex; gap:10px; align-items:flex-start; margin:8px 0; }
    .checklist li i{ width:18px; height:18px; color:var(--brand-green); margin-top:2px; }

    /* Scroll-reveal */
    .reveal{ opacity:0; transform:translateY(16px); transition:opacity .5s ease, transform .5s ease; }
    .reveal.is-visible{ opacity:1; transform:none; }

    .kpi-carousel {
       display: flex;
       justify-content: center;
       gap: 20px;
       margin: 30px 0;
     }

    .kpi-card {
      width: 230px;   /* was 200px */
      height: 150px;  /* was 130px */
      perspective: 1000px;
    }

    .kpi-inner {
      position: relative;
      width: 100%;
      height: 100%;
      transform-style: preserve-3d;
      transition: transform 0.8s;
    }

    .kpi-card.flipped .kpi-inner {
      transform: rotateY(180deg);
    }

    .kpi-front, .kpi-back {
      position: absolute;
      top:0; left: 0;
      width: 100%;
      height: 100%;
      backface-visibility: hidden;
      background: #fff;
      border-radius: 16px;
      border: 1px solid var(--border);
      box-shadow: 0 6px 18px rgba(0,0,0,.08);
      
      /* 🔑 force same layout */
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      box-sizing: border-box;
      padding: 10px; /* add here instead of only on back */
      
      
    }

    .kpi-front h3, .kpi-back h3 {
      margin: 0;
      font-size: 1rem;
      color: var(--brand-purple);
    }

    .kpi-value {
      font-size: 1.6rem;
      font-weight: 700;
      color: var(--brand-green);
     }

    .kpi-back {
      transform: rotateY(180deg);
      text-align: center;
    }

    .kpi-backline {
       margin: 5px 0;
       font-size: 0.95rem;
       color: var(--muted);
    }

    .kpi-grid {
      display: flex;
      justify-content: center;
      gap: 20px;
      margin: 30px 0;
    }

    .kpi-simple-card {
      width: 230px;
      height: 130px;
      background: #fff;
      border-radius: 16px;
      border: 1px solid var(--border);
      box-shadow: 0 6px 18px rgba(0,0,0,.08);
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      padding: 10px;
      text-align: center;
    }

    .kpi-simple-card h3 {
      margin: 0;
      font-size: 1rem;
      color: var(--brand-purple);
    }

    .kpi-simple-value {
      font-size: 1.6rem;
      font-weight: 700;
      color: var(--brand-green);
    }


      /* Chat window basic design */
      #chat-window {
        position: fixed; /* detach from parents */
        bottom: 100px;   /* sits above FAB */
        right: 20px;
        width: 300px;
        height: 250px;
        background: #fff;
        border: 1px solid var(--border);
        border-radius: 12px; /* restore round corners normally*/
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        display: flex;
        flex-direction: column;
        /* overflow: hidden; to remove for moment as it's compromising input bar */
        z-index: 99999;  /* on top of everything */
        transition: transform .2s ease, opacity .2s ease;
      }

      /* hidden by default */
      .chat-hidden {
        opacity: 0;
        pointer-events: none;
        transform: translateY(10px);
      }

      /* visible state */
      .chat-visible {
         opacity: 1;
         pointer-events: auto;
         transform: translateY(0);
      }

      .chat-header {
        background: linear-gradient(90deg, var(--brand-purple), var(--brand-green));
        color: white;
        padding: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: bold;
      }

      .chat-close {
        background: none;
        border: none;
        color: white;
        font-size: 16px;
        cursor: pointer;
      }

      .chat-body {
          flex: 1;
          padding: 12px;
          font-size: 0.9rem;
          color: var(--muted);
          overflow-y: auto
      }

      .chat-input {
        /* position: absolute */  /* This for not removing chat for more than 4 messages */
        display: flex;
        border-top: 1px solid var(--border);
        padding: 8px;
        background:#fff;
      }

      .chat-input input {
         flex: 1;
         border: none;
         padding: 10px;
         font-size: 0.9rem;
         border-radius: 0;
         outline: none;
      }

      .chat-input button {
        background: var(--brand-purple);
        color: white;
        border: none;
        padding: 0 16px;
        cursor: pointer;
        font-size: 1.2rem;
        transition: background 0.2s;
      }

      .chat-input button:hover {
         background: var(--brand-green);
      }

         
    </style>
    <script>
        function toggleVisibility(id) {
            var element = document.getElementById(id);
            if (element.classList.contains('hidden')) {
                element.classList.remove('hidden');
                element.classList.add('show');
            } else {
                element.classList.remove('show');
                element.classList.add('hidden');
            }
        }

        function loadPowerBIReport() {
           document.getElementById("analyticsContainer").innerHTML = `
           <iframe title="SustainaBOS7" width="950" height="1250"
        src="https://app.powerbi.com/reportEmbed?reportId=19eea1f2-00f5-4fcf-8d6d-6bed6f27d0e5&autoAuth=true&ctid=0bb4d87c-b9a5-49c3-8a59-4347acef01d8&navContentPaneEnabled=false&filterPaneEnabled=false"
           frameborder="0" allowFullScreen="true">
           </iframe>
    `      ;
        }

        function showSection(sectionId) {
            var sections = document.getElementsByClassName('section');
            var navItems = document.querySelectorAll('a[id^="nav-"]');  
            // selects all nav items by id
            console.log("Sections found:", sections);
            for (var i = 0; i < sections.length; i++) {
                sections[i].style.display = 'none';
            }

            // Remove highlight from all nav items
                navItems.forEach(item => {
        item.classList.remove('active-nav');
                // Optional: remove any icons previously added
                var icon = item.querySelector('img');
                if (icon) item.removeChild(icon);
            });

            // Show the selected section
            var selectedSection = document.getElementById(sectionId);
            if (selectedSection) {
                   selectedSection.style.display = 'block';
            }

            // Sinon : document.getElementById(sectionId).style.display = 'block';

            // Show instructions if it's the 'list' or 'contact' section
            if (sectionId === 'list') {
                  const box = document.getElementById('instruction-box');
                  if (box) {
                     box.style.display = 'block';
                     box.style.opacity = '1';
                     box.style.transition = 'opacity 1s ease';
                     setTimeout(() => {
                        box.style.opacity = '0';
                     }, 3000); // Fade out after 3 seconds
                  }
            }
            if (sectionId === 'contact') {
                  const box = document.getElementById('instruction-box-nul');
                  if (box) {
                     box.style.display = 'block';
                     box.style.opacity = '1';
                     box.style.transition = 'opacity 1s ease';
                     setTimeout(() => {
                        box.style.opacity = '0';
                     }, 3000); // Fade out after 3 seconds
                  }
            }

            // 👉 Add Power BI iframe only when user navigates to analytics
            if (sectionId === 'analytics') {
                loadPowerBIReport();
            }

            // Add highlight or icon to active section
            var activeNav = document.getElementById('nav-' + sectionId);
            activeNav.classList.add('active-nav');

            // Add green_leaf icon
            let leaf = document.createElement('img');
            leaf.src = '/static/green_leaf.png';  // adjust path if needed
            leaf.alt = 'leaf';
            leaf.style.height = '16px';
            leaf.style.marginLeft = '5px';
            activeNav.appendChild(leaf);


        }

        function addDevice() {
        console.log("Add Device button clicked");
        currentAction = "addDevice"; // Store the action type
        showVesselSelector();
        }

        // function modifyStatus() {
        // console.log("Modify Status button clicked");
        // currentAction = "modifyStatus"; // Store the action type
        // showVesselSelector();
        // } 

        function openTracker() {
        // Opens the Britoil SharePoint tracker in a new tab
          window.open(
            'https://britoilos-my.sharepoint.com/:x:/g/personal/axel_faurax_britoil_com_sg/EXZ7myRyuexAri5Js-87reoBpko4Jot6Xyztu5ZOijIY0A?e=QQKycU',
            '_blank', 
            'noopener'
          );
        }

        function showKPI() {
        // open analytics section
          showSection('analytics')}

        function showVessel() {
        console.log("Show Vessel button clicked");
        currentAction = "showVessel"; // Store the action type
        showVesselSelector();
        }

        function showDevice() {
        console.log("Show Device button clicked");
        currentAction = "showDevice"; // Store the action type
        showDeviceSelector();
        }


        function showVesselSelector() {
        const vesselSelector = document.getElementById('vesselSelector');
        vesselSelector.style.display = 'block';
        }

        function showDeviceSelector() {
        const deviceSelector = document.getElementById('deviceSelector');
        deviceSelector.style.display = 'block';
        }

        function confirmDeviceSelection() {
               // alert("Status is required.");
               const selectedDevice = document.getElementById('deviceDropdown').value;
               console.log("Selected Device: " + selectedDevice);
               // 👇 Call Flask backend to get device summary
               fetch('/get_device_summary', {
                   method: 'POST',
                   headers: {
                      'Content-Type': 'application/json'
                   },
                   body: JSON.stringify({ deviceName: selectedDevice })
               })
               .then(response => response.text())
               .then(html => {
                  document.getElementById('deviceSummaryDisplay').innerHTML = html;
               })
               .catch(error => {
                  console.error('Error fetching device summary:', error);
               });
        }


        function confirmVesselSelection() {
           const selectedVessel = document.getElementById('vesselDropdown').value;
           console.log("Selected Vessel: " + selectedVessel);

           // Check the action type and prompt accordingly
           if (currentAction === "addDevice") {
        
              // After vessel selection, ask for the device name
              const deviceName = prompt("Please enter the name of the device:");
        
              if (deviceName) {
                 console.log("Device name: " + deviceName);
                 // Here you can add further logic to save the device or show confirmation
                 alert("Device '" + deviceName + "' has been added to vessel '" + selectedVessel + "'");
                 // 👇 ADD THIS: send to backend so you get an email
                 fetch('/notify_new_device', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                         vessel: selectedVessel,
                         device: deviceName
                    })
                 })
                 .then(res => res.json())
                 .then(data => console.log("Notification:", data))
                 .catch(err => console.error("Error sending notification:", err));
              } else {
                  alert("Device name is required.");
              }
           } else if (currentAction === "modifyStatus") {
               const newStatus = prompt("Please enter the new status:");
               if (newStatus) {
                  console.log("New status: " + newStatus);
                  alert("Status '" + newStatus + "' has been updated for vessel '" + selectedVessel + "'");
               } else {
                  alert("Status is required.");
               }
           } else if (currentAction === "showVessel") {
               // 👇 Call Flask backend to get vessel summary
               fetch('/get_vessel_summary', {
                   method: 'POST',
                   headers: {
                      'Content-Type': 'application/json'
                   },
                   body: JSON.stringify({ vesselName: selectedVessel })
               })
               .then(response => response.text())
               .then(html => {
                  document.getElementById('vesselSummaryDisplay').innerHTML = html;
               })
               .catch(error => {
                  console.error('Error fetching vessel summary:', error);
               });
            }
        }

    function selectDeviceFromCard(deviceName){
      // Sync hidden dropdown then reuse your existing fetch logic
      const dd = document.getElementById('deviceDropdown');
      if (dd){
        dd.value = deviceName;
        confirmDeviceSelection(); // calls /get_device_summary and fills #deviceSummaryDisplay
      }
    }

    // Carousel controls
    window.addEventListener('DOMContentLoaded', function(){
      const track = document.getElementById('initiativesTrack');
      const prev  = document.getElementById('iniPrev');
      const next  = document.getElementById('iniNext');
      if(track && prev && next){
        const step = () => Math.max(track.clientWidth * 0.9, 260); // almost a page
        prev.addEventListener('click', () => track.scrollBy({left: -step(), behavior:'smooth'}));
        next.addEventListener('click', () => track.scrollBy({left:  step(), behavior:'smooth'}));
      }
    });

    </script>


</head>
<body>
    <div id="splash">
    <img src="{{ url_for('static', filename='green_leaf.png') }}" alt="Logo" id="splash-logo">
    <div id="splash-title">
        <span class="green">Sustaina</span><span class="purple">BOS</span>
    </div>
    </div>

    <a href="javascript:void(0);" id="fab-button" title="Menu">
    <img src="{{ url_for('static', filename='green_leaf.png') }}" alt="FAB Logo">
    </a>

    <div id="fab-menu" class="hidden">
      <button onclick="openChat()">Chat</button>
      <button onclick="refreshPage()">Refresh</button>
      <button onclick="openAdminOrLogout()">Admin</button>
    </div>

    <!-- Chat Window -->
    <div id="chat-window" class="chat-hidden">
      <div class="chat-header">
        <span>Sustainabos Chat</span>
        <button onclick="closeChat()" class="chat-close">✕</button>
      </div>
      <div id="chat-body" class="chat-body">
      </div>
      <div class="chat-input">
        <input type="text" id="chat-input-field" placeholder="Type a message...">
        <button id="chat-send">➤</button>
      </div>
    </div>


    <header>
      <div class="container">
        <div id="branding">
          <img src="{{ url_for('static', filename='britoil_logo.png') }}" alt="Britoil Offshore Services Logo" style="height:38px;">
          
          <h1>Fleet Sustainability View</h1>
          <br>
        </div>
        <nav>
          <ul>
            <li><a id="nav-welcome" href="#" onclick="showSection('welcome')">Home</a></li>
            <li><a id="nav-list" href="#" onclick="showSection('list')">List</a></li>
            <li><a id="nav-apps" href="#" onclick="showSection('apps')">Apps</a></li>
            <li><a id="nav-analytics" href="#" onclick="showSection('analytics')">KPIs</a></li>
            <li><a id="nav-report" href="#" onclick="showSection('report')">Docs</a></li>
            <li><a id="nav-contact" href="#" onclick="showSection('contact')">Contact</a></li>
            <li style="margin-left:auto;">
              <a href="#" onclick="logout()" title="Logout">
                <i data-lucide="log-out"></i>
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </header>

    <div class="container">
      <div id="welcome" class="section content">

        <!-- KPI Flip Cards -->
        <div class="kpi-carousel reveal">
          {% for kpi in kpis %}
          <div class="kpi-card">
            <div class="kpi-inner">
              <!-- Front -->
              <div class="kpi-front">
                <h3>{{ kpi.title }}</h3>
                <p class="kpi-value" data-target="{{ kpi.value }}" data-suffix="{{ kpi.suffix }}">0{{ kpi.suffix }}</p>
              </div>
              <!-- Back (same for now, later we can put explanations) -->
              <div class="kpi-back">
                <h3>{{ kpi.title }}</h3>
                {% if kpi.back %}
                  <p class="kpi-backline">{{ kpi.back[0] }}</p>
                  <p class="kpi-backline">{{ kpi.back[1] }}</p>
                {% endif %}
              </div>
            </div>
          </div>
          {% endfor %}
        </div>


        <h2 style="margin-top:10px">Featured content</h2>

        <!-- Shell-like 6 cards -->
        <div class="home-feature-grid reveal">

          <!-- Purpose -->
          <a href="#purpose" class="feature-card" style="text-decoration:none;">
            <div class="media media-img" style="background-image:url('{{ url_for('static', filename='britoilpic3.JPG') }}');"></div>
            <div class="body">
              <h4>Purpose of the tool</h4>
              <p>What SustainaBOS is and how Britoil teams use it.</p>
              <span class="readmore">Read more <i data-lucide="arrow-right"></i></span>
            </div>
          </a>

          <!-- Scopes -->
          <a href="#scopes" class="feature-card" style="text-decoration:none;">
            <div class="media media-img" style="background-image:url('{{ url_for('static', filename='britoilpic2.jpg') }}');"></div>
            <div class="body">
              <h4>Goals & Scopes</h4>
              <p>Scope 1/2/3 overview and Britoil’s current focus.</p>
              <span class="readmore">Read more <i data-lucide="arrow-right"></i></span>
            </div>
          </a>

          <!-- News -->
          <a href="#news" class="feature-card" style="text-decoration:none;">
            <div class="media media-img" style="background-image:url('{{ url_for('static', filename='Princess.jpeg') }}');"></div>
            <div class="body">
              <h4>BOS Princess — News</h4>
              <p>Conversion to a Geotechnical Drilling Vessel.</p>
              <span class="readmore">Read more <i data-lucide="arrow-right"></i></span>
            </div>
          </a>

          <!-- Vision -->
          <a href="#vision" class="feature-card" style="text-decoration:none;">
            <div class="media media-img" style="background-image:url('{{ url_for('static', filename='reportex3.png') }}');"></div>
            <div class="body">
              <h4>Vessel Sustainability vision</h4>
              <p>How we see the journey for Britoil vessels.</p>
              <span class="readmore">Read more <i data-lucide="arrow-right"></i></span>
            </div>
          </a>

          <!-- Vision 2 -->
          <a href="#vision2" class="feature-card" style="text-decoration:none;">
            <div class="media media-img" style="background-image:url('{{ url_for('static', filename='britoilpic1.jpg') }}');"></div>
            <div class="body">
              <h4>Company Sustainability vision</h4>
              <p>How we see the journey for Britoil company.</p>
              <span class="readmore">Read more <i data-lucide="arrow-right"></i></span>
            </div>
          </a>

          <!-- Sustainabilty Report -->
          <a href="#report" class="feature-card" style="text-decoration:none;">
            <div class="media media-img" style="background-image:url('{{ url_for('static', filename='reportex.jpg') }}');"></div>
            <div class="body">
              <h4>Sustainability Report 2025</h4>
              <p>The last sustainability report produced by the company.</p>
              <span class="readmore">Read more <i data-lucide="arrow-right"></i></span>
            </div>
          </a>


        </div>

        <!-- PURPOSE -->
        <div id="purpose" class="section-block split reveal">
          <div>
            <h3>What is <span class="green">Sustaina</span><span class="purple">BOS</span>?</h3>
            <p>Internal platform to track solutions, gather apps, quantify savings and compare vessel performance with extra analytics.</p>
            <ul class="checklist">
              <li><i data-lucide="check-circle-2"></i><span>Track the implementation of new solutions across vessels.</span></li>
              <li><i data-lucide="check-circle-2"></i><span>Consolidate cost/CO₂-eq savings and progress.</span></li>
              <li><i data-lucide="check-circle-2"></i><span>Gather the Apps used by Britoil to power their usage.</span></li>
              <li><i data-lucide="check-circle-2"></i><span>Benchmark vessels and identify opportunities with KPI's.</span></li>
              <li><i data-lucide="check-circle-2"></i><span>Create a digital Library for sustainability documents.</span></li>
              <li><i data-lucide="check-circle-2"></i><span>Interact within the team and vessels for updated data.</span></li>
              <!-- <li><i data-lucide="check-circle-2"></i><span>Dive deeper with Analytics (see section).</span></li> -->
            </ul>
            <div class="chips">
             <span class="chip">Fleet view</span>
             <span class="chip">Systems Tracker</span>
             <span class="chip">Vessel KPI</span>
            </div>
          </div>
          <div>
            <img src="{{ url_for('static', filename='green_leaf3.png') }}" alt="SustainaBOS">
          </div>
        </div>

        <!-- SCOPES -->
        <div id="scopes" class="section-block split reveal">
          <div>
            <h3>Goals & Scopes (reminder)</h3>
            <p>Britoil currently focuses mainly on Scope 3. Scope 1 fuel is not paid by us, and Scope 2 impact is comparatively small.</p>
            <div class="chips">
             <span class="chip">Scope 1 — Direct</span>
             <span class="chip">Scope 2 — Energy</span>
             <span class="chip">Scope 3 — Value chain</span>
            </div>
          </div>
          <div>
            <img src="{{ url_for('static', filename='Scopes.png') }}" alt="Scopes diagram">
          </div>
        </div>

        <!-- NEWS -->
        <div id="news" class="section-block split reveal">
          <div>
            <img src="{{ url_for('static', filename='Princess.jpeg') }}" alt="BOS Princess">
          </div>
          <div>
            <h3><b>BOS Princess — Successfully Converted</b> 🛠</h3>
            <p>The vessel has been converted from PSV to Geotechnical Drilling Vessel to support offshore wind work, including moon pool opening, rig tower & A-frame installation, plus azimuth thruster maintenance and overhaul.</p>
            <p>This strengthens Seas Geosciences’ geotechnical investigations and Britoil’s contribution to offshore wind.</p>
          </div>
        </div>

        <!-- VISION -->
        <div id="vision" class="section-block split reveal">
          <div>
            <h3>Our vision for Britoil vessels</h3>
            <ul class="checklist">
             <li><i data-lucide="check-circle-2"></i><span>Adopt proven efficiency Tech's (LED, filtration, monitoring).</span></li>
             <li><i data-lucide="check-circle-2"></i><span>Driving digital transition with innovative technology adoption.</span></li>
             <li><i data-lucide="check-circle-2"></i><span>Explore new energy possibilities,bio-fuel, reconversion.  </span></li>
             <li><i data-lucide="check-circle-2"></i><span>Measure what matters: fuel, cost & CO₂-eq savings per vessel.</span></li>
             <li><i data-lucide="check-circle-2"></i><span>Share insights between regions and speed up roll-outs.</span></li>
            </ul>
            <p style="margin-top:10px;">Powered by Axel FAURAX & the Technical Department.</p>
          </div>
          <div>
            <img src="{{ url_for('static', filename='britoilsus.png') }}" alt="Vision">
          </div>
        </div>

        <!-- VISION 2 -->
        <div id="vision2" class="section-block split reveal">
          <div>
            <h3>Our ESG vision for Britoil </h3>
            <ul class="checklist">
             <li><i data-lucide="check-circle-2"></i><span>Integrate environemantal solutions for the vessels.</span></li>
             <li><i data-lucide="check-circle-2"></i><span>Drive Social and Governance initiatives such as CSR</span></li>
             <li><i data-lucide="check-circle-2"></i><span>Report clearly—support the annual Sustainability Report.</span></li>
             <li><i data-lucide="check-circle-2"></i><span>Share insights between regions and speed up ESG actions.</span></li>
             
            </ul>
            <p style="margin-top:10px;">Powered by Axel FAURAX & the Technical Department.</p>
          </div>
          <div>
            <img src="{{ url_for('static', filename='view2.png') }}" alt="Vision2">
          </div>
        </div>
      </div>


      <div id="list" class="section content hidden">

          <!-- <p>This line is muted and won't appear on the page.</p> -->
          <!-- <div id="instruction-box" style="display: none; position: absolute; top: 150px; left: 70%; transform: translateX(-70%); background-color: #eef; padding: 25px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); z-index: 9999; transition: opacity 1s ease; opacity: 0;">
              <strong>Instructions</strong><br><br>
              By clicking on buttons <b>Show Vessel</b> and <b>Show Devices</b>, you can focus on the vessel or the device of your choice. <br><br>
 Exemple : Showing the devices of Defiance, or showing every vessel which have LED lights<br><br>
              <b>Please try!</b>
          </div> -->

          <div class="action-buttons">
             <button onclick="showVessel()">
                <i data-lucide="ship"></i>
                Show One Vessel
             </button>
             <button onclick="showDevice()">
                <i data-lucide="gauge"></i>
                Show One Device
             </button>
             <button onclick="addDevice()">
                <i data-lucide="plus-circle"></i>
                Add Devices
             </button>
             <button onclick="openTracker()">
               <i data-lucide="table"></i>
               Modify Excel Table
             </button>
             <button onclick="showKPI()">
               <i data-lucide="bar-chart-2"></i>
               Show KPI's
             </button>


          <!-- <div style="margin-bottom: 20px;">
             <button onclick="showVessel()" style="margin-right: 15px; font-size: 20px; padding: 20px 30px; color: purple;">Show One Vessel</button>
             <button onclick="showDevice()" style="margin-right: 15px; font-size: 20px; padding: 20px 30px; color: purple;">Show One Device</button>
             <button onclick="addDevice()" style="margin-right: 15px; font-size: 20px; padding: 20px 30px; color: purple;">+ Add Devices</button>
             <button onclick="openTracker()" style="margin-right: 15px; font-size: 20px; padding: 20px 30px; color: purple;">
               Modify Table
             </button> --> 
             
          </div>

          <!--  This section is for doing the dropdown menu for vessels and devices, once button click -->

          <div id="vesselSelector" style="margin-top: 20px; display: none;">
             <label for="vesselDropdown" style="font-size: 18px; color: purple;">Which vessel?</label>
             <select id="vesselDropdown" style="font-size: 16px; padding: 5px 10px; margin-left: 10px;">
                {% for vessel in listvessel_df['BOS DUBAI'] %}
                    <option value="{{ vessel }}">{{ vessel }}</option>
                {% endfor %}
             </select>
             <button onclick="confirmVesselSelection()" style="font-size: 18px; padding: 10px 20px; color: purple; margin-top: 10px;">Ok</button>
          </div>

          <div id="deviceSelector" style="margin-top: 20px; display: none;">
             <label for="deviceDropdown" style="font-size: 18px; color: purple;">Which Device?</label>
             <select id="deviceDropdown" style="font-size: 16px; padding: 5px 10px; margin-left: 10px;">
                {% for device in listdevice_df['Device'] %}
                    <option value="{{ device }}">{{ device }}</option>
                {% endfor %}
             </select>
             <button onclick="confirmDeviceSelection()" style="font-size: 18px; padding: 10px 20px; color: purple; margin-top: 10px;">Ok</button>
          </div>


          <!--  This is where the summary table will appear -->
          <div id="vesselSummaryDisplay" style="margin-top: 20px;"></div>
          <div id="deviceSummaryDisplay" style="margin-top: 20px;"></div>

          <br>

          <h3>New Initiatives - Cards</h3>
          <div class="carousel" aria-label="Initiatives carousel">
            <button class="carousel-nav carousel-prev" id="iniPrev" aria-label="Previous">‹</button>
            <div class="carousel-track" id="initiativesTrack">
               {% for device in listdevice_df['Device'] %}
                 {% if device %}
                 <div class="initiative-card" role="button" tabindex="0"
                   onclick="selectDeviceFromCard('{{ device|replace(\"'\", \"\\'\") }}')"
                   onkeypress="if(event.key==='Enter'){selectDeviceFromCard('{{ device|replace(\"'\", \"\\'\") }}')}">
                  <div class="initiative-title">{{ device }}</div>
                  <i data-lucide="{% if 'MGPS' in device %}beaker{% 
                    elif 'Chlorinator' in device %}flask-round{% 
                    elif 'CMCE LP' in device %}zap{% 
                    elif 'IWTM Filter' in device %}droplet{% 
                    elif 'EFMS' in device %}activity{% 
                    elif 'CJC Filter' in device %}gauge{% 
                    elif 'LED Lights' in device %}lightbulb{% 
                    elif 'AI CCTV' in device %}shield{% 
                    elif 'Deva Paint' in device %}lightbulb{% 
                    elif 'Spinergie Fleet' in device %}bar-chart-3{% 
                    elif 'Nautilus Log' in device %}bar-chart-3{% 
                    elif 'RE Conversion' in device %}file-text{% 
                    elif 'Silicon Paint' in device %}wind{% 
                    elif 'Shore Generator' in device %}scale{% 
                    elif 'IOW Separator' in device %}leaf{% 
                    else %}settings{% endif %}"></i>
                  <div class="initiative-sub">Click to view in which vessels the system is installed or in-process </div>
                 </div>
                 {% endif %}
               {% endfor %}
            </div>
            <button class="carousel-nav carousel-next" id="iniNext" aria-label="Next"></button>
          </div>

          <h3>Summary Track Sheet</h3>
          <table>
              {% for index, row in summary_df.iterrows() %}
              <tr>
                  {% for i, value in row.items() %}
                  {% if index == 0 %}
                  <td style="font-weight: bold;">{{ value }}</td>
                  {% elif loop.last %}
                  <td>
                     {% if value is number %}
                     <span style="color: {% if value >= 0.505 %}green{% elif value >= 0.30 and value < 0.505 %}orange{% else %}red{% endif %}; font-weight: bold;"> 
                        {{ (value * 100) | round(0) }}%
                     </span>
                     {% else %}
                     {{ value }}
                     {% endif %}
                  </td>
                  {% else %}
                  <td>{{ value }}</td>
                  {% endif %}
                  {% endfor %}
              </tr>
              {% endfor %}
          </table>

          <br>
          <h3>List of Vessels and Their Devices</h3>
          <p> Only installed devices or installation in process are displayed. You can see the 67 vessels name however </p>
          <table>
             {% for index, row in list_df.iterrows() %}
             {% set col_4_value = row[3] | string %}
             {% set col_5_value = row[4] | string %}

             {% if index == 0 or col_5_value in ["Done", "In Process"] or col_4_value == "↓" %}
             <tr>
                 {% for col_index in range(row.size) %}
                 {% set value = row[col_index] %}
                 {% if index == 0 %}
                 <td style="font-weight: bold;">{{ value }}</td>
                 {% elif value == "" or value == "nan" or value is none %}
                 <td></td>
                 {% elif col_index in [6, 7, 8] and col_5_value == "Done" %}
                 <td style="color: green;">
                    {% if value == "nan" or value is none %}
                    <!-- Display empty cell for "nan" values -->
                    {{ "" }}
                    {% else %}
                    <!-- {{ value | int | replace('0', '')}} On peut essayer ca --> 
                    {{ value | int }}
                    {% endif %}
                 </td>
                 {% else %}
                 <td>{{ value | replace('nan', '')}}</td>
                 {% endif %}
                 {% endfor %}
             </tr>
             {% endif %}
             {% endfor %}
          </table>
          
          {% for vessel in vessel_devices['Vessel Name/ ID'].unique() %}
          <button onclick="toggleVisibility('{{ vessel }}')">{{ vessel }}</button>
          <table id="{{ vessel }}" class="hidden">
              <tr>
                  <th>Devices</th>
                  <th>Installation Status</th>
                  <th>Savings/year (fuel efficiency)</th>
                  <th>Savings/year (Maitenance)</th>
                  <th>Co2 savings ton/year</th>
              </tr>
              {% for index, row in vessel_devices[vessel_devices['Vessel Name/ ID'] == vessel].iterrows() %}
              <tr>
                  <td>{{ row['Devices'] }}</td>
                  <td>{{ row['Installation Status'] }}</td>
                  <td>{{ row['Savings/year (fuel efficiency)'] }}</td>
                  <td>{{ row['Savings/year (Maitenance)'] }}</td>
                  <td>{{ row['Co2 savings ton/year'] }}</td>
              </tr>
              {% endfor %}
          </table>
          {% endfor %}
      </div>

      <div id="apps" class="section content hidden">
        <h2 class="section-title">Apps</h2>

        <!-- Reuse the same grid class as Home -->
        <div class="home-feature-grid apps-grid reveal">

          <!-- 1 -->
          <a href="https://crm.iwtm.com" target="_blank" class="feature-card" style="text-decoration:none;">
           <div class="media media-img" style="
             background-image:url('{{ url_for('static', filename='IWTMlogo.jpg') }}');
             background-size: contain; background-repeat:no-repeat; background-position:center; background-color:#f7fafc;">
           </div>
           <div class="body">
             <h4>IWT CMR</h4>
             <p>Water Analysis IWTM P10</p>
             <span class="readmore">Go to App <i data-lucide="arrow-right"></i></span>
           </div>
          </a>

          <!-- 2 -->
          <a href="https://app.shipin.ai" target="_blank" class="feature-card" style="text-decoration:none;">
           <div class="media media-img" style="
             background-image:url('{{ url_for('static', filename='ShipInlogo.png') }}');
             background-size: contain; background-repeat:no-repeat; background-position:center; background-color:#f7fafc;">
           </div>
           <div class="body">
             <h4>ShipIn</h4>
             <p>AI CCTV System by Shipin</p>
             <span class="readmore">Go to App <i data-lucide="arrow-right"></i></span>
           </div>
          </a>

          <!-- 3 -->
          <a href="https://unisea.britoil.com.sg" target="_blank" class="feature-card" style="text-decoration:none;">
           <div class="media media-img" style="
             background-image:url('{{ url_for('static', filename='unisealogo.jpg') }}');
             background-size: contain; background-repeat:no-repeat; background-position:center; background-color:#f7fafc;">
           </div>
           <div class="body">
             <h4>Unisea Emissions</h4>
             <p>Emissions and BI module by Unisea</p>
             <span class="readmore">Go to App <i data-lucide="arrow-right"></i></span>
           </div>
          </a>

          <!-- 4 -->
          <a href="https://app.nautiluslog.com" target="_blank" class="feature-card" style="text-decoration:none;">
           <div class="media media-img" style="
             background-image:url('{{ url_for('static', filename='nloglogo.png') }}');
             background-size: contain; background-repeat:no-repeat; background-position:center; background-color:#f7fafc;">
           </div>
           <div class="body">
             <h4>Nautilus Log</h4>
             <p>Inspection Report, Defect KPI's, VRR</p>
             <span class="readmore">Go to App <i data-lucide="arrow-right"></i></span>
           </div>
          </a>

          <!-- 5 -->
          <a href="https://tsl360.tractors.com.sg/login" target="_blank" class="feature-card" style="text-decoration:none;">
           <div class="media media-img" style="
             background-image:url('{{ url_for('static', filename='tsl360logo.png') }}');
             background-size: contain; background-repeat:no-repeat; background-position:center; background-color:#f7fafc;">
           </div>
           <div class="body">
             <h4>TSL360</h4>
             <p>Generators monitoring by CAT </p>
             <span class="readmore">Go to App <i data-lucide="arrow-right"></i></span>
           </div>
          </a>

          <!-- 6 -->
          <a href="https://rms.egenkit.com/#/" target="_blank" class="feature-card" style="text-decoration:none;">
           <div class="media media-img" style="
             background-image:url('{{ url_for('static', filename='egenkitlogo.png') }}');
             background-size: contain; background-repeat:no-repeat; background-position:center; background-color:#f7fafc;">
           </div>
           <div class="body">
             <h4>e-Gen KIT</h4>
             <p> Fuel monitoring, PPTEP's vessels </p>
             <span class="readmore">Go to App <i data-lucide="arrow-right"></i></span>
           </div>
          </a>

          <!-- 7 -->
          <a href="https://www.britoil.com.sg" target="_blank" class="feature-card" style="text-decoration:none;">
           <div class="media media-img" style="
             background-image:url('{{ url_for('static', filename='hempellogo.png') }}');
             background-size: contain; background-repeat:no-repeat; background-position:center; background-color:#f7fafc;">
           </div>
           <div class="body">
             <h4>Hempel Shape</h4>
             <p>Hull Analysis by Hemple</p>
             <span class="readmore">Go to App <i data-lucide="arrow-right"></i></span>
           </div>
          </a>

          <!-- 8 -->
          <a href="https://www.britoil.com.sg" target="_blank" class="feature-card" style="text-decoration:none;">
           <div class="media media-img" style="
             background-image:url('{{ url_for('static', filename='spinergielogo.jpg') }}');
             background-size: contain; background-repeat:no-repeat; background-position:center; background-color:#f7fafc;">
           </div>
           <div class="body">
             <h4>Spinergie</h4>
             <p>Spinergie Fleet Management </p>
             <span class="readmore">Go to App <i data-lucide="arrow-right"></i></span>
           </div>
          </a>

          <!-- 9 -->
          <a href="https://britoilos.sharepoint.com/sites/Vessel-Library" target="_blank" class="feature-card" style="text-decoration:none;">
           <div class="media media-img" style="
             background-image:url('{{ url_for('static', filename='SharePointlogo.png') }}');
             background-size: contain; background-repeat:no-repeat; background-position:center; background-color:#f7fafc;">
           </div>
           <div class="body">
             <h4>SharePoint</h4>
             <p>Britoil SharePoint all documentd</p>
             <span class="readmore">Go to App <i data-lucide="arrow-right"></i></span>
           </div>
          </a>

        </div>
        <br>

        <h2>Credentials - Login</h2>
        <p> If you need some credentials, please ask directly, you can see my contact in the contact section. </p>

      </div>

      <div id="analytics" class="section content hidden">

          <div class="kpi-grid">
            {% for k in kpis_section %}
              <div class="kpi-simple-card">
                <h3>{{ k.title }}</h3>
                <div class="kpi-simple-value">{{ k.value }}{{ k.suffix }}</div>
              </div>
            {% endfor %}
          </div>

          <h2>Analytics</h2>

          <p> You can interact with BI charts after sign in. Refresh if any issues </p>

          <h3>BI Analysis</h3>

          <div id="analyticsContainer"></div>

          <!-- <iframe title="SustainaBOS7" width="950" height="1250" src="https://app.powerbi.com/reportEmbed?reportId=19eea1f2-00f5-4fcf-8d6d-6bed6f27d0e5&autoAuth=true&ctid=0bb4d87c-b9a5-49c3-8a59-4347acef01d8&navContentPaneEnabled=false&filterPaneEnabled=false" frameborder="0" allowFullScreen="true"></iframe> -->

          <!-- <iframe title="SustainaBOS6" width="950" height="900" src="https://app.powerbi.com/reportEmbed?reportId=49b41197-4b6b-44b5-af29-6a685ea9dcdc&autoAuth=true&ctid=0bb4d87c-b9a5-49c3-8a59-4347acef01d8&navContentPaneEnabled=false&filterPaneEnabled=false" frameborder="0" allowFullScreen="true"></iframe> -->

          <!-- <h3>Introduction</h3>

          <iframe title="SustainaBOS4" width="950" height="250" src="https://app.powerbi.com/reportEmbed?reportId=3720fb28-575c-4f83-a708-38507f6decb9&autoAuth=true&ctid=0bb4d87c-b9a5-49c3-8a59-4347acef01d8&navContentPaneEnabled=false&filterPaneEnabled=false" frameborder="0" allowFullScreen="true"></iframe> -->

          


          <h3>Old Analytics</h3>
          <table>
              {% for index, row in summary3_df.iterrows() %}
              <tr>
                  {% for col_index in range(row.size) %}
                  {% set value = row.iloc[col_index] %}

                  {% if col_index == 0 or index == 0 %}
                  <td>{{ value }}</td>

                  {% elif col_index == 1 and index == 1 %}
                  <td style="font-weight: bold; color: orange;">
                      {{ (value * 100) | int}}%
                  </td>
                  {% elif col_index == 1 and index == 2 %}
                  <td style="font-weight: bold; color: green;">
                      {{ (value * 100) | round(0) | int }}%
                  {% elif col_index == 1 and index == 3 %}
                  <td style="font-weight: bold; color: green;">{{ (value * 100) | round(2) }}%</td>
                  {% else %}
                  <td>{{ (value * 100) | round(0) |int }}%</td>
                  {% endif %}
                  {% endfor %}
              </tr>
              {% endfor %}
          </table>


          <h3>Top 10 Vessels with Best Performance</h3>
          <div style="display: flex; justify-content: center; gap: 20px;">
              <img src="{{ url_for('static', filename='top_vessels_chartEX.png') }}" alt="Top 10 Vessels Chart" width="450">
              <img src="{{ url_for('static', filename='top_vessels_chartEX2.png') }}" alt="Top 10 Vessels Chart 2" width="450">
          </div>
          <h3>Savings by Region - 3 Offices</h3>
          <div style="display: flex; justify-content: center; gap: 20px;">
              <img src="{{ url_for('static', filename='top_region_chartEX.png') }}" alt="Savings by Region - 3 Offices" width="450">
              <img src="{{ url_for('static', filename='top_region_chartEX2.png') }}" alt="Savings by Region - Average by Vessel" width="450">
          </div>

          <h3>Savings by Devices - Initiatives</h3>
          <div style="display: flex; justify-content: center; gap: 20px;">
             <img src="{{ url_for('static', filename='top_device_chartEX.png') }}" alt="Cost Savings by Devices - Initiatives" width="450">
             <img src="{{ url_for('static', filename='top_device_chartEX2.png') }}" alt="CO2 Savings by Devices - Initiatives " width="450">
          </div>

          <h3>Track progress bars</h3>
          <div style="display: flex; justify-content: center; gap: 20px;">
             <img src="{{ url_for('static', filename='track_chartEX.png') }}" alt="Track" width="450">
             <img src="{{ url_for('static', filename='track_chartEX2.png') }}" alt="Track" width="450">

          </div>
          <br>

          <h3>Overdue Jobs - Statistics for PMS</h3>
          <p> Besides Sustainability, I'm also doing statistics for our overdue jobs and critical spare parts. Our PMS expert is doing calculations for KPI every months. I collected data and made some graphs in another tool. Here I will just put the top and worst vessels in terms of overdue jobs, to compare and be considered with previous score charts. </p> <br><br>
          <div style="display: flex; justify-content: center; gap: 20px;">
             <img src="{{ url_for('static', filename='OJ_worstEX.png') }}" alt="Track" width="450">
             <img src="{{ url_for('static', filename='OJ_worstEX2.png') }}" alt="Track" width="450">

          </div>



      </div>

      <div id="report" class="section content hidden">
         <h2>All Documents</h2>
         <br>
         <h3>Sustainability Report 2024</h3>
         Here is the sustainabilty report of 2024. I hope this new website could be involve in the next Sustainability Report 2025. Or help to do it. Here is the PDF display. <br> <br> 
         <iframe src="{{ url_for('static', filename='Report2024.pdf') }}" width="100%" height="600px">
         <!-- This browser does not support PDFs. Please download the PDF to view it: 
             <a href="{{ url_for('static', filename='Report2024.pdf') }}">Download PDF</a> -->
             
         </iframe>

         
         <h3>Sustainability Report 2025</h3>
         To come
         
         <div class="report-section" style="margin-top: 30px;">
           <h3>📄 Reports & Studies</h3>
             <ul style="list-style-type: none; padding-left: 20; margin:0;">
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:b:/g/personal/axel_faurax_britoil_com_sg/EevaaGdd2I9Fix-ihhTTSpUBCljoFEfPWiLaBlCzBlQ3GA?e=wboRxn" target="_blank">🔗 LED Light Study</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:b:/g/personal/axel_faurax_britoil_com_sg/ESAgxiOZdI5ItoEM3b3UJd8BJzCXiz4DgVrjGgRRx06YcA?e=pMHIEj" target="_blank">🔗 AI CCTV Study</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:b:/g/personal/axel_faurax_britoil_com_sg/EYadKUz1ndFGjab-1unbFBkB0diXBP36hvg2i0Bw240Ysg?e=UkaSer" target="_blank">🔗 MGPS Study</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:b:/g/personal/axel_faurax_britoil_com_sg/ERMqIzIiewBClWQiLKocjN8BdIuo2Ks6AVInt9oKMa-LZQ?e=dgdPCi" target="_blank">🔗 EFMS Study</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:p:/g/personal/axel_faurax_britoil_com_sg/Ea132zQliBVAu4Gc_H4ZSZcBzIcYKu7CWsLZGsyiaSCX5A?e=mqJhyx" target="_blank">🔗 IWTM Filters Study</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:b:/g/personal/axel_faurax_britoil_com_sg/Eb2xPkJWe0BEiWT-VtiWmD4BUFXw7fW2ZsQkvypmJ89u5Q?e=4rPoGg" target="_blank">🔗 CJC Unit Study</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:b:/g/personal/axel_faurax_britoil_com_sg/EQcq4o4Y5LpJgolosjOT5ncBuy-rpGnWClYvaNn6pmziAw?e=Kr5XTK" target="_blank">🔗 Fleet Management System Pre-Study</a></li>               
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:p:/g/personal/axel_faurax_britoil_com_sg/Ee3lqUA0Cl5ApvCfcGaexv0BIv881MnJPRGPFBxgYCMPjw?e=oFyS5x" target="_blank">🔗 New Initiatives Presentation – Dubai 2024</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:p:/g/personal/axel_faurax_britoil_com_sg/EXAFSkLNyppFtbHGKCwqRyABAuUzok_kEdlRdhw-UxKoLQ?e=gyBv4R" target="_blank">🔗 New Initiatives 2025</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:b:/g/personal/axel_faurax_britoil_com_sg/EUIW-XYFTjtBqBRw9ODl23QBJQ6Ctds1Tqsg3Ybid_-z-Q?e=rTh3e9" target="_blank">🔗 VFD Study</a></li>

             </ul>
         </div>

         <div class="report-section" style="margin-top: 30px;">
           <h3>📄 DataBases and Excel Calculators</h3>
             <ul style="list-style-type: none; padding-left: 20; margin:0;">
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:x:/g/personal/axel_faurax_britoil_com_sg/EXZ7myRyuexAri5Js-87reoBeA3TxCLpgfgyekdnVSQmKA?e=PTs9uV" target="_blank">🔗 Vessel Device Installation Tracker NV </a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:x:/g/personal/axel_faurax_britoil_com_sg/EQwx2EWZCXhAkbaYgAyU8m8BCQcuYDoLcgX-vqmrKRUB7A?e=z7UHyz" target="_blank">🔗 PMS Overdue and Postponed Stats</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:x:/g/personal/axel_faurax_britoil_com_sg/EbraJof6RRBDoBNT21B5GfIBB6dHv0MeZgx1-TTFOd4Yjw?e=NoQYfs" target="_blank">🔗 LED Calculator Fuel Savings</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:x:/g/personal/axel_faurax_britoil_com_sg/EdryQRnsByRBixSnoQ_ZXNsBnB0eH28l9cH-BKUAwuoUPg?e=rqAUOa" target="_blank">🔗 Digital Ocean Status - ERP Initiative</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos.sharepoint.com/:x:/s/Vessel-Library/EaRKrfVxnlJJsfd4XfiBLMMBm_Lxe9rzRnr_yZCzpoyxbg?e=xWa4lc" target="_blank">🔗 Britoil Technical Plan 2025 Updated</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:x:/g/personal/axel_faurax_britoil_com_sg/EeWlQm_l4LdGs1upPr4iw4oBy6GCABXPjHGxHwZQAQ5WCA?e=52IO9C" target="_blank">🔗 IWTM Samples Data & Analysis Britoil 121 (ex)</a></li>
             </ul>
         </div>
      </div>

      <div id="contact" class="section content hidden">

          <div id="instruction-box-nul" style="display: none; position: absolute; top: 250px; left: 70%; transform: translateX(-70%); background-color: #eef; padding: 25px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); z-index: 9999; transition: opacity 1s ease; opacity: 0;">
              <strong>HELLO ! </strong><br><br>
              <b>Feel free to contact me ^^</b>
          </div>

          <h2>Contact</h2>
          <h3>Axel Faurax - Sustainability Engineer</h3>
          <p>Axel is our sustainability and performance engineer. He's driving the green and innovative solutions accross the fleet. Reporting directly to Mohit Sabharwal and Florent Kirchoff.</p>
          <p>A highly adaptable and dynamic professional, Axel offers a multi-disciplinary and versatile approach when leading projects. He's strong relational and altruistic qualities are complemented by a keenness to learn and a proven competitive spirit developed through athletics. His sensitivity to both ecological and human concerns are also something to highlight.</p>
          <br>
          <h3>Contact infos</h3>
          <p>Name: Axel Faurax</p>
          <p>Phone (SG): +65 81298204 </p>
          <p>Phone (FR): +33 771770134 </p>
          <p>Email: axel.faurax@britoil.com.sg </p>
          <br>
          <h3>Office</h3>
          <p>Adress: 100G Pasir Panjang Rd</p>
          <p>Postal Code: 118523</p>
          <br> <br>
          <div style="display: flex; justify-content: center; gap: 20px;">
             <img src="{{ url_for('static', filename='QRCODE.jpg') }}" alt="Track" width="450">
          </div>
       
      </div>


    </div>
    <footer style="background-color: #333; color: #fff; padding: 20px 0; margin-top: 40px;">
       <div class="container" style="display: flex; flex-direction: column; align-items: center; text-align: center;">
         <p style="margin: 5px 0;">&copy; 2025 Britoil Offshore Services. All rights reserved.</p>
         <p style="margin: 5px 0;">
              <a href="mailto:info@britoil.com" style="color: #ccc; text-decoration: none;">Contact us</a> |
              <a href="/privacy-policy" style="color: #ccc; text-decoration: none;">Privacy Policy</a> |
              <a href="/terms-of-service" style="color: #ccc; text-decoration: none;">Terms of Service</a>
         </p>
       </div>
    </footer>

   <!-- JavaScript for splash animation -->
   <script>
      setTimeout(function () {
         document.getElementById('splash').style.display = 'none';
      }, 2500);

      // fab menu event fonction
      const fabButton = document.getElementById("fab-button");
      const fabMenu = document.getElementById("fab-menu");

      fabButton.addEventListener("click", () => {
        fabMenu.classList.toggle("show");
      });

      function refreshPage() {
        location.reload();
      }

      function logout() {
        window.location.href = "/logout";  // redirect to login page
      }

      function openAdminOrLogout() {
          if ("{{ session['user'] if 'user' in session else '' }}" === "Axel") {
            window.location.href = "/admin";
          } else {
            logout();
          }
        }


      function openChat() {
        const chat = document.getElementById("chat-window");
        chat.classList.remove("chat-hidden");
        chat.classList.add("chat-visible");
      }

      function closeChat() {
        const chat = document.getElementById("chat-window");
        chat.classList.remove("chat-visible");
        chat.classList.add("chat-hidden");
      }

      document.addEventListener("DOMContentLoaded", function () {
        const sendBtn = document.getElementById("chat-send");
        const input = document.getElementById("chat-input-field");
        const chatBody = document.getElementById("chat-body");

        if (sendBtn && input && chatBody) {
           sendBtn.addEventListener("click", function () {
              const msg = input.value.trim();
              if (msg !== "") {
                fetch("/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      message: msg
                    })
                  })
                  .then(res => res.json())
                  .then(() => {
                    loadChatMessages();  // refresh
                  })
                  .catch(err => console.error("Chat send error:", err));
                }
            });

            // Function to load all chat messages from DB
            function loadChatMessages() {
              fetch("/chat")
                .then(res => res.json())
                .then(data => {
                  chatBody.innerHTML = ""; // clear old
                  data.forEach(msg => {
                    const p = document.createElement("p");
                    p.textContent = msg.user + ": " + msg.message;
                    chatBody.appendChild(p);
                  });
                  chatBody.scrollTop = chatBody.scrollHeight;
                });
            }

            // Call this when chat window opens
            window.openChat = function () {
              const chat = document.getElementById("chat-window");
              chat.classList.remove("chat-hidden");
              chat.classList.add("chat-visible");
              loadChatMessages();
            };


          // (optional) Press Enter to send
          input.addEventListener("keypress", function (e) {
            if (e.key === "Enter") {
              sendBtn.click();
            }
          });
        }
      });


  
      window.onload = function() {
            showSection('welcome');
      };   

   </script>

   <script>
      lucide.createIcons();
   </script>

   <script>
    // Scroll-reveal for .reveal elements
    const io = new IntersectionObserver((entries)=>{
      entries.forEach(e=>{
        if(e.isIntersecting){ e.target.classList.add('is-visible'); io.unobserve(e.target); }
      });
    }, {threshold:0.12});
    document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
    // Re-render icons that appear dynamically
    if (window.lucide && lucide.createIcons) { lucide.createIcons(); }
   </script>

   <script>
     function formatNumberForDisplay(value, suffix="") {
       if (isNaN(value)) return "--" + suffix;

       // Handle percentages: always 2 decimals
       if (suffix.includes("%")) {
         return value.toFixed(2) + suffix;
       }

       // Round to 1 decimal for others
       const rounded = Math.round(value * 10) / 10;

       // If it's basically an integer, drop the ".0"
       if (Number.isInteger(rounded)) {
        return rounded.toLocaleString() + suffix;
       }

       // Otherwise, show 0 decimal
       return rounded.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + suffix;
       }

     function animateValue(el){
       const target = parseFloat(el.dataset.target);
       const suffix = el.dataset.suffix || "";

        if (isNaN(target)) {
        el.textContent = "--" + suffix;
        return;
        }

        // Adaptive duration: smaller numbers take longer to animate
        let duration;
        if (target < 50) {
          duration = 2500;
        } else if (target < 10000) {
          duration = 2500;
        } else {
          duration = 1200;
        }

        const start = 0;
        const frameRate = 60;
        const totalFrames = Math.round((duration / 1000) * frameRate);
        let frame = 0;

        const easeOutCubic = t => 1 - Math.pow(1 - t, 3);

        const timer = setInterval(()=>{
          frame++;
          const progress = easeOutCubic(frame / totalFrames);
          const current = start + (target - start) * progress;

          el.textContent = formatNumberForDisplay(current, suffix);

          if (frame >= totalFrames){
            clearInterval(timer);
            el.textContent = formatNumberForDisplay(target, suffix);
          }
        }, 1000 / frameRate);
      }

      function animateCounters(){
        document.querySelectorAll('.kpi-value').forEach(el=>{
          animateValue(el);
        });
      }

      // Flip animation every 6sfront, 3s back
      function flipCards() {
        document.querySelectorAll('.kpi-card').forEach(card=>{
          card.classList.toggle('flipped');
        });

        // If showing front now → animate counters
        if (!document.querySelector('.kpi-card').classList.contains('flipped')) {
          animateCounters();
          // front duration = 5s
          setTimeout(flipCards, 5000);
        } else {
          // back duration = 3s
          setTimeout(flipCards, 3000);
        }
      }

      // Start with front side showing + animate counters
      animateCounters();
      setTimeout(flipCards, 5000);

    </script>


   </body>
</html>
"""

#region Apps route


@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template_string(
        html_template,
        vessel_devices=vessel_devices,
        list_df=list_df,
        summary_df=summary_df,
        summary2_df=summary2_df,
        summary3_df=summary3_df,
        listvessel_df=listvessel_df,
        listdevice_df=listdevice_df,
        kpis=kpis,   # ← add this line
        kpis_section=kpis_section, #to not forget
    )

#region login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('index'))

    step = "login"   # default form
    error = None

    if request.method == 'POST':
        # Case A: Login attempt
        if 'username' in request.form and 'password' in request.form:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            user = User2.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                # check if it's still default password
                default_users = {
                    "Axel": "BOSaxfa*",
                    "admin": "secret123",
                    "Mohit": "BOSmosa*",
                    "Florent": "BOSflki*",
                    "Julian": "BOSjuoh*",
                    "Richard": "BOSrihi*",
                    "Ernest": "BOSerlo*",
                    "Sundar": "BOSsucc*",
                    "Ser Boon": "BOSseta*",
                    "Siva": "BOSsira*",
                    "Alessandro": "BOSalba*",
                }

                if default_users.get(username) == password:
                    # switch to change-password step
                    session['pending_user'] = username
                    step = "change_password"
                else:
                    # normal login
                    session['user'] = username
                    log = Metric(metric_name=username, value=0)
                    db.session.add(log)
                    db.session.commit()
                    return redirect(url_for('index'))
            else:
                error = "Invalid username or password"

        # Case B: Change password submission
        elif 'new_password' in request.form and 'confirm_password' in request.form:
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            username = session.get('pending_user')

            if not username:
                return redirect(url_for('login'))

            if new_password != confirm_password:
                error = "Passwords do not match."
                step = "change_password"
            else:
                user = User2.query.filter_by(username=username).first()
                if user:
                    user.password_hash = generate_password_hash(new_password)
                    db.session.commit()
                    session.pop('pending_user')
                    session['user'] = username

                    log = Metric(metric_name=f"{username}_password_changed", value=1)
                    db.session.add(log)
                    db.session.commit()
                    return redirect(url_for('index'))

    # --- HTML: same page handles both login + change password ---
    login_page = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Login- SustainaBOS</title>
        <style>
            body {
                font-family: 'Segoe UI', sans-serif;
                background: url('/static/imagelogin.JPG') no-repeat center center fixed;
                background-size: cover;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .login-container {
                background: rgba(255, 255, 255, 0.9);
                backdrop-filter: blur(6px);
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.15);
                text-align: center;
                width: 340px;
            }
            .login-container img {
            width: 60px;
            margin-bottom: 15px;
            }

            .login-container h2 {
                margin-bottom: 20px;
                color: var(--brand-purple, #6a1b9a);
            }
            .login-container input {
                width: 100%;
                padding: 12px;
                margin: 8px 0;
                border: 1px solid #ccc;
                border-radius: 8px;
                font-size: 14px;
                box-sizing: border-box; /* keep consistent sizing */
            }
            .login-container button {
                width: 100%;
                padding: 12px;
                margin-top: 12px;  /* add spacing below password input */
                margin-bottom: 30px; /* add spacing above text for survey input */
                background: var(--brand-purple, #6a1b9a);
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 15px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                transition: transform 0.2s;
                box-sizing: border-box; /* match input sizing */
            }
            .login-container button:hover {
                transform: translateY(-2px);
                background: var(--brand-green, #2e7d32);
            }
            .survey-button {
                display: block;
                width: 100%;
                padding: 12px;
                margin-top: 15px; /* add spacing below text */
                background: var(--brand-purple, #6a1b9a);
                color: white;
                text-align: center;
                border-radius: 8px;
                text-decoration: none;
                font-size: 15px;
                /* font-weight: bold; */
                transition: background 0.2s;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                box-sizing: border-box; /* match input sizing */
            }
            .survey-button:hover {
                transform: translateY(-2px);
                background: var(--brand-green, #2e7d32);
            }
            .error {
                color: red;
                margin-bottom: 15px;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <img src="/static/green_leaf.png" alt="Logo">
            <h2>{% if step == 'login' %}SustainaBOS Login{% else %}Set Your New Password{% endif %}</h2>
            {% if error %}
                <p class="error">{{ error }}</p>
            {% endif %}
            <form method="post">
                {% if step == 'login' %}
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Login</button>
                {% else %}
                    <input type="password" name="new_password" placeholder="New Password" required>
                    <input type="password" name="confirm_password" placeholder="Confirm Password" required>
                    <button type="submit">Change Password</button>
                {% endif %}
            </form>

            <!-- Vessel survey button -->
            <h2>For Crew</h2>
            <a href="/survey" class="survey-button">Vessel Survey</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(login_page, step=step, error=error)

@app.route("/survey", methods=["GET", "POST"])
def survey():
    vessels = list(listvessel_df['BOS DUBAI'])  # your DataFrame
    #print(vessels)
    devices = list(listdevice_df['Device'])  # 15 devices
    #print(devices)

    # GET -> render survey form
    #vessels = [v.strip() for v in list(listdevice_df['Vessel Name'].unique())]  # or your vessel list
    #devices = [d.strip() for d in list(listdevice_df['Device'].unique())]      # your 15 initiatives

    if request.method == "POST":
        vessel_name = request.form.get("vessel")
        responses = {}
        for device in devices:
            responses[device] = request.form.get(device)

        new_survey = Survey(
            vessel_name=vessel_name,
            date=datetime.utcnow().date(),
            responses=responses
        )
        db.session.add(new_survey)
        db.session.commit()
        flash("Survey submitted successfully!", "success")
        return redirect(url_for("login"))

    # Render survey form
    survey_html = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <title>Vessel Survey</title>
      <style>
        body {{
          font-family: Arial, sans-serif;
          padding: 20px;
          background: #f9f9f9;
        }}
        .survey-container {{
          background: white;
          padding: 20px;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.2);
          max-width: 700px;
          margin: auto;
        }}
        h2 {{
          text-align: center;
          color: var(--brand-purple, #6a1b9a);
        }}
        select, button {{
          margin: 5px 0;
          padding: 8px;
          font-size: 14px;
          border-radius: 6px;
        }}
        .device-row {{
          margin-bottom: 12px;
        }}
        button {{
          background: var(--brand-purple, #6a1b9a);
          color: white;
          border: none;
          cursor: pointer;
          width: 100%;
          padding: 12px;
          font-size: 16px;
        }}
        button:hover {{
          background: var(--brand-green, #2e7d32);
        }}
      </style>
    </head>
    <body>
      <div class="survey-container">
        <h2>Vessel Survey</h2>
        <form method="post">
          <label for="vessel">Select Vessel:</label>
          <select name="vessel" required>
            {''.join([f"<option value='{v}'>{v}</option>" for v in vessels])}
          </select>
          <hr>
          <h3>Devices</h3>
    """

    # Add dropdown for each device
    for device in devices:
        survey_html += f"""
        <div class="device-row">
          <label>{device}:</label>
          <select name="{device}" required>
            <option value="">--Select--</option>
            <option value="Done">Done</option>
            <option value="No Need">No Need</option>
            <option value="In Progress">In Progress</option>
            <option value="Not Installed">Not Installed</option>
          </select>
        </div>
        """

    survey_html += """
          <button type="submit">Submit Survey</button>
        </form>
      </div>
    </body>
    </html>
    """

    return survey_html

@app.route("/survey-results")
def survey_results():
    surveys = Survey.query.order_by(Survey.date.desc()).all()

    results_html = """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <title>Survey Results</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 20px; background: #f9f9f9; }
        .survey-container { background: white; padding: 20px; border-radius: 12px;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.2); max-width: 900px; margin: auto; }
        h2 { text-align: center; color: var(--brand-purple, #6a1b9a); }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: var(--brand-purple, #6a1b9a); color: white; }
        tr:nth-child(even) { background: #f3f3f3; }
      </style>
    </head>
    <body>
      <div class="survey-container">
        <h2>Survey Results</h2>
        <table>
          <tr>
            <th>Date</th>
            <th>Vessel</th>
            <th>Responses</th>
          </tr>
    """

    for s in surveys:
        responses_text = "<br>".join([f"<b>{k}</b>: {v}" for k, v in s.responses.items()])
        results_html += f"""
          <tr>
            <td>{s.date}</td>
            <td>{s.vessel_name}</td>
            <td>{responses_text}</td>
          </tr>
        """

    results_html += """
        </table>
      </div>
    </body>
    </html>
    """

    return results_html


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route("/metrics")
def metrics():
    if session.get("user") != "Axel":
        abort(403)
    data = Metric.query.order_by(Metric.timestamp.desc()).all()
    return render_template_string("""
    <div class="container section content">
      <h2>Metrics</h2>
      <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%;">
        <thead>
          <tr style="background:#f0f0f0;">
            <th>Metric</th>
            <th>Value</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>
          {% for m in data %}
          <tr>
            <td>{{ m.metric_name }}</td>
            <td>{{ m.value }}</td>
            <td>{{ m.timestamp.strftime("%Y-%m-%d %H:%M:%S") }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      <p><a href="{{ url_for('admin_dashboard') }}">Back to Admin Dashboard</a></p>
    </div>
    """, data=data)

#region admin

@app.route("/admin")
def admin_dashboard():
    if session.get("user") != "Axel":
        abort(403)  # Forbidden

    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Admin Dashboard - SustainaBOS</title>
        <style>
            body {
                font-family: 'Segoe UI', sans-serif;
                background: #f5f5f5;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 1000px;
                margin: 40px auto;
                padding: 20px;
            }
            h2 {
                text-align: center;
                margin-bottom: 30px;
                color: #333;
            }
            .card-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 20px;
            }
            .feature-card {
                background: white;
                padding: 20px;
                border-radius: 16px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
                text-decoration: none;
                color: inherit;
            }
            .feature-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 8px 20px rgba(0,0,0,0.15);
            }
            .feature-card .media {
                font-size: 32px;
                margin-bottom: 12px;
                color: #6a1b9a;
            }
            .feature-card h4 {
                margin: 10px 0 8px;
                color: #222;
            }
            .feature-card p {
                font-size: 14px;
                color: #555;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Admin Dashboard</h2>
            <div class="card-grid">
                <a href="{{ url_for('survey_results') }}" class="feature-card">
                    <div class="media">📋</div>
                    <h4>Survey Results</h4>
                    <p>View all vessel surveys.</p>
                </a>
                <a href="{{ url_for('chat') }}" class="feature-card">
                    <div class="media">💬</div>
                    <h4>Chat Log</h4>
                    <p>See all chat messages.</p>
                </a>
                <a href="{{ url_for('metrics') }}" class="feature-card">
                    <div class="media">📊</div>
                    <h4>Metrics</h4>
                    <p>Track technical KPIs and logs.</p>
                </a>
                <a href="{{ url_for('admin_add_user') }}" class="feature-card">
                    <div class="media">➕</div>
                    <h4>Create User</h4>
                    <p>Add new application users.</p>
                </a>
            </div>
        </div>
    </body>
    </html>
    """)


@app.route("/admin/add_user", methods=["GET", "POST"])
def admin_add_user():
    if session.get("user") != "Axel":
        abort(403)

    message = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if username:
            default_password = f"BOS{username.lower()}*"
            existing = User2.query.filter_by(username=username).first()
            if existing:
                message = f"User {username} already exists!"
            else:
                new_user = User2(
                    username=username,
                    password_hash=generate_password_hash(default_password)
                )
                db.session.add(new_user)
                db.session.commit()
                message = f"User {username} created with default password {default_password}"

    return render_template_string("""
    <div class="container section content">
      <h2>Add New User</h2>
      {% if message %}
        <p><strong>{{ message }}</strong></p>
      {% endif %}
      <form method="post">
        <input type="text" name="username" placeholder="Enter username" required>
        <button type="submit">Create User</button>
      </form>
      <p><a href="{{ url_for('admin_dashboard') }}">Back to Admin Dashboard</a></p>
    </div>
    """, message=message)


@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "POST":
        data = request.get_json()
        msg = data.get("message", "").strip()
        user = session.get("user", "Anonymous")

        if msg:
            new_msg = ChatMessage(user=user, message=msg)
            db.session.add(new_msg)
            db.session.commit()

        return jsonify({"status": "ok"})

    else:  # GET request
        messages = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).all()
        return jsonify([
            {"user": m.user, "message": m.message, "time": m.timestamp.isoformat()}
            for m in messages
        ])


@app.route('/notify_new_device', methods=['POST'])
def notify_new_device():
    data = request.json
    vessel = data.get("vessel")
    device = data.get("device")

    # Build the email
    sender = os.getenv("SMTP_USER")  # your email (set as env variable)
    recipient = "axel.faurax@britoil.com.sg"
    msg = MIMEText(f"🚢 New device added!\n\nVessel: {vessel}\nDevice: {device}")
    msg['Subject'] = "New Device Notification"
    msg['From'] = sender
    msg['To'] = recipient

    # Log into database
    log = DeviceLog(action="add_device", vessel_name=vessel, device_name=device)
    db.session.add(log)
    db.session.commit()

    try:
        # Connect to your mail server (Office365)
        with smtplib.SMTP(os.getenv("SMTP_SERVER", "smtp.office365.com"), int(os.getenv("SMTP_PORT", 587))) as server:
            server.starttls()
            server.login(sender, os.getenv("SMTP_PASS"))
            server.sendmail(sender, [recipient], msg.as_string())

        return jsonify({"status": "success", "message": "Notification sent"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

#region init 
#@app.route("/init-db")
#def init_db():
    #with app.app_context():
        #db.create_all()  #for creating tabs not created yet
        #seed_users()      # seeds your initial users if not present
    #return "Database initialized!"
    #return "users sent"

# If data cna be lost , to destroy table :
# (So can modify tables code (class) and re create tabs) Here is code
# with app.app_context():
    #db.drop_all()
    #db.create_all()
    #seed_users() #If still password case


if __name__ == '__main__':
    app.run(debug=True)
