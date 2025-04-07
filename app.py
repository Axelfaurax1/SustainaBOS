import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template_string

# Load the Excel file with specified column names starting from row 8 and column B
file_path = 'Vessel_Device_Installation_Tracker NV.xlsx'
column_names = ['Vessel Name/ ID', 'Spec', 'Devices', 'Installation Status', 'Date of Installation', 'Savings/year (fuel efficiency)', 'Savings/year (Maitenance)', 'Co2 savings ton/year']
df = pd.read_excel(file_path, engine='openpyxl', names=column_names, skiprows=7, usecols="B:I")

list_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Tracker', skiprows=6, nrows=399, usecols="B:I")

# Load the summary sheet
summary_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=0,  nrows=11, usecols="A:E")

summary2_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=14,  nrows=3, usecols="B:C")

summary3_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=0,  nrows=4, usecols="I:K")

# Load the list of vessel
listvessel_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=19,  nrows=68, usecols="A")

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

# Create a Flask app
app = Flask(__name__)

# HTML template for the website with improved design and images
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Fleet Sustainability View</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #E8F5E9; margin: 0; padding: 0; }
        .container { width: 80%; margin: auto; overflow: hidden; }
        header { background: #D0E8D0; color: #800080; padding-top: 20px; min-height: auto; border-bottom: #800080 2px solid; }
        header a { color: #800080; text-decoration: none; text-transform: none; font-size: 16px; font-weight: bold;}
        header ul { padding: 0; list-style: none; }
        header li { display: inline; padding: 0 10px 0 10px; }
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
            box-shadow: 0 0 30px rgba(0, 255, 0, 1);
            transform: scale(1.1);
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
           height: 60px;
           width: 60px;
           display: flex;
           justify-content: center;
           align-items: center;
           z-index: 10000;
           transition: transform 0.3s ease;
           animation: glow 1.5s ease-in-out infinite alternate;
           }
        #fab-button:hover {
           transform: scale(1.1);
           }
        #fab-button img {
           height: 36px;
           width: 36px;
           object-fit: contain;
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
           animation: fadeOut 2s ease 1 forwards;
           animation-delay: 1s;
        }
        #splash-title {
            font-size: 46px;
            font-weight: bold;
            display: flex;
            justify-content: center;
            align-items: center;
            animation: slideLeft 1s ease 1 forwards;
            animation-delay: 1s; 
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
           animation-delay: 1s;
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
        function showSection(sectionId) {
            var sections = document.getElementsByClassName('section');
            for (var i = 0; i < sections.length; i++) {
                sections[i].style.display = 'none';
            }
            document.getElementById(sectionId).style.display = 'block';
        }
        function addDevice() {
        console.log("Add Device button clicked");
        currentAction = "addDevice"; // Store the action type
        showVesselSelector();
        }
        function modifyStatus() {
        console.log("Modify Status button clicked");
        currentAction = "modifyStatus"; // Store the action type
        showVesselSelector();
        }
        function showVesselSelector() {
        const vesselSelector = document.getElementById('vesselSelector');
        vesselSelector.style.display = 'block';
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
           }
        }
    </script>
</head>
<body>
    <div id="splash">
    <img src="{{ url_for('static', filename='green_leaf.png') }}" alt="Logo" id="splash-logo">
    <div id="splash-title">
        <span class="green">Sustaina</span><span class="purple">BOS</span>
    </div>
    </div>
    <a href="javascript:void(0);" id="fab-button" title="Reload Page">
    <img src="{{ url_for('static', filename='green_leaf.png') }}" alt="FAB Logo">
    </a>
    <header>
      <div class="container">
        <div id="branding">
          <img src="{{ url_for('static', filename='britoil_logo.png') }}" alt="Britoil Offshore Services Logo" style="height:38px;">
          
          <h1>Fleet Sustainability View</h1>
          <br>
        </div>
        <nav>
          <ul>
            <li><a href="#" onclick="showSection('welcome')">Home</a></li>
            <li><a href="#" onclick="showSection('list')">List</a></li>
            <li><a href="#" onclick="showSection('analytics')">Analytics</a></li>
            <li><a href="#" onclick="showSection('contact')">Contact</a></li>
          </ul>
        </nav>
      </div>
    </header>
    <div class="container">
      <div id="welcome" class="section content">
          <h2>Welcome</h2>
          <p>Here is <b><span class="green">Sustaina</span><span class="purple">BOS</span></b>, the website for the fleet sustainability year review. Usage is for Britoil staff only. Visitors or customers can visite our sustainability section on our website : <a href="https://www.britoil.com.sg/sustainability">Britoil Website</a> <br> <br>  
