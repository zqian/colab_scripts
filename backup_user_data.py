import argparse
import csv
import json
import logging
import os
from canvasapi import Canvas
from pathlib import Path

# Add a handler to log to the console
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Turn on logging for the Canvas API
logger = logging.getLogger("canvasapi")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Add a logger for this class
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.addHandler(handler)

class CanvasBackup:
    def __init__(self, api_url, api_key):
        self.canvas = Canvas(api_url, api_key)

    def get_user_data(self, user_id):
        user_data = {}

        # Retrieve user communication channels
        user = self.canvas.get_user(user_id, id_type='sis_user_id')
        communication_channels = user.get_communication_channels()
        user_data['communication_channels'] = [
            {
                'id': channel.id,
                'type': channel.type,
                'address': channel.address,
                'position': channel.position,
                'user_id': channel.user_id,
                'workflow_state': channel.workflow_state,
            }
            for channel in communication_channels
        ]

        # Retrieve user group memberships
        courses = user.get_courses()
        user_data['groups'] = []
        
        for course in courses:
            groups = course.get_groups()
            for group in groups:
                if user.id in [member.id for member in group.get_users()]:
                    user_data['groups'].append({
                        'course_id': course.id,
                        'course_name': course.name,
                        'group_id': group.id,
                        'group_name': group.name
                    })

        return user_data


    def save_to_json(self, data, output_path):
        with open(output_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)

    def backup_users(self, csv_file, output_file):
        results = []

        # Read the CSV and process each user
        with open(csv_file, newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                user_id = row['user_id']
                user_data = self.get_user_data(user_id)
                results.append({'user_id': user_id, 'data': user_data})

        # Save results to JSON
        self.save_to_json(results, output_file)

def main():
    # Retrieve API settings from environment variables
    api_url = os.getenv('API_BASE_URL')
    api_key = os.getenv('API_KEY')

    if not api_url or not api_key:
        raise EnvironmentError("API_BASE_URL and API_KEY must be set in the environment.")

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Backup user data from Canvas.")
    parser.add_argument('csv_file', type=Path, help="Path to the CSV file containing user IDs.")
    parser.add_argument('output_file', type=Path, help="Path to the output JSON file.")
    args = parser.parse_args()

    # Initialize backup process
    backup = CanvasBackup(api_url, api_key)
    backup.backup_users(args.csv_file, args.output_file)

if __name__ == "__main__":
    main()
