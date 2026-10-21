"""
Display an overview of the most recent record dates for each serial number in the database, only detection records.
"""

from oregon_processing.core.database_manager import DatabaseManager
from oregon_processing.core.project import Project
from oregon_processing.exceptions import ConfigNotFoundError, InvalidConfigError

def get_database_status():

    try:
        project = Project()

    except (ConfigNotFoundError, InvalidConfigError) as e:
        print(f"\n\n"+str(e) + "\n\nPlease ensure the configuration file is present and valid, then try again.")
        return

    database_manager = DatabaseManager(project)
    latest_record_dates = database_manager.get_last_exported_detection_record_dates()

    #sort from least recent to most recent
    latest_record_dates = dict(sorted(latest_record_dates.items(), key=lambda item: (item[1] is not None, item[1])))

    print("\nMost Recent Detection Record Dates by Serial Number:")
    for serial, record_date in latest_record_dates.items():
        if record_date:
            print(f"Serial Number: {serial} - Last Exported Detection Record Date: {record_date}")
        else:
            print(f"Serial Number: {serial} - No detection record files found.")

if __name__ == "__main__":
    get_database_status()