The purpose of this tool is:  
<ul>
    <li>To track the implementation of new solutions.</li>
    <li>To provide a quantified overview of total savings and CO2 equivalent.</li>
    <li>To compare vessels and assess their performance.</li>
    <li>To offer additional analytics for deeper insights (see section).</li>
</ul>
For more information, please contact Axel Faurax directly (see contact section). The tool is currently under development to offer as many features as possible.
          </p>
          
          <h3>Overall yearly results :</h3>
          <table>
              {% for index, row in summary2_df.iterrows() %}
              <tr>
                  {% for col_index in range(row.size) %}
                  {% set value = row.iloc[col_index] %}
                  {% if col_index == 1 and index == 0 %}
                  <td style="font-weight: bold; color: green;">
                      {{ "{:,.2f} $".format(value|float|int) }}
                  </td>
                  {% elif col_index == 1 %}
                  <td style="font-weight: bold; color: green;">{{ value|float|int }}</td>
                  {% else %}
                  <td>{{ value }}</td>
                  {% endif %}
                  {% endfor %}
              </tr>
              {% endfor %}
          </table>
          <br>
          <img src="{{ url_for('static', filename='view2.png') }}"      alt="ESG" style="height:400px; display: block; margin: auto;">
          <h3>Green News :</h3>
          <p> <b> BOS Princess: Successfully Converted Into Geotechnical Drilling Vessel </b> 🛠 <br> <br>
          We are pleased to announce the successful conversion of the BOS Princess from a Platform Supply Vessel              (PSV) into a Geotechnical Drilling Vessel, enhancing our capabilities in support of the offshore wind industry.
          <br> <br>
          As part of this transformation, Besiktas Shipyard carried out a Moon Pool opening, Rig Tower, and A-frame installation to enhance BOS Princess’ geotechnical support capabilities. Additionally, the vessel also underwent an Azimuth Thruster maintenance and a comprehensive overhaul to ensure optimal performance in demanding offshore conditions.
          <br> <br>
          With these upgrades, BOS Princess will provide a stable and efficient platform for Seas Geosciences’ geotechnical investigations, further strengthening our commitment to advancing offshore wind energy. </p>
          <br> <br>
          <img src="{{ url_for('static', filename='Princess.jpeg') }}"      alt="Princess" style="height:600px; display: block; margin: auto;">
      <br>
      <h2><span class="green">Sustaina</span><span class="purple">BOS</span> </h2>
      Powered by Axel FAURAX and Technical Department.
      </div>
      <div id="list" class="section content hidden">
          <div style="margin-bottom: 20px;">
             <button onclick="addDevice()" style="margin-right: 10px; font-size: 18px; padding: 10px 20px; color: purple;">+ Add Devices</button>
             <button onclick="modifyStatus()" style="margin-right: 10px; font-size: 18px; padding: 10px 20px; color: purple;">Modify Status</button>
             <button onclick="modifyStatus()" style="font-size: 18px; padding: 10px 20px; color: purple;">Show Vessel</button>
          </div>
          <div id="vesselSelector" style="margin-top: 20px; display: none;">
             <label for="vesselDropdown" style="font-size: 18px; color: purple;">Which vessel?</label>
             <select id="vesselDropdown" style="font-size: 16px; padding: 5px 10px; margin-left: 10px;">
                {% for vessel in listvessel_df['BOS DUBAI'] %}
                    <option value="{{ vessel }}">{{ vessel }}</option>
                {% endfor %}
             </select>
             <button onclick="confirmVesselSelection()" style="font-size: 18px; padding: 10px 20px; color: purple; margin-top: 10px;">Ok</button>
          </div>
          <br>
          <h3>New Initiatives - Look</h3>
          <img src="{{ url_for('static', filename='initiatives1.png') }}"      alt="ini" style="height:300px; display: block; margin: auto;">
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
                     <span style="color: {% if value >= 0.50 %}green{% elif value >= 0.15 and value < 0.50 %}orange{% else %}red{% endif %}; font-weight: bold;"> 
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
                 {% elif col_index in [6, 7, 8] %}
                 <td style="color: green;">
                    {% if value == "nan" or value is none %}
                    <!-- Display empty cell for "nan" values -->
                    {{ "" }}
                    {% else %}
                    {{ value | int | replace('0', '')}}
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
      <div id="analytics" class="section content hidden">
          <h2>Analytics</h2>
          <h3>Introduction</h3>
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
                  <td style="font-weight: bold; color: orange;">
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
      <div id="contact" class="section content hidden">
          <h2>Contact</h2>
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
      document.getElementById("fab-button").addEventListener("click", function() {
            location.reload(); // Reloads the current page
        });
   </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html_template, vessel_devices=vessel_devices, list_df=list_df, summary_df=summary_df, summary2_df=summary2_df, summary3_df=summary3_df, listvessel_df=listvessel_df)

if __name__ == '__main__':
    app.run(debug=True)
