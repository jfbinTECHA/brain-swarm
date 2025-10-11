#!/usr/bin/env python3
"""
Script to start the scheduled summarizer service
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brainswarm.cortex.scheduled_summarizer import scheduled_summarizer

async def main():
    if scheduled_summarizer is None:
        print("❌ Scheduled summarizer not initialized")
        return

    print("🚀 Starting scheduled summarizer service...")
    await scheduled_summarizer.start()

    # Keep running
    try:
        while True:
            await asyncio.sleep(60)
            status = scheduled_summarizer.get_status()
            print(f"📊 Summarizer status: running={status['running']}, last_run={status['last_run']}")
    except KeyboardInterrupt:
        print("🛑 Stopping summarizer...")
        await scheduled_summarizer.stop()

if __name__ == "__main__":
    asyncio.run(main())