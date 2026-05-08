[init] GUI ready. 正式姿态来源: ur_robot_driver /joint_states
[operator] 等待 50002 监听后，在 CB3 示教器点击运行 External Control 程序。
[driver] START
[driver] DRIVER_PREFIX=/opt/ros/humble
[driver] [INFO] [launch]: All log files can be found below /root/.ros/log/2026-05-08-15-58-22-722065-Caged-sparrow-26080
[driver] [INFO] [launch]: Default logging verbosity is set to INFO
[driver] [INFO] [dashboard_client-2]: process started with pid [26140]
[driver] [INFO] [controller_stopper_node-4]: process started with pid [26144]
[driver] [INFO] [ur_ros2_control_node-1]: process started with pid [26138]
[driver] [INFO] [robot_state_helper-3]: process started with pid [26142]
[driver] [INFO] [urscript_interface-5]: process started with pid [26146]
[driver] [INFO] [robot_state_publisher-6]: process started with pid [26165]
[driver] [INFO] [trajectory_until_node-7]: process started with pid [26174]
[driver] [INFO] [spawner-8]: process started with pid [26191]
[driver] [INFO] [spawner-9]: process started with pid [26193]
[driver] [robot_state_helper-3] [INFO] [1778227103.048134277] [UR_Client_Library:]: Starting primary client pipeline
[driver] [dashboard_client-2] [0m[INFO] [1778227103.042025676] [UR_Client_Library:]: Starting primary client pipeline[0m
[driver] [controller_stopper_node-4] [0m[INFO] [1778227103.055172972] [Controller stopper]: Waiting for switch controller service to come up on controller_manager/switch_controller[0m
[driver] [ur_ros2_control_node-1] [WARN] [1778227103.073157871] [controller_manager]: [Deprecated] Passing the robot description parameter directly to the control_manager node is deprecated. Use '~/robot_description' topic from 'robot_state_publisher' instead.
[driver] [ur_ros2_control_node-1] text not specified in the tf_prefix tag
[driver] [ur_ros2_control_node-1] [INFO] [1778227103.074398394] [resource_manager]: Loading hardware 'ur10'
[driver] [robot_state_publisher-6] [INFO] [1778227103.077770404] [robot_state_publisher]: got segment base
[driver] [robot_state_publisher-6] [INFO] [1778227103.078028043] [robot_state_publisher]: got segment base_link
[driver] [robot_state_publisher-6] [INFO] [1778227103.078041426] [robot_state_publisher]: got segment base_link_inertia
[driver] [robot_state_publisher-6] [INFO] [1778227103.078160429] [robot_state_publisher]: got segment flange
[driver] [robot_state_publisher-6] [INFO] [1778227103.078168603] [robot_state_publisher]: got segment forearm_link
[driver] [robot_state_publisher-6] [INFO] [1778227103.078171241] [robot_state_publisher]: got segment ft_frame
[driver] [robot_state_publisher-6] [INFO] [1778227103.078173644] [robot_state_publisher]: got segment shoulder_link
[driver] [robot_state_publisher-6] [INFO] [1778227103.078175988] [robot_state_publisher]: got segment tool0
[driver] [robot_state_publisher-6] [INFO] [1778227103.078178348] [robot_state_publisher]: got segment upper_arm_link
[driver] [robot_state_publisher-6] [INFO] [1778227103.078180549] [robot_state_publisher]: got segment world
[driver] [robot_state_publisher-6] [INFO] [1778227103.078182992] [robot_state_publisher]: got segment wrist_1_link
[driver] [robot_state_publisher-6] [INFO] [1778227103.078185297] [robot_state_publisher]: got segment wrist_2_link
[driver] [robot_state_publisher-6] [INFO] [1778227103.078187453] [robot_state_publisher]: got segment wrist_3_link
[driver] [ur_ros2_control_node-1] [INFO] [1778227103.078098771] [resource_manager]: Initialize hardware 'ur10'
[driver] [ur_ros2_control_node-1] [INFO] [1778227103.078226874] [resource_manager]: Successful initialization of hardware 'ur10'
[driver] [ur_ros2_control_node-1] [INFO] [1778227103.078541740] [resource_manager]: 'configure' hardware 'ur10'
[driver] [ur_ros2_control_node-1] [INFO] [1778227103.078555401] [URPositionHardwareInterface]: Starting ...please wait...
[driver] [ur_ros2_control_node-1] [INFO] [1778227103.078565959] [URPositionHardwareInterface]: Initializing driver...
[driver] [ur_ros2_control_node-1] [INFO] [1778227103.081029383] [UR_Client_Library:]: SCHED_FIFO OK, priority 99
[driver] [ur_ros2_control_node-1] [INFO] [1778227103.173379701] [UR_Client_Library:]: Negotiated RTDE protocol version to 2.
[driver] [ur_ros2_control_node-1] [INFO] [1778227103.174871934] [UR_Client_Library:]: Setting up RTDE communication with frequency 125.000000
[driver] [dashboard_client-2] [0m[INFO] [1778227103.178729634] [dashboard_client]: Connecting to Dashboard Server at 10.160.9.21 with policy G5[0m
[driver] [dashboard_client-2] [0m[INFO] [1778227103.178830754] [UR_Client_Library:]: DashboardClient created for host 10.160.9.21[0m
[driver] [dashboard_client-2] [0m[INFO] [1778227103.181594707] [UR_Client_Library:]: Connected: Universal Robots Dashboard Server
[driver] [dashboard_client-2] [0m
[driver] [spawner-8] [INFO] [1778227103.259258043] [spawner_joint_state_broadcaster]: waiting for service /controller_manager/list_controllers to become available...
[driver] [spawner-9] [INFO] [1778227103.321314101] [spawner_joint_trajectory_controller]: waiting for service /controller_manager/list_controllers to become available...
[driver] [ur_ros2_control_node-1] [INFO] [1778227104.205133586] [UR_Client_Library:]: Starting primary client pipeline
[driver] [ur_ros2_control_node-1] [INFO] [1778227104.877752062] [URPositionHardwareInterface]: Calibration checksum: 'calib_17227329492635474227'.
[driver] [ur_ros2_control_node-1] [ERROR] [1778227104.877817970] [URPositionHardwareInterface]: The calibration parameters of the connected robot don't match the ones from the given kinematics config file. Please be aware that this can lead to critical inaccuracies of tcp positions. Use the ur_calibration tool to extract the correct calibration from the robot and pass that into the description. See [https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver/blob/main/ur_calibration/README.md] for details.
[driver] [ur_ros2_control_node-1] [INFO] [1778227104.877901630] [URPositionHardwareInterface]: System successfully started!
[driver] [ur_ros2_control_node-1] [INFO] [1778227104.877919955] [resource_manager]: Successful 'configure' of hardware 'ur10'
[driver] [ur_ros2_control_node-1] [INFO] [1778227104.877951851] [resource_manager]: 'activate' hardware 'ur10'
[driver] [ur_ros2_control_node-1] [INFO] [1778227104.877954515] [URPositionHardwareInterface]: Activating HW interface
[driver] [ur_ros2_control_node-1] [INFO] [1778227104.877957225] [resource_manager]: Successful 'activate' of hardware 'ur10'
[driver] [controller_stopper_node-4] [0m[INFO] [1778227104.881832555] [Controller stopper]: Service available[0m
[driver] [controller_stopper_node-4] [0m[INFO] [1778227104.881862169] [Controller stopper]: Waiting for list controllers service to come up on controller_manager/list_controllers[0m
[driver] [controller_stopper_node-4] [0m[INFO] [1778227104.881869343] [Controller stopper]: Service available[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227104.888450051] [UR_Client_Library:]: SCHED_FIFO OK, priority 99
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.078643978] [controller_manager]: Loading controller 'joint_trajectory_controller'
[driver] [ur_ros2_control_node-1] [WARN] [1778227105.090502581] [joint_trajectory_controller]: [Deprecated]: "allow_nonzero_velocity_at_trajectory_end" is set to true. The default behavior will change to false.
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.096846412] [controller_manager]: Loading controller 'joint_state_broadcaster'
[driver] [spawner-9] [INFO] [1778227105.097780179] [spawner_joint_trajectory_controller]: [94mLoaded [1mjoint_trajectory_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.112682253] [controller_manager]: Configuring controller 'joint_trajectory_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.112864777] [joint_trajectory_controller]: No specific joint names are used for command interfaces. Using 'joints' parameter.
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.112878143] [joint_trajectory_controller]: Command interfaces are [position] and state interfaces are [position velocity].
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.112891140] [joint_trajectory_controller]: Using 'splines' interpolation method.
[driver] [spawner-8] [INFO] [1778227105.113310299] [spawner_joint_state_broadcaster]: [94mLoaded [1mjoint_state_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.114133658] [joint_trajectory_controller]: Controller state will be published at 100.00 Hz.
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.117816482] [joint_trajectory_controller]: Action status changes will be monitored at 20.00 Hz.
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.130562382] [controller_manager]: Loading controller 'forward_velocity_controller'
[driver] [spawner-9] [INFO] [1778227105.145169376] [spawner_joint_trajectory_controller]: [94mLoaded [1mforward_velocity_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.145854885] [controller_manager]: Configuring controller 'forward_velocity_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.147651820] [forward_velocity_controller]: configure successful
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.153980910] [controller_manager]: Loading controller 'forward_position_controller'
[driver] [spawner-9] [INFO] [1778227105.169275532] [spawner_joint_trajectory_controller]: [94mLoaded [1mforward_position_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.169965772] [controller_manager]: Configuring controller 'forward_position_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.170502353] [forward_position_controller]: configure successful
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.177577438] [controller_manager]: Loading controller 'forward_effort_controller'
[driver] [spawner-9] [INFO] [1778227105.193289183] [spawner_joint_trajectory_controller]: [94mLoaded [1mforward_effort_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.193595248] [controller_manager]: Configuring controller 'forward_effort_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.194041734] [forward_effort_controller]: configure successful
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.200970255] [controller_manager]: Configuring controller 'joint_state_broadcaster'
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.201031036] [joint_state_broadcaster]: 'joints' or 'interfaces' parameter is empty. All available state interfaces will be published
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.209513257] [controller_manager]: Loading controller 'force_mode_controller'
[driver] [spawner-9] [INFO] [1778227105.233484564] [spawner_joint_trajectory_controller]: [94mLoaded [1mforce_mode_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.248895671] [controller_manager]: Configuring controller 'force_mode_controller'
[driver] [spawner-8] [INFO] [1778227105.249323839] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mjoint_state_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.258774013] [controller_manager]: Loading controller 'io_and_status_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.273090554] [controller_manager]: Loading controller 'passthrough_trajectory_controller'
[driver] [spawner-8] [INFO] [1778227105.273349091] [spawner_joint_state_broadcaster]: [94mLoaded [1mio_and_status_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.280896399] [controller_manager]: Configuring controller 'io_and_status_controller'
[driver] [spawner-9] [INFO] [1778227105.281182427] [spawner_joint_trajectory_controller]: [94mLoaded [1mpassthrough_trajectory_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.288856672] [controller_manager]: Configuring controller 'passthrough_trajectory_controller'
[driver] [robot_state_helper-3] [INFO] [1778227105.313001300] [robot_state_helper]: The robot is currently in mode RUNNING.
[driver] [robot_state_helper-3] [INFO] [1778227105.313012027] [robot_state_helper]: The robot is currently in safety mode NORMAL.
[driver] [spawner-8] [INFO] [1778227105.313186372] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mio_and_status_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.314444029] [controller_manager]: Loading controller 'freedrive_mode_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.328806589] [controller_manager]: Loading controller 'speed_scaling_state_broadcaster'
[driver] [spawner-9] [INFO] [1778227105.329149469] [spawner_joint_trajectory_controller]: [94mLoaded [1mfreedrive_mode_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.340672039] [speed_scaling_state_broadcaster]: Loading UR SpeedScalingStateBroadcaster with tf_prefix:
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.344789356] [controller_manager]: Configuring controller 'freedrive_mode_controller'
[driver] [spawner-8] [INFO] [1778227105.345154332] [spawner_joint_state_broadcaster]: [94mLoaded [1mspeed_scaling_state_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.352911337] [controller_manager]: Configuring controller 'speed_scaling_state_broadcaster'
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.352975587] [speed_scaling_state_broadcaster]: Publisher rate set to : 100.0 Hz
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.362864637] [controller_manager]: Loading controller 'tool_contact_controller'
[driver] [spawner-9] [INFO] [1778227105.386095726] [spawner_joint_trajectory_controller]: [94mLoaded [1mtool_contact_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.387421107] [controller_manager]: Configuring controller 'tool_contact_controller'
[driver] [spawner-8] [INFO] [1778227105.420969371] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mspeed_scaling_state_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.427114014] [controller_manager]: Loading controller 'force_torque_sensor_broadcaster'
[driver] [spawner-8] [INFO] [1778227105.466129926] [spawner_joint_state_broadcaster]: [94mLoaded [1mforce_torque_sensor_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.466838853] [controller_manager]: Configuring controller 'force_torque_sensor_broadcaster'
[driver] [spawner-8] [INFO] [1778227105.489550191] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mforce_torque_sensor_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.491822586] [controller_manager]: Loading controller 'tcp_pose_broadcaster'
[driver] [spawner-8] [INFO] [1778227105.513193414] [spawner_joint_state_broadcaster]: [94mLoaded [1mtcp_pose_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.513560565] [controller_manager]: Configuring controller 'tcp_pose_broadcaster'
[driver] [spawner-8] [INFO] [1778227105.537508494] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mtcp_pose_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.539513030] [controller_manager]: Loading controller 'ur_configuration_controller'
[driver] [spawner-8] [INFO] [1778227105.553803137] [spawner_joint_state_broadcaster]: [94mLoaded [1mur_configuration_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.554608610] [controller_manager]: Configuring controller 'ur_configuration_controller'
[driver] [spawner-8] [INFO] [1778227105.577431585] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mur_configuration_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.579108376] [controller_manager]: Loading controller 'scaled_joint_trajectory_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.593516721] [scaled_joint_trajectory_controller]: Using scaling state from the hardware from interface speed_scaling/speed_scaling_factor.
[driver] [INFO] [spawner-9]: process has finished cleanly [pid 26193]
[driver] [ur_ros2_control_node-1] [WARN] [1778227105.604461801] [scaled_joint_trajectory_controller]: [Deprecated]: "allow_nonzero_velocity_at_trajectory_end" is set to true. The default behavior will change to false.
[driver] [spawner-8] [INFO] [1778227105.609385037] [spawner_joint_state_broadcaster]: [94mLoaded [1mscaled_joint_trajectory_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.610309279] [controller_manager]: Configuring controller 'scaled_joint_trajectory_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.610528944] [scaled_joint_trajectory_controller]: No specific joint names are used for command interfaces. Using 'joints' parameter.
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.610546131] [scaled_joint_trajectory_controller]: Command interfaces are [position] and state interfaces are [position velocity].
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.610558236] [scaled_joint_trajectory_controller]: Using 'splines' interpolation method.
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.611439648] [scaled_joint_trajectory_controller]: Controller state will be published at 100.00 Hz.
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.614272330] [scaled_joint_trajectory_controller]: Action status changes will be monitored at 20.00 Hz.
[driver] [spawner-8] [INFO] [1778227105.641344068] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mscaled_joint_trajectory_controller[0m
[driver] [INFO] [spawner-8]: process has finished cleanly [pid 26191]
[driver] [ur_ros2_control_node-1] [INFO] [1778227105.827215672] [controller_manager]: Switch controller timeout is set to 0, using default 1s!
[driver] [ur_ros2_control_node-1] [INFO] [1778227112.216850004] [UR_Client_Library:]: Robot requested program
[driver] [ur_ros2_control_node-1] [INFO] [1778227112.217179002] [UR_Client_Library:]: Sent program to robot
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.210669583] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.218913241] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.227002692] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.235375354] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.243624784] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.251998873] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.260087153] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.268555296] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.276562762] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.284850514] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.293020948] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.301147113] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.309425801] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.320493643] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.328527460] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.334412813] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.346299702] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.353392798] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.358900033] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.368057710] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.377086438] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.383606567] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.392745551] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.400352283] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.408498091] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.416657642] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.424996493] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.433318682] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.441446830] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.449738253] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.457773525] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.466148071] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.474315616] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.482308066] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.491013863] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.498723661] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.507017418] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.515396693] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.523775691] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.531744260] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.540151446] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.548256761] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227112.556422799] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[verify] checking WSL/Windows 50002, /joint_states, scaled controller and action...
[verify] === DRIVER PREFIX ===
[verify] /opt/ros/humble
[verify] === WSL2 NETWORK CHECK ===
[verify] WSL2_IP=172.17.201.231
[verify] WSL_50002_LISTENING
[verify] === WINDOWS PORTPROXY CHECK ===
[verify] POWERSHELL_EXE=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
[verify] 
[verify] 侦听 ipv4:                 连接到 ipv4:
[verify] 
[verify] 地址            端口        地址            端口
[verify] --------------- ----------  --------------- ----------
[verify] 10.160.9.100    50002       172.17.201.231  50002
[verify] 
[verify] ---NETSTAT---
[verify]   TCP    10.160.9.100:50002     0.0.0.0:0              LISTENING       21796
[verify]   TCP    127.0.0.1:50002        0.0.0.0:0              LISTENING       33388
[verify]   TCP    172.17.192.1:56216     172.17.201.231:50002   TIME_WAIT       0
[verify] WINDOWS_PORTPROXY_OK
[verify] WINDOWS_50002_LISTENING
[verify] === SCALED CONTROLLER AUTO-ACTIVATE ===
[verify] [96mjoint_trajectory_controller       [0m joint_trajectory_controller/JointTrajectoryController         [96minactive[0m
[verify] [96mforward_velocity_controller       [0m velocity_controllers/JointGroupVelocityController             [96minactive[0m
[verify] [96mforward_position_controller       [0m position_controllers/JointGroupPositionController             [96minactive[0m
[verify] [96mforward_effort_controller         [0m effort_controllers/JointGroupEffortController                 [96minactive[0m
[verify] [92mjoint_state_broadcaster           [0m joint_state_broadcaster/JointStateBroadcaster                 [92mactive  [0m
[verify] [96mforce_mode_controller             [0m ur_controllers/ForceModeController                            [96minactive[0m
[verify] [92mio_and_status_controller          [0m ur_controllers/GPIOController                                 [92mactive  [0m
[verify] [96mpassthrough_trajectory_controller [0m ur_controllers/PassthroughTrajectoryController                [96minactive[0m
[verify] [96mfreedrive_mode_controller         [0m ur_controllers/FreedriveModeController                        [96minactive[0m
[verify] [92mspeed_scaling_state_broadcaster   [0m ur_controllers/SpeedScalingStateBroadcaster                   [92mactive  [0m
[verify] [96mtool_contact_controller           [0m ur_controllers/ToolContactController                          [96minactive[0m
[verify] [92mforce_torque_sensor_broadcaster   [0m force_torque_sensor_broadcaster/ForceTorqueSensorBroadcaster  [92mactive  [0m
[verify] [92mtcp_pose_broadcaster              [0m pose_broadcaster/PoseBroadcaster                              [92mactive  [0m
[verify] [92mur_configuration_controller       [0m ur_controllers/URConfigurationController                      [92mactive  [0m
[verify] [96mscaled_joint_trajectory_controller[0m ur_controllers/ScaledJointTrajectoryController                [96minactive[0m
[verify] SWITCH_SCALED_ATTEMPTED
[verify] Successfully switched controllers
[verify] === UR10 REAL READY CHECK START ===
[verify] [CMD] ros2 topic info /joint_states -v
[verify] Type: sensor_msgs/msg/JointState
[verify] 
[verify] Publisher count: 1
[verify] 
[verify] Node name: joint_state_broadcaster
[verify] Node namespace: /
[verify] Topic type: sensor_msgs/msg/JointState
[verify] Endpoint type: PUBLISHER
[verify] GID: 01.0f.76.c4.1a.66.f5.0a.00.00.00.00.00.00.86.03.00.00.00.00.00.00.00.00
[verify] QoS profile:
[verify]   Reliability: RELIABLE
[verify]   History (Depth): UNKNOWN
[verify]   Durability: TRANSIENT_LOCAL
[verify]   Lifespan: Infinite
[verify]   Deadline: Infinite
[verify]   Liveliness: AUTOMATIC
[verify]   Liveliness lease duration: Infinite
[verify] 
[verify] Subscription count: 1
[verify] 
[verify] Node name: robot_state_publisher
[verify] Node namespace: /
[verify] Topic type: sensor_msgs/msg/JointState
[verify] Endpoint type: SUBSCRIPTION
[verify] GID: 01.0f.76.c4.35.66.06.1f.00.00.00.00.00.00.15.04.00.00.00.00.00.00.00.00
[verify] QoS profile:
[verify]   Reliability: BEST_EFFORT
[verify]   History (Depth): UNKNOWN
[verify]   Durability: VOLATILE
[verify]   Lifespan: Infinite
[verify]   Deadline: Infinite
[verify]   Liveliness: AUTOMATIC
[verify]   Liveliness lease duration: Infinite
[verify] 
[verify] A message was lost!!!
[verify] 	total count change:1
[verify] 	total count: 1---
[verify] header:
[verify]   stamp:
[verify]     sec: 1778227121
[verify]     nanosec: 696488048
[verify]   frame_id: base_link
[verify] name:
[verify] - shoulder_lift_joint
[verify] - elbow_joint
[verify] - wrist_1_joint
[verify] - wrist_2_joint
[verify] - wrist_3_joint
[verify] - shoulder_pan_joint
[verify] position:
[verify] - 0.177232027053833
[verify] - -2.38171893755068
[verify] - -0.9147594610797327
[verify] - 3.614541530609131
[verify] - 0.5580821633338928
[verify] - 1.6996219158172607
[verify] velocity:
[verify] - 0.0
[verify] - -0.0
[verify] - 0.0
[verify] - 0.0
[verify] - 0.0
[verify] - 0.0
[verify] effort:
[verify] - 4.023743152618408
[verify] - -1.8876044750213623
[verify] - 0.2310333549976349
[verify] - 0.0426178015768528
[verify] - 0.01794433780014515
[verify] - 0.0686645582318306
[verify] ---
[verify] JOINT_STATES_OK
[verify] /controller_manager
[verify] /controller_stopper
[verify] /dashboard_client
[verify] /force_mode_controller
[verify] /force_torque_sensor_broadcaster
[verify] /forward_effort_controller
[verify] /forward_position_controller
[verify] /forward_velocity_controller
[verify] /freedrive_mode_controller
[verify] /io_and_status_controller
[verify] /joint_state_broadcaster
[verify] /joint_trajectory_controller
[verify] /passthrough_trajectory_controller
[verify] /robot_state_publisher
[verify] /scaled_joint_trajectory_controller
[verify] /speed_scaling_state_broadcaster
[verify] /tcp_pose_broadcaster
[verify] /tool_contact_controller
[verify] /trajectory_until_node
[verify] /transform_listener_impl_7548902406e0
[verify] /ur_configuration_controller
[verify] /ur_robot_state_helper
[verify] /urscript_interface
[verify] /dynamic_joint_states
[verify] /joint_states
[verify] [96mjoint_trajectory_controller       [0m joint_trajectory_controller/JointTrajectoryController         [96minactive[0m
[verify] [96mforward_velocity_controller       [0m velocity_controllers/JointGroupVelocityController             [96minactive[0m
[verify] [96mforward_position_controller       [0m position_controllers/JointGroupPositionController             [96minactive[0m
[verify] [96mforward_effort_controller         [0m effort_controllers/JointGroupEffortController                 [96minactive[0m
[verify] [92mjoint_state_broadcaster           [0m joint_state_broadcaster/JointStateBroadcaster                 [92mactive  [0m
[verify] [96mforce_mode_controller             [0m ur_controllers/ForceModeController                            [96minactive[0m
[verify] [92mio_and_status_controller          [0m ur_controllers/GPIOController                                 [92mactive  [0m
[verify] [96mpassthrough_trajectory_controller [0m ur_controllers/PassthroughTrajectoryController                [96minactive[0m
[verify] [96mfreedrive_mode_controller         [0m ur_controllers/FreedriveModeController                        [96minactive[0m
[verify] [92mspeed_scaling_state_broadcaster   [0m ur_controllers/SpeedScalingStateBroadcaster                   [92mactive  [0m
[verify] [96mtool_contact_controller           [0m ur_controllers/ToolContactController                          [96minactive[0m
[verify] [92mforce_torque_sensor_broadcaster   [0m force_torque_sensor_broadcaster/ForceTorqueSensorBroadcaster  [92mactive  [0m
[verify] [92mtcp_pose_broadcaster              [0m pose_broadcaster/PoseBroadcaster                              [92mactive  [0m
[verify] [92mur_configuration_controller       [0m ur_controllers/URConfigurationController                      [92mactive  [0m
[verify] [92mscaled_joint_trajectory_controller[0m ur_controllers/ScaledJointTrajectoryController                [92mactive  [0m
[verify] /joint_trajectory_controller/follow_joint_trajectory
[verify] /passthrough_trajectory_controller/follow_joint_trajectory
[verify] /scaled_joint_trajectory_controller/follow_joint_trajectory
[verify] CONTROLLER_NOT_ACTIVE
[verify] ACTION_ONLINE
[verify] === UR10 REAL READY CHECK END ===
[verify]
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.788067071] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.796358667] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.804347551] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.812652737] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.820881957] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.829058034] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.839920038] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.847237081] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.855223972] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.862281845] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.872731978] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.878617216] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.887140546] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.895080379] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.903704500] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.912467294] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.919956707] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.928196487] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.936447062] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.944628750] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.956220315] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.975214773] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.975438348] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.977849323] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227143.985410113] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.004388194] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.004541114] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.015309294] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.020150296] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.026568449] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.034819756] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.045495198] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.051820725] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.060743106] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.067792554] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.075943449] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.084156414] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.095766010] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.100584104] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.108906770] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.117260598] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.125778224] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.133537334] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.142843066] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.149939337] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.158355105] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.166555062] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.174820012] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227144.182861332] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>