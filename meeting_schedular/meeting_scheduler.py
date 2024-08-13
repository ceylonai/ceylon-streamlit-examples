import asyncio
import pickle
import queue
import threading
from typing import List
import streamlit as st
from loguru import logger
from pydantic.dataclasses import dataclass
from ceylon import Agent, CoreAdmin, on_message

admin_port = 8000
admin_peer = "Coordinator"
workspace_id = "time_scheduling"

logger.disable("ceylon.agent.common")


@dataclass(repr=True)
class Meeting:
    name: str
    date: str
    duration: int
    minimum_participants: int

    def __str__(self):
        return f"{self.name} {self.date} {self.duration} {self.minimum_participants}"


@dataclass(repr=True)
class TimeSlot:
    date: str
    start_time: int
    end_time: int

    @property
    def duration(self):
        return self.end_time - self.start_time

    def __str__(self):
        return f"{self.date} {self.start_time}-{self.end_time}"

    def is_greater_than(self, other):
        return self.end_time > other.end_time


@dataclass(repr=True)
class AvailabilityRequest:
    time_slot: TimeSlot


@dataclass(repr=True)
class AvailabilityResponse:
    owner: str
    time_slot: TimeSlot
    accepted: bool


class Participant(Agent):
    name: str
    available_times: List[TimeSlot]

    def __init__(self, name, available_times):
        self.name = name
        self.available_times = available_times
        super().__init__(name=name, workspace_id=workspace_id, admin_peer=admin_peer, admin_port=admin_port)

    @on_message(type=AvailabilityRequest)
    async def on_availability_request(self, data: AvailabilityRequest):
        if not any(self.is_overlap(slot, data.time_slot, data.time_slot.duration) for slot in self.available_times):
            await self.broadcast_data(
                AvailabilityResponse(owner=self.details().name, time_slot=data.time_slot, accepted=False))
        else:
            await self.broadcast_data(
                AvailabilityResponse(owner=self.details().name, time_slot=data.time_slot, accepted=True))

    @staticmethod
    def is_overlap(slot1: TimeSlot, slot2: TimeSlot, duration: int) -> bool:
        latest_start = max(slot1.start_time, slot2.start_time)
        earliest_end = min(slot1.end_time, slot2.end_time)
        return earliest_end - latest_start >= duration


class Coordinator(CoreAdmin):
    meeting: Meeting = None
    agreed_slots = {}
    next_time_slot = None
    output = []

    def __init__(self):
        super().__init__(name=workspace_id, port=admin_port)

    async def run(self, inputs: "bytes"):
        self.meeting = pickle.loads(inputs)
        self.output.append(f"Meeting Schedule request: {self.meeting}")

    async def on_agent_connected(self, topic: "str", agent_id: "str"):
        if self.next_time_slot is None and self.meeting is not None:
            self.next_time_slot = TimeSlot(self.meeting.date, 0, self.meeting.duration)
            await self.broadcast_data(AvailabilityRequest(time_slot=self.next_time_slot))

    @on_message(type=AvailabilityResponse)
    async def on_availability_request(self, data: AvailabilityResponse):
        await self.broadcast_data(
            AvailabilityResponse(owner=self.details().name, time_slot=data.time_slot, accepted=True))

        if data.accepted:
            time_slot_key = f"{data.time_slot}"
            self.output.append(f"{data.owner} accepts {data.time_slot}")
            if time_slot_key in self.agreed_slots:
                slots = self.agreed_slots[time_slot_key]
                if data.owner not in slots:
                    slots.append(data.owner)
                    self.agreed_slots[time_slot_key] = slots
                    if len(slots) >= self.meeting.minimum_participants:
                        self.output.append(f"Meeting scheduled: {slots} participants agreed on {data.time_slot}")
                        await self.stop()
            else:
                self.agreed_slots[time_slot_key] = [data.owner]

        current_time_slot = data.time_slot
        calculated_next_time_slot = TimeSlot(self.meeting.date, current_time_slot.start_time + 1,
                                             current_time_slot.start_time + 1 + self.meeting.duration)

        if calculated_next_time_slot.is_greater_than(self.next_time_slot):
            self.next_time_slot = calculated_next_time_slot
            self.output.append(f"Trying next time slot: {self.next_time_slot}")
            await self.broadcast_data(AvailabilityRequest(time_slot=self.next_time_slot))


async def run_meeting_scheduler(meeting, participants):
    coordinator = Coordinator()
    await coordinator.arun_admin(
        inputs=pickle.dumps(meeting),
        workers=participants
    )
    return coordinator.output


def run_scheduler_thread(meeting, participants, result_queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    output = loop.run_until_complete(run_meeting_scheduler(meeting, participants))
    result_queue.put(output)


def main():
    st.title("Meeting Scheduler")

    st.header("Meeting Details")
    meeting_name = st.text_input("Meeting Name", "Team Sync")
    meeting_date = st.date_input("Meeting Date")
    meeting_duration = st.slider("Meeting Duration (hours)", 1, 8, 2)
    min_participants = st.slider("Minimum Participants", 2, 10, 3)

    st.header("Participants")

    # Initialize session state for participants if it doesn't exist
    if 'participants' not in st.session_state:
        st.session_state.participants = []

    # Add new participant
    with st.expander("Add New Participant"):
        new_name = st.text_input("Name", f"Participant {len(st.session_state.participants) + 1}")
        new_start_time = st.slider("Available Start Time", 0, 23, 9)
        new_end_time = st.slider("Available End Time", new_start_time + 1, 24, 17)
        if st.button("Add Participant"):
            st.session_state.participants.append({
                "name": new_name,
                "start_time": new_start_time,
                "end_time": new_end_time
            })
            st.success(f"Added {new_name} to the participants list.")
            st.rerun()

    # Display and manage existing participants
    for i, participant in enumerate(st.session_state.participants):
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            st.write(f"**{participant['name']}**")
        with col2:
            st.write(f"Start: {participant['start_time']}:00")
        with col3:
            st.write(f"End: {participant['end_time']}:00")
        with col4:
            if st.button("Remove", key=f"remove_{i}"):
                st.session_state.participants.pop(i)
                st.rerun()

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

            # Create a status area
            status_area = st.empty()

            # Display scheduling progress
            with st.spinner("Scheduling meeting..."):
                while scheduler_thread.is_alive():
                    status_area.text("Processing...")
                    scheduler_thread.join(0.1)  # Wait for 0.1 seconds before checking again

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


if __name__ == "__main__":
    main()