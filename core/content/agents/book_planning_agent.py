"""Book planning agent for creating detailed content plans."""

import json
from typing import Any, Dict, List
import logging

from ..models.book import BookSeries
from ..models.content import ChapterPlan, ContentPlan, Scene
from ..services.structured_llm_service import StructuredBookPlanningService
from .base_agent import AgentState, BaseAgent


class BookPlanningAgent(BaseAgent):
    """Creates detailed content plans for individual books in the series."""
    
    @property
    def agent_name(self) -> str:
        return "BookPlanningAgent"
    
    @property
    def system_prompt(self) -> str:
        return """You are the Book Planning Agent, an expert at creating detailed, engaging content plans for children's books.

Your specialties include:
- Breaking down book concepts into well-structured chapters and scenes
- Ensuring proper pacing and story arc development
- Balancing educational content with entertainment
- Creating age-appropriate content progression
- Maintaining character consistency and development
- Planning effective scene transitions and plot points

You create comprehensive content plans that serve as blueprints for content generation, ensuring each book is well-structured, engaging, and educationally valuable.

Always provide detailed, actionable plans with clear scene descriptions, character development notes, and educational integration points."""
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute book planning for a specific book."""
        try:
            self.log_activity("Starting book planning")
            
            # Get required context
            book_number = state.context.get("book_number", 1)
            series_data = state.context.get("book_series")
            
            if not series_data:
                state.error_message = "No series data provided for book planning"
                return state
            
            # Create content plan
            content_plan = await self._create_content_plan(book_number, series_data)
            
            # Store the plan in context
            state.context["content_plan"] = content_plan
            state.context["book_plan"] = content_plan  # For backwards compatibility
            
            self.log_activity("Book planning completed", {
                "book_number": book_number,
                "chapters": len(content_plan.chapters),
                "total_scenes": sum(len(chapter.scenes) for chapter in content_plan.chapters),
                "estimated_words": content_plan.estimated_word_count
            })
            
        except Exception as e:
            error_msg = f"Book planning failed: {str(e)}"
            self.log_activity("Book planning failed", {"error": error_msg})
            state.error_message = error_msg
        
        return state
    
    async def create_book_plan(self, series_overview, book_number: int):
        """Public method to create a book plan for CLI usage.
        
        Args:
            series_overview: SeriesOverview object with series information
            book_number: Number of the book to plan (1-indexed)
            
        Returns:
            BookPlan object with detailed chapter structure
        """
        try:
            self.log_activity("Creating book plan using structured outputs", {"book_number": book_number})
            
            # Use structured output service for modern, type-safe generation
            # Expose at module scope for tests to patch
            from ..models.config import LLMConfig
            
            # Create LLM config from agent config
            llm_config = LLMConfig.from_generation_config(
                self.config,
                provider="openai"
            )
            # Respect the user's model choice - no overrides!
            
            # Initialize structured service
            structured_service = StructuredBookPlanningService(llm_config)
            
            # Generate book plan using structured outputs
            book_plan = await structured_service.create_book_plan(
                series_overview,
                book_number,
                word_count_per_book=self.config.word_count_per_book,
                chapters_per_book=self.config.chapters_per_book
            )
            
            self.log_activity("Book plan created successfully with structured outputs", {
                "book_number": book_number,
                "title": book_plan.book_title,
                "chapters": len(book_plan.chapter_plans),
                "estimated_words": book_plan.estimated_word_count,
                "method": "structured_outputs"
            })
            
            return book_plan
            
        except Exception as e:
            error_msg = f"Failed to create book plan: {str(e)}"
            logging.getLogger("bsg.BookPlanningAgent").exception("Book planning failed")
            raise RuntimeError(error_msg) from e
    
    # Fallback book plan method has been removed to enforce strict structured generation.
    
    async def _create_content_plan(self, book_number: int, series_data: Dict[str, Any]) -> ContentPlan:
        """Create a detailed content plan for a specific book."""
        
        # Extract series information
        overview = series_data["overview"]
        main_characters = overview["main_characters"]
        overarching_plot = overview["overarching_plot"]
        themes = overview["themes"]
        
        # Generate book concept
        book_concept = await self._generate_book_concept(
            book_number, overarching_plot, themes, main_characters
        )
        
        # Create chapter structure
        chapters = await self._create_chapter_structure(book_concept, main_characters)
        
        # Build complete content plan
        content_plan = ContentPlan(
            title=book_concept["title"],
            concept=book_concept["plot_summary"],  # Map plot_summary to concept
            target_themes=book_concept["educational_themes"],  # Map educational_themes to target_themes
            chapters=chapters,
            estimated_word_count=self.config.word_count_per_book  # Map target_word_count to estimated_word_count
        )
        
        return content_plan
    
    async def _generate_book_concept(
        self, 
        book_number: int, 
        overarching_plot: str, 
        themes: List[str],
        characters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate the core concept for a specific book."""
        
        # Create character summaries
        character_summaries = []
        for char in characters:
            name = char["name"]
            role = char["role"]
            traits = char.get("personality", {}).get("primary_traits", [])
            character_summaries.append(f"{name} ({role}): {', '.join(traits)}")
        
        concept_prompt = self.create_detailed_prompt(
            task_description=f"Create a detailed concept for Book {book_number} in the series",
            requirements=[
                f"Build on this overarching plot: {overarching_plot}",
                f"Incorporate these themes: {', '.join(themes)}",
                f"Feature these characters: {'; '.join(character_summaries)}",
                f"Target {self.config.word_count_per_book} words across {self.config.chapters_per_book} chapters",
                f"Appropriate for ages {self.config.target_age_range}",
                f"Reading level: {self.config.lexile_level}",
                "Include educational elements naturally in the story",
                "Ensure the book can stand alone while advancing the series",
                "Create character development opportunities",
                "Include a clear conflict and satisfying resolution"
            ],
            constraints=[
                "Keep content age-appropriate and positive",
                "Avoid scary or inappropriate themes",
                "Ensure logical story progression",
                "Balance education with entertainment",
                "Maintain character consistency"
            ],
            examples=[
                "A book where characters learn about ecosystems while solving a mystery",
                "An adventure that teaches problem-solving through teamwork",
                "A story that explores different cultures through friendship"
            ]
        )
        
        concept_response = await self.generate_response(concept_prompt)
        
        # Structure the response
        return await self._parse_book_concept(concept_response, book_number)
    
    async def _parse_book_concept(self, response: str, book_number: int) -> Dict[str, Any]:
        """Parse the book concept response into structured data."""
        
        structure_prompt = f"""
        Convert this book concept into a structured JSON format:

        {response}

        Return a JSON object with these fields:
        - title: string (book title)
        - theme: string (main theme)
        - plot_summary: string (overall plot summary)
        - main_conflict: string (primary conflict)
        - resolution: string (how conflict is resolved)
        - character_arcs: object (character development notes)
        - series_plot_advancement: string (how this advances the series)
        - setup_for_next_book: string (setup for next book, if not the last)
        - callbacks_to_previous: array (references to previous books)
        - educational_themes: array (educational themes)
        - lessons: array (age-appropriate lessons)
        - cross_curricular: array (connections to school subjects)
        - cover_concept: string (cover image concept)
        - key_illustrations: array (important illustrations needed)

        Focus on Book {book_number} specifically.
        """
        
        structured_response = await self.generate_response(structure_prompt)
        
        try:
            # Extract JSON from markdown code blocks if present
            clean_json = self._extract_json_from_response(structured_response)
            return json.loads(clean_json)
        except json.JSONDecodeError as e:
            logging.getLogger("bsg.BookPlanningAgent").exception("Failed to parse book concept JSON")
            raise ValueError(f"Failed to parse book concept JSON: {e}")
    
    async def _create_chapter_structure(
        self, 
        book_concept: Dict[str, Any], 
        characters: List[Dict[str, Any]]
    ) -> List[ChapterPlan]:
        """Create detailed chapter plans for the book."""
        
        chapters = []
        words_per_chapter = self.config.word_count_per_book // self.config.chapters_per_book
        
        # Create chapter planning prompt
        structure_prompt = self.create_detailed_prompt(
            task_description=f"Create {self.config.chapters_per_book} chapter outlines for this book",
            requirements=[
                f"Book concept: {book_concept['plot_summary']}",
                f"Main conflict: {book_concept['main_conflict']}",
                f"Resolution: {book_concept['resolution']}",
                f"Each chapter should be approximately {words_per_chapter} words",
                "Include 2-3 scenes per chapter",
                "Show clear story progression",
                "Include character development moments",
                "Balance action with quieter character moments",
                "End chapters with hooks or satisfying conclusions"
            ],
            constraints=[
                "Maintain age-appropriate content",
                "Ensure logical story flow",
                "Include all main characters meaningfully",
                "Balance dialogue and narrative",
                "Keep pacing engaging for young readers"
            ]
        )
        
        chapter_response = await self.generate_response(structure_prompt)
        
        # Parse and create individual chapters
        for i in range(1, self.config.chapters_per_book + 1):
            chapter = await self._create_single_chapter_plan(
                i, chapter_response, book_concept, characters, words_per_chapter
            )
            chapters.append(chapter)
        
        return chapters
    
    async def _create_single_chapter_plan(
        self,
        chapter_number: int,
        full_structure: str,
        book_concept: Dict[str, Any],
        characters: List[Dict[str, Any]],
        target_words: int
    ) -> ChapterPlan:
        """Create a detailed plan for a single chapter."""
        
        # Create chapter-specific progression
        total_chapters = self.config.chapters_per_book
        progression_prompts = {
            1: "This is the OPENING chapter. Introduce characters, setting, and the main challenge/adventure. Set the tone and hook readers.",
            2: "This is an EARLY chapter. Characters begin their journey, encounter first obstacles, start working together. Build momentum.",
            3: "This is a MIDDLE chapter. Characters face significant challenges, learn important lessons, show growth. Develop relationships.",
            4: "This is a MIDDLE chapter. Complications arise, characters must overcome bigger obstacles, tensions may increase.",
            5: "This is a LATE chapter. Characters approach the climax, use everything they've learned, prepare for final challenge.",
            6: "This is the FINAL chapter. Resolve the main conflict, show character growth, celebrate learning, set up for next book if applicable."
        }
        
        progression_note = progression_prompts.get(
            chapter_number, 
            f"This is chapter {chapter_number} of {total_chapters}. Continue the story progression logically."
        )
        
        # Get character names for specific references
        character_names = [char.get("name", "Character") for char in characters[:3]]  # Top 3 characters
        
        # Extract chapter-specific information
        chapter_prompt = f"""
        Create a unique, specific plan for Chapter {chapter_number} of "{book_concept['title']}".

        STORY CONTEXT:
        - Book Theme: {book_concept.get('theme', 'adventure and learning')}
        - Main Conflict: {book_concept.get('main_conflict', 'Characters face challenges')}
        - Characters: {', '.join(character_names)}
        - Educational Themes: {', '.join(book_concept.get('educational_themes', ['friendship']))}

        CHAPTER PROGRESSION:
        {progression_note}

        REQUIREMENTS FOR CHAPTER {chapter_number}:
        1. Create a UNIQUE chapter title (not "A New Discovery" - be creative!)
        2. Write a specific 2-3 sentence summary for THIS chapter only
        3. Design 2-3 distinct scenes:
           - Each scene should have a SPECIFIC setting (not "welcoming environment")
           - Name actual characters, not "main characters"
           - Create unique events that advance the plot for this specific chapter
           - Use different emotional tones for variety
           - Total scenes should be ~{target_words} words
        4. List specific plot points for this chapter
        5. Show how characters develop in this specific chapter
        6. Identify themes explored uniquely in this chapter
        7. Set age-appropriate learning objectives for this chapter
        8. Suggest specific images needed for this chapter

        IMPORTANT: Make this chapter distinctly different from other chapters. Each chapter should feel like a unique part of the adventure with its own personality, challenges, and rewards.

        Full story structure for reference:
        {full_structure}
        """
        
        chapter_response = await self.generate_response(chapter_prompt)
        
        # Parse the response into a ChapterPlan
        return await self._parse_chapter_plan(chapter_number, chapter_response, target_words)
    
    async def _parse_chapter_plan(
        self, 
        chapter_number: int, 
        response: str, 
        target_words: int
    ) -> ChapterPlan:
        """Parse chapter planning response into a ChapterPlan object."""
        
        # Debug logging
        self.log_activity(f"Parsing chapter {chapter_number} plan", {
            "response_length": len(response),
            "response_preview": response[:200] + "..." if len(response) > 200 else response
        })
        
        # Use structured parsing
        structure_prompt = f"""
        Convert this chapter plan into structured JSON:

        {response}

        Return JSON with:
        - title: string
        - summary: string
        - scenes: array of scene objects with:
          * title, setting, characters_present (array), purpose
          * key_events (array), emotional_tone
          * estimated_word_count, educational_elements (array)
          * image_opportunities (array)
        - plot_points: array
        - character_development: object
        - themes_explored: array
        - learning_objectives: array
        - vocabulary_words: array
        - image_requirements: array

        For Chapter {chapter_number}.
        """
        
        structured_response = await self.generate_response(structure_prompt)
        
        # Debug logging for structured response
        self.log_activity(f"Chapter {chapter_number} structured response", {
            "response_length": len(structured_response),
            "response_preview": structured_response[:300] + "..." if len(structured_response) > 300 else structured_response
        })
        
        try:
            # Extract JSON from markdown code blocks if present
            clean_json = self._extract_json_from_response(structured_response)
            data = json.loads(clean_json)
            
            # Debug successful parsing
            self.log_activity(f"Chapter {chapter_number} JSON parsing successful", {
                "title": data.get("title", "NO_TITLE"),
                "scenes_count": len(data.get("scenes", [])),
                "summary_length": len(data.get("summary", ""))
            })
            
            # Create Scene objects
            scenes = []
            for scene_data in data.get("scenes", []):
                scene = Scene(
                    title=scene_data["title"],
                    setting=scene_data["setting"],
                    characters_present=scene_data["characters_present"],
                    purpose=scene_data["purpose"],
                    key_events=scene_data["key_events"],
                    emotional_tone=scene_data["emotional_tone"],
                    estimated_word_count=scene_data["estimated_word_count"],
                    educational_elements=scene_data.get("educational_elements", []),
                    image_opportunities=scene_data.get("image_opportunities", []),
                    # Include missing fields that were being dropped
                    dialogue_notes=scene_data.get("dialogue_notes"),
                    continuity_notes=scene_data.get("continuity_notes")
                )
                
                # Validate the conversion to catch field-dropping bugs
                from ..utils.model_validation import validate_scene_and_warn
                validate_scene_and_warn(scene_data, scene, scene_data.get("title", "Unknown"))
                
                scenes.append(scene)
            
            return ChapterPlan(
                number=chapter_number,
                title=data["title"],
                summary=data["summary"],
                scenes=scenes,
                estimated_word_count=target_words,
                plot_points=data.get("plot_points", []),
                character_development=data.get("character_development", {}),
                themes_explored=data.get("themes_explored", []),
                learning_objectives=data.get("learning_objectives", []),
                vocabulary_words=data.get("vocabulary_words", []),
                image_requirements=data.get("image_requirements", []),
                # Include special_formatting that was being dropped
                special_formatting=data.get("special_formatting")
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logging.getLogger("bsg.BookPlanningAgent").exception("Failed to parse structured chapter plan")
            raise ValueError(f"Failed to parse structured chapter plan for chapter {chapter_number}: {e}")
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from a response that may be wrapped in markdown code blocks."""
        
        # Remove leading/trailing whitespace
        response = response.strip()
        
        # Check if response is wrapped in markdown code blocks
        if response.startswith('```json') and response.endswith('```'):
            # Extract content between ```json and ```
            lines = response.split('\n')
            # Remove first line (```json) and last line (```)
            json_lines = lines[1:-1]
            return '\n'.join(json_lines)
        elif response.startswith('```') and response.endswith('```'):
            # Generic code block without json specifier
            lines = response.split('\n')
            json_lines = lines[1:-1]
            return '\n'.join(json_lines)
        elif '```json' in response:
            # JSON block somewhere in the middle
            start_marker = '```json'
            end_marker = '```'
            start_idx = response.find(start_marker)
            if start_idx != -1:
                start_idx += len(start_marker)
                end_idx = response.find(end_marker, start_idx)
                if end_idx != -1:
                    return response[start_idx:end_idx].strip()
        
        # If no markdown blocks found, return as-is
        return response