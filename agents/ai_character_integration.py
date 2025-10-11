from typing import Dict, List, Any, Optional, Tuple, Set
from .base import logger, metrics
import time
import json
import uuid
import hashlib
from dataclasses import dataclass, field
from enum import Enum
import requests
from urllib.parse import urlparse, parse_qs

class CharacterSource(Enum):
    NOMI_AI = "nomi_ai"
    CHARACTER_AI = "character_ai"
    POE = "poe"
    REPLICA = "replica"
    CUSTOM_API = "custom_api"
    LOCAL_FILE = "local_file"

class CharacterCapability(Enum):
    CONVERSATION = "conversation"
    ROLEPLAY = "roleplay"
    ANALYSIS = "analysis"
    CREATIVE_WRITING = "creative_writing"
    TECHNICAL_ADVICE = "technical_advice"
    EMOTIONAL_SUPPORT = "emotional_support"
    LANGUAGE_LEARNING = "language_learning"
    STORYTELLING = "storytelling"
    PROBLEM_SOLVING = "problem_solving"
    HUMOR = "humor"

@dataclass
class CharacterProfile:
    """Represents an external AI character profile"""
    character_id: str
    name: str
    source: CharacterSource
    source_url: str
    description: str
    personality_traits: List[str] = field(default_factory=list)
    capabilities: List[CharacterCapability] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    avatar_url: Optional[str] = None
    creator: Optional[str] = None
    rating: Optional[float] = None
    interaction_count: int = 0
    last_interaction: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

@dataclass
class CharacterInteraction:
    """Represents an interaction with a character"""
    interaction_id: str
    character_id: str
    user_input: str
    character_response: str
    timestamp: float
    response_time: float
    quality_score: Optional[float] = None
    user_feedback: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CharacterIntegration:
    """Integration configuration for external AI characters"""
    integration_id: str
    character: CharacterProfile
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    rate_limit: int = 60  # requests per minute
    timeout: int = 30  # seconds
    retry_attempts: int = 3
    enabled: bool = True
    last_request: Optional[float] = None
    request_count: int = 0
    error_count: int = 0

