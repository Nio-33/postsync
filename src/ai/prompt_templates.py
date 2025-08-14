"""
AI Prompt Templates

This module contains standardized prompt templates for different types
of content generation and optimization tasks.
"""

from typing import Dict, List, Optional

from src.models.content import ContentTopic, PlatformType, SourceContent
from src.models.user import ContentPreferences


class PromptTemplates:
    """Collection of AI prompt templates for content generation."""
    
    @staticmethod
    def get_content_generation_prompt(
        source_content: SourceContent,
        platform: PlatformType,
        user_preferences: ContentPreferences,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Get the main content generation prompt."""
        
        platform_specs = PromptTemplates._get_platform_specifications(platform)
        user_context = PromptTemplates._build_user_context(user_preferences)
        content_context = PromptTemplates._build_content_context(source_content)
        
        prompt = f"""
You are an expert social media content creator specializing in AI and technology content for professionals.

TASK: Transform the source content below into an engaging {platform.value} post that will resonate with AI professionals, engineers, and startup founders.

{platform_specs}

{user_context}

{content_context}

CONTENT CREATION GUIDELINES:
1. PROFESSIONAL VALUE: Make it valuable and actionable for AI professionals
2. UNIQUE INSIGHTS: Go beyond summarizing - add insights, implications, or analysis
3. AUTHENTIC VOICE: Sound like a knowledgeable human expert, not a bot
4. FACTUAL ACCURACY: Only make claims supported by the source content
5. ENGAGEMENT: Include elements that encourage professional discussion
6. PLATFORM OPTIMIZATION: Follow the specified format and length requirements

{f"CUSTOM INSTRUCTIONS: {custom_instructions}" if custom_instructions else ""}

RESPONSE FORMAT:
Return your response as a JSON object with this exact structure:
{{
    "content": "Your generated post content here",
    "hashtags": ["hashtag1", "hashtag2", "hashtag3"],
    "mentions": [],
    "reasoning": "Brief explanation of your content strategy and key decisions"
}}

CRITICAL REQUIREMENTS:
- Do NOT include hashtags in the main content text
- Hashtags should be provided separately in the hashtags array
- Stay within the specified character/word limits
- Ensure content is professional and adds value
- Focus on insights relevant to the AI/tech community
- Use conservative language for factual claims
"""
        
        return prompt
    
    @staticmethod
    def get_hashtag_optimization_prompt(
        content: str,
        topics: List[ContentTopic],
        platform: PlatformType,
        max_hashtags: int = 5
    ) -> str:
        """Get prompt for hashtag optimization."""
        
        topic_context = ", ".join([topic.value.replace("-", " ").title() for topic in topics])
        
        return f"""
Generate {max_hashtags} optimal hashtags for this {platform.value} post about AI and technology.

CONTENT: {content}

TOPICS: {topic_context}

REQUIREMENTS:
- Target audience: AI professionals, engineers, startup founders
- Mix of popular and niche hashtags for maximum reach
- Appropriate for {platform.value} platform
- No spaces or special characters (except underscores)
- Professional and industry-relevant
- Include trending AI/ML hashtags when relevant

POPULAR AI HASHTAGS TO CONSIDER:
ArtificialIntelligence, MachineLearning, AI, ML, DeepLearning, DataScience, 
TechInnovation, FutureOfWork, AIStartups, MLOps, GenerativeAI, AIEthics,
TechLeadership, Innovation, DigitalTransformation, AIResearch, Automation

PLATFORM-SPECIFIC CONSIDERATIONS:
{PromptTemplates._get_hashtag_platform_guidance(platform)}

Return as a JSON array: ["hashtag1", "hashtag2", "hashtag3", ...]
"""
    
    @staticmethod
    def get_content_improvement_prompt(
        original_content: str,
        improvement_areas: List[str],
        platform: PlatformType
    ) -> str:
        """Get prompt for improving existing content."""
        
        areas_text = "\n".join([f"- {area}" for area in improvement_areas])
        
        return f"""
Improve the following {platform.value} post based on the specific feedback provided.

ORIGINAL CONTENT:
{original_content}

IMPROVEMENT AREAS:
{areas_text}

REQUIREMENTS:
- Address each improvement area specifically
- Maintain the core message and value proposition
- Keep the professional tone appropriate for AI professionals
- Follow {platform.value} best practices for length and format
- Ensure the improved version is more engaging and effective

Return the improved content as a JSON object:
{{
    "improved_content": "Your improved post content here",
    "hashtags": ["relevant", "hashtags"],
    "changes_made": "Summary of key improvements implemented"
}}
"""
    
    @staticmethod
    def get_a_b_variation_prompt(
        original_content: str,
        variation_type: str,
        platform: PlatformType
    ) -> str:
        """Get prompt for creating A/B test variations."""
        
        variation_strategies = {
            "tone": "Create a variation with a different tone (more casual vs. more formal)",
            "structure": "Reorganize the content with a different structure or flow",
            "hook": "Use a completely different opening hook or attention-grabber",
            "cta": "Change the call-to-action or engagement prompt",
            "length": "Create a significantly shorter or longer version",
            "focus": "Emphasize different aspects or angles of the same topic"
        }
        
        strategy = variation_strategies.get(variation_type, "Create a meaningful variation of the content")
        
        return f"""
Create an A/B test variation of this {platform.value} post.

ORIGINAL CONTENT:
{original_content}

VARIATION STRATEGY: {strategy}

REQUIREMENTS:
- Maintain the same core message and value
- Create a meaningfully different approach that could perform differently
- Keep it appropriate for AI professionals and the {platform.value} platform
- Ensure both versions could reasonably appeal to the target audience
- Maintain factual accuracy and professional quality

Return as JSON:
{{
    "variation_content": "Your A/B variation content here",
    "hashtags": ["relevant", "hashtags"],
    "variation_strategy": "Explanation of how this differs from the original"
}}
"""
    
    @staticmethod
    def get_content_analysis_prompt(content: str, source_url: str) -> str:
        """Get prompt for analyzing content quality and relevance."""
        
        return f"""
Analyze this social media post for quality, relevance, and potential issues.

CONTENT TO ANALYZE:
{content}

SOURCE URL: {source_url}

ANALYSIS AREAS:
1. FACTUAL ACCURACY: Are all claims supported and accurate?
2. RELEVANCE: How relevant is this to AI professionals?
3. ENGAGEMENT POTENTIAL: Will this drive meaningful engagement?
4. PROFESSIONALISM: Is the tone appropriate for business professionals?
5. VALUE PROPOSITION: What value does this provide to readers?
6. POTENTIAL ISSUES: Any concerns or red flags?

Return analysis as JSON:
{{
    "factual_accuracy_score": 0.85,
    "relevance_score": 0.90,
    "engagement_score": 0.75,
    "professionalism_score": 0.95,
    "overall_quality_score": 0.86,
    "key_strengths": ["strength1", "strength2"],
    "areas_for_improvement": ["improvement1", "improvement2"],
    "potential_issues": ["issue1", "issue2"],
    "recommendation": "approve/revise/reject"
}}
"""
    
    @staticmethod
    def _get_platform_specifications(platform: PlatformType) -> str:
        """Get platform-specific requirements and best practices."""
        
        specs = {
            PlatformType.LINKEDIN: """
PLATFORM: LinkedIn
REQUIREMENTS:
- Length: 200-400 words (optimal: 250-300 words)
- Structure: Hook → Insight → Business implication → Engagement question
- Tone: Professional thought leader, industry expert
- Format: Well-structured with line breaks for readability
- Hashtags: 3-5 relevant professional hashtags
- Goal: Drive professional discussion and showcase expertise
""",
            PlatformType.TWITTER: """
PLATFORM: Twitter
REQUIREMENTS:
- Length: 220-280 characters (optimal: 240-260 characters)
- Structure: Hook → Key insight → Call-to-action
- Tone: Conversational expert, accessible but credible
- Format: Concise and punchy, potential for threading if needed
- Hashtags: 1-2 strategic hashtags maximum
- Goal: Maximize engagement and retweets
""",
            PlatformType.INSTAGRAM: """
PLATFORM: Instagram
REQUIREMENTS:
- Length: 150-300 words
- Structure: Visual hook → Story/insight → Call-to-action
- Tone: Visual storytelling, accessible expertise
- Format: Engaging narrative with emoji integration
- Hashtags: 5-10 mix of popular and niche hashtags
- Goal: Visual engagement and community building
""",
            PlatformType.YOUTUBE: """
PLATFORM: YouTube (Description)
REQUIREMENTS:
- Length: 200-500 words
- Structure: Video summary → Key points → Links/resources
- Tone: Educational and comprehensive
- Format: Structured with timestamps and links
- Hashtags: 3-5 relevant hashtags
- Goal: Support video content and drive engagement
"""
        }
        
        return specs.get(platform, specs[PlatformType.LINKEDIN])
    
    @staticmethod
    def _build_user_context(preferences: ContentPreferences) -> str:
        """Build user context section for prompts."""
        
        topics_list = ", ".join([topic.replace("-", " ").title() for topic in preferences.topics])
        platforms_list = ", ".join([platform.value for platform in preferences.platforms])
        
        return f"""
USER PROFILE:
- Content tone preference: {preferences.tone}
- Primary topics of interest: {topics_list}
- Active platforms: {platforms_list}
- Target audience: AI professionals, engineers, and startup founders
- Posting frequency: {preferences.posts_per_day} posts per day
- Timezone: {preferences.posting_timezone}
"""
    
    @staticmethod
    def _build_content_context(source_content: SourceContent) -> str:
        """Build source content context section for prompts."""
        
        topics_text = ", ".join([topic.value.replace("-", " ").title() for topic in source_content.topics])
        
        return f"""
SOURCE CONTENT:
- Title: {source_content.title}
- Description: {source_content.description or "No description available"}
- URL: {source_content.url}
- Author: {source_content.author or "Unknown"}
- Published: {source_content.published_at.strftime("%Y-%m-%d")}
- Topics: {topics_text}
- Engagement Score: {source_content.engagement_score:.2f}/1.0
- Sentiment: {source_content.sentiment or "neutral"}
- Comments: {source_content.comments_count or 0}
- Upvotes/Likes: {source_content.upvotes or 0}
"""
    
    @staticmethod
    def _get_hashtag_platform_guidance(platform: PlatformType) -> str:
        """Get platform-specific hashtag guidance."""
        
        guidance = {
            PlatformType.LINKEDIN: """
- Use professional, industry-specific hashtags
- Mix of broad (#AI, #Innovation) and specific (#MLOps, #AIEthics) hashtags
- Avoid overly casual or trendy hashtags
- Focus on business and professional development themes
""",
            PlatformType.TWITTER: """
- Use 1-2 hashtags maximum for best engagement
- Include trending hashtags when relevant
- Mix popular and niche hashtags for reach
- Keep hashtags short and memorable
""",
            PlatformType.INSTAGRAM: """
- Use 5-10 hashtags for optimal reach
- Mix popular, moderately popular, and niche hashtags
- Include community-specific hashtags
- Consider hashtag popularity and competition
""",
            PlatformType.YOUTUBE: """
- Use 3-5 descriptive hashtags
- Focus on searchable terms
- Include category-specific hashtags
- Support video discoverability
"""
        }
        
        return guidance.get(platform, guidance[PlatformType.LINKEDIN])
    
    @staticmethod
    def get_fact_checking_prompt(content: str, source_url: str) -> str:
        """Get prompt for fact-checking generated content."""
        
        return f"""
Fact-check this social media post against its source material and general knowledge.

CONTENT TO CHECK:
{content}

SOURCE URL: {source_url}

FACT-CHECKING CRITERIA:
1. Are all factual claims accurate and verifiable?
2. Are any statistics or numbers correctly stated?
3. Are company names, product names, and proper nouns correct?
4. Are any dates, timelines, or temporal claims accurate?
5. Are technical terms and concepts used correctly?
6. Are any quotes or attributions accurate?
7. Are implications and conclusions reasonable based on the source?

Return fact-check results as JSON:
{{
    "overall_accuracy_score": 0.95,
    "factual_issues": [
        {{
            "issue": "Description of the factual error",
            "severity": "high/medium/low",
            "correction": "Suggested correction"
        }}
    ],
    "verification_status": "verified/needs_review/inaccurate",
    "confidence_level": 0.90,
    "recommendations": ["suggestion1", "suggestion2"]
}}
"""
    
    @staticmethod
    def get_sentiment_analysis_prompt(content: str) -> str:
        """Get prompt for analyzing content sentiment."""
        
        return f"""
Analyze the sentiment and emotional tone of this social media content.

CONTENT: {content}

ANALYSIS DIMENSIONS:
1. Overall sentiment (positive/negative/neutral)
2. Professional appropriateness
3. Emotional tone and energy level
4. Potential audience reaction
5. Brand safety considerations

Return sentiment analysis as JSON:
{{
    "overall_sentiment": "positive/negative/neutral",
    "sentiment_score": 0.75,
    "emotional_tone": "excited/professional/cautious/etc",
    "energy_level": "high/medium/low",
    "professional_appropriateness": 0.90,
    "brand_safety_score": 0.95,
    "potential_reactions": ["reaction1", "reaction2"],
    "recommendations": ["suggestion1", "suggestion2"]
}}
"""


# Global instance for easy access
prompt_templates = PromptTemplates()