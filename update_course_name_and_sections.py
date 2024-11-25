import json
import argparse
import os
from canvasapi import Canvas

API_URL = os.getenv('CANVAS_API_URL')
API_KEY = os.getenv('CANVAS_API_KEY')

if not API_URL or not API_KEY:
    print("Error: Please set the CANVAS_API_URL and CANVAS_API_KEY environment variables.")
    exit(1)

# Step 1: Parse command line arguments
parser = argparse.ArgumentParser(description='Update Canvas course name from JSON file. This can be retrieved from the API like /api/v1/accounts/120/courses/?enrollment_term_id=417&search_term=HBEHED&per_page=200')
parser.add_argument('json_file', type=str, help='Path to the JSON file containing course data')
args = parser.parse_args()

# Step 2: Read the JSON file
with open(args.json_file, 'r') as file:
    course_data_list = json.load(file)

# Print the number of items in the course_data
print(f"Number of items in the course_data: {len(course_data_list)}")

# Step 3: Initialize the Canvas API
canvas = Canvas(API_URL, API_KEY)

# Step 4: Fetch the course using its ID
for course_data in course_data_list:
    course_id = course_data['id']
    course = canvas.get_course(course_id)

    # Update the course name
    old_name = course_data['name']
    new_name = old_name.replace("HBEHED", "HBEHEQ")
    old_code = course_data['course_code']
    new_course_code = old_code.replace("HBEHED", "HBEHEQ")
    course.update(course={'name': new_name, 'course_code': new_course_code})

    print(f"Course ID {course_id}: name {old_name} updated to {new_name}, course_code {old_code} updated to {new_course_code}")

    # Fetch and update sections
    sections = course.get_sections()
    for section in sections:
        old_section_name = section.name
        new_section_name = section.name.replace("HBEHED", "HBEHEQ")
        section.edit(course_section={'name': new_section_name})
        print(f"Section ID {section.id}: name {old_section_name} updated to {new_section_name}")

