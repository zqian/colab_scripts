import argparse
import csv
import os
import logging
import sys

from canvasapi import Canvas  # type: ignore
from canvasapi.enrollment import Enrollment #type: ignore
from canvasapi.exceptions import CanvasException #type: ignore
from canvasapi.util import combine_kwargs #type: ignore
from canvasapi.paginated_list import PaginatedList #type: ignore
from datetime import datetime
from datetime import timezone
from typing import Optional

#logger = logging.getLogger("canvasapi")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)

# Setup a logger for this class
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

class CanvasEnrollmentsRestorer:
    # Initialize the CanvasEnrollmentsRestorer object and Canvas
    def __init__(self, after_date=None, skip_sections=None, dry_run=None):
        # Fetch configuration from environment variables
        API_BASE_URL = os.getenv('API_BASE_URL')
        API_KEY = os.getenv('API_KEY')

        if not API_BASE_URL or not API_KEY:
            raise ValueError("API_BASE_URL and API_KEY must be set in environment variables.")

        self.canvas = Canvas(API_BASE_URL, API_KEY)
        self.after_date = after_date
        self.skip_sections = skip_sections if skip_sections else []
        self.dry_run = dry_run
        logger.info(f"CanvasEnrollmentsRestorer initialized with API_BASE_URL: {API_BASE_URL}, after_date: {after_date}, skip_sections: {skip_sections}, dry_run: {dry_run}")

    # Get deleted enrollments for a user
    # Returns a PaginatedList of Enrollment objects or None if an error occurred
    def get_deleted_enrollments(self, user_id) -> PaginatedList:
        # Filter by state=deleted
        logger.info(f"---- Retrieving deleted enrollments for user {user_id}")
        params={
            'state[]': 'deleted',
        }
        try:
            enrollments = PaginatedList(
                Enrollment,
                self.canvas._Canvas__requester,
                "GET",
                f"users/sis_user_id:{user_id}/enrollments",
                _kwargs=combine_kwargs(**params),
            )
        except CanvasException as e:
            logger.error("Error fetching enrollments for user {user_id}: {e}")
            return PaginatedList
        return enrollments

    # Restore enrollments, optionally filtering by date
    def restore_enrollment(self, enrollment: Enrollment) -> str:

        enrollment_id = enrollment.id
        # Get updated_at from enrollment, convert to datetime
        updated_at = datetime.strptime(enrollment.updated_at, "%Y-%m-%dT%H:%M:%S%z")
        # Only process enrollments that were updated on 2024-08-20 or later and not in skip_sections
        if self.after_date and updated_at >= self.after_date:
            if enrollment.sis_section_id not in self.skip_sections:
                # Use the canvasapi to enroll the user in the section
                # First get the section
                section = self.canvas.get_section(enrollment.course_section_id)
                if self.dry_run:
                    message = "(DRY-RUN) Restoring enrollment"
                    logger.info(f"(DRY-RUN) Enrolling user in section {section.name}")
                else:
                    message = "Restoring enrollment"
                    logger.info(f"Enrolling user in section {section.name}")
                    # Then enroll the user
                    section.enroll_user(enrollment.user_id, 
                    enrollment={"type": enrollment.type, "enrollment_state": 'active',
                                "start_at": enrollment.start_at, "end_at": enrollment.end_at} )
            else:
                message = "Skipping because skip section set."
        else:
            message = "Skipping because date filtered."

        logger.info (f"""{message} 
            ENROLLMENT_ID: {enrollment_id} COURSE_ID: {enrollment.course_id} UPDATED: {enrollment.updated_at} 
            TYPE: {enrollment.type} COURSE_SECTION_ID: {enrollment.course_section_id} 
            SIS_IMPORT_ID: {enrollment.user["sis_import_id"]}, ENROLLMENT_STATE: {enrollment.enrollment_state}""")
                    
        return message

    def read_file_and_enroll(self, csv_file):
        with open(csv_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                user_id = row['user_id']  # Adjust this according to your CSV structure
                print(f'Fetching deleted enrollments for user: {user_id}')
                enrollments = self.get_deleted_enrollments(user_id)
                for enrollment in enrollments:
                    try: 
                        restored = self.restore_enrollment(enrollment)
                    except Exception as e: 
                        logger.error(f'Failed to restore enrollment ID {enrollment.id}.')
                        logger.error(f'Error: {e}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Restore deleted enrollments for users.')
    parser.add_argument("--csv-file", type=str, help="Path to the CSV file")
    parser.add_argument('--skip-sections', type=str, help='Comma-separated list of sections to skip.')
    parser.add_argument("--after-date", type=str, help="Only process enrollments updated after this date in ISO 8601 format (e.g., '2024-08-21T00:00:00-05:00')")
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, help="Dry run, do not actually restore enrollments")

    args = parser.parse_args()
    # Get a list of sections to skip as args
    skip_sections = args.skip_sections.split(',') if args.skip_sections else []
    after_date = datetime.strptime(args.after_date, "%Y-%m-%dT%H:%M:%S%z") if args.after_date else None
    # Create a new CanvasEnrollmentsRestorer object and call the read_file_and_enroll method
    cer = CanvasEnrollmentsRestorer(skip_sections=skip_sections, after_date=after_date, dry_run=args.dry_run)
    cer.read_file_and_enroll(args.csv_file)
