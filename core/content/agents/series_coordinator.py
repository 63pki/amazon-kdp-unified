"""Series coordinator agent for orchestrating book series generation."""

import json
from typing import Any, Dict, List
import logging

from ..models.book import BookSeries, SeriesOverview
from ..models.character import Character, PersonalityTraits, PhysicalAppearance, CharacterBackground
from ..models.config import GenerationConfig, LLMConfig
from .base_agent import AgentState, BaseAgent
from ..services.structured_llm_service import StructuredLLMService
from ..models.content import StructuredSeriesOverview


class SeriesCoordinator(BaseAgent):
    """Coordinates the overall book series generation process."""
    
    @property
    def agent_name(self) -> str:
        return "SeriesCoordinator"
    
    @property
    def system_prompt(self) -> str:
        return """You are the Series Coordinator, responsible for creating compelling children's book series.

Your expertise includes:
- Developing engaging overarching plots that span multiple books
- Creating memorable characters with consistent personalities and growth arcs
- Ensuring educational value while maintaining entertainment
- Balancing themes appropriate for young readers
- Establishing consistent tone, style, and world-building

You create series that children will love to read and learn from, with logical progression and character development across books. Focus on creating series that are both entertaining and educational, with strong themes of friendship, problem-solving, and discovery.

Always respond with valid JSON that matches the expected schema."""
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute series planning and coordination."""
        try:
            self.log_activity("Starting series coordination")
            
            # Get series concept from context
            series_concept = state.context.get("series_concept", "")
            if not series_concept:
                state.error_message = "No series concept provided"
                return state
            
            # Generate series overview
            overview = await self._generate_series_overview(series_concept)
            
            # Create book series structure
            series = BookSeries(overview=overview)
            
            state.context["book_series"] = series.model_dump()
            state.context["series_overview"] = overview.model_dump()
            
            self.log_activity("Series coordination completed", {
                "series_title": overview.title,
                "character_count": len(overview.main_characters),
                "themes": overview.themes
            })
            
        except Exception as e:
            state.error_message = f"Series coordination failed: {str(e)}"
            logging.getLogger("bsg.SeriesCoordinator").exception("Series coordination failed")
        
        return state
    
    async def generate_series_overview(self, concept: str) -> SeriesOverview:
        """Public method to generate series overview from concept."""
        return await self._generate_series_overview(concept)
    
    async def _generate_series_overview(self, concept: str) -> SeriesOverview:
        """Generate a comprehensive series overview using structured outputs."""
        try:
            llm_service = StructuredLLMService(LLMConfig.from_generation_config(self.config))
            structured: StructuredSeriesOverview = await llm_service.generate_series_overview(
                concept=concept,
                target_age_range=self.config.target_age_range,
                books_per_series=self.config.books_per_series,
            )
            return self._structured_to_overview(structured)
        except Exception as e:
            logging.getLogger("bsg.SeriesCoordinator").exception("Structured series overview generation failed")
            raise

    def _structured_to_overview(self, s: StructuredSeriesOverview) -> SeriesOverview:
        """Convert structured overview to domain model - now a simple direct mapping."""
        characters: List[Character] = []
        for cd in s.main_characters:
            # Direct mapping since schemas now match - only add system metadata
            appearance_data = cd.appearance.model_dump() if hasattr(cd.appearance, 'model_dump') else (cd.appearance or {})
            personality_data = cd.personality.model_dump() if hasattr(cd.personality, 'model_dump') else (cd.personality or {})
            background_data = cd.background.model_dump() if hasattr(cd.background, 'model_dump') else (cd.background or {})
            
            # Create domain objects with full data from LLM
            pa = PhysicalAppearance(**appearance_data)
            pt = PersonalityTraits(**personality_data)
            bg = CharacterBackground(**background_data)
            
            character = Character(
                # LLM-generated fields
                name=cd.name,
                role=cd.role,
                age=cd.age,
                species=cd.species or "human",
                appearance=pa,
                personality=pt,
                background=bg,
                importance_level=cd.importance_level or "main",
                first_appearance_book=cd.first_appearance_book,
                character_arc=cd.character_arc,
                relationships=cd.relationships or {},
                # System metadata is auto-generated by Character model
            )
            
            characters.append(character)
        return SeriesOverview(
            title=s.title,
            tagline=s.tagline,
            concept=s.concept,
            main_characters=characters,
            overarching_plot=s.overarching_plot,
            themes=s.themes,
            setting_description=s.setting_description,
            genre=s.genre,
            target_age_range=s.target_age_range,
            lexile_level=s.lexile_level,
            estimated_books=s.estimated_books,
            educational_philosophy=s.educational_philosophy,
            educational_focus=s.educational_focus,
            target_learning_outcomes=s.target_learning_outcomes,
            age_progression=s.age_progression,
            art_style_guide=s.art_style_guide,
            tone_and_voice=s.tone_and_voice,
            formatting_standards=(s.formatting_standards.model_dump() if hasattr(s.formatting_standards, 'model_dump') else (s.formatting_standards or {})),
        )
    
    def _create_character_from_data(self, char_data: Dict[str, Any]) -> Character:
        """Create a Character object from parsed data."""
        
        # Extract appearance data
        appearance_data = char_data.get("appearance", {})
        accessories_raw = appearance_data.get("accessories", [])
        accessories = self._ensure_list_of_strings(accessories_raw, field_path="appearance.accessories")
        appearance = PhysicalAppearance(
            hair_color=appearance_data.get("hair_color"),
            eye_color=appearance_data.get("eye_color"),
            clothing_style=appearance_data.get("clothing_style"),
            accessories=accessories
        )
        
        # Extract personality data
        personality_data = char_data.get("personality", {})
        personality = PersonalityTraits(
            primary_traits=self._ensure_list_of_strings(personality_data.get("primary_traits", []), field_path="personality.primary_traits"),
            strengths=self._ensure_list_of_strings(personality_data.get("strengths", []), field_path="personality.strengths"),
            weaknesses=self._ensure_list_of_strings(personality_data.get("weaknesses", []), field_path="personality.weaknesses"),
            motivations=self._ensure_list_of_strings(personality_data.get("motivations", []), field_path="personality.motivations"),
        )
        
        return Character(
            name=char_data["name"],
            role=char_data.get("role", "supporting character"),
            age=char_data.get("age"),
            species=char_data.get("species", "human"),
            appearance=appearance,
            personality=personality,
            importance_level=char_data.get("importance_level", "main")
        )
    
    def _ensure_list_of_strings(self, value: Any, field_path: str) -> List[str]:
        """Ensure a value is a list of strings; coerce single strings; raise on invalid types."""
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(v) for v in value]
        raise ValueError(f"Field '{field_path}' must be a list of strings or a string; got {type(value).__name__}")

    def _extract_json_from_response(self, response: str) -> str:
        """Extract a JSON object from a response that may include code fences or prose.
        - Handles ```json ... ``` and ``` ... ``` fences
        - If no fences, tries to locate the first JSON object/array heuristically
        """
        if not response:
            return ""
        text = response.strip()
        # Code fences with json
        if text.startswith('```json') and text.endswith('```'):
            lines = text.splitlines()
            return "\n".join(lines[1:-1])
        # Generic code fence
        if text.startswith('```') and text.endswith('```'):
            lines = text.splitlines()
            return "\n".join(lines[1:-1])
        # Embedded fenced block
        if '```json' in text:
            start = text.find('```json') + len('```json')
            end = text.find('```', start)
            if end != -1:
                return text[start:end].strip()
        if '```' in text:
            start = text.find('```') + len('```')
            end = text.find('```', start)
            if end != -1:
                return text[start:end].strip()
        # Heuristic: find first { ... } or [ ... ] block
        first_brace = text.find('{')
        first_bracket = text.find('[')
        idx = min([i for i in [first_brace, first_bracket] if i != -1], default=-1)
        if idx != -1:
            return text[idx:]
        return text