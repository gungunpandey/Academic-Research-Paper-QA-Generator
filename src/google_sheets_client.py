import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import os

class GoogleSheetsClient:
    """
    A client to interact with Google Sheets for the research paper pipeline.
    """
    def __init__(self, credentials_path, sheet_name):
        """
        Initializes the client and authenticates with Google Sheets.

        Args:
            credentials_path (str): The path to the Google API credentials JSON file.
            sheet_name (str): The name of the Google Sheet to interact with.
        """
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Credentials file not found at: {credentials_path}")

        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        self.credentials = Credentials.from_service_account_file(credentials_path, scopes=self.scopes)
        self.gc = gspread.authorize(self.credentials)
        self.sheet = self.gc.open(sheet_name).sheet1
        print(f"Successfully connected to Google Sheet: '{sheet_name}'")

    def get_all_records_as_df(self):
        """
        Fetches all records from the sheet and returns them as a pandas DataFrame.

        Returns:
            pd.DataFrame: A DataFrame containing all the records from the sheet.
        """
        records = self.sheet.get_all_records()
        return pd.DataFrame(records)

    def update_status(self, row_index, column_name, status):
        """
        Updates a specific cell in the sheet to reflect a new status.
        Note: The gspread library uses 1-based indexing for rows and columns.
              The row_index here should correspond to the row number in the Google Sheet UI.

        Args:
            row_index (int): The index of the row to update (1-based).
                           The header is row 1, so data starts at row 2.
            column_name (str): The name of the column to update (e.g., 'extraction_status').
            status (str): The new status to write in the cell (e.g., 'In Progress', 'Completed').
        """
        try:
            # Find the column number (1-based) from its header name
            col_index = self.sheet.find(column_name).col
            self.sheet.update_cell(row_index, col_index, status)
            print(f"Updated row {row_index}, column '{column_name}' to '{status}'")
        except gspread.exceptions.CellNotFound:
            print(f"Error: Column '{column_name}' not found in the sheet.")
        except Exception as e:
            print(f"An error occurred while updating the sheet: {e}")

if __name__ == '__main__':
    
    creds_path = 'credentials.json'
    sheet_name_placeholder = "Research_Paper_Metadata" 
    
    if not os.path.exists(creds_path):
        print("FATAL: credentials.json not found.")
        print("Please follow the setup instructions to get your credentials file.")
    elif sheet_name_placeholder == "YOUR_GOOGLE_SHEET_NAME":
        print("FATAL: Please replace 'YOUR_GOOGLE_SHEET_NAME' with your actual sheet name.")
    else:
        try:
            client = GoogleSheetsClient(credentials_path=creds_path, sheet_name=sheet_name_placeholder)
            df = client.get_all_records_as_df()
            print("\nSuccessfully fetched data from Google Sheet:")
            print(df.head())

            # Example of updating a cell (e.g., setting the status of the first data row)
            if not df.empty:
                 # The first data row is at index 2 in Google Sheets (row 1 is the header)
                client.update_status(row_index=2, column_name='notes', status='Test successful')

        except Exception as e:
            print(f"\nAn error occurred during the example run: {e}") 