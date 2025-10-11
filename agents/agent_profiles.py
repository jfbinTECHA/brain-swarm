from typing import Dict, List, Any, Optional
from core.base import logger
import time
import json
import os

# Behavior Profile Definitions
BEHAVIOR_PROFILES = {
    # Creativity Profiles
    "creative": {
        "name": "Creative",
        "description": "Emphasizes innovative solutions and novel approaches",
        "parameters": {
            "creativity_weight": 0.8,
            "precision_weight": 0.2,
            "caution_weight": 0.3,
            "exploration_bias": 0.7,
            "conformity_bias": 0.1,
            "risk_tolerance": 0.8,
            "divergence_factor": 0.9
        },
        "traits": ["innovative", "experimental", "unconventional", "brainstorming"]
    },

    "balanced_creative": {
        "name": "Balanced Creative",
        "description": "Creative with practical considerations",
        "parameters": {
            "creativity_weight": 0.6,
            "precision_weight": 0.4,
            "caution_weight": 0.5,
            "exploration_bias": 0.5,
            "conformity_bias": 0.3,
            "risk_tolerance": 0.6,
            "divergence_factor": 0.6
        },
        "traits": ["innovative", "practical", "balanced", "versatile"]
    },

    # Precision Profiles
    "precise": {
        "name": "Precise",
        "description": "Emphasizes accuracy and attention to detail",
        "parameters": {
            "creativity_weight": 0.2,
            "precision_weight": 0.9,
            "caution_weight": 0.7,
            "exploration_bias": 0.2,
            "conformity_bias": 0.8,
            "risk_tolerance": 0.2,
            "divergence_factor": 0.1
        },
        "traits": ["accurate", "detailed", "methodical", "thorough"]
    },

    "analytical": {
        "name": "Analytical",
        "description": "Data-driven and systematic approach",
        "parameters": {
            "creativity_weight": 0.3,
            "precision_weight": 0.8,
            "caution_weight": 0.6,
            "exploration_bias": 0.3,
            "conformity_bias": 0.7,
            "risk_tolerance": 0.3,
            "divergence_factor": 0.2
        },
        "traits": ["systematic", "data-driven", "logical", "structured"]
    },

    # Caution Profiles
    "cautious": {
        "name": "Cautious",
        "description": "Prioritizes safety and risk mitigation",
        "parameters": {
            "creativity_weight": 0.3,
            "precision_weight": 0.6,
            "caution_weight": 0.9,
            "exploration_bias": 0.2,
            "conformity_bias": 0.6,
            "risk_tolerance": 0.1,
            "divergence_factor": 0.2
        },
        "traits": ["safe", "conservative", "risk-averse", "careful"]
    },

    "conservative": {
        "name": "Conservative",
        "description": "Traditional and proven methods",
        "parameters": {
            "creativity_weight": 0.2,
            "precision_weight": 0.7,
            "caution_weight": 0.8,
            "exploration_bias": 0.1,
            "conformity_bias": 0.9,
            "risk_tolerance": 0.2,
            "divergence_factor": 0.1
        },
        "traits": ["traditional", "proven", "reliable", "stable"]
    },

    # Balanced Profiles
    "balanced": {
        "name": "Balanced",
        "description": "Well-rounded performance across all dimensions",
        "parameters": {
            "creativity_weight": 0.5,
            "precision_weight": 0.5,
            "caution_weight": 0.5,
            "exploration_bias": 0.5,
            "conformity_bias": 0.5,
            "risk_tolerance": 0.5,
            "divergence_factor": 0.5
        },
        "traits": ["balanced", "versatile", "adaptable", "moderate"]
    },

    "adaptive": {
        "name": "Adaptive",
        "description": "Adjusts behavior based on context and feedback",
        "parameters": {
            "creativity_weight": 0.6,
            "precision_weight": 0.6,
            "caution_weight": 0.4,
            "exploration_bias": 0.6,
            "conformity_bias": 0.4,
            "risk_tolerance": 0.5,
            "divergence_factor": 0.6
        },
        "traits": ["adaptive", "flexible", "responsive", "learning"]
    },

    # Specialized Profiles
    "speed_optimized": {
        "name": "Speed Optimized",
        "description": "Prioritizes speed over perfection",
        "parameters": {
            "creativity_weight": 0.4,
            "precision_weight": 0.3,
            "caution_weight": 0.2,
            "exploration_bias": 0.6,
            "conformity_bias": 0.4,
            "risk_tolerance": 0.7,
            "divergence_factor": 0.4
        },
        "traits": ["fast", "efficient", "agile", "quick"]
    },

    "quality_focused": {
        "name": "Quality Focused",
        "description": "Emphasizes high-quality outputs",
        "parameters": {
            "creativity_weight": 0.5,
            "precision_weight": 0.9,
            "caution_weight": 0.8,
            "exploration_bias": 0.3,
            "conformity_bias": 0.7,
            "risk_tolerance": 0.2,
            "divergence_factor": 0.3
        },
        "traits": ["quality", "thorough", "meticulous", "excellent"]
    }
}

