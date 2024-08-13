import asyncio
import pickle
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
            await self.broadcast_data(AvailabilityRequest(time_slot=self.next_time_slot))


async def run_meeting_scheduler(meeting, participants):
    coordinator = Coordinator()
    await coordinator.arun_admin(
        inputs=pickle.dumps(meeting),
        workers=participants
    )
    return coordinator.output


def main():
    st.title("Meeting Scheduler")

    st.header("Meeting Details")
    meeting_name = st.text_input("Meeting Name", "Team Sync")
    meeting_date = st.date_input("Meeting Date")
    meeting_duration = st.slider("Meeting Duration (hours)", 1, 8, 2)
    min_participants = st.slider("Minimum Participants", 2, 10, 3)

    st.header("Participants")
    num_participants = st.slider("Number of Participants", 2, 10, 5)

    participants = []
    for i in range(num_participants):
        st.subheader(f"Participant {i + 1}")
        name = st.text_input(f"Name", f"Participant {i + 1}", key=f"name_{i}")
        start_time = st.slider(f"Available Start Time", 0, 23, 9, key=f"start_{i}")
        end_time = st.slider(f"Available End Time", start_time + 1, 24, 17, key=f"end_{i}")
        participants.append(Participant(name, [TimeSlot(str(meeting_date), start_time, end_time)]))

    if st.button("Schedule Meeting"):
        meeting = Meeting(name=meeting_name, date=str(meeting_date), duration=meeting_duration,
                          minimum_participants=min_participants)

        with st.spinner("Scheduling meeting..."):
            output = asyncio.run(run_meeting_scheduler(meeting, participants))

        st.subheader("Scheduling Results")
        for line in output:
            st.write(line)

        st.success("Scheduling complete!")


if __name__ == "__main__":
    main()