import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
import numpy as np
from rclpy.qos import DurabilityPolicy

class ObjectChaser(Node):
    def __init__(self):
        super().__init__('object_chaser')
        
        from rclpy.qos import QoSProfile, ReliabilityPolicy
        qos_policy = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            qos_policy)
            
        cmd_vel_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )
          
        self.publishTwist = self.create_publisher(
            Twist, 
            '/cmd_vel', 
            cmd_vel_qos
        )

        self.modified_scan = self.create_publisher(
            LaserScan,
            '/modified_scan',
            qos_policy
        )
        
        print("Object Chaser Started! Mencari benda terdekat...")

        self.go_backwards = False
    
    def modify_scan(self, msg):
        scan = np.array(msg.ranges)

        for s in scan:
            if s == float('inf') or np.isinf(s):
                s = 50.0

        for i in range(len(scan) - 1):
            if scan[i] - scan[i + 1] > 6:
                print(f"dispartity at {i}:{scan[i]}/{i+1}:{scan[i+1]}")
                reference = scan[i + 1]
                for j in range(20):
                    if i - j < 0:
                        break
                    scan[i - j] = reference
            elif scan[i] - scan[i + 1] < -6:
                print(f"dispartity at {i}:{scan[i]}/{i+1}:{scan[i+1]}")
                reference = scan[i]
                for j in range(20):
                    if i + j == len(scan):
                        break
                    scan[i + j] = reference
        
        new_scan = LaserScan()
        new_scan = msg
        new_scan.ranges = scan.tolist()
        self.modified_scan.publish(new_scan)
        return scan               

    def scan_callback(self, msg):
        twist = Twist()
        ranges = self.modify_scan(msg)

        mid = len(ranges) // 2;
        degree = len(ranges) // 270
        maxindex = list(ranges).index(max(ranges))

        factor = 2
        twist.angular.z = (-1.0 + maxindex/(len(ranges) / 2.0)) * factor

        if self.go_backwards:
            twist.linear.x = -4.0
            twist.angular.z = 0.0
        else:
            twist.linear.x = (2.0 - abs(twist.angular.z / factor)) * factor

        front_range = 3;
        front = min(ranges[len(ranges)//2 - front_range:len(ranges)//2 + front_range])
        if front < 0.8:
            self.go_backwards = True
        elif front > 2:
            self.go_backwards = False
        
        print(f"max: {maxindex}")
        print(twist.angular.z)
        print(self.go_backwards)

        self.publishTwist.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = ObjectChaser()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        stop_msg = Twist()
        for p in node.publishers:
            p.publish(stop_msg)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()