"""
Content Optimization Module

This module provides content optimization features including:
- A/B testing for different content variations
- Performance-based content optimization
- Best posting time recommendations
- Content scoring and quality assessment
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

import structlog

from src.models.analytics import PostAnalytics
from src.models.content import ContentTopic, GeneratedPost, PlatformType, SourceContent
from src.models.user import ContentPreferences


class ContentOptimizer:
    """Content optimization and performance analysis."""
    
    def __init__(self):
        """Initialize content optimizer."""
        self.logger = structlog.get_logger(__name__)
        
        # Fact-checking configuration
        self.fact_check_config = {
            "claim_indicators": [
                "claims", "states", "reports", "announces", "reveals", "confirms",
                "according to", "study shows", "research indicates", "data suggests"
            ],
            "red_flag_terms": [
                "definitely will", "guaranteed to", "always", "never fails",
                "100% accurate", "completely safe", "impossible to", "certain that"
            ],
            "conservative_replacements": {
                "will definitely": "may",
                "certainly will": "could",
                "always": "often",
                "never": "rarely",
                "guarantees": "suggests",
                "proves": "indicates",
                "definitely": "likely"
            }
        }
    
    async def optimize_posting_times(
        self,
        user_analytics: List[PostAnalytics],
        platform: PlatformType,
        timezone: str = "UTC"
    ) -> Dict[str, List[Tuple[int, float]]]:
        """
        Analyze historical data to find optimal posting times.
        
        Args:
            user_analytics: Historical post analytics data
            platform: Platform to optimize for
            timezone: User's timezone
            
        Returns:
            Dictionary with optimal times by day of week
        """
        self.logger.info("Optimizing posting times", platform=platform, timezone=timezone)
        
        try:
            # Group analytics by day of week and hour
            performance_by_time = {}
            
            for analytics in user_analytics:
                if analytics.platform != platform:
                    continue
                
                # Extract posting time (would need to be stored with posts)
                post_time = analytics.first_tracked_at
                day_of_week = post_time.strftime("%A")
                hour = post_time.hour
                
                if day_of_week not in performance_by_time:
                    performance_by_time[day_of_week] = {}
                
                if hour not in performance_by_time[day_of_week]:
                    performance_by_time[day_of_week][hour] = []
                
                performance_by_time[day_of_week][hour].append(analytics.engagement_rate)
            
            # Calculate average performance for each time slot
            optimal_times = {}
            for day, hours in performance_by_time.items():
                day_optimal = []
                
                for hour, engagement_rates in hours.items():
                    if len(engagement_rates) >= 2:  # Need minimum data points
                        avg_engagement = sum(engagement_rates) / len(engagement_rates)
                        day_optimal.append((hour, avg_engagement))
                
                # Sort by engagement rate and take top times
                day_optimal.sort(key=lambda x: x[1], reverse=True)
                optimal_times[day] = day_optimal[:3]  # Top 3 times per day
            
            self.logger.info(
                "Posting time optimization completed",
                platform=platform,
                days_analyzed=len(optimal_times)
            )
            
            return optimal_times
            
        except Exception as e:
            self.logger.error("Posting time optimization failed", error=str(e))
            return self._get_default_posting_times(platform)
    
    def _get_default_posting_times(self, platform: PlatformType) -> Dict[str, List[Tuple[int, float]]]:
        """Get default optimal posting times based on platform research."""
        if platform == PlatformType.LINKEDIN:
            # LinkedIn optimal times (business hours, weekdays)
            return {
                "Monday": [(9, 0.85), (13, 0.80), (17, 0.75)],
                "Tuesday": [(10, 0.90), (14, 0.85), (16, 0.80)],
                "Wednesday": [(11, 0.88), (15, 0.83), (17, 0.78)],
                "Thursday": [(9, 0.87), (13, 0.82), (16, 0.77)],
                "Friday": [(10, 0.75), (14, 0.70), (16, 0.65)],
                "Saturday": [(11, 0.60), (15, 0.55)],
                "Sunday": [(19, 0.65), (20, 0.60)]
            }
        elif platform == PlatformType.TWITTER:
            # Twitter optimal times (more spread throughout day)
            return {
                "Monday": [(9, 0.80), (15, 0.85), (21, 0.75)],
                "Tuesday": [(9, 0.82), (15, 0.87), (21, 0.77)],
                "Wednesday": [(9, 0.85), (15, 0.90), (21, 0.80)],
                "Thursday": [(9, 0.83), (15, 0.88), (21, 0.78)],
                "Friday": [(9, 0.75), (15, 0.80), (21, 0.85)],
                "Saturday": [(11, 0.70), (16, 0.75), (20, 0.80)],
                "Sunday": [(12, 0.75), (17, 0.80), (19, 0.85)]
            }
        else:
            # Generic default
            return {
                "Monday": [(9, 0.75), (13, 0.80), (17, 0.75)],
                "Tuesday": [(9, 0.75), (13, 0.80), (17, 0.75)],
                "Wednesday": [(9, 0.75), (13, 0.80), (17, 0.75)],
                "Thursday": [(9, 0.75), (13, 0.80), (17, 0.75)],
                "Friday": [(9, 0.70), (13, 0.75), (17, 0.70)],
                "Saturday": [(11, 0.65), (16, 0.70)],
                "Sunday": [(12, 0.65), (18, 0.70)]
            }
    
    async def score_content_quality(
        self,
        generated_post: GeneratedPost,
        source_content: SourceContent,
        user_preferences: ContentPreferences
    ) -> Dict[str, float]:
        """
        Score content quality across multiple dimensions.
        
        Args:
            generated_post: Generated post to score
            source_content: Original source content
            user_preferences: User's content preferences
            
        Returns:
            Dictionary with quality scores
        """
        self.logger.debug("Scoring content quality", platform=generated_post.platform)
        
        try:
            scores = {
                "relevance": await self._score_relevance(generated_post, source_content),
                "readability": self._score_readability(generated_post),
                "engagement_potential": self._score_engagement_potential(generated_post),
                "brand_alignment": self._score_brand_alignment(generated_post, user_preferences),
                "platform_optimization": self._score_platform_optimization(generated_post),
                "factual_accuracy": self._score_factual_accuracy(generated_post, source_content)
            }
            
            # Calculate overall score
            weights = {
                "relevance": 0.25,
                "readability": 0.15,
                "engagement_potential": 0.20,
                "brand_alignment": 0.15,
                "platform_optimization": 0.15,
                "factual_accuracy": 0.10
            }
            
            overall_score = sum(scores[key] * weights[key] for key in weights)
            scores["overall"] = overall_score
            
            return scores
            
        except Exception as e:
            self.logger.error("Content quality scoring failed", error=str(e))
            return {"overall": 0.5}
    
    async def _score_relevance(self, generated_post: GeneratedPost, source_content: SourceContent) -> float:
        """Score content relevance to source material."""
        # Basic keyword overlap analysis
        post_words = set(generated_post.content.lower().split())
        source_words = set(
            (source_content.title + " " + (source_content.description or "")).lower().split()
        )
        
        if not source_words:
            return 0.5
        
        overlap = len(post_words.intersection(source_words))
        return min(overlap / max(len(source_words) * 0.3, 1), 1.0)
    
    def _score_readability(self, generated_post: GeneratedPost) -> float:
        """Score content readability and clarity."""
        content = generated_post.content
        
        # Basic readability metrics
        word_count = len(content.split())
        sentence_count = content.count('.') + content.count('!') + content.count('?')
        
        if sentence_count == 0:
            return 0.3
        
        avg_words_per_sentence = word_count / sentence_count
        
        # Optimal range: 15-20 words per sentence
        if 15 <= avg_words_per_sentence <= 20:
            readability_score = 1.0
        elif 10 <= avg_words_per_sentence < 15 or 20 < avg_words_per_sentence <= 25:
            readability_score = 0.8
        else:
            readability_score = 0.6
        
        # Bonus for proper punctuation and structure
        if any(char in content for char in ['.', '!', '?']):
            readability_score += 0.1
        
        # Penalty for excessive capitalization
        if sum(1 for c in content if c.isupper()) / len(content) > 0.1:
            readability_score -= 0.2
        
        return min(max(readability_score, 0.1), 1.0)
    
    def _score_engagement_potential(self, generated_post: GeneratedPost) -> float:
        """Score potential for user engagement."""
        content = generated_post.content.lower()
        
        score = 0.5  # Base score
        
        # Positive engagement indicators
        engagement_words = [
            "what do you think", "thoughts?", "agree?", "experience",
            "share", "comment", "question", "opinion", "perspective"
        ]
        
        for phrase in engagement_words:
            if phrase in content:
                score += 0.1
        
        # Question marks encourage engagement
        question_count = generated_post.content.count('?')
        score += min(question_count * 0.1, 0.2)
        
        # Hashtags can increase discoverability
        hashtag_count = len(generated_post.hashtags)
        if 1 <= hashtag_count <= 5:
            score += 0.1
        elif hashtag_count > 5:
            score -= 0.1  # Too many hashtags can hurt engagement
        
        # Platform-specific adjustments
        if generated_post.platform == PlatformType.LINKEDIN:
            # LinkedIn favors professional insights and discussions
            professional_indicators = [
                "insight", "analysis", "strategy", "leadership", "innovation",
                "growth", "development", "professional", "industry"
            ]
            for word in professional_indicators:
                if word in content:
                    score += 0.05
        
        elif generated_post.platform == PlatformType.TWITTER:
            # Twitter favors concise, punchy content
            if len(generated_post.content) < 200:
                score += 0.1
            
            # Trending topics and timely content
            trending_indicators = [
                "breaking", "new", "just", "now", "today", "latest",
                "trending", "viral", "hot"
            ]
            for word in trending_indicators:
                if word in content:
                    score += 0.05
        
        return min(score, 1.0)
    
    def _score_brand_alignment(self, generated_post: GeneratedPost, user_preferences: ContentPreferences) -> float:
        """Score alignment with user's brand and preferences."""
        content = generated_post.content.lower()
        
        score = 0.7  # Base score assuming good alignment
        
        # Check tone alignment
        tone_keywords = {
            "professional": [
                "industry", "business", "strategy", "analysis", "development",
                "innovation", "leadership", "expertise", "solution"
            ],
            "casual": [
                "cool", "awesome", "amazing", "fun", "easy", "simple",
                "love", "like", "enjoy", "exciting"
            ],
            "expert": [
                "research", "study", "evidence", "data", "analysis",
                "methodology", "framework", "technical", "advanced"
            ]
        }
        
        preferred_tone = user_preferences.tone.lower()
        if preferred_tone in tone_keywords:
            tone_words = tone_keywords[preferred_tone]
            tone_matches = sum(1 for word in tone_words if word in content)
            score += min(tone_matches * 0.02, 0.2)
        
        # Check topic alignment
        user_topics = [topic.lower().replace("-", " ") for topic in user_preferences.topics]
        for topic in user_topics:
            if topic in content:
                score += 0.05
        
        # Platform preference alignment
        if generated_post.platform in user_preferences.platforms:
            score += 0.1
        else:
            score -= 0.2
        
        return min(max(score, 0.1), 1.0)
    
    def _score_platform_optimization(self, generated_post: GeneratedPost) -> float:
        """Score optimization for specific platform requirements."""
        score = 0.5  # Base score
        
        if generated_post.platform == PlatformType.LINKEDIN:
            # LinkedIn optimization factors
            content_length = len(generated_post.content)
            
            # Optimal length: 200-400 words
            if 200 <= content_length <= 400:
                score += 0.3
            elif 150 <= content_length < 200 or 400 < content_length <= 500:
                score += 0.2
            elif content_length < 150:
                score += 0.1
            
            # Professional hashtags
            if 3 <= len(generated_post.hashtags) <= 5:
                score += 0.2
            
            # Line breaks for readability
            if "\n" in generated_post.content:
                score += 0.1
        
        elif generated_post.platform == PlatformType.TWITTER:
            # Twitter optimization factors
            content_length = len(generated_post.content)
            
            # Optimal length: 220-280 characters
            if 220 <= content_length <= 280:
                score += 0.4
            elif 180 <= content_length < 220:
                score += 0.3
            elif content_length > 280:
                score -= 0.3  # Over limit
            
            # Hashtag optimization
            if 1 <= len(generated_post.hashtags) <= 2:
                score += 0.2
            elif len(generated_post.hashtags) > 2:
                score -= 0.1
            
            # Twitter-specific elements
            if "@" in generated_post.content or len(generated_post.mentions) > 0:
                score += 0.1
        
        return min(max(score, 0.1), 1.0)
    
    def _score_factual_accuracy(self, generated_post: GeneratedPost, source_content: SourceContent) -> float:
        """Score factual accuracy and conservative claims."""
        content = generated_post.content.lower()
        
        score = 0.8  # Base high score for conservative generation
        
        # Check for unsupported strong claims
        strong_claims = [
            "definitely", "certainly", "always", "never", "all", "every",
            "guarantees", "proves", "causes", "will happen", "must"
        ]
        
        for claim in strong_claims:
            if claim in content:
                score -= 0.1
        
        # Bonus for conservative language
        conservative_language = [
            "suggests", "indicates", "appears", "might", "could", "may",
            "according to", "based on", "reportedly", "potentially", "likely"
        ]
        
        for phrase in conservative_language:
            if phrase in content:
                score += 0.05
        
        # Check for source attribution
        if any(word in content for word in ["source", "according", "reports", "study"]):
            score += 0.1
        
        return min(max(score, 0.1), 1.0)
    
    async def suggest_improvements(
        self,
        generated_post: GeneratedPost,
        quality_scores: Dict[str, float],
        user_preferences: ContentPreferences
    ) -> List[str]:
        """
        Suggest specific improvements based on quality scores.
        
        Args:
            generated_post: Generated post to improve
            quality_scores: Quality assessment scores
            user_preferences: User's content preferences
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        try:
            # Relevance improvements
            if quality_scores.get("relevance", 0) < 0.7:
                suggestions.append(
                    "Consider adding more specific details from the source content to improve relevance."
                )
            
            # Readability improvements
            if quality_scores.get("readability", 0) < 0.7:
                if len(generated_post.content.split()) / generated_post.content.count('.') > 25:
                    suggestions.append("Break up long sentences for better readability.")
                if generated_post.content.count('\n') == 0 and len(generated_post.content) > 200:
                    suggestions.append("Add line breaks to improve content structure.")
            
            # Engagement improvements
            if quality_scores.get("engagement_potential", 0) < 0.7:
                if "?" not in generated_post.content:
                    suggestions.append("Add a question to encourage audience engagement.")
                if not any(word in generated_post.content.lower() for word in ["what", "how", "why", "when"]):
                    suggestions.append("Include thought-provoking questions or discussion prompts.")
            
            # Platform optimization
            if quality_scores.get("platform_optimization", 0) < 0.7:
                if generated_post.platform == PlatformType.LINKEDIN:
                    if len(generated_post.content) < 200:
                        suggestions.append("Expand content to 200-400 words for optimal LinkedIn performance.")
                    if len(generated_post.hashtags) < 3:
                        suggestions.append("Add 3-5 relevant professional hashtags for better discoverability.")
                
                elif generated_post.platform == PlatformType.TWITTER:
                    if len(generated_post.content) > 280:
                        suggestions.append("Shorten content to fit Twitter's 280-character limit.")
                    if len(generated_post.hashtags) > 2:
                        suggestions.append("Reduce hashtags to 1-2 for better Twitter engagement.")
            
            # Brand alignment
            if quality_scores.get("brand_alignment", 0) < 0.7:
                suggestions.append(
                    f"Adjust tone to better match your preferred '{user_preferences.tone}' style."
                )
            
            # Factual accuracy
            if quality_scores.get("factual_accuracy", 0) < 0.8:
                suggestions.append("Use more conservative language and avoid making strong unsupported claims.")
            
            return suggestions
            
        except Exception as e:
            self.logger.error("Failed to generate improvement suggestions", error=str(e))
            return ["Consider reviewing content for clarity and engagement potential."]
    
    async def a_b_test_content(
        self,
        content_variations: List[GeneratedPost],
        test_duration_hours: int = 24,
        test_audience_split: float = 0.5
    ) -> Dict[str, any]:
        """
        Set up A/B test for content variations.
        
        Args:
            content_variations: Different versions to test
            test_duration_hours: How long to run the test
            test_audience_split: Percentage split for test (0.0-1.0)
            
        Returns:
            A/B test configuration
        """
        self.logger.info("Setting up A/B test", variations=len(content_variations))
        
        try:
            if len(content_variations) < 2:
                raise ValueError("Need at least 2 content variations for A/B testing")
            
            test_config = {
                "test_id": f"test_{int(datetime.utcnow().timestamp())}",
                "variations": [
                    {
                        "id": f"variation_{i}",
                        "content": variation,
                        "audience_split": test_audience_split if i == 0 else 1 - test_audience_split,
                    }
                    for i, variation in enumerate(content_variations[:2])  # Limit to 2 variations
                ],
                "start_time": datetime.utcnow(),
                "end_time": datetime.utcnow() + timedelta(hours=test_duration_hours),
                "metrics_to_track": ["impressions", "likes", "comments", "shares", "clicks"],
                "status": "active"
            }
            
            return test_config
            
        except Exception as e:
            self.logger.error("A/B test setup failed", error=str(e))
            return {}
    
    async def analyze_test_results(
        self,
        test_config: Dict,
        results_data: List[PostAnalytics]
    ) -> Dict[str, any]:
        """
        Analyze A/B test results and determine winner.
        
        Args:
            test_config: Test configuration
            results_data: Analytics data for test variations
            
        Returns:
            Test analysis results
        """
        self.logger.info("Analyzing A/B test results", test_id=test_config.get("test_id"))
        
        try:
            # Group results by variation
            variation_results = {}
            for analytics in results_data:
                # Would need to match analytics to variations based on post metadata
                variation_id = "variation_0"  # Placeholder logic
                
                if variation_id not in variation_results:
                    variation_results[variation_id] = []
                variation_results[variation_id].append(analytics)
            
            # Calculate performance metrics for each variation
            performance_summary = {}
            for variation_id, analytics_list in variation_results.items():
                if not analytics_list:
                    continue
                
                total_impressions = sum(a.impressions for a in analytics_list)
                total_engagements = sum(a.total_engagements for a in analytics_list)
                avg_engagement_rate = sum(a.engagement_rate for a in analytics_list) / len(analytics_list)
                
                performance_summary[variation_id] = {
                    "total_impressions": total_impressions,
                    "total_engagements": total_engagements,
                    "average_engagement_rate": avg_engagement_rate,
                    "post_count": len(analytics_list)
                }
            
            # Determine winner
            winner = max(
                performance_summary.keys(),
                key=lambda v: performance_summary[v]["average_engagement_rate"]
            ) if performance_summary else None
            
            analysis = {
                "test_id": test_config.get("test_id"),
                "winner": winner,
                "performance_summary": performance_summary,
                "confidence_level": self._calculate_confidence(performance_summary),
                "recommendations": self._generate_test_recommendations(performance_summary),
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error("A/B test analysis failed", error=str(e))
            return {}
    
    def _calculate_confidence(self, performance_summary: Dict) -> float:
        """Calculate statistical confidence in A/B test results."""
        # Simplified confidence calculation
        if len(performance_summary) < 2:
            return 0.0
        
        values = [v["average_engagement_rate"] for v in performance_summary.values()]
        if len(values) < 2:
            return 0.0
        
        # Simple difference ratio as confidence measure
        max_val = max(values)
        min_val = min(values)
        
        if min_val == 0:
            return 0.9 if max_val > 0 else 0.0
        
        confidence = min((max_val - min_val) / min_val, 0.95)
        return max(confidence, 0.1)
    
    def _generate_test_recommendations(self, performance_summary: Dict) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        if not performance_summary:
            return ["Insufficient data for recommendations."]
        
        # Find best and worst performing variations
        sorted_variations = sorted(
            performance_summary.items(),
            key=lambda x: x[1]["average_engagement_rate"],
            reverse=True
        )
        
        if len(sorted_variations) >= 2:
            best = sorted_variations[0]
            worst = sorted_variations[-1]
            
            improvement = ((best[1]["average_engagement_rate"] - worst[1]["average_engagement_rate"]) 
                          / worst[1]["average_engagement_rate"] * 100)
            
            recommendations.append(
                f"Variation {best[0]} performed {improvement:.1f}% better than {worst[0]}."
            )
            
            recommendations.append(
                "Consider using the winning variation's approach for future content."
            )
        
        return recommendations
    
    async def comprehensive_fact_check(
        self,
        generated_post: GeneratedPost,
        source_content: SourceContent
    ) -> Dict[str, Union[float, List[str], bool]]:
        """
        Comprehensive fact-checking pipeline for generated content.
        
        Args:
            generated_post: Generated post to fact-check
            source_content: Original source content for verification
            
        Returns:
            Fact-check results with score, issues, and pass/fail status
        """
        self.logger.info("Starting comprehensive fact-check", platform=generated_post.platform)
        
        try:
            # Multi-layer fact-checking pipeline
            results = {
                "overall_score": 0.0,
                "passes_fact_check": False,
                "issues_found": [],
                "warnings": [],
                "suggestions": [],
                "confidence_level": 0.0
            }
            
            # Layer 1: Source attribution and claims verification
            attribution_score = await self._verify_source_attribution(generated_post, source_content)
            
            # Layer 2: Conservative language assessment
            conservative_score = self._assess_conservative_language(generated_post)
            
            # Layer 3: Claim substantiation check
            substantiation_score = await self._verify_claim_substantiation(generated_post, source_content)
            
            # Layer 4: Hallucination detection
            hallucination_score = await self._detect_hallucinations(generated_post, source_content)
            
            # Layer 5: Temporal accuracy check
            temporal_score = self._verify_temporal_accuracy(generated_post, source_content)
            
            # Calculate weighted overall score
            weights = {
                "attribution": 0.15,
                "conservative": 0.25,
                "substantiation": 0.30,
                "hallucination": 0.25,
                "temporal": 0.05
            }
            
            overall_score = (
                attribution_score * weights["attribution"] +
                conservative_score * weights["conservative"] +
                substantiation_score * weights["substantiation"] +
                hallucination_score * weights["hallucination"] +
                temporal_score * weights["temporal"]
            )
            
            results["overall_score"] = overall_score
            results["passes_fact_check"] = overall_score >= 0.95  # 95% threshold for PRD 99.8% target
            results["confidence_level"] = min(overall_score + 0.05, 1.0)
            
            # Generate improvement suggestions if score is low
            if overall_score < 0.95:
                results["suggestions"] = await self._generate_fact_check_suggestions(
                    generated_post, source_content, {
                        "attribution": attribution_score,
                        "conservative": conservative_score,
                        "substantiation": substantiation_score,
                        "hallucination": hallucination_score,
                        "temporal": temporal_score
                    }
                )
            
            return results
            
        except Exception as e:
            self.logger.error("Comprehensive fact-check failed", error=str(e))
            return {
                "overall_score": 0.0,
                "passes_fact_check": False,
                "issues_found": ["Fact-check system error"],
                "warnings": [],
                "suggestions": ["Manual review required due to system error"],
                "confidence_level": 0.0
            }
    
    async def _verify_source_attribution(
        self, 
        generated_post: GeneratedPost, 
        source_content: SourceContent
    ) -> float:
        """Verify proper source attribution and linkage."""
        score = 0.8  # Base score
        
        post_content = generated_post.content.lower()
        
        # Check for source attribution
        attribution_indicators = [
            "source:", "according to", "via", "from", "reports", 
            "study by", "research from", "data from"
        ]
        
        has_attribution = any(indicator in post_content for indicator in attribution_indicators)
        if has_attribution:
            score += 0.15
        
        # Check for URL preservation (if applicable)
        if source_content.url:
            # In a real implementation, we'd check if the URL is included or referenced
            score += 0.05
        
        return min(score, 1.0)
    
    def _assess_conservative_language(self, generated_post: GeneratedPost) -> float:
        """Assess use of conservative, non-absolute language."""
        score = 0.7  # Base score
        
        content = generated_post.content.lower()
        
        # Check for problematic absolute statements
        red_flags = self.fact_check_config["red_flag_terms"]
        red_flag_count = sum(1 for flag in red_flags if flag in content)
        
        # Penalize absolute statements
        score -= min(red_flag_count * 0.2, 0.5)
        
        # Reward conservative language
        conservative_terms = [
            "appears to", "suggests", "indicates", "may", "might", "could",
            "potentially", "reportedly", "according to", "based on", "likely"
        ]
        
        conservative_count = sum(1 for term in conservative_terms if term in content)
        score += min(conservative_count * 0.05, 0.2)
        
        # Check for proper qualifying language around claims
        claims = re.findall(r'[A-Z][^.!?]*(?:claims?|states?|reports?|announces?)[^.!?]*[.!?]', 
                           generated_post.content)
        
        for claim in claims:
            if any(qualifier in claim.lower() for qualifier in conservative_terms):
                score += 0.05
        
        return min(max(score, 0.1), 1.0)
    
    async def _verify_claim_substantiation(
        self, 
        generated_post: GeneratedPost, 
        source_content: SourceContent
    ) -> float:
        """Verify that claims in post are substantiated by source content."""
        score = 0.8  # Base score assuming good alignment
        
        # Extract potential claims from generated content
        claims = self._extract_claims(generated_post.content)
        
        if not claims:
            return score  # No claims to verify
        
        # Compare claims against source content
        source_text = f"{source_content.title} {source_content.description or ''}".lower()
        
        unsubstantiated_claims = 0
        total_claims = len(claims)
        
        for claim in claims:
            claim_words = set(claim.lower().split())
            source_words = set(source_text.split())
            
            # Calculate overlap between claim and source
            overlap = len(claim_words.intersection(source_words))
            overlap_ratio = overlap / max(len(claim_words), 1)
            
            # If claim has low overlap with source, it may be unsubstantiated
            if overlap_ratio < 0.3:
                unsubstantiated_claims += 1
        
        if total_claims > 0:
            substantiation_ratio = 1 - (unsubstantiated_claims / total_claims)
            score = score * substantiation_ratio
        
        return max(score, 0.1)
    
    def _extract_claims(self, content: str) -> List[str]:
        """Extract potential factual claims from content."""
        claims = []
        
        # Look for sentences with claim indicators
        sentences = re.split(r'[.!?]+', content)
        
        claim_patterns = [
            r'.*\b(?:claims?|states?|reports?|announces?|reveals?|confirms?)\b.*',
            r'.*\b(?:study shows?|research indicates?|data suggests?)\b.*',
            r'.*\b(?:according to|based on)\b.*',
            r'.*\b(?:will|would|could|may|might)\s+(?:increase|decrease|improve|reduce)\b.*'
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Ignore very short sentences
                for pattern in claim_patterns:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        claims.append(sentence)
                        break
        
        return claims
    
    async def _detect_hallucinations(
        self, 
        generated_post: GeneratedPost, 
        source_content: SourceContent
    ) -> float:
        """Detect potential AI hallucinations or unsupported information."""
        score = 0.9  # High base score, reduce for hallucinations
        
        post_content = generated_post.content.lower()
        source_text = f"{source_content.title} {source_content.description or ''}".lower()
        
        # Check for specific numbers, dates, or names that might be hallucinated
        hallucination_indicators = [
            # Specific numbers that might be made up
            r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion))?',
            r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?%',
            r'\b(?:19|20)\d{2}\b',  # Years
            # Specific company valuations or metrics
            r'\b\d+(?:\.\d+)?\s*(?:million|billion|trillion)\s*(?:users|customers|employees)',
        ]
        
        post_specific_data = []
        for pattern in hallucination_indicators:
            matches = re.findall(pattern, post_content, re.IGNORECASE)
            post_specific_data.extend(matches)
        
        # Check if specific data points from post appear in source
        unsupported_data = 0
        for data_point in post_specific_data:
            if data_point.lower() not in source_text:
                unsupported_data += 1
        
        if post_specific_data:
            hallucination_ratio = unsupported_data / len(post_specific_data)
            score -= hallucination_ratio * 0.5
        
        # Check for common hallucination patterns
        hallucination_phrases = [
            "recent study by", "new research from", "according to experts",
            "industry insiders say", "leaked documents", "confidential sources"
        ]
        
        for phrase in hallucination_phrases:
            if phrase in post_content and phrase not in source_text:
                score -= 0.1
        
        return max(score, 0.1)
    
    def _verify_temporal_accuracy(
        self, 
        generated_post: GeneratedPost, 
        source_content: SourceContent
    ) -> float:
        """Verify temporal accuracy and appropriate tense usage."""
        score = 0.9  # High base score
        
        # Check publication recency
        hours_since_publication = (datetime.utcnow() - source_content.published_at).total_seconds() / 3600
        
        post_content = generated_post.content.lower()
        
        # Check for inappropriate temporal language
        if hours_since_publication > 24:  # Content is more than a day old
            if any(term in post_content for term in ["just announced", "breaking", "just released", "today"]):
                score -= 0.3
        
        if hours_since_publication > 168:  # Content is more than a week old
            if any(term in post_content for term in ["this week", "recently announced", "latest"]):
                score -= 0.2
        
        # Check for future tense claims about past events
        future_patterns = [
            r'will\s+(?:announce|release|launch|reveal)',
            r'is\s+going\s+to\s+(?:announce|release|launch)'
        ]
        
        for pattern in future_patterns:
            if re.search(pattern, post_content):
                score -= 0.2
        
        return max(score, 0.1)
    
    async def _generate_fact_check_suggestions(
        self,
        generated_post: GeneratedPost,
        source_content: SourceContent,
        component_scores: Dict[str, float]
    ) -> List[str]:
        """Generate specific suggestions to improve fact-check score."""
        suggestions = []
        
        # Attribution suggestions
        if component_scores["attribution"] < 0.9:
            suggestions.append("Add clear source attribution (e.g., 'According to [source]')")
            if source_content.url:
                suggestions.append("Consider including or referencing the source URL")
        
        # Conservative language suggestions
        if component_scores["conservative"] < 0.8:
            suggestions.append("Use more conservative language - replace absolute statements with qualified ones")
            suggestions.append("Consider phrases like 'appears to', 'suggests', or 'may indicate'")
        
        # Substantiation suggestions
        if component_scores["substantiation"] < 0.9:
            suggestions.append("Ensure all claims are directly supported by the source material")
            suggestions.append("Remove or qualify statements that go beyond what the source states")
        
        # Hallucination suggestions
        if component_scores["hallucination"] < 0.9:
            suggestions.append("Verify all specific numbers, dates, and names against the source")
            suggestions.append("Remove any details not explicitly mentioned in the source")
        
        # Temporal suggestions
        if component_scores["temporal"] < 0.9:
            hours_old = (datetime.utcnow() - source_content.published_at).total_seconds() / 3600
            if hours_old > 24:
                suggestions.append("Adjust temporal language to reflect the age of the source content")
        
        return suggestions
    
    async def auto_correct_content(
        self,
        generated_post: GeneratedPost,
        fact_check_results: Dict
    ) -> GeneratedPost:
        """
        Automatically correct common fact-checking issues.
        
        Args:
            generated_post: Original generated post
            fact_check_results: Results from fact-checking
            
        Returns:
            Corrected version of the post
        """
        corrected_content = generated_post.content
        
        try:
            # Apply conservative language replacements
            for absolute_term, conservative_term in self.fact_check_config["conservative_replacements"].items():
                corrected_content = re.sub(
                    r'\b' + re.escape(absolute_term) + r'\b',
                    conservative_term,
                    corrected_content,
                    flags=re.IGNORECASE
                )
            
            # Remove overly specific claims that might be hallucinated
            red_flag_patterns = [
                r'exactly \$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion))?',
                r'precisely \d+(?:\.\d+)?%',
                r'confirmed \d+ (?:users|customers|employees)'
            ]
            
            for pattern in red_flag_patterns:
                corrected_content = re.sub(pattern, lambda m: m.group(0).replace('exactly ', 'approximately ').replace('precisely ', 'about ').replace('confirmed ', 'reported '), corrected_content, flags=re.IGNORECASE)
            
            # Create corrected post
            corrected_post = GeneratedPost(
                platform=generated_post.platform,
                content=corrected_content,
                hashtags=generated_post.hashtags,
                mentions=generated_post.mentions,
                character_count=len(corrected_content),
                estimated_reading_time=generated_post.estimated_reading_time,
                relevance_score=generated_post.relevance_score,
                engagement_prediction=generated_post.engagement_prediction,
                fact_check_score=min(generated_post.fact_check_score + 0.1, 1.0),  # Slight improvement
                ai_model=generated_post.ai_model,
                generation_prompt=generated_post.generation_prompt,
            )
            
            self.logger.info("Content auto-correction completed", 
                           original_length=len(generated_post.content),
                           corrected_length=len(corrected_content))
            
            return corrected_post
            
        except Exception as e:
            self.logger.error("Auto-correction failed", error=str(e))
            return generated_post  # Return original if correction fails


# Global content optimizer instance
content_optimizer = ContentOptimizer()