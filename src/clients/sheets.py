import gspread
from gspread.exceptions import APIError
from oauth2client.service_account import ServiceAccountCredentials
import time
import src.utils.utils as utils

class GoogleSheetHandler:

    def __init__(self, json_credential_file, spreadsheet_name="16img22ajmEOcVyWrS3sdXSneN0imFqT0VDYpYpCfLe8"):
        # Set up the credentials
        scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(json_credential_file, scope)
        client = gspread.authorize(creds)

        # Open the spreadsheet and worksheet
        self.spreadsheet = client.open_by_key(spreadsheet_name)
    

    def select_worksheet(self, worksheet_name):
        self.worksheet = self.spreadsheet.worksheet(worksheet_name)


    def get_data_as_dict(self, worksheet_name):
        try:
            self.select_worksheet(worksheet_name)
            return self.worksheet.get_all_records()
        except APIError as e:
            utils.logger.error(f"Google Sheets API Error Occurred. {str(e)} Retrying in 80 seconds.")
            time.sleep(80)
            return self.get_data_as_dict(worksheet_name)
    
    def dict_to_list_of_lists(self, dict_list):
        # Ensure there are records to process
        if not dict_list:
            return []

        # Step 1: Get the Column Headers
        headers = list(dict_list[0].keys())

        # Step 2: Create the First Row
        list_of_lists = [headers]

        # Step 3: Iterate and Collect Values
        for record in dict_list:
            row = [record[header] for header in headers]
            
            # Step 4: Append Each Row
            list_of_lists.append(row)

        return list_of_lists
    
    def update_cells(self, result):
        counter = 0
        cell_list = self.worksheet.range(1, 1, len(result), len(result[0]))
        for _, row in enumerate(result):
            for _, col in enumerate(row):
                try:
                    col = col.strip("'")
                except Exception:
                    pass
                cell_list[counter].value = col
                counter += 1
        self.worksheet.update_cells(cell_list, value_input_option="USER_ENTERED")


    def reflect_changes_to_sheet(self, data_list, worksheet_name):
        # Use the batch update method for faster writes
        if len(data_list) == 0:
            return
        for t in range(3):
            try:
                self.select_worksheet(worksheet_name)
                data=self.dict_to_list_of_lists(data_list)
                self.update_cells(data)
                utils.logger.info(f"Change reflected to sheet {worksheet_name}")
                break
            except APIError as e:
                utils.logger.warning(e)
                time.sleep(80)
                continue

    def get_col_number(self, col_name):
        # Get all the values in the first row
        first_row = self.worksheet.row_values(1)
        # Find and return the column number for the specified column name
        return first_row.index(col_name) + 1

    def update_sheet_cell_based_on_column_condition(self, worksheet_name, condition_col_name, condition, target_col_name, new_value):
        for t in range(3):
            try:
                self.select_worksheet(worksheet_name)
                # Get column numbers from column names
                condition_col_number = self.get_col_number( condition_col_name)
                target_col_number = self.get_col_number(target_col_name)

                # Fetch the data in the condition column
                condition_values = self.worksheet.col_values(condition_col_number)

                # Iterate and update the target column based on the condition
                for i, value in enumerate(condition_values, start=1):
                    if value == condition:
                        # utils.logger.info(f"{i}, {target_col_number}, {new_value}")
                        self.worksheet.update_cell(i, target_col_number, new_value)
                break
            except APIError as e:
                utils.logger.warning(e)
                time.sleep(80)
                continue

    def update_sheet_cell_based_on_two_column_conditions(self, worksheet_name, condition_col_name1, condition1, condition_col_name2, condition2, target_col_name, new_value):
        for t in range(3):
            try:
                self.select_worksheet(worksheet_name)
                # Get column numbers from column names
                condition_col_number1 = self.get_col_number(condition_col_name1)
                condition_col_number2 = self.get_col_number(condition_col_name2)
                target_col_number = self.get_col_number(target_col_name)

                # Fetch the data in both condition columns
                condition_values1 = self.worksheet.col_values(condition_col_number1)
                condition_values2 = self.worksheet.col_values(condition_col_number2)

                # Iterate and update the target column based on both conditions
                for i, (value1, value2) in enumerate(zip(condition_values1, condition_values2), start=1):
                    if value1 == condition1 and value2 == condition2:
                        # utils.logger.info(f"{i}, {target_col_number}, {new_value}")
                        self.worksheet.update_cell(i, target_col_number, new_value)
                break
            except APIError as e:
                utils.logger.warning(e)
                time.sleep(80)
                continue

    def update_sheet_cell_based_on_three_column_conditions(self, worksheet_name, condition_col_name1, condition1, condition_col_name2, condition2, condition_col_name3, condition3, target_col_name, new_value):
        for t in range(3):
            try:
                self.select_worksheet(worksheet_name)
                # Get column numbers from column names
                condition_col_number1 = self.get_col_number(condition_col_name1)
                condition_col_number2 = self.get_col_number(condition_col_name2)
                condition_col_number3 = self.get_col_number(condition_col_name3)
                target_col_number = self.get_col_number(target_col_name)

                # Fetch the data in both condition columns
                condition_values1 = self.worksheet.col_values(condition_col_number1)
                condition_values2 = self.worksheet.col_values(condition_col_number2)
                condition_values3 = self.worksheet.col_values(condition_col_number3)

                # Iterate and update the target column based on both conditions
                for i, (value1, value2, value3) in enumerate(zip(condition_values1, condition_values2, condition_values3), start=1):
                    if value1 == condition1 and value2 == condition2 and value3 == condition3:
                        # utils.logger.info(f"{i}, {target_col_number}, {new_value}")
                        self.worksheet.update_cell(i, target_col_number, new_value)
                break
            except APIError as e:
                utils.logger.warning(e)
                time.sleep(80)
                continue

    def append_data_to_worksheet(self, data, worksheet_name):
        """
        data: list of dicts
        """
        self.select_worksheet(worksheet_name)
        rows_new = len(data)
        rows_old = self.worksheet.row_count
        rows = rows_new + rows_old
        if rows > 0:
            cols = len(data[0].keys())
        else:
            cols = 0
        if self.worksheet.col_count != cols:
            print(self.worksheet.col_count, cols, "Wrong columns number to append to worksheet")
            return
        self.worksheet.resize(rows, cols)
        cell_list = self.worksheet.range(rows_old + 1, 1, rows, cols)
        counter = 0
        for row in data:
            for col, value in row.items():
                try:
                    col = col.strip("'")
                except Exception:
                    pass
                cell_list[counter].value = value
                counter += 1
        self.worksheet.update_cells(cell_list, value_input_option="USER_ENTERED")
        return self.worksheet