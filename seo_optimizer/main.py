from ceylon import Agent, RunnerAgent, AgentJobStepRequest, AgentJobResponse, JobRequest, JobSteps, Step
from langchain_community.chat_models import ChatOllama
from typing import Dict, Any

# Simulated LLM for demonstration purposes
llm = ChatOllama(model="llama3:instruct")


class KeywordAnalysisAgent(Agent):
    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        # Simulated keyword analysis
        keywords = ["SEO", "optimization", "multi-agent", "Ceylon"]
        return AgentJobResponse(
            worker=self.details().name,
            job_data={"keywords": keywords}
        )


class ContentAnalysisAgent(Agent):
    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        # Simulated content analysis
        content_score = 8.5
        improvement_suggestions = [
            "Add more relevant keywords",
            "Increase content length",
            "Improve readability"
        ]
        return AgentJobResponse(
            worker=self.details().name,
            job_data={
                "content_score": content_score,
                "suggestions": improvement_suggestions
            }
        )


class BacklinkAnalysisAgent(Agent):
    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        # Simulated backlink analysis
        backlink_count = 150
        domain_authority = 45
        return AgentJobResponse(
            worker=self.details().name,
            job_data={
                "backlink_count": backlink_count,
                "domain_authority": domain_authority
            }
        )


class TechnicalSEOAgent(Agent):
    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        # Simulated technical SEO analysis
        issues = [
            "Slow page load speed",
            "Missing meta descriptions",
            "Broken links detected"
        ]
        return AgentJobResponse(
            worker=self.details().name,
            job_data={"technical_issues": issues}
        )


class SEORecommendationAgent(Agent):
    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        # Compile recommendations based on other agents' outputs
        keyword_data = request.context.get("keyword_analysis", {})
        content_data = request.context.get("content_analysis", {})
        backlink_data = request.context.get("backlink_analysis", {})
        technical_data = request.context.get("technical_seo", {})

        recommendations = [
            f"Focus on these keywords: {', '.join(keyword_data.get('keywords', []))}",
            f"Improve content: {', '.join(content_data.get('suggestions', []))}",
            f"Work on increasing backlinks (current count: {backlink_data.get('backlink_count', 0)})",
            f"Fix technical issues: {', '.join(technical_data.get('technical_issues', []))}"
        ]

        return AgentJobResponse(
            worker=self.details().name,
            job_data={"recommendations": recommendations}
        )


def main():
    # Initialize agents
    keyword_agent = KeywordAnalysisAgent(name="keyword_analysis", role="Keyword Analyst")
    content_agent = ContentAnalysisAgent(name="content_analysis", role="Content Analyst")
    backlink_agent = BacklinkAnalysisAgent(name="backlink_analysis", role="Backlink Analyst")
    technical_agent = TechnicalSEOAgent(name="technical_seo", role="Technical SEO Specialist")
    recommendation_agent = SEORecommendationAgent(name="seo_recommendation", role="SEO Strategist")

    # Set up the RunnerAgent
    chief = RunnerAgent(
        workers=[keyword_agent, content_agent, backlink_agent, technical_agent, recommendation_agent],
        tool_llm=llm,
        server_mode=False
    )

    # Define the job
    job = JobRequest(
        title="SEO Optimization",
        explanation="Analyze and provide recommendations for improving website SEO",
        steps=JobSteps(steps=[
            Step(worker="keyword_analysis", explanation="Analyze relevant keywords", dependencies=[]),
            Step(worker="content_analysis", explanation="Analyze website content", dependencies=[]),
            Step(worker="backlink_analysis", explanation="Analyze backlink profile", dependencies=[]),
            Step(worker="technical_seo", explanation="Perform technical SEO analysis", dependencies=[]),
            Step(worker="seo_recommendation", explanation="Compile SEO recommendations",
                 dependencies=["keyword_analysis", "content_analysis", "backlink_analysis", "technical_seo"])
        ])
    )

    # Execute the job
    result = chief.execute(job)

    # Print the final recommendations
    print("SEO Recommendations:")
    for recommendation in result.job_data.get("recommendations", []):
        print(f"- {recommendation}")


if __name__ == "__main__":
    main()