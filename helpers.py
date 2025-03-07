import pandas as pd
from models import db, Map
import pickle

def load_dataframe(file_path):
    """
    Load a CSV or Excel file into a Pandas DataFrame.
    
    Parameters:
        file_path (str): The path to the CSV or Excel file.
        
    Returns:
        pd.DataFrame: The loaded DataFrame.
    """
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    elif file_path.endswith(('.xls', '.xlsx')):
        return pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format. Please provide a CSV or Excel file.")

# Example usage:
# df = load_dataframe("data.csv")
# df = load_dataframe("data.xlsx")


def add_map_record(sheetname, sitename, metadata, data):
    """
    Adds a new record to the Map table with pickled data.

    Parameters:
        sheetname (str): The name of the sheet.
        sitename (str): The site name.
        data (any): The data to store (pickled).

    Returns:
        Map: The newly created Map record.
    """
    # Pickle the data before storing it in the database
    pickled_data = data
    pickled_metadata = metadata
    # Create a new record with the pickled data
    new_record = Map(sheetname=sheetname, sitename=sitename, mapmetadata = pickled_metadata, data=pickled_data)
    # Add the new record to the session and commit the changes
    db.session.add(new_record)
    db.session.commit()
    return new_record

def get_map_record(map_id):
    """
    Retrieves a Map record from the database, unpacks it, and unpickles necessary columns.

    Parameters:
        map_id (int): The ID of the map record to retrieve.

    Returns:
        dict: A dictionary containing the sheetname, sitename, metadata, and data.
    """
    # Fetch the record from the database
    map_entry = Map.query.get_or_404(map_id)

    # Unpickle metadata and data
    #mapmetadata = pickle.loads(map_entry.metadata)
    data = pd.DataFrame(map_entry.data)  # Convert back to DataFrame

    return {
        "sheetname": map_entry.sheetname,
        "sitename": map_entry.sitename,
        "metadata": map_entry.mapmetadata,
        "data": data,
        'status':map_entry.status,
        'notes':map_entry.notes
    }
