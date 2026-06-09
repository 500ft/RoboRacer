from glob import glob
from setuptools import setup

package_name = "f1tenth_modeling"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", glob("config/*.yaml")),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="redhose",
    maintainer_email="redhose@example.com",
    description="ROS 2 runtime layer for F1TENTH model validation and SysID excitation.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "gym_bridge_node = f1tenth_modeling.gym_bridge_node:main",
            "sysid_excitation_node = f1tenth_modeling.sysid_excitation_node:main",
        ],
    },
)
