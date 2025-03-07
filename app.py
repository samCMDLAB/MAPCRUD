import os
from flask import Flask, render_template, request, url_for, redirect, jsonify
from models import db, Map  # Import models
from helpers import load_dataframe, get_map_record, add_map_record
import folium
import pandas as pd
from markupsafe import Markup
from folium.elements import Element


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Ensure tables are created within the application context
with app.app_context():
    db.create_all()

# Create 'spreadsheets' folder if it doesn't exist
if not os.path.exists('spreadsheets'):
    os.makedirs('spreadsheets')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_spreadsheet():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part", 400
        
        file = request.files['file']
        if file.filename == '':
            return "No selected file", 400
        fileid  = len(os.listdir('spreadsheets')) + 1
        filename = f'{fileid}_{file.filename}'
        file.save(os.path.join('spreadsheets',filename))                     
        return redirect(url_for('map_setup', filename=filename))
    
    return render_template('upload.html')


@app.route('/map_setup', methods=['GET', 'POST'])
def map_setup():
    filename = request.args.get('filename', None)
    if not filename:
        return "Filename is missing", 400
    
    file_path = os.path.join('spreadsheets', filename)
    df = load_dataframe(file_path)
    columns = df.columns.tolist()
    
    if request.method == 'POST':
        tooltip_columns = request.form.getlist('tooltip_columns')
        lat_column = request.form.get('lat_column')
        lon_column = request.form.get('lon_column')
        id_column = request.form.get('id_column')  # New: Capture the ID column
        map_type = request.form.get('map_type')

        if not lat_column or not lon_column:
            return "Latitude and Longitude fields are required", 400
        if not id_column:
            return "A Unique ID column is required", 400  # Ensure ID column is selected
        
        metadata = {
            "tooltip_columns": tooltip_columns,
            "lat_column": lat_column,
            "lon_column": lon_column,
            "id_column": id_column,  # New: Add ID column to metadata
            "map_type": map_type
        }
        
        if map_type != "heatmap":
            status_marker = request.form.get('status_marker')
            notes_section = request.form.get('notes_section')
            
            if status_marker == "yes":
                status_titles = request.form.getlist('status_titles[]')
                status_colors = request.form.getlist('status_colors[]')
                
                if len(status_titles) != len(status_colors):
                    return "Each status must have a corresponding color", 400
                
                metadata["status_marker"] = status_marker
                metadata["status_data"] = dict(zip(status_titles, status_colors))
            
            metadata["notes_section"] = notes_section
        
        new_map = add_map_record(
            sheetname=filename, 
            sitename=filename.split("_")[0], 
            metadata=metadata, 
            data=df
        )
        db.session.add(new_map)
        db.session.commit()
        
        return redirect(url_for('view_map', map_id=new_map.id))
    
    return render_template('map_setup.html', filename=filename, columns=columns)


@app.route('/view_map/<int:map_id>')
def view_map(map_id):
    map_entry = get_map_record(map_id)
    if not map_entry:
        return "Map not found", 404

    df = pd.DataFrame(map_entry["data"])
    lat_column = map_entry["metadata"]["lat_column"]
    lon_column = map_entry["metadata"]["lon_column"]
    id_column = map_entry["metadata"].get("id_column", None)  # Get ID column from metadata
    tooltip_columns = map_entry["metadata"]["tooltip_columns"]

    df.dropna(subset=[lat_column, lon_column], inplace=True)

    if map_entry["metadata"]['map_type'] != "heatmap":
        meta_status = map_entry['metadata']['status_data']
        meta_status.update({"default": "#808080" })
        status_dict = map_entry.get("status", {}) or {}
        notes_dict = map_entry.get("notes", {}) or {}

        markers_data = []
        for _, row in df.iterrows():
            lat, lon = row[lat_column], row[lon_column]
            unique_id = str(row[id_column]) if id_column and id_column in row else f"{lat},{lon}"  # Use ID if available, else fallback

            status = status_dict.get(unique_id, "default")  # Use unique_id as key
            note = notes_dict.get(unique_id, "")

            tooltip = {col: row[col] for col in tooltip_columns}

            markers_data.append({
                "lat": lat,
                "lon": lon,
                "status": status,
                "note": note,
                "tooltip": tooltip,
                "id": unique_id,  # Include unique ID
                "mapid": map_id
            })
        heatmap_data = None
    else:
        meta_status = None
        heatmap_data = []
        intensity_column = map_entry["metadata"].get("intensity_column", None)

        if intensity_column:
            for _, row in df.iterrows():
                lat, lon, intensity = row[lat_column], row[lon_column], row[intensity_column]
                heatmap_data.append([lat, lon, intensity])
        else:
            for _, row in df.iterrows():
                lat, lon = row[lat_column], row[lon_column]
                heatmap_data.append([lat, lon, 1])  # Default intensity of 1 if not specified.

        markers_data = None

    # Pass data to the template
    return render_template(
        'view_map.html', 
        markers_data=markers_data, 
        meta_status=meta_status, 
        heatmap_data=heatmap_data, 
        map_type=map_entry["metadata"]['map_type']
    )




@app.route('/update_point', methods=['POST'])
def update_point():
    data = request.json
    map_id = data.get("map_id")
    marker_id = data.get("id")  # Use marker ID instead of latlon

    if not map_id or not marker_id:
        print(data)
        return {"error": "Invalid request - missing map_id or marker_id"}, 400

    # Retrieve map record using helper function
    map_entry = get_map_record(map_id)
    if not map_entry:
        return {"error": "Map not found"}, 404

    # Extract existing status and notes dictionaries
    status_dict = map_entry.get("status", {}) or {}
    notes_dict = map_entry.get("notes", {}) or {}

    # Update status if provided
    if "status" in data:
        status_dict[marker_id] = data["status"]

    # Update note if provided
    if "note" in data:
        notes_dict[marker_id] = data["note"]

    # Fetch the actual database object to update
    db_map_entry = Map.query.get(map_id)
    db_map_entry.status = status_dict
    db_map_entry.notes = notes_dict

    # Commit changes to the database
    db.session.commit()

    return {"message": "Update successful"}


@app.route('/update_point_ext', methods=['GET'])
def update_point_ext():
    map_id = request.args.get("map")
    marker_id = request.args.get("id")
    status = request.args.get("status")
    note = request.args.get("note")

    if not map_id or not marker_id:
        return {"error": "Missing required parameters"}, 400

    map_entry = get_map_record(map_id)
    if not map_entry:
        return {"error": "Map not found"}, 404

    status_dict = map_entry.get("status", {}) or {}
    notes_dict = map_entry.get("notes", {}) or {}

    # Only overwrite if explicitly passed and non-empty
    if status is not None and status.strip() != "":
        status_clean = status.replace('"', '').replace("'", "").strip()
        status_dict[marker_id] = status_clean

    if note is not None and note.strip() != "":
        notes_dict[marker_id] = note.strip()

    db_map_entry = Map.query.get(map_id)
    db_map_entry.status = status_dict
    db_map_entry.notes = notes_dict
    db.session.commit()

    return {"message": "Update successful"}


if __name__ == '__main__':
    app.run(debug=True)
    