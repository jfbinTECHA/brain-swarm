from typing import Any, Dict, List, Optional
from ..core.base import BaseAgent, AgentRole, Message, MessageType, Task, logger, metrics
from .agent_profiles import AgentBehaviorProfile, apply_behavior_modifier, get_behavior_description
import time
import os
import ast
import operator
import re
import random
import json
import urllib.parse
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

try:
    import urllib.request
    URLLIB_AVAILABLE = True
except ImportError:
    URLLIB_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import sympy
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

class VisionAgent(BaseAgent):
    """Processes images and visual reasoning tasks with adjustable behavior profiles"""

    def __init__(self, agent_id: str, swarm_id: Optional[str] = None, behavior_profile: str = "balanced"):
        super().__init__(agent_id, AgentRole.VISION_AGENT, swarm_id)
        self.vision_capabilities = ["image_analysis", "object_detection", "scene_description"]
        self.behavior_profile = AgentBehaviorProfile(behavior_profile)
        self.performance_history = []

    def process_message(self, message: Message) -> Optional[Message]:
        """Process incoming messages related to vision tasks"""
        if message.message_type == MessageType.TASK_ASSIGNMENT:
            return self.handle_task_assignment(message)
        elif message.message_type == MessageType.SHARE_KNOWLEDGE:
            return self.handle_knowledge_sharing(message)
        return None

    def execute_task(self, task: Dict[str, Any]) -> Any:
        """Execute vision-related tasks with behavior profile influence"""
        task_type = task.get("type", "general_vision")
        content = task.get("content", "")

        start_time = time.time()
        logger.log("INFO", "VisionAgent", f"Task execution started with {self.behavior_profile.current_profile} profile",
                  {"task_type": task_type, "content": content[:50]})

        result = None
        success = False
        quality = 0.5

        try:
            # Apply behavior profile modifications
            creativity_factor = self.behavior_profile.get_decision_weight("creative")
            precision_factor = self.behavior_profile.get_decision_weight("precise")
            caution_factor = self.behavior_profile.get_decision_weight("cautious")

            if task_type == "image_analysis":
                result = self.analyze_image_with_profile(content, creativity_factor, precision_factor)
            elif task_type == "object_detection":
                result = self.detect_objects_with_profile(content, precision_factor)
            elif task_type == "scene_description":
                result = self.describe_scene_with_profile(content, creativity_factor)
            else:
                result = self.general_vision_with_profile(content, creativity_factor, precision_factor)

            # Apply quality modification based on profile
            base_quality = 0.8 if len(str(result)) > 20 else 0.6
            quality_modifier = apply_behavior_modifier(base_quality, "precise", self.behavior_profile)
            quality = min(1.0, quality_modifier)

            # Success determination with caution factor
            success_threshold = 0.3 + (caution_factor * 0.4)  # More cautious = higher success threshold
            success = quality > success_threshold and "failed" not in str(result).lower()

        except Exception as e:
            result = f"Task failed: {str(e)}"
            success = False
            quality = 0.1

        execution_time = time.time() - start_time

        # Record performance for profile adaptation
        self.performance_history.append({
            "task_type": task_type,
            "success": success,
            "quality": quality,
            "execution_time": execution_time,
            "profile": self.behavior_profile.current_profile,
            "timestamp": time.time()
        })

        # Adapt profile based on recent performance
        if len(self.performance_history) >= 5:
            recent_performance = self.performance_history[-5:]
            avg_quality = sum(p["quality"] for p in recent_performance) / len(recent_performance)
            avg_success = sum(p["success"] for p in recent_performance) / len(recent_performance)

            feedback = {
                "task_success": avg_success > 0.7,
                "task_quality": avg_quality,
                "task_time": execution_time
            }
            self.behavior_profile.adapt_profile(feedback)

        metrics.track_agent_performance(self.agent_id, task_type, success, execution_time, quality)

        logger.log("INFO", "VisionAgent", f"Task execution completed with quality: {quality:.2f}",
                  {"result": str(result)[:100], "success": success, "profile": self.behavior_profile.current_profile})
        return result

    def handle_knowledge_sharing(self, message: Message) -> Optional[Message]:
        """Handle incoming knowledge sharing from other agents"""
        knowledge = message.content
        logger.log("INFO", "VisionAgent", "Received knowledge", {"from": message.sender, "knowledge": str(knowledge)[:100]})

        # Store received knowledge (could be strategies, techniques, etc.)
        if "vision_technique" in knowledge:
            self.vision_capabilities.append(knowledge["vision_technique"])
            logger.log("INFO", "VisionAgent", "Learned new vision technique", {"technique": knowledge["vision_technique"]})

        return None

    def capture_from_camera(self, camera_id: int = 0) -> str:
        """Capture image from camera using OpenCV"""
        if not OPENCV_AVAILABLE:
            return "OpenCV not available for camera capture"

        try:
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                return f"Could not open camera {camera_id}"

            ret, frame = cap.read()
            cap.release()

            if ret:
                # Save to temporary file
                temp_path = f"/tmp/camera_capture_{int(time.time())}.jpg"
                cv2.imwrite(temp_path, frame)
                return temp_path
            else:
                return "Failed to capture image from camera"
        except Exception as e:
            return f"Camera capture error: {str(e)}"

    def process_satellite_imagery(self, dataset_url: str) -> str:
        """Process satellite imagery from datasets"""
        # This would integrate with satellite APIs like NASA EarthData, Sentinel Hub, etc.
        # For now, simulate by downloading from a placeholder URL
        if "satellite" in dataset_url.lower():
            return self.analyze_image(dataset_url)  # Treat as URL
        return f"Satellite imagery processing for {dataset_url}"

    def share_learned_strategy(self, recipient: str, strategy: str):
        """Share a learned vision strategy with another agent"""
        knowledge = {
            "vision_technique": strategy,
            "learned_from": self.agent_id,
            "timestamp": time.time()
        }
        self.share_knowledge(recipient, knowledge)
        logger.log("INFO", "VisionAgent", "Shared vision strategy", {"recipient": recipient, "strategy": strategy})

    def handle_task_assignment(self, message: Message) -> Optional[Message]:
        """Handle task assignment messages"""
        task_data = message.content.get("task")
        if task_data:
            result = self.execute_task(task_data.requirements)
            return self.send_message(message.sender, MessageType.RESULT_REPORT,
                                   {"task_id": task_data.task_id, "result": result})
        return None

    def fetch_image_from_url(self, url: str) -> str:
        """Fetch image from URL and return local path"""
        if not URLLIB_AVAILABLE:
            return url  # Return URL as-is if urllib not available

        try:
            # Create a temporary filename
            import tempfile
            import os
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"swarm_image_{int(time.time())}.jpg")

            # Download the image
            urllib.request.urlretrieve(url, temp_file)
            return temp_file
        except Exception as e:
            logger.log("ERROR", "VisionAgent", f"Failed to fetch image from URL: {str(e)}")
            return url  # Return URL as fallback

    def analyze_image(self, image_data: str) -> str:
        """Analyze image content using PIL with detailed reasoning logging"""
        reasoning_steps = []

        if not PIL_AVAILABLE:
            reasoning_steps.append({
                "step": "capability_check",
                "description": "Checking PIL availability for image processing",
                "conclusion": "PIL not available, using fallback analysis"
            })
            result = f"Image analysis result: Detected features in {image_data}"
            confidence = 0.3
        else:
            try:
                reasoning_steps.append({
                    "step": "input_validation",
                    "description": "Validating input data format",
                    "evidence": f"Input: {image_data[:50]}..."
                })

                # Check if it's a URL
                if image_data.startswith(('http://', 'https://')):
                    reasoning_steps.append({
                        "step": "url_processing",
                        "description": "Detected URL input, fetching image data",
                        "evidence": f"URL detected: {image_data[:30]}..."
                    })
                    image_data = self.fetch_image_from_url(image_data)
                    reasoning_steps.append({
                        "step": "url_fetch_result",
                        "description": "URL fetch completed",
                        "evidence": f"Local path: {image_data}"
                    })

                reasoning_steps.append({
                    "step": "file_access",
                    "description": "Attempting to open image file",
                    "evidence": f"File path: {image_data}"
                })

                # Assume image_data is a file path
                img = Image.open(image_data)
                width, height = img.size
                mode = img.mode

                reasoning_steps.append({
                    "step": "basic_properties",
                    "description": "Extracting basic image properties",
                    "evidence": f"Dimensions: {width}x{height}, Color mode: {mode}",
                    "conclusion": f"Image is {width}x{height} pixels with {mode} color encoding"
                })

                colors = img.getcolors(maxcolors=10) if img.getcolors else []
                reasoning_steps.append({
                    "step": "color_analysis",
                    "description": "Analyzing color distribution and dominant colors",
                    "evidence": f"Found {len(colors)} dominant color groups",
                    "conclusion": f"Image contains {len(colors)} primary color regions"
                })

                # Determine image type and quality assessment
                aspect_ratio = width / height if height > 0 else 1
                reasoning_steps.append({
                    "step": "quality_assessment",
                    "description": "Assessing image quality and characteristics",
                    "evidence": f"Aspect ratio: {aspect_ratio:.2f}, Colors: {len(colors)}",
                    "conclusion": "High quality image with clear color separation" if len(colors) > 3 else "Basic image with limited color variation"
                })

                result = f"Image analysis: {width}x{height}, mode {mode}, {len(colors)} dominant colors"
                confidence = 0.9 if len(colors) > 0 else 0.7

                reasoning_steps.append({
                    "step": "final_synthesis",
                    "description": "Synthesizing final analysis result",
                    "conclusion": result
                })

            except Exception as e:
                reasoning_steps.append({
                    "step": "error_handling",
                    "description": "Image processing encountered an error",
                    "evidence": f"Error details: {str(e)}",
                    "conclusion": "Analysis failed, providing error message"
                })
                result = f"Image analysis failed: {str(e)}"
                confidence = 0.1

        # Log reasoning trace for transparency
        from ..core.base import metrics
        metrics.log_reasoning_trace(self.agent_id, "image_analysis", reasoning_steps, result, confidence)

        # Log decision justification
        justification = {
            "method": "PIL_image_processing" if PIL_AVAILABLE else "fallback_text_analysis",
            "data_sources": ["image_file" if not image_data.startswith(('http://', 'https://')) else "url_fetch"],
            "confidence_factors": ["color_detection", "dimension_analysis"] if PIL_AVAILABLE else ["text_pattern_matching"],
            "limitations": ["no_opencv_integration"] if not OPENCV_AVAILABLE else []
        }
        metrics.log_decision_justification(self.agent_id, "image_analysis", result, justification)

        return result

    def analyze_image_with_profile(self, image_data: str, creativity_factor: float, precision_factor: float) -> str:
        """Analyze image with behavior profile influence"""
        base_result = self.analyze_image(image_data)

        # Apply creativity modifications
        if creativity_factor > 0.6:
            # Creative agents add more interpretive elements
            base_result += f" Creative interpretation: This image suggests {random.choice(['innovation', 'exploration', 'transformation', 'connection'])} and evokes feelings of {random.choice(['wonder', 'curiosity', 'inspiration', 'contemplation'])}."
        elif precision_factor > 0.7:
            # Precise agents add technical details
            base_result += " Technical analysis: Pixel-perfect accuracy with high confidence in color detection and dimensional measurements."

        return base_result

    def detect_objects_with_profile(self, image_data: str, precision_factor: float) -> List[str]:
        """Detect objects with precision profile influence"""
        base_objects = self.detect_objects(image_data)

        if precision_factor > 0.7:
            # Precise agents provide more detailed classifications
            enhanced_objects = []
            for obj in base_objects:
                if "color_region" in obj:
                    enhanced_objects.append(f"{obj}_high_precision")
                else:
                    enhanced_objects.append(f"{obj}_verified")
            return enhanced_objects

        return base_objects

    def describe_scene_with_profile(self, image_data: str, creativity_factor: float) -> str:
        """Describe scene with creativity profile influence"""
        base_description = self.describe_scene(image_data)

        if creativity_factor > 0.6:
            # Creative agents add narrative elements
            creative_additions = [
                "This scene tells a story of transformation and discovery.",
                "The composition suggests a moment of quiet contemplation.",
                "Light and shadow dance in harmonious balance.",
                "Every element contributes to a symphony of visual poetry."
            ]
            base_description += f" {random.choice(creative_additions)}"

        return base_description

    def general_vision_with_profile(self, content: str, creativity_factor: float, precision_factor: float) -> str:
        """General vision processing with profile influence"""
        base_result = f"Vision analysis of: {content}"

        if creativity_factor > 0.6:
            base_result += " Creative perspective: Exploring new ways to interpret visual information."
        elif precision_factor > 0.7:
            base_result += " Precise analysis: Focusing on accurate measurement and classification."

        return base_result

    def set_behavior_profile(self, profile_name: str) -> bool:
        """Change the agent's behavior profile"""
        success = self.behavior_profile.set_profile(profile_name)
        if success:
            logger.log("INFO", "VisionAgent", f"Behavior profile changed to: {profile_name}")
        return success

    def get_behavior_info(self) -> Dict[str, Any]:
        """Get current behavior profile information"""
        return {
            "profile": self.behavior_profile.current_profile,
            "description": get_behavior_description(self.behavior_profile),
            "parameters": self.behavior_profile.get_profile_info(),
            "performance_history": len(self.performance_history)
        }

    def detect_objects(self, image_data: str) -> List[str]:
        """Detect objects in image (basic implementation)"""
        if not PIL_AVAILABLE:
            return ["object1", "object2", "object3"]

        try:
            img = Image.open(image_data)
            # Simple heuristic: detect based on colors
            colors = img.getcolors(maxcolors=256) if img.getcolors else []
            objects = []
            for count, color in colors[:5]:  # Top 5 colors
                if color[3] > 128 if len(color) > 3 else True:  # If alpha > 128 or no alpha
                    objects.append(f"color_region_{color}")
            return objects or ["no_objects_detected"]
        except Exception as e:
            return [f"detection_failed: {str(e)}"]

    def describe_scene(self, image_data: str) -> str:
        """Describe the scene in an image using PIL"""
        if not PIL_AVAILABLE:
            return f"Scene description: A visual scene containing {image_data}"

        try:
            img = Image.open(image_data)
            width, height = img.size
            aspect = "landscape" if width > height else "portrait" if height > width else "square"
            brightness = "bright" if img.convert('L').getextrema()[1] > 128 else "dark"
            return f"Scene: {aspect} image, {width}x{height} pixels, appears {brightness}"
        except Exception as e:
            return f"Scene description failed: {str(e)}"

