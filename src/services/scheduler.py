"""
Background Job Scheduler Service

This service handles background job processing including:
- Scheduled content publishing
- Analytics data collection
- Content discovery automation
- Cleanup tasks
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import structlog

from src.services.publishing import PublishingService
from src.services.content_discovery import ContentDiscoveryService
from src.services.analytics import AnalyticsService
from src.integrations.firestore import firestore_client


class BackgroundScheduler:
    """Background job scheduler for automated tasks."""
    
    def __init__(self):
        """Initialize scheduler with services."""
        self.logger = structlog.get_logger(__name__)
        self.publishing = PublishingService()
        self.content_discovery = ContentDiscoveryService()
        self.analytics = AnalyticsService()
        self.db = firestore_client
        
        # Job control
        self.is_running = False
        self.job_intervals = {
            "publish_scheduled_content": 60,  # Every 1 minute
            "discover_content": 1800,         # Every 30 minutes
            "collect_analytics": 3600,        # Every 1 hour
            "cleanup_old_data": 86400,        # Every 24 hours
        }
        self.last_run = {}
    
    async def start(self):
        """Start the background scheduler."""
        if self.is_running:
            self.logger.warning("Scheduler already running")
            return
        
        self.is_running = True
        self.logger.info("Starting background scheduler")
        
        # Initialize last run times
        current_time = datetime.utcnow()
        for job_name in self.job_intervals:
            self.last_run[job_name] = current_time
        
        # Start the main loop
        await self._run_scheduler_loop()
    
    async def stop(self):
        """Stop the background scheduler."""
        self.is_running = False
        self.logger.info("Stopping background scheduler")
    
    async def _run_scheduler_loop(self):
        """Main scheduler loop."""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                
                # Check and run jobs
                await self._check_and_run_jobs(current_time)
                
                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error("Scheduler loop error", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _check_and_run_jobs(self, current_time: datetime):
        """Check which jobs need to run and execute them."""
        jobs_to_run = []
        
        for job_name, interval_seconds in self.job_intervals.items():
            last_run = self.last_run.get(job_name)
            if not last_run:
                jobs_to_run.append(job_name)
                continue
            
            time_since_last_run = (current_time - last_run).total_seconds()
            if time_since_last_run >= interval_seconds:
                jobs_to_run.append(job_name)
        
        if jobs_to_run:
            self.logger.info("Running scheduled jobs", jobs=jobs_to_run)
        
        # Run jobs concurrently
        job_tasks = []
        for job_name in jobs_to_run:
            job_tasks.append(self._run_job(job_name, current_time))
        
        if job_tasks:
            await asyncio.gather(*job_tasks, return_exceptions=True)
    
    async def _run_job(self, job_name: str, current_time: datetime):
        """Run a specific job."""
        try:
            self.logger.info("Starting job", job=job_name)
            
            result = None
            if job_name == "publish_scheduled_content":
                result = await self._publish_scheduled_content_job()
            elif job_name == "discover_content":
                result = await self._discover_content_job()
            elif job_name == "collect_analytics":
                result = await self._collect_analytics_job()
            elif job_name == "cleanup_old_data":
                result = await self._cleanup_old_data_job()
            
            # Update last run time
            self.last_run[job_name] = current_time
            
            self.logger.info("Job completed", job=job_name, result=result)
            
        except Exception as e:
            self.logger.error("Job failed", job=job_name, error=str(e))
    
    async def _publish_scheduled_content_job(self) -> Dict:
        """Job to publish scheduled content."""
        try:
            result = await self.publishing.process_scheduled_content()
            return result
        except Exception as e:
            self.logger.error("Scheduled content publishing failed", error=str(e))
            return {"processed": 0, "successful": 0, "failed": 0}
    
    async def _discover_content_job(self) -> Dict:
        """Job to discover new content for all active users."""
        try:
            # Get all active users (simplified - would have proper user management)
            active_users = await self._get_active_users()
            
            if not active_users:
                return {"users_processed": 0, "content_discovered": 0}
            
            # Run content discovery for multiple users
            discovery_results = await self.content_discovery.bulk_discover_content(active_users)
            
            total_discovered = sum(discovery_results.values())
            
            return {
                "users_processed": len(active_users),
                "content_discovered": total_discovered,
                "results": discovery_results
            }
            
        except Exception as e:
            self.logger.error("Content discovery job failed", error=str(e))
            return {"users_processed": 0, "content_discovered": 0}
    
    async def _collect_analytics_job(self) -> Dict:
        """Job to collect analytics data from platforms."""
        try:
            # Get users with connected social accounts
            users_with_accounts = await self._get_users_with_social_accounts()
            
            collected_count = 0
            for user_id in users_with_accounts:
                try:
                    # Refresh analytics data for each user
                    await self.analytics.refresh_analytics_data(user_id)
                    collected_count += 1
                except Exception as e:
                    self.logger.warning(
                        "Analytics collection failed for user",
                        user_id=user_id,
                        error=str(e)
                    )
            
            return {
                "users_processed": len(users_with_accounts),
                "successful_collections": collected_count
            }
            
        except Exception as e:
            self.logger.error("Analytics collection job failed", error=str(e))
            return {"users_processed": 0, "successful_collections": 0}
    
    async def _cleanup_old_data_job(self) -> Dict:
        """Job to cleanup old data."""
        try:
            # Cleanup old content and analytics data
            content_cleaned = await self.content_discovery.cleanup_old_content(days_old=30)
            data_cleaned = await self.db.cleanup_old_data(days=90)
            
            return {
                "old_content_cleaned": content_cleaned,
                "old_data_cleaned": data_cleaned
            }
            
        except Exception as e:
            self.logger.error("Cleanup job failed", error=str(e))
            return {"old_content_cleaned": 0, "old_data_cleaned": 0}
    
    async def _get_active_users(self) -> List[str]:
        """Get list of active user IDs."""
        try:
            # For now, return a simplified list
            # In production, this would query for users with active subscriptions
            # and recent activity
            
            # Mock data for development
            return ["user_1", "user_2", "user_3"]  # Replace with actual user query
            
        except Exception as e:
            self.logger.error("Failed to get active users", error=str(e))
            return []
    
    async def _get_users_with_social_accounts(self) -> List[str]:
        """Get users who have connected social media accounts."""
        try:
            # For now, return a simplified list
            # In production, this would query for users with valid OAuth tokens
            
            # Mock data for development
            return ["user_1", "user_2"]  # Replace with actual user query
            
        except Exception as e:
            self.logger.error("Failed to get users with social accounts", error=str(e))
            return []
    
    async def run_job_once(self, job_name: str) -> Dict:
        """Run a specific job once (for testing or manual triggering)."""
        if job_name not in self.job_intervals:
            raise ValueError(f"Unknown job: {job_name}")
        
        self.logger.info("Running job manually", job=job_name)
        
        current_time = datetime.utcnow()
        await self._run_job(job_name, current_time)
        
        return {"job": job_name, "status": "completed", "run_at": current_time}
    
    def get_job_status(self) -> Dict:
        """Get current status of the scheduler and jobs."""
        current_time = datetime.utcnow()
        job_statuses = {}
        
        for job_name, interval_seconds in self.job_intervals.items():
            last_run = self.last_run.get(job_name)
            if last_run:
                time_since_last_run = (current_time - last_run).total_seconds()
                next_run_in = max(0, interval_seconds - time_since_last_run)
            else:
                time_since_last_run = None
                next_run_in = 0
            
            job_statuses[job_name] = {
                "interval_seconds": interval_seconds,
                "last_run": last_run,
                "time_since_last_run": time_since_last_run,
                "next_run_in": next_run_in
            }
        
        return {
            "is_running": self.is_running,
            "current_time": current_time,
            "jobs": job_statuses
        }


# Global scheduler instance
background_scheduler = BackgroundScheduler()