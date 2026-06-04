"""Content generation agent for creating actual story content."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from src.book_series_generator.models.content import Scene, ChapterPlan
from src.book_series_generator.models.book import Book, Chapter
from src.book_series_generator.models.character import Character
from src.book_series_generator.services.llm_service import get_llm_service
from src.book_series_generator.agents.base_agent import AgentState, BaseAgent
from src.book_series_generator.services.structured_llm_service import get_token_limit_param


class ContentGenerationRequest(BaseModel):
    """Request for content generation."""
    chapter_plan: ChapterPlan
    book_title: str
    series_title: str
    characters: List[Character]
    target_audience: str
    reading_level: str
    educational_themes: List[str]
    previous_chapters_summary: Optional[str] = None


class GeneratedContent(BaseModel):
    """Generated story content."""
    title: str
    content: str
    word_count: int
    reading_time_minutes: int
    educational_elements_included: List[str]
    character_development_notes: List[str]


class ContentGenerationAgent(BaseAgent):
    """Generates engaging story content from detailed plans."""
    
    @property
    def agent_name(self) -> str:
        return "ContentGenerationAgent"
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert children's book author specializing in creating engaging, educational stories.

                    Your expertise includes:
                    - Writing age-appropriate, captivating narrative content
                    - Creating natural dialogue that sounds authentic for children
                    - Maintaining consistent character voices and personalities
                    - Seamlessly incorporating educational elements into engaging stories
                    - Balancing action, description, and character development
                    - Using vocabulary appropriate for the target reading level
                    - Creating positive messages about friendship, problem-solving, and personal growth

                    Writing Guidelines:
                    - Use vivid, sensory descriptions that help children visualize scenes
                    - Create dialogue that sounds natural and age-appropriate
                    - Include moments of humor and wonder appropriate for children
                    - Ensure educational elements feel natural, not forced
                    - Maintain consistent character personalities and growth
                    - Use active voice and varied sentence structures
                    - Include emotional moments that children can relate to

                    Always write in a warm, encouraging tone that helps children feel confident about reading and learning."""
                        
    def level_prompt(self, request: ContentGenerationRequest) -> str:
        return f"""
                    TARGET AGE RANGE: {request.target_audience}
                    BOOK LEXILE LEVEL: {request.reading_level}

                    YOUR WRITING MUST CONFORM TO THIS TARGET AGE RANGE AND LEXILE LEVEL ABSOLUTELY.  THIS IS YOUR PRIME DIRECTIVE.
                """

    async def execute(self, state: AgentState) -> AgentState:
        """Execute content generation for a chapter."""
        try:
            self.log_activity("Starting content generation")
            
            request = ContentGenerationRequest.model_validate(state.context)
            content = await self.generate_chapter_content(request)
            
            state.context["generated_content"] = content.model_dump()
            state.context["word_count"] = content.word_count
            state.context["reading_time"] = content.reading_time_minutes
            
            self.log_activity("Content generation completed", {
                "word_count": content.word_count,
                "reading_time": content.reading_time_minutes
            })
            
        except Exception as e:
            state.error_message = f"Content generation failed: {str(e)}"
            self.log_activity("Content generation failed", {"error": str(e)})
            
        return state
    
    async def generate_chapter_content(self, request: ContentGenerationRequest) -> GeneratedContent:
        """Generate complete chapter content from a plan."""
        
        # Build the generation prompt
        prompt = self._build_content_prompt(request)
        
        # Use LLM service to generate content with dynamic system prompt
        llm_service = get_llm_service()
        system_prompt = self.system_prompt + self.level_prompt(request=request)
        generated_text = await llm_service.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=3000  # Adequate for chapter content
        )
        
        # Process the generated content
        processed_content = self._process_generated_content(generated_text, request)
        
        return processed_content
    
    def _build_content_prompt(self, request: ContentGenerationRequest) -> str:
        """Build a detailed prompt for content generation."""
        
        prompt_parts = []
        
        # Chapter context
        prompt_parts.append(f"Write Chapter {request.chapter_plan.number} of '{request.book_title}' in the '{request.series_title}' series.")
        prompt_parts.append(f"Chapter Title: {request.chapter_plan.title}")
        prompt_parts.append(f"Chapter Summary: {request.chapter_plan.summary}")
        prompt_parts.append("")
        
        # Target audience and reading level
        prompt_parts.append(f"Target Audience: {request.target_audience}")
        prompt_parts.append(f"Reading Level: {request.reading_level}")
        prompt_parts.append("")
        
        # Characters
        if request.characters:
            prompt_parts.append("Main Characters:")
            for char in request.characters:
                prompt_parts.append(f"- {char.name}: {char.role}")

            prompt_parts.append("")
        
        # Educational themes
        if request.educational_themes:
            prompt_parts.append(f"Educational Themes to Include: {', '.join(request.educational_themes)}")
            prompt_parts.append("")
        
        # Previous context (to maintain cohesion)
        if request.previous_chapters_summary:
            prompt_parts.append("Context from previous chapters (use to maintain continuity, do NOT repeat events):")
            prompt_parts.append(request.previous_chapters_summary)
            prompt_parts.append("")
        
        # Chapter plan guidance (no literal scene headings)
        prompt_parts.append("Chapter Guidance (for the author only, do not include these labels in the output):")
        for i, scene in enumerate(request.chapter_plan.scenes, 1):
            prompt_parts.append(f"- Scene idea {i}: {scene.title} | Setting: {scene.setting} | Characters: {', '.join(scene.characters_present)} | Key events: {', '.join(scene.key_events)}")
        prompt_parts.append("")
        
        # Strong content requirements to reduce repetition and improve flow
        prompt_parts.append("Content Requirements:")
        prompt_parts.append("- Write 1000-1500 words of continuous story prose (no bullet lists, no outline labels).")
        prompt_parts.append("- Do NOT include headings like 'Scene 1', 'Scene 2', or any meta-structure labels.")
        prompt_parts.append("- Avoid repetitive phrasing and formulaic chapter endings; do NOT use 'To be continued'.")
        prompt_parts.append("- Ensure this chapter has a unique voice and events distinct from other chapters.")
        prompt_parts.append("- Maintain narrative continuity with previous chapters; reference past events naturally.")
        prompt_parts.append("- Include natural dialogue and child-friendly descriptions; focus on feelings, actions, and learning moments.")
        prompt_parts.append("- Use age-appropriate vocabulary and sentence structure; keep paragraphs short and engaging.")
        prompt_parts.append("- End with a satisfying beat that transitions logically to the next chapter, not a cliff-hanger unless appropriate.")
        prompt_parts.append("")
        
        prompt_parts.append("Write the complete chapter content now (no headings or meta commentary):")
        
        return "\n".join(prompt_parts)
    
    def _process_generated_content(self, generated_text: str, request: ContentGenerationRequest) -> GeneratedContent:
        """Process and validate generated content."""
        
        # Clean up the generated text
        content = generated_text.strip()
        
        # Calculate metrics
        word_count = len(content.split())
        reading_time_minutes = max(1, word_count // 30)  # ~30 words per minute for children
        
        # Extract educational elements mentioned
        educational_elements_included = []
        for theme in request.educational_themes:
            if theme.lower() in content.lower():
                educational_elements_included.append(theme)
        
        # Basic character development tracking
        character_development_notes = []
        for char in request.characters:
            char_name = char.name
            if char_name in content:
                character_development_notes.append(f"{char_name} appears in this chapter")
        
        return GeneratedContent(
            title=request.chapter_plan.title,
            content=content,
            word_count=word_count,
            reading_time_minutes=reading_time_minutes,
            educational_elements_included=educational_elements_included,
            character_development_notes=character_development_notes
        )