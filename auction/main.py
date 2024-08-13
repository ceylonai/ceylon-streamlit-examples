import asyncio
import pickle
import queue
import threading
from typing import List
import streamlit as st
from pydantic.dataclasses import dataclass

from ceylon import Agent, CoreAdmin, on_message

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


class Auctioneer(CoreAdmin):
    item: Item
    bids: List[Bid] = []
    expected_bidders: int
    connected_bidders: int = 0
    output: List[str] = []

    def __init__(self, item: Item, expected_bidders: int):
        self.item = item
        self.expected_bidders = expected_bidders
        super().__init__(name=workspace_id, port=admin_port)

    async def on_agent_connected(self, topic: str, agent_id: str):
        self.connected_bidders += 1
        self.output.append(f"Bidder {agent_id} connected. {self.connected_bidders}/{self.expected_bidders} bidders connected.")
        if self.connected_bidders == self.expected_bidders:
            self.output.append("All bidders connected. Starting the auction.")
            await self.start_auction()

    async def start_auction(self):
        self.output.append(f"Starting auction for {self.item.name} with starting price ${self.item.starting_price}")
        await self.broadcast_data(AuctionStart(item=self.item))

    @on_message(type=Bid)
    async def on_bid(self, bid: Bid):
        self.bids.append(bid)
        self.output.append(f"Received bid from {bid.bidder} for ${bid.amount:.2f}")
        await self.end_auction()

    async def end_auction(self):
        if not self.bids:
            self.output.append(f"No bids received for {self.item.name}")
        else:
            winning_bid = max(self.bids, key=lambda x: x.amount)
            result = AuctionResult(winner=winning_bid.bidder, winning_bid=winning_bid.amount)
            await self.broadcast_data(result)
            self.output.append(f"Auction ended. Winner: {result.winner}, Winning Bid: ${result.winning_bid:.2f}")

        await self.broadcast_data(AuctionEnd())
        await self.stop()


async def run_auction(item, bidders):
    auctioneer = Auctioneer(item, expected_bidders=len(bidders))
    await auctioneer.arun_admin(inputs=b"", workers=bidders)
    return auctioneer.output


def run_auction_thread(item, bidders, result_queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    output = loop.run_until_complete(run_auction(item, bidders))
    result_queue.put(output)


def main():
    st.title("Single Item Auction")

    st.header("Item Details")
    item_name = st.text_input("Item Name", "Rare Painting")
    starting_price = st.number_input("Starting Price", min_value=1.0, value=1000.0, step=100.0)

    st.header("Bidders")

    # Initialize session state for bidders if it doesn't exist
    if 'bidders' not in st.session_state:
        st.session_state.bidders = []

    # Add new bidder
    with st.expander("Add New Bidder"):
        new_name = st.text_input("Name", f"Bidder {len(st.session_state.bidders) + 1}")
        new_budget = st.number_input("Budget", min_value=1.0, value=1500.0, step=100.0)
        if st.button("Add Bidder"):
            st.session_state.bidders.append({
                "name": new_name,
                "budget": new_budget
            })
            st.success(f"Added {new_name} to the bidders list.")
            st.rerun()

    # Display and manage existing bidders
    for i, bidder in enumerate(st.session_state.bidders):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.write(f"**{bidder['name']}**")
        with col2:
            st.write(f"Budget: ${bidder['budget']:.2f}")
        with col3:
            if st.button("Remove", key=f"remove_{i}"):
                st.session_state.bidders.pop(i)
                st.rerun()

    if st.button("Start Auction"):
        if len(st.session_state.bidders) < 2:
            st.error("Not enough bidders. Need at least 2.")
        else:
            item = Item(name=item_name, starting_price=starting_price)
            bidders = [
                Bidder(b["name"], b["budget"])
                for b in st.session_state.bidders
            ]

            result_queue = queue.Queue()
            auction_thread = threading.Thread(target=run_auction_thread, args=(item, bidders, result_queue))
            auction_thread.start()

            # Create a status area
            status_area = st.empty()

            # Display auction progress
            with st.spinner("Running auction..."):
                while auction_thread.is_alive():
                    status_area.text("Processing...")
                    auction_thread.join(0.1)  # Wait for 0.1 seconds before checking again

                output = result_queue.get()

                for line in output:
                    status_area.text(line)
                    st.write(line)
                    if "Auction ended." in line:
                        st.success("Auction completed successfully!")
                        break

            st.success("Auction process completed!")


if __name__ == "__main__":
    main()