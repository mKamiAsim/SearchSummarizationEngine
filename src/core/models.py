"""
Pydantic data models for the research engine.

These models provide type safety and validation for data flowing through
the pipeline stages. Each model represents a specific data structure used
in the research workflow.
"""

from typing import Any
from pydantic import BaseModel, Field


class AssistantPersona(BaseModel):
    """
    Model for assistant persona selection output.
    
    Represents the expert persona selected to answer a research question.
    Used in Stage 1 of the pipeline.
    
    Attributes:
        persona: Expert role/title (e.g., "Quantum Computing Researcher")
        expertise: Key areas of knowledge
        approach: How they would approach answering the question
    """
    
    persona: str = Field(
        ...,
        description="Expert role or title",
        examples=["Quantum Computing Researcher", "AI Ethics Specialist"],
    )
    expertise: str = Field(
        ...,
        description="Key areas of knowledge",
        examples=["Quantum algorithms, quantum supremacy, QPU architectures"],
    )
    approach: str = Field(
        ...,
        description="Approach to answering the question",
        examples=["Technical but accessible explanation with recent breakthroughs"],
    )


class SearchQueryGeneration(BaseModel):
    """
    Model for search query generation output.
    
    Represents the structured output from Stage 2 of the pipeline.
    
    Attributes:
        queries: List of search queries to execute
        reasoning: Explanation of why these queries were chosen
    """
    
    queries: list[str] = Field(
        ...,
        description="List of search queries to execute",
        min_length=1,
        max_length=10,
    )
    reasoning: str = Field(
        ...,
        description="Reasoning for query selection",
    )


class SearchResult(BaseModel):
    """
    Model for a single search result.
    
    Represents one URL returned from a web search.
    
    Attributes:
        url: The result URL
        title: Title of the search result
        snippet: Brief description/snippet from search
        search_query: The query that produced this result
        rank: Position in search results (1-indexed)
    """
    
    url: str = Field(..., description="Result URL")
    title: str = Field(default="", description="Result title")
    snippet: str = Field(default="", description="Search result snippet")
    search_query: str = Field(..., description="Query that produced this result")
    rank: int = Field(default=0, description="Position in search results", ge=1)


class ScrapedContent(BaseModel):
    """
    Model for scraped web page content.
    
    Represents the text content extracted from a web page.
    
    Attributes:
        url: Source URL
        content: Extracted text content
        title: Page title (if available)
        success: Whether scraping was successful
        error_message: Error message if scraping failed
        content_length: Number of characters in content
    """
    
    url: str = Field(..., description="Source URL")
    content: str = Field(default="", description="Extracted text content")
    title: str = Field(default="", description="Page title")
    success: bool = Field(default=True, description="Whether scraping succeeded")
    error_message: str = Field(default="", description="Error message if failed")
    content_length: int = Field(default=0, description="Character count")
    
    def is_valid(self) -> bool:
        """Check if content is valid for summarization."""
        return self.success and len(self.content.strip()) > 0


class SummarizedResult(BaseModel):
    """
    Model for a summarized search result.
    
    Represents the summary of a single scraped web page.
    
    Attributes:
        url: Source URL
        summary: Generated summary text
        search_query: Original search query
        user_question: Original user question
        key_points: List of key points extracted
        relevance_score: Estimated relevance (0-100)
    """
    
    url: str = Field(..., description="Source URL")
    summary: str = Field(..., description="Generated summary")
    search_query: str = Field(..., description="Search query used")
    user_question: str = Field(..., description="Original user question")
    key_points: list[str] = Field(default_factory=list, description="Key points")
    relevance_score: int = Field(default=50, description="Relevance 0-100", ge=0, le=100)


class ResearchReport(BaseModel):
    """
    Model for the final research report.
    
    The complete output of the research pipeline.
    
    Attributes:
        user_question: Original research question
        report_content: Full report text in markdown format
        search_queries_used: List of search queries executed
        sources: List of source URLs cited
        summary_count: Number of results summarized
        generated_at: Timestamp (ISO format string)
        metadata: Additional metadata
    """
    
    user_question: str = Field(..., description="Original research question")
    report_content: str = Field(..., description="Full report in markdown")
    search_queries_used: list[str] = Field(
        default_factory=list,
        description="Search queries executed",
    )
    sources: list[str] = Field(default_factory=list, description="Source URLs")
    summary_count: int = Field(default=0, description="Number of results summarized")
    generated_at: str = Field(default="", description="Generation timestamp (ISO)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save report content to file.
        
        Args:
            filepath: Path to save the report
        """
        from pathlib import Path
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.report_content, encoding="utf-8")
    
    def get_word_count(self) -> int:
        """Get approximate word count of report."""
        return len(self.report_content.split())
    
    def get_source_count(self) -> int:
        """Get number of unique sources."""
        return len(set(self.sources))


class PipelineState(BaseModel):
    """
    Model for tracking pipeline execution state.
    
    Used internally to pass data between pipeline stages.
    
    Attributes:
        user_question: Original question
        assistant_persona: Selected persona
        search_queries: Generated queries
        search_results: Raw search results
        scraped_content: Scraped page content
        summaries: Per-result summaries
        final_report: Compiled report
        errors: List of errors encountered
        execution_time_ms: Total execution time in milliseconds
    """
    
    user_question: str = Field(..., description="Original research question")
    assistant_persona: AssistantPersona | None = Field(
        default=None,
        description="Selected assistant persona",
    )
    search_queries: list[str] = Field(default_factory=list, description="Generated queries")
    search_results: list[SearchResult] = Field(
        default_factory=list,
        description="Raw search results",
    )
    scraped_content: list[ScrapedContent] = Field(
        default_factory=list,
        description="Scraped content from URLs",
    )
    summaries: list[SummarizedResult] = Field(
        default_factory=list,
        description="Per-result summaries",
    )
    final_report: ResearchReport | None = Field(
        default=None,
        description="Final compiled report",
    )
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
    execution_time_ms: int = Field(default=0, description="Execution time in ms")
    
    def add_error(self, error: str) -> None:
        """Add an error to the error list."""
        self.errors.append(error)
    
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0
    
    def get_error_summary(self) -> str:
        """Get formatted error summary."""
        if not self.errors:
            return "No errors"
        return f"{len(self.errors)} error(s): {'; '.join(self.errors)}"