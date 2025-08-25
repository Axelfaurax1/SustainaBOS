import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template_string, request, redirect, url_for, session
import os
import smtplib
from email.mime.text import MIMEText

# Create a Flask app
app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-now")  # set a real value in Render later

# --- Simple users (change these!) ---
users = {
    "Axel": "BOSaxfa*",
    "admin": "secret123",
    "Mohit": "BOSmosa*",
    "Florent": "BOSflki*",
    "Julian": "BOSjuoh*"
}


# Load the Excel file with specified column names starting from row 8 and column B
file_path = 'Vessel_Device_Installation_Tracker NV.xlsx'
column_names = ['Vessel Name/ ID', 'Spec', 'Devices', 'Installation Status', 'Date of Installation', 'Savings/year (fuel efficiency)', 'Savings/year (Maitenance)', 'Co2 savings ton/year']
df = pd.read_excel(file_path, engine='openpyxl', names=column_names, skiprows=7, usecols="B:I")

list_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Tracker', skiprows=6, nrows=428, usecols="B:J")

# Load the summary sheet
summary_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=0,  nrows=16, usecols="A:F")

summary2_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=15,  nrows=3, usecols="B:C")

summary3_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=0,  nrows=4, usecols="I:K")

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
listvessel_df = pd.read_excel(file_path, engine='openpyxl', sheet_name='Summary', skiprows=24,  nrows=70, usecols="A")

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


# HTML template for the website with improved design and images
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>SustainaBOS</title>
    <link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}" type="image/x-icon">
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

        function modifyStatus() {
        console.log("Modify Status button clicked");
        currentAction = "modifyStatus"; // Store the action type
        showVesselSelector();
        }

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
            <li><a id="nav-welcome" href="#" onclick="showSection('welcome')">Home</a></li>
            <li><a id="nav-list" href="#" onclick="showSection('list')">List</a></li>
            <li><a id="nav-analytics" href="#" onclick="showSection('analytics')">Analytics</a></li>
            <li><a id="nav-report" href="#" onclick="showSection('report')">Report</a></li>
            <li><a id="nav-contact" href="#" onclick="showSection('contact')">Contact</a></li>
          </ul>
        </nav>
      </div>
    </header>

    <div class="container">
      <div id="welcome" class="section content">

          <iframe title="SustainaBOS2" width="950" height="200" src="https://app.powerbi.com/reportEmbed?reportId=1062d591-1686-420c-bd67-580dcef8cd4c&autoAuth=true&ctid=0bb4d87c-b9a5-49c3-8a59-4347acef01d8&navContentPaneEnabled=false&filterPaneEnabled=false" frameborder="0" allowFullScreen="true"></iframe>

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
          
          <!-- <h3>Overall yearly results :</h3>
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
          </table> -->

          <h3>Scope 1, 2, 3 - Reminder :</h3>
          <p> Here is both an explanation and a reminder of what we called Scopes in Sustainability. Also what it means for Britoil. Today Britoil is mainly focus on the third Scopes, because Scope 1 we are not paying the fuel, and Scope 2 has a minimal impact compare to the tow others. </p>

          <img src="{{ url_for('static', filename='Scopes.png') }}"      alt="Scopes" style="width:950px; display: block; margin: auto;">


          <br>
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

      <br>
      <br>
          <img src="{{ url_for('static', filename='view2.png') }}"      alt="ESG" style="height:400px; display: block; margin: auto;">


      </div>

      <div id="list" class="section content hidden">

          <!-- <p>This line is muted and won't appear on the page.</p> -->
          <!-- <div id="instruction-box" style="display: none; position: absolute; top: 150px; left: 70%; transform: translateX(-70%); background-color: #eef; padding: 25px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); z-index: 9999; transition: opacity 1s ease; opacity: 0;">
              <strong>Instructions</strong><br><br>
              By clicking on buttons <b>Show Vessel</b> and <b>Show Devices</b>, you can focus on the vessel or the device of your choice. <br><br>
 Exemple : Showing the devices of Defiance, or showing every vessel which have LED lights<br><br>
              <b>Please try!</b>
          </div> -->

          <div style="margin-bottom: 20px;">
             <button onclick="showVessel()" style="margin-right: 15px; font-size: 20px; padding: 20px 30px; color: purple;">Show One Vessel</button>
             <button onclick="showDevice()" style="margin-right: 15px; font-size: 20px; padding: 20px 30px; color: purple;">Show One Device</button>
             <button onclick="addDevice()" style="margin-right: 15px; font-size: 20px; padding: 20px 30px; color: purple;">+ Add Devices</button>
             <button onclick="modifyStatus()" style="margin-right: 15px; font-size: 20px; padding: 20px 30px; color: purple;">Modify Status</button>
             
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

      <div id="analytics" class="section content hidden">
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
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:b:/g/personal/axel_faurax_britoil_com_sg/EYadKUz1ndFGjab-1unbFBkB0diXBP36hvg2i0Bw240Ysg?e=UkaSer" target="_blank">🔗 MGPS Study</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:b:/g/personal/axel_faurax_britoil_com_sg/ERMqIzIiewBClWQiLKocjN8BdIuo2Ks6AVInt9oKMa-LZQ?e=dgdPCi" target="_blank">🔗 EFMS Study</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:p:/g/personal/axel_faurax_britoil_com_sg/Ea132zQliBVAu4Gc_H4ZSZcBzIcYKu7CWsLZGsyiaSCX5A?e=mqJhyx" target="_blank">🔗 IWTM Filters Study</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:p:/g/personal/axel_faurax_britoil_com_sg/Ee3lqUA0Cl5ApvCfcGaexv0BIv881MnJPRGPFBxgYCMPjw?e=oFyS5x" target="_blank">🔗 New Initiatives Presentation – Dubai 2024</a></li>
               <li style="margin-bottom: 12px;"><a href="https://britoilos-my.sharepoint.com/:p:/g/personal/axel_faurax_britoil_com_sg/EXAFSkLNyppFtbHGKCwqRyABAuUzok_kEdlRdhw-UxKoLQ?e=gyBv4R" target="_blank">🔗 New Initiatives 2025</a></li>
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
  
      window.onload = function() {
            showSection('welcome');

      };
   </script>

   </body>
