"""
Google Gemini AI Integration

This module handles AI content generation using Google's Gemini API
for creating platform-optimized social media posts.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

import google.generativeai as genai
import structlog

from src.config.settings import get_settings
from src.models.content import ContentTopic, GeneratedPost, PlatformType, SourceContent
from src.models.user import ContentPreferences
from src.utils.monitoring import performance_monitor, track_performance
from src.utils.error_handling import (
    with_retry, with_circuit_breaker, with_error_handling, 
    ContentGenerationError, APIRateLimitError, ErrorContext, error_handler
)


class GeminiClient:
    """Google Gemini AI client for content generation."""
    
    def __init__(self):
        """Initialize Gemini client."""
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        
        # Configure Gemini API
        genai.configure(api_key=self.settings.gemini_api_key)
        
        # Initialize model
        self.model = genai.GenerativeModel(self.settings.gemini_model)
        
        # Generation configuration
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=40,
            max_output_tokens=2048,
        )
        
        # Safety settings
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
    
    @track_performance("content_generation", {"model": "gemini"})
    async def generate_posts(
        self,
        source_content: SourceContent,
        platforms: List[PlatformType],
        user_preferences: ContentPreferences,
        custom_instructions: Optional[str] = None
    ) -> Dict[PlatformType, GeneratedPost]:
        """
        Generate platform-optimized posts from source content.
        
        Args:
            source_content: Original content to transform
            platforms: Target platforms for generation
            user_preferences: User's content preferences
            custom_instructions: Optional custom generation instructions
            
        Returns:
            Dictionary mapping platforms to generated posts
        """
        start_time = time.time()
        generation_success = True
        
        self.logger.info(
            "Generating posts with Gemini",
            content_id=source_content.source_id,
            platforms=platforms
        )
        
        generated_posts = {}
        
        for platform in platforms:
            try:
                post = await self._generate_platform_post(
                    source_content=source_content,
                    platform=platform,
                    user_preferences=user_preferences,
                    custom_instructions=custom_instructions
                )
                if post:
                    generated_posts[platform] = post
                    
            except Exception as e:
                generation_success = False
                self.logger.error(
                    "Failed to generate post for platform",
                    platform=platform,
                    content_id=source_content.source_id,
                    error=str(e)
                )
                continue
        
        # Track performance metrics
        duration = time.time() - start_time
        success_rate = len(generated_posts) / len(platforms) if platforms else 0
        
        # Track overall generation performance
        await performance_monitor.track_content_generation_performance(
            success=generation_success and len(generated_posts) > 0,
            duration_seconds=duration,
            platform=",".join([p.value for p in platforms]),
            fact_check_score=sum(p.fact_check_score for p in generated_posts.values()) / len(generated_posts) if generated_posts else 0,
            user_id="system"  # Would be actual user_id in practice
        )
        
        self.logger.info(
            "Post generation completed",
            content_id=source_content.source_id,
            successful_platforms=len(generated_posts),
            duration=duration,
            success_rate=success_rate
        )
        
        return generated_posts
    
    async def _generate_platform_post(
        self,
        source_content: SourceContent,
        platform: PlatformType,
        user_preferences: ContentPreferences,
        custom_instructions: Optional[str] = None
    ) -> Optional[GeneratedPost]:
        """Generate a post for a specific platform."""
        try:
            # Build the generation prompt
            prompt = self._build_generation_prompt(
                source_content=source_content,
                platform=platform,
                user_preferences=user_preferences,
                custom_instructions=custom_instructions
            )
            
            # Generate content with Gemini
            response = await self._call_gemini_api(prompt)
            
            if not response:
                return None
            
            # Parse and validate the response
            post_data = self._parse_generation_response(response, platform)
            
            if not post_data:
                return None
            
            # Calculate quality scores
            quality_scores = await self._calculate_quality_scores(
                post_content=post_data["content"],
                source_content=source_content,
                platform=platform
            )
            
            # Create GeneratedPost object
            generated_post = GeneratedPost(
                platform=platform,
                content=post_data["content"],
                hashtags=post_data.get("hashtags", []),
                mentions=post_data.get("mentions", []),
                character_count=len(post_data["content"]),
                estimated_reading_time=self._estimate_reading_time(post_data["content"]),
                relevance_score=quality_scores["relevance"],
                engagement_prediction=quality_scores["engagement"],
                fact_check_score=quality_scores["fact_check"],
                ai_model=self.settings.gemini_model,
                generation_prompt=prompt[:200] + "..." if len(prompt) > 200 else prompt,
            )
            
            return generated_post
            
        except Exception as e:
            self.logger.error(
                "Platform post generation failed",
                platform=platform,
                error=str(e)
            )
            return None
    
    def _build_generation_prompt(
        self,
        source_content: SourceContent,
        platform: PlatformType,
        user_preferences: ContentPreferences,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Build the AI generation prompt for specific platform and preferences."""
        
        # Platform-specific requirements
        platform_specs = {
            PlatformType.LINKEDIN: {
                "length": "200-400 words",
                "tone": "professional and authoritative",
                "structure": "Hook → Insight → Business implication → Engagement question",
                "hashtags": "3-5 relevant professional hashtags",
                "format": "Well-structured with line breaks for readability"
            },
            PlatformType.TWITTER: {
                "length": "220-280 characters",
                "tone": "conversational but credible",
                "structure": "Hook → Key insight → Call-to-action",
                "hashtags": "1-2 relevant hashtags",
                "format": "Concise and punchy with potential for engagement"
            }
        }
        
        spec = platform_specs.get(platform, platform_specs[PlatformType.LINKEDIN])
        
        # Build topics context
        topics_context = ", ".join([topic.value.replace("-", " ").title() for topic in source_content.topics])
        
        # Build user context
        user_context = f"""
User Profile:
- Tone preference: {user_preferences.tone}
- Topics of interest: {', '.join(user_preferences.topics)}
- Target audience: AI professionals, engineers, and startup founders
"""
        
        # Main prompt
        prompt = f"""
You are an expert social media content creator specializing in AI and technology content for professionals.

TASK: Transform the source content below into an engaging {platform.value} post.

PLATFORM: {platform.value}
REQUIREMENTS:
- Length: {spec['length']}
- Tone: {spec['tone']}
- Structure: {spec['structure']}
- Hashtags: {spec['hashtags']}
- Format: {spec['format']}

{user_context}

SOURCE CONTENT:
Title: {source_content.title}
Description: {source_content.description or "No description available"}
URL: {source_content.url}
Topics: {topics_context}
Engagement Score: {source_content.engagement_score:.2f}
Author: {source_content.author or "Unknown"}

CONTENT GUIDELINES:
1. Make it valuable and actionable for AI professionals
2. Include insights that go beyond just summarizing the source
3. Use professional language appropriate for business networks
4. Ensure factual accuracy - don't make claims beyond what's in the source
5. Add relevant hashtags naturally
6. Include a clear call-to-action or discussion prompt
7. Maintain authenticity - sound like a human expert, not a bot

{f"CUSTOM INSTRUCTIONS: {custom_instructions}" if custom_instructions else ""}

RESPONSE FORMAT:
Return your response as a JSON object with this exact structure:
{{
    "content": "Your generated post content here",
    "hashtags": ["hashtag1", "hashtag2", "hashtag3"],
    "mentions": [],
    "reasoning": "Brief explanation of your content strategy"
}}

IMPORTANT: 
- Do NOT include the hashtags in the main content text
- Hashtags should be provided separately in the hashtags array
- Ensure the content stays within the character/word limits
- Make it engaging and professional
- Focus on insights and value for the AI community
"""
        
        return prompt
    
    @with_circuit_breaker("gemini")
    @with_retry(max_attempts=3, retryable_errors=[APIRateLimitError, ContentGenerationError])
    async def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """Make API call to Gemini and return response."""
        try:
            # Generate content
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            # Check if response was blocked
            if response.candidates[0].finish_reason.name == "SAFETY":
                self.logger.warning("Gemini response blocked by safety filter")
                raise ContentGenerationError(
                    "Content blocked by safety filter",
                    context=ErrorContext(service="gemini", operation="generate_content")
                )
            
            # Extract text from response
            response_text = response.text
            
            if not response_text:
                self.logger.warning("Empty response from Gemini")
                raise ContentGenerationError(
                    "Empty response from Gemini API",
                    context=ErrorContext(service="gemini", operation="generate_content")
                )
            
            return response_text
            
        except Exception as e:
            # Classify and handle the error
            error_str = str(e).lower()
            
            if "quota" in error_str or "rate limit" in error_str:
                raise APIRateLimitError(
                    f"Gemini API rate limit: {str(e)}",
                    context=ErrorContext(service="gemini", operation="generate_content")
                )
            elif "safety" in error_str or "blocked" in error_str:
                raise ContentGenerationError(
                    f"Content blocked: {str(e)}",
                    context=ErrorContext(service="gemini", operation="generate_content")
                )
            else:
                self.logger.error("Gemini API call failed", error=str(e))
                raise ContentGenerationError(
                    f"Gemini API error: {str(e)}",
                    context=ErrorContext(service="gemini", operation="generate_content"),
                    original_error=e
                )
            
            return None
    
    def _parse_generation_response(
        self, response: str, platform: PlatformType
    ) -> Optional[Dict]:
        """Parse and validate the AI generation response."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Look for JSON block
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_text = response[start:end].strip()
            elif response.startswith("{") and response.endswith("}"):
                json_text = response
            else:
                # Try to find JSON-like content
                start = response.find("{")
                end = response.rfind("}") + 1
                if start >= 0 and end > start:
                    json_text = response[start:end]
                else:
                    self.logger.warning("Could not find JSON in response")
                    return None
            
            # Parse JSON
            post_data = json.loads(json_text)
            
            # Validate required fields
            if "content" not in post_data:
                self.logger.warning("Missing content field in response")
                return None
            
            # Validate platform-specific constraints
            content = post_data["content"]
            
            if platform == PlatformType.TWITTER and len(content) > 280:
                self.logger.warning("Twitter content too long", length=len(content))
                # Truncate if needed
                post_data["content"] = content[:277] + "..."
            
            # Ensure hashtags is a list
            if "hashtags" not in post_data:
                post_data["hashtags"] = []
            elif not isinstance(post_data["hashtags"], list):
                post_data["hashtags"] = []
            
            # Ensure mentions is a list
            if "mentions" not in post_data:
                post_data["mentions"] = []
            elif not isinstance(post_data["mentions"], list):
                post_data["mentions"] = []
            
            return post_data
            
        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse JSON response", error=str(e))
            return None
        except Exception as e:
            self.logger.error("Response parsing failed", error=str(e))
            return None
    
    async def _calculate_quality_scores(
        self,
        post_content: str,
        source_content: SourceContent,
        platform: PlatformType
    ) -> Dict[str, float]:
        """Calculate quality scores for generated content."""
        try:
            # Relevance score based on keyword overlap and topic alignment
            relevance_score = self._calculate_relevance_score(post_content, source_content)
            
            # Engagement prediction based on content characteristics
            engagement_score = self._predict_engagement(post_content, platform)
            
            # Fact-check score (basic implementation)
            fact_check_score = self._basic_fact_check(post_content, source_content)
            
            return {
                "relevance": relevance_score,
                "engagement": engagement_score,
                "fact_check": fact_check_score
            }
            
        except Exception as e:
            self.logger.error("Quality score calculation failed", error=str(e))
            return {
                "relevance": 0.5,
                "engagement": 0.5,
                "fact_check": 0.5
            }
    
    def _calculate_relevance_score(self, post_content: str, source_content: SourceContent) -> float:
        """Calculate relevance score based on content similarity."""
        # Simple keyword-based relevance calculation
        post_words = set(post_content.lower().split())
        source_words = set((source_content.title + " " + (source_content.description or "")).lower().split())
        
        if not source_words:
            return 0.5
        
        overlap = len(post_words.intersection(source_words))
        relevance = min(overlap / len(source_words), 1.0)
        
        # Boost score for topic alignment
        topic_keywords = [topic.value.replace("-", " ") for topic in source_content.topics]
        for keyword in topic_keywords:
            if keyword.lower() in post_content.lower():
                relevance = min(relevance + 0.1, 1.0)
        
        return max(relevance, 0.1)  # Minimum score
    
    def _predict_engagement(self, post_content: str, platform: PlatformType) -> float:
        """Predict engagement potential based on content characteristics."""
        score = 0.5  # Base score
        
        content_lower = post_content.lower()
        
        # Positive indicators
        engagement_indicators = [
            "what do you think", "thoughts?", "agree?", "experience", "share",
            "question", "comment", "breakthrough", "game-changing", "revolutionary",
            "insight", "trend", "future", "prediction", "analysis"
        ]
        
        for indicator in engagement_indicators:
            if indicator in content_lower:
                score += 0.05
        
        # Platform-specific adjustments
        if platform == PlatformType.LINKEDIN:
            # LinkedIn favors longer, more detailed content
            if len(post_content) > 200:
                score += 0.1
            if "?" in post_content:  # Questions drive engagement
                score += 0.1
        
        elif platform == PlatformType.TWITTER:
            # Twitter favors concise, punchy content
            if len(post_content) < 200:
                score += 0.1
            if post_content.count("#") <= 2:  # Not too many hashtags
                score += 0.05
        
        return min(score, 1.0)
    
    def _basic_fact_check(self, post_content: str, source_content: SourceContent) -> float:
        """Basic fact-checking score based on conservative content generation."""
        # High confidence if post content doesn't make claims beyond source
        score = 0.8  # Default high confidence
        
        # Check for unsupported claims
        claim_indicators = [
            "definitely", "certainly", "always", "never", "will",
            "causes", "proves", "guarantees", "all", "every"
        ]
        
        content_lower = post_content.lower()
        for indicator in claim_indicators:
            if indicator in content_lower:
                score -= 0.1
        
        # Boost score for conservative language
        conservative_indicators = [
            "suggests", "indicates", "appears", "might", "could",
            "according to", "based on", "reportedly", "potentially"
        ]
        
        for indicator in conservative_indicators:
            if indicator in content_lower:
                score += 0.05
        
        return max(min(score, 1.0), 0.3)  # Keep within bounds
    
    def _estimate_reading_time(self, content: str) -> int:
        """Estimate reading time in seconds (average 200 words per minute)."""
        word_count = len(content.split())
        reading_time_minutes = word_count / 200
        return max(int(reading_time_minutes * 60), 5)  # Minimum 5 seconds
    
    async def optimize_hashtags(
        self,
        content: str,
        topics: List[ContentTopic],
        platform: PlatformType,
        max_hashtags: int = 5
    ) -> List[str]:
        """Generate optimized hashtags for content."""
        try:
            # Build hashtag optimization prompt
            prompt = f"""
