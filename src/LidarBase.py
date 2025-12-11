from rplidar import RPLidar

import time

# Configure the LIDAR port (usually /dev/ttyUSB0)

PORT_NAME = '/dev/ttyUSB0'


def run():
    lidar = RPLidar(PORT_NAME)

    try:

        print("Starting LIDAR...")

        lidar.connect()

        info = lidar.get_info()

        print("Device Info:", info)

        health = lidar.get_health()

        print("Device Health:", health)

        lidar.start_motor()

        for scan in lidar.iter_scans():

            for (_, angle, distance) in scan:
                print(f"Angle: {angle:.2f}, Distance: {distance:.2f} mm")



    except KeyboardInterrupt:

        print("Stopping...")

    finally:

        lidar.stop()

        lidar.stop_motor()

        lidar.disconnect()

        print("LIDAR disconnected.")


if __name__ == '__main__':
    run()