import streamlit as st
import asyncio
from typing import Optional, Type
from langchain.pydantic_v1 import BaseModel, Field
from langchain_community.chat_models import ChatOllama
from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from langchain_experimental.llms.ollama_functions import OllamaFunctions
from loguru import logger

from ceylon import Task, SpecializedAgent, TaskManager
from ceylon.llm.tools.search_tool import SearchTools


class QueryInput(BaseModel):
    prompt: str = Field(description="Input prompt")


class ImageGenerationTool(BaseTool):
    name = "ImageGenerationTool"
    description = "Useful for when you need to generate an image. Input should be a description of what you want to generate."
    args_schema: Type[BaseModel] = QueryInput
    return_direct: bool = True

    def _run(
            self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        logger.info(f"Processing query: {query}")
        return f"https://cdn.pixabay.com/photo/2024/01/02/10/33/stream-8482939_1280.jpg"

    async def _arun(
            self,
            query: str,
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        return self._run(query, run_manager=run_manager.get_sync() if run_manager else None)


def create_task_manager():
    article_task = Task(name="Write Article",
                        description="Write an article about AI advancements. The final output should strictly include only the title and the content and cover image, without any additional sections or formatting.")

    tasks = [article_task]

    llm_lib = ChatOllama(model="llama3.1:latest")
    llm_tool = OllamaFunctions(model="llama3.1:latest", format="json")

    agents = [
        SpecializedAgent(
            name="researcher",
            role="Research Specialist",
            context="Searches for relevant information on the web to gather data for content creation.",
            skills=[
                "Online Research",
                "Keyword Research",
                "Information Retrieval",
                "Fact-Checking",
                "Source Verification",
                "Research"
            ],
            tools=[SearchTools.search_internet],
            llm=llm_lib,
            tool_llm=llm_tool
        ),
        SpecializedAgent(
            name="illustrator",
            role="Illustrator",
            context="Creates images from text descriptions. The final output should strictly include only the title and the content and cover image, without any additional sections or formatting.",
            skills=[
                "Image Generation",
                "Captioning",
                "Image Manipulation",
                "Image Editing",
            ],
            tools=[ImageGenerationTool()],
            llm=llm_lib,
            tool_llm=llm_tool
        ),
        SpecializedAgent(
            name="writer",
            role="Content Writer",
            context="Simplifies technical concepts with metaphors and creates narrative-driven content while ensuring scientific accuracy.",
            skills=[
                "Creative Writing",
                "Technical Writing",
                "Storytelling",
                "Content Strategy",
                "SEO Writing",
                "Editing and Proofreading"
            ],
            tools=[],
            llm=llm_lib,
            tool_llm=llm_tool
        ),
    ]

    return TaskManager(tasks, agents, tool_llm=llm_tool, llm=llm_lib)


def run_task_manager():
    task_manager = create_task_manager()
    tasks = asyncio.run(task_manager.async_do(inputs=b""))
    return [t.final_answer for t in tasks]


def main():
    st.title("AI Article Writer")
    st.write("This application uses specialized agents to write an article about AI advancements.")

    if st.button("Generate Article"):
        with st.spinner("Generating article... This may take a few minutes."):
            results = run_task_manager()

        for result in results:
            st.markdown(result)


if __name__ == "__main__":
    main()