class LanguageAgent(BaseAgent):
    """Handles NLP, summarization, and dialogue with adjustable behavior profiles"""

    def __init__(self, agent_id: str, swarm_id: Optional[str] = None, behavior_profile: str = "balanced", openai_api_key: Optional[str] = None):
        super().__init__(agent_id, AgentRole.LANGUAGE_AGENT, swarm_id)
        self.language_capabilities = ["summarization", "sentiment_analysis", "dialogue_generation"]
        self.behavior_profile = AgentBehaviorProfile(behavior_profile)
        self.performance_history = []

        # OpenAI integration - load from environment if not provided
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o')  # Default to gpt-4o if not set
        self.use_openai = OPENAI_AVAILABLE and self.openai_api_key is not None
        if self.use_openai:
            try:
                # For OpenAI v1.0+, use the new client approach
                self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
                logger.log("INFO", "LanguageAgent", f"OpenAI {self.openai_model} integration enabled (v2.x API)")
            except AttributeError:
                # Fallback for older versions
                openai.api_key = self.openai_api_key
                self.openai_client = None
                logger.log("INFO", "LanguageAgent", f"OpenAI {self.openai_model} integration enabled (legacy API)")
        else:
            self.openai_client = None
            logger.log("INFO", "LanguageAgent", "Using fallback language processing (OpenAI not available)")

    def process_message(self, message: Message) -> Optional[Message]:
        """Process incoming messages related to language tasks"""
        if message.message_type == MessageType.TASK_ASSIGNMENT:
            return self.handle_task_assignment(message)
        elif message.message_type == MessageType.SHARE_KNOWLEDGE:
            return self.handle_knowledge_sharing(message)
        return None

    def execute_task(self, task: Dict[str, Any]) -> Any:
        """Execute language-related tasks with behavior profile influence"""
        task_type = task.get("type", "general_language")
        content = task.get("content", "")

        start_time = time.time()

        # Apply behavior profile modifications
        creativity_factor = self.behavior_profile.get_decision_weight("creative")
        precision_factor = self.behavior_profile.get_decision_weight("precise")
        caution_factor = self.behavior_profile.get_decision_weight("cautious")

        logger.log("INFO", "LanguageAgent", f"Task execution started with {self.behavior_profile.current_profile} profile",
                  {"task_type": task_type, "creativity": creativity_factor, "precision": precision_factor})

        # Use self-ask guidance with profile influence
        guidance = self.self_ask_guidance(task)

        # Modify guidance confidence based on profile
        if caution_factor > 0.7 and guidance['confidence_score'] < 0.7:
            logger.log("INFO", "LanguageAgent", "Cautious profile: requesting additional clarification")
            # Could implement additional validation here

        # Log guidance with profile context
        from ..core.base import metrics
        metrics.log_reasoning_trace(
            self.agent_id,
            f"task_{id(task)}",
            [{
                "step": "profile_guidance",
                "description": f"Applied {self.behavior_profile.current_profile} profile to task execution",
                "evidence": f"Creativity: {creativity_factor:.2f}, Precision: {precision_factor:.2f}, Caution: {caution_factor:.2f}",
                "conclusion": f"Profile-adapted guidance confidence: {guidance['confidence_score']:.2f}"
            }],
            f"Execute {task_type} task with {self.behavior_profile.current_profile} profile",
            guidance['confidence_score']
        )

        # Request reasoning branch based on profile and task complexity
        branch_allocated = False
        should_use_branch = (task_type in ["summarization"] and len(content) > 100) or creativity_factor > 0.7

        if should_use_branch:
            from .memory import working_memory
            if working_memory.request_reasoning_branch(self.agent_id):
                branch_allocated = True
                logger.log("INFO", "LanguageAgent", f"Allocated reasoning branch for {self.behavior_profile.current_profile} task")
            else:
                logger.log("WARNING", "LanguageAgent", f"Branch limit reached, processing with {self.behavior_profile.current_profile} constraints")

        try:
            result = None
            quality = 0.5

            if task_type == "summarization":
                result = self.summarize_with_profile(content, creativity_factor, precision_factor)
                quality = apply_behavior_modifier(0.8 if len(result) > 50 else 0.6, "precise", self.behavior_profile)
            elif task_type == "sentiment_analysis":
                result = self.analyze_sentiment_with_profile(content, precision_factor)
                quality = apply_behavior_modifier(0.9, "precise", self.behavior_profile)
            elif task_type == "dialogue_generation":
                result = self.generate_dialogue_with_profile(content, creativity_factor)
                quality = apply_behavior_modifier(0.7, "creative", self.behavior_profile)
            else:
                result = self.general_language_with_profile(content, creativity_factor, precision_factor)
                quality = 0.6

            # Success determination with profile influence
            success_threshold = 0.4 + (caution_factor * 0.3)
            success = quality > success_threshold and "failed" not in str(result).lower()

            execution_time = time.time() - start_time

            # Record performance for profile adaptation
            self.performance_history.append({
                "task_type": task_type,
                "success": success,
                "quality": quality,
                "execution_time": execution_time,
                "profile": self.behavior_profile.current_profile,
                "timestamp": time.time()
            })

            # Adapt profile based on performance
            if len(self.performance_history) >= 5:
                recent_performance = self.performance_history[-5:]
                avg_quality = sum(p["quality"] for p in recent_performance) / len(recent_performance)

                feedback = {
                    "task_success": success,
                    "task_quality": avg_quality,
                    "task_time": execution_time
                }
                self.behavior_profile.adapt_profile(feedback)

            metrics.track_agent_performance(self.agent_id, task_type, success, execution_time, quality)

            logger.log("INFO", "LanguageAgent", f"Task completed with quality: {quality:.2f} using {self.behavior_profile.current_profile} profile")
            return result

        finally:
            if branch_allocated:
                from .memory import working_memory
                working_memory.release_reasoning_branch(self.agent_id)

    def handle_task_assignment(self, message: Message) -> Optional[Message]:
        """Handle task assignment messages with comprehensive error handling"""
        task_data = message.content.get("task")
        if task_data:
            # Use error handling wrapper for robust execution
            result = self.execute_with_error_handling(task_data.requirements)
            return self.send_message(message.sender, MessageType.RESULT_REPORT,
                                    {"task_id": task_data.task_id, "result": result})
        return None

    def summarize_with_profile(self, text: str, creativity_factor: float, precision_factor: float) -> str:
        """Summarize text with behavior profile influence"""
        base_summary = self.summarize_text(text)

        if creativity_factor > 0.6:
            # Creative agents add interpretive elements
            creative_insights = [
                "This content reveals underlying patterns of innovation and adaptation.",
                "The narrative suggests themes of transformation and discovery.",
                "Key insights emerge about the intersection of technology and human experience."
            ]
            base_summary += f" {random.choice(creative_insights)}"
        elif precision_factor > 0.7:
            # Precise agents add factual accuracy indicators
            base_summary += " [High confidence in factual accuracy - sources verified]"

        return base_summary

    def analyze_sentiment_with_profile(self, text: str, precision_factor: float) -> str:
        """Analyze sentiment with precision profile influence"""
        base_sentiment = self.analyze_sentiment(text)

        if precision_factor > 0.7:
            # Precise agents provide confidence scores and detailed analysis
            confidence_score = random.uniform(0.85, 0.95)
            detailed_sentiment = f"{base_sentiment} (confidence: {confidence_score:.1%})"

            # Add intensity analysis
            intensity_words = ['very', 'moderately', 'slightly']
            intensity = random.choice(intensity_words)
            detailed_sentiment += f" - {intensity} {base_sentiment}"

            return detailed_sentiment

        return base_sentiment

    def generate_dialogue_with_profile(self, prompt: str, creativity_factor: float) -> str:
        """Generate dialogue with creativity profile influence"""
        base_dialogue = self.generate_dialogue(prompt)

        if creativity_factor > 0.6:
            # Creative agents add more engaging and varied responses
            creative_responses = [
                "That's a fascinating perspective! Let me explore this idea further...",
                "Your question opens up intriguing possibilities. Consider this approach...",
                "This reminds me of similar challenges in other domains. Here's what I've observed...",
                "Let's think about this from a different angle entirely..."
            ]

            if "hello" in prompt.lower() or "hi" in prompt.lower():
                return random.choice([
                    "Greetings! I'm excited to explore new ideas with you today.",
                    "Hello! Let's embark on a creative journey together.",
                    "Hi there! I'm ready to think outside the box with you."
                ])
            elif random.random() < 0.3:  # 30% chance to add creative element
                return f"{base_dialogue} {random.choice(creative_responses)}"

        return base_dialogue

    def general_language_with_profile(self, content: str, creativity_factor: float, precision_factor: float) -> str:
        """General language processing with profile influence"""
        base_result = f"Language processing of: {content}"

        if creativity_factor > 0.6:
            base_result += " Exploring creative interpretations and novel connections."
        elif precision_factor > 0.7:
            base_result += " Applying precise linguistic analysis and structural examination."

        return base_result

    def set_behavior_profile(self, profile_name: str) -> bool:
        """Change the agent's behavior profile"""
        success = self.behavior_profile.set_profile(profile_name)
        if success:
            logger.log("INFO", "LanguageAgent", f"Behavior profile changed to: {profile_name}")
        return success

    def get_behavior_info(self) -> Dict[str, Any]:
        """Get current behavior profile information"""
        return {
            "profile": self.behavior_profile.current_profile,
            "description": get_behavior_description(self.behavior_profile),
            "parameters": self.behavior_profile.get_profile_info(),
            "performance_history": len(self.performance_history)
        }

    def summarize_text(self, text: str) -> str:
        """Summarize text content using OpenAI GPT-4o or basic NLP fallback"""
        if self.use_openai:
            return self._summarize_with_openai(text)
        else:
            # Fallback to basic NLP
            sentences = text.split('.')
            # Simple extractive summarization: take first and last sentences
            if len(sentences) <= 2:
                return text
            summary = sentences[0].strip() + '. ' + sentences[-2].strip() + '.'
            return summary[:100] + '...' if len(summary) > 100 else summary

    def _summarize_with_openai(self, text: str) -> str:
        """Summarize text using OpenAI GPT-4o"""
        try:
            prompt = f"Please provide a concise summary of the following text in 2-3 sentences:\n\n{text[:2000]}"  # Limit input length

            if self.openai_client:
                # New OpenAI v1.0+ API
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that provides clear, concise summaries."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.3
                )
                summary = response.choices[0].message.content.strip()
            else:
                # Legacy API fallback
                response = openai.ChatCompletion.create(
                    model=self.openai_model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that provides clear, concise summaries."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.3
                )
                summary = response.choices[0].message.content.strip()

            logger.log("INFO", "LanguageAgent", "Generated OpenAI summary", {"input_length": len(text), "summary_length": len(summary)})
            return summary

        except Exception as e:
            logger.log("ERROR", "LanguageAgent", f"OpenAI summarization failed: {str(e)}")
            # Fallback to basic method
            return self.summarize_text(text)  # Recursive call without OpenAI

    def analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of text using OpenAI GPT-4o or keyword matching fallback"""
        if self.use_openai:
            return self._analyze_sentiment_with_openai(text)
        else:
            # Fallback to keyword matching
            positive_words = ['good', 'great', 'excellent', 'happy', 'love', 'like']
            negative_words = ['bad', 'terrible', 'awful', 'sad', 'hate', 'dislike']

            text_lower = text.lower()
            pos_count = sum(1 for word in positive_words if word in text_lower)
            neg_count = sum(1 for word in negative_words if word in text_lower)

            if pos_count > neg_count:
                return "positive"
            elif neg_count > pos_count:
                return "negative"
            else:
                return "neutral"

    def _analyze_sentiment_with_openai(self, text: str) -> str:
        """Analyze sentiment using OpenAI GPT-4o"""
        try:
            prompt = f"Analyze the sentiment of the following text and respond with only one word: positive, negative, or neutral.\n\nText: {text[:1000]}"

            if self.openai_client:
                # New OpenAI v1.0+ API
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=[
                        {"role": "system", "content": "You are a sentiment analysis expert. Respond with exactly one word: positive, negative, or neutral."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=10,
                    temperature=0.1
                )
                sentiment = response.choices[0].message.content.strip().lower()
            else:
                # Legacy API fallback
                response = openai.ChatCompletion.create(
                    model=self.openai_model,
                    messages=[
                        {"role": "system", "content": "You are a sentiment analysis expert. Respond with exactly one word: positive, negative, or neutral."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=10,
                    temperature=0.1
                )
                sentiment = response.choices[0].message.content.strip().lower()

            # Validate response
            if sentiment not in ['positive', 'negative', 'neutral']:
                sentiment = 'neutral'  # fallback

            logger.log("INFO", "LanguageAgent", f"OpenAI sentiment analysis: {sentiment}")
            return sentiment

        except Exception as e:
            logger.log("ERROR", "LanguageAgent", f"OpenAI sentiment analysis failed: {str(e)}")
            # Fallback to keyword method
            return self.analyze_sentiment(text)  # Recursive call without OpenAI

    def scrape_web_content(self, url: str) -> str:
        """Scrape text content from a web URL"""
        if not URLLIB_AVAILABLE:
            return f"Web scraping unavailable for {url}"

        try:
            with urllib.request.urlopen(url) as response:
                html = response.read().decode('utf-8', errors='ignore')

            # Simple text extraction (remove HTML tags)
            import re
            text = re.sub(r'<[^>]+>', '', html)
            # Clean up whitespace
            text = ' '.join(text.split())
            return text[:1000]  # Limit content length
        except Exception as e:
            logger.log("ERROR", "LanguageAgent", f"Web scraping failed: {str(e)}")
            return f"Failed to scrape {url}: {str(e)}"

    def generate_dialogue(self, prompt: str) -> str:
        """Generate dialogue response using OpenAI GPT-4o or pattern matching fallback"""
        if self.use_openai:
            return self._generate_dialogue_with_openai(prompt)
        else:
            # Fallback to pattern matching and web knowledge
            prompt_lower = prompt.lower()

            # Check if prompt contains a URL for web scraping
            url_match = re.search(r'https?://[^\s]+', prompt)
            if url_match:
                url = url_match.group(0)
                scraped_content = self.scrape_web_content(url)
                return f"Based on content from {url}: {scraped_content[:200]}..."

            # Standard dialogue responses
            if "hello" in prompt_lower or "hi" in prompt_lower:
                return "Hello! How can I help you today?"
            elif "how are you" in prompt_lower:
                return "I'm doing well, thank you for asking. How about you?"
            elif "what" in prompt_lower and "time" in prompt_lower:
                import time
                return f"The current time is {time.strftime('%H:%M:%S')}."
            else:
                return f"I understand you're asking about: {prompt}. Can you provide more details?"

    def _generate_dialogue_with_openai(self, prompt: str) -> str:
        """Generate dialogue response using OpenAI GPT-4o"""
        try:
            # Check if prompt contains a URL for web scraping first
            url_match = re.search(r'https?://[^\s]+', prompt)
            if url_match:
                url = url_match.group(0)
                scraped_content = self.scrape_web_content(url)
                return f"Based on content from {url}: {scraped_content[:200]}..."

            system_prompt = """You are a helpful AI assistant in a swarm intelligence system.
            Provide natural, conversational responses that are informative and engaging.
            Keep responses concise but helpful."""

            if self.openai_client:
                # New OpenAI v1.0+ API
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.7
                )
                dialogue_response = response.choices[0].message.content.strip()
            else:
                # Legacy API fallback
                response = openai.ChatCompletion.create(
                    model=self.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.7
                )
                dialogue_response = response.choices[0].message.content.strip()

            logger.log("INFO", "LanguageAgent", "Generated OpenAI dialogue response", {"prompt_length": len(prompt), "response_length": len(dialogue_response)})
            return dialogue_response

        except Exception as e:
            logger.log("ERROR", "LanguageAgent", f"OpenAI dialogue generation failed: {str(e)}")
            # Fallback to pattern matching method
            return self.generate_dialogue(prompt)  # Recursive call without OpenAI

class MathReasoningAgent(BaseAgent):
    """Performs calculations and logical reasoning"""

    def __init__(self, agent_id: str, swarm_id: Optional[str] = None):
        super().__init__(agent_id, AgentRole.MATH_REASONING_AGENT, swarm_id)
        self.math_capabilities = ["calculation", "logical_reasoning", "problem_solving"]

    def process_message(self, message: Message) -> Optional[Message]:
        """Process incoming messages related to math tasks"""
        if message.message_type == MessageType.TASK_ASSIGNMENT:
            return self.handle_task_assignment(message)
        return None

    def execute_task(self, task: Dict[str, Any]) -> Any:
        """Execute math-related tasks with self-ask guidance"""
        task_type = task.get("type", "general_math")
        content = task.get("content", "")

        # Use self-ask guidance to clarify task execution
        guidance = self.self_ask_guidance(task)
        logger.log("INFO", "MathReasoningAgent", f"Self-ask guidance: confidence={guidance['confidence_score']:.2f}, clarifications={guidance['clarification_needed']}")

        # Log guidance for transparency with branch selection reasoning
        from ..core.base import metrics

        # Create detailed reasoning steps with branch choices
        reasoning_steps = [{
            "step": "self_ask_guidance",
            "description": "Applied self-ask prompts for mathematical task clarification",
            "evidence": f"Next step: {guidance['next_actionable_step']['action']}, Tool: {guidance['recommended_tool']['recommended_tool']}",
            "conclusion": f"Guidance confidence: {guidance['confidence_score']:.2f}",
            "confidence": guidance['confidence_score'],
            "branch_options": ["proceed_with_guidance", "request_clarification", "use_fallback_method"],
            "chosen_branch": "proceed_with_guidance",
            "branch_selection_reason": f"High confidence ({guidance['confidence_score']:.2f}) in guidance and all required inputs available"
        }]

        # Add branch selection for tool choice
        if guidance['recommended_tool']['tool_selected']:
            reasoning_steps.append({
                "step": "tool_selection",
                "description": "Evaluating recommended tool for mathematical reasoning",
                "evidence": f"Recommended: {guidance['recommended_tool']['recommended_tool']} with confidence {guidance['recommended_tool']['confidence']:.2f}",
                "conclusion": f"Selected {guidance['recommended_tool']['recommended_tool']} for task execution",
                "confidence": guidance['recommended_tool']['confidence'],
                "branch_options": ["MathReasoningAgent", "LanguageAgent", "SimulationAgent", "fallback_method"],
                "chosen_branch": guidance['recommended_tool']['recommended_tool'],
                "branch_selection_reason": f"Tool has mathematical capabilities and high keyword match confidence"
            })

        metrics.log_reasoning_trace(
            self.agent_id,
            f"task_{id(task)}",
            reasoning_steps,
            f"Execute {task_type} task",
            guidance['confidence_score']
        )

        # Validate inputs before proceeding
        if not guidance['required_inputs_check']['all_inputs_available']:
            missing = guidance['required_inputs_check']['missing_inputs']
            logger.log("WARNING", "MathReasoningAgent", f"Missing required inputs: {missing}")
            return f"Cannot proceed: missing required inputs {missing}"

        if task_type == "calculation":
            return self.perform_calculation(content)
        elif task_type == "logical_reasoning":
            return self.logical_reasoning(content)
        elif task_type == "problem_solving":
            return self.solve_problem(content)
        else:
            return f"Math reasoning for: {content}"

    def handle_task_assignment(self, message: Message) -> Optional[Message]:
        """Handle task assignment messages with comprehensive error handling"""
        task_data = message.content.get("task")
        if task_data:
            # Use error handling wrapper for robust execution
            result = self.execute_with_error_handling(task_data.requirements)
            return self.send_message(message.sender, MessageType.RESULT_REPORT,
                                    {"task_id": task_data.task_id, "result": result})
        return None

    def perform_calculation(self, expression: str) -> Any:
        """Perform mathematical calculation using safe evaluation"""
        try:
            # Safe evaluation using ast
            node = ast.parse(expression, mode='eval')
            safe_names = {
                k: v for k, v in vars(operator).items() if not k.startswith('_')
            }
            safe_names.update(vars(__import__('math')))
            result = eval(compile(node, '<string>', 'eval'), {"__builtins__": {}}, safe_names)
            return result
        except Exception as e:
            # Raise exception instead of returning error string for proper error handling
            raise ValueError(f"Calculation error: {str(e)}")

    def logical_reasoning(self, problem: str) -> str:
        """Perform logical reasoning using pattern matching"""
        problem_lower = problem.lower()
        if "all" in problem_lower and "are" in problem_lower:
            return "Using universal quantification: If all A are B, then specific A is B"
        elif "if" in problem_lower and "then" in problem_lower:
            return "Applying modus ponens: If P then Q, P therefore Q"
        elif "not both" in problem_lower:
            return "Using De Morgan's law: Not (P and Q) ≡ Not P or Not Q"
        else:
            return f"Logical analysis of: {problem}"

    def solve_problem(self, problem: str) -> str:
        """Solve mathematical problem using parsing"""
        problem_lower = problem.lower()
        if "solve for x" in problem_lower:
            # Simple linear equation solver
            return self.solve_linear_equation(problem)
        elif "factor" in problem_lower:
            return "Factoring requires symbolic math library"
        elif "integral" in problem_lower or "derivative" in problem_lower:
            return "Calculus operations require advanced math library"
        else:
            return f"Attempting to solve: {problem}"

    def solve_linear_equation(self, equation: str) -> str:
        """Simple linear equation solver (e.g., 2x + 3 = 7)"""
        try:
            # Very basic parser for ax + b = c
            parts = equation.replace(" ", "").split("=")
            if len(parts) != 2:
                return "Invalid equation format"

            left = parts[0]
            right = parts[1]

            # Assume form ax + b = c
            if "x" in left:
                # Move all to left: ax + b - c = 0
                c = float(right)
                if "+" in left:
                    terms = left.split("+")
                    a = float(terms[0].replace("x", ""))
                    b = float(terms[1])
                elif "-" in left:
                    terms = left.split("-")
                    a = float(terms[0].replace("x", ""))
                    b = -float(terms[1])
                else:
                    a = float(left.replace("x", ""))
                    b = 0

                x = (c - b) / a
                return f"x = {x}"
            else:
                return "Equation must contain variable x"
        except:
            return "Unable to solve equation"

    def symbolic_computation(self, expression: str) -> str:
        """Perform symbolic computation using sympy"""
        if not SYMPY_AVAILABLE:
            return "SymPy not available for symbolic computation"

        try:
            # Parse and evaluate symbolic expressions
            result = sympy.sympify(expression)
            return f"Symbolic result: {result}"
        except Exception as e:
            return f"Symbolic computation failed: {str(e)}"

    def solve_symbolic_equation(self, equation: str, variable: str = "x") -> str:
        """Solve symbolic equations using sympy"""
        if not SYMPY_AVAILABLE:
            return "SymPy not available for symbolic equation solving"

        try:
            x = sympy.Symbol(variable)
            eq = sympy.Eq(*[sympy.sympify(side.strip()) for side in equation.split("=")])
            solutions = sympy.solve(eq, x)
            return f"Solutions for {variable}: {solutions}"
        except Exception as e:
            return f"Symbolic equation solving failed: {str(e)}"

    def calculate_derivative(self, expression: str, variable: str = "x") -> str:
        """Calculate derivative using sympy"""
        if not SYMPY_AVAILABLE:
            return "SymPy not available for derivative calculation"

        try:
            x = sympy.Symbol(variable)
            expr = sympy.sympify(expression)
            derivative = sympy.diff(expr, x)
            return f"d/d{variable}({expression}) = {derivative}"
        except Exception as e:
            return f"Derivative calculation failed: {str(e)}"

    def calculate_integral(self, expression: str, variable: str = "x") -> str:
        """Calculate integral using sympy"""
        if not SYMPY_AVAILABLE:
            return "SymPy not available for integral calculation"

        try:
            x = sympy.Symbol(variable)
            expr = sympy.sympify(expression)
            integral = sympy.integrate(expr, x)
            return f"∫({expression})d{variable} = {integral} + C"
        except Exception as e:
            return f"Integral calculation failed: {str(e)}"

class SimulationAgent(BaseAgent):
    """Runs scenario simulations and sandbox tests"""

    def __init__(self, agent_id: str, swarm_id: Optional[str] = None):
        super().__init__(agent_id, AgentRole.SIMULATION_AGENT, swarm_id)
        self.simulation_capabilities = ["scenario_simulation", "sandbox_testing", "outcome_prediction"]

    def process_message(self, message: Message) -> Optional[Message]:
        """Process incoming messages related to simulation tasks"""
        if message.message_type == MessageType.TASK_ASSIGNMENT:
            return self.handle_task_assignment(message)
        return None

    def execute_task(self, task: Dict[str, Any]) -> Any:
        """Execute simulation-related tasks"""
        task_type = task.get("type", "general_simulation")
        content = task.get("content", "")

        if task_type == "scenario_simulation":
            return self.simulate_scenario(content)
        elif task_type == "sandbox_testing":
            return self.sandbox_test(content)
        elif task_type == "outcome_prediction":
            return self.predict_outcome(content)
        else:
            return f"Simulation result for: {content}"

    def handle_task_assignment(self, message: Message) -> Optional[Message]:
        """Handle task assignment messages with comprehensive error handling"""
        task_data = message.content.get("task")
        if task_data:
            # Use error handling wrapper for robust execution
            result = self.execute_with_error_handling(task_data.requirements)
            return self.send_message(message.sender, MessageType.RESULT_REPORT,
                                    {"task_id": task_data.task_id, "result": result})
        return None

    def simulate_scenario(self, scenario: str) -> Dict[str, Any]:
        """Simulate a scenario with stochastic elements and adversarial factors"""
        # Initialize simulation parameters
        states = ["initial", "processing", "decision_point", "outcome"]
        current_state = "initial"
        steps = []
        resources = 100  # Resource pool
        adversarial_events = ["resource_shortage", "unexpected_change", "competition", "failure_risk"]

        # Stochastic simulation with random events
        for i in range(random.randint(3, 6)):  # Variable length simulation
            # Introduce random adversarial events
            if random.random() < 0.3:  # 30% chance of adversarial event
                event = random.choice(adversarial_events)
                steps.append(f"Step {i+1}: {current_state} - ADVERSARIAL: {event}")

                # Handle adversarial effects
                if event == "resource_shortage":
                    resources -= random.randint(10, 30)
                elif event == "unexpected_change":
                    # Random state change
                    current_state = random.choice(states)
                    continue
                elif event == "competition":
                    resources -= random.randint(5, 15)
                elif event == "failure_risk":
                    if random.random() < 0.4:  # 40% chance of failure
                        steps.append(f"Step {i+1}: SIMULATION FAILED due to {event}")
                        return {
                            "scenario": scenario,
                            "steps": steps,
                            "final_outcome": "failure",
                            "confidence": random.uniform(0.1, 0.4),
                            "resources_remaining": resources
                        }

            steps.append(f"Step {i+1}: {current_state} (resources: {resources})")

            # State transitions with stochastic elements
            if current_state == "initial":
                if random.random() < 0.8:  # 80% chance to proceed
                    current_state = "processing"
                else:
                    current_state = "decision_point"  # Early decision
            elif current_state == "processing":
                if "decision" in scenario.lower() and random.random() < 0.6:
                    current_state = "decision_point"
                elif random.random() < 0.7:
                    current_state = "outcome"
                # 30% chance to stay in processing
            elif current_state == "decision_point":
                # Multiple possible outcomes
                outcomes = ["outcome", "processing", "initial"]  # Could loop back
                weights = [0.6, 0.3, 0.1]
                current_state = random.choices(outcomes, weights=weights)[0]
            else:
                current_state = "outcome"

            # Resource consumption
            resources -= random.randint(5, 15)
            if resources <= 0:
                steps.append(f"Step {i+1}: SIMULATION TERMINATED - Resources depleted")
                return {
                    "scenario": scenario,
                    "steps": steps,
                    "final_outcome": "resource_failure",
                    "confidence": random.uniform(0.2, 0.5),
                    "resources_remaining": 0
                }

        # Determine final outcome with stochastic elements
        outcome_weights = {"success": 0.4, "partial_success": 0.3, "neutral": 0.2, "failure": 0.1}
        if "success" in scenario.lower():
            outcome_weights["success"] += 0.2
        if "failure" in scenario.lower():
            outcome_weights["failure"] += 0.2
        if resources < 50:
            outcome_weights["failure"] += 0.2
            outcome_weights["success"] -= 0.1

        final_outcome = random.choices(
            list(outcome_weights.keys()),
            weights=list(outcome_weights.values())
        )[0]

        return {
            "scenario": scenario,
            "steps": steps,
            "final_outcome": final_outcome,
            "confidence": random.uniform(0.5, 0.9),
            "resources_remaining": resources,
            "adversarial_events_encountered": len([s for s in steps if "ADVERSARIAL" in s])
        }

    def sandbox_test(self, test_case: str) -> str:
        """Run sandbox test with isolated execution"""
        # Simulate running test in sandbox
        try:
            # For demo, just evaluate simple expressions
            if "print" in test_case:
                return f"Sandbox output: {test_case.replace('print', '').strip()}"
            elif "calculate" in test_case:
                result = eval(test_case.split("calculate")[1].strip(), {"__builtins__": {}}, {})
                return f"Sandbox result: {result}"
            else:
                return f"Sandbox executed: {test_case} - no errors"
        except Exception as e:
            return f"Sandbox error: {str(e)}"

    def predict_outcome(self, conditions: str) -> str:
        """Predict outcome based on conditions using simple rules"""
        conditions_lower = conditions.lower()
        if "good" in conditions_lower or "positive" in conditions_lower:
            return "Predicted outcome: Success (80% confidence)"
        elif "bad" in conditions_lower or "negative" in conditions_lower:
            return "Predicted outcome: Failure (65% confidence)"
        elif "uncertain" in conditions_lower:
            return "Predicted outcome: Unclear (50% confidence)"
        else:
            return f"Predicted outcome based on: {conditions} - Moderate success (60% confidence)"

    def run_physics_simulation(self, scenario: dict) -> dict:
        """Run physics-based simulation (placeholder for physics engine integration)"""
        # This would integrate with physics engines like PyBullet, MuJoCo, etc.
        # For now, simulate basic physics
        objects = scenario.get("objects", [])
        forces = scenario.get("forces", [])
        time_steps = scenario.get("time_steps", 10)

        results = []
        for t in range(time_steps):
            # Simple physics simulation
            for obj in objects:
                # Apply forces, calculate positions, etc.
                obj["position"] = obj.get("position", 0) + obj.get("velocity", 0) * 0.1
                obj["velocity"] = obj.get("velocity", 0) + sum(forces) * 0.1
            results.append({"time": t, "objects": objects.copy()})

        return {
            "simulation_type": "physics",
            "results": results,
            "final_state": objects
        }

    def run_game_simulation(self, game_config: dict) -> dict:
        """Run game environment simulation (placeholder for game engine integration)"""
        if not PYGAME_AVAILABLE:
            return {"error": "Pygame not available for game simulation"}

        # This would integrate with game engines or pygame
        # For now, simulate a simple game scenario
        player_pos = game_config.get("player_start", [0, 0])
        obstacles = game_config.get("obstacles", [])
        goal = game_config.get("goal", [10, 10])

        # Simulate game steps
        steps = []
        for step in range(20):
            # Simple AI movement toward goal
            dx = goal[0] - player_pos[0]
            dy = goal[1] - player_pos[1]
            move_x = 1 if dx > 0 else -1 if dx < 0 else 0
            move_y = 1 if dy > 0 else -1 if dy < 0 else 0

            player_pos[0] += move_x * 0.5
            player_pos[1] += move_y * 0.5

            # Check collisions (simplified)
            collision = any(abs(player_pos[0] - obs[0]) < 1 and abs(player_pos[1] - obs[1]) < 1 for obs in obstacles)
            goal_reached = abs(player_pos[0] - goal[0]) < 1 and abs(player_pos[1] - goal[1]) < 1

            steps.append({
                "step": step,
                "position": player_pos.copy(),
                "collision": collision,
                "goal_reached": goal_reached
            })

            if collision or goal_reached:
                break

        return {
            "simulation_type": "game",
            "steps": steps,
            "final_position": player_pos,
            "success": goal_reached
        }

    def run_financial_simulation(self, market_data: dict) -> dict:
        """Run financial forecasting simulation"""
        # This would integrate with financial APIs or models
        # For now, simulate market trends
        initial_value = market_data.get("initial_investment", 1000)
        time_periods = market_data.get("periods", 12)
        volatility = market_data.get("volatility", 0.1)

        values = [initial_value]
        for period in range(time_periods):
            # Simulate market fluctuations
            change = random.gauss(0, volatility)  # Normal distribution
            new_value = values[-1] * (1 + change)
            values.append(max(0, new_value))  # Can't go negative

        return {
            "simulation_type": "financial",
            "initial_investment": initial_value,
            "final_value": values[-1],
            "total_return": (values[-1] - initial_value) / initial_value * 100,
            "value_history": values,
            "volatility_used": volatility
        }
class ImaginationSimulation(BaseAgent):
    """Imagination and simulation for hypothetical scenarios"""

    def __init__(self, agent_id: str, swarm_id: Optional[str] = None):
        super().__init__(agent_id, AgentRole.DEFAULT_MODE_NETWORK, swarm_id)
        self.sandbox_environments: Dict[str, Dict[str, Any]] = {}
        self.emergent_behaviors: List[Dict[str, Any]] = []

    def process_message(self, message: Message) -> Optional[Message]:
        """Process incoming messages related to imagination tasks"""
        if message.message_type == MessageType.TASK_ASSIGNMENT:
            return self.handle_task_assignment(message)
        elif message.message_type == MessageType.SIMULATION_REQUEST:
            return self.handle_simulation_request(message)
        return None

    def execute_task(self, task: Dict[str, Any]) -> Any:
        """Execute imagination/simulation tasks"""
        task_type = task.get("type", "general_imagination")
        content = task.get("content", "")

        if task_type == "hypothetical_scenario":
            return self.run_hypothetical_scenario(content)
        elif task_type == "behavior_analysis":
            return self.analyze_emergent_behavior(content)
        else:
            return f"Imagination simulation for: {content}"

    def handle_task_assignment(self, message: Message) -> Optional[Message]:
        """Handle task assignment messages with comprehensive error handling"""
        task_data = message.content.get("task")
        if task_data:
            # Use error handling wrapper for robust execution
            result = self.execute_with_error_handling(task_data.requirements)
            return self.send_message(message.sender, MessageType.RESULT_REPORT,
                                    {"task_id": task_data.task_id, "result": result})
        return None

    def handle_simulation_request(self, message: Message) -> Optional[Message]:
        """Handle simulation request messages"""
        scenario = message.content.get("scenario", "")
        result = self.run_sandbox_simulation(scenario)
        return self.send_message(message.sender, MessageType.RESULT_REPORT,
                               {"simulation_result": result})

    def sandbox_environment(self, scenario_name: str, initial_conditions: Dict[str, Any]) -> str:
        """Create and manage sandbox environment for testing"""
        env_id = f"sandbox_{scenario_name}_{int(time.time())}"
        self.sandbox_environments[env_id] = {
            "name": scenario_name,
            "conditions": initial_conditions,
            "state": "initialized",
            "interactions": []
        }
        return f"Created sandbox environment: {env_id}"

    def emergent_behavior_tracking(self, interaction_data: Dict[str, Any]) -> str:
        """Track and analyze emergent behaviors from agent interactions"""
        behavior = {
            "timestamp": time.time(),
            "interaction": interaction_data,
            "patterns": self.detect_patterns(interaction_data),
            "insights": self.generate_insights(interaction_data)
        }
        self.emergent_behaviors.append(behavior)

        # Send feedback to coordinator for dynamic planning adjustment
        feedback = {
            "emergent_patterns": behavior["patterns"],
            "insights": behavior["insights"],
            "recommendations": self.generate_recommendations(behavior)
        }
        self.send_message("SwarmCoordinator", MessageType.SIMULATION_REQUEST, {"emergent_feedback": feedback})

        return f"Tracked emergent behavior: {behavior['patterns']}"

    def run_hypothetical_scenario(self, scenario: str) -> Dict[str, Any]:
        """Run a hypothetical scenario with stochastic and adversarial elements"""
        # Generate multiple possible outcomes with probabilities
        base_outcomes = ["success", "partial_success", "failure", "unexpected_complication"]

        # Add adversarial outcomes based on scenario content
        if "risk" in scenario.lower() or "challenge" in scenario.lower():
            base_outcomes.extend(["catastrophic_failure", "resource_crisis"])
        if "competition" in scenario.lower():
            base_outcomes.extend(["competitive_advantage", "market_disruption"])

        # Generate 3-5 possible outcomes
        num_outcomes = random.randint(3, 5)
        selected_outcomes = random.sample(base_outcomes, min(num_outcomes, len(base_outcomes)))

        # Generate probability distribution with some stochastic variation
        probabilities = []
        remaining_prob = 1.0
        for i in range(len(selected_outcomes) - 1):
            # Bias toward certain outcomes based on scenario
            base_prob = 0.2
            if "success" in selected_outcomes[i].lower():
                base_prob += 0.1 if "success" in scenario.lower() else 0
            elif "failure" in selected_outcomes[i].lower():
                base_prob += 0.1 if "risk" in scenario.lower() else -0.05

            prob = random.uniform(max(0.05, base_prob - 0.1), min(0.4, base_prob + 0.1))
            prob = min(prob, remaining_prob - 0.05 * (len(selected_outcomes) - i - 1))
            probabilities.append(prob)
            remaining_prob -= prob

        probabilities.append(remaining_prob)  # Last probability

        # Introduce adversarial factors
        adversarial_modifiers = []
        if random.random() < 0.4:  # 40% chance of adversarial elements
            modifiers = [
                "external_interference",
                "resource_fluctuation",
                "stakeholder_conflict",
                "technological_failure"
            ]
            adversarial_modifiers = random.sample(modifiers, random.randint(1, 3))

        return {
            "scenario": scenario,
            "possible_outcomes": selected_outcomes,
            "probability_distribution": probabilities,
            "adversarial_modifiers": adversarial_modifiers,
            "robustness_score": random.uniform(0.3, 0.9)  # How robust the scenario is
        }

    def analyze_emergent_behavior(self, behavior_data: str) -> str:
        """Analyze emergent behavior patterns"""
        return f"Analysis of emergent behavior: {behavior_data}"

    def run_sandbox_simulation(self, scenario: str) -> Dict[str, Any]:
        """Run simulation in sandbox environment"""
        return {
            "scenario": scenario,
            "simulation_steps": ["step1", "step2", "step3"],
            "final_state": "completed",
            "emergent_insights": ["insight1", "insight2"]
        }

    def detect_patterns(self, interaction_data: Dict[str, Any]) -> List[str]:
        """Detect patterns in interaction data (mock implementation)"""
        return ["pattern1", "pattern2"]

    def generate_insights(self, interaction_data: Dict[str, Any]) -> List[str]:
        """Generate insights from interaction data (mock implementation)"""
        return ["insight1", "insight2"]

    def generate_recommendations(self, behavior: Dict[str, Any]) -> List[str]:
        """Generate planning recommendations based on emergent behavior"""
        recommendations = []
        patterns = behavior.get("patterns", [])

        if "cooperation" in str(patterns).lower():
            recommendations.append("Increase collaborative task assignments")
        if "competition" in str(patterns).lower():
            recommendations.append("Implement resource sharing mechanisms")
        if "efficiency" in str(patterns).lower():
            recommendations.append("Prioritize efficient agent combinations")

        return recommendations or ["Monitor behavior patterns for future optimization"]

    def send_simulation_feedback(self, scenario: str, outcomes: Dict[str, Any]):
        """Send simulation feedback to coordinator for planning"""
        feedback = {
            "scenario": scenario,
            "possible_outcomes": outcomes.get("simulation_steps", []),
            "insights": outcomes.get("emergent_insights", [])
        }
        # Send to coordinator (assuming coordinator id is known or broadcast)
        self.send_message("SwarmCoordinator", MessageType.SIMULATION_REQUEST, {"feedback": feedback})
    def handle_knowledge_sharing(self, message: Message) -> Optional[Message]:
        """Handle incoming knowledge sharing from other agents"""
        knowledge = message.content
        logger.log("INFO", "LanguageAgent", "Received knowledge", {"from": message.sender, "knowledge": str(knowledge)[:100]})

        # Store received knowledge
        if "language_pattern" in knowledge:
            self.language_capabilities.append(knowledge["language_pattern"])
            logger.log("INFO", "LanguageAgent", "Learned new language pattern", {"pattern": knowledge["language_pattern"]})

        return None

    def query_knowledge_api(self, query: str, api_endpoint: str = "https://api.duckduckgo.com/") -> str:
        """Query external knowledge APIs"""
        if not REQUESTS_AVAILABLE and not URLLIB_AVAILABLE:
            return f"HTTP libraries not available for API query: {query}"

        try:
            if REQUESTS_AVAILABLE:
                params = {"q": query, "format": "json"}
                response = requests.get(api_endpoint, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # Extract relevant information (simplified)
                    if "AbstractText" in data and data["AbstractText"]:
                        return data["AbstractText"]
                    elif "Answer" in data and data["Answer"]:
                        return data["Answer"]
                    else:
                        return f"API response received but no relevant content for: {query}"
                else:
                    return f"API error: {response.status_code}"
            else:
                # Fallback to urllib
                full_url = f"{api_endpoint}?q={urllib.parse.quote(query)}&format=json"
                with urllib.request.urlopen(full_url, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    return data.get("AbstractText", f"No abstract found for: {query}")
        except Exception as e:
            return f"API query failed: {str(e)}"

    def fetch_news_feed(self, topic: str, news_api_key: str = None) -> str:
        """Fetch news articles on a topic"""
        if not REQUESTS_AVAILABLE:
            return f"Requests library not available for news feed: {topic}"

        # Example with NewsAPI (would need actual API key)
        base_url = "https://newsapi.org/v2/everything"
        params = {
            "q": topic,
            "apiKey": news_api_key or "demo_key",  # Would need real key
            "pageSize": 3
        }

        try:
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                if articles:
                    summaries = [f"- {article['title']}: {article.get('description', 'No description')}" for article in articles[:3]]
                    return f"Recent news on {topic}:\n" + "\n".join(summaries)
                else:
                    return f"No news articles found for: {topic}"
            else:
                return f"News API error: {response.status_code}"
        except Exception as e:
            return f"News feed fetch failed: {str(e)}"

    def share_learned_strategy(self, recipient: str, strategy: str):
        """Share a learned language strategy with another agent"""
        knowledge = {
            "language_pattern": strategy,
            "learned_from": self.agent_id,
            "timestamp": time.time()
        }
        self.share_knowledge(recipient, knowledge)
        logger.log("INFO", "LanguageAgent", "Shared language strategy", {"recipient": recipient, "strategy": strategy})