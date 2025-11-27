from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="appinstalltest",
    version="0.1.4",
    description="APK Compatibility Testing Platform",
    author="Chen Wenkun",
    packages=["appinstalltest_lib"],
    package_data={
        "appinstalltest_lib": ["static/*", "static/favicon.png", "static/style.css", "static/app.js", "static/index.html", "static/dashboard.html"]
    },
    include_package_data=True,
    install_requires=[
        "fastapi",
        "uvicorn",
        "adbutils",
        "loguru",
        "python-multipart",
        "pyaxmlparser",
        "requests",
        "tidevice"
    ],
    entry_points={
        "console_scripts": [
            "appinstalltest=appinstalltest_lib.start_server:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