Generate {max_hashtags} optimal hashtags for this {platform.value} post about AI and technology.

Content: {content}
Topics: {', '.join([topic.value for topic in topics])}

Requirements:
- Relevant to AI/ML/technology professional audience
- Mix of popular and niche hashtags
- Appropriate for {platform.value}
- No spaces, special characters except underscores
- Return as JSON array: ["hashtag1", "hashtag2", ...]

Popular AI hashtags to consider: ArtificialIntelligence, MachineLearning, AI, ML, DeepLearning, 
DataScience, TechInnovation, FutureOfWork, AIStartups, MLOps, GenerativeAI, AIEthics
"""
            
            response = await self._call_gemini_api(prompt)
            if not response:
                return self._fallback_hashtags(topics, platform)
            
            # Parse hashtag response
            try:
                if "```json" in response:
                    start = response.find("```json") + 7
                    end = response.find("```", start)
                    json_text = response[start:end].strip()
                else:
                    json_text = response.strip()
                
                hashtags = json.loads(json_text)
                
                if isinstance(hashtags, list):
                    # Clean and validate hashtags
                    clean_hashtags = []
                    for tag in hashtags[:max_hashtags]:
                        if isinstance(tag, str):
                            clean_tag = tag.replace("#", "").replace(" ", "")
                            if clean_tag and len(clean_tag) <= 30:
                                clean_hashtags.append(clean_tag)
                    
                    return clean_hashtags
                
            except (json.JSONDecodeError, KeyError):
                pass
            
            return self._fallback_hashtags(topics, platform)
            
        except Exception as e:
            self.logger.error("Hashtag optimization failed", error=str(e))
            return self._fallback_hashtags(topics, platform)
    
    def _fallback_hashtags(self, topics: List[ContentTopic], platform: PlatformType) -> List[str]:
        """Generate fallback hashtags based on topics."""
        hashtag_map = {
            ContentTopic.ARTIFICIAL_INTELLIGENCE: ["AI", "ArtificialIntelligence"],
            ContentTopic.MACHINE_LEARNING: ["MachineLearning", "ML"],
            ContentTopic.GENERATIVE_AI: ["GenerativeAI", "ChatGPT", "LLM"],
            ContentTopic.AI_STARTUPS: ["AIStartups", "TechStartups", "Innovation"],
            ContentTopic.AI_FUNDING: ["AIFunding", "VentureCapital", "TechInvestment"],
            ContentTopic.AI_RESEARCH: ["AIResearch", "DeepLearning", "DataScience"],
            ContentTopic.AI_ETHICS: ["AIEthics", "ResponsibleAI", "TechEthics"],
            ContentTopic.AI_POLICY: ["AIPolicy", "TechPolicy", "AIGovernance"],
            ContentTopic.AI_CAREERS: ["AICareers", "TechJobs", "FutureOfWork"],
            ContentTopic.AI_TOOLS: ["AITools", "MLOps", "TechTools"],
        }
        
        hashtags = set()
        for topic in topics:
            hashtags.update(hashtag_map.get(topic, []))
        
        # Add platform-specific defaults
        if platform == PlatformType.LINKEDIN:
            hashtags.update(["TechInnovation", "ProfessionalDevelopment"])
        elif platform == PlatformType.TWITTER:
            hashtags.update(["Tech", "Innovation"])
        
        return list(hashtags)[:5]
    
    async def check_connection(self) -> bool:
        """Check if Gemini API connection is working."""
        try:
            test_prompt = "Say 'Hello, PostSync!' in exactly those words."
            response = await self._call_gemini_api(test_prompt)
            return response is not None and "Hello, PostSync!" in response
            
        except Exception as e:
            self.logger.error("Gemini connection check failed", error=str(e))
            return False


# Global Gemini client instance
gemini_client = GeminiClient()


async def generate_content_posts(
    source_content: SourceContent,
    platforms: List[PlatformType],
    user_preferences: ContentPreferences,
    custom_instructions: Optional[str] = None
) -> Dict[PlatformType, GeneratedPost]:
    """Convenience function to generate posts using Gemini."""
    return await gemini_client.generate_posts(
        source_content=source_content,
        platforms=platforms,
        user_preferences=user_preferences,
        custom_instructions=custom_instructions
    )