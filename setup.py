from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="appinstalltest",
    version="0.1.1",
    description="APK Compatibility Testing Platform",
    author="Chen Wenkun",
    packages=find_packages(),
    py_modules=["main", "apk_manager", "device_manager", "test_runner", "start_server"],
    install_requires=requirements,
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "appinstalltest=start_server:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
