#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

# قراءة README
def read_readme():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()

# قراءة المتطلبات
def read_requirements():
    requirements = []
    if os.path.exists("requirements.txt"):
        with open("requirements.txt", "r", encoding="utf-8") as f:
            requirements = [line.strip() for line in f.readlines() 
                          if line.strip() and not line.startswith("#")]
    return requirements

setup(
    name="laqta-optimized",
    version="2.0.0",
    author="LAQTA Team",
    author_email="support@laqta.com",
    description="سكرابر منتجات أمازون محسن وسريع مع واجهة رسومية",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/laqta/optimized-scraper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: X11 Applications :: Qt",
        "Environment :: Win32 (MS Windows)",
        "Environment :: MacOS X",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "performance": [
            "uvloop>=0.17.0",
            "orjson>=3.9.0",
            "lxml>=4.9.0",
        ],
        "monitoring": [
            "psutil>=5.9.0",
            "memory-profiler>=0.61.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "laqta-optimized=integrated_app:main",
            "laqta-test=quick_test:main",
            "laqta-scraper=optimized_scraper:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.txt", "*.md"],
    },
    keywords=[
        "amazon", "scraper", "ecommerce", "price-tracking", 
        "deals", "discounts", "telegram-bot", "async", 
        "playwright", "optimization", "performance"
    ],
    project_urls={
        "Bug Reports": "https://github.com/laqta/optimized-scraper/issues",
        "Documentation": "https://github.com/laqta/optimized-scraper/wiki",
        "Source": "https://github.com/laqta/optimized-scraper",
    },
)