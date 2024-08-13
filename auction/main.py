import asyncio
import queue
import threading

import streamlit as st
from ceylon import Agent, on_message
from pydantic.dataclasses import dataclass

admin_port = 8000
admin_peer = "Auctioneer"
workspace_id = "single_item_auction"


@dataclass(repr=True)
class Item:
    name: str
    starting_price: float


@dataclass(repr=True)
class Bid:
    bidder: str
    amount: float


@dataclass(repr=True)
class AuctionStart:
    item: Item


@dataclass(repr=True)
class AuctionResult:
    winner: str
    winning_bid: float


@dataclass(repr=True)
class AuctionEnd:
    pass


class Bidder(Agent):
    name: str
    budget: float

    def __init__(self, name: str, budget: float):
        self.name = name
        self.budget = budget
        super().__init__(name=name, workspace_id=workspace_id, admin_peer=admin_peer, admin_port=admin_port,
                         role="bidder")

    @on_message(type=AuctionStart)
    async def on_auction_start(self, data: AuctionStart):
        if self.budget > data.item.starting_price:
            bid_amount = min(self.budget, data.item.starting_price * 1.1)  # Simple bidding strategy
            await self.broadcast_data(Bid(bidder=self.name, amount=bid_amount))

    @on_message(type=AuctionResult)
    async def on_auction_result(self, data: AuctionResult):
        if data.winner == self.name:
            self.budget -= data.winning_bid


class AuctionMonitor(Agent):
    def __init__(self, message_queue):
        self.message_queue = message_queue
        super().__init__(name="AuctionMonitor", workspace_id=workspace_id, admin_peer=admin_peer, admin_port=admin_port,
                         role="monitor")

    @on_message(type=AuctionStart)
    async def on_auction_start(self, data: AuctionStart):
        self.message_queue.put(f"Auction started for {data.item.name} with starting price ${data.item.starting_price}")

    @on_message(type=Bid)
    async def on_bid(self, data: Bid):
        self.message_queue.put(f"Bid received: {data.bidder} bid ${data.amount:.2f}")

    @on_message(type=AuctionResult)
    async def on_auction_result(self, data: AuctionResult):
        self.message_queue.put(f"Auction ended. Winner: {data.winner}, Winning Bid: ${data.winning_bid:.2f}")

    @on_message(type=AuctionEnd)
    async def on_auction_end(self, data: AuctionEnd):
        self.message_queue.put("Auction process completed")

async def run_auction(item, bidders, message_queue):
    # Simulating auction events
    await asyncio.sleep(1)
    message_queue.put(f"Auction started for {item.name} with starting price ${item.starting_price}")
    for bidder in bidders:
        await asyncio.sleep(0.5)
        message_queue.put(f"Bid received: {bidder} bid ${item.starting_price + 100:.2f}")
    await asyncio.sleep(1)
    winner = bidders[-1]
    winning_bid = item.starting_price + 100
    message_queue.put(f"Auction ended. Winner: {winner}, Winning Bid: ${winning_bid:.2f}")
    message_queue.put("Auction process completed")
    message_queue.put(None)  # Signal that the auction is complete

def run_auction_in_thread(item, bidders, message_queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_auction(item, bidders, message_queue))

def main():
    st.title("Real-time Auction Dashboard")

    # Item details with unique keys
    item_name = st.text_input("Item Name", "Rare Painting", key="item_name_input")
    starting_price = st.number_input("Starting Price", min_value=1.0, value=1000.0, step=100.0, key="starting_price_input")

    # Bidder management
    if 'bidders' not in st.session_state:
        st.session_state.bidders = []

    new_bidder = st.text_input("Add new bidder", key="new_bidder_input")
    if st.button("Add Bidder", key="add_bidder_button") and new_bidder:
        st.session_state.bidders.append(new_bidder)

    st.write("Current Bidders:")
    for i, bidder in enumerate(st.session_state.bidders):
        st.write(f"- {bidder}", key=f"bidder_{i}")

    if st.button("Start Auction", key="start_auction_button") and len(st.session_state.bidders) > 1:
        item = Item(name=item_name, starting_price=starting_price)
        message_queue = queue.Queue()

        # Start the auction in a separate thread
        auction_thread = threading.Thread(target=run_auction_in_thread, args=(item, st.session_state.bidders, message_queue))
        auction_thread.start()

        # Prepare areas for real-time updates
        progress_area = st.empty()
        log_area = st.empty()

        # Initialize log
        log = []

        # Update the dashboard in real-time
        while True:
            try:
                message = message_queue.get(timeout=0.1)
                if message is None:
                    break
                log.append(message)

                # Update progress area
                with progress_area.container():
                    st.subheader("Auction Progress")
                    st.write(message)

                # Update log area
                with log_area.container():
                    st.subheader("Auction Log")
                    st.write("\n".join(log))

            except queue.Empty:
                continue

        st.success("Auction completed!")

if __name__ == "__main__":
    main()