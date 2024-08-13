# Meeting Scheduler Tutorial

## Introduction

This tutorial will guide you through using and understanding a Meeting Scheduler application built with Python and Streamlit. The application helps schedule meetings by finding suitable time slots based on participants' availability.

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.7 or higher
- pip (Python package installer)

## Installation

1. Install the required packages:
   ```
   pip install streamlit asyncio loguru pydantic ceylon
   ```

2. Save the `meeting_scheduler.py` file to your local machine.

## Running the Application

To run the Meeting Scheduler:

1. Open a terminal or command prompt.
2. Navigate to the directory containing `meeting_scheduler.py`.
3. Run the following command:
   ```
   streamlit run meeting_scheduler.py
   ```
4. Your default web browser should open automatically, displaying the Meeting Scheduler interface.

## Using the Meeting Scheduler

### Step 1: Set Meeting Details

1. Enter the meeting name (default is "Team Sync").
2. Select the meeting date using the date picker.
3. Use the slider to set the meeting duration (in hours).
4. Set the minimum number of required participants using the slider.

### Step 2: Add Participants

1. Click on "Add New Participant" to expand the section.
2. Enter the participant's name.
3. Set their available start and end times using the sliders.
4. Click "Add Participant" to add them to the list.
5. Repeat for each participant.

### Step 3: Schedule the Meeting

1. Once you've added all participants, click the "Schedule Meeting" button.
2. The application will attempt to find a suitable time slot for the meeting.
3. You'll see the scheduling progress and results displayed on the screen.

## Understanding the Code

The `meeting_scheduler.py` file consists of several key components:

1. **Data Structures**: Classes like `Meeting`, `TimeSlot`, `AvailabilityRequest`, and `AvailabilityResponse` define the data models used in the application.

2. **Participant Class**: Represents each meeting participant and handles their availability.

3. **Coordinator Class**: Manages the meeting scheduling process, including collecting responses from participants and determining the best meeting time.

4. **Streamlit Interface**: Creates the user interface for inputting meeting details and participant information.

5. **Scheduling Logic**: Uses asynchronous programming to simulate the scheduling process in real-time.

## Key Features

- **Dynamic Participant Management**: Easily add or remove participants with their availability.
- **Real-time Scheduling**: Watch the scheduling process unfold as the application searches for a suitable time slot.
- **Flexible Meeting Parameters**: Customize meeting duration, date, and minimum participant requirements.

## Customization Tips

1. **Modify Time Range**: In the Streamlit interface section, you can adjust the range of the time sliders to fit your needs.

2. **Change Scheduling Algorithm**: In the `Coordinator` class, you can modify the `on_availability_request` method to implement different scheduling strategies.

3. **Add More Participant Details**: Extend the `Participant` class to include additional information like roles or priorities.

## Troubleshooting

- If you encounter any "module not found" errors, ensure all required packages are installed correctly.
- If the scheduling process seems stuck, check that you've added enough participants to meet the minimum requirement.
