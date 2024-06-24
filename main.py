import csv
import logging
import os
import time
from typing import Any, Tuple

import numpy as np
from liquidctl import find_liquidctl_devices
from psutil import sensors_temperatures


def init_fans() -> Tuple[Any] | None:
    """Initialise the fans"""
    logging.info("Initialising liquidctl devices:")
    devices = find_liquidctl_devices()
    fans = []
    for dev in devices:
        with dev.connect():
            try:
                init_output = dev.initialize()
                if init_output:
                    for k, v, unit in init_output:
                        logging.info(f"- {k}: {v} {unit}")
                    fans.append(dev)
                else:
                    logging.error(
                        f"Error initialising {dev.description} at {dev.bus}:{dev.address}"
                    )
            except AssertionError as ex:
                logging.error(f"{ex}, could not access device")
    if fans:
        return tuple(fans)
    return None


def load_fan_curve() -> np.ndarray:
    """Load the fan curve defined at `./fan_curve.csv`. Returns as a 2xN numpy array where the
    first column is temprature and the second is fan duty"""
    logging.info("Initialising fan curve:")
    curve_path = os.path.join(os.path.dirname(__file__), "fan_curve.csv")
    with open(curve_path, "r", encoding="utf-8") as file:
        rows = csv.reader(file, delimiter=",")
        curve = np.vstack([[float(r[0]), float(r[1])] for r in rows], dtype=np.float32)
    logging.info(f"Loaded fan curve with {curve.shape[0]} temp/duty pairs \n{curve}")
    return curve


def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Started")
    init_fans()
    curve = load_fan_curve()
    while True:
        try:
            cpu_temp = sensors_temperatures()["coretemp"][0].current
            duty = int(np.interp(cpu_temp, curve[:, 0], curve[:, 1]))
            logging.info(f"Temp: {cpu_temp}, Fan duty: {duty}")
            for dev in find_liquidctl_devices():
                with dev.connect():
                    for channel in list(dev._speed_channels.keys()):
                        dev.set_fixed_speed(channel, duty)
            time.sleep(2)
        except KeyboardInterrupt as ex:
            logging.info(f"{str(ex)}, Stopping script")
            break


if __name__ == "__main__":
    main()
