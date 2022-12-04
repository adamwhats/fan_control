import logging
import time
from csv import reader
from typing import Generator, Tuple, List

import numpy as np
from liquidctl import find_liquidctl_devices
from psutil import sensors_temperatures


def init() -> Tuple[Generator, np.ndarray, np.ndarray]:
    # Initialise fans
    logging.info("Initialising liquidctl devices:")
    devices = find_liquidctl_devices()
    for dev in devices:
        with dev.connect():
            try:
                init_output = dev.initialize()
                if init_output:
                    for k, v, unit in init_output:
                        logging.info(f"- {k}: {v} {unit}")
                else:
                    raise logging.error(
                        f"Error initialising {dev.description} at {dev.bus}:{dev.address}")
            except AssertionError as ex:
                logging.error(f"{str(ex)}, could not access devices")
                pass

    # Initialise fan curve
    logging.info("Initialising fan curve:")
    with open('fan_curve.csv', 'r') as file:
        rows = reader(file, delimiter=',')
        temp, duty = [], []
        for row in rows:
            temp.append(row[0]), duty.append(row[1])
        logging.info(f"- Temp (°C): {[str(t).rjust(3) for t in temp]}")
        logging.info(f"- Duty  (%): {[str(d).rjust(3) for d in duty]}")
        temp = np.array(temp, dtype=np.float32)
        duty = np.array(duty, dtype=np.float32)

    return temp, duty


def set_fan_duty(duty: int) -> None:
    devices = find_liquidctl_devices()
    for dev in devices:
        with dev.connect():
            for channel in list(dev._speed_channels.keys()):
                dev.set_fixed_speed(channel, duty)


def main():
    logging.basicConfig(level=logging.INFO)
    logging.info('Started')
    curve_t, curve_d = init()
    while True:
        try:
            cpu_temp = sensors_temperatures()['coretemp'][0].current
            duty = int(np.interp(cpu_temp, curve_t, curve_d))
            logging.info(f"Temp: {cpu_temp}, Fan duty: {duty}")
            set_fan_duty(duty)
            time.sleep(2)
        except KeyboardInterrupt as ex:
            logging.info(f"{str(ex)}, Stopping script")
            break


if __name__ == '__main__':
    main()
