"""Consistency checking agent for maintaining series coherence."""

from typing import Dict, List, Any, Set
from collections import defaultdict
import re

from ..models.book import BookSeries, Book, Chapter
from ..models.character import Character
from .base_agent import AgentState, BaseAgent


class ConsistencyIssue:
    """Represents a consistency issue found in the series."""
    
    def __init__(self, issue_type: str, description: str, severity: str, location: str):
        self.issue_type = issue_type
        self.description = description
        self.severity = severity  # "low", "medium", "high", "critical"
        self.location = location
    
    def __str__(self):
        return f"[{self.severity.upper()}] {self.issue_type}: {self.description} (Location: {self.location})"


class ConsistencyAgent(BaseAgent):
    """Ensures consistency across the book series."""
    
    @property
    def agent_name(self) -> str:
        return "ConsistencyAgent"
    
    @property
    def system_prompt(self) -> str:
        return """You are the Consistency Agent, responsible for maintaining coherence across book series.

Your responsibilities include:
- Checking character consistency across books and scenes
- Ensuring plot continuity and logical progression
- Maintaining consistent world-building and settings
- Verifying educational theme integration
- Checking for appropriate difficulty progression
- Ensuring series-wide quality standards

You identify inconsistencies and suggest corrections to maintain a cohesive, high-quality reading experience throughout the entire series."""
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute consistency checking on the book series."""
        try:
            self.log_activity("Starting consistency check")
            
            series_data = state.context.get("book_series")
            if not series_data:
                state.error_message = "No series data provided for consistency check"
                return state
            
            # Perform various consistency checks
            series = BookSeries.model_validate(series_data)
            issues = await self.validate_series_consistency(series)
            
            state.context["consistency_issues"] = [str(issue) for issue in issues]
            state.context["consistency_check_passed"] = len(issues) == 0
            
            if issues:
                self.log_activity("Consistency issues found", {"issues": [str(i) for i in issues]})
            else:
                self.log_activity("Consistency check passed")
            
        except Exception as e:
            state.error_message = f"Consistency check failed: {str(e)}"
            self.log_activity("Consistency check failed", {"error": str(e)})
            
        return state
    
    async def validate_series_consistency(self, series: BookSeries) -> Dict[str, Any]:
        """Validate consistency across the entire series."""
        
        issues = []
        
        # Character consistency checks
        character_issues = self._check_character_consistency(series)
        issues.extend(character_issues)
        
        # Plot continuity checks
        plot_issues = self._check_plot_continuity(series)
        issues.extend(plot_issues)
        
        # Educational theme consistency
        theme_issues = self._check_educational_themes(series)
        issues.extend(theme_issues)
        
        # Reading level progression
        reading_issues = self._check_reading_level_progression(series)
        issues.extend(reading_issues)
        
        # World-building consistency
        world_issues = self._check_world_building(series)
        issues.extend(world_issues)
        
        # Quality consistency
        quality_issues = self._check_quality_standards(series)
        issues.extend(quality_issues)
        
        # Create summary report
        return {
            "overall_consistent": len(issues) == 0,
            "total_issues": len(issues),
            "issues": [str(issue) for issue in issues],
            "issues_by_severity": self._categorize_issues_by_severity(issues),
            "issues_by_type": self._categorize_issues_by_type(issues),
            "critical_issues": [str(i) for i in issues if i.severity == "critical"],
            "recommendations": self._generate_recommendations(issues)
        }
    
    def _check_character_consistency(self, series: BookSeries) -> List[ConsistencyIssue]:
        """Check for character consistency across the series."""
        issues = []
        
        # Track character appearances and descriptions
        character_tracker = defaultdict(lambda: {"descriptions": [], "locations": []})
        
        for book in series.books:
            for chapter in book.chapters:
                # Extract character mentions from content
                for character in series.main_characters:
                    if character.name in chapter.content:
                        character_tracker[character.name]["descriptions"].append(chapter.content)
                        character_tracker[character.name]["locations"].append(f"Book {book.book_number}, Chapter {chapter.number}")
        
        # Check for consistency issues
        for char_name, data in character_tracker.items():
            if len(data["descriptions"]) > 1:
                # Look for potential inconsistencies in character descriptions
                descriptions = data["descriptions"]
                
                # Check for conflicting physical descriptions
                physical_terms = self._extract_physical_descriptions(descriptions)
                conflicts = self._find_conflicting_descriptions(physical_terms)
                
                if conflicts:
                    issues.append(ConsistencyIssue(
                        "character_inconsistency",
                        f"Potential conflicting descriptions for {char_name}: {', '.join(conflicts)}",
                        "medium",
                        f"Multiple locations: {', '.join(data['locations'][:3])}"
                    ))
        
        # Check for missing main characters in books
        for character in series.main_characters:
            appearances = 0
            for book in series.books:
                for chapter in book.chapters:
                    if character.name in chapter.content:
                        appearances += 1
                        break
            
            if appearances == 0:
                issues.append(ConsistencyIssue(
                    "missing_character",
                    f"Main character {character.name} does not appear in any book content",
                    "high",
                    "Series-wide"
                ))
            elif appearances < len(series.books) * 0.5:  # Character appears in less than half the books
                issues.append(ConsistencyIssue(
                    "underutilized_character",
                    f"Main character {character.name} appears in only {appearances} out of {len(series.books)} books",
                    "low",
                    "Series-wide"
                ))
        
        return issues
    
    def _check_plot_continuity(self, series: BookSeries) -> List[ConsistencyIssue]:
        """Check for plot continuity and logical progression."""
        issues = []
        
        if len(series.books) < 2:
            return issues
        
        # Check for logical book progression
        for i in range(1, len(series.books)):
            prev_book = series.books[i-1]
            curr_book = series.books[i]
            
            # Check if there are any references to previous events
            prev_events = self._extract_key_events(prev_book)
            curr_references = self._check_for_references(curr_book, prev_events)
            
            if not curr_references and i > 1:  # Allow first book to not reference previous
                issues.append(ConsistencyIssue(
                    "plot_discontinuity",
                    f"Book {curr_book.book_number} doesn't reference any events from Book {prev_book.book_number}",
                    "medium",
                    f"Book {curr_book.book_number}"
                ))
        
        # Check for series-wide story arc
        first_book = series.books[0]
        last_book = series.books[-1]
        
        # Look for character development progression
        character_development = self._analyze_character_development(series)
        if not character_development:
            issues.append(ConsistencyIssue(
                "no_character_development",
                "No clear character development arc detected across the series",
                "medium",
                "Series-wide"
            ))
        
        return issues
    
    def _check_educational_themes(self, series: BookSeries) -> List[ConsistencyIssue]:
        """Check educational theme consistency and integration."""
        issues = []
        
        series_themes = set(series.educational_elements)
        
        for book in series.books:
            book_themes = set(book.educational_themes or [])
            
            # Check if book themes align with series themes
            if not book_themes.intersection(series_themes):
                issues.append(ConsistencyIssue(
                    "theme_misalignment",
                    f"Book {book.book_number} has no educational themes that align with series themes",
                    "medium",
                    f"Book {book.book_number}"
                ))
            
            # Check if educational themes are actually present in content
            for theme in book.educational_themes or []:
                if not self._is_theme_present_in_content(theme, book):
                    issues.append(ConsistencyIssue(
                        "missing_theme_content",
                        f"Educational theme '{theme}' is listed but not clearly present in Book {book.book_number} content",
                        "low",
                        f"Book {book.book_number}"
                    ))
        
        return issues
    
    def _check_reading_level_progression(self, series: BookSeries) -> List[ConsistencyIssue]:
        """Check for appropriate reading level progression."""
        issues = []
        
        if len(series.books) < 2:
            return issues
        
        # Analyze complexity progression
        complexities = []
        for book in series.books:
            complexity = self._calculate_reading_complexity(book)
            complexities.append(complexity)
        
        # Check for appropriate progression (should be stable or slightly increasing)
        for i in range(1, len(complexities)):
            if complexities[i] < complexities[i-1] * 0.8:  # Significant decrease
                issues.append(ConsistencyIssue(
                    "reading_level_regression",
                    f"Book {i+1} appears significantly easier than Book {i} (complexity: {complexities[i]:.2f} vs {complexities[i-1]:.2f})",
                    "low",
                    f"Book {i+1}"
                ))
            elif complexities[i] > complexities[i-1] * 1.5:  # Too big jump
                issues.append(ConsistencyIssue(
                    "reading_level_jump",
                    f"Book {i+1} appears significantly harder than Book {i} (complexity: {complexities[i]:.2f} vs {complexities[i-1]:.2f})",
                    "medium",
                    f"Book {i+1}"
                ))
        
        return issues
    
    def _check_world_building(self, series: BookSeries) -> List[ConsistencyIssue]:
        """Check for consistent world-building across the series."""
        issues = []
        
        # Track settings and locations mentioned
        locations = defaultdict(lambda: {"descriptions": [], "books": []})
        
        for book in series.books:
            for chapter in book.chapters:
                # Extract location mentions (simplified)
                content_words = chapter.content.lower().split()
                for scene in chapter.scenes:
                    location = scene.setting
                    locations[location]["descriptions"].append(scene.setting)
                    locations[location]["books"].append(book.book_number)
        
        # Check for consistent location descriptions
        for location, data in locations.items():
            if len(set(data["books"])) > 1:  # Location appears in multiple books
                # Check for consistency (simplified check)
                descriptions = data["descriptions"]
                if len(set(descriptions)) > 1:
                    issues.append(ConsistencyIssue(
                        "location_inconsistency",
                        f"Location '{location}' has varying descriptions across books",
                        "low",
                        f"Books: {', '.join(map(str, set(data['books'])))}"
                    ))
        
        return issues
    
    def _check_quality_standards(self, series: BookSeries) -> List[ConsistencyIssue]:
        """Check for consistent quality standards."""
        issues = []
        
        # Check word count consistency
        word_counts = [book.word_count for book in series.books if book.word_count]
        if word_counts:
            avg_words = sum(word_counts) / len(word_counts)
            for book in series.books:
                if book.word_count and abs(book.word_count - avg_words) > avg_words * 0.5:
                    issues.append(ConsistencyIssue(
                        "word_count_variation",
                        f"Book {book.book_number} word count ({book.word_count}) significantly differs from series average ({avg_words:.0f})",
                        "low",
                        f"Book {book.book_number}"
                    ))
        
        # Check chapter count consistency
        chapter_counts = [len(book.chapters) for book in series.books]
        if chapter_counts:
            avg_chapters = sum(chapter_counts) / len(chapter_counts)
            for book in series.books:
                if abs(len(book.chapters) - avg_chapters) > avg_chapters * 0.5:
                    issues.append(ConsistencyIssue(
                        "chapter_count_variation",
                        f"Book {book.book_number} has {len(book.chapters)} chapters, significantly different from series average ({avg_chapters:.1f})",
                        "low",
                        f"Book {book.book_number}"
                    ))
        
        return issues
    
    # Helper methods
    
    def _extract_physical_descriptions(self, descriptions: List[str]) -> List[str]:
        """Extract physical description terms from text."""
        physical_terms = []
        for desc in descriptions:
            # Look for common physical descriptors
            words = desc.lower().split()
            for word in words:
                if word in ['tall', 'short', 'blonde', 'brown', 'blue', 'green', 'curly', 'straight']:
                    physical_terms.append(word)
        return physical_terms
    
    def _find_conflicting_descriptions(self, terms: List[str]) -> List[str]:
        """Find conflicting physical descriptions."""
        conflicts = []
        conflicting_pairs = [
            ('tall', 'short'),
            ('blonde', 'brown'),
            ('blue', 'green'),
            ('curly', 'straight')
        ]
        
        for pair in conflicting_pairs:
            if pair[0] in terms and pair[1] in terms:
                conflicts.append(f"{pair[0]} vs {pair[1]}")
        
        return conflicts
    
    def _extract_key_events(self, book: Book) -> List[str]:
        """Extract key events from a book."""
        events = []
        for chapter in book.chapters:
            for scene in chapter.scenes:
                events.extend(scene.plot_points)
        return events
    
    def _check_for_references(self, book: Book, prev_events: List[str]) -> bool:
        """Check if a book references previous events."""
        content = " ".join([chapter.content for chapter in book.chapters]).lower()
        for event in prev_events:
            if event.lower() in content:
                return True
        return False
    
    def _analyze_character_development(self, series: BookSeries) -> bool:
        """Analyze character development across the series."""
        # Simplified check - look for character names in different contexts
        for character in series.main_characters:
            first_appearance = None
            last_appearance = None
            
            for book in series.books:
                for chapter in book.chapters:
                    if character.name in chapter.content:
                        if first_appearance is None:
                            first_appearance = chapter.content
                        last_appearance = chapter.content
            
            # If character appears in different contexts, assume development
            if first_appearance and last_appearance and first_appearance != last_appearance:
                return True
        
        return False
    
    def _is_theme_present_in_content(self, theme: str, book: Book) -> bool:
        """Check if an educational theme is present in book content."""
        content = " ".join([chapter.content for chapter in book.chapters]).lower()
        theme_words = theme.lower().split()
        
        for word in theme_words:
            if word in content:
                return True
        
        return False
    
    def _calculate_reading_complexity(self, book: Book) -> float:
        """Calculate reading complexity score for a book."""
        total_words = 0
        total_sentences = 0
        total_syllables = 0
        
        for chapter in book.chapters:
            words = chapter.content.split()
            total_words += len(words)
            
            # Count sentences (simplified)
            sentences = len([s for s in chapter.content.split('.') if s.strip()])
            total_sentences += sentences
            
            # Estimate syllables (simplified)
            for word in words:
                total_syllables += max(1, len([c for c in word.lower() if c in 'aeiou']))
        
        if total_sentences == 0:
            return 0
        
        # Simplified Flesch-Kincaid-like formula
        avg_sentence_length = total_words / total_sentences
        avg_syllables_per_word = total_syllables / total_words if total_words > 0 else 0
        
        complexity = avg_sentence_length + avg_syllables_per_word
        return complexity
    
    def _categorize_issues_by_severity(self, issues: List[ConsistencyIssue]) -> Dict[str, int]:
        """Categorize issues by severity level."""
        severity_counts = defaultdict(int)
        for issue in issues:
            severity_counts[issue.severity] += 1
        return dict(severity_counts)
    
    def _categorize_issues_by_type(self, issues: List[ConsistencyIssue]) -> Dict[str, int]:
        """Categorize issues by type."""
        type_counts = defaultdict(int)
        for issue in issues:
            type_counts[issue.issue_type] += 1
        return dict(type_counts)
    
    def _generate_recommendations(self, issues: List[ConsistencyIssue]) -> List[str]:
        """Generate recommendations based on found issues."""
        recommendations = []
        
        issue_types = set(issue.issue_type for issue in issues)
        
        if "character_inconsistency" in issue_types:
            recommendations.append("Review character descriptions for consistency across all books")
        
        if "plot_discontinuity" in issue_types:
            recommendations.append("Add references to previous book events to maintain story continuity")
        
        if "theme_misalignment" in issue_types:
            recommendations.append("Ensure educational themes are consistent with series goals")
        
        if "reading_level_jump" in issue_types:
            recommendations.append("Smooth out reading difficulty progression between books")
        
        if not recommendations:
            recommendations.append("Series shows good consistency overall")
        
        return recommendations