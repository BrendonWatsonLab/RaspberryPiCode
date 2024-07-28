import asyncio
import json
from datetime import datetime, timedelta
from gpiozero import DigitalOutputDevice
import ntplib
from concurrent.futures import ThreadPoolExecutor
import logging
import requests
import time

def wait_for_internet_connection():
    primary_url = "http://www.google.com"
    fallback_url = "http://www.cloudflare.com"
    while True:
        try:
            response = requests.get(primary_url, timeout=5)

            # If the request was successful, break out of the loop
            if response.status_code == 200:
                logger.info("Internet Connection Successful!!")
                break
            elif response.status_code == 429:
                logger.warning("Too many requests, Changing to fall back url!!")
                primary_url = fallback_url
                time.sleep(5)
            else :
                logger.warning(f"Unexpected status code : {response.status_code}")	    
        except (requests.ConnectionError,requests.Timeout) as e:
            # If the connection failed, wait for a bit and then retry
            logger.error("No internet connection. Waiting to retry...")
            time.sleep(5)
        time.sleep(5)
        
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# NTP setup
PRIMARY_NTP_SERVER = 'time.nist.gov'
BACKUP_NTP_SERVER = 'pool.ntp.org'
executor = ThreadPoolExecutor(max_workers=2)



class EventScheduler:
    def __init__(self, offset=timedelta(seconds=0)):
        self.offset = offset
        self.events = []
        self.devices = {}  # Store DigitalOutputDevice instances

    async def update_offset(self):
        client = ntplib.NTPClient()
        for server in [PRIMARY_NTP_SERVER, BACKUP_NTP_SERVER]:
            try:
                response = await asyncio.get_event_loop().run_in_executor(executor, lambda: client.request(server, version=3, timeout=5))
                self.offset = timedelta(seconds=response.offset)
                logger.info(f"Offset updated from {server}: {self.offset.total_seconds()} seconds")
                return
            except Exception as e:
                logger.error(f"Error updating offset from {server}: {e}")
        logger.warning("Failed to update offset from both servers; continuing with last known offset.")
        
    def load_events_from_json(self, file_path):
        with open(file_path, 'r') as file:
            try:
                event_data = json.load(file)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from {file_path}: {e}")
                return

        now = datetime.utcnow() + self.offset
        for event in event_data:
            try:
                event_datetime = self.calculate_initial_datetime(event, now)
            except Exception as e:
                logger.error(f"Error processing event {event}: {e}")
                continue

            pin = event.get('pin')
            duration = event.get('duration', 0.1)
            initial_value = event.get('pin_initial_value', False)
            if pin is not None:
                self.setup_device(pin, initial_value)
            
            callback = self.get_callback(event['callback'], pin, duration)
            

            description = event.get('description', 'No description provided')
            repeat = event.get('repeat', 'none')
            self.add_event(event_datetime, callback, description, repeat)

    def calculate_initial_datetime(self, event, now):
        if event['repeat'] == 'none':
            event_time = datetime.fromisoformat(event['event_time']) 
            if now <= event_time:
               return event_time
            else:
               raise ValueError("The specified event time is in the past.")
        else:
            time_parts = datetime.strptime(event['event_time'], '%H:%M:%S').time()
            return self.adjust_datetime(now, time_parts, event['repeat'])

    def adjust_datetime(self, now, time_parts, repeat):
        if repeat == 'day':
            result = datetime.combine(now.date(), time_parts)
            return result + timedelta(days=1) if result <= now else result
        elif repeat == 'hour':
            result = now.replace(minute=time_parts.minute, second=time_parts.second, microsecond=0)
            return result + timedelta(hours=1) if result <= now else result
        elif repeat == 'minute':
            result = now.replace(second=time_parts.second, microsecond=0)
            return result + timedelta(minutes=1) if result <= now else result

    def setup_device(self, pin, initial_value):
        if pin not in self.devices:
            self.devices[pin] = DigitalOutputDevice(pin, initial_value=initial_value)

    def get_callback(self, callback_name, pin, duration):
        if pin is not None:
            if callback_name == "turn_on_starter":
                return lambda: self.turn_on_starter(pin)
            elif callback_name == "turn_off_starter":
                return lambda: self.turn_off_starter(pin)
            elif callback_name == "give_pulse":
                return lambda: self.give_pulse(pin, duration)
        return lambda: self.update_offset()

    async def turn_on_starter(self, pin):
        device = self.devices[pin]
        device.off()
        logger.info(f"Starter on pin {pin} activated.")

    async def turn_off_starter(self, pin):
        device = self.devices[pin]
        device.on()
        logger.info(f"Starter on pin {pin} deactivated.")

    async def give_pulse(self, pin, duration):
        device = self.devices[pin]
        device.on()
        await asyncio.sleep(duration)
        device.off()
        logger.info(f"Pulse given on pin {pin}.")

    def add_event(self, event_time, callback, description, repeat):
        self.events.append((event_time, callback, description, repeat))
        self.events.sort(key=lambda x: x[0])


    async def run(self):
        while True:
            if not self.events:
                await asyncio.sleep(1)
                continue

            now = datetime.utcnow() + self.offset
            next_event_time, next_callback, description, repeat = self.events[0]
            sleep_duration = (next_event_time - now).total_seconds() - 0.5 if (next_event_time - now).total_seconds() > 0.5 else 0

            if sleep_duration > 0:
                await asyncio.sleep(sleep_duration)

            now = datetime.utcnow() + self.offset
            if now >= next_event_time:
                try:
                    await next_callback()
                    logger.info(f"Executing event: {description} at time: {now}")
                except Exception as e:
                    logger.error(f"Error executing {description}: {e}")

                self.events.pop(0)  # Remove the executed event

                if repeat != 'none':
                    if repeat == 'hour':
                        next_event_time += timedelta(hours=1)
                    elif repeat == 'day':
                        next_event_time += timedelta(days=1)
                    elif repeat == 'minute':
                        next_event_time += timedelta(minutes=1)

                    self.add_event(next_event_time, next_callback, description, repeat)  # Reschedule if needed

async def main():
	logger.info("Started the Scheduler Program")
	wait_for_internet_connection()
	scheduler = EventScheduler()
	await scheduler.update_offset()
	scheduler.load_events_from_json('events.json')
	asyncio.create_task(scheduler.run())
	while True:
		await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())