class CharacterIntegrationManager:
    """Manages integration with external AI character platforms"""

    def __init__(self):
        self.characters: Dict[str, CharacterProfile] = {}
        self.integrations: Dict[str, CharacterIntegration] = {}
        self.interactions: List[CharacterInteraction] = []
        self.session_tokens: Dict[str, Dict[str, Any]] = {}

        # Rate limiting
        self.rate_limits: Dict[str, List[float]] = {}

        # Initialize with supported platforms
        self._initialize_platform_integrations()

    def _initialize_platform_integrations(self):
        """Initialize integrations for supported AI character platforms"""

        # Nomi.ai integration template
        nomi_integration = CharacterIntegration(
            integration_id="nomi_ai_default",
            character=CharacterProfile(
                character_id="nomi_ai_template",
                name="Nomi.ai Character",
                source=CharacterSource.NOMI_AI,
                source_url="https://beta.nomi.ai",
                description="AI character from Nomi.ai platform",
                capabilities=[
                    CharacterCapability.CONVERSATION,
                    CharacterCapability.ROLEPLAY,
                    CharacterCapability.EMOTIONAL_SUPPORT
                ],
                languages=["en"],
                tags=["AI", "companion", "conversation"]
            ),
            api_endpoint="https://api.nomi.ai/v1",
            headers={
                "User-Agent": "Kilo-Swarm-Integration/1.0",
                "Accept": "application/json"
            }
        )

        # Character.AI integration template
        character_ai_integration = CharacterIntegration(
            integration_id="character_ai_default",
            character=CharacterProfile(
                character_id="character_ai_template",
                name="Character.AI Character",
                source=CharacterSource.CHARACTER_AI,
                source_url="https://character.ai",
                description="AI character from Character.AI platform",
                capabilities=[
                    CharacterCapability.CONVERSATION,
                    CharacterCapability.ROLEPLAY,
                    CharacterCapability.STORYTELLING
                ],
                languages=["en"],
                tags=["AI", "character", "roleplay"]
            ),
            api_endpoint="https://api.character.ai/v1",
            headers={
                "User-Agent": "Kilo-Swarm-Integration/1.0",
                "Accept": "application/json"
            }
        )

        self.integrations["nomi_ai"] = nomi_integration
        self.integrations["character_ai"] = character_ai_integration

    def add_character_from_url(self, url: str, api_key: Optional[str] = None) -> Optional[str]:
        """Add a character from a URL (e.g., Nomi.ai profile URL)"""

        try:
            parsed_url = urlparse(url)
            character_id = None

            # Extract character ID from URL
            if "nomi.ai" in parsed_url.netloc:
                # Handle Nomi.ai URLs like: https://beta.nomi.ai/profile/nomis/343798146
                path_parts = parsed_url.path.split('/')
                if len(path_parts) >= 4 and path_parts[2] == "nomis":
                    character_id = path_parts[3]

                if character_id:
                    return self._add_nomi_character(character_id, url, api_key)

            elif "character.ai" in parsed_url.netloc:
                # Handle Character.AI URLs
                query_params = parse_qs(parsed_url.query)
                character_id = query_params.get('char', [None])[0]

                if character_id:
                    return self._add_character_ai_character(character_id, url, api_key)

            # Generic URL-based character addition
            return self._add_generic_character(url, api_key)

        except Exception as e:
            logger.log("ERROR", "CharacterIntegrationManager", f"Failed to add character from URL {url}: {str(e)}")
            return None

    def _add_nomi_character(self, character_id: str, url: str, api_key: Optional[str] = None) -> Optional[str]:
        """Add a Nomi.ai character"""

        integration_id = f"nomi_ai_{character_id}"

        # Create character profile
        character = CharacterProfile(
            character_id=f"nomi_{character_id}",
            name=f"Nomi Character {character_id}",
            source=CharacterSource.NOMI_AI,
            source_url=url,
            description=f"AI character from Nomi.ai platform (ID: {character_id})",
            capabilities=[
                CharacterCapability.CONVERSATION,
                CharacterCapability.ROLEPLAY,
                CharacterCapability.EMOTIONAL_SUPPORT,
                CharacterCapability.HUMOR
            ],
            languages=["en"],  # Default, can be updated
            tags=["nomi.ai", "AI", "companion", "character"],
            metadata={
                "platform_id": character_id,
                "platform": "nomi.ai",
                "profile_url": url
            }
        )

        # Create integration
        integration = CharacterIntegration(
            integration_id=integration_id,
            character=character,
            api_endpoint=f"https://api.nomi.ai/v1/characters/{character_id}",
            api_key=api_key,
            headers={
                "Authorization": f"Bearer {api_key}" if api_key else "",
                "User-Agent": "Kilo-Swarm-Integration/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            rate_limit=30,  # Nomi.ai rate limits
            timeout=60  # Longer timeout for character responses
        )

        self.characters[character.character_id] = character
        self.integrations[integration_id] = integration

        logger.log("INFO", "CharacterIntegrationManager", f"Added Nomi.ai character: {character.name}")
        return character.character_id

    def _add_character_ai_character(self, character_id: str, url: str, api_key: Optional[str] = None) -> Optional[str]:
        """Add a Character.AI character"""

        integration_id = f"character_ai_{character_id}"

        character = CharacterProfile(
            character_id=f"character_ai_{character_id}",
            name=f"Character.AI {character_id}",
            source=CharacterSource.CHARACTER_AI,
            source_url=url,
            description=f"AI character from Character.AI platform (ID: {character_id})",
            capabilities=[
                CharacterCapability.CONVERSATION,
                CharacterCapability.ROLEPLAY,
                CharacterCapability.STORYTELLING,
                CharacterCapability.CREATIVE_WRITING
            ],
            languages=["en"],
            tags=["character.ai", "AI", "character", "roleplay"],
            metadata={
                "platform_id": character_id,
                "platform": "character.ai",
                "profile_url": url
            }
        )

        integration = CharacterIntegration(
            integration_id=integration_id,
            character=character,
            api_endpoint="https://api.character.ai/v1/chat",
            api_key=api_key,
            headers={
                "Authorization": f"Bearer {api_key}" if api_key else "",
                "User-Agent": "Kilo-Swarm-Integration/1.0",
                "Accept": "application/json"
            },
            rate_limit=20,  # Character.AI rate limits
            timeout=45
        )

        self.characters[character.character_id] = character
        self.integrations[integration_id] = integration

        logger.log("INFO", "CharacterIntegrationManager", f"Added Character.AI character: {character.name}")
        return character.character_id

    def _add_generic_character(self, url: str, api_key: Optional[str] = None) -> Optional[str]:
        """Add a generic character from URL"""

        character_id = f"generic_{hashlib.md5(url.encode()).hexdigest()[:8]}"

        character = CharacterProfile(
            character_id=character_id,
            name=f"External Character {character_id[:8]}",
            source=CharacterSource.CUSTOM_API,
            source_url=url,
            description=f"External AI character from {url}",
            capabilities=[
                CharacterCapability.CONVERSATION,
                CharacterCapability.ANALYSIS
            ],
            languages=["en"],
            tags=["external", "API", "character"],
            metadata={
                "source_url": url,
                "api_key_provided": api_key is not None
            }
        )

        integration = CharacterIntegration(
            integration_id=f"generic_{character_id}",
            character=character,
            api_endpoint=url,
            api_key=api_key,
            headers={
                "Authorization": f"Bearer {api_key}" if api_key else "",
                "User-Agent": "Kilo-Swarm-Integration/1.0",
                "Accept": "application/json"
            },
            rate_limit=10,  # Conservative default
            timeout=30
        )

        self.characters[character.character_id] = character
        self.integrations[integration.integration_id] = integration

        logger.log("INFO", "CharacterIntegrationManager", f"Added generic character: {character.name}")
        return character.character_id

    def interact_with_character(self, character_id: str, user_input: str,
                              context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Interact with a character"""

        if character_id not in self.characters:
            logger.log("ERROR", "CharacterIntegrationManager", f"Character {character_id} not found")
            return None

        character = self.characters[character_id]
        integration = None

        # Find the integration for this character
        for integ in self.integrations.values():
            if integ.character.character_id == character_id:
                integration = integ
                break

        if not integration or not integration.enabled:
            logger.log("ERROR", "CharacterIntegrationManager", f"No enabled integration found for character {character_id}")
            return None

        # Check rate limits
        if not self._check_rate_limit(integration.integration_id, integration.rate_limit):
            logger.log("WARNING", "CharacterIntegrationManager", f"Rate limit exceeded for {character_id}")
            return "Rate limit exceeded. Please try again later."

        try:
            start_time = time.time()

            # Make API call to character platform
            response = self._call_character_api(integration, user_input, context)

            response_time = time.time() - start_time

            # Record interaction
            interaction = CharacterInteraction(
                interaction_id=str(uuid.uuid4()),
                character_id=character_id,
                user_input=user_input,
                character_response=response,
                timestamp=time.time(),
                response_time=response_time,
                context=context or {}
            )

            self.interactions.append(interaction)

            # Update character stats
            character.interaction_count += 1
            character.last_interaction = time.time()

            # Update integration stats
            integration.last_request = time.time()
            integration.request_count += 1

            # Record rate limit timestamp
            self._record_rate_limit_request(integration.integration_id)

            logger.log("INFO", "CharacterIntegrationManager", f"Interaction with {character_id} completed in {response_time:.2f}s")

            return response

        except Exception as e:
            logger.log("ERROR", "CharacterIntegrationManager", f"Interaction with {character_id} failed: {str(e)}")

            # Update error count
            integration.error_count += 1

            return f"Sorry, I encountered an error while communicating with {character.name}. Please try again."

    def _call_character_api(self, integration: CharacterIntegration, user_input: str,
                          context: Optional[Dict[str, Any]] = None) -> str:
        """Make API call to character platform"""

        payload = {
            "message": user_input,
            "context": context or {},
            "timestamp": time.time()
        }

        # Customize payload based on platform
        if integration.character.source == CharacterSource.NOMI_AI:
            payload = self._format_nomi_payload(integration, user_input, context)
        elif integration.character.source == CharacterSource.CHARACTER_AI:
            payload = self._format_character_ai_payload(integration, user_input, context)

        headers = integration.headers.copy()
        if integration.api_key:
            headers["Authorization"] = f"Bearer {integration.api_key}"

        response = requests.post(
            integration.api_endpoint,
            json=payload,
            headers=headers,
            timeout=integration.timeout
        )

        response.raise_for_status()
        response_data = response.json()

        # Extract response based on platform
        if integration.character.source == CharacterSource.NOMI_AI:
            return self._parse_nomi_response(response_data)
        elif integration.character.source == CharacterSource.CHARACTER_AI:
            return self._parse_character_ai_response(response_data)
        else:
            return response_data.get("response", response_data.get("message", "No response"))

    def _format_nomi_payload(self, integration: CharacterIntegration, user_input: str,
                           context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format payload for Nomi.ai API"""
        return {
            "character_id": integration.character.metadata.get("platform_id"),
            "message": user_input,
            "context": context or {},
            "session_id": self.session_tokens.get(integration.integration_id, {}).get("session_id")
        }

    def _format_character_ai_payload(self, integration: CharacterIntegration, user_input: str,
                                   context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format payload for Character.AI API"""
        return {
            "character_id": integration.character.metadata.get("platform_id"),
            "message": user_input,
            "context": context or {},
            "session_token": self.session_tokens.get(integration.integration_id, {}).get("token")
        }

    def _parse_nomi_response(self, response_data: Dict[str, Any]) -> str:
        """Parse response from Nomi.ai API"""
        return response_data.get("response", response_data.get("message", "No response from Nomi.ai"))

    def _parse_character_ai_response(self, response_data: Dict[str, Any]) -> str:
        """Parse response from Character.AI API"""
        return response_data.get("response", response_data.get("replies", [{}])[0].get("text", "No response from Character.AI"))

    def _check_rate_limit(self, integration_id: str, rate_limit: int) -> bool:
        """Check if request is within rate limits"""
        now = time.time()
        window_start = now - 60  # 1 minute window

        if integration_id not in self.rate_limits:
            self.rate_limits[integration_id] = []

        # Remove old requests outside the window
        self.rate_limits[integration_id] = [
            req_time for req_time in self.rate_limits[integration_id]
            if req_time > window_start
        ]

        # Check if under limit
        return len(self.rate_limits[integration_id]) < rate_limit

    def _record_rate_limit_request(self, integration_id: str):
        """Record a request for rate limiting"""
        if integration_id not in self.rate_limits:
            self.rate_limits[integration_id] = []

        self.rate_limits[integration_id].append(time.time())

    def get_character_stats(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a character"""

        if character_id not in self.characters:
            return None

        character = self.characters[character_id]

        # Calculate interaction stats
        character_interactions = [i for i in self.interactions if i.character_id == character_id]

        if not character_interactions:
            avg_response_time = 0
            total_interactions = 0
        else:
            avg_response_time = sum(i.response_time for i in character_interactions) / len(character_interactions)
            total_interactions = len(character_interactions)

        return {
            "character_id": character.character_id,
            "name": character.name,
            "source": character.source.value,
            "total_interactions": character.interaction_count,
            "recent_interactions": total_interactions,
            "average_response_time": avg_response_time,
            "last_interaction": character.last_interaction,
            "capabilities": [cap.value for cap in character.capabilities],
            "rating": character.rating,
            "tags": character.tags
        }

    def get_integration_health(self) -> Dict[str, Any]:
        """Get health status of all integrations"""

        health_status = {}

        for integration_id, integration in self.integrations.items():
            recent_requests = self.rate_limits.get(integration_id, [])
            now = time.time()
            recent_window = now - 300  # Last 5 minutes

            recent_request_count = len([t for t in recent_requests if t > recent_window])

            health_status[integration_id] = {
                "character_id": integration.character.character_id,
                "character_name": integration.character.name,
                "enabled": integration.enabled,
                "total_requests": integration.request_count,
                "error_count": integration.error_count,
                "recent_requests": recent_request_count,
                "rate_limit": integration.rate_limit,
                "last_request": integration.last_request,
                "error_rate": (integration.error_count / max(1, integration.request_count)) * 100 if integration.request_count > 0 else 0
            }

        return health_status

    def list_characters(self) -> List[Dict[str, Any]]:
        """List all available characters"""

        return [{
            "character_id": char.character_id,
            "name": char.name,
            "source": char.source.value,
            "description": char.description,
            "capabilities": [cap.value for cap in char.capabilities],
            "languages": char.languages,
            "tags": char.tags,
            "rating": char.rating,
            "interaction_count": char.interaction_count,
            "last_interaction": char.last_interaction
        } for char in self.characters.values()]

    def update_character_profile(self, character_id: str, updates: Dict[str, Any]):
        """Update character profile information"""

        if character_id not in self.characters:
            return False

        character = self.characters[character_id]

        # Update allowed fields
        allowed_fields = ['name', 'description', 'personality_traits', 'capabilities',
                         'languages', 'tags', 'avatar_url', 'rating']

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(character, field, value)

        character.updated_at = time.time()

        logger.log("INFO", "CharacterIntegrationManager", f"Updated character profile: {character_id}")
        return True

# Global character integration manager
character_manager = CharacterIntegrationManager()

# Integration functions
def add_character_from_url(url: str, api_key: Optional[str] = None) -> Optional[str]:
    """Add a character from a URL"""
    return character_manager.add_character_from_url(url, api_key)

def interact_with_character(character_id: str, user_input: str,
                          context: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Interact with a character"""
    return character_manager.interact_with_character(character_id, user_input, context)

def get_character_stats(character_id: str) -> Optional[Dict[str, Any]]:
    """Get character statistics"""
    return character_manager.get_character_stats(character_id)

def list_available_characters() -> List[Dict[str, Any]]:
    """List all available characters"""
    return character_manager.list_characters()

def get_integration_health() -> Dict[str, Any]:
    """Get integration health status"""
    return character_manager.get_integration_health()