# Ceylon and Streamlit Integration in Meeting Scheduler

This guide focuses on how the Ceylon framework is integrated with Streamlit in the Meeting Scheduler application, explaining the process from user input to result display.

## 1. Initiating the Scheduling Process

The scheduling process begins when the user clicks the "Schedule Meeting" button in the Streamlit interface:

```python
if st.button("Schedule Meeting"):
    if len(st.session_state.participants) < min_participants:
        st.error(f"Not enough participants. Need at least {min_participants}.")
    else:
        meeting = Meeting(name=meeting_name, date=str(meeting_date), duration=meeting_duration,
                          minimum_participants=min_participants)
        participants = [
            Participant(p["name"], [TimeSlot(str(meeting_date), p["start_time"], p["end_time"])])
            for p in st.session_state.participants
        ]

        result_queue = queue.Queue()
        scheduler_thread = threading.Thread(target=run_scheduler_thread, args=(meeting, participants, result_queue))
        scheduler_thread.start()
```

This code:
1. Creates a `Meeting` object with user-input details.
2. Creates `Participant` objects from the Streamlit session state.
3. Starts a new thread to run the Ceylon-based scheduler.

## 2. Running the Ceylon Scheduler

The `run_scheduler_thread` function is where Ceylon and Streamlit integration begins:

```python
def run_scheduler_thread(meeting, participants, result_queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    output = loop.run_until_complete(run_meeting_scheduler(meeting, participants))
    result_queue.put(output)
```

This function:
1. Creates a new asyncio event loop.
2. Runs the `run_meeting_scheduler` coroutine, which uses Ceylon.
3. Puts the output into a queue for Streamlit to access.

## 3. Ceylon Scheduling Process

The `run_meeting_scheduler` function sets up and runs the Ceylon-based scheduling system:

```python
async def run_meeting_scheduler(meeting, participants):
    coordinator = Coordinator()
    await coordinator.arun_admin(
        inputs=pickle.dumps(meeting),
        workers=participants
    )
    return coordinator.output
```

This function:
1. Creates a `Coordinator` (which is a Ceylon `CoreAdmin`).
2. Runs the coordinator with the meeting details and participants.
3. Returns the coordinator's output.

## 4. Displaying Results in Streamlit

While the Ceylon scheduler is running, Streamlit provides real-time updates:

```python
with st.spinner("Scheduling meeting..."):
    while scheduler_thread.is_alive():
        status_area.text("Processing...")
        scheduler_thread.join(0.1)

    output = result_queue.get()

    for line in output:
        status_area.text(line)
        st.write(line)
        if "Meeting scheduled:" in line:
            st.success("Meeting successfully scheduled!")
            break
    else:
        st.warning("Unable to find a suitable time for all participants.")

st.success("Scheduling process completed!")
```

This code:
1. Displays a spinner while the scheduler is running.
2. Retrieves the output from the queue once the scheduler finishes.
3. Displays each line of the output in real-time.
4. Shows a success message if a meeting time is found, or a warning if not.

## 5. Ceylon-Streamlit Data Flow

1. **Streamlit to Ceylon**: User inputs from Streamlit (meeting details, participant information) are converted into Ceylon-compatible objects (`Meeting`, `Participant`).

2. **Ceylon to Streamlit**: The `Coordinator` in Ceylon generates output messages, which are collected in its `output` list. This list is then passed back to Streamlit via a queue.

## 6. Key Points of Integration

- **Asynchronous Execution**: Ceylon's asynchronous nature is managed by running it in a separate thread, allowing Streamlit to remain responsive.
- **Real-time Updates**: Streamlit's ability to update content dynamically is used to display Ceylon's output in real-time.
- **State Management**: Streamlit's session state is used to store participant information, which is then converted into Ceylon `Participant` objects.
- **Error Handling**: Both Streamlit and Ceylon contribute to error handling, with Streamlit displaying user-friendly messages based on Ceylon's output.