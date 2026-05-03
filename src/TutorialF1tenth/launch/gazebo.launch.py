from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os, xacro
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.actions import ExecuteProcess


def generate_launch_description():
    share_dir = get_package_share_directory('TutorialF1tenth')
    pkg_parent_path = os.path.join(share_dir, '..')

    rviz_config_file = os.path.join(share_dir, 'config', 'default.rviz')

    set_gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[pkg_parent_path]
    )

    controller_params_file = os.path.join(
        get_package_share_directory('TutorialF1tenth'),
        'config',
        'f1tenth_controllers.yaml'
    )

    # 1. URDF Processing
    xacro_file = os.path.join(share_dir, 'urdf', 'racecar.xacro')
    robot_description_config = xacro.process_file(xacro_file)
    robot_urdf = robot_description_config.toxml()

    gui_arg = DeclareLaunchArgument("gui", default_value="true", description="Start Gazebo GUI")
    gui = LaunchConfiguration("gui")

    # 2. Gazebo Simulation Nodes
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
        ]),
        launch_arguments={
            "gz_args": [
                "-r -v 4 ",
                PathJoinSubstitution([
                    FindPackageShare("TutorialF1tenth"), 
                    "worlds", 
                    "demo_track.world" 
                ])
            ]
        }.items(),
        condition=IfCondition(gui),
    )

    # gazebo = IncludeLaunchDescription(
    # PythonLaunchDescriptionSource([
    #     PathJoinSubstitution([
    #         FindPackageShare("ros_gz_sim"),
    #         "launch",
    #         "gz_sim.launch.py"
    #     ])
    # ]),
    # launch_arguments={
    #     "gz_args": ["-r -v 4 empty.sdf"]
    # }.items(),
    # condition=IfCondition(gui),
    # )

    # 3. Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[{'robot_description': robot_urdf}]
    )

    # 4. Spawner Entity
    gz_spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-topic", "robot_description", 
            "-name", "f1tenth_robot", 
            "-allow_renaming", "true",
            "-z", "0.2", 
        ],
    )

    # 5. ROS GZ BRIDGE 
    gazebo_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
        ],
        output="screen",
    )

    load_joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    load_f1tenth_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["f1tenth_controller", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    gazebo_headless = IncludeLaunchDescription(
    PythonLaunchDescriptionSource([
        PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
    ]),
    launch_arguments={"gz_args": ["--headless-rendering -s -r -v 3 empty.sdf"]}.items(),
    condition=UnlessCondition(gui),
    )
    
    # PENTING: Print untuk debug
    print(f"Loading controller params from: {controller_params_file}")
    
    # controller_manager = Node(
    #     package='controller_manager',
    #     executable='ros2_control_node',
    #     parameters=[controller_params_file],  # ← Harus di sini!
    #     output='screen'
    # )

    cmd_vel_relay = Node(
        package='topic_tools',
        executable='relay',
        name='cmd_vel_relay',
        output='screen',
        arguments=['/cmd_vel', '/f1tenth_controller/reference_unstamped'],
    )

    odom_to_tf_bridge = Node(
        package='TutorialF1tenth',
        executable='odom_tf_bridge',
        name='odom_tf_bridge',
        output='screen'
    )
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        output='screen'
    )

    init_cmd_vel = ExecuteProcess(
        cmd=[
            'ros2', 'topic', 'pub', '--once', 
            '/cmd_vel', 
            'geometry_msgs/msg/Twist', 
            '{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}'
        ],
        output='screen'
    )


    return LaunchDescription([
        cmd_vel_relay,
        set_gz_resource_path, 
        gui_arg,
        gazebo,
        gazebo_headless,
        robot_state_publisher,
        odom_to_tf_bridge,
        gz_spawn_entity,
        gazebo_bridge,
        # controller_manager,
        load_joint_state_broadcaster,
        load_f1tenth_controller,
        rviz_node,
        init_cmd_vel,
    ])