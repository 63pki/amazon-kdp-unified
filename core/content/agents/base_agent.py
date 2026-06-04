"""Base agent class for the book generation system."""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

from ..models.config import GenerationConfig


class AgentState(BaseModel):
    """Base state for agents."""
    
    messages: List[BaseMessage] = []
    context: Dict[str, Any] = {}
    error_message: Optional[str] = None
    retry_count: int = 0


class BaseAgent(ABC):
    """Base class for all agents in the book generation system."""
    
    def __init__(self, config: GenerationConfig):
        """Initialize the agent with configuration."""
        self.config = config
        self.llm = ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.openai_model,
            temperature=config.openai_temperature,
        )
        
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Return the name of this agent."""
        raise NotImplementedError("Subclasses must implement agent_name property")
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        raise NotImplementedError("Subclasses must implement system_prompt property")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[BaseModel]] = None
    ) -> str:
        """Generate a response using the LLM."""
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt)
        ]
        
        if context:
            context_str = self._format_context(context)
            messages.insert(1, HumanMessage(content=f"Context: {context_str}"))
        
        try:
            response = await self.llm.ainvoke(messages)
            
            if response_model:
                # Try to parse as structured output
                try:
                    parsed = response_model.model_validate_json(response.content)
                    return parsed.model_dump_json(indent=2)
                except Exception as parse_error:
                    raise ValueError(
                        f"Failed to parse LLM response into {response_model.__name__}: {parse_error}"
                    )
                    
            return response.content
            
        except Exception as e:
            raise Exception(f"LLM generation failed for {self.agent_name}: {str(e)}")
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary for inclusion in prompts."""
        formatted_items = []
        for key, value in context.items():
            if isinstance(value, (dict, list)):
                formatted_items.append(f"{key}: {json.dumps(value, indent=2)}")
            else:
                formatted_items.append(f"{key}: {value}")
        return "\n".join(formatted_items)
    
    def create_detailed_prompt(
        self, 
        task_description: str,
        requirements: List[str],
        constraints: List[str],
        examples: Optional[List[str]] = None
    ) -> str:
        """Create a detailed, structured prompt."""
        prompt_parts = [
            f"Task: {task_description}",
            "",
            "Requirements:",
        ]
        
        for i, req in enumerate(requirements, 1):
            prompt_parts.append(f"{i}. {req}")
        
        if constraints:
            prompt_parts.extend(["", "Constraints:"])
            for i, constraint in enumerate(constraints, 1):
                prompt_parts.append(f"{i}. {constraint}")
        
        if examples:
            prompt_parts.extend(["", "Examples:"])
            for i, example in enumerate(examples, 1):
                prompt_parts.append(f"{i}. {example}")
        
        return "\n".join(prompt_parts)
    
    def validate_output(self, output: str, validation_rules: List[str]) -> List[str]:
        """Validate generated output against rules."""
        issues = []
        
        # Basic validation
        if not output or not output.strip():
            issues.append("Output is empty")
            return issues
        
        # Apply custom validation rules
        for rule in validation_rules:
            if not self._check_validation_rule(output, rule):
                issues.append(f"Validation failed: {rule}")
        
        return issues
    
    def _check_validation_rule(self, output: str, rule: str) -> bool:
        """Check a single validation rule against output."""
        # This is a simplified validation system
        # In practice, you'd implement more sophisticated rule checking
        
        if "word_count" in rule:
            # Extract expected word count from rule
            try:
                parts = rule.split()
                if "minimum" in rule:
                    min_words = int([p for p in parts if p.isdigit()][0])
                    return len(output.split()) >= min_words
                elif "maximum" in rule:
                    max_words = int([p for p in parts if p.isdigit()][0])
                    return len(output.split()) <= max_words
            except (IndexError, ValueError):
                pass
        
        if "contains" in rule:
            # Check if output contains required text
            required_text = rule.split("contains:")[-1].strip()
            return required_text.lower() in output.lower()
        
        return True  # Default to passing if rule not recognized
    
    async def process_with_feedback_loop(
        self,
        initial_prompt: str,
        validation_rules: List[str],
        max_iterations: int = 3,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process with feedback loop for quality improvement."""
        current_output = None
        
        for iteration in range(max_iterations):
            if iteration == 0:
                prompt = initial_prompt
            else:
                # Create feedback prompt
                issues = self.validate_output(current_output, validation_rules)
                if not issues:
                    break  # Output is valid
                
                feedback = "Please revise your previous response to address these issues:\n"
                feedback += "\n".join(f"- {issue}" for issue in issues)
                feedback += f"\n\nPrevious response:\n{current_output}"
                prompt = feedback
            
            current_output = await self.generate_response(prompt, context)
        
        return current_output
    
    def log_activity(self, activity: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log agent activity for debugging and monitoring."""
        logger = logging.getLogger(f"bsg.{self.agent_name}")
        if details:
            logger.info("%s | details=%s", activity, details)
        else:
            logger.info("%s", activity)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the agent's main functionality."""
        pass