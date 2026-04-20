# generated from colcon_powershell/shell/template/prefix_chain.ps1.em

# This script extends the environment with the environment of other prefix
# paths which were sourced when this file was generated as well as all packages
# contained in this prefix path.

# function to source another script with conditional trace output
# first argument: the path of the script
function _colcon_prefix_chain_powershell_source_script {
  param (
    $_colcon_prefix_chain_powershell_source_script_param
  )
  # source script with conditional trace output
  if (Test-Path $_colcon_prefix_chain_powershell_source_script_param) {
    if ($env:COLCON_TRACE) {
      echo ". '$_colcon_prefix_chain_powershell_source_script_param'"
    }
    . "$_colcon_prefix_chain_powershell_source_script_param"
  } else {
    Write-Error "not found: '$_colcon_prefix_chain_powershell_source_script_param'"
  }
}

# source chained prefixes
_colcon_prefix_chain_powershell_source_script "/opt/ros/humble\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/srdfdom\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/setup.zsh\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/setup.sh\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/setup.ps1\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/setup.bash\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/rviz_marker_tools\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/ruckig\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/random_numbers\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/pilz_industrial_motion_planner_testutils\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/pilz_industrial_motion_planner\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/ompl\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_task_constructor_msgs\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_simple_controller_manager\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_ros_warehouse\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_ros_robot_interaction\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_ros_planning_interface\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_ros_planning\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_ros_occupancy_map_monitor\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_ros_move_group\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_resources_prbt_support\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_resources_prbt_pg70_support\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_resources_prbt_moveit_config\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_resources_prbt_ikfast_manipulator_plugin\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_resources_pr2_description\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_resources_panda_moveit_config\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_resources_panda_description\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_resources_fanuc_moveit_config\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_resources_fanuc_description\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_py\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_planners_ompl\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_planners_chomp\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_msgs\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_kinematics\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_core\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_configs_utils\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/moveit_common\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/local_setup.zsh\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/local_setup.sh\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/local_setup.ps1\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/local_setup.bash\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/geometric_shapes\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/chomp_motion_planner\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/_local_setup_util_sh.py\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/_local_setup_util_ps1.py\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/moveit_ws/install/COLCON_IGNORE\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/ur10_simulation_bringup\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/ur10_perception\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/ur10_moveit_config\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/ur10_examples_py\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/ur10_examples\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/ur10_description\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/setup.zsh\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/setup.sh\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/setup.ps1\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/setup.bash\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/local_setup.zsh\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/local_setup.sh\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/local_setup.ps1\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/local_setup.bash\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/_local_setup_util_sh.py\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/_local_setup_util_ps1.py\local_setup.ps1"
_colcon_prefix_chain_powershell_source_script "/root/ur10_ws/install/COLCON_IGNORE\local_setup.ps1"

# source this prefix
$env:COLCON_CURRENT_PREFIX=(Split-Path $PSCommandPath -Parent)
_colcon_prefix_chain_powershell_source_script "$env:COLCON_CURRENT_PREFIX\local_setup.ps1"
