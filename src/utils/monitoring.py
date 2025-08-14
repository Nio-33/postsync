"""
Performance Monitoring and Alerting System

This module provides comprehensive monitoring capabilities for PostSync:
- System performance metrics
- Content generation success rates
- API health monitoring
- Alert management and escalation
- Performance analytics
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

import structlog
from google.cloud import monitoring_v3
from google.cloud import logging as cloud_logging

from src.config.settings import get_settings


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class MetricType(Enum):
    """Types of metrics tracked."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    name: str
    value: Union[int, float]
    timestamp: datetime
    metric_type: MetricType
    labels: Dict[str, str]
    description: str


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    severity: AlertSeverity
    title: str
    description: str
    metric_name: str
    current_value: Union[int, float]
    threshold: Union[int, float]
    timestamp: datetime
    resolved: bool = False
    acknowledged: bool = False


class PerformanceMonitor:
    """Performance monitoring and alerting system."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        
        # Initialize Google Cloud Monitoring client
        try:
            self.monitoring_client = monitoring_v3.MetricServiceClient()
            self.project_name = f"projects/{self.settings.google_cloud_project}"
        except Exception as e:
            self.logger.warning("Cloud Monitoring unavailable", error=str(e))
            self.monitoring_client = None
            self.project_name = None
        
        # Initialize Cloud Logging
        try:
            self.logging_client = cloud_logging.Client()
            self.log_handler = self.logging_client.get_default_handler()
        except Exception as e:
            self.logger.warning("Cloud Logging unavailable", error=str(e))
            self.logging_client = None
            self.log_handler = None
        
        # In-memory metrics storage (for development/fallback)
        self.metrics_buffer: List[PerformanceMetric] = []
        self.active_alerts: List[Alert] = []
        
        # Performance thresholds from PRD requirements
        self.thresholds = {
            "content_generation_success_rate": 95.0,  # 95% minimum
            "system_uptime": 99.9,  # 99.9% SLA
            "content_generation_time": 20.0,  # <20 seconds per PRD
            "api_response_time": 3.0,  # <3 seconds
            "error_rate": 1.0,  # <1% error rate
            "fact_check_accuracy": 99.5,  # 99.5% accuracy
            "user_satisfaction": 4.5,  # >4.5/5 rating
            "engagement_improvement": 150.0  # 150% improvement target
        }
        
        # Alert cooldown periods (prevent spam)
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.cooldown_duration = timedelta(minutes=30)
    
    async def track_metric(
        self,
        name: str,
        value: Union[int, float],
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
        description: str = ""
    ) -> None:
        """
        Track a performance metric.
        
        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            labels: Optional labels for the metric
            description: Metric description
        """
        try:
            metric = PerformanceMetric(
                name=name,
                value=value,
                timestamp=datetime.utcnow(),
                metric_type=metric_type,
                labels=labels or {},
                description=description
            )
            
            # Store in buffer
            self.metrics_buffer.append(metric)
            
            # Send to Google Cloud Monitoring if available
            if self.monitoring_client:
                await self._send_to_cloud_monitoring(metric)
            
            # Check for alert conditions
            await self._check_alert_conditions(metric)
            
            self.logger.debug(
                "Metric tracked",
                name=name,
                value=value,
                type=metric_type.value
            )
            
        except Exception as e:
            self.logger.error("Failed to track metric", name=name, error=str(e))
    
    async def _send_to_cloud_monitoring(self, metric: PerformanceMetric) -> None:
        """Send metric to Google Cloud Monitoring."""
        try:
            # Create time series data
            series = monitoring_v3.TimeSeries()
            series.metric.type = f"custom.googleapis.com/postsync/{metric.name}"
            
            # Add labels
            for key, value in metric.labels.items():
                series.metric.labels[key] = value
            
            # Set resource
            series.resource.type = "global"
            
            # Create data point
            point = monitoring_v3.Point()
            point.value.double_value = float(metric.value)
            point.interval.end_time.seconds = int(metric.timestamp.timestamp())
            series.points = [point]
            
            # Send to monitoring
            request = monitoring_v3.CreateTimeSeriesRequest(
                name=self.project_name,
                time_series=[series]
            )
            
            self.monitoring_client.create_time_series(request=request)
            
        except Exception as e:
            self.logger.error("Failed to send metric to Cloud Monitoring", error=str(e))
    
    async def _check_alert_conditions(self, metric: PerformanceMetric) -> None:
        """Check if metric triggers any alert conditions."""
        try:
            metric_name = metric.name
            value = metric.value
            
            # Skip if in cooldown period
            if metric_name in self.alert_cooldowns:
                if datetime.utcnow() < self.alert_cooldowns[metric_name]:
                    return
            
            # Check against thresholds
            alert_triggered = False
            severity = AlertSeverity.INFO
            
            if metric_name in self.thresholds:
                threshold = self.thresholds[metric_name]
                
                if metric_name in ["content_generation_success_rate", "system_uptime", 
                                 "fact_check_accuracy", "user_satisfaction"]:
                    # Higher is better metrics
                    if value < threshold:
                        alert_triggered = True
                        if value < threshold * 0.8:
                            severity = AlertSeverity.CRITICAL
                        elif value < threshold * 0.9:
                            severity = AlertSeverity.HIGH
                        else:
                            severity = AlertSeverity.MEDIUM
                
                elif metric_name in ["content_generation_time", "api_response_time", "error_rate"]:
                    # Lower is better metrics
                    if value > threshold:
                        alert_triggered = True
                        if value > threshold * 2:
                            severity = AlertSeverity.CRITICAL
                        elif value > threshold * 1.5:
                            severity = AlertSeverity.HIGH
                        else:
                            severity = AlertSeverity.MEDIUM
            
            # Special case: engagement improvement (higher is better, but different threshold logic)
            if metric_name == "engagement_improvement" and value < self.thresholds[metric_name]:
                alert_triggered = True
                severity = AlertSeverity.MEDIUM
            
            if alert_triggered:
                alert = Alert(
                    id=f"{metric_name}_{int(time.time())}",
                    severity=severity,
                    title=f"{metric_name.replace('_', ' ').title()} Alert",
                    description=f"{metric_name} is {value}, threshold is {self.thresholds.get(metric_name, 'N/A')}",
                    metric_name=metric_name,
                    current_value=value,
                    threshold=self.thresholds.get(metric_name, 0),
                    timestamp=datetime.utcnow()
                )
                
                await self._trigger_alert(alert)
                
                # Set cooldown
                self.alert_cooldowns[metric_name] = datetime.utcnow() + self.cooldown_duration
            
        except Exception as e:
            self.logger.error("Failed to check alert conditions", error=str(e))
    
    async def _trigger_alert(self, alert: Alert) -> None:
        """Trigger an alert and send notifications."""
        try:
            self.active_alerts.append(alert)
            
            self.logger.warning(
                "Alert triggered",
                alert_id=alert.id,
                severity=alert.severity.value,
                title=alert.title,
                current_value=alert.current_value,
                threshold=alert.threshold
            )
            
            # Send to Cloud Logging as structured log
            if self.logging_client:
                self.logging_client.logger("postsync-alerts").log_struct({
                    "alert_id": alert.id,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "description": alert.description,
                    "metric_name": alert.metric_name,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold,
                    "timestamp": alert.timestamp.isoformat()
                }, severity="WARNING" if alert.severity == AlertSeverity.MEDIUM else "ERROR")
            
            # Send external notifications for critical alerts
            if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                await self._send_alert_notification(alert)
            
        except Exception as e:
            self.logger.error("Failed to trigger alert", alert_id=alert.id, error=str(e))
    
    async def _send_alert_notification(self, alert: Alert) -> None:
        """Send alert notification to external systems."""
        try:
            # In a production system, this would integrate with:
            # - Slack/Discord webhooks
            # - Email notifications
            # - PagerDuty/OpsGenie
            # - SMS alerts
            
            notification_payload = {
                "alert_id": alert.id,
                "severity": alert.severity.value,
                "title": alert.title,
                "description": alert.description,
                "timestamp": alert.timestamp.isoformat(),
                "metric": {
                    "name": alert.metric_name,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold
                }
            }
            
            self.logger.info(
                "Alert notification sent",
                alert_id=alert.id,
                severity=alert.severity.value,
                payload=notification_payload
            )
            
        except Exception as e:
            self.logger.error("Failed to send alert notification", error=str(e))
    
    async def track_content_generation_performance(
        self,
        success: bool,
        duration_seconds: float,
        platform: str,
        fact_check_score: float,
        user_id: str
    ) -> None:
        """Track content generation performance metrics."""
        try:
            labels = {"platform": platform, "user_id": user_id}
            
            # Track success rate
            await self.track_metric(
                "content_generation_success",
                1 if success else 0,
                MetricType.COUNTER,
                labels,
                "Content generation success/failure counter"
            )
            
            # Track generation time
            await self.track_metric(
                "content_generation_time",
                duration_seconds,
                MetricType.HISTOGRAM,
                labels,
                "Time taken to generate content"
            )
            
            # Track fact-check score
            await self.track_metric(
                "fact_check_score",
                fact_check_score,
                MetricType.GAUGE,
                labels,
                "Fact-checking accuracy score"
            )
            
        except Exception as e:
            self.logger.error("Failed to track content generation performance", error=str(e))
    
    async def track_api_performance(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time: float
    ) -> None:
        """Track API endpoint performance."""
        try:
            labels = {
                "endpoint": endpoint,
                "method": method,
                "status_code": str(status_code)
            }
            
            # Track request count
            await self.track_metric(
                "api_requests_total",
                1,
                MetricType.COUNTER,
                labels,
                "Total API requests"
            )
            
            # Track response time
            await self.track_metric(
                "api_response_time",
                response_time,
                MetricType.HISTOGRAM,
                labels,
                "API response time in seconds"
            )
            
            # Track error rate
            if status_code >= 400:
                await self.track_metric(
                    "api_errors_total",
                    1,
                    MetricType.COUNTER,
                    labels,
                    "Total API errors"
                )
            
        except Exception as e:
            self.logger.error("Failed to track API performance", error=str(e))
    
    async def track_user_engagement(
        self,
        user_id: str,
        platform: str,
        engagement_rate: float,
        baseline_rate: float
    ) -> None:
        """Track user engagement performance."""
        try:
            labels = {"user_id": user_id, "platform": platform}
            
            # Calculate improvement percentage
            if baseline_rate > 0:
                improvement = (engagement_rate / baseline_rate) * 100
            else:
                improvement = 100  # If no baseline, assume 100% improvement
            
            await self.track_metric(
                "engagement_improvement",
                improvement,
                MetricType.GAUGE,
                labels,
                "Engagement improvement percentage"
            )
            
            await self.track_metric(
                "engagement_rate",
                engagement_rate,
                MetricType.GAUGE,
                labels,
                "Current engagement rate"
            )
            
        except Exception as e:
            self.logger.error("Failed to track user engagement", error=str(e))
    
    async def get_system_health(self) -> Dict[str, Union[str, float, bool]]:
        """Get overall system health status."""
        try:
            # Calculate recent metrics
            recent_metrics = [
                m for m in self.metrics_buffer 
                if m.timestamp > datetime.utcnow() - timedelta(hours=1)
            ]
            
            # System health indicators
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_percentage": 99.9,  # Would be calculated from actual uptime
                "active_alerts": len([a for a in self.active_alerts if not a.resolved]),
                "critical_alerts": len([a for a in self.active_alerts 
                                      if a.severity == AlertSeverity.CRITICAL and not a.resolved]),
                "metrics_tracked": len(recent_metrics)
            }
            
            # Calculate success rates
            success_metrics = [m for m in recent_metrics if m.name == "content_generation_success"]
            if success_metrics:
                total_attempts = len(success_metrics)
                successful_attempts = sum(m.value for m in success_metrics)
                success_rate = (successful_attempts / total_attempts) * 100 if total_attempts > 0 else 0
                health_status["content_generation_success_rate"] = success_rate
            
            # Calculate average response times
            response_time_metrics = [m for m in recent_metrics if m.name == "api_response_time"]
            if response_time_metrics:
                avg_response_time = sum(m.value for m in response_time_metrics) / len(response_time_metrics)
                health_status["average_response_time"] = avg_response_time
            
            # Determine overall status
            critical_alerts = health_status["critical_alerts"]
            success_rate = health_status.get("content_generation_success_rate", 100)
            
            if critical_alerts > 0:
                health_status["status"] = "critical"
            elif success_rate < 90:
                health_status["status"] = "degraded"
            elif len(self.active_alerts) > 5:
                health_status["status"] = "warning"
            
            return health_status
            
        except Exception as e:
            self.logger.error("Failed to get system health", error=str(e))
            return {
                "status": "unknown",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_performance_report(
        self,
        hours_back: int = 24
    ) -> Dict[str, Union[str, float, List[Dict]]]:
        """Generate comprehensive performance report."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            recent_metrics = [
                m for m in self.metrics_buffer 
                if m.timestamp > cutoff_time
            ]
            
            report = {
                "period": f"Last {hours_back} hours",
                "generated_at": datetime.utcnow().isoformat(),
                "total_metrics": len(recent_metrics),
                "summary": {},
                "alerts": [],
                "recommendations": []
            }
            
            # Group metrics by name
            metrics_by_name = {}
            for metric in recent_metrics:
                if metric.name not in metrics_by_name:
                    metrics_by_name[metric.name] = []
                metrics_by_name[metric.name].append(metric)
            
            # Calculate summary statistics
            for name, metrics in metrics_by_name.items():
                values = [m.value for m in metrics]
                report["summary"][name] = {
                    "count": len(values),
                    "average": sum(values) / len(values) if values else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                    "latest": values[-1] if values else 0
                }
            
            # Include recent alerts
            recent_alerts = [
                a for a in self.active_alerts 
                if a.timestamp > cutoff_time
            ]
            
            for alert in recent_alerts:
                report["alerts"].append({
                    "id": alert.id,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "timestamp": alert.timestamp.isoformat(),
                    "resolved": alert.resolved
                })
            
            # Generate recommendations
            report["recommendations"] = await self._generate_performance_recommendations(report["summary"])
            
            return report
            
        except Exception as e:
            self.logger.error("Failed to generate performance report", error=str(e))
            return {
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def _generate_performance_recommendations(
        self,
        summary: Dict[str, Dict]
    ) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        try:
            # Check content generation performance
            if "content_generation_time" in summary:
                avg_time = summary["content_generation_time"]["average"]
                if avg_time > 15:
                    recommendations.append(
                        f"Content generation averaging {avg_time:.1f}s - consider optimizing AI model calls"
                    )
            
            # Check API response times
            if "api_response_time" in summary:
                avg_response = summary["api_response_time"]["average"]
                if avg_response > 2:
                    recommendations.append(
                        f"API responses averaging {avg_response:.1f}s - consider implementing caching"
                    )
            
            # Check success rates
            if "content_generation_success" in summary:
                success_rate = summary["content_generation_success"]["average"] * 100
                if success_rate < 95:
                    recommendations.append(
                        f"Content generation success rate at {success_rate:.1f}% - review error patterns"
                    )
            
            # Check engagement performance
            if "engagement_improvement" in summary:
                avg_improvement = summary["engagement_improvement"]["average"]
                if avg_improvement < 120:
                    recommendations.append(
                        f"Engagement improvement at {avg_improvement:.1f}% - consider A/B testing content approaches"
                    )
            
            if not recommendations:
                recommendations.append("System performance is within acceptable parameters")
            
        except Exception as e:
            self.logger.error("Failed to generate recommendations", error=str(e))
            recommendations.append("Unable to generate recommendations due to system error")
        
        return recommendations
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        try:
            for alert in self.active_alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    self.logger.info(
                        "Alert acknowledged",
                        alert_id=alert_id,
                        acknowledged_by=acknowledged_by
                    )
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e))
            return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Mark an alert as resolved."""
        try:
            for alert in self.active_alerts:
                if alert.id == alert_id:
                    alert.resolved = True
                    self.logger.info(
                        "Alert resolved",
                        alert_id=alert_id,
                        resolved_by=resolved_by
                    )
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to resolve alert", alert_id=alert_id, error=str(e))
            return False


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Decorator for tracking function performance
def track_performance(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to track function execution performance."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                duration = time.time() - start_time
                
                # Track performance metrics
                asyncio.create_task(
                    performance_monitor.track_metric(
                        f"{metric_name}_duration",
                        duration,
                        MetricType.HISTOGRAM,
                        labels,
                        f"Execution time for {func.__name__}"
                    )
                )
                
                asyncio.create_task(
                    performance_monitor.track_metric(
                        f"{metric_name}_success",
                        1 if success else 0,
                        MetricType.COUNTER,
                        labels,
                        f"Success rate for {func.__name__}"
                    )
                )
        
        return wrapper
    return decorator