</html>
"""

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
        listdevice_df=listdevice_df
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if username in users and users[username] == password:
            session['user'] = username
            session.permanent = True
            return redirect(url_for('index'))
        else:
            error = "Invalid username or password"
    else:
        error = None

    login_page = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Login</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: url('/static/imagelogin.JPG') no-repeat center center fixed;
                background-size: cover;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .login-container {{
                background: rgba(255, 255, 255, 0.9);
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                text-align: center;
                width: 350px;
            }}
            .login-container h2 {{
                margin-bottom: 20px;
            }}
            .login-container input {{
                width: 100%;
                padding: 10px;
                margin: 8px 0;
                border: 1px solid #ccc;
                border-radius: 6px;
            }}
            .login-container button {{
                width: 100%;
                padding: 12px;
                background: #007BFF;
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
            }}
            .login-container button:hover {{
                background: #0056b3;
            }}
            .error {{
                color: red;
                margin-bottom: 15px;
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <h2>Please Sign In</h2>
            {f'<p class="error">{error}</p>' if error else ''}
            <form method="post">
                <input type="text" name="username" placeholder="Username" required><br>
                <input type="password" name="password" placeholder="Password" required><br>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    """
    return login_page

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

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

    try:
        # Connect to your mail server (Office365)
        with smtplib.SMTP(os.getenv("SMTP_SERVER", "smtp.office365.com"), int(os.getenv("SMTP_PORT", 587))) as server:
            server.starttls()
            server.login(sender, os.getenv("SMTP_PASS"))
            server.sendmail(sender, [recipient], msg.as_string())

        return jsonify({"status": "success", "message": "Notification sent"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)