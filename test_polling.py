#!/usr/bin/env python3
"""
Test script to demonstrate polling endpoint for progress tracking.
This script uploads a CSV and polls the status endpoint to track progress.
"""

import asyncio
import sys
import time
from pathlib import Path

import httpx


class ProgressTracker:
    """Track and display job progress"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def upload_csv(self, csv_file_path: str) -> str:
        """
        Upload CSV file and get job ID

        Args:
            csv_file_path: Path to CSV file

        Returns:
            Job ID
        """
        print(f"📤 Uploading CSV file: {csv_file_path}")
        print("-" * 60)

        with open(csv_file_path, "rb") as f:
            files = {"file": (Path(csv_file_path).name, f, "text/csv")}
            response = await self.client.post(
                f"{self.base_url}/hospitals/bulk", files=files
            )

        if response.status_code == 202:
            data = response.json()
            job_id = data["job_id"]
            total = data["total_hospitals"]
            print("✅ Upload successful!")
            print(f"   Job ID: {job_id}")
            print(f"   Total hospitals: {total}")
            print(f"   Status: {data['status']}")
            print()
            return job_id
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            sys.exit(1)

    async def poll_status(self, job_id: str, poll_interval: float = 2.0):
        """
        Poll job status until completion

        Args:
            job_id: Job identifier
            poll_interval: Seconds between polls
        """
        print(f"🔄 Polling job status (every {poll_interval}s)...")
        print("=" * 60)

        previous_processed = 0
        start_time = time.time()

        while True:
            try:
                response = await self.client.get(
                    f"{self.base_url}/hospitals/bulk/status/{job_id}"
                )

                if response.status_code != 200:
                    print(f"❌ Error getting status: {response.status_code}")
                    break

                data = response.json()
                status = data["status"]
                processed = data["processed_hospitals"]
                total = data["total_hospitals"]
                failed = data["failed_hospitals"]
                progress = data["progress_percentage"]
                current = data.get("current_hospital", "N/A")
                eta = data.get("estimated_time_remaining_seconds")

                # Clear line and show progress
                elapsed = time.time() - start_time
                print(f"\r⏱️  Elapsed: {elapsed:.1f}s", end=" | ")
                print(f"Progress: {progress:.1f}% ({processed}/{total})", end=" | ")
                print(f"Failed: {failed}", end=" | ")

                if eta is not None:
                    print(f"ETA: {eta:.1f}s", end=" | ")

                print(f"Status: {status}", end="")

                # Show new completions
                if processed > previous_processed:
                    print(f"\n   ✓ Completed: {current}")
                    previous_processed = processed

                # Check if job is complete
                if status == "completed":
                    print("\n")
                    print("=" * 60)
                    print("✅ Job completed successfully!")
                    print("-" * 60)
                    self._display_result(data)
                    break
                elif status == "failed":
                    print("\n")
                    print("=" * 60)
                    print("❌ Job failed!")
                    print(f"Error: {data.get('error', 'Unknown error')}")
                    break

                # Wait before next poll
                await asyncio.sleep(poll_interval)

            except KeyboardInterrupt:
                print("\n\n⚠️  Polling interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Error during polling: {e}")
                break

    def _display_result(self, data: dict):
        """Display final result"""
        result = data.get("result")
        if not result:
            print("No result data available")
            return

        print(f"Batch ID: {result['batch_id']}")
        print(f"Total Hospitals: {result['total_hospitals']}")
        print(f"Processed: {result['processed_hospitals']}")
        print(f"Failed: {result['failed_hospitals']}")
        print(f"Processing Time: {result['processing_time_seconds']}s")
        print(f"Batch Activated: {result['batch_activated']}")
        print()

        # Show hospital details
        print("Hospital Details:")
        print("-" * 60)
        for hospital in result["hospitals"][:10]:  # Show first 10
            status_icon = "✓" if hospital["status"] == "created_and_activated" else "✗"
            print(
                f"{status_icon} Row {hospital['row']}: {hospital['name']} "
                f"(ID: {hospital.get('hospital_id', 'N/A')})"
            )

        if len(result["hospitals"]) > 10:
            print(f"... and {len(result['hospitals']) - 10} more")

    async def get_all_jobs(self):
        """Get status of all jobs"""
        print("📊 Fetching all jobs...")
        print("-" * 60)

        response = await self.client.get(f"{self.base_url}/hospitals/bulk/jobs")

        if response.status_code == 200:
            data = response.json()
            stats = data["stats"]
            jobs = data["jobs"]

            print(f"Total Jobs: {data['total_jobs']}")
            print(f"  Pending: {stats['pending_jobs']}")
            print(f"  Processing: {stats['processing_jobs']}")
            print(f"  Completed: {stats['completed_jobs']}")
            print(f"  Failed: {stats['failed_jobs']}")
            print()

            if jobs:
                print("Recent Jobs:")
                for job in jobs[-5:]:  # Show last 5
                    print(
                        f"  • {job['job_id'][:8]}... - {job['status']} - "
                        f"{job['processed_hospitals']}/{job['total_hospitals']} "
                        f"({job['progress_percentage']}%)"
                    )
        else:
            print(f"❌ Error getting jobs: {response.status_code}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


async def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("HOSPITAL BULK PROCESSOR - POLLING TEST")
    print("=" * 60)
    print()

    # Configuration
    base_url = "http://localhost:8000"
    csv_file = "sample_hospitals.csv"
    poll_interval = 2.0  # seconds

    # Check if CSV file exists
    if not Path(csv_file).exists():
        print(f"❌ Error: CSV file not found: {csv_file}")
        print("Please ensure sample_hospitals.csv exists in the current directory")
        sys.exit(1)

    tracker = ProgressTracker(base_url=base_url)

    try:
        # Check server health
        try:
            response = await tracker.client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ Server is healthy")
                print()
            else:
                print(f"⚠️  Server health check returned: {response.status_code}")
                print()
        except Exception as e:
            print(f"❌ Cannot connect to server at {base_url}")
            print(f"Error: {e}")
            print("\nPlease ensure the server is running:")
            print("  docker-compose up")
            print("  or")
            print("  uvicorn app.main:app --reload")
            sys.exit(1)

        # Upload CSV
        job_id = await tracker.upload_csv(csv_file)

        # Poll for status
        await tracker.poll_status(job_id, poll_interval=poll_interval)

        print()
        print("=" * 60)
        print()

        # Show all jobs
        await tracker.get_all_jobs()

        print()
        print("=" * 60)
        print("✨ Test completed!")
        print()
        print("You can check the job status anytime using:")
        print(f"  curl {base_url}/hospitals/bulk/status/{job_id}")
        print()

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await tracker.close()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
