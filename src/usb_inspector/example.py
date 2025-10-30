import asyncio
import contextlib
import logging

from usb_inspector.monitor import USBDeviceMonitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def custom_callback(event_type: str, device_info: dict):
    """Example custom async callback function"""
    if event_type == "connected":
        product = device_info.get("product", None)
        logger.info("Custom handler: New device detected - %s", product)
        # Can do async operations here
        await asyncio.sleep(0.1)  # Simulating async work
    else:
        logger.info("Custom handler: Device removed - %s", device_info["device_id"])


async def main():
    """Example usage with asyncio"""

    # Example 1: Basic monitoring
    monitor = USBDeviceMonitor(poll_interval=1.0)

    # Example 2: With custom callback
    await monitor.monitor(callback=custom_callback)

    # Example 3: Just get current devices without monitoring
    # devices = await monitor.get_current_devices()
    # for dev in devices:
    #     print(monitor.get_device_info(dev))
    # print("Currently connected USB devices:")
    # Example 4: Run monitoring as a background task
    monitor_task = asyncio.create_task(monitor.monitor())

    try:
        # Do other async work here
        await asyncio.sleep(10)

        # Wait for the monitor task to complete
        await monitor_task

    except asyncio.CancelledError:
        logger.info("Monitoring task was cancelled.")
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user.")
        monitor_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await monitor_task
    finally:
        logger.info("Exiting program.")


async def example_with_multiple_tasks():
    """Example showing USB monitoring alongside other async tasks"""

    monitor = USBDeviceMonitor(poll_interval=5.0)

    async def some_other_task():
        """Simulate other async work"""
        for i in range(20):
            await asyncio.sleep(2)
            logger.info("Other task working... %d", i)

    try:
        # Run both tasks concurrently
        await asyncio.gather(
            monitor.monitor(callback=custom_callback), some_other_task()
        )
    except asyncio.CancelledError:
        logger.info("Tasks were cancelled.")
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user.")
        monitor.stop()  # Ensure the monitor stops gracefully
    finally:
        logger.info("Exiting example_with_multiple_tasks.")


if __name__ == "__main__":
    try:
        # Run the async main function
        asyncio.run(main())

        # Or use the multiple tasks example
        # asyncio.run(example_with_multiple_tasks())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user.")