class AgentBehaviorProfile:
    """Manages agent behavior profiles and their application"""

    def __init__(self, profile_name: str = "balanced"):
        self.current_profile = profile_name
        self.parameters = BEHAVIOR_PROFILES.get(profile_name, BEHAVIOR_PROFILES["balanced"]).copy()
        self.custom_profiles = {}
        self.profile_history = []
        self.learning_enabled = True

        # Load saved custom profiles
        self.load_custom_profiles()

    def set_profile(self, profile_name: str) -> bool:
        """Set the current behavior profile"""
        if profile_name in BEHAVIOR_PROFILES or profile_name in self.custom_profiles:
            old_profile = self.current_profile
            self.current_profile = profile_name

            if profile_name in BEHAVIOR_PROFILES:
                self.parameters = BEHAVIOR_PROFILES[profile_name].copy()
            else:
                self.parameters = self.custom_profiles[profile_name].copy()

            # Record profile change
            self.profile_history.append({
                "timestamp": time.time(),
                "from_profile": old_profile,
                "to_profile": profile_name,
                "reason": "manual_change"
            })

            logger.log("INFO", "AgentBehaviorProfile", f"Switched to profile: {profile_name}")
            return True

        logger.log("WARNING", "AgentBehaviorProfile", f"Profile not found: {profile_name}")
        return False

    def create_custom_profile(self, name: str, base_profile: str, modifications: Dict[str, float]) -> bool:
        """Create a custom profile based on an existing one with modifications"""
        if base_profile not in BEHAVIOR_PROFILES:
            return False

        # Start with base profile
        custom_profile = BEHAVIOR_PROFILES[base_profile].copy()

        # Apply modifications
        for param, value in modifications.items():
            if param in custom_profile["parameters"]:
                # Ensure value stays within reasonable bounds
                custom_profile["parameters"][param] = max(0.0, min(1.0, value))

        # Update description
        custom_profile["name"] = name
        custom_profile["description"] = f"Custom profile based on {base_profile}"

        # Save custom profile
        self.custom_profiles[name] = custom_profile
        self.save_custom_profiles()

        logger.log("INFO", "AgentBehaviorProfile", f"Created custom profile: {name}")
        return True

    def adapt_profile(self, feedback: Dict[str, Any]) -> None:
        """Adapt profile based on performance feedback"""
        if not self.learning_enabled:
            return

        # Simple adaptation logic based on feedback
        adaptation_needed = False

        if feedback.get("task_success") == False:
            # If task failed, increase caution and precision
            if self.parameters["caution_weight"] < 0.8:
                self.parameters["caution_weight"] += 0.1
                adaptation_needed = True
            if self.parameters["precision_weight"] < 0.8:
                self.parameters["precision_weight"] += 0.1
                adaptation_needed = True

        elif feedback.get("task_quality", 0) < 0.6:
            # If quality is low, increase precision
            if self.parameters["precision_weight"] < 0.9:
                self.parameters["precision_weight"] += 0.1
                adaptation_needed = True

        elif feedback.get("task_time", 0) > feedback.get("expected_time", 60):
            # If task took too long, increase speed focus
            if self.parameters["exploration_bias"] > 0.3:
                self.parameters["exploration_bias"] -= 0.1
                adaptation_needed = True

        if adaptation_needed:
            logger.log("INFO", "AgentBehaviorProfile", f"Adapted profile based on feedback: {feedback}")

            # Record adaptation
            self.profile_history.append({
                "timestamp": time.time(),
                "adaptation": "automatic",
                "feedback": feedback,
                "new_parameters": self.parameters.copy()
            })

    def get_decision_weight(self, decision_type: str) -> float:
        """Get decision weight based on current profile and decision type"""
        weights = {
            "creative": self.parameters["creativity_weight"],
            "precise": self.parameters["precision_weight"],
            "cautious": self.parameters["caution_weight"],
            "exploratory": self.parameters["exploration_bias"],
            "conforming": self.parameters["conformity_bias"],
            "risky": self.parameters["risk_tolerance"],
            "divergent": self.parameters["divergence_factor"]
        }

        return weights.get(decision_type, 0.5)

    def should_take_risk(self, risk_level: float) -> bool:
        """Determine if agent should take a risk based on profile"""
        risk_threshold = 1.0 - self.parameters["risk_tolerance"]
        return risk_level <= risk_threshold

    def get_exploration_factor(self) -> float:
        """Get exploration factor for decision making"""
        return self.parameters["exploration_bias"]

    def get_conformity_factor(self) -> float:
        """Get conformity factor for decision making"""
        return self.parameters["conformity_bias"]

    def get_profile_info(self) -> Dict[str, Any]:
        """Get current profile information"""
        profile_data = self.parameters.copy()
        profile_data["current_profile"] = self.current_profile
        profile_data["traits"] = profile_data.get("traits", [])
        profile_data["learning_enabled"] = self.learning_enabled
        return profile_data

    def save_custom_profiles(self):
        """Save custom profiles to file"""
        try:
            with open("custom_agent_profiles.json", "w") as f:
                json.dump(self.custom_profiles, f, indent=2)
        except Exception as e:
            logger.log("ERROR", "AgentBehaviorProfile", f"Failed to save custom profiles: {e}")

    def load_custom_profiles(self):
        """Load custom profiles from file"""
        try:
            if os.path.exists("custom_agent_profiles.json"):
                with open("custom_agent_profiles.json", "r") as f:
                    self.custom_profiles = json.load(f)
        except Exception as e:
            logger.log("ERROR", "AgentBehaviorProfile", f"Failed to load custom profiles: {e}")
            self.custom_profiles = {}

    def get_available_profiles(self) -> List[str]:
        """Get list of all available profiles"""
        return list(BEHAVIOR_PROFILES.keys()) + list(self.custom_profiles.keys())

    def get_profile_details(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific profile"""
        if profile_name in BEHAVIOR_PROFILES:
            return BEHAVIOR_PROFILES[profile_name]
        elif profile_name in self.custom_profiles:
            return self.custom_profiles[profile_name]
        return None

# Global profile manager instance
profile_manager = AgentBehaviorProfile()

# Utility functions for behavior modification
def apply_behavior_modifier(base_value: float, behavior_type: str, profile: AgentBehaviorProfile) -> float:
    """Apply behavior modification to a base value"""
    modifier = profile.get_decision_weight(behavior_type)

    # Apply modification based on behavior type
    if behavior_type == "creative":
        # Creative agents add more variation
        return base_value * (0.8 + modifier * 0.4)
    elif behavior_type == "precise":
        # Precise agents reduce variation
        return base_value * (0.9 + modifier * 0.2)
    elif behavior_type == "cautious":
        # Cautious agents are more conservative
        return base_value * (0.7 + modifier * 0.3)
    else:
        return base_value

def get_behavior_description(profile: AgentBehaviorProfile) -> str:
    """Get a human-readable description of the current behavior profile"""
    profile_info = profile.get_profile_info()
    traits = profile_info.get("traits", [])

    if not traits:
        return f"Custom profile with balanced characteristics"

    # Create descriptive text
    trait_descriptions = {
        "innovative": "innovative thinking",
        "experimental": "experimental approaches",
        "accurate": "high accuracy",
        "detailed": "attention to detail",
        "safe": "risk mitigation",
        "conservative": "proven methods",
        "balanced": "well-rounded approach",
        "fast": "speed optimization",
        "quality": "quality focus"
    }

    descriptions = [trait_descriptions.get(trait, trait) for trait in traits[:3]]
    return f"Profile emphasizing {', '.join(descriptions)}"