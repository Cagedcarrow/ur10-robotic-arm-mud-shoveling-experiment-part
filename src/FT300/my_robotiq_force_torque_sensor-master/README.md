# my_robotiq_force_torque_sensor

This is a ROS package which calls low-level communications functions by Robotiq that interface with Robotiq's FT300 force torque sensor.
There is an existing package, [robotiq_force_torque_sensor](http://wiki.ros.org/robotiq_force_torque_sensor), but it is not compatible with Noetic.

The publisher topic name and sensor frame ID are read from the parameter server from parameters `/ftsensor_node_name` and `/ftsensor_frame` respectively.

The code license is preserved in all code files. The original source from Robotiq can be found at [support.robotiq.com](support.robotiq.com).
