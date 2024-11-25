import csv
import os
import argparse
import logging
from canvasapi import Canvas
from canvasapi.util import combine_kwargs

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the Canvas API (conditionally based on dry-run)
def initialize_canvas_api(dry_run):
    if not dry_run:
        API_URL = os.getenv("CANVAS_API_URL")
        API_KEY = os.getenv("CANVAS_API_KEY")

        if not API_URL or not API_KEY:
            raise EnvironmentError("Please set the CANVAS_API_URL and CANVAS_API_KEY environment variables.")
        
        return Canvas(API_URL, API_KEY)
    return None

# Read users to process
def read_users_to_process(file_path):
    deleted_users = []
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['status'] == 'deleted':
                deleted_users.append(row)
    logging.info(f"Found {len(deleted_users)} users marked as deleted.")
    return deleted_users

# Read enrollments and filter only relevant ones
def read_enrollments(file_path, deleted_users):
    enrollments = []
    deleted_user_ids = {user['user_id'] for user in deleted_users}
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['user_id'] in deleted_user_ids:
                enrollments.append(row)
    logging.info(f"Retained {len(enrollments)} relevant enrollments from the enrollment file.")
    return enrollments

# Enroll users based on deleted status
def enroll_users(deleted_users, enrollments, canvas, dry_run=False):
    if not deleted_users or not enrollments:
        logging.warning("No users or enrollments to process.")
        return
    
    logging.info(f"Starting to process {len(deleted_users)} users for enrollment.")

    for deleted_user in deleted_users:
        user_id = deleted_user['user_id']
        
        # Find corresponding enrollment record
        for enrollment in enrollments:
            if enrollment['user_id'] == user_id:
                section_id = enrollment['canvas_section_id']  # Use section_id from the enrollment object
                base_role_type = enrollment['base_role_type']
                kwargs = {
                    "enrollment[user_id]": enrollment['canvas_user_id'],
                    "enrollment[type]": base_role_type,  # Use base_role_type as the type
                    "enrollment[enrollment_state]": "active",
                    # Add other necessary enrollment parameters here
                }

                if dry_run:
                    logging.info(f"Dry run: Would enroll user {user_id} in section {section_id} with type {base_role_type}")
                else:
                    logging.info(f"Enrolling user {user_id} in section {section_id}")
                    # Make the API call to enroll the user
                    response = canvas._requester.request(
                        "POST",
                        f"sections/{section_id}/enrollments",
                        _kwargs=combine_kwargs(**kwargs),
                    )
                    if response.status_code == 200:
                        logging.info(f"Successfully enrolled user {user_id} in section {section_id}.")
                    else:
                        logging.error(f"Failed to enroll user {user_id} in section {section_id}. Response code: {response.status_code}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process and enroll users in Canvas based on CSV input.")
    parser.add_argument('users_to_process', type=str, help="Path to the users to process CSV file")
    parser.add_argument('enrollments', type=str, help="Path to the enrollments CSV file")
    parser.add_argument('--dry-run', action='store_true', help="Simulate the enrollment process without making changes")

    args = parser.parse_args()

    # Initialize Canvas API only if dry-run is False
    canvas = initialize_canvas_api(args.dry_run)

    deleted_users = read_users_to_process(args.users_to_process)
    enrollments = read_enrollments(args.enrollments, deleted_users)
    enroll_users(deleted_users, enrollments, canvas, dry_run=args.dry_run)

