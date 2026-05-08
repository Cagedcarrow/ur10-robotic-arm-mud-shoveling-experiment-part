[init] GUI ready. 正式姿态来源: ur_robot_driver /joint_states
[operator] 等待 50002 监听后，在 CB3 示教器点击运行 External Control 程序。
[driver] START
[driver] DRIVER_PREFIX=/opt/ros/humble
[driver] [INFO] [launch]: All log files can be found below /root/.ros/log/2026-05-08-16-02-25-818199-Caged-sparrow-28014
[driver] [INFO] [launch]: Default logging verbosity is set to INFO
[driver] [INFO] [dashboard_client-2]: process started with pid [28052]
[driver] [INFO] [controller_stopper_node-4]: process started with pid [28056]
[driver] [INFO] [ur_ros2_control_node-1]: process started with pid [28050]
[driver] [INFO] [robot_state_helper-3]: process started with pid [28054]
[driver] [INFO] [urscript_interface-5]: process started with pid [28058]
[driver] [INFO] [robot_state_publisher-6]: process started with pid [28060]
[driver] [INFO] [trajectory_until_node-7]: process started with pid [28062]
[driver] [INFO] [spawner-8]: process started with pid [28072]
[driver] [INFO] [spawner-9]: process started with pid [28090]
[driver] [robot_state_helper-3] [INFO] [1778227346.164630293] [UR_Client_Library:]: Starting primary client pipeline
[driver] [controller_stopper_node-4] [0m[INFO] [1778227346.206868647] [Controller stopper]: Waiting for switch controller service to come up on controller_manager/switch_controller[0m
[driver] [dashboard_client-2] [0m[INFO] [1778227346.207865984] [UR_Client_Library:]: Starting primary client pipeline[0m
[driver] [ur_ros2_control_node-1] [WARN] [1778227346.213180222] [controller_manager]: [Deprecated] Passing the robot description parameter directly to the control_manager node is deprecated. Use '~/robot_description' topic from 'robot_state_publisher' instead.
[driver] [ur_ros2_control_node-1] text not specified in the tf_prefix tag
[driver] [ur_ros2_control_node-1] [INFO] [1778227346.214440325] [resource_manager]: Loading hardware 'ur10'
[driver] [ur_ros2_control_node-1] [INFO] [1778227346.220819116] [resource_manager]: Initialize hardware 'ur10'
[driver] [ur_ros2_control_node-1] [INFO] [1778227346.221198066] [resource_manager]: Successful initialization of hardware 'ur10'
[driver] [robot_state_publisher-6] [INFO] [1778227346.221728594] [robot_state_publisher]: got segment base
[driver] [robot_state_publisher-6] [INFO] [1778227346.221823542] [robot_state_publisher]: got segment base_link
[driver] [robot_state_publisher-6] [INFO] [1778227346.221830596] [robot_state_publisher]: got segment base_link_inertia
[driver] [robot_state_publisher-6] [INFO] [1778227346.221833928] [robot_state_publisher]: got segment flange
[driver] [robot_state_publisher-6] [INFO] [1778227346.221836545] [robot_state_publisher]: got segment forearm_link
[driver] [robot_state_publisher-6] [INFO] [1778227346.221839281] [robot_state_publisher]: got segment ft_frame
[driver] [robot_state_publisher-6] [INFO] [1778227346.221841653] [robot_state_publisher]: got segment shoulder_link
[driver] [robot_state_publisher-6] [INFO] [1778227346.221844207] [robot_state_publisher]: got segment tool0
[driver] [robot_state_publisher-6] [INFO] [1778227346.221846576] [robot_state_publisher]: got segment upper_arm_link
[driver] [robot_state_publisher-6] [INFO] [1778227346.221849025] [robot_state_publisher]: got segment world
[driver] [robot_state_publisher-6] [INFO] [1778227346.221851421] [robot_state_publisher]: got segment wrist_1_link
[driver] [robot_state_publisher-6] [INFO] [1778227346.221853767] [robot_state_publisher]: got segment wrist_2_link
[driver] [robot_state_publisher-6] [INFO] [1778227346.221856055] [robot_state_publisher]: got segment wrist_3_link
[driver] [ur_ros2_control_node-1] [INFO] [1778227346.221881330] [resource_manager]: 'configure' hardware 'ur10'
[driver] [ur_ros2_control_node-1] [INFO] [1778227346.221895438] [URPositionHardwareInterface]: Starting ...please wait...
[driver] [ur_ros2_control_node-1] [INFO] [1778227346.221906827] [URPositionHardwareInterface]: Initializing driver...
[driver] [ur_ros2_control_node-1] [INFO] [1778227346.223366268] [UR_Client_Library:]: SCHED_FIFO OK, priority 99
[driver] [ur_ros2_control_node-1] [INFO] [1778227346.292433770] [UR_Client_Library:]: Negotiated RTDE protocol version to 2.
[driver] [ur_ros2_control_node-1] [INFO] [1778227346.296175071] [UR_Client_Library:]: Setting up RTDE communication with frequency 125.000000
[driver] [dashboard_client-2] [0m[INFO] [1778227346.665951014] [dashboard_client]: Connecting to Dashboard Server at 10.160.9.21 with policy G5[0m
[driver] [dashboard_client-2] [0m[INFO] [1778227346.666228768] [UR_Client_Library:]: DashboardClient created for host 10.160.9.21[0m
[driver] [dashboard_client-2] [0m[INFO] [1778227346.667669039] [UR_Client_Library:]: Connected: Universal Robots Dashboard Server
[driver] [dashboard_client-2] [0m
[driver] [spawner-8] [INFO] [1778227346.862647523] [spawner_joint_state_broadcaster]: waiting for service /controller_manager/list_controllers to become available...
[driver] [spawner-9] [INFO] [1778227346.882026293] [spawner_joint_trajectory_controller]: waiting for service /controller_manager/list_controllers to become available...
[driver] [ur_ros2_control_node-1] [INFO] [1778227347.333400692] [UR_Client_Library:]: Starting primary client pipeline
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.052770770] [URPositionHardwareInterface]: Calibration checksum: 'calib_17227329492635474227'.
[driver] [ur_ros2_control_node-1] [ERROR] [1778227348.052859227] [URPositionHardwareInterface]: The calibration parameters of the connected robot don't match the ones from the given kinematics config file. Please be aware that this can lead to critical inaccuracies of tcp positions. Use the ur_calibration tool to extract the correct calibration from the robot and pass that into the description. See [https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver/blob/main/ur_calibration/README.md] for details.
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.052981394] [URPositionHardwareInterface]: System successfully started!
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.053006137] [resource_manager]: Successful 'configure' of hardware 'ur10'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.053136485] [resource_manager]: 'activate' hardware 'ur10'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.053160817] [URPositionHardwareInterface]: Activating HW interface
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.053167973] [resource_manager]: Successful 'activate' of hardware 'ur10'
[driver] [controller_stopper_node-4] [0m[INFO] [1778227348.057726271] [Controller stopper]: Service available[0m
[driver] [controller_stopper_node-4] [0m[INFO] [1778227348.057757961] [Controller stopper]: Waiting for list controllers service to come up on controller_manager/list_controllers[0m
[driver] [controller_stopper_node-4] [0m[INFO] [1778227348.057766678] [Controller stopper]: Service available[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.059807639] [UR_Client_Library:]: SCHED_FIFO OK, priority 99
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.118464697] [controller_manager]: Loading controller 'joint_state_broadcaster'
[driver] [spawner-8] [INFO] [1778227348.132671348] [spawner_joint_state_broadcaster]: [94mLoaded [1mjoint_state_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.133472259] [controller_manager]: Configuring controller 'joint_state_broadcaster'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.133535510] [joint_state_broadcaster]: 'joints' or 'interfaces' parameter is empty. All available state interfaces will be published
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.224191375] [controller_manager]: Loading controller 'joint_trajectory_controller'
[driver] [ur_ros2_control_node-1] [WARN] [1778227348.232306596] [joint_trajectory_controller]: [Deprecated]: "allow_nonzero_velocity_at_trajectory_end" is set to true. The default behavior will change to false.
[driver] [spawner-9] [INFO] [1778227348.236779670] [spawner_joint_trajectory_controller]: [94mLoaded [1mjoint_trajectory_controller[0m
[driver] [spawner-8] [INFO] [1778227348.253495447] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mjoint_state_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.256069472] [controller_manager]: Loading controller 'io_and_status_controller'
[driver] [spawner-8] [INFO] [1778227348.268372490] [spawner_joint_state_broadcaster]: [94mLoaded [1mio_and_status_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.268649740] [controller_manager]: Configuring controller 'io_and_status_controller'
[driver] [spawner-8] [INFO] [1778227348.292796587] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mio_and_status_controller[0m
[driver] [robot_state_helper-3] [INFO] [1778227348.293442434] [robot_state_helper]: The robot is currently in mode RUNNING.
[driver] [robot_state_helper-3] [INFO] [1778227348.293458853] [robot_state_helper]: The robot is currently in safety mode NORMAL.
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.294268086] [controller_manager]: Loading controller 'speed_scaling_state_broadcaster'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.300315412] [speed_scaling_state_broadcaster]: Loading UR SpeedScalingStateBroadcaster with tf_prefix:
[driver] [spawner-8] [INFO] [1778227348.308449798] [spawner_joint_state_broadcaster]: [94mLoaded [1mspeed_scaling_state_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.308821061] [controller_manager]: Configuring controller 'speed_scaling_state_broadcaster'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.308958834] [speed_scaling_state_broadcaster]: Publisher rate set to : 100.0 Hz
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.332038053] [controller_manager]: Configuring controller 'joint_trajectory_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.332267405] [joint_trajectory_controller]: No specific joint names are used for command interfaces. Using 'joints' parameter.
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.332292979] [joint_trajectory_controller]: Command interfaces are [position] and state interfaces are [position velocity].
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.332311590] [joint_trajectory_controller]: Using 'splines' interpolation method.
[driver] [spawner-8] [INFO] [1778227348.332695759] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mspeed_scaling_state_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.333497661] [joint_trajectory_controller]: Controller state will be published at 100.00 Hz.
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.336853176] [joint_trajectory_controller]: Action status changes will be monitored at 20.00 Hz.
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.351093081] [controller_manager]: Loading controller 'force_torque_sensor_broadcaster'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.380364133] [controller_manager]: Loading controller 'forward_velocity_controller'
[driver] [spawner-8] [INFO] [1778227348.380574223] [spawner_joint_state_broadcaster]: [94mLoaded [1mforce_torque_sensor_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.388053889] [controller_manager]: Configuring controller 'force_torque_sensor_broadcaster'
[driver] [spawner-9] [INFO] [1778227348.388403089] [spawner_joint_trajectory_controller]: [94mLoaded [1mforward_velocity_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.396016600] [controller_manager]: Configuring controller 'forward_velocity_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.397035830] [forward_velocity_controller]: configure successful
[driver] [spawner-8] [INFO] [1778227348.420398190] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mforce_torque_sensor_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.420997992] [controller_manager]: Loading controller 'forward_position_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.436084314] [controller_manager]: Loading controller 'tcp_pose_broadcaster'
[driver] [spawner-9] [INFO] [1778227348.436559769] [spawner_joint_trajectory_controller]: [94mLoaded [1mforward_position_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.451982540] [controller_manager]: Configuring controller 'forward_position_controller'
[driver] [spawner-8] [INFO] [1778227348.452341748] [spawner_joint_state_broadcaster]: [94mLoaded [1mtcp_pose_broadcaster[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.452434840] [forward_position_controller]: configure successful
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.460359231] [controller_manager]: Configuring controller 'tcp_pose_broadcaster'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.486340816] [controller_manager]: Loading controller 'forward_effort_controller'
[driver] [spawner-8] [INFO] [1778227348.487234568] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mtcp_pose_broadcaster[0m
[driver] [spawner-9] [INFO] [1778227348.517723292] [spawner_joint_trajectory_controller]: [94mLoaded [1mforward_effort_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.518347161] [controller_manager]: Configuring controller 'forward_effort_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.519418283] [forward_effort_controller]: configure successful
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.524432065] [controller_manager]: Loading controller 'ur_configuration_controller'
[driver] [spawner-8] [INFO] [1778227348.540672474] [spawner_joint_state_broadcaster]: [94mLoaded [1mur_configuration_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.541212705] [controller_manager]: Loading controller 'force_mode_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.556215881] [controller_manager]: Configuring controller 'ur_configuration_controller'
[driver] [spawner-9] [INFO] [1778227348.556554173] [spawner_joint_trajectory_controller]: [94mLoaded [1mforce_mode_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.564210302] [controller_manager]: Configuring controller 'force_mode_controller'
[driver] [spawner-8] [INFO] [1778227348.596659114] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mur_configuration_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.597291460] [controller_manager]: Loading controller 'passthrough_trajectory_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.612174546] [controller_manager]: Loading controller 'scaled_joint_trajectory_controller'
[driver] [spawner-9] [INFO] [1778227348.612526847] [spawner_joint_trajectory_controller]: [94mLoaded [1mpassthrough_trajectory_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.630739595] [scaled_joint_trajectory_controller]: Using scaling state from the hardware from interface speed_scaling/speed_scaling_factor.
[driver] [ur_ros2_control_node-1] [WARN] [1778227348.636755738] [scaled_joint_trajectory_controller]: [Deprecated]: "allow_nonzero_velocity_at_trajectory_end" is set to true. The default behavior will change to false.
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.643967265] [controller_manager]: Configuring controller 'passthrough_trajectory_controller'
[driver] [spawner-8] [INFO] [1778227348.644438309] [spawner_joint_state_broadcaster]: [94mLoaded [1mscaled_joint_trajectory_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.652327903] [controller_manager]: Configuring controller 'scaled_joint_trajectory_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.652459035] [scaled_joint_trajectory_controller]: No specific joint names are used for command interfaces. Using 'joints' parameter.
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.652470330] [scaled_joint_trajectory_controller]: Command interfaces are [position] and state interfaces are [position velocity].
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.652487366] [scaled_joint_trajectory_controller]: Using 'splines' interpolation method.
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.653091857] [scaled_joint_trajectory_controller]: Controller state will be published at 100.00 Hz.
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.654905709] [scaled_joint_trajectory_controller]: Action status changes will be monitored at 20.00 Hz.
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.661589645] [controller_manager]: Loading controller 'freedrive_mode_controller'
[driver] [spawner-9] [INFO] [1778227348.676853505] [spawner_joint_trajectory_controller]: [94mLoaded [1mfreedrive_mode_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.692414375] [controller_manager]: Configuring controller 'freedrive_mode_controller'
[driver] [spawner-8] [INFO] [1778227348.692779219] [spawner_joint_state_broadcaster]: [92mConfigured and activated [1mscaled_joint_trajectory_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.707612008] [controller_manager]: Loading controller 'tool_contact_controller'
[driver] [spawner-9] [INFO] [1778227348.740930148] [spawner_joint_trajectory_controller]: [94mLoaded [1mtool_contact_controller[0m
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.742063957] [controller_manager]: Configuring controller 'tool_contact_controller'
[driver] [ur_ros2_control_node-1] [INFO] [1778227348.804057163] [controller_manager]: Switch controller timeout is set to 0, using default 1s!
[driver] [INFO] [spawner-8]: process has finished cleanly [pid 28072]
[driver] [INFO] [spawner-9]: process has finished cleanly [pid 28090]
[driver] [ur_ros2_control_node-1] [INFO] [1778227352.212595489] [UR_Client_Library:]: Robot requested program
[driver] [ur_ros2_control_node-1] [INFO] [1778227352.212799510] [UR_Client_Library:]: Sent program to robot
[verify] checking WSL/Windows 50002, /joint_states, scaled controller and action...
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.123553023] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.131859325] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.141072365] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.148353414] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.156578861] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.165862744] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.173319245] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.181077812] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.189308641] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.197558699] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.205870722] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.214031648] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.222270759] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.230508333] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.239720894] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.247448245] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.255161511] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.263546549] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.271749490] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.279979521] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.288101446] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.296220693] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.304599513] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.312571763] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.320895716] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.329080126] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.337430914] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.346759076] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.353783566] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.362084043] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.370305618] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.378434251] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.386630586] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.394946488] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.403434877] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.411301100] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.419630599] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.427814315] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.435955209] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.444254476] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.453931540] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.460654696] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.468906964] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.477126926] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227365.485588523] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
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
[verify]   TCP    172.17.192.1:63753     172.17.201.231:50002   TIME_WAIT       0
[verify] WINDOWS_PORTPROXY_OK
[verify] WINDOWS_50002_LISTENING
[verify] === SCALED CONTROLLER AUTO-ACTIVATE ===
[verify] [92mjoint_state_broadcaster           [0m joint_state_broadcaster/JointStateBroadcaster                 [92mactive  [0m
[verify] [92mio_and_status_controller          [0m ur_controllers/GPIOController                                 [92mactive  [0m
[verify] [92mspeed_scaling_state_broadcaster   [0m ur_controllers/SpeedScalingStateBroadcaster                   [92mactive  [0m
[verify] [96mjoint_trajectory_controller       [0m joint_trajectory_controller/JointTrajectoryController         [96minactive[0m
[verify] [92mforce_torque_sensor_broadcaster   [0m force_torque_sensor_broadcaster/ForceTorqueSensorBroadcaster  [92mactive  [0m
[verify] [96mforward_velocity_controller       [0m velocity_controllers/JointGroupVelocityController             [96minactive[0m
[verify] [96mforward_position_controller       [0m position_controllers/JointGroupPositionController             [96minactive[0m
[verify] [92mtcp_pose_broadcaster              [0m pose_broadcaster/PoseBroadcaster                              [92mactive  [0m
[verify] [96mforward_effort_controller         [0m effort_controllers/JointGroupEffortController                 [96minactive[0m
[verify] [92mur_configuration_controller       [0m ur_controllers/URConfigurationController                      [92mactive  [0m
[verify] [96mforce_mode_controller             [0m ur_controllers/ForceModeController                            [96minactive[0m
[verify] [96mpassthrough_trajectory_controller [0m ur_controllers/PassthroughTrajectoryController                [96minactive[0m
[verify] [96mscaled_joint_trajectory_controller[0m ur_controllers/ScaledJointTrajectoryController                [96minactive[0m
[verify] [96mfreedrive_mode_controller         [0m ur_controllers/FreedriveModeController                        [96minactive[0m
[verify] [96mtool_contact_controller           [0m ur_controllers/ToolContactController                          [96minactive[0m
[verify] SCALED_ALREADY_ACTIVE
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
[verify] GID: 01.0f.76.c4.92.6d.6b.32.00.00.00.00.00.00.36.03.00.00.00.00.00.00.00.00
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
[verify] GID: 01.0f.76.c4.9c.6d.e7.42.00.00.00.00.00.00.15.04.00.00.00.00.00.00.00.00
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
[verify]     sec: 1778227365
[verify]     nanosec: 603989551
[verify]   frame_id: base_link
[verify] name:
[verify] - shoulder_lift_joint
[verify] - elbow_joint
[verify] - wrist_1_joint
[verify] - wrist_2_joint
[verify] - wrist_3_joint
[verify] - shoulder_pan_joint
[verify] position:
[verify] - 0.1772080659866333
[verify] - -2.381730858479635
[verify] - -0.9147833029376429
[verify] - 3.6144936084747314
[verify] - 0.5580582022666931
[verify] - 1.6996219158172607
[verify] velocity:
[verify] - 0.0
[verify] - -0.0
[verify] - 0.0
[verify] - 0.0
[verify] - 0.0
[verify] - 0.0
[verify] effort:
[verify] - 3.987122058868408
[verify] - -1.8808790445327759
[verify] - 0.2243042290210724
[verify] - 0.0538330152630806
[verify] - 0.01345825381577015
[verify] - 0.009155274368822575
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
[verify] /transform_listener_impl_7e16143f9af0
[verify] /ur_configuration_controller
[verify] /ur_robot_state_helper
[verify] /urscript_interface
[verify] /dynamic_joint_states
[verify] /joint_states
[verify] [92mjoint_state_broadcaster           [0m joint_state_broadcaster/JointStateBroadcaster                 [92mactive  [0m
[verify] [92mio_and_status_controller          [0m ur_controllers/GPIOController                                 [92mactive  [0m
[verify] [92mspeed_scaling_state_broadcaster   [0m ur_controllers/SpeedScalingStateBroadcaster                   [92mactive  [0m
[verify] [96mjoint_trajectory_controller       [0m joint_trajectory_controller/JointTrajectoryController         [96minactive[0m
[verify] [92mforce_torque_sensor_broadcaster   [0m force_torque_sensor_broadcaster/ForceTorqueSensorBroadcaster  [92mactive  [0m
[verify] [96mforward_velocity_controller       [0m velocity_controllers/JointGroupVelocityController             [96minactive[0m
[verify] [96mforward_position_controller       [0m position_controllers/JointGroupPositionController             [96minactive[0m
[verify] [92mtcp_pose_broadcaster              [0m pose_broadcaster/PoseBroadcaster                              [92mactive  [0m
[verify] [96mforward_effort_controller         [0m effort_controllers/JointGroupEffortController                 [96minactive[0m
[verify] [92mur_configuration_controller       [0m ur_controllers/URConfigurationController                      [92mactive  [0m
[verify] [96mforce_mode_controller             [0m ur_controllers/ForceModeController                            [96minactive[0m
[verify] [96mpassthrough_trajectory_controller [0m ur_controllers/PassthroughTrajectoryController                [96minactive[0m
[verify] [96mscaled_joint_trajectory_controller[0m ur_controllers/ScaledJointTrajectoryController                [96minactive[0m
[verify] [96mfreedrive_mode_controller         [0m ur_controllers/FreedriveModeController                        [96minactive[0m
[verify] [96mtool_contact_controller           [0m ur_controllers/ToolContactController                          [96minactive[0m
[verify] /joint_trajectory_controller/follow_joint_trajectory
[verify] /passthrough_trajectory_controller/follow_joint_trajectory
[verify] /scaled_joint_trajectory_controller/follow_joint_trajectory
[verify] CONTROLLER_ACTIVE
[verify] ACTION_ONLINE
[verify] READY_FOR_RVIZ2_MOVEIT_EXECUTION
[verify] === UR10 REAL READY CHECK END ===
[verify]
[operator] RViz2 中使用 Start State = Current，只做小范围 Plan -> Execute。
[moveit] START
[moveit] [INFO] [launch]: All log files can be found below /root/.ros/log/2026-05-08-16-02-50-589804-Caged-sparrow-28449
[moveit] [INFO] [launch]: Default logging verbosity is set to INFO
[moveit] [INFO] [robot_state_publisher-1]: process started with pid [28478]
[moveit] [INFO] [move_group-2]: process started with pid [28480]
[moveit] [INFO] [rviz2-3]: process started with pid [28482]
[moveit] [robot_state_publisher-1] [WARN] [1778227370.930912262] [kdl_parser]: The root link base_jizuo has an inertia specified in the URDF, but KDL does not support a root link with an inertia.  As a workaround, you can add an extra dummy link to your URDF.
[moveit] [robot_state_publisher-1] [INFO] [1778227370.931022811] [robot_state_publisher]: got segment base_jizuo
[moveit] [robot_state_publisher-1] [INFO] [1778227370.931078575] [robot_state_publisher]: got segment base_jizuo_base_ur10_with_dizuo
[moveit] [robot_state_publisher-1] [INFO] [1778227370.931082783] [robot_state_publisher]: got segment sensor_shovel
[moveit] [robot_state_publisher-1] [INFO] [1778227370.931085514] [robot_state_publisher]: got segment sensor_shovel_tcp
[moveit] [robot_state_publisher-1] [INFO] [1778227370.931088085] [robot_state_publisher]: got segment ur10
[moveit] [robot_state_publisher-1] [INFO] [1778227370.931090633] [robot_state_publisher]: got segment ur10_forearm
[moveit] [robot_state_publisher-1] [INFO] [1778227370.931093098] [robot_state_publisher]: got segment ur10_shoulder
[moveit] [robot_state_publisher-1] [INFO] [1778227370.931095656] [robot_state_publisher]: got segment ur10_upper_arm
[moveit] [robot_state_publisher-1] [INFO] [1778227370.931098032] [robot_state_publisher]: got segment wrist_1_joint
[moveit] [robot_state_publisher-1] [INFO] [1778227370.931100394] [robot_state_publisher]: got segment wrist_2_joint
[moveit] [robot_state_publisher-1] [INFO] [1778227370.931102717] [robot_state_publisher]: got segment wrist_3_joint
[moveit] [move_group-2] Error:   Link 'ur10_wrist_3_link' specified as parent for end effector 'shovel_eef' is not known to the URDF
[moveit] [move_group-2]          at line 440 in /root/moveit_ws/src/srdfdom/src/model.cpp
[moveit] [move_group-2] Warning: Link 'ur10_wrist_1_link' is not known to URDF. Cannot disable/enable collisons.
[moveit] [move_group-2]          at line 594 in /root/moveit_ws/src/srdfdom/src/model.cpp
[moveit] [move_group-2] Warning: Link 'ur10_wrist_1_link' is not known to URDF. Cannot disable/enable collisons.
[moveit] [move_group-2]          at line 589 in /root/moveit_ws/src/srdfdom/src/model.cpp
[moveit] [move_group-2] Warning: Link 'ur10_wrist_2_link' is not known to URDF. Cannot disable/enable collisons.
[moveit] [move_group-2]          at line 589 in /root/moveit_ws/src/srdfdom/src/model.cpp
[moveit] [move_group-2] [INFO] [1778227371.018976010] [moveit_rdf_loader.rdf_loader]: Loaded robot model in 0.0095882 seconds
[moveit] [move_group-2] [INFO] [1778227371.019677426] [moveit_robot_model.robot_model]: Loading robot model 'assembly'...
[moveit] [rviz2-3] /opt/ros/humble/lib/rviz2/rviz2: symbol lookup error: /root/ur10_ws/.venv/lib/python3.10/site-packages/PyQt5/Qt5/plugins/platforms/../../lib/libQt5XcbQpa.so.5: undefined symbol: _ZdlPvm, version Qt_5
[moveit] [ERROR] [rviz2-3]: process has died [pid 28482, exit code 127, cmd '/opt/ros/humble/lib/rviz2/rviz2 -d /root/ur10_ws/install/ur10_assembly_real_control/share/ur10_assembly_real_control/config/moveit.rviz --ros-args -r __node:=rviz2 --params-file /tmp/launch_params_kl4sf5mc --params-file /tmp/launch_params_iteuyube --params-file /tmp/launch_params_eo4tz1id --params-file /tmp/launch_params_3w__n9hh --params-file /tmp/launch_params_3r9ghn70'].
[moveit] [move_group-2] [WARN] [1778227371.119782642] [kdl_parser]: The root link base_jizuo has an inertia specified in the URDF, but KDL does not support a root link with an inertia.  As a workaround, you can add an extra dummy link to your URDF.
[moveit] [move_group-2] [INFO] [1778227371.224404203] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Publishing maintained planning scene on 'monitored_planning_scene'
[moveit] [move_group-2] [INFO] [1778227371.224647780] [moveit.ros_planning_interface.moveit_cpp]: Listening to 'joint_states' for joint states
[moveit] [move_group-2] [INFO] [1778227371.225679112] [moveit_ros.current_state_monitor]: Listening to joint states on topic 'joint_states'
[moveit] [move_group-2] [INFO] [1778227371.228922083] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Listening to '/attached_collision_object' for attached collision objects
[moveit] [move_group-2] [INFO] [1778227371.229032077] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Starting planning scene monitor
[moveit] [move_group-2] [INFO] [1778227371.230017116] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Listening to '/planning_scene'
[moveit] [move_group-2] [INFO] [1778227371.230039000] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Starting world geometry update monitor for collision objects, attached objects, octomap updates.
[moveit] [move_group-2] [INFO] [1778227371.230684857] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Listening to 'collision_object'
[moveit] [move_group-2] [INFO] [1778227371.232118361] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Listening to 'planning_scene_world' for planning scene world geometry
[moveit] [move_group-2] [WARN] [1778227371.235172287] [moveit.ros.occupancy_map_monitor.middleware_handle]: Resolution not specified for Octomap. Assuming resolution = 0.1 instead
[moveit] [move_group-2] [ERROR] [1778227371.235222772] [moveit.ros.occupancy_map_monitor.middleware_handle]: No 3D sensor plugin(s) defined for octomap updates
[moveit] [move_group-2] [INFO] [1778227371.311949692] [moveit.ros_planning_interface.moveit_cpp]: Loading planning pipeline 'ompl'
[moveit] [move_group-2] [INFO] [1778227371.361735835] [moveit.ros_planning.planning_pipeline]: Using planning interface 'OMPL'
[moveit] [move_group-2] [INFO] [1778227371.371623676] [moveit_ros.add_time_optimal_parameterization]: Param 'ompl.path_tolerance' was not set. Using default value: 0.100000
[moveit] [move_group-2] [INFO] [1778227371.371675927] [moveit_ros.add_time_optimal_parameterization]: Param 'ompl.resample_dt' was not set. Using default value: 0.100000
[moveit] [move_group-2] [INFO] [1778227371.371679460] [moveit_ros.add_time_optimal_parameterization]: Param 'ompl.min_angle_change' was not set. Using default value: 0.001000
[moveit] [move_group-2] [INFO] [1778227371.371694060] [moveit_ros.fix_workspace_bounds]: Param 'ompl.default_workspace_bounds' was not set. Using default value: 10.000000
[moveit] [move_group-2] [INFO] [1778227371.371704744] [moveit_ros.fix_start_state_bounds]: Param 'ompl.start_state_max_bounds_error' was set to 0.100000
[moveit] [move_group-2] [INFO] [1778227371.371707260] [moveit_ros.fix_start_state_bounds]: Param 'ompl.start_state_max_dt' was not set. Using default value: 0.500000
[moveit] [move_group-2] [INFO] [1778227371.371713842] [moveit_ros.fix_start_state_collision]: Param 'ompl.start_state_max_dt' was not set. Using default value: 0.500000
[moveit] [move_group-2] [INFO] [1778227371.371716466] [moveit_ros.fix_start_state_collision]: Param 'ompl.jiggle_fraction' was not set. Using default value: 0.020000
[moveit] [move_group-2] [INFO] [1778227371.371732514] [moveit_ros.fix_start_state_collision]: Param 'ompl.max_sampling_attempts' was not set. Using default value: 100
[moveit] [move_group-2] [INFO] [1778227371.371739087] [moveit.ros_planning.planning_pipeline]: Using planning request adapter 'Add Time Optimal Parameterization'
[moveit] [move_group-2] [INFO] [1778227371.371742937] [moveit.ros_planning.planning_pipeline]: Using planning request adapter 'Fix Workspace Bounds'
[moveit] [move_group-2] [INFO] [1778227371.371744832] [moveit.ros_planning.planning_pipeline]: Using planning request adapter 'Fix Start State Bounds'
[moveit] [move_group-2] [INFO] [1778227371.371746370] [moveit.ros_planning.planning_pipeline]: Using planning request adapter 'Fix Start State In Collision'
[moveit] [move_group-2] [INFO] [1778227371.371747902] [moveit.ros_planning.planning_pipeline]: Using planning request adapter 'Fix Start State Path Constraints'
[moveit] [move_group-2] [INFO] [1778227371.404428143] [moveit.plugins.moveit_simple_controller_manager]: Added FollowJointTrajectory controller for scaled_joint_trajectory_controller
[moveit] [move_group-2] [INFO] [1778227371.404937125] [moveit.plugins.moveit_simple_controller_manager]: Returned 1 controllers in list
[moveit] [move_group-2] [INFO] [1778227371.405033987] [moveit.plugins.moveit_simple_controller_manager]: Returned 1 controllers in list
[moveit] [move_group-2] [INFO] [1778227371.405752110] [moveit_ros.trajectory_execution_manager]: Trajectory execution is not managing controllers
[moveit] [move_group-2] [INFO] [1778227371.405774558] [move_group.move_group]: MoveGroup debug mode is ON
[moveit] [move_group-2] [INFO] [1778227371.428749490] [move_group.move_group]:
[moveit] [move_group-2]
[moveit] [move_group-2] ********************************************************
[moveit] [move_group-2] * MoveGroup using:
[moveit] [move_group-2] *     - ApplyPlanningSceneService
[moveit] [move_group-2] *     - ClearOctomapService
[moveit] [move_group-2] *     - CartesianPathService
[moveit] [move_group-2] *     - ExecuteTrajectoryAction
[moveit] [move_group-2] *     - GetPlanningSceneService
[moveit] [move_group-2] *     - KinematicsService
[moveit] [move_group-2] *     - MoveAction
[moveit] [move_group-2] *     - MotionPlanService
[moveit] [move_group-2] *     - QueryPlannersService
[moveit] [move_group-2] *     - StateValidationService
[moveit] [move_group-2] ********************************************************
[moveit] [move_group-2]
[moveit] [move_group-2] [INFO] [1778227371.428791199] [moveit_move_group_capabilities_base.move_group_context]: MoveGroup context using planning plugin ompl_interface/OMPLPlanner
[moveit] [move_group-2] [INFO] [1778227371.428799775] [moveit_move_group_capabilities_base.move_group_context]: MoveGroup context initialization complete
[moveit] [move_group-2] [96mLoading 'move_group/ApplyPlanningSceneService'...
[moveit] [move_group-2] [0m[96mLoading 'move_group/ClearOctomapService'...
[moveit] [move_group-2] [0m[96mLoading 'move_group/MoveGroupCartesianPathService'...
[moveit] [move_group-2] [0m[96mLoading 'move_group/MoveGroupExecuteTrajectoryAction'...
[moveit] [move_group-2] [0m[96mLoading 'move_group/MoveGroupGetPlanningSceneService'...
[moveit] [move_group-2] [0m[96mLoading 'move_group/MoveGroupKinematicsService'...
[moveit] [move_group-2] [0m[96mLoading 'move_group/MoveGroupMoveAction'...
[moveit] [move_group-2] [0m[96mLoading 'move_group/MoveGroupPlanService'...
[moveit] [move_group-2] [0m[96mLoading 'move_group/MoveGroupQueryPlannersService'...
[moveit] [move_group-2] [0m[96mLoading 'move_group/MoveGroupStateValidationService'...
[moveit] [move_group-2] [0m[92m
[moveit] [move_group-2] You can start planning now!
[moveit] [move_group-2]
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.755964142] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.764543695] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.772498767] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.780675736] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.788597209] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.797080748] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.805257053] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.813490141] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.821630652] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.829872316] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.838039564] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.846464983] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.854535651] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.862896918] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.870914266] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.879481473] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.888351712] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.895933580] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.903861133] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.912272354] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.920437321] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.928617514] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.936857540] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.945318397] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.953207450] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.961329664] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.969957334] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.977777588] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.986188343] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227396.994390670] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.002598026] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.010825102] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.018869789] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.027245201] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.035470582] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.043481862] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.051695021] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.060077890] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.068413149] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.076601484] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.085165581] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.092787115] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.100994553] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.109361245] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>
[driver] [ur_ros2_control_node-1] [ERROR] [1778227397.117596460] [UR_Client_Library:]: Pipeline producer overflowed! <RTDE Data Pipeline>